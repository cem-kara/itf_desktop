# database/repositories/dokumanlar_repository.py
# ─────────────────────────────────────────────────────────────────────────────
# Dokumanlar Repository (Ortak Belgeler)
# ─────────────────────────────────────────────────────────────────────────────

from typing import Dict, Optional, Any, List

from database.base_repository import BaseRepository

from database.table_config import TABLES


class DokumanlarRepository(BaseRepository):
    """
    Dokumanlar tablosu CRUD ve basit sorgular.

    Kullanım:
        registry = RepositoryRegistry(db)
        repo = registry.get("Dokumanlar")

        repo.get_by_entity("cihaz", "RAD-001")
    """

    def __init__(self, db, table_name: str = "Dokumanlar"):
        config = TABLES.get(table_name, {})
        super().__init__(
            db=db,
            table_name=table_name,
            pk=config.get("pk", ["EntityType", "EntityId", "BelgeTuru", "Belge"]),
            columns=config.get("columns", []),
            has_sync=False,  # Local-only
            date_fields=config.get("date_fields", []),
        )

    def get_by_entity(self, entity_type: str, entity_id: str) -> List[Dict[str, Any]]:
        """EntityType + EntityId ile belge kayıtlarını getirir."""
        return self.get_where({"EntityType": entity_type, "EntityId": entity_id})

    def get_one(self, entity_type: str, entity_id: str, belge_turu: str, belge: str) -> Optional[Dict[str, Any]]:
        """Composite PK ile tek kaydı getirir."""
        return self.get_by_id([entity_type, entity_id, belge_turu, belge])

    def get_by_doc_type(self, entity_type: str, entity_id: str, doc_type: str) -> List[Dict[str, Any]]:
        """DocType filtresi ile belgeleri getirir."""
        return self.get_where({"EntityType": entity_type, "EntityId": entity_id, "DocType": doc_type})
