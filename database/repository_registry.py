from database.base_repository import BaseRepository
from database.table_config import TABLES


class RepositoryRegistry:
    def __init__(self, db):
        self.db = db
        self._repos = {}

    def get(self, table_name):
        """
        İstenilen tablo için repository döner.
        Özel repository sınıfları varsa onları kullanır (PersonelRepository, vb).
        Aynı repository bir kez oluşturulur (singleton-like).
        """
        if table_name not in self._repos:
            # Özel repository sınıfları
            if table_name == "Personel":
                from database.repositories.personel_repository import PersonelRepository
                self._repos[table_name] = PersonelRepository(self.db)
            elif table_name == "Cihazlar":
                from database.repositories.cihaz_repository import CihazRepository
                self._repos[table_name] = CihazRepository(self.db)
            elif table_name == "Cihaz_Teknik":
                from database.repositories.cihaz_teknik_repository import CihazTeknikRepository
                self._repos[table_name] = CihazTeknikRepository(self.db)
            elif table_name == "RKE_Envanter":
                from database.repositories.rke_repository import RKERepository
                self._repos[table_name] = RKERepository(self.db)
            else:
                # Generic BaseRepository
                cfg = TABLES[table_name]
                has_sync = cfg.get("sync", True) and cfg.get("pk") is not None
                extra_cols = ["sync_status", "updated_at"] if has_sync else []

                self._repos[table_name] = BaseRepository(
                    db=self.db,
                    table_name=table_name,
                    pk=cfg["pk"],
                    columns=cfg["columns"] + extra_cols,
                    has_sync=has_sync,
                    date_fields=cfg.get("date_fields")
                )

        return self._repos[table_name]

    def all_syncable(self):
        """
        Sadece senkronize edilebilir tabloların repository'lerini döner
        """
        return {
            name: self.get(name)
            for name, cfg in TABLES.items()
            if cfg.get("sync", True) and cfg.get("pk") is not None
        }

    def all(self):
        """
        Tüm repository'leri dict olarak döner
        """
        return {
            name: self.get(name)
            for name in TABLES.keys()
        }
