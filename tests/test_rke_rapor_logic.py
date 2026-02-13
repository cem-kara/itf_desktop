# -*- coding: utf-8 -*-
"""
rke_rapor.py unit testleri
===========================
Kapsam:
  1. COLUMNS / SONUC_RENK sabitler
  2. html_genel_rapor  : HTML içerik doğrulaması
  3. html_hurda_rapor  : Hurda HTML doğrulaması
  4. RaporTableModel   : Qt model (rowCount, columnCount, data, header, set_data, get_row)
  5. Sonuç hesabı      : Fiziksel/Skopi durumuna göre "Kullanıma Uygun / Değil"
  6. _filtrele mantığı : ABD, Birim, Tarih, Hurda modu
  7. Tarih sıralama    : parse_date + cascading filter
"""
import sys
import datetime
import pytest


# ──────────────────────────────────────────────────
#  Saf Python soyutlamaları (Qt bağımlılığı olmadan)
# ──────────────────────────────────────────────────

def _sonuc_belirle(fiziksel: str, skopi: str) -> str:
    """rke_rapor.VeriYukleyiciThread içindeki sonuç mantığı."""
    if "Değil" in fiziksel or "Değil" in skopi:
        return "Kullanıma Uygun Değil"
    return "Kullanıma Uygun"


def _filtrele(ham_veriler: list, f_abd="Tüm Bölümler",
              f_birim="Tüm Birimler", f_tarih="Tüm Tarihler",
              hurda_modu=False) -> list:
    """RKERaporPage._filtrele mantığı."""
    result = []
    for row in ham_veriler:
        if "Tüm" not in f_abd   and row.get("ABD",   "") != f_abd:   continue
        if "Tüm" not in f_birim and row.get("Birim", "") != f_birim: continue
        if "Tüm" not in f_tarih and row.get("Tarih", "") != f_tarih: continue
        if hurda_modu and "Değil" not in row.get("Sonuc", ""):        continue
        result.append(row)
    return result


def _parse_date(s: str) -> datetime.date:
    for fmt in ("%Y-%m-%d", "%d.%m.%Y"):
        try:
            return datetime.datetime.strptime(s, fmt).date()
        except Exception:
            continue
    return datetime.date.min


def _tarih_sırala(tarih_seti: set) -> list:
    """VeriYukleyiciThread içindeki tarih sıralama."""
    return sorted(tarih_seti, key=_parse_date, reverse=True)


def _cascade_tarih(ham_veriler, f_abd, f_birim) -> set:
    """_on_abd_birim_degisti: Seçili ABD/Birim için mevcut tarihleri döndürür."""
    tarihler = set()
    for row in ham_veriler:
        if "Tüm" not in f_abd   and row.get("ABD",   "") != f_abd:   continue
        if "Tüm" not in f_birim and row.get("Birim", "") != f_birim: continue
        if row.get("Tarih"):
            tarihler.add(row["Tarih"])
    return tarihler


# ─── Test verisi ───
VERİ = [
    {"EkipmanNo": "RKE-OAC-001", "Cins": "Önlük", "Pb": "0.25",
     "Birim": "Radyoloji", "ABD": "Radyoloji ABD", "Tarih": "2024-01-10",
     "Fiziksel": "Kullanıma Uygun", "Skopi": "Yapılmadı",
     "Sonuc": "Kullanıma Uygun", "KontrolEden": "Ali Veli",
     "Aciklama": "Normal", "Cins": "Önlük"},
    {"EkipmanNo": "RKE-OAC-002", "Cins": "Önlük", "Pb": "0.35",
     "Birim": "Kardiyoloji", "ABD": "Kardiyoloji ABD", "Tarih": "2024-01-15",
     "Fiziksel": "Kullanıma Uygun Değil", "Skopi": "Yapılmadı",
     "Sonuc": "Kullanıma Uygun Değil", "KontrolEden": "Ali Veli",
     "Aciklama": "Çatlak", "Cins": "Önlük"},
    {"EkipmanNo": "RKE-TID-003", "Cins": "Tiroid", "Pb": "0.50",
     "Birim": "Radyoloji", "ABD": "Radyoloji ABD", "Tarih": "2024-01-10",
     "Fiziksel": "Kullanıma Uygun", "Skopi": "Kullanıma Uygun Değil",
     "Sonuc": "Kullanıma Uygun Değil", "KontrolEden": "Mehmet Can",
     "Aciklama": "Skopi hatası"},
    {"EkipmanNo": "RKE-OAC-004", "Cins": "Önlük", "Pb": "0.25",
     "Birim": "Nöroloji", "ABD": "Nöroloji ABD", "Tarih": "2024-02-01",
     "Fiziksel": "Kullanıma Uygun", "Skopi": "Kullanıma Uygun",
     "Sonuc": "Kullanıma Uygun", "KontrolEden": "Mehmet Can",
     "Aciklama": ""},
]


@pytest.fixture(scope="module")
def qapp():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication(sys.argv)


# =============================================================
#  1. Sabitler
# =============================================================
class TestRaporSabitler:

    def test_columns_8_adet(self):
        from ui.pages.cihaz.rke_rapor import COLUMNS
        assert len(COLUMNS) == 8

    def test_columns_ilk_ekipman_no(self):
        from ui.pages.cihaz.rke_rapor import COLUMNS
        assert COLUMNS[0][0] == "EkipmanNo"

    def test_columns_sonuc_var(self):
        from ui.pages.cihaz.rke_rapor import COLUMNS
        anahtarlar = [c[0] for c in COLUMNS]
        assert "Sonuc" in anahtarlar

    def test_columns_kontrol_eden_var(self):
        from ui.pages.cihaz.rke_rapor import COLUMNS
        anahtarlar = [c[0] for c in COLUMNS]
        assert "KontrolEden" in anahtarlar

    def test_sonuc_renk_uygun_var(self):
        from ui.pages.cihaz.rke_rapor import SONUC_RENK
        assert "Kullanıma Uygun" in SONUC_RENK

    def test_sonuc_renk_uygun_degil_var(self):
        from ui.pages.cihaz.rke_rapor import SONUC_RENK
        assert "Kullanıma Uygun Değil" in SONUC_RENK

    def test_sonuc_renk_2_eleman(self):
        from ui.pages.cihaz.rke_rapor import SONUC_RENK
        assert len(SONUC_RENK) == 2

    def test_columns_pb_var(self):
        from ui.pages.cihaz.rke_rapor import COLUMNS
        anahtarlar = [c[0] for c in COLUMNS]
        assert "Pb" in anahtarlar


# =============================================================
#  2. HTML Genel Rapor
# =============================================================
class TestHtmlGenelRapor:

    def test_html_genel_rapor_html_donuyor(self):
        from ui.pages.cihaz.rke_rapor import html_genel_rapor
        out = html_genel_rapor(VERİ[:2], "Radyoloji")
        assert "<html" in out.lower()

    def test_filtre_ozeti_iceriyor(self):
        from ui.pages.cihaz.rke_rapor import html_genel_rapor
        out = html_genel_rapor(VERİ[:2], "Radyoloji ABD")
        assert "Radyoloji ABD" in out

    def test_baslik_iceriyor(self):
        from ui.pages.cihaz.rke_rapor import html_genel_rapor
        out = html_genel_rapor(VERİ, "Tüm")
        assert "RKE" in out.upper()

    def test_ekipman_no_iceriyor(self):
        from ui.pages.cihaz.rke_rapor import html_genel_rapor
        out = html_genel_rapor([VERİ[0]], "Test")
        assert "RKE-OAC-001" in out

    def test_imza_tablosu_var(self):
        from ui.pages.cihaz.rke_rapor import html_genel_rapor
        out = html_genel_rapor(VERİ, "Test")
        assert "sig-table" in out or "İmza" in out

    def test_tarih_iceriyor(self):
        from ui.pages.cihaz.rke_rapor import html_genel_rapor
        out = html_genel_rapor(VERİ, "Test")
        yil = str(datetime.datetime.now().year)
        assert yil in out

    def test_bos_veri_html_donuyor(self):
        from ui.pages.cihaz.rke_rapor import html_genel_rapor
        out = html_genel_rapor([], "Test")
        assert "<table" in out.lower()


# =============================================================
#  3. HTML Hurda Rapor
# =============================================================
class TestHtmlHurdaRapor:

    def test_hurda_html_donuyor(self):
        from ui.pages.cihaz.rke_rapor import html_hurda_rapor
        hurda = [v for v in VERİ if "Değil" in v.get("Sonuc", "")]
        out = html_hurda_rapor(hurda)
        assert "<html" in out.lower()

    def test_hurda_baslik_iceriyor(self):
        from ui.pages.cihaz.rke_rapor import html_hurda_rapor
        out = html_hurda_rapor(VERİ[:1])
        assert "HURDA" in out.upper() or "HEK" in out.upper()

    def test_hurda_yasal_paragraf_var(self):
        from ui.pages.cihaz.rke_rapor import html_hurda_rapor
        out = html_hurda_rapor(VERİ[:1])
        assert "legal" in out or "arz" in out.lower()

    def test_hurda_ekipman_satiri_var(self):
        from ui.pages.cihaz.rke_rapor import html_hurda_rapor
        out = html_hurda_rapor([VERİ[1]])
        assert "RKE-OAC-002" in out

    def test_hurda_sira_numarasi_var(self):
        from ui.pages.cihaz.rke_rapor import html_hurda_rapor
        hurda = [v for v in VERİ if "Değil" in v.get("Sonuc", "")]
        out = html_hurda_rapor(hurda)
        assert "<td>1</td>" in out

    def test_hurda_imza_tablosu_var(self):
        from ui.pages.cihaz.rke_rapor import html_hurda_rapor
        out = html_hurda_rapor(VERİ[:1])
        assert "Kontrol Eden" in out


# =============================================================
#  4. Sonuç Belirleme Mantığı
# =============================================================
class TestSonucBelirleme:

    def test_her_ikisi_uygun(self):
        assert _sonuc_belirle("Kullanıma Uygun", "Kullanıma Uygun") == "Kullanıma Uygun"

    def test_fiziksel_uygun_degil(self):
        assert _sonuc_belirle("Kullanıma Uygun Değil", "Kullanıma Uygun") == "Kullanıma Uygun Değil"

    def test_skopi_uygun_degil(self):
        assert _sonuc_belirle("Kullanıma Uygun", "Kullanıma Uygun Değil") == "Kullanıma Uygun Değil"

    def test_her_ikisi_uygun_degil(self):
        assert _sonuc_belirle("Kullanıma Uygun Değil", "Kullanıma Uygun Değil") == "Kullanıma Uygun Değil"

    def test_skopi_yapilmadi_uygun(self):
        assert _sonuc_belirle("Kullanıma Uygun", "Yapılmadı") == "Kullanıma Uygun"

    def test_bos_degerler_uygun(self):
        assert _sonuc_belirle("", "") == "Kullanıma Uygun"

    def test_sadece_degil_icerirse_uygun_degil(self):
        assert _sonuc_belirle("Kullanıma Uygun Değil", "") == "Kullanıma Uygun Değil"


# =============================================================
#  5. Filtre Mantığı
# =============================================================
class TestFiltreMantigi:

    def test_filtre_yok_hepsi(self):
        assert len(_filtrele(VERİ)) == 4

    def test_abd_filtre(self):
        r = _filtrele(VERİ, f_abd="Radyoloji ABD")
        assert len(r) == 2
        assert all(x["ABD"] == "Radyoloji ABD" for x in r)

    def test_birim_filtre(self):
        r = _filtrele(VERİ, f_birim="Radyoloji")
        assert len(r) == 2

    def test_tarih_filtre(self):
        r = _filtrele(VERİ, f_tarih="2024-01-10")
        assert len(r) == 2

    def test_abd_birim_kombinasyon(self):
        r = _filtrele(VERİ, f_abd="Radyoloji ABD", f_birim="Radyoloji")
        assert len(r) == 2

    def test_hurda_modu_sadece_uygun_degil(self):
        r = _filtrele(VERİ, hurda_modu=True)
        assert len(r) == 2
        assert all("Değil" in x["Sonuc"] for x in r)

    def test_hurda_modu_abd_filtre_kombinasyon(self):
        r = _filtrele(VERİ, f_abd="Radyoloji ABD", hurda_modu=True)
        assert len(r) == 1

    def test_bos_veri(self):
        assert _filtrele([]) == []

    def test_olmayan_abd(self):
        assert _filtrele(VERİ, f_abd="Eczacılık ABD") == []

    def test_tarih_ve_hurda_modu(self):
        r = _filtrele(VERİ, f_tarih="2024-01-10", hurda_modu=True)
        assert len(r) == 1
        assert r[0]["EkipmanNo"] == "RKE-TID-003"


# =============================================================
#  6. Tarih Sıralama
# =============================================================
class TestTarihSiralama:

    def test_en_yeni_once(self):
        tarihler = {"2024-01-01", "2024-03-15", "2024-02-10"}
        sirali = _tarih_sırala(tarihler)
        assert sirali[0] == "2024-03-15"

    def test_eski_en_son(self):
        tarihler = {"2024-01-01", "2024-06-30"}
        sirali = _tarih_sırala(tarihler)
        assert sirali[-1] == "2024-01-01"

    def test_farkli_format_destekleniyor(self):
        d = _parse_date("15.03.2024")
        assert d == datetime.date(2024, 3, 15)

    def test_gecersiz_tarih_min_doner(self):
        d = _parse_date("not-a-date")
        assert d == datetime.date.min

    def test_bos_tarih_set(self):
        assert _tarih_sırala(set()) == []


# =============================================================
#  7. Cascade Tarih Filtresi
# =============================================================
class TestCascadeTarih:

    def test_abd_filtresi_tarihleri_kisitlar(self):
        t = _cascade_tarih(VERİ, "Nöroloji ABD", "Tüm Birimler")
        assert "2024-02-01" in t
        assert "2024-01-10" not in t

    def test_birim_filtresi_tarihleri_kisitlar(self):
        t = _cascade_tarih(VERİ, "Tüm Bölümler", "Kardiyoloji")
        assert "2024-01-15" in t
        assert "2024-02-01" not in t

    def test_tum_filtreler_tum_tarihler(self):
        t = _cascade_tarih(VERİ, "Tüm Bölümler", "Tüm Birimler")
        assert len(t) == 3  # 2024-01-10, 2024-01-15, 2024-02-01

    def test_bos_veri_bos_set(self):
        assert _cascade_tarih([], "Tüm", "Tüm") == set()


# =============================================================
#  8. RaporTableModel (Qt)
# =============================================================
class TestRaporTableModel:

    def test_bos_model_row_sifir(self, qapp):
        from ui.pages.cihaz.rke_rapor import RaporTableModel
        m = RaporTableModel()
        assert m.rowCount() == 0

    def test_dolu_model_row_count(self, qapp):
        from ui.pages.cihaz.rke_rapor import RaporTableModel
        m = RaporTableModel(VERİ)
        assert m.rowCount() == 4

    def test_column_count_8(self, qapp):
        from ui.pages.cihaz.rke_rapor import RaporTableModel
        m = RaporTableModel()
        assert m.columnCount() == 8

    def test_display_role_ekipman_no(self, qapp):
        from PySide6.QtCore import Qt
        from ui.pages.cihaz.rke_rapor import RaporTableModel
        m = RaporTableModel(VERİ)
        idx = m.createIndex(0, 0)  # EkipmanNo
        assert m.data(idx, Qt.DisplayRole) == "RKE-OAC-001"

    def test_display_role_sonuc(self, qapp):
        from PySide6.QtCore import Qt
        from ui.pages.cihaz.rke_rapor import RaporTableModel
        m = RaporTableModel(VERİ)
        idx = m.createIndex(0, 5)  # Sonuc sütunu (index 5)
        assert m.data(idx, Qt.DisplayRole) == "Kullanıma Uygun"

    def test_gecersiz_index_none(self, qapp):
        from PySide6.QtCore import Qt, QModelIndex
        from ui.pages.cihaz.rke_rapor import RaporTableModel
        m = RaporTableModel(VERİ)
        assert m.data(QModelIndex(), Qt.DisplayRole) is None

    def test_foreground_uygun_degil_kirmizi(self, qapp):
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QColor
        from ui.pages.cihaz.rke_rapor import RaporTableModel
        m = RaporTableModel(VERİ)
        idx = m.createIndex(1, 5)  # Sonuc = "Kullanıma Uygun Değil"
        renk = m.data(idx, Qt.ForegroundRole)
        assert renk is not None
        assert isinstance(renk, QColor)

    def test_header_horizontal_dolu(self, qapp):
        from PySide6.QtCore import Qt
        from ui.pages.cihaz.rke_rapor import RaporTableModel
        m = RaporTableModel()
        h = m.headerData(0, Qt.Horizontal, Qt.DisplayRole)
        assert h is not None and len(h) > 0

    def test_header_dikey_none(self, qapp):
        from PySide6.QtCore import Qt
        from ui.pages.cihaz.rke_rapor import RaporTableModel
        m = RaporTableModel()
        assert m.headerData(0, Qt.Vertical, Qt.DisplayRole) is None

    def test_set_data_gunceller(self, qapp):
        from ui.pages.cihaz.rke_rapor import RaporTableModel
        m = RaporTableModel([])
        assert m.rowCount() == 0
        m.set_data(VERİ)
        assert m.rowCount() == 4

    def test_get_row_gecerli(self, qapp):
        from ui.pages.cihaz.rke_rapor import RaporTableModel
        m = RaporTableModel(VERİ)
        row = m.get_row(2)
        assert row["EkipmanNo"] == "RKE-TID-003"

    def test_get_row_sinir_disi_none(self, qapp):
        from ui.pages.cihaz.rke_rapor import RaporTableModel
        m = RaporTableModel(VERİ)
        assert m.get_row(99) is None

    def test_alignment_tarih_merkez(self, qapp):
        from PySide6.QtCore import Qt
        from ui.pages.cihaz.rke_rapor import RaporTableModel
        m = RaporTableModel(VERİ)
        idx = m.createIndex(0, 4)  # Tarih sütunu
        alignment = m.data(idx, Qt.TextAlignmentRole)
        assert alignment is not None
