import time

import time
from core.di import get_cloud_adapter
from core.logger import logger
from database.table_config import TABLES


class GSheetManager:
    """
    Google Sheets access layer.

    Optimization strategy:
    OLD: get_all_records() on every operation -> dirty * multiple API calls
    NEW: one read per table -> in-memory index -> batch writes
    """

    BATCH_SIZE = 50
    RATE_LIMIT_DELAY = 1.1

    def __init__(self, cloud_adapter=None):
        self._cloud = cloud_adapter or get_cloud_adapter()

    def get_worksheet(self, table_name: str):
        ws = self._cloud.get_worksheet(table_name)
        if ws is None:
            raise RuntimeError(
                f"Worksheet erisimi yok (mode={self._cloud.mode}, table={table_name})"
            )
        return ws

    # ===================================================
    # READ + CACHE
    # ===================================================

    def read_all(self, table_name: str) -> tuple:
        """
        Read full table once.

        Returns:
            (rows, pk_index, ws)
            - rows: list[dict]
            - pk_index: dict[str, int]  (pk_value -> sheet row number)
            - ws: worksheet object
        """
        self._validate_table(table_name)
        cfg = TABLES[table_name]
        pk = cfg["pk"]
        pk_cols = pk if isinstance(pk, list) else [pk]

        ws = self.get_worksheet(table_name)

        logger.info(f"GSheets: {table_name} okunuyor (tek sefer)")
        records = ws.get_all_records()

        rows = []
        pk_index = {}

        for idx, row in enumerate(records):
            item = {}
            for col in cfg["columns"]:
                item[col] = str(row.get(col, "")).strip()
            rows.append(item)

            key = "|".join(str(row.get(col, "")).strip() for col in pk_cols)
            if key and key != "|".join([""] * len(pk_cols)):
                pk_index[key] = idx + 2

        logger.info(f"GSheets: {table_name} -> {len(rows)} kayit, {len(pk_index)} indexed")
        return rows, pk_index, ws

    # ===================================================
    # BATCH WRITE
    # ===================================================

    def batch_update(self, table_name: str, ws, pk_index: dict, updates: list[dict]):
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
                    f"GSheets update atlandi - PK bulunamadi ({table_name}): {key}"
                )
                continue

            values = [data.get(col, "") for col in columns]
            batch_cells.append({"range": f"A{row_num}", "values": [values]})

        total = len(batch_cells)
        for i in range(0, total, self.BATCH_SIZE):
            chunk = batch_cells[i:i + self.BATCH_SIZE]
            ws.batch_update(chunk)

            sent = min(i + self.BATCH_SIZE, total)
            logger.info(f"GSheets guncellendi ({table_name}): {sent}/{total}")

            if sent < total:
                time.sleep(self.RATE_LIMIT_DELAY)

    def batch_append(self, table_name: str, ws, new_rows: list[dict]):
        if not new_rows:
            return

        self._validate_table(table_name)
        cfg = TABLES[table_name]
        columns = cfg["columns"]

        all_values = []
        for data in new_rows:
            row = [data.get(col, "") for col in columns]
            all_values.append(row)

        total = len(all_values)
        for i in range(0, total, self.BATCH_SIZE):
            chunk = all_values[i:i + self.BATCH_SIZE]
            ws.append_rows(chunk)

            sent = min(i + self.BATCH_SIZE, total)
            logger.info(f"GSheets eklendi ({table_name}): {sent}/{total}")

            if sent < total:
                time.sleep(self.RATE_LIMIT_DELAY)

    # ===================================================
    # SINGLE OPS (backward compatibility)
    # ===================================================

    def read(self, table_name: str) -> list[dict]:
        rows, _, _ = self.read_all(table_name)
        return rows

    def append(self, table_name: str, data: dict):
        self._validate_table(table_name)
        cfg = TABLES[table_name]
        ws = self.get_worksheet(table_name)

        row = [data.get(col, "") for col in cfg["columns"]]
        ws.append_row(row)
        logger.info(f"GSheets eklendi ({table_name}): {data.get(cfg['pk'])}")

    def update(self, table_name: str, pk_value, data: dict) -> bool:
        _, pk_index, ws = self.read_all(table_name)
        self.batch_update(table_name, ws, pk_index, [data])
        return str(pk_value).strip() in pk_index

    def exists(self, table_name: str, pk_value) -> bool:
        _, pk_index, _ = self.read_all(table_name)
        return str(pk_value).strip() in pk_index

    @staticmethod
    def _validate_table(table_name: str):
        if table_name not in TABLES:
            raise ValueError(f"Tanimsiz tablo: {table_name}")
