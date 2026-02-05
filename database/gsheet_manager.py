from core.logger import logger
from google_baglanti import get_worksheet
from database.table_config import TABLES


class GSheetManager:

    def read(self, table_name):
        cfg = TABLES[table_name]
        ws = get_worksheet(table_name)

        logger.info(f"GSheets: {table_name} okunuyor")
        rows = ws.get_all_records()

        result = []
        for row in rows:
            item = {}
            for col in cfg["columns"]:
                item[col] = str(row.get(col, "")).strip()
            result.append(item)

        logger.info(f"GSheets kayıt sayısı ({table_name}): {len(result)}")
        return result

    def append(self, table_name, data: dict):
        cfg = TABLES[table_name]
        ws = get_worksheet(table_name)

        row = [data.get(col, "") for col in cfg["columns"]]
        ws.append_row(row)

        logger.info(f"GSheets eklendi ({table_name}): {data.get(cfg['pk'])}")

    def update(self, table_name, pk_value, data: dict):
        cfg = TABLES[table_name]
        ws = get_worksheet(table_name)
        records = ws.get_all_records()

        for idx, row in enumerate(records, start=2):
            if str(row.get(cfg["pk"])) == str(pk_value):
                values = [data.get(col, "") for col in cfg["columns"]]
                ws.update(f"A{idx}", [values])
                logger.info(f"GSheets güncellendi ({table_name}): {pk_value}")
                return

        logger.warning(f"GSheets update bulunamadı ({table_name}): {pk_value}")
