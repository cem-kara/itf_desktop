# -*- coding: utf-8 -*-
"""
database/repository_registry.py için unit testler
==================================================
Kapsam:
  - get()            : repo oluşturma, aynı repo'nun cachelenmesi
  - all_syncable()   : sadece sync=True ve pk!=None tabloları
  - all()            : tüm tablolar
  - has_sync flag    : sync=False ve pk=None tablolar için has_sync=False
"""
import sqlite3
import pytest
from database.repository_registry import RepositoryRegistry
from database.table_config import TABLES


# ─────────────────────────────────────────────────────────────
#  MockDB
# ─────────────────────────────────────────────────────────────

class MockDB:
    def __init__(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row

    def execute(self, sql, params=()):
        cur = self.conn.cursor()
        cur.execute(sql, params)
        self.conn.commit()
        return cur

    def close(self):
        self.conn.close()


@pytest.fixture()
def db():
    _db = MockDB()
    yield _db
    _db.close()


@pytest.fixture()
def registry(db):
    return RepositoryRegistry(db)


# =============================================================================
#  1. get()
# =============================================================================

class TestRegistryGet:

    def test_bilinen_tablo_donduruluyor(self, registry):
        repo = registry.get("Tatiller")
        assert repo is not None

    def test_cihazlar_tablosu_donduruluyor(self, registry):
        repo = registry.get("Cihazlar")
        assert repo is not None
        assert repo.table == "Cihazlar"

    def test_personel_tablosu_pk_dogru(self, registry):
        repo = registry.get("Personel")
        assert repo.pk == "KimlikNo"

    def test_composite_pk_fhsz(self, registry):
        repo = registry.get("FHSZ_Puantaj")
        assert repo.is_composite is True
        assert set(repo.pk_list) == {"Personelid", "AitYil", "Donem"}

    def test_ayni_tablo_iki_kere_ayni_nesne(self, registry):
        """Aynı tablo ikinci kez istendiğinde cache'den dönmeli."""
        repo1 = registry.get("Cihazlar")
        repo2 = registry.get("Cihazlar")
        assert repo1 is repo2

    def test_farkli_tablolar_farkli_nesneler(self, registry):
        repo_cihaz = registry.get("Cihazlar")
        repo_ariza = registry.get("Cihaz_Ariza")
        assert repo_cihaz is not repo_ariza

    def test_bilinmeyen_tablo_key_error(self, registry):
        with pytest.raises(KeyError):
            registry.get("YokTablo_XYZ")


# =============================================================================
#  2. has_sync flag
# =============================================================================

class TestHasSyncFlag:

    def test_loglar_has_sync_false(self, registry):
        """Loglar tablosu sync=False olmalı."""
        repo = registry.get("Loglar")
        assert repo.has_sync is False

    def test_tatiller_pk_var_sync_true(self, registry):
        """Tatiller pk='Tarih' → syncable."""
        repo = registry.get("Tatiller")
        # Tatiller'de sync_mode='pull_only' var ama "sync" anahtarı yok → True
        assert repo.has_sync is True

    def test_personel_has_sync_true(self, registry):
        repo = registry.get("Personel")
        assert repo.has_sync is True

    def test_cihazlar_has_sync_true(self, registry):
        repo = registry.get("Cihazlar")
        assert repo.has_sync is True


# =============================================================================
#  3. Kolon listesi
# =============================================================================

class TestColumns:

    def test_sync_tablosunda_sync_kolonlari_eklenir(self, registry):
        """has_sync=True tablolarda sync_status ve updated_at eklenmiş olmalı."""
        repo = registry.get("Cihazlar")
        assert "sync_status" in repo.columns
        assert "updated_at" in repo.columns

    def test_nosync_tablosunda_sync_kolonlari_yok(self, registry):
        """has_sync=False tablolarda sync_status eklenmemeli."""
        repo = registry.get("Loglar")
        assert "sync_status" not in repo.columns
        assert "updated_at" not in repo.columns

    def test_periyodik_bakim_kolonlari(self, registry):
        repo = registry.get("Periyodik_Bakim")
        beklenen = ["Planid", "Cihazid", "BakimPeriyodu", "BakimSirasi",
                    "PlanlananTarih", "Bakim", "Durum", "BakimTarihi",
                    "BakimTipi", "YapilanIslemler", "Aciklama", "Teknisyen", "Rapor"]
        for kolon in beklenen:
            assert kolon in repo.columns, f"Eksik kolon: {kolon}"

    def test_cihaz_ariza_kolonlari(self, registry):
        repo = registry.get("Cihaz_Ariza")
        beklenen = ["Arizaid", "Cihazid", "BaslangicTarihi", "ArizaTipi",
                    "Oncelik", "Baslik", "Durum"]
        for kolon in beklenen:
            assert kolon in repo.columns, f"Eksik kolon: {kolon}"


# =============================================================================
#  4. all_syncable() / all()
# =============================================================================

class TestRegistryCollections:

    def test_all_syncable_loglar_disinda(self, registry):
        """Loglar (sync=False) all_syncable'da olmamalı."""
        syncable = registry.all_syncable()
        assert "Loglar" not in syncable

    def test_all_syncable_personel_var(self, registry):
        syncable = registry.all_syncable()
        assert "Personel" in syncable

    def test_all_syncable_cihazlar_var(self, registry):
        syncable = registry.all_syncable()
        assert "Cihazlar" in syncable

    def test_all_kapsami(self, registry):
        """all() tüm TABLES anahtarlarını içermeli."""
        all_repos = registry.all()
        for table_name in TABLES:
            assert table_name in all_repos

    def test_all_syncable_dict_tipinde(self, registry):
        result = registry.all_syncable()
        assert isinstance(result, dict)

    def test_all_dict_tipinde(self, registry):
        result = registry.all()
        assert isinstance(result, dict)

    def test_all_repo_nesneleri_correct_table(self, registry):
        """all() içindeki her repo kendi tablosunu göstermeli."""
        from database.base_repository import BaseRepository
        all_repos = registry.all()
        for name, repo in all_repos.items():
            assert isinstance(repo, BaseRepository)
            assert repo.table == name
