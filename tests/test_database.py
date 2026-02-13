# -*- coding: utf-8 -*-
"""
database katmanı unit testleri
================================
Kapsam:
  - BaseRepository : insert, update, get_by_id, get_all,
                     get_dirty, mark_clean, composite PK,
                     sync_status mantığı, partial update
  - RepositoryRegistry : get(), singleton, all_syncable(), all()

Tüm testler in-memory SQLite kullanır — dosya I/O yoktur.
"""
import sqlite3
import pytest
from unittest.mock import MagicMock


# ─── Test fixture: sahte DB ───────────────────────────────────

class FakeDB:
    """In-memory SQLite: SQLiteManager arayüzünü taklit eder."""

    def __init__(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row

    def execute(self, sql, params=()):
        cur = self.conn.cursor()
        cur.execute(sql, params)
        self.conn.commit()
        return cur

    def executemany(self, sql, params_list):
        cur = self.conn.cursor()
        cur.executemany(sql, params_list)
        self.conn.commit()

    def close(self):
        self.conn.close()


# ─── Fixtures ────────────────────────────────────────────────

@pytest.fixture
def ariza_db():
    """Cihaz_Ariza tablosunu içeren in-memory DB + BaseRepository."""
    from database.base_repository import BaseRepository

    db = FakeDB()
    db.execute("""
        CREATE TABLE Cihaz_Ariza (
            Arizaid TEXT PRIMARY KEY,
            Cihazid TEXT,
            BaslangicTarihi TEXT,
            Saat TEXT,
            Bildiren TEXT,
            ArizaTipi TEXT,
            Oncelik TEXT,
            Baslik TEXT,
            ArizaAcikla TEXT,
            Durum TEXT,
            Rapor TEXT,
            sync_status TEXT DEFAULT 'clean',
            updated_at TEXT
        )
    """)
    columns = [
        "Arizaid", "Cihazid", "BaslangicTarihi", "Saat", "Bildiren",
        "ArizaTipi", "Oncelik", "Baslik", "ArizaAcikla", "Durum", "Rapor",
        "sync_status", "updated_at"
    ]
    repo = BaseRepository(db=db, table_name="Cihaz_Ariza",
                          pk="Arizaid", columns=columns, has_sync=True)
    yield repo, db
    db.close()


@pytest.fixture
def periyodik_db():
    """Periyodik_Bakim tablosunu içeren in-memory DB + BaseRepository."""
    from database.base_repository import BaseRepository

    db = FakeDB()
    db.execute("""
        CREATE TABLE Periyodik_Bakim (
            Planid TEXT PRIMARY KEY,
            Cihazid TEXT,
            BakimPeriyodu TEXT,
            BakimSirasi TEXT,
            PlanlananTarih TEXT,
            Bakim TEXT,
            Durum TEXT,
            BakimTarihi TEXT,
            BakimTipi TEXT,
            YapilanIslemler TEXT,
            Aciklama TEXT,
            Teknisyen TEXT,
            Rapor TEXT,
            sync_status TEXT DEFAULT 'clean',
            updated_at TEXT
        )
    """)
    columns = [
        "Planid", "Cihazid", "BakimPeriyodu", "BakimSirasi", "PlanlananTarih",
        "Bakim", "Durum", "BakimTarihi", "BakimTipi", "YapilanIslemler",
        "Aciklama", "Teknisyen", "Rapor", "sync_status", "updated_at"
    ]
    repo = BaseRepository(db=db, table_name="Periyodik_Bakim",
                          pk="Planid", columns=columns, has_sync=True)
    yield repo, db
    db.close()


@pytest.fixture
def fhsz_db():
    """Composite PK testi için FHSZ_Puantaj tablosu."""
    from database.base_repository import BaseRepository

    db = FakeDB()
    db.execute("""
        CREATE TABLE FHSZ_Puantaj (
            Personelid TEXT,
            AitYil TEXT,
            Donem TEXT,
            AdSoyad TEXT,
            Birim TEXT,
            CalismaKosulu TEXT,
            AylikGun TEXT,
            KullanilanIzin TEXT,
            FiiliCalismaSaat TEXT,
            sync_status TEXT DEFAULT 'clean',
            updated_at TEXT,
            PRIMARY KEY (Personelid, AitYil, Donem)
        )
    """)
    columns = [
        "Personelid", "AitYil", "Donem", "AdSoyad", "Birim",
        "CalismaKosulu", "AylikGun", "KullanilanIzin", "FiiliCalismaSaat",
        "sync_status", "updated_at"
    ]
    repo = BaseRepository(db=db, table_name="FHSZ_Puantaj",
                          pk=["Personelid", "AitYil", "Donem"],
                          columns=columns, has_sync=True)
    yield repo, db
    db.close()


@pytest.fixture
def no_sync_db():
    """has_sync=False tablosu (Sabitler gibi)."""
    from database.base_repository import BaseRepository

    db = FakeDB()
    db.execute("""
        CREATE TABLE Sabitler (
            Anahtar TEXT PRIMARY KEY,
            Deger TEXT
        )
    """)
    repo = BaseRepository(db=db, table_name="Sabitler",
                          pk="Anahtar", columns=["Anahtar", "Deger"],
                          has_sync=False)
    yield repo, db
    db.close()


# ════════════════════════════════════════════════════════════
#  1. BaseRepository — INSERT
# ════════════════════════════════════════════════════════════

class TestBaseRepositoryInsert:

    def test_insert_basit_kayit(self, ariza_db):
        repo, db = ariza_db
        repo.insert({
            "Arizaid": "ARZ-001", "Cihazid": "CIH-001",
            "Baslik": "Ekran Bozuk", "Durum": "Açık"
        })
        row = repo.get_by_id("ARZ-001")
        assert row is not None
        assert row["Arizaid"] == "ARZ-001"
        assert row["Baslik"] == "Ekran Bozuk"

    def test_insert_sync_status_dirty_otomatik(self, ariza_db):
        """sync_status belirtilmezse 'dirty' olmalı."""
        repo, db = ariza_db
        repo.insert({"Arizaid": "ARZ-002", "Durum": "Açık"})
        row = repo.get_by_id("ARZ-002")
        assert row["sync_status"] == "dirty"

    def test_insert_sync_status_clean_korunur(self, ariza_db):
        """Pull işlemi 'clean' gönderdiğinde bu değer korunmalı."""
        repo, db = ariza_db
        repo.insert({"Arizaid": "ARZ-003", "sync_status": "clean"})
        row = repo.get_by_id("ARZ-003")
        assert row["sync_status"] == "clean"

    def test_insert_eksik_alanlar_none_olur(self, ariza_db):
        """Belirtilmeyen kolonlar None olarak kaydedilmeli."""
        repo, db = ariza_db
        repo.insert({"Arizaid": "ARZ-004"})
        row = repo.get_by_id("ARZ-004")
        assert row["Cihazid"] is None
        assert row["Baslik"] is None

    def test_insert_or_replace_gunceller(self, ariza_db):
        """Aynı PK ile tekrar insert → REPLACE davranışı."""
        repo, db = ariza_db
        repo.insert({"Arizaid": "ARZ-005", "Baslik": "Eski"})
        repo.insert({"Arizaid": "ARZ-005", "Baslik": "Yeni"})
        row = repo.get_by_id("ARZ-005")
        assert row["Baslik"] == "Yeni"
        assert len(repo.get_all()) == 1

    def test_insert_no_sync_dirty_eklenmez(self, no_sync_db):
        """has_sync=False tablolarda sync_status set edilmemeli."""
        repo, db = no_sync_db
        repo.insert({"Anahtar": "versiyon", "Deger": "1.0"})
        row = repo.get_by_id("versiyon")
        assert row is not None
        # Kolonda sync_status yok — insert başarılı olmalı
        assert row["Anahtar"] == "versiyon"


# ════════════════════════════════════════════════════════════
#  2. BaseRepository — GET
# ════════════════════════════════════════════════════════════

class TestBaseRepositoryGet:

    def test_get_by_id_mevcut(self, ariza_db):
        repo, db = ariza_db
        repo.insert({"Arizaid": "ARZ-010", "Baslik": "Test"})
        row = repo.get_by_id("ARZ-010")
        assert row["Arizaid"] == "ARZ-010"

    def test_get_by_id_yok_none(self, ariza_db):
        repo, db = ariza_db
        assert repo.get_by_id("YOOOOOK") is None

    def test_get_all_bos_tablo(self, ariza_db):
        repo, db = ariza_db
        assert repo.get_all() == []

    def test_get_all_birden_fazla(self, ariza_db):
        repo, db = ariza_db
        for i in range(5):
            repo.insert({"Arizaid": f"ARZ-{i:03d}"})
        result = repo.get_all()
        assert len(result) == 5

    def test_get_all_dict_listesi(self, ariza_db):
        """get_all dict listesi dönmeli."""
        repo, db = ariza_db
        repo.insert({"Arizaid": "ARZ-100", "Baslik": "X"})
        result = repo.get_all()
        assert isinstance(result[0], dict)

    def test_get_by_id_dict_donus(self, ariza_db):
        """get_by_id dict dönmeli, sqlite3.Row değil."""
        repo, db = ariza_db
        repo.insert({"Arizaid": "ARZ-101"})
        row = repo.get_by_id("ARZ-101")
        assert isinstance(row, dict)


# ════════════════════════════════════════════════════════════
#  3. BaseRepository — UPDATE
# ════════════════════════════════════════════════════════════

class TestBaseRepositoryUpdate:

    def test_update_alan_guncellenir(self, ariza_db):
        repo, db = ariza_db
        repo.insert({"Arizaid": "ARZ-020", "Durum": "Açık", "Baslik": "Test"})
        repo.update("ARZ-020", {"Durum": "Kapalı (Çözüldü)"})
        row = repo.get_by_id("ARZ-020")
        assert row["Durum"] == "Kapalı (Çözüldü)"

    def test_update_diger_alanlar_korunur(self, ariza_db):
        """Güncellenmemiş alanlar değişmemeli."""
        repo, db = ariza_db
        repo.insert({"Arizaid": "ARZ-021", "Baslik": "Bozuk", "Bildiren": "Ahmet"})
        repo.update("ARZ-021", {"Durum": "İşlemde"})
        row = repo.get_by_id("ARZ-021")
        assert row["Baslik"] == "Bozuk"
        assert row["Bildiren"] == "Ahmet"

    def test_update_sync_status_dirty_olur(self, ariza_db):
        """sync_status belirtilmeden update → 'dirty' olmalı."""
        repo, db = ariza_db
        repo.insert({"Arizaid": "ARZ-022", "sync_status": "clean"})
        repo.update("ARZ-022", {"Durum": "İşlemde"})
        row = repo.get_by_id("ARZ-022")
        assert row["sync_status"] == "dirty"

    def test_update_sync_status_explicit_clean(self, ariza_db):
        """Explicit sync_status='clean' update'de korunmalı."""
        repo, db = ariza_db
        repo.insert({"Arizaid": "ARZ-023"})
        repo.update("ARZ-023", {"Durum": "Açık", "sync_status": "clean"})
        row = repo.get_by_id("ARZ-023")
        assert row["sync_status"] == "clean"

    def test_update_bos_data_etkisiz(self, ariza_db):
        """Boş dict ile update hiçbir şey yapmamalı."""
        repo, db = ariza_db
        repo.insert({"Arizaid": "ARZ-024", "Durum": "Açık"})
        repo.update("ARZ-024", {})
        row = repo.get_by_id("ARZ-024")
        assert row["Durum"] == "Açık"

    def test_update_yok_kayit_sessiz_gecilir(self, ariza_db):
        """Olmayan kayıt güncelleme exception fırlatmamalı."""
        repo, db = ariza_db
        repo.update("YOOOOOK", {"Durum": "Test"})  # exception olmamalı


# ════════════════════════════════════════════════════════════
#  4. BaseRepository — SYNC
# ════════════════════════════════════════════════════════════

class TestBaseRepositorySync:

    def test_get_dirty_bos(self, ariza_db):
        repo, db = ariza_db
        assert repo.get_dirty() == []

    def test_get_dirty_sadece_dirty(self, ariza_db):
        repo, db = ariza_db
        repo.insert({"Arizaid": "ARZ-030", "sync_status": "dirty"})
        repo.insert({"Arizaid": "ARZ-031", "sync_status": "clean"})
        dirty = repo.get_dirty()
        assert len(dirty) == 1
        assert dirty[0]["Arizaid"] == "ARZ-030"

    def test_mark_clean(self, ariza_db):
        repo, db = ariza_db
        repo.insert({"Arizaid": "ARZ-032"})
        # insert → dirty
        assert repo.get_by_id("ARZ-032")["sync_status"] == "dirty"
        repo.mark_clean("ARZ-032")
        assert repo.get_by_id("ARZ-032")["sync_status"] == "clean"

    def test_mark_clean_sonra_get_dirty_bos(self, ariza_db):
        repo, db = ariza_db
        repo.insert({"Arizaid": "ARZ-033"})
        repo.mark_clean("ARZ-033")
        assert repo.get_dirty() == []

    def test_no_sync_get_dirty_bos(self, no_sync_db):
        """has_sync=False tablolarda get_dirty [] dönmeli."""
        repo, db = no_sync_db
        result = repo.get_dirty()
        assert result == []

    def test_no_sync_mark_clean_exception_yok(self, no_sync_db):
        repo, db = no_sync_db
        repo.insert({"Anahtar": "k1", "Deger": "v1"})
        repo.mark_clean("k1")  # exception olmamalı


# ════════════════════════════════════════════════════════════
#  5. BaseRepository — Composite PK
# ════════════════════════════════════════════════════════════

class TestBaseRepositoryCompositePK:

    def test_composite_insert_ve_get(self, fhsz_db):
        repo, db = fhsz_db
        repo.insert({
            "Personelid": "P001", "AitYil": "2024", "Donem": "1",
            "AdSoyad": "Ali Veli", "FiiliCalismaSaat": "160"
        })
        row = repo.get_by_id(["P001", "2024", "1"])
        assert row is not None
        assert row["AdSoyad"] == "Ali Veli"

    def test_composite_get_by_id_dict(self, fhsz_db):
        repo, db = fhsz_db
        repo.insert({"Personelid": "P002", "AitYil": "2024", "Donem": "2"})
        row = repo.get_by_id({"Personelid": "P002", "AitYil": "2024", "Donem": "2"})
        assert row is not None

    def test_composite_update(self, fhsz_db):
        repo, db = fhsz_db
        repo.insert({
            "Personelid": "P003", "AitYil": "2024", "Donem": "1",
            "FiiliCalismaSaat": "100"
        })
        repo.update(["P003", "2024", "1"], {"FiiliCalismaSaat": "160"})
        row = repo.get_by_id(["P003", "2024", "1"])
        assert row["FiiliCalismaSaat"] == "160"

    def test_composite_mark_clean(self, fhsz_db):
        repo, db = fhsz_db
        repo.insert({"Personelid": "P004", "AitYil": "2024", "Donem": "1"})
        repo.mark_clean(["P004", "2024", "1"])
        row = repo.get_by_id(["P004", "2024", "1"])
        assert row["sync_status"] == "clean"

    def test_composite_pk_property(self, fhsz_db):
        """Composite PK'da .pk list döner."""
        repo, db = fhsz_db
        assert repo.is_composite is True
        assert isinstance(repo.pk, list)
        assert "Personelid" in repo.pk

    def test_tekli_pk_property(self, ariza_db):
        """Tekli PK'da .pk string döner."""
        repo, db = ariza_db
        assert repo.is_composite is False
        assert repo.pk == "Arizaid"

    def test_pk_key_composite(self, fhsz_db):
        repo, db = fhsz_db
        data = {"Personelid": "P001", "AitYil": "2024", "Donem": "1"}
        key = repo._pk_key(data)
        assert key == "P001|2024|1"

    def test_pk_key_tekli(self, ariza_db):
        repo, db = ariza_db
        data = {"Arizaid": "ARZ-999"}
        key = repo._pk_key(data)
        assert key == "ARZ-999"


# ════════════════════════════════════════════════════════════
#  6. RepositoryRegistry
# ════════════════════════════════════════════════════════════

class TestRepositoryRegistry:

    @pytest.fixture
    def registry_db(self):
        """RepositoryRegistry için gerçek tablo şemasıyla DB."""
        db = FakeDB()
        # FakeDB in-memory SQLite kullandığından MigrationManager uyumsuz;
        # test tablolarını doğrudan oluştur.
        db.execute("""
            CREATE TABLE IF NOT EXISTS Cihaz_Ariza (
                Arizaid TEXT PRIMARY KEY,
                Cihazid TEXT, BaslangicTarihi TEXT, Saat TEXT,
                Bildiren TEXT, ArizaTipi TEXT, Oncelik TEXT,
                Baslik TEXT, ArizaAcikla TEXT, Durum TEXT, Rapor TEXT,
                sync_status TEXT DEFAULT 'clean', updated_at TEXT
            )
        """)
        db.execute("""
            CREATE TABLE IF NOT EXISTS Ariza_Islem (
                Islemid TEXT PRIMARY KEY,
                Arizaid TEXT, Tarih TEXT, Saat TEXT, IslemYapan TEXT,
                IslemTuru TEXT, YapilanIslem TEXT, YeniDurum TEXT, Rapor TEXT,
                sync_status TEXT DEFAULT 'clean', updated_at TEXT
            )
        """)
        db.execute("""
            CREATE TABLE IF NOT EXISTS Periyodik_Bakim (
                Planid TEXT PRIMARY KEY,
                Cihazid TEXT, BakimPeriyodu TEXT, BakimSirasi TEXT,
                PlanlananTarih TEXT, Bakim TEXT, Durum TEXT,
                BakimTarihi TEXT, BakimTipi TEXT, YapilanIslemler TEXT,
                Aciklama TEXT, Teknisyen TEXT, Rapor TEXT,
                sync_status TEXT DEFAULT 'clean', updated_at TEXT
            )
        """)
        yield db
        db.close()

    def test_get_returns_repository(self, registry_db):
        from database.repository_registry import RepositoryRegistry
        registry = RepositoryRegistry(registry_db)
        repo = registry.get("Cihaz_Ariza")
        assert repo is not None
        assert repo.table == "Cihaz_Ariza"

    def test_get_singleton(self, registry_db):
        """Aynı tablo için her seferinde aynı repo nesnesi dönmeli."""
        from database.repository_registry import RepositoryRegistry
        registry = RepositoryRegistry(registry_db)
        repo1 = registry.get("Cihaz_Ariza")
        repo2 = registry.get("Cihaz_Ariza")
        assert repo1 is repo2

    def test_get_farkli_tablolar(self, registry_db):
        from database.repository_registry import RepositoryRegistry
        registry = RepositoryRegistry(registry_db)
        r1 = registry.get("Cihaz_Ariza")
        r2 = registry.get("Ariza_Islem")
        assert r1 is not r2
        assert r1.table == "Cihaz_Ariza"
        assert r2.table == "Ariza_Islem"

    def test_pk_cihaz_ariza(self, registry_db):
        from database.repository_registry import RepositoryRegistry
        registry = RepositoryRegistry(registry_db)
        repo = registry.get("Cihaz_Ariza")
        assert repo.pk == "Arizaid"

    def test_pk_ariza_islem(self, registry_db):
        from database.repository_registry import RepositoryRegistry
        registry = RepositoryRegistry(registry_db)
        repo = registry.get("Ariza_Islem")
        assert repo.pk == "Islemid"

    def test_pk_periyodik_bakim(self, registry_db):
        from database.repository_registry import RepositoryRegistry
        registry = RepositoryRegistry(registry_db)
        repo = registry.get("Periyodik_Bakim")
        assert repo.pk == "Planid"

    def test_unknown_table_raises(self, registry_db):
        from database.repository_registry import RepositoryRegistry
        registry = RepositoryRegistry(registry_db)
        with pytest.raises(KeyError):
            registry.get("OLMAYAN_TABLO")

    def test_ariza_islem_crud(self, registry_db):
        """Registry üzerinden tam CRUD döngüsü."""
        from database.repository_registry import RepositoryRegistry
        registry = RepositoryRegistry(registry_db)
        repo = registry.get("Ariza_Islem")
        repo.insert({
            "Islemid": "ISL-001",
            "Arizaid": "ARZ-001",
            "IslemYapan": "Tekniker Mehmet",
            "YeniDurum": "Kapalı (Çözüldü)"
        })
        row = repo.get_by_id("ISL-001")
        assert row["IslemYapan"] == "Tekniker Mehmet"

        repo.update("ISL-001", {"YeniDurum": "İşlemde"})
        row = repo.get_by_id("ISL-001")
        assert row["YeniDurum"] == "İşlemde"

    def test_periyodik_bakim_crud(self, registry_db):
        from database.repository_registry import RepositoryRegistry
        registry = RepositoryRegistry(registry_db)
        repo = registry.get("Periyodik_Bakim")
        repo.insert({
            "Planid": "P-001",
            "Cihazid": "CIH-001",
            "BakimPeriyodu": "3 Ay",
            "Durum": "Planlandı"
        })
        row = repo.get_by_id("P-001")
        assert row["BakimPeriyodu"] == "3 Ay"

    def test_cihaz_ariza_get_all_filtreli(self, registry_db):
        """Insert sonrası get_all doğru kayıt sayısı döner."""
        from database.repository_registry import RepositoryRegistry
        registry = RepositoryRegistry(registry_db)
        repo = registry.get("Cihaz_Ariza")
        for i in range(3):
            repo.insert({"Arizaid": f"ARZ-{i:03d}", "Durum": "Açık"})
        result = repo.get_all()
        assert len(result) == 3

    def test_dirty_sonra_clean(self, registry_db):
        """insert → dirty → mark_clean → clean döngüsü."""
        from database.repository_registry import RepositoryRegistry
        registry = RepositoryRegistry(registry_db)
        repo = registry.get("Cihaz_Ariza")
        repo.insert({"Arizaid": "ARZ-SYNC"})
        assert repo.get_by_id("ARZ-SYNC")["sync_status"] == "dirty"
        repo.mark_clean("ARZ-SYNC")
        assert repo.get_by_id("ARZ-SYNC")["sync_status"] == "clean"
        assert repo.get_dirty() == []
