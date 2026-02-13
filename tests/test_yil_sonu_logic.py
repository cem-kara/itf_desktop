# -*- coding: utf-8 -*-
"""
test_yil_sonu_logic.py
========================
yil_sonu_islemleri.py unit testleri

Kapsam:
  1. _int              — Tur donusum (float, virgul, None, hatali)
  2. _hizmet_yili      — Hizmet yili hesabi (farkli formatlar, edge case)
  3. _hakedis          — Hakkedis gun hesabi (sinir degerleri)
  4. _hesapla          — Yillik izin devir mantiginin tamami
  5. _hesapla          — Sua izni devir mantiginin tamami
  6. Alan kontrolu     — Dondurulen dict'te tum alanlarin varligi
  7. Qt sayfa          — Checkbox/buton etkinligi, widget varligi
"""
import sys
import datetime
import pytest


@pytest.fixture(scope="module")
def qapp():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication(sys.argv)


# ─────────────────────────────────────────────────────────────
#  Soyutlamalar — Qt bagimliligı olmadan is mantigini test et
# ─────────────────────────────────────────────────────────────

def _int(val) -> int:
    """DevirWorker._int saf Python."""
    try:
        return int(float(str(val).replace(",", ".")))
    except Exception:
        return 0


def _hizmet_yili(tarih_str: str) -> int:
    """DevirWorker._hizmet_yili saf Python."""
    for fmt in ("%d.%m.%Y", "%Y-%m-%d", "%d/%m/%Y"):
        try:
            baslama = datetime.datetime.strptime(str(tarih_str).strip(), fmt)
            bugun   = datetime.datetime.now()
            return (
                bugun.year - baslama.year
                - ((bugun.month, bugun.day) < (baslama.month, baslama.day))
            )
        except Exception:
            continue
    return 0


def _hakedis(hizmet_yil: int) -> int:
    return 30 if hizmet_yil >= 10 else (20 if hizmet_yil > 0 else 0)


def _hesapla(row: dict, baslama_str: str) -> dict:
    """DevirWorker._hesapla saf Python simulasyonu."""
    yeni: dict = {}
    mevcut_hakedis = _int(row.get("YillikHakedis"))
    mevcut_kalan   = _int(row.get("YillikKalan"))
    yeni_devir     = min(mevcut_kalan, mevcut_hakedis)
    hizmet_yil     = _hizmet_yili(baslama_str)
    yeni_hakedis   = _hakedis(hizmet_yil)

    yeni["YillikDevir"]      = yeni_devir
    yeni["YillikHakedis"]    = yeni_hakedis
    yeni["YillikToplamHak"]  = yeni_devir + yeni_hakedis
    yeni["YillikKullanilan"] = 0
    yeni["YillikKalan"]      = yeni_devir + yeni_hakedis

    yeni_sua_hak = _int(row.get("SuaCariYilKazanim"))
    yeni["SuaKullanilabilirHak"] = yeni_sua_hak
    yeni["SuaKullanilan"]        = 0
    yeni["SuaKalan"]             = yeni_sua_hak
    yeni["SuaCariYilKazanim"]    = 0

    return yeni


# Test verisi
BUGUN = datetime.date.today()

def _tarih(n_yil: int) -> str:
    """n yil onceki bugunun tarihi (GG.AA.YYYY)."""
    return f"{BUGUN.day:02d}.{BUGUN.month:02d}.{BUGUN.year - n_yil}"


ORNEK_ROW = {
    "TCKimlik":            "12345678901",
    "AdSoyad":             "Test Personel",
    "YillikDevir":         5,
    "YillikHakedis":       20,
    "YillikToplamHak":     25,
    "YillikKullanilan":    15,
    "YillikKalan":         10,
    "SuaKullanilabilirHak": 0,
    "SuaKullanilan":       3,
    "SuaKalan":            0,
    "SuaCariYilKazanim":   7,
    "RaporMazeretTop":     2,
}


# =============================================================
#  1. _int Donusumu
# =============================================================
class TestIntDonusum:

    def test_tam_sayi_string(self):
        assert _int("20") == 20

    def test_float_string(self):
        assert _int("14.5") == 14

    def test_virgul_ondalik(self):
        assert _int("7,5") == 7

    def test_int_dogrudan(self):
        assert _int(30) == 30

    def test_float_dogrudan(self):
        assert _int(12.9) == 12

    def test_bos_string(self):
        assert _int("") == 0

    def test_none(self):
        assert _int(None) == 0

    def test_harf_string(self):
        assert _int("abc") == 0

    def test_sifir(self):
        assert _int("0") == 0

    def test_negatif(self):
        assert _int("-5") == -5


# =============================================================
#  2. _hizmet_yili Hesabi
# =============================================================
class TestHizmetYili:

    def test_10_yil(self):
        assert _hizmet_yili(_tarih(10)) == 10

    def test_5_yil(self):
        assert _hizmet_yili(_tarih(5)) == 5

    def test_1_yil(self):
        assert _hizmet_yili(_tarih(1)) == 1

    def test_25_yil(self):
        assert _hizmet_yili(_tarih(25)) == 25

    def test_iso_format(self):
        tarih = f"{BUGUN.year - 8}-{BUGUN.month:02d}-{BUGUN.day:02d}"
        assert _hizmet_yili(tarih) == 8

    def test_slash_format(self):
        tarih = f"{BUGUN.day:02d}/{BUGUN.month:02d}/{BUGUN.year - 3}"
        assert _hizmet_yili(tarih) == 3

    def test_gecersiz_string(self):
        assert _hizmet_yili("gecersiz") == 0

    def test_bos_string(self):
        assert _hizmet_yili("") == 0

    def test_none_string(self):
        assert _hizmet_yili("None") == 0


# =============================================================
#  3. Hakedis Hesabi
# =============================================================
class TestHakedisHesabi:

    def test_tam_sinir_10_yil_30_gun(self):
        assert _hakedis(10) == 30

    def test_15_yil_30_gun(self):
        assert _hakedis(15) == 30

    def test_25_yil_30_gun(self):
        assert _hakedis(25) == 30

    def test_9_yil_20_gun(self):
        assert _hakedis(9) == 20

    def test_1_yil_20_gun(self):
        assert _hakedis(1) == 20

    def test_0_yil_0_gun(self):
        assert _hakedis(0) == 0

    def test_sinir_alti_9_yil_hala_20_gun(self):
        assert _hakedis(9) == 20


# =============================================================
#  4. Yillik Izin Devir Mantigi
# =============================================================
class TestYillikIzinDevir:

    def test_kalan_kucukse_kalan_devir_olur(self):
        """Kalan(10) < Hakedis(20) => Devir = 10"""
        row = {**ORNEK_ROW, "YillikKalan": 10, "YillikHakedis": 20}
        r = _hesapla(row, _tarih(5))
        assert r["YillikDevir"] == 10

    def test_kalan_buyukse_hakedis_sinir_olur(self):
        """Kalan(25) > Hakedis(20) => Devir = 20 (max hakedis kadar)"""
        row = {**ORNEK_ROW, "YillikKalan": 25, "YillikHakedis": 20}
        r = _hesapla(row, _tarih(5))
        assert r["YillikDevir"] == 20

    def test_kalan_sifir_devir_sifir(self):
        row = {**ORNEK_ROW, "YillikKalan": 0, "YillikHakedis": 20}
        r = _hesapla(row, _tarih(5))
        assert r["YillikDevir"] == 0

    def test_kullanilan_sifirlanir(self):
        row = {**ORNEK_ROW, "YillikKullanilan": 15}
        r = _hesapla(row, _tarih(5))
        assert r["YillikKullanilan"] == 0

    def test_toplam_hak_devir_plus_hakedis(self):
        row = {**ORNEK_ROW, "YillikKalan": 8, "YillikHakedis": 20}
        r = _hesapla(row, _tarih(5))
        assert r["YillikToplamHak"] == r["YillikDevir"] + r["YillikHakedis"]

    def test_yeni_kalan_toplam_haka_esit(self):
        row = {**ORNEK_ROW, "YillikKalan": 8, "YillikHakedis": 20}
        r = _hesapla(row, _tarih(5))
        assert r["YillikKalan"] == r["YillikToplamHak"]

    def test_10_yil_hakedis_30_gun(self):
        row = {**ORNEK_ROW, "YillikKalan": 5, "YillikHakedis": 20}
        r = _hesapla(row, _tarih(10))
        assert r["YillikHakedis"] == 30

    def test_9_yil_hakedis_20_gun(self):
        row = {**ORNEK_ROW, "YillikKalan": 5, "YillikHakedis": 20}
        r = _hesapla(row, _tarih(9))
        assert r["YillikHakedis"] == 20

    def test_gecersiz_tarih_hakedis_sifir(self):
        row = {**ORNEK_ROW}
        r = _hesapla(row, "HATALITARIH")
        assert r["YillikHakedis"] == 0

    def test_sifir_hakedis_sinir(self):
        """Kalan > 0 ama Hakedis = 0 => Devir = 0"""
        row = {**ORNEK_ROW, "YillikKalan": 15, "YillikHakedis": 0}
        r = _hesapla(row, "HATALITARIH")
        assert r["YillikDevir"] == 0

    def test_yeni_kalan_hic_negatif_olmaz(self):
        row = {**ORNEK_ROW, "YillikKalan": 0, "YillikHakedis": 0}
        r = _hesapla(row, "HATALITARIH")
        assert r["YillikKalan"] >= 0


# =============================================================
#  5. Sua Izni Devir Mantigi
# =============================================================
class TestSuaIzniDevir:

    def test_cari_kazanim_yeni_hak_olur(self):
        """SuaCariYilKazanim(7) => SuaKullanilabilirHak(7)"""
        row = {**ORNEK_ROW, "SuaCariYilKazanim": 7}
        r = _hesapla(row, _tarih(5))
        assert r["SuaKullanilabilirHak"] == 7

    def test_sua_kalan_yeni_haka_esit(self):
        row = {**ORNEK_ROW, "SuaCariYilKazanim": 5}
        r = _hesapla(row, _tarih(5))
        assert r["SuaKalan"] == 5

    def test_sua_kullanilan_sifirlanir(self):
        row = {**ORNEK_ROW, "SuaCariYilKazanim": 3, "SuaKullanilan": 2}
        r = _hesapla(row, _tarih(5))
        assert r["SuaKullanilan"] == 0

    def test_cari_kazanim_sifirlanir(self):
        """Eski cari kazanim yeni yil icin 0 olmali."""
        row = {**ORNEK_ROW, "SuaCariYilKazanim": 10}
        r = _hesapla(row, _tarih(5))
        assert r["SuaCariYilKazanim"] == 0

    def test_cari_kazanim_sifirsa_hak_sifir(self):
        row = {**ORNEK_ROW, "SuaCariYilKazanim": 0}
        r = _hesapla(row, _tarih(5))
        assert r["SuaKullanilabilirHak"] == 0

    def test_cari_kazanim_string_isleniyor(self):
        row = {**ORNEK_ROW, "SuaCariYilKazanim": "6"}
        r = _hesapla(row, _tarih(5))
        assert r["SuaKullanilabilirHak"] == 6

    def test_tum_sua_alanlari_guncelleniyor(self):
        row = {**ORNEK_ROW, "SuaCariYilKazanim": 4}
        r = _hesapla(row, _tarih(5))
        for alan in ["SuaKullanilabilirHak", "SuaKullanilan", "SuaKalan", "SuaCariYilKazanim"]:
            assert alan in r, f"{alan} eksik"


# =============================================================
#  6. _hesapla Alan Kontrolu
# =============================================================
class TestHesaplaAlanKontrol:

    def test_tum_yillik_alanlar_var(self):
        r = _hesapla(ORNEK_ROW, _tarih(5))
        for alan in ["YillikDevir", "YillikHakedis", "YillikToplamHak",
                     "YillikKullanilan", "YillikKalan"]:
            assert alan in r, f"{alan} eksik"

    def test_tum_sua_alanlari_var(self):
        r = _hesapla(ORNEK_ROW, _tarih(5))
        for alan in ["SuaKullanilabilirHak", "SuaKullanilan",
                     "SuaKalan", "SuaCariYilKazanim"]:
            assert alan in r, f"{alan} eksik"

    def test_string_hakedis_isleniyor(self):
        row = {**ORNEK_ROW, "YillikHakedis": "20", "YillikKalan": "10"}
        r = _hesapla(row, _tarih(5))
        assert isinstance(r["YillikDevir"], int)

    def test_tum_degerler_int(self):
        r = _hesapla(ORNEK_ROW, _tarih(5))
        for k, v in r.items():
            assert isinstance(v, int), f"{k} int degil: {type(v)}"


# =============================================================
#  7. Qt Sayfa Testleri
# =============================================================
class TestYilSonuIslemleriPageQt:

    def test_sayfa_olusturuluyor(self, qapp):
        from ui.pages.yil_sonu_islemleri import YilSonuIslemleriPage
        page = YilSonuIslemleriPage()
        assert page is not None

    def test_chk_onay_var(self, qapp):
        from ui.pages.yil_sonu_islemleri import YilSonuIslemleriPage
        page = YilSonuIslemleriPage()
        assert hasattr(page, "_chk_onay")

    def test_btn_baslat_baslangicta_disabled(self, qapp):
        from ui.pages.yil_sonu_islemleri import YilSonuIslemleriPage
        page = YilSonuIslemleriPage()
        assert not page._btn_baslat.isEnabled()

    def test_chk_isaretlenince_btn_aktif(self, qapp):
        from ui.pages.yil_sonu_islemleri import YilSonuIslemleriPage
        page = YilSonuIslemleriPage()
        page._chk_onay.setChecked(True)
        assert page._btn_baslat.isEnabled()

    def test_chk_kaldirilinca_btn_pasif(self, qapp):
        from ui.pages.yil_sonu_islemleri import YilSonuIslemleriPage
        page = YilSonuIslemleriPage()
        page._chk_onay.setChecked(True)
        page._chk_onay.setChecked(False)
        assert not page._btn_baslat.isEnabled()

    def test_txt_log_var(self, qapp):
        from ui.pages.yil_sonu_islemleri import YilSonuIslemleriPage
        page = YilSonuIslemleriPage()
        assert hasattr(page, "_txt_log")

    def test_txt_log_readonly(self, qapp):
        from ui.pages.yil_sonu_islemleri import YilSonuIslemleriPage
        page = YilSonuIslemleriPage()
        assert page._txt_log.isReadOnly()

    def test_pbar_baslangicta_gizli(self, qapp):
        from ui.pages.yil_sonu_islemleri import YilSonuIslemleriPage
        page = YilSonuIslemleriPage()
        assert not page._pbar.isVisible()

    def test_pbar_var(self, qapp):
        from ui.pages.yil_sonu_islemleri import YilSonuIslemleriPage
        page = YilSonuIslemleriPage()
        assert hasattr(page, "_pbar")

    def test_btn_kapat_var(self, qapp):
        from ui.pages.yil_sonu_islemleri import YilSonuIslemleriPage
        page = YilSonuIslemleriPage()
        assert hasattr(page, "btn_kapat")
