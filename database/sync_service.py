import time
from core.logger import (
    logger, 
    log_sync_start, 
    log_sync_step, 
    log_sync_error, 
    log_sync_complete
)
from database.gsheet_manager import GSheetManager
from database.table_config import TABLES


class SyncService:
    """
    Senkronizasyon servisi.

    Her tablo için akış:
    ────────────────────
    1. Google Sheets'i TEK SEFER oku (read_all)
    2. Local dirty kayıtları topla
    3. PUSH: dirty kayıtları toplu gönder (batch_update + batch_append)
    4. PULL: remote'ta olup local'de olmayanları toplu ekle
    5. PULL: remote'taki güncellemeleri local'e yansıt (clean kayıtlar için)
    6. Bir sonraki tabloya geç

    API çağrı sayısı:
    ESKİ → tablo başına: 1 + (dirty × 3) = onlarca istek
    YENİ → tablo başına: 1 okuma + 1-2 yazma = 2-3 istek
    """

    def __init__(self, db, registry):
        self.db = db
        self.registry = registry
        self.gsheet = GSheetManager()

    # ═══════════════════════════════════════════════

    def sync_all(self):
        """
        Tüm senkronize edilebilir tabloları sırayla işler.
        """
        syncable = [
            (name, cfg) for name, cfg in TABLES.items()
            if cfg.get("sync", True) and cfg.get("pk") is not None
        ]

        total = len(syncable)
        success = 0
        errors = []

        logger.info(f"Toplam {total} tablo senkronize edilecek")

        for i, (table_name, cfg) in enumerate(syncable, 1):
            try:
                logger.info(f"[{i}/{total}] {table_name} sync başladı")
                log_sync_start(table_name)
                
                self.sync_table(table_name)
                
                success += 1
                logger.info(f"[{i}/{total}] {table_name} sync başarılı ✓")
                
            except Exception as e:
                error_type = type(e).__name__
                error_msg = str(e)
                
                logger.error(f"[{i}/{total}] {table_name} sync hatası: {error_type}")
                log_sync_error(table_name, "sync_table", e)
                
                errors.append({
                    'table': table_name,
                    'error_type': error_type,
                    'error_msg': error_msg[:100]  # İlk 100 karakter
                })
                
                # Bir tablo hata alırsa diğerlerine devam et
                continue

        # Özet log
        logger.info("=" * 60)
        logger.info(f"SYNC ÖZETİ: {success}/{total} tablo başarılı")
        if errors:
            logger.error(f"Başarısız tablolar: {len(errors)}")
            for err in errors:
                logger.error(f"  - {err['table']}: {err['error_type']} - {err['error_msg']}")
        logger.info("=" * 60)

        if errors:
            failed_tables = [e['table'] for e in errors]
            raise RuntimeError(
                f"Şu tablolarda sync hatası: {', '.join(failed_tables)}"
            )

    # ═══════════════════════════════════════════════

    def sync_table(self, table_name: str):
        """
        Tek tablo senkronizasyonu — optimize edilmiş akış.
        Composite PK (list) ve tekli PK (string) destekler.
        
        🔧 FIX: Google Sheets'teki güncellemeler artık local'e yansıyor!
        """
        cfg = TABLES[table_name]

        # ── Pull-only tablolar (Sabitler, Tatiller) ──
        if cfg.get("sync_mode") == "pull_only":
            logger.info(f"  {table_name} pull_only modda çalışıyor")
            log_sync_step(table_name, "pull_only_mode")
            self._pull_replace(table_name, cfg)
            return
        
        repo = self.registry.get(table_name)
        cfg = TABLES[table_name]
        pk = cfg["pk"]  # string veya list

        # PK'yı her zaman list olarak tut
        pk_cols = pk if isinstance(pk, list) else [pk]

        def make_key(data):
            """Dict'ten composite key string üretir."""
            return "|".join(str(data.get(col, "")).strip() for col in pk_cols)

        try:
            # ──────────────────────────────────────────
            # 1️⃣  Google Sheets'i TEK SEFER oku
            # ──────────────────────────────────────────
            log_sync_step(table_name, "read_remote")
            remote_rows, pk_index, ws = self.gsheet.read_all(table_name)
            log_sync_step(table_name, "read_remote_complete", len(remote_rows))

            # ──────────────────────────────────────────
            # 2️⃣  PUSH: Local → Google Sheets
            # ──────────────────────────────────────────
            log_sync_step(table_name, "check_dirty")
            dirty_rows = repo.get_dirty()
            logger.info(f"  Local dirty: {len(dirty_rows)}")

            to_update = []
            to_append = []

            for row in dirty_rows:
                key = make_key(row)
                if key in pk_index:
                    to_update.append(row)
                else:
                    to_append.append(row)

            if to_update:
                log_sync_step(table_name, "push_update", len(to_update))
                self.gsheet.batch_update(table_name, ws, pk_index, to_update)
                logger.info(f"  PUSH güncelleme: {len(to_update)}")

            if to_append:
                log_sync_step(table_name, "push_append", len(to_append))
                self.gsheet.batch_append(table_name, ws, to_append)
                logger.info(f"  PUSH yeni ekleme: {len(to_append)}")

            # Dirty → clean
            for row in dirty_rows:
                pk_val = {col: row.get(col) for col in pk_cols} if len(pk_cols) > 1 else row.get(pk_cols[0])
                repo.mark_clean(pk_val)

            # ──────────────────────────────────────────
            # 3️⃣  PULL: Google Sheets → Local
            # ──────────────────────────────────────────
            log_sync_step(table_name, "pull_remote")
            new_count = 0
            updated_count = 0

            for remote in remote_rows:
                key = make_key(remote)
                if not key or key == "|".join([""] * len(pk_cols)):
                    continue

                pk_val = {col: remote.get(col) for col in pk_cols} if len(pk_cols) > 1 else remote.get(pk_cols[0])
                local = repo.get_by_id(pk_val)

                if not local:
                    # Yeni kayıt → ekle
                    remote["sync_status"] = "clean"
                    repo.insert(remote)
                    new_count += 1
                else:
                    # 🔧 FIX: Mevcut kayıt var
                    # Local'de dirty değilse (yani kullanıcı değiştirmemişse),
                    # Google Sheets'teki güncellemeleri al
                    local_status = local.get("sync_status", "").strip()
                    
                    if local_status != "dirty":
                        # Remote'taki verilerle local'i güncelle
                        # (sync_status'u clean olarak koru)
                        remote["sync_status"] = "clean"
                        
                        # Sadece değişen alanları güncelle
                        has_changes = False
                        for col in cfg["columns"]:
                            if col in ["sync_status", "updated_at"]:
                                continue
                            remote_val = str(remote.get(col, "")).strip()
                            local_val = str(local.get(col, "")).strip()
                            if remote_val != local_val:
                                has_changes = True
                                break
                        
                        if has_changes:
                            repo.insert(remote)  # INSERT OR REPLACE
                            updated_count += 1
                    # else: Local dirty → kullanıcı değiştirmiş, dokunma

            if new_count:
                log_sync_step(table_name, "pull_new", new_count)
                logger.info(f"  PULL yeni kayıt: {new_count}")
            
            if updated_count:
                log_sync_step(table_name, "pull_update", updated_count)
                logger.info(f"  PULL güncelleme: {updated_count}")

            # İstatistiklerle tamamlama logu
            stats = {
                'pushed': len(to_update) + len(to_append),
                'pulled': new_count + updated_count
            }
            log_sync_complete(table_name, stats)
            logger.info(f"  {table_name} sync tamamlandı ✓")
            
        except Exception as e:
            log_sync_error(table_name, "sync_table", e)
            raise  # Hatayı yukarı ilet

    def _pull_replace(self, table_name, cfg):
        """
        Pull-only modda çalışan tablolar için özel sync mantığı.
        
        Akış:
        1. Google Sheets'ten tüm kayıtları oku
        2. Local tabloyu tamamen temizle
        3. Sheets'teki kayıtları local'e ekle
        
        Kullanım: Sabitler, Tatiller gibi sadece merkezi yönetilen tablolar için
        """
        columns = cfg["columns"]
        
        try:
            log_sync_step(table_name, "pull_only_start")
            
            # Google Sheets'i oku
            from database.google import get_worksheet
            ws = get_worksheet(table_name)
            
            if not ws:
                logger.warning(f"  {table_name} worksheet bulunamadı, atlanıyor")
                return
            
            records = ws.get_all_records()
            log_sync_step(table_name, "pull_only_read", len(records))
            logger.info(f"  Google Sheets'ten {len(records)} kayıt okundu")
            
            # Local tabloyu temizle
            self.db.execute(f"DELETE FROM {table_name}")
            logger.info(f"  Local {table_name} tablosu temizlendi")
            
            # Sheets'ten tüm kayıtları ekle
            inserted = 0
            for row in records:
                # Sadece tanımlı kolonları al
                cols = ", ".join(columns)
                placeholders = ", ".join(["?"] * len(columns))
                values = [str(row.get(col, "")).strip() for col in columns]
                
                try:
                    self.db.execute(
                        f"INSERT INTO {table_name} ({cols}) VALUES ({placeholders})",
                        values
                    )
                    inserted += 1
                except Exception as row_error:
                    logger.warning(f"  Satır eklenemedi: {row_error}")
                    continue
            
            log_sync_step(table_name, "pull_only_complete", inserted)
            logger.info(f"  {table_name} pull_only: {inserted}/{len(records)} kayıt yüklendi ✓")
            
            # İstatistikler
            stats = {'pushed': 0, 'pulled': inserted}
            log_sync_complete(table_name, stats)
            
        except Exception as e:
            log_sync_error(table_name, "pull_only", e)
            raise
