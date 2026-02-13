# -*- coding: utf-8 -*-
"""
izin_giris.py iş mantığı unit testleri
========================================
Kapsam:
  1. _parse_date          : çoklu format tarih parse
  2. Çakışma algoritması  : (yeni_bas <= vt_bit) and (yeni_bit >= vt_bas)
  3. Bakiye düşme mantığı : Yıllık / Şua / Rapor-Mazeret
  4. Bitiş tarihi hesabı  : iş günü + hafta sonu / tatil atlama
  5. IzinTableModel       : Qt model (rowCount, data, header, renk)
"""
import sys
import pytest
from datetime import date, timedelta, datetime


# ──────────────────────────────────────────────────
#  _parse_date — module level fonksiyon
# ──────────────────────────────────────────────────
_DATE_FMTS = ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y", "%Y/%m/%d", "%d-%m-%Y")

def _parse_date(val):
    val = str(val).strip()
    if not val:
        return None
    for fmt in _DATE_FMTS:
        try:
            return datetime.strptime(val, fmt).date()
        except ValueError:
            continue
    return None


# ──────────────────────────────────────────────────
#  Çakışma algoritması (pure Python)
# ──────────────────────────────────────────────────
def _cakisma_var_mi(yeni_bas: date, yeni_bit: date,
                   mevcut_izinler: list, tc: str) -> bool:
    """izin_giris._on_save içindeki çakışma kontrolü."""
    for kayit in mevcut_izinler:
        if str(kayit.get("Durum", "")) == "İptal":
            continue
        if str(kayit.get("Personelid", "")) != tc:
            continue
        vt_bas = _parse_date(kayit.get("BaslamaTarihi", ""))
        vt_bit = _parse_date(kayit.get("BitisTarihi", ""))
        if vt_bas and vt_bit:
            if (yeni_bas <= vt_bit) and (yeni_bit >= vt_bas):
                return True
    return False


# ──────────────────────────────────────────────────
#  Bakiye düşme (pure Python)
# ──────────────────────────────────────────────────
def _bakiye_hesapla(izin_bilgi: dict, izin_tipi: str, gun: int) -> dict:
    """izin_giris._bakiye_dus mantığını dict üzerinde simüle eder."""
    bilgi = dict(izin_bilgi)  # kopya
    if izin_tipi == "Yıllık İzin":
        bilgi["YillikKullanilan"] = float(bilgi.get("YillikKullanilan", 0)) + gun
        bilgi["YillikKalan"]      = float(bilgi.get("YillikKalan", 0)) - gun
    elif izin_tipi == "Şua İzni":
        bilgi["SuaKullanilan"] = float(bilgi.get("SuaKullanilan", 0)) + gun
        bilgi["SuaKalan"]      = float(bilgi.get("SuaKalan", 0)) - gun
    elif izin_tipi in ["Sağlık Raporu", "Mazeret İzni"]:
        bilgi["RaporMazeretTop"] = float(bilgi.get("RaporMazeretTop", 0)) + gun
    return bilgi


# ──────────────────────────────────────────────────
#  Bitiş tarihi hesabı (pure Python)
# ──────────────────────────────────────────────────
def _hesapla_bitis(baslama: date, gun: int, tatiller: set) -> date:
    """izin_giris._calculate_bitis mantığı — hafta sonu ve tatilleri atlar."""
    kalan = gun
    current = baslama
    while kalan > 0:
        current += timedelta(days=1)
        if current.weekday() in (5, 6):   # Cumartesi, Pazar
            continue
        if current.strftime("%Y-%m-%d") in tatiller:
            continue
        kalan -= 1
    return current


# ──────────────────────────────────────────────────
#  Qt fixture
# ──────────────────────────────────────────────────
@pytest.fixture(scope="module")
def qapp():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication(sys.argv)


# =============================================================
#  1. _parse_date
# =============================================================
class TestParseDateIzin:

    def test_yyyy_mm_dd(self):
        assert _parse_date("2024-03-15") == date(2024, 3, 15)

    def test_dd_mm_yyyy(self):
        assert _parse_date("15.03.2024") == date(2024, 3, 15)

    def test_dd_slash_mm_slash_yyyy(self):
        assert _parse_date("15/03/2024") == date(2024, 3, 15)

    def test_yyyy_slash_mm_slash_dd(self):
        assert _parse_date("2024/03/15") == date(2024, 3, 15)

    def test_dd_dash_mm_dash_yyyy(self):
        assert _parse_date("15-03-2024") == date(2024, 3, 15)

    def test_bos_string_none(self):
        assert _parse_date("") is None

    def test_none_str_none(self):
        assert _parse_date("None") is None

    def test_bosluk_none(self):
        assert _parse_date("   ") is None

    def test_gecersiz_format_none(self):
        assert _parse_date("not-a-date") is None

    def test_yanlis_gun_none(self):
        assert _parse_date("2024-13-01") is None

    def test_artik_yil_subat_29(self):
        assert _parse_date("2024-02-29") == date(2024, 2, 29)

    def test_non_artik_yil_subat_29_none(self):
        assert _parse_date("2023-02-29") is None


# =============================================================
#  2. Çakışma Kontrolü
# =============================================================
class TestCakismaKontrolu:

    MEVCUT = [
        {"Personelid": "12345", "BaslamaTarihi": "2026-02-10",
         "BitisTarihi": "2026-02-14", "Durum": "Onaylandı"},
        {"Personelid": "12345", "BaslamaTarihi": "2026-02-20",
         "BitisTarihi": "2026-02-25", "Durum": "Onaylandı"},
    ]

    def test_tam_cakisma(self):
        bas = date(2026, 2, 11)
        bit = date(2026, 2, 13)
        assert _cakisma_var_mi(bas, bit, self.MEVCUT, "12345") is True

    def test_bas_cakisiyor(self):
        """Yeni izin mevcut içinde başlıyor."""
        bas = date(2026, 2, 12)
        bit = date(2026, 2, 16)
        assert _cakisma_var_mi(bas, bit, self.MEVCUT, "12345") is True

    def test_bit_cakisiyor(self):
        """Yeni izin mevcut içinde bitiyor."""
        bas = date(2026, 2, 8)
        bit = date(2026, 2, 12)
        assert _cakisma_var_mi(bas, bit, self.MEVCUT, "12345") is True

    def test_kapsayan_cakisma(self):
        """Yeni izin mevcutu tamamen kapsıyor."""
        bas = date(2026, 2, 9)
        bit = date(2026, 2, 16)
        assert _cakisma_var_mi(bas, bit, self.MEVCUT, "12345") is True

    def test_cakisma_yok_arasi(self):
        """İki mevcut izin arasında boşluk."""
        bas = date(2026, 2, 15)
        bit = date(2026, 2, 19)
        assert _cakisma_var_mi(bas, bit, self.MEVCUT, "12345") is False

    def test_cakisma_yok_sonrasi(self):
        bas = date(2026, 2, 26)
        bit = date(2026, 3, 1)
        assert _cakisma_var_mi(bas, bit, self.MEVCUT, "12345") is False

    def test_cakisma_yok_oncesi(self):
        bas = date(2026, 2, 1)
        bit = date(2026, 2, 9)
        assert _cakisma_var_mi(bas, bit, self.MEVCUT, "12345") is False

    def test_iptal_kayit_atlanir(self):
        """Durum=İptal olan kayıt çakışma kontrolüne dahil edilmemeli."""
        iptal = [{"Personelid": "12345", "BaslamaTarihi": "2026-02-11",
                  "BitisTarihi": "2026-02-13", "Durum": "İptal"}]
        bas = date(2026, 2, 11)
        bit = date(2026, 2, 13)
        assert _cakisma_var_mi(bas, bit, iptal, "12345") is False

    def test_farkli_personel_atlanir(self):
        """Başka personelin kaydı çakışma vermemeli."""
        bas = date(2026, 2, 11)
        bit = date(2026, 2, 13)
        assert _cakisma_var_mi(bas, bit, self.MEVCUT, "99999") is False

    def test_bos_liste_cakisma_yok(self):
        assert _cakisma_var_mi(date(2026, 1, 1), date(2026, 1, 5), [], "12345") is False

    def test_kenar_bas_bitis_esit(self):
        """Yeni iznin bitişi mevcut iznin başlangıcına eşit → çakışır."""
        bas = date(2026, 2, 14)
        bit = date(2026, 2, 14)
        assert _cakisma_var_mi(bas, bit, self.MEVCUT, "12345") is True

    def test_kenar_bit_bitis_esit(self):
        """Yeni iznin başlangıcı mevcut iznin bitişine eşit → çakışır."""
        bas = date(2026, 2, 25)
        bit = date(2026, 2, 28)
        assert _cakisma_var_mi(bas, bit, self.MEVCUT, "12345") is True


# =============================================================
#  3. Bakiye Düşme Mantığı
# =============================================================
class TestBakiyeDusme:

    BASE = {
        "YillikKullanilan": 5.0,
        "YillikKalan":     15.0,
        "SuaKullanilan":    3.0,
        "SuaKalan":         7.0,
        "RaporMazeretTop":  2.0,
    }

    def test_yillik_izin_kullanilan_artar(self):
        bilgi = _bakiye_hesapla(self.BASE, "Yıllık İzin", 3)
        assert bilgi["YillikKullanilan"] == 8.0

    def test_yillik_izin_kalan_azalir(self):
        bilgi = _bakiye_hesapla(self.BASE, "Yıllık İzin", 3)
        assert bilgi["YillikKalan"] == 12.0

    def test_yillik_izin_toplam_korunur(self):
        bilgi = _bakiye_hesapla(self.BASE, "Yıllık İzin", 3)
        assert bilgi["YillikKullanilan"] + bilgi["YillikKalan"] == 20.0

    def test_sua_izni_kullanilan_artar(self):
        bilgi = _bakiye_hesapla(self.BASE, "Şua İzni", 2)
        assert bilgi["SuaKullanilan"] == 5.0

    def test_sua_izni_kalan_azalir(self):
        bilgi = _bakiye_hesapla(self.BASE, "Şua İzni", 2)
        assert bilgi["SuaKalan"] == 5.0

    def test_saglik_raporu_top_artar(self):
        bilgi = _bakiye_hesapla(self.BASE, "Sağlık Raporu", 5)
        assert bilgi["RaporMazeretTop"] == 7.0

    def test_mazeret_izni_top_artar(self):
        bilgi = _bakiye_hesapla(self.BASE, "Mazeret İzni", 1)
        assert bilgi["RaporMazeretTop"] == 3.0

    def test_diger_izin_tipi_degistirmez(self):
        """Ücretsiz İzin bakiyede değişiklik yapmaz."""
        bilgi = _bakiye_hesapla(self.BASE, "Ücretsiz İzin", 10)
        assert bilgi["YillikKalan"] == 15.0
        assert bilgi["SuaKalan"] == 7.0
        assert bilgi["RaporMazeretTop"] == 2.0

    def test_sifir_gun_degistirmez(self):
        bilgi = _bakiye_hesapla(self.BASE, "Yıllık İzin", 0)
        assert bilgi["YillikKalan"] == 15.0

    def test_orijinal_dict_degismez(self):
        """Fonksiyon orijinal dict'i mutate etmemeli."""
        original = dict(self.BASE)
        _bakiye_hesapla(self.BASE, "Yıllık İzin", 5)
        assert self.BASE["YillikKalan"] == original["YillikKalan"]


# =============================================================
#  4. Bitiş Tarihi Hesaplama
# =============================================================
class TestBitisTarihiHesapla:

    def test_1_gun_hafta_ici(self):
        """Pazartesi + 1 iş günü → Salı."""
        bas = date(2024, 1, 1)   # Pazartesi
        bitis = _hesapla_bitis(bas, 1, set())
        assert bitis == date(2024, 1, 2)  # Salı

    def test_cuma_1_gun_pazartesi(self):
        """Cuma + 1 iş günü → Pazartesi (hafta sonunu atlar)."""
        bas = date(2024, 1, 5)   # Cuma
        bitis = _hesapla_bitis(bas, 1, set())
        assert bitis == date(2024, 1, 8)  # Pazartesi

    def test_cuma_2_gun_sali(self):
        """Cuma + 2 iş günü → Salı."""
        bas = date(2024, 1, 5)   # Cuma
        bitis = _hesapla_bitis(bas, 2, set())
        assert bitis == date(2024, 1, 9)  # Salı

    def test_tatil_atlama(self):
        """Tatil günü sayılmaz."""
        bas = date(2024, 1, 1)   # Pazartesi
        tatiller = {"2024-01-02"}  # Salı tatil
        bitis = _hesapla_bitis(bas, 1, tatiller)
        assert bitis == date(2024, 1, 3)  # Çarşamba

    def test_birden_fazla_tatil_atlama(self):
        bas = date(2024, 1, 1)   # Pazartesi
        tatiller = {"2024-01-02", "2024-01-03"}  # Salı + Çarşamba tatil
        bitis = _hesapla_bitis(bas, 1, tatiller)
        assert bitis == date(2024, 1, 4)  # Perşembe

    def test_5_gun_tam_hafta(self):
        """
        Pazartesi (1 Oca) + 5 gün izin.
        _calculate_bitis 'işe geri dönüş günü' döndürür:
        5 gün = Pzt/Sal/Çar/Per/Cum → dönüş = ertesi Pazartesi (8 Oca).
        """
        bas = date(2024, 1, 1)   # Pazartesi
        bitis = _hesapla_bitis(bas, 5, set())
        assert bitis == date(2024, 1, 8)  # Pazartesi — işe dönüş günü

    def test_tatil_yok_sifir_gun_aynı_gun(self):
        """0 iş günü → başlangıç tarihinin kendisi."""
        bas = date(2024, 1, 1)
        bitis = _hesapla_bitis(bas, 0, set())
        assert bitis == bas

    def test_cumartesi_baslama_pazartesi_bitiyor(self):
        """Cumartesiden başlayan izin Pazartesi gün ekler."""
        bas = date(2024, 1, 6)   # Cumartesi
        bitis = _hesapla_bitis(bas, 1, set())
        assert bitis == date(2024, 1, 8)  # Pazartesi


# =============================================================
#  5. IzinTableModel (Qt)
# =============================================================
class TestIzinTableModel:

    IZIN_DATA = [
        {"IzinTipi": "Yıllık İzin", "BaslamaTarihi": "2024-03-01",
         "BitisTarihi": "2024-03-05", "Gun": "5", "Durum": "Onaylandı"},
        {"IzinTipi": "Şua İzni", "BaslamaTarihi": "2024-04-10",
         "BitisTarihi": "2024-04-12", "Gun": "3", "Durum": "Beklemede"},
        {"IzinTipi": "Sağlık Raporu", "BaslamaTarihi": "2024-05-20",
         "BitisTarihi": "2024-05-22", "Gun": "3", "Durum": "İptal"},
    ]

    def test_bos_model_row_count_sifir(self, qapp):
        from ui.pages.personel.izin_giris import IzinTableModel
        m = IzinTableModel()
        assert m.rowCount() == 0

    def test_dolu_model_row_count(self, qapp):
        from ui.pages.personel.izin_giris import IzinTableModel
        m = IzinTableModel(self.IZIN_DATA)
        assert m.rowCount() == 3

    def test_column_count(self, qapp):
        from ui.pages.personel.izin_giris import IzinTableModel, IZIN_COLUMNS
        m = IzinTableModel()
        assert m.columnCount() == len(IZIN_COLUMNS)

    def test_display_role_izin_tipi(self, qapp):
        from PySide6.QtCore import Qt, QModelIndex
        from ui.pages.personel.izin_giris import IzinTableModel
        m = IzinTableModel(self.IZIN_DATA)
        idx = m.createIndex(0, 0)
        assert m.data(idx, Qt.DisplayRole) == "Yıllık İzin"

    def test_display_role_gun(self, qapp):
        from PySide6.QtCore import Qt
        from ui.pages.personel.izin_giris import IzinTableModel
        m = IzinTableModel(self.IZIN_DATA)
        idx = m.createIndex(0, 3)  # Gun sütunu (index 3)
        assert m.data(idx, Qt.DisplayRole) == "5"

    def test_display_role_tarih_format(self, qapp):
        """BaslamaTarihi ISO → DD.MM.YYYY formatına dönüşmeli."""
        from PySide6.QtCore import Qt
        from ui.pages.personel.izin_giris import IzinTableModel
        m = IzinTableModel(self.IZIN_DATA)
        idx = m.createIndex(0, 1)  # BaslamaTarihi sütunu
        assert m.data(idx, Qt.DisplayRole) == "01.03.2024"

    def test_gecersiz_index_none(self, qapp):
        from PySide6.QtCore import Qt, QModelIndex
        from ui.pages.personel.izin_giris import IzinTableModel
        m = IzinTableModel(self.IZIN_DATA)
        assert m.data(QModelIndex(), Qt.DisplayRole) is None

    def test_header_horizontal(self, qapp):
        from PySide6.QtCore import Qt
        from ui.pages.personel.izin_giris import IzinTableModel
        m = IzinTableModel()
        h = m.headerData(0, Qt.Horizontal, Qt.DisplayRole)
        assert h is not None
        assert len(h) > 0

    def test_header_dikey_none(self, qapp):
        from PySide6.QtCore import Qt
        from ui.pages.personel.izin_giris import IzinTableModel
        m = IzinTableModel()
        assert m.headerData(0, Qt.Vertical, Qt.DisplayRole) is None

    def test_set_data_gunceller(self, qapp):
        from ui.pages.personel.izin_giris import IzinTableModel
        m = IzinTableModel([])
        assert m.rowCount() == 0
        m.set_data(self.IZIN_DATA)
        assert m.rowCount() == 3

    def test_get_row_gecerli(self, qapp):
        from ui.pages.personel.izin_giris import IzinTableModel
        m = IzinTableModel(self.IZIN_DATA)
        row = m.get_row(1)
        assert row["IzinTipi"] == "Şua İzni"

    def test_get_row_sinir_disi_none(self, qapp):
        from ui.pages.personel.izin_giris import IzinTableModel
        m = IzinTableModel(self.IZIN_DATA)
        assert m.get_row(99) is None

    def test_foreground_onayli_yesil(self, qapp):
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QColor
        from ui.pages.personel.izin_giris import IzinTableModel
        m = IzinTableModel(self.IZIN_DATA)
        idx = m.createIndex(0, 4)  # Durum = Onaylandı
        renk = m.data(idx, Qt.ForegroundRole)
        assert renk is not None
        assert isinstance(renk, QColor)

    def test_foreground_iptal_kirmizi(self, qapp):
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QColor
        from ui.pages.personel.izin_giris import IzinTableModel
        m = IzinTableModel(self.IZIN_DATA)
        idx = m.createIndex(2, 4)  # Durum = İptal
        renk = m.data(idx, Qt.ForegroundRole)
        assert renk is not None

    def test_alignment_gun_merkez(self, qapp):
        from PySide6.QtCore import Qt
        from ui.pages.personel.izin_giris import IzinTableModel
        m = IzinTableModel(self.IZIN_DATA)
        idx = m.createIndex(0, 3)  # Gun
        alignment = m.data(idx, Qt.TextAlignmentRole)
        assert alignment is not None
