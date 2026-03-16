from typing import Optional, List, Tuple
from core.hata_yonetici import SonucYonetici, logger
from database.repository_registry import RepositoryRegistry
from datetime import date, datetime

class DisAlanKatsayiService:
    def __init__(self, registry: RepositoryRegistry):
        if not registry:
            raise ValueError("Registry boş olamaz")
        self._r = registry

    def get_aktif_katsayi(self, anabilim_dali: str, birim: str) -> SonucYonetici:
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
                return SonucYonetici.tamam(veri=None)
            # En güncel GecerlilikBaslangic
            gecerli.sort(key=lambda x: x["GecerlilikBaslangic"], reverse=True)
            return SonucYonetici.tamam(veri=gecerli[0])
        except Exception as e:
            return SonucYonetici.hata(e, "DisAlanKatsayiService.get_aktif_katsayi")

    def get_tum_aktif_dict(self) -> SonucYonetici:
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
            return SonucYonetici.tamam(veri=sonuc)
        except Exception as e:
            return SonucYonetici.hata(e, "DisAlanKatsayiService.get_tum_aktif_dict")

    def get_tum_protokoller(self) -> SonucYonetici:
        try:
            data = self._r.get("Dis_Alan_Katsayi_Protokol").get_all() or []
            return SonucYonetici.tamam(veri=data)
        except Exception as e:
            return SonucYonetici.hata(e, "DisAlanKatsayiService.get_tum_protokoller")

    def get_birim_listesi(self) -> SonucYonetici:
        try:
            rows = self._r.get("Dis_Alan_Katsayi_Protokol").get_all() or []
            data = list({(r["AnaBilimDali"], r["Birim"]) for r in rows})
            return SonucYonetici.tamam(veri=data)
        except Exception as e:
            return SonucYonetici.hata(e, "DisAlanKatsayiService.get_birim_listesi")

    def protokol_ekle(self, veri: dict) -> SonucYonetici:
        try:
            repo = self._r.get("Dis_Alan_Katsayi_Protokol")
            pk = (veri.get("AnaBilimDali"), veri.get("Birim"), veri.get("GecerlilikBaslangic"))
            if repo.get_by_id(pk):
                return SonucYonetici.hata(Exception("Aynı protokol zaten mevcut"), "DisAlanKatsayiService.protokol_ekle")
            repo.insert(veri)
            return SonucYonetici.tamam("Protokol eklendi.")
        except Exception as e:
            return SonucYonetici.hata(e, "DisAlanKatsayiService.protokol_ekle")

    def protokol_guncelle(self, pk: tuple, veri: dict) -> SonucYonetici:
        try:
            repo = self._r.get("Dis_Alan_Katsayi_Protokol")
            kayit = repo.get_by_id(pk)
            if not kayit:
                return SonucYonetici.hata(Exception("Güncellenecek protokol bulunamadı"), "DisAlanKatsayiService.protokol_guncelle")
            # Geçmişe dönük kayıt ise sadece açıklama ve referans güncellenebilir
            today = date.today().isoformat()
            if kayit["GecerlilikBaslangic"] < today:
                veri = {k: v for k, v in veri.items() if k in ("AciklamaFormul", "ProtokolRef")}
                if not veri:
                    return SonucYonetici.hata(Exception("Geçmişe dönük kayıtta sadece açıklama/referans güncellenebilir"), "DisAlanKatsayiService.protokol_guncelle")
            repo.update(pk, veri)
            return SonucYonetici.tamam("Protokol güncellendi.")
        except Exception as e:
            return SonucYonetici.hata(e, "DisAlanKatsayiService.protokol_guncelle")

    def protokol_pasife_al(self, anabilim_dali: str, birim: str) -> SonucYonetici:
        try:
            repo = self._r.get("Dis_Alan_Katsayi_Protokol")
            today = date.today().isoformat()
            aktifler = repo.get_where({"AnaBilimDali": anabilim_dali, "Birim": birim, "Aktif": 1})
            for kayit in aktifler:
                pk = (kayit["AnaBilimDali"], kayit["Birim"], kayit["GecerlilikBaslangic"])
                repo.update(pk, {"Aktif": 0, "GecerlilikBitis": today})
            return SonucYonetici.tamam("Protokol pasife alındı.")
        except Exception as e:
            return SonucYonetici.hata(e, "DisAlanKatsayiService.protokol_pasife_al")
