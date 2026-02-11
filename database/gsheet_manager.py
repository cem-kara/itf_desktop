import time
from core.logger import logger
from database.google import get_worksheet
from database.table_config import TABLES


class GSheetManager:
    """
    Google Sheets erişim katmanı.

    Optimizasyon stratejisi:
    ─────────────────────────
    ESKİ: Her işlemde get_all_records() → N dirty kayıt = N×3 API çağrısı
    YENİ: Tablo başına TEK okuma → bellekte index → toplu yazma

    Bu sayede 2000+ kayıtlı tablolar bile sorunsuz senkronize olur.
    """

    # Google Sheets API rate limit koruması
    BATCH_SIZE = 50           # Tek seferde yazılacak satır
    RATE_LIMIT_DELAY = 1.1    # İstekler arası bekleme (saniye)

    # ═══════════════════════════════════════════════
    #  TEK OKUMA + CACHE
    # ═══════════════════════════════════════════════

    def read_all(self, table_name: str) -> tuple:
        """
        Tablo verisini TEK SEFERDE okur.

        Returns:
            (rows, pk_index, ws)
            - rows     : list[dict]           → tüm kayıtlar
            - pk_index : dict[str, int]       → pk_value → satır numarası (sheet'teki)
            - ws       : worksheet nesnesi    → yazma işlemleri için
        """
        self._validate_table(table_name)
        cfg = TABLES[table_name]
        pk = cfg["pk"]

        # PK'yı her zaman list olarak tut
        pk_cols = pk if isinstance(pk, list) else [pk]

        ws = get_worksheet(table_name)

        logger.info(f"GSheets: {table_name} okunuyor (tek sefer)")
        records = ws.get_all_records()

        rows = []
        pk_index = {}

        for idx, row in enumerate(records):
            item = {}
            for col in cfg["columns"]:
                item[col] = str(row.get(col, "")).strip()
            rows.append(item)

            # Composite key → "val1|val2|val3"
            key = "|".join(str(row.get(col, "")).strip() for col in pk_cols)
            if key and key != "|".join([""] * len(pk_cols)):
                pk_index[key] = idx + 2  # sheet row number

        logger.info(
            f"GSheets: {table_name} → {len(rows)} kayıt, "
            f"{len(pk_index)} indexed"
        )

        return rows, pk_index, ws

    # ═══════════════════════════════════════════════
    #  TOPLU YAZMA (BATCH)
    # ═══════════════════════════════════════════════

    def batch_update(self, table_name: str, ws, pk_index: dict,
                     updates: list[dict]):
        """
        Birden fazla kaydı TOPLU günceller.

        Args:
            ws        : worksheet nesnesi (read_all'dan)
            pk_index  : pk → satır no eşlemesi (read_all'dan)
            updates   : güncellenecek kayıtlar listesi
        """
        if not updates:
            return

        self._validate_table(table_name)
        cfg = TABLES[table_name]
        pk = cfg["pk"]
        pk_cols = pk if isinstance(pk, list) else [pk]
        columns = cfg["columns"]

        batch_cells = []

        for data in updates:
            key = "|".join(str(data.get(col, "")).strip() for col in pk_cols)
            row_num = pk_index.get(key)

            if row_num is None:
                logger.warning(
                    f"GSheets update atlandı — PK bulunamadı "
                    f"({table_name}): {key}"
                )
                continue

            values = [data.get(col, "") for col in columns]
            batch_cells.append({
                "range": f"A{row_num}",
                "values": [values]
            })

        # Parçalı gönder (rate limit koruması)
        total = len(batch_cells)
        for i in range(0, total, self.BATCH_SIZE):
            chunk = batch_cells[i:i + self.BATCH_SIZE]
            ws.batch_update(chunk)

            sent = min(i + self.BATCH_SIZE, total)
            logger.info(
                f"GSheets güncellendi ({table_name}): "
                f"{sent}/{total}"
            )

            if sent < total:
                time.sleep(self.RATE_LIMIT_DELAY)

    # ─────────────────────────────────────────────

    def batch_append(self, table_name: str, ws, new_rows: list[dict]):
        """
        Birden fazla kaydı TOPLU ekler.
        """
        if not new_rows:
            return

        self._validate_table(table_name)
        cfg = TABLES[table_name]
        columns = cfg["columns"]

        all_values = []
        for data in new_rows:
            row = [data.get(col, "") for col in columns]
            all_values.append(row)

        # Parçalı gönder
        total = len(all_values)
        for i in range(0, total, self.BATCH_SIZE):
            chunk = all_values[i:i + self.BATCH_SIZE]
            ws.append_rows(chunk)

            sent = min(i + self.BATCH_SIZE, total)
            logger.info(
                f"GSheets eklendi ({table_name}): "
                f"{sent}/{total}"
            )

            if sent < total:
                time.sleep(self.RATE_LIMIT_DELAY)

    # ═══════════════════════════════════════════════
    #  TEKLİ İŞLEMLER (geriye uyumluluk)
    # ═══════════════════════════════════════════════

    def read(self, table_name: str) -> list[dict]:
        """Geriye uyumlu — sadece rows döner."""
        rows, _, _ = self.read_all(table_name)
        return rows

    def append(self, table_name: str, data: dict):
        """Tekli ekleme (küçük işlemler için)."""
        self._validate_table(table_name)
        cfg = TABLES[table_name]
        ws = get_worksheet(table_name)

        row = [data.get(col, "") for col in cfg["columns"]]
        ws.append_row(row)
        logger.info(f"GSheets eklendi ({table_name}): {data.get(cfg['pk'])}")

    def update(self, table_name: str, pk_value, data: dict) -> bool:
        """Tekli güncelleme (küçük işlemler için)."""
        _, pk_index, ws = self.read_all(table_name)
        self.batch_update(table_name, ws, pk_index, [data])
        return str(pk_value).strip() in pk_index

    def exists(self, table_name: str, pk_value) -> bool:
        """Tekli kontrol (küçük işlemler için)."""
        _, pk_index, _ = self.read_all(table_name)
        return str(pk_value).strip() in pk_index

    # ═══════════════════════════════════════════════

    @staticmethod
    def _validate_table(table_name: str):
        if table_name not in TABLES:
            raise ValueError(f"Tanımsız tablo: {table_name}")