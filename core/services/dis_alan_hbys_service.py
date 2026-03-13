# core/services/dis_alan_hbys_service.py
from typing import Optional
from core.logger import logger
from database.repository_registry import RepositoryRegistry
from datetime import datetime

class DisAlanHbysService:
    def __init__(self, registry: RepositoryRegistry):
        if not registry:
            raise ValueError("Registry boş olamaz")
        self._r = registry

    def excel_import(self, veri_list: list[dict]) -> int:
        """
        IT'den gelen HBYS referans verilerini topluca ekler/günceller.
        veri_list: list[dict] — her dict sistem alanlarını içerir
        """
        repo = self._r.get("Dis_Alan_Hbys_Referans")
        sayac = 0
        for kayit in veri_list:
            try:
                pk = (
                    kayit.get("AnaBilimDali"),
                    kayit.get("Birim"),
                    int(kayit.get("DonemAy", 0)),
                    int(kayit.get("DonemYil", 0)),
                )
                veri = {
                    "AnaBilimDali": kayit.get("AnaBilimDali"),
                    "Birim": kayit.get("Birim"),
                    "DonemAy": int(kayit.get("DonemAy", 0)),
                    "DonemYil": int(kayit.get("DonemYil", 0)),
                    "ToplamVaka": int(kayit.get("ToplamVaka", 0)),
                    "OrtIslemSureDk": float(kayit.get("OrtIslemSureDk", 0)),
                    "PersonelSayisi": int(kayit.get("PersonelSayisi", 0)),
                    "CKolluOrani": float(kayit.get("CKolluOrani", 0)),
                    "ImportTarihi": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "KaynakDosya": "",
                }
                if repo.get_by_id(pk):
                    repo.update(pk, veri)
                else:
                    repo.insert(veri)
                sayac += 1
            except Exception as e:
                logger.error(f"HBYS referans import satır hata: {e}")
        return sayac

    def get_referans(self, anabilim_dali: str, birim: str, donem_ay: int, donem_yil: int) -> Optional[dict]:
        repo = self._r.get("Dis_Alan_Hbys_Referans")
        pk = (anabilim_dali, birim, donem_ay, donem_yil)
        return repo.get_by_id(pk)

    def get_ust_sinir(self, anabilim_dali: str, birim: str, donem_ay: int, donem_yil: int) -> float:
        ref = self.get_referans(anabilim_dali, birim, donem_ay, donem_yil)
        if not ref:
            return 0.0
        try:
            return (
                float(ref.get("ToplamVaka", 0)) *
                float(ref.get("OrtIslemSureDk", 0)) *
                float(ref.get("CKolluOrani", 0)) / 60.0
            )
        except Exception:
            return 0.0
