from core.logger import logger
from database.gsheet_manager import GSheetManager
from database.table_config import TABLES


class SyncService:
    def __init__(self, db, registry):
        self.db = db
        self.registry = registry
        self.gsheet = GSheetManager()

    # -----------------------------------------------------

    def sync_all(self):
        """
        Tüm tabloları sırayla senkron eder
        """
        for table_name in TABLES.keys():
            self.sync_table(table_name)

    # -----------------------------------------------------

    def sync_table(self, table_name: str):
        """
        Tek tablo senkronu
        """
        logger.info(f"{table_name} sync başladı")

        repo = self.registry.get(table_name)
        pk = repo.pk

        # 1️⃣ Local dirty kayıtlar → GSheets
        dirty_rows = repo.get_dirty()

        logger.info(f"Local dirty kayıt sayısı ({table_name}): {len(dirty_rows)}")

        for row in dirty_rows:
            if self.gsheet.exists(table_name, row[pk]):
                self.gsheet.update(table_name, row[pk], row)
            else:
                self.gsheet.append(table_name, row)

            repo.mark_clean(row[pk])

        # 2️⃣ GSheets → Local
        remote_rows = self.gsheet.read(table_name)
        logger.info(f"GSheets kayıt sayısı ({table_name}): {len(remote_rows)}")

        for remote in remote_rows:
            local = repo.get_by_id(remote[pk])
            if not local:
                repo.insert(remote)
            else:
                repo.update(remote[pk], remote)

        logger.info(f"{table_name} sync tamamlandı")
