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

    def get_sabitler_listesi(self, kod: Optional[str] = None) -> SonucYonetici:
        try:
            rows = self._r.get("Sabitler").get_all() or []
            if kod is not None:
                hedef = str(kod).strip()
                rows = [r for r in rows if str(r.get("Kod", "")).strip() == hedef]
            return SonucYonetici.tamam(veri=rows)
        except Exception as e:
            return SonucYonetici.hata(e, "FhszService.get_sabitler_listesi")

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

    def get_donem_puantaj_listesi(self, yil: str | int, donem: str | int) -> SonucYonetici:
        try:
            data = self.get_puantaj_listesi(yil=int(str(yil)), donem=str(donem))
            if not data.basarili:
                return data
            return SonucYonetici.tamam(veri=data.veri or [])
        except Exception as e:
            return SonucYonetici.hata(e, "FhszService.get_donem_puantaj_listesi")

    def sua_bakiye_guncelle(self, yil_str: str) -> SonucYonetici:
        try:
            tum = self._r.get("FHSZ_Puantaj").get_all() or []
            personel_toplam: dict[str, float] = {}
            for r in tum:
                if str(r.get("AitYil", "")).strip() != str(yil_str):
                    continue
                tc = str(r.get("Personelid", "")).strip()
                try:
                    saat = float(str(r.get("FiiliCalismaSaat", 0)).replace(",", "."))
                except (ValueError, TypeError):
                    saat = 0.0
                personel_toplam[tc] = personel_toplam.get(tc, 0.0) + saat

            izin_bilgi = self._r.get("Izin_Bilgi")
            for tc, toplam_saat in personel_toplam.items():
                from core.hesaplamalar import sua_hak_edis_hesapla
                yeni_hak = sua_hak_edis_hesapla(toplam_saat)
                mevcut = izin_bilgi.get_by_id(tc)
                if not mevcut:
                    continue
                try:
                    eski = float(str(mevcut.get("SuaCariYilKazanim", 0)).replace(",", "."))
                except (ValueError, TypeError):
                    eski = -1.0
                if eski != yeni_hak:
                    izin_bilgi.update(tc, {"SuaCariYilKazanim": yeni_hak})
            return SonucYonetici.tamam(veri=len(personel_toplam))
        except Exception as e:
            return SonucYonetici.hata(e, "FhszService.sua_bakiye_guncelle")

    def donem_puantaj_kaydet(self, yil: str | int, donem: str | int, kayitlar: list[dict]) -> SonucYonetici:
        try:
            yil_str = str(yil)
            donem_str = str(donem)
            repo = self._r.get("FHSZ_Puantaj")
            tum = repo.get_all() or []
            for r in tum:
                if str(r.get("AitYil", "")).strip() == yil_str and str(r.get("Donem", "")).strip() == donem_str:
                    pk = [
                        str(r.get("Personelid", "")),
                        str(r.get("AitYil", "")),
                        str(r.get("Donem", "")),
                    ]
                    try:
                        repo.delete(pk)
                    except Exception:
                        pass
            for kayit in kayitlar:
                repo.insert(kayit)
            sonuc = self.sua_bakiye_guncelle(yil_str)
            if not sonuc.basarili:
                return sonuc
            return SonucYonetici.tamam(veri=len(kayitlar))
        except Exception as e:
            return SonucYonetici.hata(e, "FhszService.donem_puantaj_kaydet")

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
