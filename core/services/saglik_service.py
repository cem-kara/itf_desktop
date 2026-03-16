"""
SaglikService — Personel Sağlık Takip işlemleri için service katmanı

Sorumluluklar:
- Sağlık takip kayıtları (muayene, sonuç, doküman)
- Personel + Sağlık verisi birleşik sorgular
- Yeni kayıt ekleme / güncelleme
"""
from typing import Optional
from core.hata_yonetici import SonucYonetici
from database.repository_registry import RepositoryRegistry


class SaglikService:
    """Personel sağlık takip işlemleri hizmeti."""

    def __init__(self, registry: RepositoryRegistry):
        if not registry:
            raise ValueError("RepositoryRegistry boş olamaz")
        self._r = registry

    # ───────────────────────────────────────────────────────────
    #  Repository Accessors
    # ───────────────────────────────────────────────────────────

    # ───────────────────────────────────────────────────────────
    #  Sağlık Kayıtları
    # ───────────────────────────────────────────────────────────

    def get_saglik_kayitlari(self, personel_id: Optional[str] = None) -> SonucYonetici:
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
            return SonucYonetici.tamam(data=tum)
        except Exception as e:
            return SonucYonetici.hata(e, "SaglikService.get_saglik_kayitlari")

    def get_saglik_kaydi(self, kayit_no: str) -> SonucYonetici:
        """Tek sağlık kaydını getir."""
        try:
            data = self._r.get("Personel_Saglik_Takip").get_by_pk(kayit_no)
            return SonucYonetici.tamam(data=data)
        except Exception as e:
            return SonucYonetici.hata(e, f"SaglikService.get_saglik_kaydi({kayit_no})")

    def saglik_kaydi_ekle(self, veri: dict) -> SonucYonetici:
        """Yeni sağlık takip kaydı ekle."""
        try:
            self._r.get("Personel_Saglik_Takip").insert(veri)
            return SonucYonetici.tamam(f"Sağlık kaydı eklendi: {veri.get('KayitNo', '?')}")
        except Exception as e:
            return SonucYonetici.hata(e, "SaglikService.saglik_kaydi_ekle")

    def saglik_kaydi_guncelle(self, kayit_no: str, veri: dict) -> SonucYonetici:
        """Sağlık kaydını güncelle."""
        try:
            self._r.get("Personel_Saglik_Takip").update(kayit_no, veri)
            return SonucYonetici.tamam(f"Sağlık kaydı güncellendi: {kayit_no}")
        except Exception as e:
            return SonucYonetici.hata(e, "SaglikService.saglik_kaydi_guncelle")

    def saglik_kaydi_sil(self, kayit_no: str) -> SonucYonetici:
        """Sağlık kaydını sil."""
        try:
            self._r.get("Personel_Saglik_Takip").delete(kayit_no)
            return SonucYonetici.tamam(f"Sağlık kaydı silindi: {kayit_no}")
        except Exception as e:
            return SonucYonetici.hata(e, "SaglikService.saglik_kaydi_sil")

    # ───────────────────────────────────────────────────────────
    #  Personel + Sağlık Birleşik Sorgu
    # ───────────────────────────────────────────────────────────

    def get_personel_saglik_ozeti(self, personel_id: str) -> SonucYonetici:
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
            kayitlar_sonuc = self.get_saglik_kayitlari(personel_id)
            if not kayitlar_sonuc.basarili:
                return kayitlar_sonuc
            kayitlar = kayitlar_sonuc.data or []

            son_kayit = None
            if kayitlar:
                son_kayit = sorted(
                    kayitlar,
                    key=lambda r: str(r.get("MuayeneTarihi", "")),
                    reverse=True
                )[0]

            data = {
                "personel": personel or {},
                "son_kayit": son_kayit,
                "toplam_kayit": len(kayitlar),
            }
            return SonucYonetici.tamam(data=data)
        except Exception as e:
            return SonucYonetici.hata(e, f"SaglikService.get_personel_saglik_ozeti({personel_id})")

    def get_personel_listesi(self, aktif_only: bool = True) -> SonucYonetici:
        """
        Sağlık paneli için personel listesi.
        Sağlık takip sayfasında personel seçici olarak kullanılır.
        """
        try:
            rows = self._r.get("Personel").get_all() or []
            if aktif_only:
                rows = [r for r in rows if str(r.get("Durum", "")).strip().lower() != "pasif"]
            return SonucYonetici.tamam(data=rows)
        except Exception as e:
            return SonucYonetici.hata(e, "SaglikService.get_personel_listesi")

    def get_dokumanlar(self, personel_id: str, belge_turu: Optional[str] = None) -> SonucYonetici:
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
            return SonucYonetici.tamam(data=result)
        except Exception as e:
            return SonucYonetici.hata(e, f"SaglikService.get_dokumanlar({personel_id})")
