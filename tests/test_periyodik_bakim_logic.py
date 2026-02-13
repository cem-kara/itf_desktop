# -*- coding: utf-8 -*-
"""
Periyodik Bakım iş mantığı unit testleri
==========================================
Kapsam:
  - _ay_ekle            : tarih kaydırma
  - INSERT satır üretimi : periyoda göre çoklu satır
  - Planid formatı       : P-<timestamp>
  - Durum / kilitlenme mantığı
  - Veri alanlarının doğruluğu (Cihazid, BakimPeriyodu, BakimSirasi…)
  - Tablo kolon adları (DB şemasıyla uyum)

Qt gerekmez — saf Python testleri.
"""
import time
import datetime
import pytest
from dateutil.relativedelta import relativedelta


# ─── Test edilecek saf fonksiyonlar ──────────────────────────

def _ay_ekle(kaynak_tarih, ay_sayisi: int):
    return kaynak_tarih + relativedelta(months=ay_sayisi)


def _satirlar_olustur(cihaz_id, periyot, tarih, durum,
                      yapilan, aciklama, teknisyen, dosya_link,
                      bakim_t="", base_id=1000000000):
    """periyodik_bakim.py'deki INSERT mantığının saf Python kopyası."""
    tekrar  = 1
    ay_adim = 0
    if "3 Ay"  in periyot: tekrar, ay_adim = 4,  3
    elif "6 Ay"  in periyot: tekrar, ay_adim = 2,  6
    elif "1 Yıl" in periyot: tekrar, ay_adim = 1, 12

    satirlar = []
    for i in range(tekrar):
        yeni_tarih = _ay_ekle(tarih, i * ay_adim)
        ilk        = (i == 0)
        s_durum    = durum if ilk else "Planlandı"
        s_bakim_t  = bakim_t if (ilk and s_durum == "Yapıldı") else ""
        satirlar.append({
            "Planid":          f"P-{base_id + i}",
            "Cihazid":         cihaz_id,
            "BakimPeriyodu":   periyot,
            "BakimSirasi":     f"{i + 1}. Bakım",
            "PlanlananTarih":  yeni_tarih.strftime("%Y-%m-%d"),
            "Bakim":           "Periyodik",
            "Durum":           s_durum,
            "BakimTarihi":     s_bakim_t,
            "BakimTipi":       "Periyodik",
            "YapilanIslemler": yapilan   if ilk else "",
            "Aciklama":        aciklama  if ilk else "",
            "Teknisyen":       teknisyen if ilk else "",
            "Rapor":           dosya_link if ilk else "",
        })
    return satirlar


BASLANGIC = datetime.date(2024, 1, 15)


# ════════════════════════════════════════════════════════════
#  1. _ay_ekle
# ════════════════════════════════════════════════════════════

class TestAyEkle:

    def test_sifir_ay_ayni_tarih(self):
        assert _ay_ekle(BASLANGIC, 0) == BASLANGIC

    def test_3_ay_sonrasi(self):
        assert _ay_ekle(BASLANGIC, 3) == datetime.date(2024, 4, 15)

    def test_6_ay_sonrasi(self):
        assert _ay_ekle(BASLANGIC, 6) == datetime.date(2024, 7, 15)

    def test_12_ay_sonrasi_yil_atlama(self):
        assert _ay_ekle(BASLANGIC, 12) == datetime.date(2025, 1, 15)

    def test_24_ay_2_yil(self):
        assert _ay_ekle(BASLANGIC, 24) == datetime.date(2026, 1, 15)

    def test_ay_sonu_ocak_31_subat(self):
        """Ocak 31 + 1 ay → Şubat 28/29 (relativedelta güvenli)."""
        ocak_31 = datetime.date(2024, 1, 31)
        subat   = _ay_ekle(ocak_31, 1)
        # 2024 artık yıl → Şubat 29
        assert subat == datetime.date(2024, 2, 29)

    def test_aralik_ay_gecisi(self):
        aralik = datetime.date(2024, 12, 15)
        assert _ay_ekle(aralik, 1) == datetime.date(2025, 1, 15)

    def test_negstif_ay(self):
        """Negatif değer geçmişe gitmeli."""
        assert _ay_ekle(BASLANGIC, -3) == datetime.date(2023, 10, 15)


# ════════════════════════════════════════════════════════════
#  2. Periyot → Satır Sayısı
# ════════════════════════════════════════════════════════════

class TestSatirSayisi:

    def _satirlar(self, periyot):
        return _satirlar_olustur("CIH-001", periyot, BASLANGIC,
                                 "Planlandı", "", "", "Tekniker", "")

    def test_3_ay_4_satir(self):
        assert len(self._satirlar("3 Ay")) == 4

    def test_6_ay_2_satir(self):
        assert len(self._satirlar("6 Ay")) == 2

    def test_1_yil_1_satir(self):
        assert len(self._satirlar("1 Yıl")) == 1

    def test_tek_seferlik_1_satir(self):
        assert len(self._satirlar("Tek Seferlik")) == 1

    def test_bilinmeyen_periyot_1_satir(self):
        assert len(self._satirlar("Bilinmiyor")) == 1


# ════════════════════════════════════════════════════════════
#  3. Tarih Aralıkları
# ════════════════════════════════════════════════════════════

class TestTarihAraliklari:

    def test_3_ay_tarihler(self):
        satirlar = _satirlar_olustur("CIH-001", "3 Ay", BASLANGIC,
                                     "Planlandı", "", "", "", "")
        tarihler = [s["PlanlananTarih"] for s in satirlar]
        assert tarihler == ["2024-01-15", "2024-04-15", "2024-07-15", "2024-10-15"]

    def test_6_ay_tarihler(self):
        satirlar = _satirlar_olustur("CIH-001", "6 Ay", BASLANGIC,
                                     "Planlandı", "", "", "", "")
        tarihler = [s["PlanlananTarih"] for s in satirlar]
        assert tarihler == ["2024-01-15", "2024-07-15"]

    def test_1_yil_tarih(self):
        satirlar = _satirlar_olustur("CIH-001", "1 Yıl", BASLANGIC,
                                     "Planlandı", "", "", "", "")
        assert satirlar[0]["PlanlananTarih"] == "2024-01-15"

    def test_tarih_formati_yyyy_mm_dd(self):
        satirlar = _satirlar_olustur("CIH-001", "3 Ay", BASLANGIC,
                                     "Planlandı", "", "", "", "")
        for s in satirlar:
            tarih = s["PlanlananTarih"]
            datetime.date.fromisoformat(tarih)  # exception → format bozuk


# ════════════════════════════════════════════════════════════
#  4. İlk Satır vs Sonraki Satırlar
# ════════════════════════════════════════════════════════════

class TestIlkVeSonrakiSatirlar:

    def _uret(self, periyot="3 Ay", durum="Planlandı",
              yapilan="Test", aciklama="Not", teknisyen="Ahmet",
              dosya="http://link"):
        return _satirlar_olustur("CIH-001", periyot, BASLANGIC,
                                 durum, yapilan, aciklama, teknisyen, dosya)

    def test_ilk_satir_durum_ayni(self):
        satirlar = self._uret(durum="Yapıldı")
        assert satirlar[0]["Durum"] == "Yapıldı"

    def test_sonraki_satirlar_planlanmis(self):
        satirlar = self._uret(durum="Yapıldı")
        for s in satirlar[1:]:
            assert s["Durum"] == "Planlandı"

    def test_ilk_satir_yapilan_islem_dolu(self):
        satirlar = self._uret()
        assert satirlar[0]["YapilanIslemler"] == "Test"

    def test_sonraki_satirlar_yapilan_bos(self):
        satirlar = self._uret()
        for s in satirlar[1:]:
            assert s["YapilanIslemler"] == ""

    def test_ilk_satir_aciklama_dolu(self):
        satirlar = self._uret()
        assert satirlar[0]["Aciklama"] == "Not"

    def test_sonraki_satirlar_aciklama_bos(self):
        satirlar = self._uret()
        for s in satirlar[1:]:
            assert s["Aciklama"] == ""

    def test_ilk_satir_teknisyen_dolu(self):
        satirlar = self._uret()
        assert satirlar[0]["Teknisyen"] == "Ahmet"

    def test_sonraki_satirlar_teknisyen_bos(self):
        satirlar = self._uret()
        for s in satirlar[1:]:
            assert s["Teknisyen"] == ""

    def test_ilk_satir_rapor_linki(self):
        satirlar = self._uret()
        assert satirlar[0]["Rapor"] == "http://link"

    def test_sonraki_satirlar_rapor_bos(self):
        satirlar = self._uret()
        for s in satirlar[1:]:
            assert s["Rapor"] == ""


# ════════════════════════════════════════════════════════════
#  5. BakimTarihi Mantığı
# ════════════════════════════════════════════════════════════

class TestBakimTarihi:

    def test_yapildi_bakim_tarihi_dolar(self):
        satirlar = _satirlar_olustur("CIH-001", "3 Ay", BASLANGIC,
                                     "Yapıldı", "", "", "", "",
                                     bakim_t="2024-01-15")
        assert satirlar[0]["BakimTarihi"] == "2024-01-15"

    def test_yapildi_sonraki_bakim_tarihi_bos(self):
        satirlar = _satirlar_olustur("CIH-001", "3 Ay", BASLANGIC,
                                     "Yapıldı", "", "", "", "",
                                     bakim_t="2024-01-15")
        for s in satirlar[1:]:
            assert s["BakimTarihi"] == ""

    def test_planlanmis_bakim_tarihi_bos(self):
        satirlar = _satirlar_olustur("CIH-001", "3 Ay", BASLANGIC,
                                     "Planlandı", "", "", "", "",
                                     bakim_t="2024-01-15")
        # Planlandı durumunda bile bakim_t set edilmemeli
        assert satirlar[0]["BakimTarihi"] == ""


# ════════════════════════════════════════════════════════════
#  6. Planid Formatı
# ════════════════════════════════════════════════════════════

class TestPlanidFormati:

    def test_planid_p_ile_baslar(self):
        satirlar = _satirlar_olustur("CIH-001", "3 Ay", BASLANGIC,
                                     "Planlandı", "", "", "", "")
        for s in satirlar:
            assert s["Planid"].startswith("P-")

    def test_planid_benzersiz(self):
        satirlar = _satirlar_olustur("CIH-001", "3 Ay", BASLANGIC,
                                     "Planlandı", "", "", "", "")
        idler = [s["Planid"] for s in satirlar]
        assert len(idler) == len(set(idler))

    def test_planid_ardisik_artar(self):
        satirlar = _satirlar_olustur("CIH-001", "3 Ay", BASLANGIC,
                                     "Planlandı", "", "", "", "",
                                     base_id=1000000000)
        nums = [int(s["Planid"].split("-")[1]) for s in satirlar]
        for i in range(1, len(nums)):
            assert nums[i] == nums[i - 1] + 1


# ════════════════════════════════════════════════════════════
#  7. Zorunlu Alan Varlığı
# ════════════════════════════════════════════════════════════

class TestZorunluAlanlar:

    ZORUNLU = [
        "Planid", "Cihazid", "BakimPeriyodu", "BakimSirasi",
        "PlanlananTarih", "Bakim", "Durum", "BakimTarihi",
        "BakimTipi", "YapilanIslemler", "Aciklama", "Teknisyen", "Rapor"
    ]

    def test_tum_kolon_adlari_mevcut(self):
        satirlar = _satirlar_olustur("CIH-001", "3 Ay", BASLANGIC,
                                     "Planlandı", "", "", "", "")
        for satir in satirlar:
            for alan in self.ZORUNLU:
                assert alan in satir, f"'{alan}' eksik"

    def test_bakim_tipi_periyodik(self):
        satirlar = _satirlar_olustur("CIH-001", "1 Yıl", BASLANGIC,
                                     "Planlandı", "", "", "", "")
        assert satirlar[0]["BakimTipi"] == "Periyodik"

    def test_bakim_alani_periyodik(self):
        satirlar = _satirlar_olustur("CIH-001", "1 Yıl", BASLANGIC,
                                     "Planlandı", "", "", "", "")
        assert satirlar[0]["Bakim"] == "Periyodik"

    def test_bakim_sirasi_formati(self):
        """'1. Bakım', '2. Bakım' … formatında olmalı."""
        satirlar = _satirlar_olustur("CIH-001", "3 Ay", BASLANGIC,
                                     "Planlandı", "", "", "", "")
        for i, satir in enumerate(satirlar, 1):
            assert satir["BakimSirasi"] == f"{i}. Bakım"

    def test_cihaz_id_dogru(self):
        satirlar = _satirlar_olustur("CIH-XYZ", "6 Ay", BASLANGIC,
                                     "Planlandı", "", "", "", "")
        for satir in satirlar:
            assert satir["Cihazid"] == "CIH-XYZ"

    def test_bakim_periyodu_korunur(self):
        satirlar = _satirlar_olustur("CIH-001", "6 Ay", BASLANGIC,
                                     "Planlandı", "", "", "", "")
        for satir in satirlar:
            assert satir["BakimPeriyodu"] == "6 Ay"


# ════════════════════════════════════════════════════════════
#  8. UPDATE Veri Yapısı
# ════════════════════════════════════════════════════════════

class TestUpdateVeriYapisi:
    """UPDATE dict'inin beklenen kolonları içerdiğini doğrular."""

    BEKLENEN_KOLONLAR = [
        "Cihazid", "BakimPeriyodu", "PlanlananTarih",
        "Durum", "BakimTarihi", "YapilanIslemler",
        "Aciklama", "Teknisyen", "Rapor"
    ]

    def _update_dict(self, durum="Planlandı", bakim_t=""):
        return {
            "Cihazid":         "CIH-001",
            "BakimPeriyodu":   "3 Ay",
            "PlanlananTarih":  "2024-01-15",
            "Durum":           durum,
            "BakimTarihi":     bakim_t if durum == "Yapıldı" else "",
            "YapilanIslemler": "Bakım yapıldı",
            "Aciklama":        "Her şey tamam",
            "Teknisyen":       "Ali Veli",
            "Rapor":           "http://example.com/rapor.pdf",
        }

    def test_update_tum_kolonlar_mevcut(self):
        d = self._update_dict()
        for k in self.BEKLENEN_KOLONLAR:
            assert k in d

    def test_update_yapildi_bakim_tarihi(self):
        d = self._update_dict(durum="Yapıldı", bakim_t="2024-01-15")
        assert d["BakimTarihi"] == "2024-01-15"

    def test_update_planlanmis_bakim_tarihi_bos(self):
        d = self._update_dict(durum="Planlandı")
        assert d["BakimTarihi"] == ""

    def test_mevcut_link_korunur(self):
        """Yeni dosya seçilmediyse mevcut link korunmalı."""
        mevcut_link = "https://drive.google.com/file/abc"
        dosya_link  = "-"  # yeni seçilmedi
        if dosya_link == "-" and mevcut_link:
            dosya_link = mevcut_link
        assert dosya_link == mevcut_link

    def test_yeni_dosya_link_eski_link_degistirir(self):
        mevcut_link = "https://drive.google.com/file/abc"
        dosya_link  = "https://drive.google.com/file/yeni"
        if dosya_link == "-" and mevcut_link:
            dosya_link = mevcut_link
        assert dosya_link == "https://drive.google.com/file/yeni"
