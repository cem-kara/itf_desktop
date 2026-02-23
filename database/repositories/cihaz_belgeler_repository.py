# database/repositories/cihaz_belgeler_repository.py
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Cihaz Belgeler Repository (Merkezi Belgeler)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

from typing import Dict, Optional, Any, List

from database.base_repository import BaseRepository
from database.table_config import TABLES


class CihazBelgelerRepository(BaseRepository):
    """
    Cihaz_Belgeler tablosu CRUD ve basit sorgular.
    
    Merkezi belgeler tablosu.
    - Cihazlar için belgeler
    - Arızalar için belgeler (IliskiliBelgeID=Arizaid)
    - Bakımlar için belgeler (IliskiliBelgeID=Planid)
    - Kalibrasyonlar için belgeler (IliskiliBelgeID=Kalid)

    Kullanım:
        registry = RepositoryRegistry(db)
        repo = registry.get("Cihaz_Belgeler")

        belgeler = repo.get_by_cihaz_id("RAD-001")
    """

    def __init__(self, db, table_name: str = "Cihaz_Belgeler"):
        config = TABLES.get(table_name, {})
        super().__init__(
            db=db,
            table_name=table_name,
            pk=config.get("pk", ["Cihazid", "BelgeTuru", "Belge"]),
            columns=config.get("columns", []),
            has_sync=False,  # Local-only, synced değil
            date_fields=config.get("date_fields", []),
        )

    def get_by_cihaz_id(self, cihaz_id: str) -> List[Dict[str, Any]]:
        """Cihaz ID ile belge kayıtlarını getirir."""
        return self.get_where({"Cihazid": cihaz_id})

    def get_one(self, cihaz_id: str, belge_turu: str, belge: str) -> Optional[Dict[str, Any]]:
        """Composite PK ile tek kaydı getirir."""
        return self.get_by_id([cihaz_id, belge_turu, belge])

    def get_by_related_id(self, related_id: str, related_type: str) -> List[Dict[str, Any]]:
        """İlişkili ID (Arıza/Bakım/Kalibrasyon) ile belgeleri getirir."""
        return self.get_where({
            "IliskiliBelgeID": related_id,
            "IliskiliBelgeTipi": related_type
        })

