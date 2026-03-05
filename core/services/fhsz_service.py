"""
FhszService — FHSZ (Fazla Hizmet Süresi/Zorunlu) Puantaj işlemleri için service katmanı

Sorumluluklar:
- FHSZ puantaj kayıtları yükleme ve kaydetme
- İzin verisi birleştirme (tatil günleri dahil)
- Personel sabitler (birim, çalışma koşulu)
"""
from typing import Optional
from core.logger import logger
from database.repository_registry import RepositoryRegistry


class FhszService:
    """FHSZ puantaj işlemleri hizmeti."""

    def __init__(self, registry: RepositoryRegistry):
        if not registry:
            raise ValueError("RepositoryRegistry boş olamaz")
        self._r = registry

    # ───────────────────────────────────────────────────────────
    #  Puantaj Kayıtları
    # ───────────────────────────────────────────────────────────

    def get_puantaj_listesi(
        self,
        yil: Optional[int] = None,
        donem: Optional[str] = None,
        personel_id: Optional[str] = None,
    ) -> list[dict]:
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

            return tum
        except Exception as e:
            logger.error(f"FHSZ puantaj yükleme hatası: {e}")
            return []

    def puantaj_kaydet(self, veri: dict) -> bool:
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
                logger.info(f"FHSZ puantaj güncellendi: {pk}")
            else:
                repo.insert(veri)
                logger.info(f"FHSZ puantaj eklendi: {pk}")
            return True
        except Exception as e:
            logger.error(f"FHSZ puantaj kaydetme hatası: {e}")
            return False

    def puantaj_sil(self, personel_id: str, yil: str, donem: str) -> bool:
        """Puantaj kaydını sil."""
        try:
            pk = (str(personel_id), str(yil), str(donem))
            self._r.get("FHSZ_Puantaj").delete(pk)
            logger.info(f"FHSZ puantaj silindi: {pk}")
            return True
        except Exception as e:
            logger.error(f"FHSZ puantaj silme hatası: {e}")
            return False

    # ───────────────────────────────────────────────────────────
    #  Yardımcı Veri
    # ───────────────────────────────────────────────────────────

    def get_personel_listesi(self, aktif_only: bool = True) -> list[dict]:
        """Puantaj sayfası için personel listesi."""
        try:
            rows = self._r.get("Personel").get_all() or []
            if aktif_only:
                rows = [r for r in rows if str(r.get("Durum", "")).strip().lower() != "pasif"]
            return rows
        except Exception as e:
            logger.error(f"Personel listesi (FHSZ) yükleme hatası: {e}")
            return []

    def get_izin_listesi(self, yil: Optional[int] = None) -> list[dict]:
        """İzin Giris kayıtlarını getir (tatil hesabı için)."""
        try:
            tum = self._r.get("Izin_Giris").get_all() or []
            if yil is not None:
                tum = [
                    r for r in tum
                    if str(yil) in str(r.get("BaslamaTarihi", ""))
                       or str(yil) in str(r.get("BitisTarihi", ""))
                ]
            return tum
        except Exception as e:
            logger.error(f"İzin listesi (FHSZ) yükleme hatası: {e}")
            return []

    def get_tatil_gunleri(self, yil: Optional[int] = None) -> list[dict]:
        """Resmi tatil günlerini getir."""
        try:
            tum = self._r.get("Tatiller").get_all() or []
            if yil is not None:
                tum = [r for r in tum if str(yil) in str(r.get("Tarih", ""))]
            return tum
        except Exception as e:
            logger.error(f"Tatil günleri yükleme hatası: {e}")
            return []

    def get_sabitler_by_kod(self, kod: str) -> list[str]:
        """Belirli Kod'a ait sabit değerleri döndür."""
        try:
            sabitler = self._r.get("Sabitler").get_all() or []
            return sorted({
                str(s.get("MenuEleman", "")).strip()
                for s in sabitler
                if str(s.get("Kod", "")).strip() == kod
                   and str(s.get("MenuEleman", "")).strip()
            })
        except Exception as e:
            logger.error(f"Sabitler [{kod}] yükleme hatası: {e}")
            return []

    def get_izin_bilgi(self, tc_no: str) -> Optional[dict]:
        """Personelin izin bakiye bilgisini getir."""
        try:
            return self._r.get("Izin_Bilgi").get_by_pk(tc_no)
        except Exception as e:
            logger.error(f"İzin bilgi yükleme hatası ({tc_no}): {e}")
            return None

    def izin_bilgi_guncelle(self, tc_no: str, veri: dict) -> bool:
        """İzin bakiye bilgisini güncelle."""
        try:
            self._r.get("Izin_Bilgi").update(tc_no, veri)
            logger.info(f"İzin bilgi güncellendi: {tc_no}")
            return True
        except Exception as e:
            logger.error(f"İzin bilgi güncelleme hatası: {e}")
            return False
