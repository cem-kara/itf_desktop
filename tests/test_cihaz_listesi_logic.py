# -*- coding: utf-8 -*-
"""
cihaz_listesi.py iş mantığı unit testleri
==========================================
Kapsam:
  1. _filter_table   : CihazTipi, Kaynak, Birim filtresi
  2. Kombinasyon filtreler
  3. Sınır durumlar (boş liste, olmayan değer)
  4. Combobox benzersiz değer toplama
  5. Qt sayfa testleri (rowCount, UserRole veri, lbl_count)
"""
import sys
import pytest


@pytest.fixture(scope="module")
def qapp():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication(sys.argv)


VERI = [
    {"Cihazid": "C001", "Marka": "GE",      "Model": "X100", "SeriNo": "SN01",
     "Birim": "Radyoloji",   "CihazTipi": "MR",  "Kaynak": "Döner Sermaye", "Durum": "Aktif"},
    {"Cihazid": "C002", "Marka": "Siemens", "Model": "Y200", "SeriNo": "SN02",
     "Birim": "Radyoloji",   "CihazTipi": "BT",  "Kaynak": "Döner Sermaye", "Durum": "Aktif"},
    {"Cihazid": "C003", "Marka": "Philips", "Model": "Z300", "SeriNo": "SN03",
     "Birim": "Kardiyoloji", "CihazTipi": "EKG", "Kaynak": "Bütçe",         "Durum": "Bakımda"},
    {"Cihazid": "C004", "Marka": "Toshiba", "Model": "A100", "SeriNo": "SN04",
     "Birim": "Kardiyoloji", "CihazTipi": "MR",  "Kaynak": "Bütçe",         "Durum": "Arızalı"},
    {"Cihazid": "C005", "Marka": "GE",      "Model": "B200", "SeriNo": "SN05",
     "Birim": "Nöroloji",    "CihazTipi": "EEG", "Kaynak": "Döner Sermaye", "Durum": "Aktif"},
]


def _filter(data, tip="Tüm Tipler", kaynak="Tüm Kaynaklar", birim="Tüm Birimler"):
    filtered = []
    for row in data:
        if tip    != "Tüm Tipler"    and str(row.get("CihazTipi", "")) != tip:    continue
        if kaynak != "Tüm Kaynaklar" and str(row.get("Kaynak", ""))   != kaynak: continue
        if birim  != "Tüm Birimler"  and str(row.get("Birim", ""))    != birim:  continue
        filtered.append(row)
    return filtered


def _uniq(data, field):
    return {str(r.get(field)) for r in data if r.get(field)}


# =============================================================
#  1. Tek Alan Filtre
# =============================================================
class TestFiltreTekAlan:

    def test_filtre_yok_hepsi(self):
        assert len(_filter(VERI)) == 5

    def test_tip_mr(self):
        ids = {r["Cihazid"] for r in _filter(VERI, tip="MR")}
        assert ids == {"C001", "C004"}

    def test_tip_bt(self):
        r = _filter(VERI, tip="BT")
        assert len(r) == 1 and r[0]["Cihazid"] == "C002"

    def test_tip_ekg(self):
        r = _filter(VERI, tip="EKG")
        assert len(r) == 1 and r[0]["Cihazid"] == "C003"

    def test_tip_eeg(self):
        r = _filter(VERI, tip="EEG")
        assert len(r) == 1 and r[0]["Cihazid"] == "C005"

    def test_kaynak_donel_sermaye(self):
        ids = {r["Cihazid"] for r in _filter(VERI, kaynak="Döner Sermaye")}
        assert ids == {"C001", "C002", "C005"}

    def test_kaynak_butce(self):
        ids = {r["Cihazid"] for r in _filter(VERI, kaynak="Bütçe")}
        assert ids == {"C003", "C004"}

    def test_birim_radyoloji(self):
        ids = {r["Cihazid"] for r in _filter(VERI, birim="Radyoloji")}
        assert ids == {"C001", "C002"}

    def test_birim_kardiyoloji(self):
        ids = {r["Cihazid"] for r in _filter(VERI, birim="Kardiyoloji")}
        assert ids == {"C003", "C004"}

    def test_birim_noroloji(self):
        r = _filter(VERI, birim="Nöroloji")
        assert len(r) == 1 and r[0]["Cihazid"] == "C005"


# =============================================================
#  2. Kombinasyon Filtreler
# =============================================================
class TestFiltreKombinasyon:

    def test_tip_kaynak(self):
        r = _filter(VERI, tip="MR", kaynak="Döner Sermaye")
        assert len(r) == 1 and r[0]["Cihazid"] == "C001"

    def test_tip_birim(self):
        r = _filter(VERI, tip="MR", birim="Kardiyoloji")
        assert len(r) == 1 and r[0]["Cihazid"] == "C004"

    def test_kaynak_birim(self):
        r = _filter(VERI, kaynak="Bütçe", birim="Kardiyoloji")
        assert len(r) == 2

    def test_uc_filtre_eslesen_yok(self):
        assert _filter(VERI, tip="BT", kaynak="Bütçe", birim="Radyoloji") == []

    def test_uc_filtre_bir_sonuc(self):
        r = _filter(VERI, tip="BT", kaynak="Döner Sermaye", birim="Radyoloji")
        assert len(r) == 1 and r[0]["Cihazid"] == "C002"


# =============================================================
#  3. Sınır Durumlar
# =============================================================
class TestSinirDurumlar:

    def test_bos_veri(self):
        assert _filter([], tip="MR") == []

    def test_olmayan_tip(self):
        assert _filter(VERI, tip="USG") == []

    def test_olmayan_birim(self):
        assert _filter(VERI, birim="Dahiliye") == []

    def test_bos_cihaz_tipi_eslesmez(self):
        v = [{"Cihazid": "X", "CihazTipi": "", "Kaynak": "Bütçe", "Birim": "Test"}]
        assert _filter(v, tip="MR") == []

    def test_none_alan_eslesmez(self):
        v = [{"Cihazid": "X", "CihazTipi": None, "Kaynak": "Bütçe", "Birim": "Test"}]
        assert _filter(v, tip="MR") == []

    def test_tek_eleman_eslesen(self):
        r = _filter([VERI[0]], tip="MR", kaynak="Döner Sermaye", birim="Radyoloji")
        assert len(r) == 1


# =============================================================
#  4. Combobox Benzersiz Değerler
# =============================================================
class TestComboboxDolgusu:

    def test_tipler(self):
        assert _uniq(VERI, "CihazTipi") == {"MR", "BT", "EKG", "EEG"}

    def test_birimler(self):
        assert _uniq(VERI, "Birim") == {"Radyoloji", "Kardiyoloji", "Nöroloji"}

    def test_kaynaklar(self):
        assert _uniq(VERI, "Kaynak") == {"Döner Sermaye", "Bütçe"}

    def test_bos_alan_dahil_edilmez(self):
        v = [{"CihazTipi": "MR"}, {"CihazTipi": ""}, {"CihazTipi": None}]
        tipler = _uniq(v, "CihazTipi")
        assert "" not in tipler
        assert "MR" in tipler


# =============================================================
#  5. Qt Sayfa Testleri
# =============================================================
class TestCihazListesiQt:

    def test_sinyaller_var(self, qapp):
        from ui.pages.cihaz.cihaz_listesi import CihazListesiPage
        page = CihazListesiPage(db=None)
        assert hasattr(page, "edit_requested")
        assert hasattr(page, "add_requested")
        assert hasattr(page, "periodic_maintenance_requested")

    def test_populate_satir_sayisi(self, qapp):
        from ui.pages.cihaz.cihaz_listesi import CihazListesiPage
        page = CihazListesiPage(db=None)
        page._populate_table(VERI)
        assert page.table.rowCount() == 5

    def test_populate_bos(self, qapp):
        from ui.pages.cihaz.cihaz_listesi import CihazListesiPage
        page = CihazListesiPage(db=None)
        page._populate_table([])
        assert page.table.rowCount() == 0

    def test_populate_cihazid_sutun(self, qapp):
        from ui.pages.cihaz.cihaz_listesi import CihazListesiPage
        page = CihazListesiPage(db=None)
        page._populate_table([VERI[0]])
        assert page.table.item(0, 0).text() == "C001"

    def test_populate_marka_sutun(self, qapp):
        from ui.pages.cihaz.cihaz_listesi import CihazListesiPage
        page = CihazListesiPage(db=None)
        page._populate_table([VERI[0]])
        assert page.table.item(0, 1).text() == "GE"

    def test_userdata_saklanıyor(self, qapp):
        from PySide6.QtCore import Qt
        from ui.pages.cihaz.cihaz_listesi import CihazListesiPage
        page = CihazListesiPage(db=None)
        page._populate_table([VERI[0]])
        data = page.table.item(0, 0).data(Qt.UserRole)
        assert data["Cihazid"] == "C001"

    def test_lbl_count_guncelleniyor(self, qapp):
        from ui.pages.cihaz.cihaz_listesi import CihazListesiPage
        page = CihazListesiPage(db=None)
        page._populate_table(VERI)
        assert "5" in page.lbl_count.text()

    def test_tablo_sutun_sayisi(self, qapp):
        from ui.pages.cihaz.cihaz_listesi import CihazListesiPage
        page = CihazListesiPage(db=None)
        assert page.table.columnCount() == 7
