"""
FhszService — FHSZ (Fazla Hizmet Süresi/Zorunlu) Puantaj işlemleri için service katmanı

Sorumluluklar:
- FHSZ puantaj kayıtları yükleme ve kaydetme
- İzin verisi birleştirme (tatil günleri dahil)
- Personel sabitler (birim, çalışma koşulu)
"""
from typing import Optional

from core.hata_yonetici import SonucYonetici
from database.repository_registry import RepositoryRegistry


class FhszService:
    """FHSZ puantaj işlemleri hizmeti."""

    def __init__(self, registry: RepositoryRegistry):
        if not registry:
            raise ValueError("RepositoryRegistry boş olamaz")
        self._r = registry

    # ───────────────────────────────────────────────────────────
    #  Repository Accessors
    # ───────────────────────────────────────────────────────────

    def get_sabitler_repo(self) -> SonucYonetici:
        """Sabitler repository'sine eriş."""
        return SonucYonetici.tamam(veri=self._r.get("Sabitler"))

    # ───────────────────────────────────────────────────────────
    #  Puantaj Kayıtları
    # ───────────────────────────────────────────────────────────

    def get_puantaj_listesi(
        self,
        yil: Optional[int] = None,
        donem: Optional[str] = None,
        personel_id: Optional[str] = None,
    ) -> SonucYonetici:
        """
        FHSZ puantaj kayıtlarını getir.

        Args:
            yil:        Yıl filtresi (int)
            donem:      Dönem filtresi ("1" … "6")
            personel_id: Personel filtresi
        """
        try:
            tum = self._r.get("FHSZ_Puantaj").get_all() or []

            if yil is not None:
                tum = [r for r in tum if str(r.get("AitYil", "")) == str(yil)]
            if donem is not None:
                tum = [r for r in tum if str(r.get("Donem", "")) == str(donem)]
            if personel_id is not None:
                tum = [r for r in tum if str(r.get("Personelid", "")).strip() == str(personel_id).strip()]

            return SonucYonetici.tamam(veri=tum)
        except Exception as e:
            return SonucYonetici.hata(e, "FhszService.get_puantaj_listesi")

    def puantaj_kaydet(self, veri: dict) -> SonucYonetici:
        """
        Puantaj kaydı ekle veya güncelle (upsert).
        PK: (Personelid, AitYil, Donem)
        """
        try:
            repo = self._r.get("FHSZ_Puantaj")
            pk = (
                str(veri.get("Personelid", "")),
                str(veri.get("AitYil", "")),
                str(veri.get("Donem", "")),
            )
            mevcut = repo.get_by_pk(pk)
            if mevcut:
                repo.update(pk, veri)
                return SonucYonetici.tamam(f"FHSZ puantaj güncellendi: {pk}")
            else:
                repo.insert(veri)
                return SonucYonetici.tamam(f"FHSZ puantaj eklendi: {pk}")
        except Exception as e:
            return SonucYonetici.hata(e, "FhszService.puantaj_kaydet")

    def puantaj_sil(self, personel_id: str, yil: str, donem: str) -> SonucYonetici:
        """Puantaj kaydını sil."""
        try:
            pk = (str(personel_id), str(yil), str(donem))
            self._r.get("FHSZ_Puantaj").delete(pk)
            return SonucYonetici.tamam(f"FHSZ puantaj silindi: {pk}")
        except Exception as e:
            return SonucYonetici.hata(e, "FhszService.puantaj_sil")

    # ───────────────────────────────────────────────────────────
    #  Yardımcı Veri
    # ───────────────────────────────────────────────────────────

    def get_personel_listesi(self, aktif_only: bool = True) -> SonucYonetici:
        """Puantaj sayfası için personel listesi."""
        try:
            rows = self._r.get("Personel").get_all() or []
            if aktif_only:
                rows = [r for r in rows if str(r.get("Durum", "")).strip().lower() != "pasif"]
            return SonucYonetici.tamam(veri=rows)
        except Exception as e:
            return SonucYonetici.hata(e, "FhszService.get_personel_listesi")

    def get_izin_listesi(self, yil: Optional[int] = None) -> SonucYonetici:
        """İzin Giris kayıtlarını getir (tatil hesabı için)."""
        try:
            tum = self._r.get("Izin_Giris").get_all() or []
            if yil is not None:
                tum = [
                    r for r in tum
                    if str(yil) in str(r.get("BaslamaTarihi", ""))
                       or str(yil) in str(r.get("BitisTarihi", ""))
                ]
            return SonucYonetici.tamam(veri=tum)
        except Exception as e:
            return SonucYonetici.hata(e, "FhszService.get_izin_listesi")

    def get_tatil_gunleri(self, yil: Optional[int] = None) -> SonucYonetici:
        """Resmi tatil günlerini getir."""
        try:
            tum = self._r.get("Tatiller").get_all() or []
            if yil is not None:
                tum = [r for r in tum if str(yil) in str(r.get("Tarih", ""))]
            return SonucYonetici.tamam(veri=tum)
        except Exception as e:
            return SonucYonetici.hata(e, "FhszService.get_tatil_gunleri")

    def get_sabitler_by_kod(self, kod: str) -> SonucYonetici:
        """Belirli Kod'a ait sabit değerleri döndür."""
        try:
            sabitler = self._r.get("Sabitler").get_all() or []
            data = sorted({
                str(s.get("MenuEleman", "")).strip()
                for s in sabitler
                if str(s.get("Kod", "")).strip() == kod
                   and str(s.get("MenuEleman", "")).strip()
            })
            return SonucYonetici.tamam(veri=data)
        except Exception as e:
            return SonucYonetici.hata(e, "FhszService.get_sabitler_by_kod")

    def get_izin_bilgi(self, tc_no: str) -> SonucYonetici:
        """Personelin izin bakiye bilgisini getir."""
        try:
            data = self._r.get("Izin_Bilgi").get_by_pk(tc_no)
            return SonucYonetici.tamam(veri=data)
        except Exception as e:
            return SonucYonetici.hata(e, "FhszService.get_izin_bilgi")

    def izin_bilgi_guncelle(self, tc_no: str, veri: dict) -> SonucYonetici:
        """İzin bakiye bilgisini güncelle."""
        try:
            self._r.get("Izin_Bilgi").update(tc_no, veri)
            return SonucYonetici.tamam(f"İzin bilgi güncellendi: {tc_no}")
        except Exception as e:
            return SonucYonetici.hata(e, "FhszService.izin_bilgi_guncelle")
