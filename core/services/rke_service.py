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

    def get_rke_repo(self):
        """RKE_List repository'sine eriş."""
        return self._r.get("RKE_List")

    def get_muayene_repo(self):
        """RKE_Muayene repository'sine eriş."""
        return self._r.get("RKE_Muayene")

    def get_dokuman_repo(self):
        """Dokumanlar repository'sine eriş."""
        return self._r.get("Dokumanlar")

    # ───────────────────────────────────────────────────────────
    #  RKE Envanter
    # ───────────────────────────────────────────────────────────

    def get_rke_listesi(self) -> SonucYonetici:
        """Tüm RKE envanter kayıtlarını döndür."""
        try:
            data = self._r.get("RKE_List").get_all() or []
            return SonucYonetici.tamam(veri=data)
        except Exception as e:
            return SonucYonetici.hata(e, "RkeService.get_rke_listesi")

    def get_sabitler_listesi(self, kod: Optional[str] = None) -> SonucYonetici:
        try:
            rows = self._r.get("Sabitler").get_all() or []
            if kod is not None:
                hedef = str(kod).strip()
                rows = [r for r in rows if str(r.get("Kod", "")).strip() == hedef]
            return SonucYonetici.tamam(veri=rows)
        except Exception as e:
            return SonucYonetici.hata(e, "RkeService.get_sabitler_listesi")

    def get_rke(self, ekipman_no: str) -> SonucYonetici:
        """Tek RKE kaydını ekipman no'ya göre getir."""
        try:
            data = self._r.get("RKE_List").get_by_pk(ekipman_no)
            return SonucYonetici.tamam(veri=data)
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
            return SonucYonetici.tamam(veri=tum)
        except Exception as e:
            return SonucYonetici.hata(e, "RkeService.get_muayene_listesi")

    def get_muayene(self, kayit_no: str) -> SonucYonetici:
        """Tek muayene kaydını getir."""
        try:
            data = self._r.get("RKE_Muayene").get_by_pk(kayit_no)
            return SonucYonetici.tamam(veri=data)
        except Exception as e:
            return SonucYonetici.hata(e, f"RkeService.get_muayene({kayit_no})")

    def muayene_ekle(self, veri: dict) -> SonucYonetici:
        """Yeni muayene kaydı ekle; RKE_List.Durum ve KontrolTarihi'ni güncelle."""
        try:
            self._r.get("RKE_Muayene").insert(veri)
            self._rke_listini_guncelle(veri)
            return SonucYonetici.tamam(f"Muayene eklendi: {veri.get('KayitNo', '?')}")
        except Exception as e:
            return SonucYonetici.hata(e, "RkeService.muayene_ekle")

    def muayene_guncelle(self, kayit_no: str, veri: dict) -> SonucYonetici:
        """Muayene kaydını güncelle; RKE_List'i de güncelle."""
        try:
            self._r.get("RKE_Muayene").update(kayit_no, veri)
            self._rke_listini_guncelle(veri)
            return SonucYonetici.tamam(f"Muayene güncellendi: {kayit_no}")
        except Exception as e:
            return SonucYonetici.hata(e, "RkeService.muayene_guncelle")

    def _rke_listini_guncelle(self, muayene: dict) -> None:
        """
        Muayene sonucuna göre RKE_List.Durum ve KontrolTarihi'ni günceller.

        Durum belirleme:
          Fiziksel VEYA Skopi → "Kullanıma Uygun Değil"  → "Uygun Değil"
          İkisi de "Kullanıma Uygun" (Skopi "Yapılmadı" dahil)  → "Uygun"

        KontrolTarihi: Skopi tarihi varsa skopi, yoksa fiziksel tarihi.
        """
        ekipman_no = str(muayene.get("EkipmanNo", "")).strip()
        if not ekipman_no:
            return
        try:
            fiz = str(muayene.get("FizikselDurum", "")).strip()
            sko = str(muayene.get("SkopiDurum", "")).strip()
            fiz_t = str(muayene.get("FMuayeneTarihi", "") or "").strip()
            sko_t = str(muayene.get("SMuayeneTarihi", "") or "").strip()

            uygun_d = ("Değil" in fiz) or ("Değil" in sko)
            yeni_durum = "Uygun Değil" if uygun_d else "Uygun"

            # Kontrol tarihi: skopi varsa skopi, yoksa fiziksel
            yeni_tarih = sko_t if sko_t else fiz_t

            guncelleme: dict = {"Durum": yeni_durum}
            if yeni_tarih:
                guncelleme["KontrolTarihi"] = yeni_tarih

            self._r.get("RKE_List").update(ekipman_no, guncelleme)
        except Exception as e:
            from core.logger import logger
            logger.warning(f"RKE_List güncelleme (muayene sonrası): {e}")

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
            rke_list = rke_list_sonuc.veri or []

            muayene_list_sonuc = self.get_muayene_listesi()
            if not muayene_list_sonuc.basarili:
                return muayene_list_sonuc
            muayene_list = muayene_list_sonuc.veri or []

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

            return SonucYonetici.tamam(veri={"rke_list": rke_list, "muayene_list": muayene_list})

        except Exception as e:
            return SonucYonetici.hata(e, "RkeService.get_rapor_verisi")
