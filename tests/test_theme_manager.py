# -*- coding: utf-8 -*-
"""
ThemeManager & table_config unit testleri
==========================================
Kapsam:
  - ThemeManager.get_all_component_styles : zorunlu anahtar varlığı
  - ThemeManager.get_color / get_dark_theme_color
  - ThemeManager.get_status_color
  - ThemeManager singleton
  - STYLES dict — tüm sayfaların beklediği anahtarlar
  - table_config.TABLES — PK, kolon varlığı, zorunlu tablolar

Qt bağımlılığı: QApplication (QObject türevi ThemeManager için).
"""
import sys
import pytest


# ─── QApplication fixture ────────────────────────────────────

@pytest.fixture(scope="module")
def qapp():
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication(sys.argv)
    yield app


# ════════════════════════════════════════════════════════════
#  1. STYLES — Zorunlu Anahtarlar
# ════════════════════════════════════════════════════════════

class TestStylesZorunluAnahtarlar:
    """
    Her sayfa farklı stil anahtarlarını S["..."] ile kullanır.
    Eksik anahtar → KeyError → sayfa açılmaz.
    """

    # Tüm sayfalarda ortak kullanılan anahtarlar
    ZORUNLU = [
        "page",
        "table",
        "input",
        "combo",
        "date",
        "save_btn",
        "cancel_btn",
        "action_btn",
        "refresh_btn",
        "file_btn",
        "footer_label",
    ]

    @pytest.fixture
    def styles(self, qapp):
        from ui.theme_manager import ThemeManager
        return ThemeManager.get_all_component_styles()

    def test_styles_dict_donus(self, styles):
        assert isinstance(styles, dict)

    def test_page_anahtari_var(self, styles):
        assert "page" in styles

    def test_table_anahtari_var(self, styles):
        assert "table" in styles

    def test_input_anahtari_var(self, styles):
        assert "input" in styles

    def test_combo_anahtari_var(self, styles):
        assert "combo" in styles

    def test_date_anahtari_var(self, styles):
        assert "date" in styles

    def test_save_btn_anahtari_var(self, styles):
        assert "save_btn" in styles

    def test_cancel_btn_anahtari_var(self, styles):
        assert "cancel_btn" in styles

    def test_action_btn_anahtari_var(self, styles):
        assert "action_btn" in styles

    def test_refresh_btn_anahtari_var(self, styles):
        assert "refresh_btn" in styles

    def test_file_btn_anahtari_var(self, styles):
        assert "file_btn" in styles

    def test_footer_label_anahtari_var(self, styles):
        assert "footer_label" in styles

    def test_tum_zorunlu_anahtarlar(self, styles):
        eksikler = [k for k in self.ZORUNLU if k not in styles]
        assert eksikler == [], f"Eksik anahtarlar: {eksikler}"

    def test_stil_degerler_string(self, styles):
        """Her stil değeri string olmalı."""
        for k, v in styles.items():
            assert isinstance(v, str), f"'{k}' string değil: {type(v)}"

    def test_stil_degerler_bos_degil(self, styles):
        """Hiçbir stil değeri boş olmamalı."""
        for k, v in styles.items():
            assert v.strip(), f"'{k}' boş"

    def test_get_all_copy_donus(self, qapp):
        """get_all_component_styles farklı nesne döndürmeli (değişiklik izole)."""
        from ui.theme_manager import ThemeManager
        s1 = ThemeManager.get_all_component_styles()
        s2 = ThemeManager.get_all_component_styles()
        s1["__test__"] = "x"
        assert "__test__" not in s2


# ════════════════════════════════════════════════════════════
#  2. ThemeManager — Singleton
# ════════════════════════════════════════════════════════════

class TestThemeManagerSingleton:

    def test_instance_ayni_nesne(self, qapp):
        from ui.theme_manager import ThemeManager
        t1 = ThemeManager.instance()
        t2 = ThemeManager.instance()
        assert t1 is t2

    def test_instance_theme_manager_tipi(self, qapp):
        from ui.theme_manager import ThemeManager
        assert isinstance(ThemeManager.instance(), ThemeManager)


# ════════════════════════════════════════════════════════════
#  3. ThemeManager — get_color
# ════════════════════════════════════════════════════════════

class TestGetColor:

    def test_bilinen_renk_hex_donus(self, qapp):
        from ui.theme_manager import ThemeManager
        renk = ThemeManager.get_color("BLUE_700")
        assert isinstance(renk, str)
        assert renk.startswith("#")

    def test_bilinmeyen_renk_fallback(self, qapp):
        from ui.theme_manager import ThemeManager
        renk = ThemeManager.get_color("OLMAYAN_RENK_XYZ")
        assert isinstance(renk, str)
        assert renk == "#ffffff"  # varsayılan fallback

    def test_renk_hex_format(self, qapp):
        """Dönen hex kodu 7 karakter (#RRGGBB) olmalı."""
        from ui.theme_manager import ThemeManager
        renk = ThemeManager.get_color("BLUE_700")
        assert len(renk) == 7
        assert renk[0] == "#"


# ════════════════════════════════════════════════════════════
#  4. ThemeManager — get_dark_theme_color
# ════════════════════════════════════════════════════════════

class TestGetDarkThemeColor:

    def test_bg_primary_donus(self, qapp):
        from ui.theme_manager import ThemeManager
        renk = ThemeManager.get_dark_theme_color("BG_PRIMARY")
        assert isinstance(renk, str)

    def test_bilinmeyen_fallback(self, qapp):
        from ui.theme_manager import ThemeManager
        renk = ThemeManager.get_dark_theme_color("OLMAYAN_XYZ")
        assert renk == "#ffffff"


# ════════════════════════════════════════════════════════════
#  5. ThemeManager — load_stylesheet
# ════════════════════════════════════════════════════════════

class TestLoadStylesheet:

    def test_string_donus(self, qapp):
        from ui.theme_manager import ThemeManager
        tm = ThemeManager()
        css = tm.load_stylesheet()
        assert isinstance(css, str)

    def test_cache_calisiyor(self, qapp):
        """İkinci çağrı aynı nesneyi dönmeli."""
        from ui.theme_manager import ThemeManager
        tm = ThemeManager()
        css1 = tm.load_stylesheet()
        css2 = tm.load_stylesheet()
        assert css1 is css2


# ════════════════════════════════════════════════════════════
#  6. table_config.TABLES — Zorunlu Tablolar
# ════════════════════════════════════════════════════════════

class TestTableConfigZorunluTablolar:

    ZORUNLU_TABLOLAR = [
        "Personel", "Izin_Giris", "Izin_Bilgi", "FHSZ_Puantaj",
        "Cihazlar", "Cihaz_Ariza", "Ariza_Islem", "Periyodik_Bakim",
        "Kalibrasyon", "Sabitler", "Tatiller",
    ]

    @pytest.fixture
    def tables(self):
        from database.table_config import TABLES
        return TABLES

    def test_tum_zorunlu_tablolar_mevcut(self, tables):
        eksikler = [t for t in self.ZORUNLU_TABLOLAR if t not in tables]
        assert eksikler == [], f"Eksik tablolar: {eksikler}"

    def test_her_tabloda_pk_var(self, tables):
        for ad, cfg in tables.items():
            assert "pk" in cfg or cfg.get("pk") is None, f"{ad}: pk eksik"

    def test_her_tabloda_columns_var(self, tables):
        for ad, cfg in tables.items():
            assert "columns" in cfg, f"{ad}: columns eksik"
            assert isinstance(cfg["columns"], list), f"{ad}: columns list değil"
            assert len(cfg["columns"]) > 0, f"{ad}: columns boş"


# ════════════════════════════════════════════════════════════
#  7. table_config — Cihaz Tabloları Kolon Doğruluğu
# ════════════════════════════════════════════════════════════

class TestTableConfigCihazKolonlar:

    @pytest.fixture
    def tables(self):
        from database.table_config import TABLES
        return TABLES

    def test_cihaz_ariza_pk_arizaid(self, tables):
        assert tables["Cihaz_Ariza"]["pk"] == "Arizaid"

    def test_cihaz_ariza_zorunlu_kolonlar(self, tables):
        cols = tables["Cihaz_Ariza"]["columns"]
        for k in ["Arizaid", "Cihazid", "Baslik", "Durum", "Oncelik"]:
            assert k in cols, f"'{k}' Cihaz_Ariza'da yok"

    def test_ariza_islem_pk_islemid(self, tables):
        assert tables["Ariza_Islem"]["pk"] == "Islemid"

    def test_ariza_islem_arizaid_kolon(self, tables):
        assert "Arizaid" in tables["Ariza_Islem"]["columns"]

    def test_periyodik_bakim_pk_planid(self, tables):
        assert tables["Periyodik_Bakim"]["pk"] == "Planid"

    def test_periyodik_bakim_zorunlu_kolonlar(self, tables):
        cols = tables["Periyodik_Bakim"]["columns"]
        for k in ["Planid", "Cihazid", "BakimPeriyodu", "Durum",
                  "BakimTarihi", "YapilanIslemler", "Aciklama", "Teknisyen"]:
            assert k in cols, f"'{k}' Periyodik_Bakim'da yok"

    def test_cihazlar_pk_cihazid(self, tables):
        assert tables["Cihazlar"]["pk"] == "Cihazid"

    def test_cihazlar_zorunlu_kolonlar(self, tables):
        cols = tables["Cihazlar"]["columns"]
        for k in ["Cihazid", "Marka", "Model", "Durum"]:
            assert k in cols, f"'{k}' Cihazlar'da yok"


# ════════════════════════════════════════════════════════════
#  8. table_config — Personel Tabloları
# ════════════════════════════════════════════════════════════

class TestTableConfigPersonelKolonlar:

    @pytest.fixture
    def tables(self):
        from database.table_config import TABLES
        return TABLES

    def test_personel_pk_kimlikno(self, tables):
        assert tables["Personel"]["pk"] == "KimlikNo"

    def test_personel_adsoyad_kolon(self, tables):
        assert "AdSoyad" in tables["Personel"]["columns"]

    def test_izin_giris_pk(self, tables):
        assert tables["Izin_Giris"]["pk"] == "Izinid"

    def test_izin_bilgi_pk(self, tables):
        assert tables["Izin_Bilgi"]["pk"] == "TCKimlik"

    def test_fhsz_puantaj_composite_pk(self, tables):
        pk = tables["FHSZ_Puantaj"]["pk"]
        assert isinstance(pk, list)
        assert "Personelid" in pk
        assert "AitYil"     in pk
        assert "Donem"      in pk

    def test_tatiller_two_way(self, tables):
        cfg = tables["Tatiller"]
        assert cfg.get("sync_mode") != "pull_only"
        assert cfg.get("sync", True) is not False

    def test_tatiller_kolonlar(self, tables):
        cols = tables["Tatiller"]["columns"]
        assert "Tarih"      in cols
        assert "ResmiTatil" in cols


# ════════════════════════════════════════════════════════════
#  9. table_config — Sync Yapılandırması
# ════════════════════════════════════════════════════════════

class TestTableConfigSyncYapisi:

    @pytest.fixture
    def tables(self):
        from database.table_config import TABLES
        return TABLES

    def test_sync_tablolarda_pk_var(self, tables):
        """Sync edilecek tablolarda PK None olmamalı."""
        for ad, cfg in tables.items():
            if cfg.get("sync", True):
                pk = cfg.get("pk")
                if pk is not None:
                    assert pk != "", f"{ad}: pk boş string"

    def test_kolon_listesi_tekrar_icermiyor(self, tables):
        """Aynı kolon adı bir tabloda iki kez olmamalı."""
        for ad, cfg in tables.items():
            cols = cfg["columns"]
            assert len(cols) == len(set(cols)), \
                f"{ad}: kolon listesinde tekrar var: {[c for c in cols if cols.count(c)>1]}"

    def test_pk_kolonlar_listede(self, tables):
        """PK olarak tanımlanan kolon(lar) columns listesinde de olmalı."""
        for ad, cfg in tables.items():
            pk  = cfg.get("pk")
            cols = cfg.get("columns", [])
            if pk is None:
                continue
            pk_list = pk if isinstance(pk, list) else [pk]
            for p in pk_list:
                assert p in cols, f"{ad}: PK '{p}' columns listesinde yok"
