import time
from core.logger import logger
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
    5. Bir sonraki tabloya geç

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

        for i, (table_name, cfg) in enumerate(syncable, 1):
            try:
                logger.info(f"[{i}/{total}] {table_name} sync başladı")
                self.sync_table(table_name)
                success += 1
            except Exception as e:
                logger.error(f"{table_name} sync hatası: {e}")
                errors.append(table_name)
                # Bir tablo hata alırsa diğerlerine devam et
                continue

        logger.info(
            f"Sync özeti: {success}/{total} başarılı"
            + (f", hatalar: {errors}" if errors else "")
        )

        if errors:
            raise RuntimeError(
                f"Şu tablolarda sync hatası: {', '.join(errors)}"
            )

    # ═══════════════════════════════════════════════

    def sync_table(self, table_name: str):
        """
        Tek tablo senkronizasyonu — optimize edilmiş akış.
        Composite PK (list) ve tekli PK (string) destekler.
        """
        repo = self.registry.get(table_name)
        cfg = TABLES[table_name]
        pk = cfg["pk"]  # string veya list

        # PK'yı her zaman list olarak tut
        pk_cols = pk if isinstance(pk, list) else [pk]

        def make_key(data):
            """Dict'ten composite key string üretir."""
            return "|".join(str(data.get(col, "")).strip() for col in pk_cols)

        # ──────────────────────────────────────────
        # 1️⃣  Google Sheets'i TEK SEFER oku
        # ──────────────────────────────────────────
        remote_rows, pk_index, ws = self.gsheet.read_all(table_name)

        # ──────────────────────────────────────────
        # 2️⃣  PUSH: Local → Google Sheets
        # ──────────────────────────────────────────
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
            self.gsheet.batch_update(table_name, ws, pk_index, to_update)
            logger.info(f"  PUSH güncelleme: {len(to_update)}")

        if to_append:
            self.gsheet.batch_append(table_name, ws, to_append)
            logger.info(f"  PUSH yeni ekleme: {len(to_append)}")

        # Dirty → clean
        for row in dirty_rows:
            pk_val = {col: row.get(col) for col in pk_cols} if len(pk_cols) > 1 else row.get(pk_cols[0])
            repo.mark_clean(pk_val)

        # ──────────────────────────────────────────
        # 3️⃣  PULL: Google Sheets → Local
        # ──────────────────────────────────────────
        new_count = 0

        for remote in remote_rows:
            key = make_key(remote)
            if not key or key == "|".join([""] * len(pk_cols)):
                continue

            pk_val = {col: remote.get(col) for col in pk_cols} if len(pk_cols) > 1 else remote.get(pk_cols[0])
            local = repo.get_by_id(pk_val)

            if not local:
                remote["sync_status"] = "clean"
                repo.insert(remote)
                new_count += 1

        if new_count:
            logger.info(f"  PULL yeni kayıt: {new_count}")

        logger.info(f"  {table_name} sync tamamlandı ✓")