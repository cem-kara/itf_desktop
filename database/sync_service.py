from core.logger import logger
from database.gsheet_manager import GSheetManager
from database.table_config import TABLES


class SyncService:
    def __init__(self, repositories: dict):
        """
        repositories = {
            "Personel": PersonelRepository(),
            "Izin_Giris": IzinGirisRepository(),
            ...
        }
        """
        self.gsheet = GSheetManager()
        self.repos = repositories

    def sync_all(self):
        for table_name in TABLES.keys():
            self.sync_table(table_name)

    def sync_table(self, table_name):
        logger.info(f"{table_name} sync başladı")

        repo = self.repos[table_name]
        cfg = TABLES[table_name]
        pk = cfg["pk"]

        # 1️⃣ Local → GSheets
        dirty = repo.get_dirty()
        for row in dirty:
            if self.gsheet_record_exists(table_name, pk, row[pk]):
                self.gsheet.update(table_name, row[pk], row)
            else:
                self.gsheet.append(table_name, row)
            repo.mark_clean(row[pk])

        # 2️⃣ GSheets → Local
        remote_rows = self.gsheet.read(table_name)
        for remote in remote_rows:
            local = repo.get_by_id(remote[pk])
            if not local:
                repo.insert(remote)

        logger.info(f"{table_name} sync tamamlandı")

    def gsheet_record_exists(self, table_name, pk, value):
        records = self.gsheet.read(table_name)
        return any(str(r.get(pk)) == str(value) for r in records)
