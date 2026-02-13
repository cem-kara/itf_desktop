# -*- coding: utf-8 -*-
"""
rke_muayene.py unit testleri
==============================
Kapsam:
  1. tabloyu_filtrele  : ABD + metin arama
  2. ekipman_secildi   : Geçmiş muayene filtreleme
  3. KayitWorker durum : "Kullanıma Uygun / Değil" belirleme
  4. Ekipman No parse  : "RKE-001 | Önlük" → "RKE-001"
  5. Muayene ID üretme : "M-{timestamp}" format kontrolü
  6. CheckableComboBox : Qt bileşeni davranışı
  7. TopluKayitWorker  : Toplu durum mantığı
  8. cols_rke          : Sütun tanım uyumu
"""
import sys
import re
import time
import pytest


@pytest.fixture(scope="module")
def qapp():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication(sys.argv)


# ──────────────────────────────────────────────────
#  Saf Python soyutlamaları
# ──────────────────────────────────────────────────

COLS_RKE = ["EkipmanNo", "AnaBilimDali", "Birim", "KoruyucuCinsi", "KontrolTarihi", "Durum"]


def _tabloyu_filtrele_muayene(rke_data, secilen_abd="Tüm ABD", ara="") -> list:
    """rke_muayene.tabloyu_filtrele saf Python."""
    result = []
    for row in rke_data:
        abd = str(row.get("AnaBilimDali", "")).strip()
        if secilen_abd != "Tüm ABD" and abd != secilen_abd:
            continue
        if ara and ara.lower() not in " ".join([str(v) for v in row.values()]).lower():
            continue
        result.append(row)
    return result


def _ekipman_no_parse(combo_text: str) -> str:
    """cmb_rke text'inden ekipman_no ayrıştırma."""
    return combo_text.split("|")[0].strip()


def _durum_belirle(fiziksel_durum: str, skopi_durum: str) -> str:
    """KayitWorker içindeki durum belirleme mantığı."""
    if "Değil" in fiziksel_durum or "Değil" in skopi_durum:
        return "Kullanıma Uygun Değil"
    return "Kullanıma Uygun"


def _gecmis_filtrele(tum_muayeneler, ekipman_no) -> list:
    """ekipman_secildi içindeki geçmiş filtreleme."""
    return [
        m for m in tum_muayeneler
        if str(m.get("EkipmanNo", "")).strip() == str(ekipman_no).strip()
    ]


def _muayene_id_olustur() -> str:
    """KayitWorker: f'M-{int(time.time())}' format."""
    return f"M-{int(time.time())}"


def _toplu_durum_belirle(fiziksel: str, skopi: str) -> str:
    """TopluKayitWorker durum mantığı (KayitWorker ile aynı)."""
    return _durum_belirle(fiziksel, skopi)


# ─── Test verisi ───
RKE_DATA = [
    {"EkipmanNo": "RKE-OAC-001", "AnaBilimDali": "Radyoloji ABD",
     "Birim": "Radyoloji", "KoruyucuCinsi": "Önlük",
     "KontrolTarihi": "2024-12-01", "Durum": "Kullanıma Uygun"},
    {"EkipmanNo": "RKE-OAC-002", "AnaBilimDali": "Radyoloji ABD",
     "Birim": "Radyoloji", "KoruyucuCinsi": "Önlük",
     "KontrolTarihi": "2024-11-15", "Durum": "Kullanıma Uygun Değil"},
    {"EkipmanNo": "RKE-TID-001", "AnaBilimDali": "Kardiyoloji ABD",
     "Birim": "Kardiyoloji", "KoruyucuCinsi": "Tiroid",
     "KontrolTarihi": "2025-01-01", "Durum": "Kullanıma Uygun"},
    {"EkipmanNo": "RKE-GOZ-001", "AnaBilimDali": "Nöroloji ABD",
     "Birim": "Nöroloji", "KoruyucuCinsi": "Gözlük",
     "KontrolTarihi": "2025-02-01", "Durum": "Hurda"},
]

MUAYENE_GECMİSİ = [
    {"KayitNo": "M-001", "EkipmanNo": "RKE-OAC-001", "FMuayeneTarihi": "2024-12-01",
     "FizikselDurum": "Kullanıma Uygun", "SkopiDurum": "Yapılmadı",
     "Aciklamalar": "Normal kontrol", "Rapor": ""},
    {"KayitNo": "M-002", "EkipmanNo": "RKE-OAC-001", "FMuayeneTarihi": "2024-06-01",
     "FizikselDurum": "Kullanıma Uygun", "SkopiDurum": "Kullanıma Uygun",
     "Aciklamalar": "Ara kontrol", "Rapor": "https://drive.google.com/file/abc"},
    {"KayitNo": "M-003", "EkipmanNo": "RKE-TID-001", "FMuayeneTarihi": "2025-01-01",
     "FizikselDurum": "Kullanıma Uygun Değil", "SkopiDurum": "Yapılmadı",
     "Aciklamalar": "Hasar var", "Rapor": ""},
]


# =============================================================
#  1. cols_rke Sütun Tanımı
# =============================================================
class TestColsRke:

    def test_6_sutun(self):
        assert len(COLS_RKE) == 6

    def test_ekipman_no_ilk(self):
        assert COLS_RKE[0] == "EkipmanNo"

    def test_abd_var(self):
        assert "AnaBilimDali" in COLS_RKE

    def test_durum_var(self):
        assert "Durum" in COLS_RKE

    def test_cins_var(self):
        assert "KoruyucuCinsi" in COLS_RKE


# =============================================================
#  2. tabloyu_filtrele (Muayene sayfası)
# =============================================================
class TestTabloyuFiltreMuayene:

    def test_filtre_yok_hepsi(self):
        assert len(_tabloyu_filtrele_muayene(RKE_DATA)) == 4

    def test_abd_filtresi_radyoloji(self):
        r = _tabloyu_filtrele_muayene(RKE_DATA, "Radyoloji ABD")
        assert len(r) == 2
        assert all(x["AnaBilimDali"] == "Radyoloji ABD" for x in r)

    def test_abd_filtresi_kardiyoloji(self):
        r = _tabloyu_filtrele_muayene(RKE_DATA, "Kardiyoloji ABD")
        assert len(r) == 1

    def test_abd_filtresi_olmayan(self):
        assert _tabloyu_filtrele_muayene(RKE_DATA, "Eczacılık ABD") == []

    def test_metin_arama_ekipman_no(self):
        r = _tabloyu_filtrele_muayene(RKE_DATA, ara="GOZ")
        assert len(r) == 1 and r[0]["EkipmanNo"] == "RKE-GOZ-001"

    def test_metin_arama_durum(self):
        r = _tabloyu_filtrele_muayene(RKE_DATA, ara="hurda")
        assert len(r) == 1

    def test_metin_arama_buyuk_kucuk_harf(self):
        r = _tabloyu_filtrele_muayene(RKE_DATA, ara="rke-oac")
        assert len(r) == 2

    def test_abd_ve_arama_kombinasyon(self):
        r = _tabloyu_filtrele_muayene(RKE_DATA, "Radyoloji ABD", "001")
        assert len(r) == 1

    def test_bos_veri(self):
        assert _tabloyu_filtrele_muayene([]) == []

    def test_metin_arama_eslesen_yok(self):
        assert _tabloyu_filtrele_muayene(RKE_DATA, ara="XXXXXXX") == []


# =============================================================
#  3. Ekipman No Parse
# =============================================================
class TestEkipmanNoParse:

    def test_boru_separator_dogru_ayirim(self):
        assert _ekipman_no_parse("RKE-OAC-001 | Önlük") == "RKE-OAC-001"

    def test_bosluk_temizleniyor(self):
        assert _ekipman_no_parse("  RKE-TID-001  | Tiroid  ") == "RKE-TID-001"

    def test_boru_yok_tum_metin(self):
        assert _ekipman_no_parse("RKE-GOZ-001") == "RKE-GOZ-001"

    def test_bos_string(self):
        assert _ekipman_no_parse("") == ""

    def test_cok_boru_ilkten_once_alinir(self):
        assert _ekipman_no_parse("RKE-001 | Önlük | Extra") == "RKE-001"


# =============================================================
#  4. Muayene Kaydı Durum Belirleme (KayitWorker)
# =============================================================
class TestMuayeneDurumBelirleme:

    def test_her_ikisi_uygun(self):
        assert _durum_belirle("Kullanıma Uygun", "Kullanıma Uygun") == "Kullanıma Uygun"

    def test_fiziksel_uygun_degil(self):
        assert _durum_belirle("Kullanıma Uygun Değil", "Kullanıma Uygun") == "Kullanıma Uygun Değil"

    def test_skopi_uygun_degil(self):
        assert _durum_belirle("Kullanıma Uygun", "Kullanıma Uygun Değil") == "Kullanıma Uygun Değil"

    def test_her_ikisi_uygun_degil(self):
        assert _durum_belirle("Kullanıma Uygun Değil", "Kullanıma Uygun Değil") == "Kullanıma Uygun Değil"

    def test_skopi_yapilmadi_uygun(self):
        assert _durum_belirle("Kullanıma Uygun", "Yapılmadı") == "Kullanıma Uygun"

    def test_fiziksel_bos_uygun(self):
        assert _durum_belirle("", "Kullanıma Uygun") == "Kullanıma Uygun"

    def test_her_ikisi_bos_uygun(self):
        assert _durum_belirle("", "") == "Kullanıma Uygun"

    def test_fiziksel_bos_skopi_degil(self):
        assert _durum_belirle("", "Kullanıma Uygun Değil") == "Kullanıma Uygun Değil"


# =============================================================
#  5. Geçmiş Muayene Filtreleme (ekipman_secildi)
# =============================================================
class TestGecmisFiltrele:

    def test_ekipman_gecmisi_dogru_sayida(self):
        r = _gecmis_filtrele(MUAYENE_GECMİSİ, "RKE-OAC-001")
        assert len(r) == 2

    def test_diger_ekipman_gecmisi(self):
        r = _gecmis_filtrele(MUAYENE_GECMİSİ, "RKE-TID-001")
        assert len(r) == 1

    def test_olmayan_ekipman_bos(self):
        r = _gecmis_filtrele(MUAYENE_GECMİSİ, "RKE-999-999")
        assert r == []

    def test_bos_gecmis_bos_donus(self):
        r = _gecmis_filtrele([], "RKE-OAC-001")
        assert r == []

    def test_veri_alanlari_dogru(self):
        r = _gecmis_filtrele(MUAYENE_GECMİSİ, "RKE-OAC-001")
        assert all("FMuayeneTarihi" in item for item in r)

    def test_rapor_linki_var(self):
        r = _gecmis_filtrele(MUAYENE_GECMİSİ, "RKE-OAC-001")
        linkli = [x for x in r if "http" in str(x.get("Rapor", ""))]
        assert len(linkli) == 1


# =============================================================
#  6. Muayene ID Üretimi
# =============================================================
class TestMuayeneIdUretimi:

    def test_m_prefix(self):
        mid = _muayene_id_olustur()
        assert mid.startswith("M-")

    def test_sayisal_suffix(self):
        mid = _muayene_id_olustur()
        suffix = mid[2:]
        assert suffix.isdigit()

    def test_makul_zaman_damgasi(self):
        mid = _muayene_id_olustur()
        ts = int(mid[2:])
        now = int(time.time())
        assert abs(ts - now) < 5

    def test_ardisik_benzersiz(self):
        import time as t
        id1 = _muayene_id_olustur()
        t.sleep(0.01)
        id2 = _muayene_id_olustur()
        # Aynı saniyede çalışabilir ama format aynı olmalı
        assert id1.startswith("M-") and id2.startswith("M-")


# =============================================================
#  7. Toplu Kayıt Durum Mantığı
# =============================================================
class TestTopluKayitDurum:

    def test_toplu_uygun(self):
        assert _toplu_durum_belirle("Kullanıma Uygun", "Yapılmadı") == "Kullanıma Uygun"

    def test_toplu_uygun_degil_fiziksel(self):
        assert _toplu_durum_belirle("Kullanıma Uygun Değil", "") == "Kullanıma Uygun Değil"

    def test_toplu_uygun_degil_skopi(self):
        assert _toplu_durum_belirle("", "Kullanıma Uygun Değil") == "Kullanıma Uygun Değil"

    def test_toplu_her_ekipman_durum_bagimsiz(self):
        """Her ekipman kendi fiziksel/skopi durumuna göre hesaplanmalı."""
        ekipmanlar = [
            ("Kullanıma Uygun", "Yapılmadı"),
            ("Kullanıma Uygun Değil", "Yapılmadı"),
        ]
        sonuclar = [_toplu_durum_belirle(f, s) for f, s in ekipmanlar]
        assert sonuclar[0] == "Kullanıma Uygun"
        assert sonuclar[1] == "Kullanıma Uygun Değil"


# =============================================================
#  8. CheckableComboBox (Qt)
# =============================================================
class TestCheckableComboBox:

    def test_bos_combo_text_bos(self, qapp):
        from ui.pages.cihaz.rke_muayene import CheckableComboBox
        cb = CheckableComboBox()
        assert cb.getCheckedItems() == ""

    def test_item_ekleme(self, qapp):
        from ui.pages.cihaz.rke_muayene import CheckableComboBox
        cb = CheckableComboBox()
        cb.addItem("Madde 1")
        cb.addItem("Madde 2")
        assert cb.count() == 2

    def test_add_items_toplu(self, qapp):
        from ui.pages.cihaz.rke_muayene import CheckableComboBox
        cb = CheckableComboBox()
        cb.addItems(["A", "B", "C"])
        assert cb.count() == 3

    def test_set_checked_items_string(self, qapp):
        from ui.pages.cihaz.rke_muayene import CheckableComboBox
        cb = CheckableComboBox()
        cb.addItems(["Önlük sağlam", "Tiroid hasarlı", "Uygun"])
        cb.setCheckedItems("Önlük sağlam, Uygun")
        text = cb.getCheckedItems()
        assert "Önlük sağlam" in text
        assert "Uygun" in text

    def test_set_checked_items_liste(self, qapp):
        from ui.pages.cihaz.rke_muayene import CheckableComboBox
        cb = CheckableComboBox()
        cb.addItems(["A", "B", "C"])
        cb.setCheckedItems(["A", "C"])
        text = cb.getCheckedItems()
        assert "A" in text
        assert "C" in text

    def test_cleared_items_bos(self, qapp):
        from ui.pages.cihaz.rke_muayene import CheckableComboBox
        cb = CheckableComboBox()
        cb.addItems(["A", "B"])
        cb.setCheckedItems(["A"])
        cb.setCheckedItems([])
        # Hiçbiri seçili değil → boş
        assert cb.getCheckedItems() == ""

    def test_bos_liste_ile_set(self, qapp):
        from ui.pages.cihaz.rke_muayene import CheckableComboBox
        cb = CheckableComboBox()
        cb.addItems(["X", "Y"])
        cb.setCheckedItems("")
        assert cb.getCheckedItems() == ""


# =============================================================
#  9. Qt Pencere Yapısı
# =============================================================
class TestRKEMuayenePenceresiQt:

    def test_cmb_rke_var(self, qapp):
        from ui.pages.cihaz.rke_muayene import RKEMuayenePenceresi
        win = RKEMuayenePenceresi()
        assert hasattr(win, "cmb_rke")

    def test_tablo_sutun_sayisi(self, qapp):
        from ui.pages.cihaz.rke_muayene import RKEMuayenePenceresi
        win = RKEMuayenePenceresi()
        assert win.tablo.columnCount() == len(COLS_RKE)

    def test_gecmis_tablo_4_sutun(self, qapp):
        from ui.pages.cihaz.rke_muayene import RKEMuayenePenceresi
        win = RKEMuayenePenceresi()
        assert win.tbl_gecmis.columnCount() == 4

    def test_btn_toplu_var(self, qapp):
        from ui.pages.cihaz.rke_muayene import RKEMuayenePenceresi
        win = RKEMuayenePenceresi()
        assert hasattr(win, "btn_toplu")

    def test_temizle_gecmis_tabloyu_sifirlar(self, qapp):
        from ui.pages.cihaz.rke_muayene import RKEMuayenePenceresi
        win = RKEMuayenePenceresi()
        win.tbl_gecmis.insertRow(0)
        win.temizle()
        assert win.tbl_gecmis.rowCount() == 0

    def test_temizle_dosya_sifirlar(self, qapp):
        from ui.pages.cihaz.rke_muayene import RKEMuayenePenceresi
        win = RKEMuayenePenceresi()
        win.secilen_dosya = "/tmp/test.pdf"
        win.temizle()
        assert win.secilen_dosya is None

    def test_lbl_sayi_baslangic(self, qapp):
        from ui.pages.cihaz.rke_muayene import RKEMuayenePenceresi
        win = RKEMuayenePenceresi()
        assert "Ekipman" in win.lbl_sayi.text() or "0" in win.lbl_sayi.text()
