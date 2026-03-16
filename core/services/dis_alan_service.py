# core/services/dis_alan_service.py
"""
DisAlanService — Radyoloji dışı alanlarda (anjio, ERCP, ESWL vb.)
                 çalışan personelin tutanaklı şua süresi kayıtları
                 ve aylık izin hakkı hesaplama servisi.

Sorumluluklar:
- Tutanak bazlı çalışma kaydı ekleme / sorgulama / silme
- Aylık toplam saat hesaplama
- İzin günü hakkı hesaplama (eşik tablosuna göre)
- Dönem özeti oluşturma ve RKS onay akışı
"""
from typing import Optional
from core.logger import logger
from database.repository_registry import RepositoryRegistry


# ─────────────────────────────────────────────────────────────
#  İzin Hakkı Eşik Tablosu
#  Yıllık kümülatif şua süresi (saat) → kazanılan izin günü
#  Kaynak: Radyoloji biriminin mevzuat / protokolüne göre ayarlayın.
# ─────────────────────────────────────────────────────────────
def _izin_gunu_hesapla(toplam_saat: float) -> float:
    """
    Sağlık İzni tablosu (0 < saat <= 50 -> 1 gün ... 1451-1500 -> 30 gün).
    50 saatlik dilimlerle artar, 30 günde tavanlanır.
    """
    try:
        saat = float(toplam_saat)
    except (ValueError, TypeError):
        return 0.0

    if saat <= 0:
        return 0.0
    gun = int((saat + 50 - 1) // 50)
    return float(min(30, max(1, gun)))


class DisAlanService:
    """Dış alan (anjio/ERCP/ESWL vb.) tutanaklı çalışma servisi."""

    def __init__(self, registry: RepositoryRegistry):
        if not registry:
            raise ValueError("RepositoryRegistry boş olamaz")
        self._r = registry

    # ─────────────────────────────────────────────────────────
    #  Personel
    # ─────────────────────────────────────────────────────────

    def get_dis_alan_personeli(self) -> list[dict]:
        """
        Dis_Alan_Calisma tablosundan benzersiz kişi (TCKimlik, AdSoyad) listesi döndürür.
        """
        try:
            rows = self._r.get("Dis_Alan_Calisma").get_all() or []
            unique = {}
            for r in rows:
                tc = str(r.get("TCKimlik", "")).strip()
                ad = str(r.get("AdSoyad", "")).strip()
                if tc and tc not in unique:
                    unique[tc] = {"TCKimlik": tc, "AdSoyad": ad}
            return list(unique.values())
        except Exception as e:
            logger.error(f"Dış alan personel listesi hatası: {e}")
            return []

    # ─────────────────────────────────────────────────────────
    #  Çalışma Kaydı  (Dis_Alan_Calisma)
    # ─────────────────────────────────────────────────────────

    def get_calisma_listesi(
        self,
        tckimlik: Optional[str] = None,
        donem_ay: Optional[int] = None,
        donem_yil: Optional[int] = None,
    ) -> list[dict]:
        """Filtrelenmiş çalışma kayıtlarını döndürür."""
        try:
            rows = self._r.get("Dis_Alan_Calisma").get_all() or []

            if tckimlik is not None:
                rows = [r for r in rows if str(r.get("TCKimlik", "")) == str(tckimlik)]
            if donem_ay is not None:
                rows = [r for r in rows if str(r.get("DonemAy", "")) == str(donem_ay)]
            if donem_yil is not None:
                rows = [r for r in rows if str(r.get("DonemYil", "")) == str(donem_yil)]

            return rows
        except Exception as e:
            logger.error(f"Dış alan çalışma listesi hatası: {e}")
            return []

    def calisma_kaydet(self, veri: dict) -> bool:
        """
        Yeni tutanak kaydı ekler.
        PK: (TCKimlik, DonemAy, DonemYil, TutanakNo)
        Aynı tutanak numarası aynı dönemde tekrar girilirse hata döner.
        """
        try:
            repo = self._r.get("Dis_Alan_Calisma")
            pk = (
                str(veri.get("TCKimlik", "")),
                str(veri.get("DonemAy", "")),
                str(veri.get("DonemYil", "")),
                str(veri.get("TutanakNo", "")),
            )
            if repo.get_by_pk(pk):
                logger.warning(f"Tutanak zaten kayıtlı: {pk}")
                return False

            repo.insert(veri)
            logger.info(
                f"Dış alan kaydı eklendi | "
                f"{veri.get('AdSoyad')} | "
                f"{veri.get('DonemAy')}/{veri.get('DonemYil')} | "
                f"{veri.get('IslemTipi')} | "
                f"{veri.get('HesaplananSaat'):.2f} saat"
            )
            return True
        except Exception as e:
            logger.error(f"Dış alan kayıt hatası: {e}")
            return False

    def calisma_sil(
        self,
        tckimlik: str,
        donem_ay: int,
        donem_yil: int,
        tutanak_no: str,
    ) -> bool:
        """Tutanak kaydını siler. Onaylanmış dönem özeti varsa silmeyi engeller."""
        try:
            # Önce bu döneme ait onaylanmış özet var mı kontrol et
            ozet_pk = (str(tckimlik), str(donem_ay), str(donem_yil))
            ozet = self._r.get("Dis_Alan_Izin_Ozet").get_by_pk(ozet_pk)
            if ozet and int(ozet.get("RksOnay", 0)) == 1:
                logger.warning(
                    f"Onaylanmış dönem kaydı silinemez: "
                    f"{tckimlik} {donem_ay}/{donem_yil}"
                )
                return False

            pk = (str(tckimlik), str(donem_ay), str(donem_yil), str(tutanak_no))
            self._r.get("Dis_Alan_Calisma").delete(pk)
            logger.info(f"Dış alan kaydı silindi: {pk}")
            return True
        except Exception as e:
            logger.error(f"Dış alan silme hatası: {e}")
            return False

    # ─────────────────────────────────────────────────────────
    #  Hesaplama
    # ─────────────────────────────────────────────────────────

    def aylik_toplam_saat(
        self,
        tckimlik: str,
        donem_ay: int,
        donem_yil: int,
    ) -> float:
        """Personelin ilgili aydaki tüm tutanakların toplam saatini döndürür."""
        kayitlar = self.get_calisma_listesi(
            tckimlik=tckimlik,
            donem_ay=donem_ay,
            donem_yil=donem_yil,
        )
        return round(sum(float(k.get("HesaplananSaat", 0)) for k in kayitlar), 2)

    def yillik_toplam_saat(self, tckimlik: str, yil: int) -> float:
        """Personelin o yılki tüm ayların toplam saatini döndürür."""
        kayitlar = self.get_calisma_listesi(
            tckimlik=tckimlik,
            donem_yil=yil,
        )
        return round(sum(float(k.get("HesaplananSaat", 0)) for k in kayitlar), 2)

    def izin_hakki_hesapla(self, tckimlik: str, yil: int) -> float:
        """
        Yıllık kümülatif şua süresinden izin günü hakkını hesaplar.
        Dönem özetine yazmaz — sadece hesaplar.
        """
        toplam = self.yillik_toplam_saat(tckimlik, yil)
        return _izin_gunu_hesapla(toplam)

    # ─────────────────────────────────────────────────────────
    #  Dönem Özeti  (Dis_Alan_Izin_Ozet)
    # ─────────────────────────────────────────────────────────

    def get_ozet(
        self,
        tckimlik: str,
        donem_ay: int,
        donem_yil: int,
    ) -> Optional[dict]:
        """Dönem özetini döndürür. Yoksa None."""
        try:
            pk = (str(tckimlik), str(donem_ay), str(donem_yil))
            return self._r.get("Dis_Alan_Izin_Ozet").get_by_pk(pk)
        except Exception as e:
            logger.error(f"Dönem özeti okuma hatası: {e}")
            return None

    def ozet_hesapla_ve_kaydet(
        self,
        tckimlik: str,
        ad_soyad: str,
        donem_ay: int,
        donem_yil: int,
        kaydeden: Optional[str] = None,
    ) -> Optional[dict]:
        """
        İlgili aydaki tüm tutanakları toplayıp dönem özetini hesaplar
        ve Dis_Alan_Izin_Ozet tablosuna yazar/günceller.

        Onaylanmış dönem yeniden hesaplanamaz — önce onay kaldırılmalı.

        Returns:
            Oluşturulan/güncellenen özet dict'i veya None (hata).
        """
        from datetime import datetime

        try:
            repo_ozet = self._r.get("Dis_Alan_Izin_Ozet")
            pk = (str(tckimlik), str(donem_ay), str(donem_yil))
            mevcut = repo_ozet.get_by_pk(pk)

            if mevcut and int(mevcut.get("RksOnay", 0)) == 1:
                logger.warning(
                    f"Onaylanmış dönem yeniden hesaplanamaz: "
                    f"{tckimlik} {donem_ay}/{donem_yil}"
                )
                return None

            toplam_saat = self.aylik_toplam_saat(tckimlik, donem_ay, donem_yil)

            # Yıllık kümülatif: önceki aylar + bu ay
            onceki_toplam = 0.0
            for ay in range(1, donem_ay):
                onceki_toplam += self.aylik_toplam_saat(tckimlik, ay, donem_yil)
            yillik_kumülatif = onceki_toplam + toplam_saat

            izin_gun = _izin_gunu_hesapla(yillik_kumülatif)

            ozet = {
                "TCKimlik":   str(tckimlik),
                "AdSoyad":    ad_soyad,
                "DonemAy":    donem_ay,
                "DonemYil":   donem_yil,
                "ToplamSaat":       toplam_saat,
                "IzinGunHakki":     izin_gun,
                "HesaplamaTarihi":  datetime.now().strftime("%Y-%m-%d"),
                "RksOnay":          0,
                "Notlar":           f"Yıllık kümülatif: {yillik_kumülatif:.2f} saat",
            }

            if mevcut:
                repo_ozet.update(pk, ozet)
                logger.info(f"Dönem özeti güncellendi: {pk} → {toplam_saat:.2f} saat / {izin_gun} gün")
            else:
                repo_ozet.insert(ozet)
                logger.info(f"Dönem özeti oluşturuldu: {pk} → {toplam_saat:.2f} saat / {izin_gun} gün")

            return ozet

        except Exception as e:
            logger.error(f"Dönem özeti hesaplama hatası: {e}")
            return None

    def ozet_onayla(
        self,
        tckimlik: str,
        donem_ay: int,
        donem_yil: int,
    ) -> bool:
        """RKS onayını verir. Onaylı kayıt artık değiştirilemez ve silinemez."""
        try:
            repo = self._r.get("Dis_Alan_Izin_Ozet")
            pk = (str(tckimlik), str(donem_ay), str(donem_yil))
            ozet = repo.get_by_pk(pk)
            if not ozet:
                logger.warning(f"Onaylanacak özet bulunamadı: {pk}")
                return False

            repo.update(pk, {"RksOnay": 1})
            logger.info(f"Dönem özeti onaylandı: {pk}")
            return True
        except Exception as e:
            logger.error(f"Dönem onay hatası: {e}")
            return False

    def get_yillik_ozet_listesi(
        self,
        yil: int,
        sadece_onaysiz: bool = False,
    ) -> list[dict]:
        """
        Tüm personelin yıllık özetlerini döndürür.
        sadece_onaysiz=True → RksOnay=0 olanları filtreler (RKS takip ekranı için).
        """
        try:
            rows = self._r.get("Dis_Alan_Izin_Ozet").get_all() or []
            rows = [r for r in rows if str(r.get("DonemYil", "")) == str(yil)]
            if sadece_onaysiz:
                rows = [r for r in rows if int(r.get("RksOnay", 0)) == 0]
            return rows
        except Exception as e:
            logger.error(f"Yıllık özet listesi hatası: {e}")
            return []
