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
from core.date_utils import looks_like_date_column, normalize_date_fields


class SyncBatchError(RuntimeError):
    """
    Tüm tablo senkronizasyonunda birden fazla tablonun hata alması durumunu
    yapılandırılmış olarak taşır.
    """

    def __init__(self, failures, total_tables=0, successful_tables=0):
        self.failures = failures or []
        self.total_tables = total_tables
        self.successful_tables = successful_tables
        failed_tables = [f.get("table", "?") for f in self.failures]
        super().__init__(f"Şu tablolarda sync hatası: {', '.join(failed_tables)}")

    def to_ui_messages(self, max_tables=3):
        fail_count = len(self.failures)
        short_msg = f"{fail_count} tabloda hata"

        listed = [f.get("table", "?") for f in self.failures[:max_tables]]
        detail_msg = f"Başarısız tablolar: {', '.join(listed)}"
        if fail_count > max_tables:
            detail_msg += f" ve {fail_count - max_tables} tablo daha"

        return short_msg, detail_msg

    def to_event(self):
        return {
            "event": "SYNC_BATCH_FAILED",
            "total_tables": self.total_tables,
            "successful_tables": self.successful_tables,
            "failed_tables": len(self.failures),
            "failures": self.failures,
        }


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
        failures = []

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
                failure = {
                    "event": "SYNC_TABLE_FAILED",
                    "table": table_name,
                    "step": "sync_table",
                    "error_type": error_type,
                    "error_msg": error_msg[:200],
                    "table_index": i,
                    "table_total": total,
                }
                 
                logger.error(f"[{i}/{total}] {table_name} sync hatası: {error_type}")
                log_sync_error(table_name, "sync_table", e)
                 
                failures.append(failure)
                 
                # Bir tablo hata alırsa diğerlerine devam et
                continue

        # Özet log
        logger.info("=" * 60)
        logger.info(f"SYNC ÖZETİ: {success}/{total} tablo başarılı")
        if failures:
            logger.error(f"Başarısız tablolar: {len(failures)}")
            for fail in failures:
                logger.error(
                    f"  - {fail['table']}: {fail['error_type']} - {fail['error_msg']}"
                )
        logger.info("=" * 60)

        if failures:
            raise SyncBatchError(
                failures=failures,
                total_tables=total,
                successful_tables=success,
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
            just_pushed_keys = set()
            for row in dirty_rows:
                pk_val = {col: row.get(col) for col in pk_cols} if len(pk_cols) > 1 else row.get(pk_cols[0])
                repo.mark_clean(pk_val)
                just_pushed_keys.add(make_key(row))  # PULL'da stale remote ile ezilmesin

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

                # Az önce push edilmiş kayıt: remote henüz güncel değil, atla
                if key in just_pushed_keys:
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
        2. Satırları doğrula (boş PK, bilinmeyen kolon adı vb.)
        3. Local tabloyu tamamen temizle
        4. INSERT OR REPLACE ile tüm kayıtları yaz
           (Sheets'te yinelenen PK varsa son değer kazanır)

        Kullanım: Sabitler, Tatiller gibi sadece merkezi yönetilen tablolar için
        """
        columns = cfg["columns"]
        pk = cfg["pk"]
        date_fields = cfg.get("date_fields") or [c for c in columns if looks_like_date_column(c)]
        # Composite PK desteği: string ise listeye çevir
        pk_cols = pk if isinstance(pk, list) else [pk]

        try:
            log_sync_step(table_name, "pull_only_start")

            # ── 1. Google Sheets'i oku ──
            from database.google import get_worksheet
            ws = get_worksheet(table_name)

            if not ws:
                logger.warning(f"  {table_name} worksheet bulunamadı, atlanıyor")
                return

            records = ws.get_all_records()
            log_sync_step(table_name, "pull_only_read", len(records))
            logger.info(f"  Google Sheets'ten {len(records)} kayıt okundu")

            # ── 2. Boş PK filtresi + aynı tarihe düşen tatilleri birleştir ──
            #
            # Örnek: 23.04.2023 hem "Ramazan Bayramı 3.gün" hem
            # "Ulusal Egemenlik ve Çocuk Bayramı" olabilir.
            # Tarih PRIMARY KEY olduğu için çakışma yaşanır.
            # Çözüm: aynı tarihe ait isimleri " / " ile birleştirip tek kayıt yap.
            #
            # ResmiTatil dışındaki kolonlar (varsa) son satırın değerini alır.

            skipped_rows = []          # boş PK nedeniyle atlanan satırlar
            merged: dict = {}          # {tarih_key: row_dict}  (birleştirilmiş)
            merge_log: dict = {}       # {tarih_key: [isim1, isim2, ...]}

            MERGE_COL = "ResmiTatil"   # Birleştirilecek metin kolonu

            for i, row in enumerate(records, start=2):  # start=2: başlık satırı 1
                row = normalize_date_fields(row, date_fields)
                pk_values = [str(row.get(col, "")).strip() for col in pk_cols]

                # Boş PK → atla
                if any(v == "" for v in pk_values):
                    reason = f"Boş PK ({', '.join(pk_cols)}={pk_values})"
                    skipped_rows.append({"sheet_row": i, "reason": reason})
                    logger.warning(
                        f"  [{table_name}] Satır #{i} atlandı — {reason} | "
                        f"Veri: { {c: row.get(c) for c in columns} }"
                    )
                    continue

                key = "|".join(pk_values)

                if key not in merged:
                    # İlk kez görülen tarih: kaydı olduğu gibi al
                    merged[key] = {c: str(row.get(c, "")).strip() for c in columns}
                    merge_log[key] = [merged[key].get(MERGE_COL, "")]
                else:
                    # Aynı tarih tekrar geldi: sadece MERGE_COL'u birleştir,
                    # diğer kolonları son satırın değeriyle güncelle
                    yeni_isim = str(row.get(MERGE_COL, "")).strip()
                    if yeni_isim and yeni_isim not in merge_log[key]:
                        merge_log[key].append(yeni_isim)
                        merged[key][MERGE_COL] = " / ".join(merge_log[key])
                    # Diğer kolonları güncelle (PK ve MERGE_COL hariç)
                    for c in columns:
                        if c not in pk_cols and c != MERGE_COL:
                            merged[key][c] = str(row.get(c, "")).strip()

            # Birleştirme özeti logla
            merged_dates = [k for k, v in merge_log.items() if len(v) > 1]
            if merged_dates:
                logger.info(
                    f"  [{table_name}] Aynı güne düşen {len(merged_dates)} tatil "
                    f"birleştirildi:"
                )
                for key in merged_dates:
                    logger.info(
                        f"    {key.replace('|', ' + ')} → "
                        f"\"{merged[key].get(MERGE_COL)}\""
                    )

            if skipped_rows:
                logger.error(
                    f"  [{table_name}] {len(skipped_rows)} satır boş PK nedeniyle "
                    f"atlandı — Google Sheets'te düzeltilmesi gerekiyor!"
                )

            valid_records = list(merged.values())

            # ── 3. Local tabloyu temizle ──
            self.db.execute(f"DELETE FROM {table_name}")
            logger.info(f"  Local {table_name} tablosu temizlendi")

            # ── 4. INSERT ile kayıtları yaz ──
            # Birleştirme sonrası artık duplicate PK kalmaz,
            # yine de OR REPLACE bırakıyoruz ek güvence olarak.
            inserted = 0
            failed_rows = []
            cols_str = ", ".join(columns)
            placeholders = ", ".join(["?"] * len(columns))
            sql = f"INSERT OR REPLACE INTO {table_name} ({cols_str}) VALUES ({placeholders})"

            for row in valid_records:
                values = [row.get(col, "") for col in columns]
                try:
                    self.db.execute(sql, values)
                    inserted += 1
                except Exception as row_error:
                    row_preview = {c: row.get(c) for c in columns}
                    failed_rows.append({"error": str(row_error), "data": row_preview})
                    logger.error(
                        f"  [{table_name}] INSERT hatası: "
                        f"{type(row_error).__name__}: {row_error} | Veri: {row_preview}"
                    )
                    continue

            # ── 5. Özet rapor ──
            total_skipped = len(skipped_rows) + len(failed_rows)
            log_sync_step(table_name, "pull_only_complete", inserted)
            logger.info(
                f"  {table_name} pull_only tamamlandı: "
                f"{inserted} kayıt eklendi "
                f"({len(records)} Sheets satırı → {len(valid_records)} benzersiz kayıt"
                + (f", {total_skipped} atlandı" if total_skipped else "")
                + ") ✓"
            )

            stats = {'pushed': 0, 'pulled': inserted}
            log_sync_complete(table_name, stats)

        except Exception as e:
            log_sync_error(table_name, "pull_only", e)
            raise
