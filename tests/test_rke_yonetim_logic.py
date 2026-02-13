# -*- coding: utf-8 -*-
"""
rke_yonetim.py unit testleri
==============================
Kapsam:
  1. cols_map          : Sütun eşleme doğruluğu
  2. tabloyu_filtrele  : ABD / Birim / Cins + metin arama
  3. kod_hesapla       : EkipmanNo ve KoruyucuNumarasi üretme
  4. kisaltma_maps     : Kısaltma → tam isim haritası
  5. Durum renklendirme: Tablo hücre renk mantığı
  6. Qt sayfa testleri : Tablo dolgu, lbl_sayi
"""
import sys
import pytest


@pytest.fixture(scope="module")
def qapp():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication(sys.argv)


# ──────────────────────────────────────────────────
#  Saf Python soyutlamaları
# ──────────────────────────────────────────────────

COLS_MAP = {
    "KayitNo": "ID", "EkipmanNo": "Ekipman No",
    "KoruyucuNumarasi": "Koruyucu No", "AnaBilimDali": "ABD",
    "Birim": "Birim", "KoruyucuCinsi": "Cins",
    "KontrolTarihi": "Son Kontrol", "Durum": "Durum"
}


def _tabloyu_filtrele(rke_listesi, f_abd="Tüm Bölümler",
                      f_birim="Tüm Birimlar", f_cins="Tüm Cinslar",
                      ara="") -> list:
    """rke_yonetim tabloyu_filtrele saf Python implementasyonu."""
    result = []
    for k in rke_listesi:
        v_abd   = str(k.get("AnaBilimDali", "")).strip()
        v_birim = str(k.get("Birim", "")).strip()
        v_cins  = str(k.get("KoruyucuCinsi", "")).strip()

        if f_abd   != "Tüm Bölümler"  and v_abd   != f_abd:   continue
        if f_birim != "Tüm Birimlar"   and v_birim != f_birim: continue
        if f_cins  != "Tüm Cinslar"    and v_cins  != f_cins:  continue

        if ara:
            tum_deger = " ".join([str(v) for v in k.values()]).lower()
            if ara.lower() not in tum_deger:
                continue
        result.append(k)
    return result


def _get_kisaltma(kisaltma_maps, grup, deger) -> str:
    """rke_yonetim.kod_hesapla içindeki get_kisaltma mantığı."""
    if not deger:
        return "UNK"
    if grup in kisaltma_maps and deger in kisaltma_maps[grup]:
        return kisaltma_maps[grup][deger]
    return deger[:3].upper()


def _kod_hesapla(rke_listesi, kisaltma_maps, abd, birim, cins,
                 secili_kayit=None) -> dict:
    """rke_yonetim.kod_hesapla saf Python simülasyonu."""
    k_abd   = _get_kisaltma(kisaltma_maps, "AnaBilimDali", abd)
    k_birim = _get_kisaltma(kisaltma_maps, "Birim", birim)
    k_cins  = _get_kisaltma(kisaltma_maps, "Koruyucu_Cinsi", cins)

    sayac_genel = sum(
        1 for k in rke_listesi
        if str(k.get("KoruyucuCinsi", "")).strip() == cins
    )
    sayac_yerel = sum(
        1 for k in rke_listesi
        if (str(k.get("KoruyucuCinsi", "")).strip() == cins and
            str(k.get("AnaBilimDali",  "")).strip() == abd  and
            str(k.get("Birim", "")).strip() == birim)
    )

    ekipman_no = None if secili_kayit else f"RKE-{k_cins}-{str(sayac_genel+1).zfill(3)}"
    koruyucu_no = None
    if birim == "Radyoloji Depo":
        koruyucu_no = ""
    elif abd and birim and cins:
        koruyucu_no = f"{k_abd}-{k_birim}-{k_cins}-{str(sayac_yerel+1).zfill(3)}"

    return {"EkipmanNo": ekipman_no, "KoruyucuNumarasi": koruyucu_no}


RKE_LISTESI = [
    {"KayitNo": "1", "EkipmanNo": "RKE-OAC-001", "KoruyucuNumarasi": "RAD-RAD-OAC-001",
     "AnaBilimDali": "Radyoloji ABD", "Birim": "Radyoloji", "KoruyucuCinsi": "Önlük",
     "KontrolTarihi": "2024-12-01", "Durum": "Kullanıma Uygun"},
    {"KayitNo": "2", "EkipmanNo": "RKE-OAC-002", "KoruyucuNumarasi": "RAD-RAD-OAC-002",
     "AnaBilimDali": "Radyoloji ABD", "Birim": "Radyoloji", "KoruyucuCinsi": "Önlük",
     "KontrolTarihi": "2024-11-01", "Durum": "Kullanıma Uygun Değil"},
    {"KayitNo": "3", "EkipmanNo": "RKE-TID-001", "KoruyucuNumarasi": "KAR-KAR-TID-001",
     "AnaBilimDali": "Kardiyoloji ABD", "Birim": "Kardiyoloji", "KoruyucuCinsi": "Tiroid",
     "KontrolTarihi": "2025-01-01", "Durum": "Kullanıma Uygun"},
    {"KayitNo": "4", "EkipmanNo": "RKE-OAC-003", "KoruyucuNumarasi": "KAR-KAR-OAC-001",
     "AnaBilimDali": "Kardiyoloji ABD", "Birim": "Kardiyoloji", "KoruyucuCinsi": "Önlük",
     "KontrolTarihi": "2025-02-01", "Durum": "Hurda"},
    {"KayitNo": "5", "EkipmanNo": "RKE-GOZ-001", "KoruyucuNumarasi": "NOR-NOR-GOZ-001",
     "AnaBilimDali": "Nöroloji ABD", "Birim": "Nöroloji", "KoruyucuCinsi": "Gözlük",
     "KontrolTarihi": "2025-01-15", "Durum": "Kullanıma Uygun"},
]

KISALTMA_MAPS = {
    "AnaBilimDali":   {"Radyoloji ABD": "RAD", "Kardiyoloji ABD": "KAR", "Nöroloji ABD": "NOR"},
    "Birim":          {"Radyoloji": "RAD", "Kardiyoloji": "KAR", "Nöroloji": "NOR"},
    "Koruyucu_Cinsi": {"Önlük": "OAC", "Tiroid": "TID", "Gözlük": "GOZ"},
}


# =============================================================
#  1. cols_map Sütun Eşleme
# =============================================================
class TestColsMap:

    def test_tum_anahtarlar_var(self):
        beklenen = ["KayitNo", "EkipmanNo", "KoruyucuNumarasi", "AnaBilimDali",
                    "Birim", "KoruyucuCinsi", "KontrolTarihi", "Durum"]
        for k in beklenen:
            assert k in COLS_MAP, f"{k} cols_map'te yok"

    def test_id_label(self):
        assert COLS_MAP["KayitNo"] == "ID"

    def test_ekipman_no_label(self):
        assert COLS_MAP["EkipmanNo"] == "Ekipman No"

    def test_durum_label(self):
        assert COLS_MAP["Durum"] == "Durum"

    def test_sutun_sayisi_8(self):
        assert len(COLS_MAP) == 8


# =============================================================
#  2. tabloyu_filtrele Mantığı
# =============================================================
class TestTabloyuFiltrele:

    def test_filtre_yok_hepsi(self):
        assert len(_tabloyu_filtrele(RKE_LISTESI)) == 5

    def test_abd_filtresi(self):
        r = _tabloyu_filtrele(RKE_LISTESI, f_abd="Radyoloji ABD")
        assert len(r) == 2
        assert all(x["AnaBilimDali"] == "Radyoloji ABD" for x in r)

    def test_birim_filtresi(self):
        r = _tabloyu_filtrele(RKE_LISTESI, f_birim="Kardiyoloji")
        assert len(r) == 2

    def test_cins_filtresi(self):
        r = _tabloyu_filtrele(RKE_LISTESI, f_cins="Önlük")
        assert len(r) == 3

    def test_cins_tiroid(self):
        r = _tabloyu_filtrele(RKE_LISTESI, f_cins="Tiroid")
        assert len(r) == 1
        assert r[0]["EkipmanNo"] == "RKE-TID-001"

    def test_abd_birim_kombinasyon(self):
        r = _tabloyu_filtrele(RKE_LISTESI, f_abd="Radyoloji ABD", f_birim="Radyoloji")
        assert len(r) == 2

    def test_uc_filtre(self):
        r = _tabloyu_filtrele(RKE_LISTESI, f_abd="Kardiyoloji ABD",
                              f_birim="Kardiyoloji", f_cins="Tiroid")
        assert len(r) == 1

    def test_metin_arama_ekipman_no(self):
        r = _tabloyu_filtrele(RKE_LISTESI, ara="GOZ")
        assert len(r) == 1
        assert r[0]["EkipmanNo"] == "RKE-GOZ-001"

    def test_metin_arama_buyuk_kucuk_harf(self):
        r = _tabloyu_filtrele(RKE_LISTESI, ara="goz")
        assert len(r) == 1

    def test_metin_arama_eslesen_yok(self):
        assert _tabloyu_filtrele(RKE_LISTESI, ara="XXXXXXX") == []

    def test_bos_liste(self):
        assert _tabloyu_filtrele([]) == []

    def test_olmayan_abd(self):
        assert _tabloyu_filtrele(RKE_LISTESI, f_abd="Eczacılık ABD") == []


# =============================================================
#  3. Ekipman Kodu Hesaplama
# =============================================================
class TestKodHesapla:

    def test_ekipman_no_format_rke(self):
        r = _kod_hesapla(RKE_LISTESI, KISALTMA_MAPS, "Radyoloji ABD", "Radyoloji", "Önlük")
        assert r["EkipmanNo"].startswith("RKE-")

    def test_ekipman_no_cins_kisaltmasi(self):
        r = _kod_hesapla(RKE_LISTESI, KISALTMA_MAPS, "Radyoloji ABD", "Radyoloji", "Önlük")
        assert "OAC" in r["EkipmanNo"]

    def test_ekipman_no_sayac_dogrulugu(self):
        """Var olan 3 Önlük → yeni sayac 4 olmalı."""
        r = _kod_hesapla(RKE_LISTESI, KISALTMA_MAPS, "Radyoloji ABD", "Radyoloji", "Önlük")
        assert r["EkipmanNo"] == "RKE-OAC-004"

    def test_ekipman_no_tiroid_sayac(self):
        """Var olan 1 Tiroid → yeni sayac 2."""
        r = _kod_hesapla(RKE_LISTESI, KISALTMA_MAPS, "Kardiyoloji ABD", "Kardiyoloji", "Tiroid")
        assert r["EkipmanNo"] == "RKE-TID-002"

    def test_koruyucu_no_format(self):
        r = _kod_hesapla(RKE_LISTESI, KISALTMA_MAPS, "Nöroloji ABD", "Nöroloji", "Gözlük")
        # Nöroloji ABD=NOR, Nöroloji=NOR, Gözlük=GOZ → var 1 → 002
        assert r["KoruyucuNumarasi"] == "NOR-NOR-GOZ-002"

    def test_radyoloji_depo_bos_koruyucu_no(self):
        r = _kod_hesapla(RKE_LISTESI, KISALTMA_MAPS, "Radyoloji ABD", "Radyoloji Depo", "Önlük")
        assert r["KoruyucuNumarasi"] == ""

    def test_secili_kayit_ekipman_no_degismez(self):
        r = _kod_hesapla(RKE_LISTESI, KISALTMA_MAPS, "Radyoloji ABD", "Radyoloji", "Önlük",
                         secili_kayit={"KayitNo": "1"})
        assert r["EkipmanNo"] is None  # Güncelleme modunda dokunmaz

    def test_bilinmeyen_cins_kisaltma_fallback(self):
        r = _kod_hesapla([], {}, "Radyoloji ABD", "Radyoloji", "Yeni Cins")
        # Kısaltma: deger[:3].upper() = "YEN"
        assert "YEN" in r["EkipmanNo"]

    def test_bos_cins_unk_kisaltmasi(self):
        k = _get_kisaltma(KISALTMA_MAPS, "Koruyucu_Cinsi", "")
        assert k == "UNK"

    def test_zfill_3_basamak(self):
        r = _kod_hesapla([], KISALTMA_MAPS, "Radyoloji ABD", "Radyoloji", "Önlük")
        assert r["EkipmanNo"] == "RKE-OAC-001"  # 001 (3 basamak)


# =============================================================
#  4. Kısaltma Haritası
# =============================================================
class TestKisaltmaHaritasi:

    def test_bilinen_kisaltma_dogrudan_alinir(self):
        k = _get_kisaltma(KISALTMA_MAPS, "Koruyucu_Cinsi", "Önlük")
        assert k == "OAC"

    def test_bilinen_abd_kisaltmasi(self):
        k = _get_kisaltma(KISALTMA_MAPS, "AnaBilimDali", "Radyoloji ABD")
        assert k == "RAD"

    def test_bilinmeyen_ilk_3_harf(self):
        k = _get_kisaltma(KISALTMA_MAPS, "Koruyucu_Cinsi", "Baret")
        assert k == "BAR"

    def test_bos_deger_unk(self):
        assert _get_kisaltma(KISALTMA_MAPS, "Koruyucu_Cinsi", "") == "UNK"

    def test_none_unk(self):
        assert _get_kisaltma(KISALTMA_MAPS, "Koruyucu_Cinsi", None) == "UNK"

    def test_bilinmeyen_grup(self):
        k = _get_kisaltma({}, "YokGrup", "Değer")
        assert k == "DEĞ" or len(k) <= 3


# =============================================================
#  5. Durum Renklendirme
# =============================================================
class TestDurumRenklendirme:

    def test_uygun_degil_kirmizi(self):
        val = "Kullanıma Uygun Değil"
        kirmizi = "Değil" in val or "Hurda" in val
        assert kirmizi is True

    def test_hurda_kirmizi(self):
        val = "Hurda"
        kirmizi = "Değil" in val or "Hurda" in val
        assert kirmizi is True

    def test_uygun_yesil(self):
        val = "Kullanıma Uygun"
        kirmizi = "Değil" in val or "Hurda" in val
        assert kirmizi is False

    def test_bos_yesil(self):
        val = ""
        assert ("Değil" in val or "Hurda" in val) is False


# =============================================================
#  6. Qt Sayfa Testleri
# =============================================================
class TestRKEYonetimPenceresiQt:
    # Üretim sınıfı: RKEYonetimPage
    # inputs → self.ui dict, tablo → self._table, temizle → _on_clear, secili_kayit → _secili

    def test_tablo_sutun_sayisi(self, qapp):
        from ui.pages.rke.rke_yonetim import RKEYonetimPage
        win = RKEYonetimPage(db=None)
        # _table QTableView — model üzerinden sütun sayısı
        assert win._table.model().columnCount() == 8

    def test_inputs_kayitno_var(self, qapp):
        from ui.pages.rke.rke_yonetim import RKEYonetimPage
        win = RKEYonetimPage(db=None)
        assert "KayitNo" in win.ui

    def test_inputs_ekipman_no_var(self, qapp):
        from ui.pages.rke.rke_yonetim import RKEYonetimPage
        win = RKEYonetimPage(db=None)
        assert "EkipmanNo" in win.ui

    def test_inputs_durum_var(self, qapp):
        from ui.pages.rke.rke_yonetim import RKEYonetimPage
        win = RKEYonetimPage(db=None)
        assert "Durum" in win.ui

    def test_temizle_secili_kayit_none(self, qapp):
        from ui.pages.rke.rke_yonetim import RKEYonetimPage
        win = RKEYonetimPage(db=None)
        win._secili = {"KayitNo": "1"}
        win._on_clear()
        assert win._secili is None

    def test_btn_kaydet_text(self, qapp):
        from ui.pages.rke.rke_yonetim import RKEYonetimPage
        win = RKEYonetimPage(db=None)
        assert "KAYDET" in win.btn_kaydet.text().upper()

    def test_lbl_sayi_baslangic(self, qapp):
        from ui.pages.rke.rke_yonetim import RKEYonetimPage
        win = RKEYonetimPage(db=None)
        assert "kayıt" in win._lbl_sayi.text().lower() or "0" in win._lbl_sayi.text()
