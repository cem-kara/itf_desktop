"""
RkeService — RKE (Radyasyon Koruyucu Ekipman) işlemleri için service katmanı

Sorumluluklar:
- RKE envanter listesi
- Muayene kayıtları (fiziksel + skopi)
- Raporlama için veri toplama
"""
from typing import Optional
from core.hata_yonetici import SonucYonetici
from database.repository_registry import RepositoryRegistry


class RkeService:
    """RKE modülü işlemleri hizmeti."""

    def __init__(self, registry: RepositoryRegistry):
        if not registry:
            raise ValueError("RepositoryRegistry boş olamaz")
        self._r = registry

    # ───────────────────────────────────────────────────────────
    #  Repository Accessor'ları (UI için güvenli geçiş)
    # ───────────────────────────────────────────────────────────
    
    # ───────────────────────────────────────────────────────────
    #  RKE Envanter
    # ───────────────────────────────────────────────────────────

    def get_rke_listesi(self) -> SonucYonetici:
        """Tüm RKE envanter kayıtlarını döndür."""
        try:
            data = self._r.get("RKE_List").get_all() or []
            return SonucYonetici.tamam(data=data)
        except Exception as e:
            return SonucYonetici.hata(e, "RkeService.get_rke_listesi")

    def get_rke(self, ekipman_no: str) -> SonucYonetici:
        """Tek RKE kaydını ekipman no'ya göre getir."""
        try:
            data = self._r.get("RKE_List").get_by_pk(ekipman_no)
            return SonucYonetici.tamam(data=data)
        except Exception as e:
            return SonucYonetici.hata(e, f"RkeService.get_rke({ekipman_no})")

    def rke_ekle(self, veri: dict) -> SonucYonetici:
        """Yeni RKE ekipmanı ekle."""
        try:
            self._r.get("RKE_List").insert(veri)
            return SonucYonetici.tamam(f"RKE eklendi: {veri.get('EkipmanNo', '?')}")
        except Exception as e:
            return SonucYonetici.hata(e, "RkeService.rke_ekle")

    def rke_guncelle(self, ekipman_no: str, veri: dict) -> SonucYonetici:
        """RKE kaydını güncelle."""
        try:
            self._r.get("RKE_List").update(ekipman_no, veri)
            return SonucYonetici.tamam(f"RKE güncellendi: {ekipman_no}")
        except Exception as e:
            return SonucYonetici.hata(e, "RkeService.rke_guncelle")

    def rke_sil(self, ekipman_no: str) -> SonucYonetici:
        """RKE kaydını sil."""
        try:
            self._r.get("RKE_List").delete(ekipman_no)
            return SonucYonetici.tamam(f"RKE silindi: {ekipman_no}")
        except Exception as e:
            return SonucYonetici.hata(e, "RkeService.rke_sil")

    # ───────────────────────────────────────────────────────────
    #  Muayene
    # ───────────────────────────────────────────────────────────

    def get_muayene_listesi(self, ekipman_no: Optional[str] = None) -> SonucYonetici:
        """
        Muayene kayıtlarını getir.

        Args:
            ekipman_no: Belirtilirse sadece o ekipmana ait kayıtlar döner.
                        None ise tüm muayeneler döner.
        """
        try:
            tum = self._r.get("RKE_Muayene").get_all() or []
            if ekipman_no is not None:
                tum = [
                    r for r in tum
                    if str(r.get("EkipmanNo", "")).strip() == str(ekipman_no).strip()
                ]
            return SonucYonetici.tamam(data=tum)
        except Exception as e:
            return SonucYonetici.hata(e, "RkeService.get_muayene_listesi")

    def get_muayene(self, kayit_no: str) -> SonucYonetici:
        """Tek muayene kaydını getir."""
        try:
            data = self._r.get("RKE_Muayene").get_by_pk(kayit_no)
            return SonucYonetici.tamam(data=data)
        except Exception as e:
            return SonucYonetici.hata(e, f"RkeService.get_muayene({kayit_no})")

    def muayene_ekle(self, veri: dict) -> SonucYonetici:
        """Yeni muayene kaydı ekle."""
        try:
            self._r.get("RKE_Muayene").insert(veri)
            return SonucYonetici.tamam(f"Muayene eklendi: {veri.get('KayitNo', '?')}")
        except Exception as e:
            return SonucYonetici.hata(e, "RkeService.muayene_ekle")

    def muayene_guncelle(self, kayit_no: str, veri: dict) -> SonucYonetici:
        """Muayene kaydını güncelle."""
        try:
            self._r.get("RKE_Muayene").update(kayit_no, veri)
            return SonucYonetici.tamam(f"Muayene güncellendi: {kayit_no}")
        except Exception as e:
            return SonucYonetici.hata(e, "RkeService.muayene_guncelle")

    def muayene_sil(self, kayit_no: str) -> SonucYonetici:
        """Muayene kaydını sil."""
        try:
            self._r.get("RKE_Muayene").delete(kayit_no)
            return SonucYonetici.tamam(f"Muayene silindi: {kayit_no}")
        except Exception as e:
            return SonucYonetici.hata(e, "RkeService.muayene_sil")

    # ───────────────────────────────────────────────────────────
    #  Raporlama
    # ───────────────────────────────────────────────────────────

    def get_rapor_verisi(self, filtre: Optional[dict] = None) -> SonucYonetici:
        """
        Raporlama için RKE + Muayene verilerini birleştirerek döndür.

        Args:
            filtre: {"birim": "...", "yil": 2024, "durum": "..."} gibi opsiyonel filtre

        Returns:
            SonucYonetici
        """
        try:
            rke_list_sonuc = self.get_rke_listesi()
            if not rke_list_sonuc.basarili:
                return rke_list_sonuc
            rke_list = rke_list_sonuc.data or []

            muayene_list_sonuc = self.get_muayene_listesi()
            if not muayene_list_sonuc.basarili:
                return muayene_list_sonuc
            muayene_list = muayene_list_sonuc.data or []

            if filtre:
                birim = filtre.get("birim")
                yil = filtre.get("yil")
                durum = filtre.get("durum")

                if birim:
                    rke_list = [r for r in rke_list if str(r.get("Birim", "")) == birim]
                    ekipman_nos = {str(r.get("EkipmanNo", "")) for r in rke_list}
                    muayene_list = [m for m in muayene_list if str(m.get("EkipmanNo", "")) in ekipman_nos]

                if yil:
                    muayene_list = [
                        m for m in muayene_list
                        if str(yil) in str(m.get("FMuayeneTarihi", ""))
                           or str(yil) in str(m.get("SMuayeneTarihi", ""))
                    ]

                if durum:
                    rke_list = [r for r in rke_list if str(r.get("Durum", "")) == durum]

            return SonucYonetici.tamam(data={"rke_list": rke_list, "muayene_list": muayene_list})

        except Exception as e:
            return SonucYonetici.hata(e, "RkeService.get_rapor_verisi")
