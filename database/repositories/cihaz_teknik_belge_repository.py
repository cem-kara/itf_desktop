# database/repositories/cihaz_teknik_belge_repository.py
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Cihaz Teknik Belge Repository
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

from typing import Dict, Optional, Any, List

from database.base_repository import BaseRepository
from database.table_config import TABLES


class CihazTeknikBelgeRepository(BaseRepository):
    """
    Cihaz_Teknik_Belge tablosu CRUD ve basit sorgular.

    Kullanım:
        registry = RepositoryRegistry(db)
        repo = registry.get("Cihaz_Teknik_Belge")

        belgeler = repo.get_by_cihaz_id("RAD-001")
    """

    def __init__(self, db, table_name: str = "Cihaz_Teknik_Belge"):
        config = TABLES.get(table_name, {})
        super().__init__(
            db=db,
            table_name=table_name,
            pk=config.get("pk", ["Cihazid", "BelgeTuru", "Belge"]),
            columns=config.get("columns", []),
            has_sync=True,
            date_fields=config.get("date_fields", []),
        )

    def get_by_cihaz_id(self, cihaz_id: str) -> List[Dict[str, Any]]:
        """Cihaz ID ile belge kayıtlarını getirir."""
        return self.get_where({"Cihazid": cihaz_id})

    def get_one(self, cihaz_id: str, belge_turu: str, belge: str) -> Optional[Dict[str, Any]]:
        """Composite PK ile tek kaydı getirir."""
        return self.get_by_id([cihaz_id, belge_turu, belge])
