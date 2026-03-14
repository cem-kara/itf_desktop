from typing import Optional, List, Tuple
from core.logger import logger
from database.repository_registry import RepositoryRegistry
from datetime import date, datetime

class DisAlanKatsayiService:
    def __init__(self, registry: RepositoryRegistry):
        if not registry:
            raise ValueError("Registry boş olamaz")
        self._r = registry

    def get_aktif_katsayi(self, anabilim_dali: str, birim: str) -> Optional[dict]:
        try:
            repo = self._r.get("Dis_Alan_Katsayi_Protokol")
            today = date.today().isoformat()
            # Aktif ve geçerli protokoller
            protokoller = repo.get_where({
                "AnaBilimDali": anabilim_dali,
                "Birim": birim,
                "Aktif": 1
            })
            # Filtre: GecerlilikBitis NULL veya >= today
            gecerli = [p for p in protokoller if not p.get("GecerlilikBitis") or p["GecerlilikBitis"] >= today]
            if not gecerli:
                return None
            # En güncel GecerlilikBaslangic
            gecerli.sort(key=lambda x: x["GecerlilikBaslangic"], reverse=True)
            return gecerli[0]
        except Exception as e:
            logger.error(f"DisAlanKatsayiService.get_aktif_katsayi: {e}")
            return None

    def get_tum_aktif_dict(self) -> dict:
        """
        Tüm aktif katsayı protokollerini {(AnaBilimDali, Birim): kayit} dict'i olarak döner.
        Worker thread'e geçirilmek üzere ana thread'de önceden çekilir — DB'ye thread'den erişilmez.
        """
        try:
            today = date.today().isoformat()
            rows = self._r.get("Dis_Alan_Katsayi_Protokol").get_all() or []
            sonuc: dict = {}
            for p in rows:
                if not p.get("Aktif"):
                    continue
                bitis = p.get("GecerlilikBitis")
                if bitis and bitis < today:
                    continue
                key = (str(p.get("AnaBilimDali", "")), str(p.get("Birim", "")))
                # En güncel GecerlilikBaslangic öncelikli
                mevcut = sonuc.get(key)
                if mevcut is None or p.get("GecerlilikBaslangic", "") > mevcut.get("GecerlilikBaslangic", ""):
                    sonuc[key] = p
            return sonuc
        except Exception as e:
            logger.error(f"DisAlanKatsayiService.get_tum_aktif_dict: {e}")
            return {}

    def get_tum_protokoller(self) -> List[dict]:
        try:
            return self._r.get("Dis_Alan_Katsayi_Protokol").get_all() or []
        except Exception as e:
            logger.error(f"DisAlanKatsayiService.get_tum_protokoller: {e}")
            return []

    def get_birim_listesi(self) -> List[Tuple[str, str]]:
        try:
            rows = self._r.get("Dis_Alan_Katsayi_Protokol").get_all() or []
            return list({(r["AnaBilimDali"], r["Birim"]) for r in rows})
        except Exception as e:
            logger.error(f"DisAlanKatsayiService.get_birim_listesi: {e}")
            return []

    def protokol_ekle(self, veri: dict) -> bool:
        try:
            repo = self._r.get("Dis_Alan_Katsayi_Protokol")
            pk = (veri.get("AnaBilimDali"), veri.get("Birim"), veri.get("GecerlilikBaslangic"))
            if repo.get_by_id(pk):
                logger.warning("Aynı protokol zaten mevcut")
                return False
            repo.insert(veri)
            return True
        except Exception as e:
            logger.error(f"DisAlanKatsayiService.protokol_ekle: {e}")
            return False

    def protokol_guncelle(self, pk: tuple, veri: dict) -> bool:
        try:
            repo = self._r.get("Dis_Alan_Katsayi_Protokol")
            kayit = repo.get_by_id(pk)
            if not kayit:
                return False
            # Geçmişe dönük kayıt ise sadece açıklama ve referans güncellenebilir
            today = date.today().isoformat()
            if kayit["GecerlilikBaslangic"] < today:
                veri = {k: v for k, v in veri.items() if k in ("AciklamaFormul", "ProtokolRef")}
                if not veri:
                    return False
            repo.update(pk, veri)
            return True
        except Exception as e:
            logger.error(f"DisAlanKatsayiService.protokol_guncelle: {e}")
            return False

    def protokol_pasife_al(self, anabilim_dali: str, birim: str) -> bool:
        try:
            repo = self._r.get("Dis_Alan_Katsayi_Protokol")
            today = date.today().isoformat()
            aktifler = repo.get_where({"AnaBilimDali": anabilim_dali, "Birim": birim, "Aktif": 1})
            for kayit in aktifler:
                pk = (kayit["AnaBilimDali"], kayit["Birim"], kayit["GecerlilikBaslangic"])
                repo.update(pk, {"Aktif": 0, "GecerlilikBitis": today})
            return True
        except Exception as e:
            logger.error(f"DisAlanKatsayiService.protokol_pasife_al: {e}")
            return False
