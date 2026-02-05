from core.logger import logger
from database.google_baglanti import get_worksheet
from database.table_config import TABLES


class GSheetManager:
    """
    Google Sheets erişim katmanı.
    - Yetkilendirme içermez
    - Sadece okuma / ekleme / güncelleme yapar
    """

    def read(self, table_name: str) -> list[dict]:
        """
        Google Sheets'ten tabloyu okur ve
        kolon isimlerine göre dict listesi döner
        """
        if table_name not in TABLES:
            raise ValueError(f"Tanımsız tablo: {table_name}")

        cfg = TABLES[table_name]
        ws = get_worksheet(table_name)

        logger.info(f"GSheets: {table_name} verileri okunuyor")

        records = ws.get_all_records()
        result = []

        for row in records:
            item = {}
            for col in cfg["columns"]:
                item[col] = str(row.get(col, "")).strip()
            result.append(item)

        logger.info(f"GSheets kayıt sayısı ({table_name}): {len(result)}")
        return result

    # -----------------------------------------------------

    def append(self, table_name: str, data: dict):
        """
        Google Sheets'e yeni kayıt ekler
        """
        if table_name not in TABLES:
            raise ValueError(f"Tanımsız tablo: {table_name}")

        cfg = TABLES[table_name]
        ws = get_worksheet(table_name)

        row = [data.get(col, "") for col in cfg["columns"]]
        ws.append_row(row)

        logger.info(
            f"GSheets eklendi ({table_name}): {data.get(cfg['pk'])}"
        )

    # -----------------------------------------------------

    def update(self, table_name: str, pk_value, data: dict) -> bool:
        """
        Primary key'e göre Google Sheets kaydını günceller
        """
        if table_name not in TABLES:
            raise ValueError(f"Tanımsız tablo: {table_name}")

        cfg = TABLES[table_name]
        ws = get_worksheet(table_name)

        records = ws.get_all_records()

        for idx, row in enumerate(records, start=2):
            sheet_pk = str(row.get(cfg["pk"], "")).strip()
            local_pk = str(pk_value).strip()

            if sheet_pk == local_pk:
                values = [data.get(col, "") for col in cfg["columns"]]
                ws.update(f"A{idx}", [values])

                logger.info(
                    f"GSheets güncellendi ({table_name}): {pk_value}"
                )
                return True

        logger.warning(
            f"GSheets update bulunamadı ({table_name}): {pk_value}"
        )
        return False

    # -----------------------------------------------------

    def exists(self, table_name: str, pk_value) -> bool:
        """
        Google Sheets'te kayıt var mı kontrolü
        """
        if table_name not in TABLES:
            raise ValueError(f"Tanımsız tablo: {table_name}")

        cfg = TABLES[table_name]
        ws = get_worksheet(table_name)

        records = ws.get_all_records()
        local_pk = str(pk_value).strip()

        for row in records:
            if str(row.get(cfg["pk"], "")).strip() == local_pk:
                return True

        return False
