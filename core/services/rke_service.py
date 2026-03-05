"""
RkeService — RKE (Radyasyon Koruyucu Ekipman) işlemleri için service katmanı

Sorumluluklar:
- RKE envanter listesi
- Muayene kayıtları (fiziksel + skopi)
- Raporlama için veri toplama
"""
from typing import Optional
from core.logger import logger
from database.repository_registry import RepositoryRegistry


class RkeService:
    """RKE modülü işlemleri hizmeti."""

    def __init__(self, registry: RepositoryRegistry):
        if not registry:
            raise ValueError("RepositoryRegistry boş olamaz")
        self._r = registry

    # ───────────────────────────────────────────────────────────
    #  RKE Envanter
    # ───────────────────────────────────────────────────────────

    def get_rke_listesi(self) -> list[dict]:
        """Tüm RKE envanter kayıtlarını döndür."""
        try:
            return self._r.get("RKE_List").get_all() or []
        except Exception as e:
            logger.error(f"RKE listesi yükleme hatası: {e}")
            return []

    def get_rke(self, ekipman_no: str) -> Optional[dict]:
        """Tek RKE kaydını ekipman no'ya göre getir."""
        try:
            return self._r.get("RKE_List").get_by_pk(ekipman_no)
        except Exception as e:
            logger.error(f"RKE '{ekipman_no}' yükleme hatası: {e}")
            return None

    def rke_ekle(self, veri: dict) -> bool:
        """Yeni RKE ekipmanı ekle."""
        try:
            self._r.get("RKE_List").insert(veri)
            logger.info(f"RKE eklendi: {veri.get('EkipmanNo', '?')}")
            return True
        except Exception as e:
            logger.error(f"RKE ekleme hatası: {e}")
            return False

    def rke_guncelle(self, ekipman_no: str, veri: dict) -> bool:
        """RKE kaydını güncelle."""
        try:
            self._r.get("RKE_List").update(ekipman_no, veri)
            logger.info(f"RKE güncellendi: {ekipman_no}")
            return True
        except Exception as e:
            logger.error(f"RKE güncelleme hatası: {e}")
            return False

    def rke_sil(self, ekipman_no: str) -> bool:
        """RKE kaydını sil."""
        try:
            self._r.get("RKE_List").delete(ekipman_no)
            logger.info(f"RKE silindi: {ekipman_no}")
            return True
        except Exception as e:
            logger.error(f"RKE silme hatası: {e}")
            return False

    # ───────────────────────────────────────────────────────────
    #  Muayene
    # ───────────────────────────────────────────────────────────

    def get_muayene_listesi(self, ekipman_no: Optional[str] = None) -> list[dict]:
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
            return tum
        except Exception as e:
            logger.error(f"Muayene listesi yükleme hatası: {e}")
            return []

    def get_muayene(self, kayit_no: str) -> Optional[dict]:
        """Tek muayene kaydını getir."""
        try:
            return self._r.get("RKE_Muayene").get_by_pk(kayit_no)
        except Exception as e:
            logger.error(f"Muayene '{kayit_no}' yükleme hatası: {e}")
            return None

    def muayene_ekle(self, veri: dict) -> bool:
        """Yeni muayene kaydı ekle."""
        try:
            self._r.get("RKE_Muayene").insert(veri)
            logger.info(f"Muayene eklendi: {veri.get('KayitNo', '?')}")
            return True
        except Exception as e:
            logger.error(f"Muayene ekleme hatası: {e}")
            return False

    def muayene_guncelle(self, kayit_no: str, veri: dict) -> bool:
        """Muayene kaydını güncelle."""
        try:
            self._r.get("RKE_Muayene").update(kayit_no, veri)
            logger.info(f"Muayene güncellendi: {kayit_no}")
            return True
        except Exception as e:
            logger.error(f"Muayene güncelleme hatası: {e}")
            return False

    def muayene_sil(self, kayit_no: str) -> bool:
        """Muayene kaydını sil."""
        try:
            self._r.get("RKE_Muayene").delete(kayit_no)
            logger.info(f"Muayene silindi: {kayit_no}")
            return True
        except Exception as e:
            logger.error(f"Muayene silme hatası: {e}")
            return False

    # ───────────────────────────────────────────────────────────
    #  Raporlama
    # ───────────────────────────────────────────────────────────

    def get_rapor_verisi(self, filtre: Optional[dict] = None) -> dict:
        """
        Raporlama için RKE + Muayene verilerini birleştirerek döndür.

        Args:
            filtre: {"birim": "...", "yil": 2024, "durum": "..."} gibi opsiyonel filtre

        Returns:
            {"rke_list": [...], "muayene_list": [...]}
        """
        try:
            rke_list = self.get_rke_listesi()
            muayene_list = self.get_muayene_listesi()

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

            return {"rke_list": rke_list, "muayene_list": muayene_list}

        except Exception as e:
            logger.error(f"RKE rapor verisi hatası: {e}")
            return {"rke_list": [], "muayene_list": []}
