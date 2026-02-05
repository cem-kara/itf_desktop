from database.base_repository import BaseRepository
from database.table_config import TABLES


class RepositoryRegistry:
    def __init__(self, db):
        self.db = db
        self._repos = {}

    def get(self, table_name):
        """
        İstenilen tablo için repository döner.
        Aynı repository bir kez oluşturulur (singleton-like).
        """
        if table_name not in self._repos:
            cfg = TABLES[table_name]

            self._repos[table_name] = BaseRepository(
                db=self.db,
                table_name=table_name,
                pk=cfg["pk"],
                columns=cfg["columns"] + ["sync_status", "updated_at"]
            )

        return self._repos[table_name]

    def all(self):
        """
        Tüm repository'leri dict olarak döner
        """
        return {
            name: self.get(name)
            for name in TABLES.keys()
        }
