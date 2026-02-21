# database/repositories/cihaz_teknik_repository.py
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Cihaz Teknik Verileri Repository
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

from typing import Dict, Optional, Any

from database.base_repository import BaseRepository
from database.table_config import TABLES


class CihazTeknikRepository(BaseRepository):
    """
    Cihaz_Teknik tablosu CRUD ve basit sorgular.

    Kullanım:
        registry = RepositoryRegistry(db)
        repo = registry.get("Cihaz_Teknik")

        teknik = repo.get_by_cihaz_id("RAD-001")
    """

    def __init__(self, db, table_name: str = "Cihaz_Teknik"):
        config = TABLES.get(table_name, {})
        super().__init__(
            db=db,
            table_name=table_name,
            pk=config.get("pk", "Cihazid"),
            columns=config.get("columns", []),
            has_sync=True,
            date_fields=config.get("date_fields", []),
        )

    def get_by_cihaz_id(self, cihaz_id: str) -> Optional[Dict[str, Any]]:
        """Cihaz ID ile teknik kaydi getirir."""
        return self.get_by_id(cihaz_id)
