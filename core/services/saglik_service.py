"""
SaglikService — Personel Sağlık Takip işlemleri için service katmanı

Sorumluluklar:
- Sağlık takip kayıtları (muayene, sonuç, doküman)
- Personel + Sağlık verisi birleşik sorgular
- Yeni kayıt ekleme / güncelleme
"""
from typing import Optional
from core.logger import logger
from database.repository_registry import RepositoryRegistry


class SaglikService:
    """Personel sağlık takip işlemleri hizmeti."""

    def __init__(self, registry: RepositoryRegistry):
        if not registry:
            raise ValueError("RepositoryRegistry boş olamaz")
        self._r = registry

    # ───────────────────────────────────────────────────────────
    #  Sağlık Kayıtları
    # ───────────────────────────────────────────────────────────

    def get_saglik_kayitlari(self, personel_id: Optional[str] = None) -> list[dict]:
        """
        Sağlık takip kayıtlarını getir.

        Args:
            personel_id: Belirtilirse sadece o personelin kayıtları döner.
        """
        try:
            tum = self._r.get("Personel_Saglik_Takip").get_all() or []
            if personel_id is not None:
                tum = [
                    r for r in tum
                    if str(r.get("Personelid", "")).strip() == str(personel_id).strip()
                ]
            return tum
        except Exception as e:
            logger.error(f"Sağlık kayıtları yükleme hatası: {e}")
            return []

    def get_saglik_kaydi(self, kayit_no: str) -> Optional[dict]:
        """Tek sağlık kaydını getir."""
        try:
            return self._r.get("Personel_Saglik_Takip").get_by_pk(kayit_no)
        except Exception as e:
            logger.error(f"Sağlık kaydı '{kayit_no}' yükleme hatası: {e}")
            return None

    def saglik_kaydi_ekle(self, veri: dict) -> bool:
        """Yeni sağlık takip kaydı ekle."""
        try:
            self._r.get("Personel_Saglik_Takip").insert(veri)
            logger.info(f"Sağlık kaydı eklendi: {veri.get('KayitNo', '?')} ({veri.get('Personelid', '?')})")
            return True
        except Exception as e:
            logger.error(f"Sağlık kaydı ekleme hatası: {e}")
            return False

    def saglik_kaydi_guncelle(self, kayit_no: str, veri: dict) -> bool:
        """Sağlık kaydını güncelle."""
        try:
            self._r.get("Personel_Saglik_Takip").update(kayit_no, veri)
            logger.info(f"Sağlık kaydı güncellendi: {kayit_no}")
            return True
        except Exception as e:
            logger.error(f"Sağlık kaydı güncelleme hatası: {e}")
            return False

    def saglik_kaydi_sil(self, kayit_no: str) -> bool:
        """Sağlık kaydını sil."""
        try:
            self._r.get("Personel_Saglik_Takip").delete(kayit_no)
            logger.info(f"Sağlık kaydı silindi: {kayit_no}")
            return True
        except Exception as e:
            logger.error(f"Sağlık kaydı silme hatası: {e}")
            return False

    # ───────────────────────────────────────────────────────────
    #  Personel + Sağlık Birleşik Sorgu
    # ───────────────────────────────────────────────────────────

    def get_personel_saglik_ozeti(self, personel_id: str) -> dict:
        """
        Bir personelin son sağlık durumunu özetle.

        Returns:
            {
                "personel": {...},
                "son_kayit": {...} | None,
                "toplam_kayit": int
            }
        """
        try:
            personel = self._r.get("Personel").get_by_pk(personel_id)
            kayitlar = self.get_saglik_kayitlari(personel_id)

            son_kayit = None
            if kayitlar:
                son_kayit = sorted(
                    kayitlar,
                    key=lambda r: str(r.get("MuayeneTarihi", "")),
                    reverse=True
                )[0]

            return {
                "personel": personel or {},
                "son_kayit": son_kayit,
                "toplam_kayit": len(kayitlar),
            }
        except Exception as e:
            logger.error(f"Personel sağlık özeti hatası ({personel_id}): {e}")
            return {"personel": {}, "son_kayit": None, "toplam_kayit": 0}

    def get_personel_listesi(self, aktif_only: bool = True) -> list[dict]:
        """
        Sağlık paneli için personel listesi.
        Sağlık takip sayfasında personel seçici olarak kullanılır.
        """
        try:
            rows = self._r.get("Personel").get_all() or []
            if aktif_only:
                rows = [r for r in rows if str(r.get("Durum", "")).strip().lower() != "pasif"]
            return rows
        except Exception as e:
            logger.error(f"Personel listesi (sağlık) yükleme hatası: {e}")
            return []

    def get_dokumanlar(self, personel_id: str, belge_turu: Optional[str] = None) -> list[dict]:
        """
        Personele ait sağlık belgelerini getir.

        Args:
            personel_id: Personel TC/ID
            belge_turu: Opsiyonel filtre ("RaporDosya" vb.)
        """
        try:
            tum = self._r.get("Dokumanlar").get_all() or []
            result = [
                r for r in tum
                if str(r.get("EntityId", "")).strip() == str(personel_id).strip()
                   and str(r.get("EntityType", "")).strip() == "Personel_Saglik"
            ]
            if belge_turu:
                result = [r for r in result if str(r.get("BelgeTuru", "")) == belge_turu]
            return result
        except Exception as e:
            logger.error(f"Sağlık belgeleri yükleme hatası ({personel_id}): {e}")
            return []
