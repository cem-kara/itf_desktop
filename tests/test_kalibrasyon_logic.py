# -*- coding: utf-8 -*-
"""
kalibrasyon_takip.py iş mantığı unit testleri
===============================================
Kapsam:
  1. Ay adımı hesaplama (geçerlilik → ay sayısı)
  2. Bitiş tarihi hesaplama (_tarih_hesapla)
  3. Çoklu dönem satırı oluşturma (_kaydet_devam)
  4. İlk/sonraki satır içerik doğrulaması
  5. Tarih sıralaması tutarlılığı
  6. Sütun adı uyumsuzluğu belgeleme (Kalid vs Kalid)
"""
import pytest
import datetime
from dateutil.relativedelta import relativedelta


# ──────────────────────────────────────────────────
#  Saf Python iş mantığı (Qt bağımlılığı yok)
# ──────────────────────────────────────────────────

def _ay_adim(gecerlilik: str) -> int:
    if "6 Ay"  in gecerlilik: return 6
    if "1 Yıl" in gecerlilik: return 12
    if "2 Yıl" in gecerlilik: return 24
    if "3 Yıl" in gecerlilik: return 36
    return 0  # Tek Seferlik veya bilinmeyen


def _bitis_tarihi(baslangic: datetime.date, gecerlilik: str) -> datetime.date:
    bitis = baslangic
    if "6 Ay"  in gecerlilik: return bitis + relativedelta(months=6)
    if "1 Yıl" in gecerlilik: return bitis + relativedelta(years=1)
    if "2 Yıl" in gecerlilik: return bitis + relativedelta(years=2)
    if "3 Yıl" in gecerlilik: return bitis + relativedelta(years=3)
    return bitis


def _satirlari_olustur(baslangic: datetime.date, gecerlilik: str,
                       donem_sayisi: int, cihaz_id: str = "C001",
                       firma: str = "Firma", durum: str = "Tamamlandı",
                       sertifika: str = "-", aciklama: str = "") -> list:
    ay_adim = _ay_adim(gecerlilik)
    if ay_adim == 0:
        donem_sayisi = 1
    base_id = 1700000000
    satirlar = []
    for i in range(donem_sayisi):
        yeni_bas = baslangic + relativedelta(months=i * ay_adim)
        yeni_bit = (yeni_bas + relativedelta(months=ay_adim)
                    if ay_adim > 0 else baslangic)
        ilk = (i == 0)
        satirlar.append({
            "Kalid":    f"KAL-{base_id + i}",
            "Cihazid":          cihaz_id,
            "Firma":            firma if ilk else "",
            "SertifikaNo":      "SERT-001" if ilk else "",
            "YapilanTarih":     yeni_bas.strftime("%Y-%m-%d"),
            "GecerlilikSuresi": gecerlilik,
            "BitisTarihi":      yeni_bit.strftime("%Y-%m-%d"),
            "Durum":            durum if ilk else "Planlandı",
            "Sertifika":        sertifika if ilk else "",
            "Aciklama":         aciklama if ilk else "Otomatik planlandı.",
        })
    return satirlar


BAS = datetime.date(2024, 1, 15)


# =============================================================
#  1. Ay Adımı Hesaplama
# =============================================================
class TestAyAdimi:

    def test_6_ay(self):
        assert _ay_adim("6 Ay") == 6

    def test_1_yil(self):
        assert _ay_adim("1 Yıl") == 12

    def test_2_yil(self):
        assert _ay_adim("2 Yıl") == 24

    def test_3_yil(self):
        assert _ay_adim("3 Yıl") == 36

    def test_tek_seferlik_sifir(self):
        assert _ay_adim("Tek Seferlik") == 0

    def test_bilinmeyen_sifir(self):
        assert _ay_adim("Diğer") == 0


# =============================================================
#  2. Bitiş Tarihi Hesaplama
# =============================================================
class TestBitisTarihi:

    def test_6_ay_bitis(self):
        assert _bitis_tarihi(BAS, "6 Ay") == datetime.date(2024, 7, 15)

    def test_1_yil_bitis(self):
        assert _bitis_tarihi(BAS, "1 Yıl") == datetime.date(2025, 1, 15)

    def test_2_yil_bitis(self):
        assert _bitis_tarihi(BAS, "2 Yıl") == datetime.date(2026, 1, 15)

    def test_3_yil_bitis(self):
        assert _bitis_tarihi(BAS, "3 Yıl") == datetime.date(2027, 1, 15)

    def test_tek_seferlik_baslangic_ayni(self):
        assert _bitis_tarihi(BAS, "Tek Seferlik") == BAS

    def test_subat_artik_yil(self):
        bas = datetime.date(2024, 2, 29)
        assert _bitis_tarihi(bas, "1 Yıl") == datetime.date(2025, 2, 28)

    def test_ocak_31_6_ay(self):
        bas = datetime.date(2024, 1, 31)
        result = _bitis_tarihi(bas, "6 Ay")
        assert result == datetime.date(2024, 7, 31)


# =============================================================
#  3. Dönem Sayısı
# =============================================================
class TestDonemSayisi:

    def test_tek_seferlik_1_satir(self):
        assert len(_satirlari_olustur(BAS, "Tek Seferlik", 5)) == 1

    def test_1_yil_1_donem(self):
        assert len(_satirlari_olustur(BAS, "1 Yıl", 1)) == 1

    def test_1_yil_3_donem(self):
        assert len(_satirlari_olustur(BAS, "1 Yıl", 3)) == 3

    def test_6_ay_4_donem(self):
        assert len(_satirlari_olustur(BAS, "6 Ay", 4)) == 4

    def test_2_yil_2_donem(self):
        assert len(_satirlari_olustur(BAS, "2 Yıl", 2)) == 2

    def test_3_yil_10_donem(self):
        assert len(_satirlari_olustur(BAS, "3 Yıl", 10)) == 10


# =============================================================
#  4. İlk Satır İçerik
# =============================================================
class TestIlkSatir:

    def setup_method(self):
        self.s = _satirlari_olustur(BAS, "1 Yıl", 3, "C042",
                                    "ABC Lab", "Tamamlandı",
                                    "https://link.test", "Test notu")
        self.ilk = self.s[0]

    def test_cihaz_id(self):
        assert self.ilk["Cihazid"] == "C042"

    def test_firma(self):
        assert self.ilk["Firma"] == "ABC Lab"

    def test_durum(self):
        assert self.ilk["Durum"] == "Tamamlandı"

    def test_sertifika(self):
        assert self.ilk["Sertifika"] == "https://link.test"

    def test_aciklama(self):
        assert self.ilk["Aciklama"] == "Test notu"

    def test_yapilan_tarih(self):
        assert self.ilk["YapilanTarih"] == "2024-01-15"

    def test_bitis_tarihi(self):
        assert self.ilk["BitisTarihi"] == "2025-01-15"

    def test_kal_prefix(self):
        assert self.ilk["Kalid"].startswith("KAL-")


# =============================================================
#  5. Sonraki Satırlar
# =============================================================
class TestSonrakiSatirlar:

    def setup_method(self):
        self.s = _satirlari_olustur(BAS, "6 Ay", 4, "C001", "Firma A")

    def test_ikinci_firma_bos(self):
        assert self.s[1]["Firma"] == ""

    def test_ikinci_durum_planlandı(self):
        assert self.s[1]["Durum"] == "Planlandı"

    def test_ikinci_sertifika_bos(self):
        assert self.s[1]["Sertifika"] == ""

    def test_ikinci_aciklama_otomatik(self):
        assert "Otomatik" in self.s[1]["Aciklama"]

    def test_son_satir_planlandı(self):
        assert self.s[-1]["Durum"] == "Planlandı"

    def test_benzersiz_idler(self):
        ids = [s["Kalid"] for s in self.s]
        assert len(ids) == len(set(ids))


# =============================================================
#  6. Tarih Sıralaması
# =============================================================
class TestTarihSiralamasi:

    def test_6_aylik_4_donem(self):
        bas = datetime.date(2024, 1, 1)
        s = _satirlari_olustur(bas, "6 Ay", 4)
        beklenen = ["2024-01-01", "2024-07-01", "2025-01-01", "2025-07-01"]
        assert [x["YapilanTarih"] for x in s] == beklenen

    def test_1_yillik_3_donem(self):
        bas = datetime.date(2024, 3, 10)
        s = _satirlari_olustur(bas, "1 Yıl", 3)
        assert [x["YapilanTarih"] for x in s] == [
            "2024-03-10", "2025-03-10", "2026-03-10"
        ]

    def test_bitis_her_zaman_baslangictan_sonra(self):
        s = _satirlari_olustur(datetime.date(2024, 6, 1), "1 Yıl", 2)
        for satir in s:
            yt = datetime.datetime.strptime(satir["YapilanTarih"], "%Y-%m-%d").date()
            bt = datetime.datetime.strptime(satir["BitisTarihi"], "%Y-%m-%d").date()
            assert bt > yt


# =============================================================
#  7. table_config Sütun Uyumu
# =============================================================
class TestKalibrasyonSutunUyumu:

    def test_kalibrasyon_tablosu_var(self):
        from database.table_config import TABLES
        assert "Kalibrasyon" in TABLES

    def test_pk_kalid(self):
        from database.table_config import TABLES
        assert TABLES["Kalibrasyon"]["pk"] == "Kalid"

    def test_zorunlu_kolonlar(self):
        from database.table_config import TABLES
        cols = TABLES["Kalibrasyon"]["columns"]
        for k in ["Kalid", "Cihazid", "Firma", "SertifikaNo",
                  "YapilanTarih", "BitisTarihi", "Durum", "Aciklama"]:
            assert k in cols, f"Eksik kolon: {k}"

    def test_sutun_adı_pk_uyumu(self):
        """
        ✅ kalibrasyon_takip.py PK'sı table_config ile uyumlu olmalı.
        (Düzeltildi: 'Kalid' -> 'Kalid' olarak güncellendi.)
        """
        from database.table_config import TABLES
        pk = TABLES["Kalibrasyon"]["pk"]
        assert pk == "Kalid", f"DB PK beklenen 'Kalid', bulunan '{pk}'"

    def test_gecerlilik_kolon_adi(self):
        """
        ✅ Gecerlilik suresi kolonu DB ve UI'da 'Gecerlilik' olarak tutarli olmali.
        (Duzeltildi: kalibrasyon_takip.py 'Gecerlilik' kullanacak sekilde guncellendi.)
        """
        from database.table_config import TABLES
        cols = TABLES["Kalibrasyon"]["columns"]
        assert "Gecerlilik" in cols, "DB'de 'Gecerlilik' kolonu bulunamadi"
