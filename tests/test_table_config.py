# -*- coding: utf-8 -*-
"""
table_config.py kapsamlı doğrulama testleri
============================================
Kapsam:
  - Tüm tablolar mevcut
  - PK tanımları doğru
  - Kolon listeleri eksiksiz
  - sync_mode / sync / has_sync alanları
  - Composite PK yapısı
  - Migrations ile PK uyumu
"""
import pytest


@pytest.fixture(scope="module")
def tables():
    from database.table_config import TABLES
    return TABLES


# =============================================================
#  1. Tablo Varlık Kontrolü
# =============================================================
class TestTabloVarlik:

    BEKLENEN_TABLOLAR = [
        "Personel", "Izin_Giris", "Izin_Bilgi", "FHSZ_Puantaj",
        "Cihazlar", "Cihaz_Ariza", "Ariza_Islem", "Periyodik_Bakim",
        "Kalibrasyon", "Sabitler", "Tatiller", "Loglar",
        "RKE_List", "RKE_Muayene",
    ]

    def test_tum_tablolar_mevcut(self, tables):
        for tablo in self.BEKLENEN_TABLOLAR:
            assert tablo in tables, f"Eksik tablo: {tablo}"

    def test_toplam_tablo_sayisi_yeterli(self, tables):
        assert len(tables) >= 14

    def test_her_tablonun_pk_alani_var(self, tables):
        for ad, cfg in tables.items():
            assert "pk" in cfg, f"{ad}: 'pk' anahtarı yok"

    def test_her_tablonun_columns_alani_var(self, tables):
        for ad, cfg in tables.items():
            assert "columns" in cfg, f"{ad}: 'columns' anahtarı yok"

    def test_her_tablonun_columns_bos_degil(self, tables):
        for ad, cfg in tables.items():
            assert len(cfg["columns"]) > 0, f"{ad}: columns listesi boş"


# =============================================================
#  2. PK Tanımları
# =============================================================
class TestPkTanimlari:

    def test_personel_pk(self, tables):
        assert tables["Personel"]["pk"] == "KimlikNo"

    def test_izin_giris_pk(self, tables):
        assert tables["Izin_Giris"]["pk"] == "Izinid"

    def test_izin_bilgi_pk(self, tables):
        assert tables["Izin_Bilgi"]["pk"] == "TCKimlik"

    def test_fhsz_puantaj_composite_pk(self, tables):
        pk = tables["FHSZ_Puantaj"]["pk"]
        assert isinstance(pk, list)
        assert "Personelid" in pk
        assert "AitYil" in pk
        assert "Donem" in pk

    def test_cihazlar_pk(self, tables):
        assert tables["Cihazlar"]["pk"] == "Cihazid"

    def test_cihaz_ariza_pk(self, tables):
        assert tables["Cihaz_Ariza"]["pk"] == "Arizaid"

    def test_ariza_islem_pk(self, tables):
        assert tables["Ariza_Islem"]["pk"] == "Islemid"

    def test_periyodik_bakim_pk(self, tables):
        assert tables["Periyodik_Bakim"]["pk"] == "Planid"

    def test_kalibrasyon_pk(self, tables):
        assert tables["Kalibrasyon"]["pk"] == "Kalid"

    def test_sabitler_pk(self, tables):
        assert tables["Sabitler"]["pk"] == "Rowid"

    def test_tatiller_pk(self, tables):
        assert tables["Tatiller"]["pk"] == "Tarih"

    def test_loglar_pk_none(self, tables):
        assert tables["Loglar"]["pk"] is None

    def test_rke_list_pk(self, tables):
        assert tables["RKE_List"]["pk"] == "KayitNo"

    def test_rke_muayene_pk(self, tables):
        assert tables["RKE_Muayene"]["pk"] == "KayitNo"


# =============================================================
#  3. Kritik Kolon Varlığı
# =============================================================
class TestKritikKolonlar:

    def test_personel_kimlik_no(self, tables):
        assert "KimlikNo" in tables["Personel"]["columns"]

    def test_personel_adsoyad(self, tables):
        assert "AdSoyad" in tables["Personel"]["columns"]

    def test_personel_durum(self, tables):
        assert "Durum" in tables["Personel"]["columns"]

    def test_izin_giris_personelid(self, tables):
        assert "Personelid" in tables["Izin_Giris"]["columns"]

    def test_izin_giris_durum(self, tables):
        assert "Durum" in tables["Izin_Giris"]["columns"]

    def test_izin_giris_tarihler(self, tables):
        cols = tables["Izin_Giris"]["columns"]
        assert "BaslamaTarihi" in cols
        assert "BitisTarihi" in cols

    def test_izin_bilgi_yillik_alanlar(self, tables):
        cols = tables["Izin_Bilgi"]["columns"]
        assert "YillikKullanilan" in cols
        assert "YillikKalan" in cols

    def test_izin_bilgi_sua_alanlar(self, tables):
        cols = tables["Izin_Bilgi"]["columns"]
        assert "SuaKullanilan" in cols
        assert "SuaKalan" in cols

    def test_fhsz_puantaj_aylik_gun(self, tables):
        assert "AylikGun" in tables["FHSZ_Puantaj"]["columns"]

    def test_fhsz_puantaj_fiili_calisma(self, tables):
        assert "FiiliCalismaSaat" in tables["FHSZ_Puantaj"]["columns"]

    def test_cihazlar_marka_model(self, tables):
        cols = tables["Cihazlar"]["columns"]
        assert "Marka" in cols
        assert "Model" in cols

    def test_cihaz_ariza_durum(self, tables):
        assert "Durum" in tables["Cihaz_Ariza"]["columns"]

    def test_kalibrasyon_bitis_tarihi(self, tables):
        assert "BitisTarihi" in tables["Kalibrasyon"]["columns"]

    def test_kalibrasyon_firma(self, tables):
        assert "Firma" in tables["Kalibrasyon"]["columns"]

    def test_rke_list_ekipman_no(self, tables):
        assert "EkipmanNo" in tables["RKE_List"]["columns"]

    def test_rke_muayene_fiziksel_durum(self, tables):
        assert "FizikselDurum" in tables["RKE_Muayene"]["columns"]

    def test_sabitler_kod_menueleman(self, tables):
        cols = tables["Sabitler"]["columns"]
        assert "Kod" in cols
        assert "MenuEleman" in cols


# =============================================================
#  4. Sync Modu Kontrolleri
# =============================================================
class TestSyncModu:

    def test_sabitler_pull_only(self, tables):
        assert tables["Sabitler"].get("sync_mode") == "pull_only"

    def test_tatiller_pull_only(self, tables):
        assert tables["Tatiller"].get("sync_mode") == "pull_only"

    def test_loglar_sync_false(self, tables):
        """Loglar sync dışı olmalı."""
        assert tables["Loglar"].get("sync") is False

    def test_personel_sync_modu_yok(self, tables):
        """Normal tablolarda sync_mode tanımlı olmamalı (varsayılan: iki yönlü sync)."""
        assert "sync_mode" not in tables["Personel"]

    def test_cihaz_ariza_sync_modu_yok(self, tables):
        assert "sync_mode" not in tables["Cihaz_Ariza"]


# =============================================================
#  5. Composite PK Yapısı
# =============================================================
class TestCompositePk:

    def test_fhsz_pk_list_degil_string_degil(self, tables):
        pk = tables["FHSZ_Puantaj"]["pk"]
        assert isinstance(pk, list)
        assert not isinstance(pk, str)

    def test_fhsz_pk_3_alan(self, tables):
        assert len(tables["FHSZ_Puantaj"]["pk"]) == 3

    def test_fhsz_pk_alanlari_columns_icerisinde(self, tables):
        pk_cols = tables["FHSZ_Puantaj"]["pk"]
        tum_cols = tables["FHSZ_Puantaj"]["columns"]
        for pk_col in pk_cols:
            assert pk_col in tum_cols, f"PK kolonu columns'da yok: {pk_col}"

    def test_diger_tablolar_tek_pk(self, tables):
        """Composite PK sadece FHSZ_Puantaj'da olmalı."""
        for ad, cfg in tables.items():
            if ad == "FHSZ_Puantaj":
                continue
            pk = cfg.get("pk")
            if pk is not None:
                assert not isinstance(pk, list), f"{ad} beklenmedik composite PK"


# =============================================================
#  6. PK değerleri columns içinde yer alıyor
# =============================================================
class TestPkColumnsUyumu:

    def test_her_string_pk_columns_icerisinde(self, tables):
        for ad, cfg in tables.items():
            pk = cfg.get("pk")
            if pk is None or isinstance(pk, list):
                continue
            assert pk in cfg["columns"], \
                f"{ad}: PK '{pk}' columns içinde yok"
