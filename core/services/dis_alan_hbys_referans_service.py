# core/services/dis_alan_hbys_referans_service.py
from typing import Optional
from core.logger import logger
from database.repository_registry import RepositoryRegistry

class DisAlanHbysReferansService:
    def __init__(self, registry: RepositoryRegistry):
        if not registry:
            raise ValueError("Registry boş olamaz")
        self._r = registry

    def get_referans_listesi(self, aktif_only: bool = False) -> list[dict]:
        try:
            repo = self._r.get("Dis_Alan_Hbys_Referans")
            if aktif_only:
                return repo.get_where({"Aktif": 1})
            return repo.get_all() or []
        except Exception as e:
            logger.error(f"DisAlanHbysReferansService.get_referans_listesi: {e}")
            return []

    def ekle(self, veri: dict) -> bool:
        try:
            repo = self._r.get("Dis_Alan_Hbys_Referans")
            repo.insert(veri)
            return True
        except Exception as e:
            logger.error(f"DisAlanHbysReferansService.ekle: {e}")
            return False

    def guncelle(self, pk: str, veri: dict) -> bool:
        try:
            repo = self._r.get("Dis_Alan_Hbys_Referans")
            repo.update(pk, veri)
            return True
        except Exception as e:
            logger.error(f"DisAlanHbysReferansService.guncelle: {e}")
            return False

    def sil(self, pk: str) -> bool:
        try:
            return self._r.get("Dis_Alan_Hbys_Referans").delete(pk)
        except Exception as e:
            logger.error(f"DisAlanHbysReferansService.sil: {e}")
            return False
