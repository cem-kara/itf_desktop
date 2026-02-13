# -*- coding: utf-8 -*-
"""
database/base_repository.py için unit testler
=============================================
Kapsam:
  - insert          : tekli PK, composite PK, sync_status otomatik atama
  - update          : partial update, sync_status=dirty otomatik
  - get_by_id       : tekli ve composite PK ile getirme
  - get_all         : tüm kayıtlar
  - get_dirty       : sync_status='dirty' filtreleme
  - mark_clean      : sync_status güncelleme
  - INSERT OR REPLACE: aynı PK üzerine yazma
"""
import sqlite3
import pytest
from database.base_repository import BaseRepository


# ─────────────────────────────────────────────────────────────
#  Yardımcı: MockDB (in-memory sqlite3)
# ─────────────────────────────────────────────────────────────

class MockDB:
    """SQLiteManager arayüzünü taklit eden in-memory bağlantı."""
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


# ─────────────────────────────────────────────────────────────
#  Fixtures
# ─────────────────────────────────────────────────────────────

@pytest.fixture()
def db():
    """Her test için temiz in-memory DB."""
    _db = MockDB()
    yield _db
    _db.close()


@pytest.fixture()
def repo(db):
    """
    Tekli PK'li test tablosu:
      Kayitid | Ad | Deger | sync_status | updated_at
    """
    db.execute("""
        CREATE TABLE Test_Kayit (
            Kayitid     TEXT,
            Ad          TEXT,
            Deger       INTEGER,
            sync_status TEXT DEFAULT 'dirty',
            updated_at  TEXT,
            PRIMARY KEY (Kayitid)
        )
    """)
    return BaseRepository(
        db=db,
        table_name="Test_Kayit",
        pk="Kayitid",
        columns=["Kayitid", "Ad", "Deger", "sync_status", "updated_at"],
        has_sync=True
    )


@pytest.fixture()
def repo_no_sync(db):
    """Sync olmayan tablo (Loglar benzeri)."""
    db.execute("""
        CREATE TABLE Test_Log (
            Tarih TEXT,
            Mesaj TEXT
        )
    """)
    return BaseRepository(
        db=db,
        table_name="Test_Log",
        pk=None,
        columns=["Tarih", "Mesaj"],
        has_sync=False
    )


@pytest.fixture()
def repo_composite(db):
    """
    Composite PK'li test tablosu:
      PersonelId | Yil | Donem | Deger | sync_status | updated_at
    """
    db.execute("""
        CREATE TABLE Test_Puantaj (
            PersonelId  TEXT,
            Yil         INTEGER,
            Donem       INTEGER,
            Deger       REAL,
            sync_status TEXT DEFAULT 'dirty',
            updated_at  TEXT,
            PRIMARY KEY (PersonelId, Yil, Donem)
        )
    """)
    return BaseRepository(
        db=db,
        table_name="Test_Puantaj",
        pk=["PersonelId", "Yil", "Donem"],
        columns=["PersonelId", "Yil", "Donem", "Deger", "sync_status", "updated_at"],
        has_sync=True
    )


# =============================================================================
#  1. INSERT
# =============================================================================

class TestInsert:

    def test_temel_insert(self, repo):
        repo.insert({"Kayitid": "K1", "Ad": "Ahmet", "Deger": 10})
        row = repo.get_by_id("K1")
        assert row is not None
        assert row["Ad"] == "Ahmet"
        assert row["Deger"] == 10

    def test_sync_status_otomatik_dirty(self, repo):
        """sync_status belirtilmezse otomatik 'dirty' olmalı."""
        repo.insert({"Kayitid": "K2", "Ad": "Mehmet"})
        row = repo.get_by_id("K2")
        assert row["sync_status"] == "dirty"

    def test_sync_status_clean_korunur(self, repo):
        """Pull işlemi 'clean' gönderdiğinde korunmalı."""
        repo.insert({"Kayitid": "K3", "Ad": "Ayşe", "sync_status": "clean"})
        row = repo.get_by_id("K3")
        assert row["sync_status"] == "clean"

    def test_insert_or_replace(self, repo):
        """Aynı PK ile tekrar insert → mevcut kaydın üstüne yazar."""
        repo.insert({"Kayitid": "K4", "Ad": "Eski", "Deger": 1})
        repo.insert({"Kayitid": "K4", "Ad": "Yeni", "Deger": 99})
        all_rows = repo.get_all()
        k4_rows = [r for r in all_rows if r["Kayitid"] == "K4"]
        assert len(k4_rows) == 1
        assert k4_rows[0]["Ad"] == "Yeni"

    def test_updated_at_otomatik_doldurulur(self, repo):
        repo.insert({"Kayitid": "K5", "Ad": "Test"})
        row = repo.get_by_id("K5")
        assert row["updated_at"] is not None
        assert len(row["updated_at"]) > 0

    def test_nosync_tablo_insert(self, repo_no_sync):
        """sync_status yoksa insert yine de çalışmalı."""
        repo_no_sync.insert({"Tarih": "2025-01-01", "Mesaj": "Test log"})
        rows = repo_no_sync.get_all()
        assert len(rows) == 1
        assert rows[0]["Mesaj"] == "Test log"

    def test_composite_pk_insert(self, repo_composite):
        repo_composite.insert({"PersonelId": "P1", "Yil": 2024, "Donem": 1, "Deger": 150.0})
        row = repo_composite.get_by_id(["P1", 2024, 1])
        assert row is not None
        assert row["Deger"] == 150.0


# =============================================================================
#  2. UPDATE
# =============================================================================

class TestUpdate:

    def test_temel_update(self, repo):
        repo.insert({"Kayitid": "U1", "Ad": "Eski", "Deger": 1})
        repo.update("U1", {"Ad": "Yeni"})
        row = repo.get_by_id("U1")
        assert row["Ad"] == "Yeni"

    def test_update_sync_status_dirty_olur(self, repo):
        """Update sonrası sync_status otomatik 'dirty' olmalı."""
        repo.insert({"Kayitid": "U2", "Ad": "Test", "sync_status": "clean"})
        repo.update("U2", {"Ad": "Değişti"})
        row = repo.get_by_id("U2")
        assert row["sync_status"] == "dirty"

    def test_update_sync_status_clean_korunabilir(self, repo):
        """Pull sync_status='clean' ile update gönderdiğinde korunmalı."""
        repo.insert({"Kayitid": "U3", "Ad": "Test"})
        repo.update("U3", {"Ad": "Güncel", "sync_status": "clean"})
        row = repo.get_by_id("U3")
        assert row["sync_status"] == "clean"

    def test_partial_update_diger_alanlar_dokunulmaz(self, repo):
        """Sadece belirtilen alan güncellenmeli, diğerleri değişmemeli."""
        repo.insert({"Kayitid": "U4", "Ad": "Sabit", "Deger": 42})
        repo.update("U4", {"Deger": 99})
        row = repo.get_by_id("U4")
        assert row["Ad"] == "Sabit"
        assert row["Deger"] == 99

    def test_bos_data_gonderilirse_hicbir_sey_olmaz(self, repo):
        """Güncellenecek alan yoksa sessizce geçmeli."""
        repo.insert({"Kayitid": "U5", "Ad": "Test"})
        # PK dışında alan yok → update erken döner
        repo.update("U5", {})
        row = repo.get_by_id("U5")
        assert row is not None

    def test_composite_pk_update(self, repo_composite):
        repo_composite.insert({"PersonelId": "P2", "Yil": 2024, "Donem": 2, "Deger": 100.0})
        repo_composite.update(["P2", 2024, 2], {"Deger": 200.0})
        row = repo_composite.get_by_id(["P2", 2024, 2])
        assert row["Deger"] == 200.0

    def test_updated_at_degisir(self, repo):
        """update sonrası updated_at güncellenmeli."""
        import time
        repo.insert({"Kayitid": "U6", "Ad": "Test", "updated_at": "2020-01-01T00:00:00"})
        time.sleep(0.01)
        repo.update("U6", {"Ad": "Yeni"})
        row = repo.get_by_id("U6")
        assert row["updated_at"] != "2020-01-01T00:00:00"


# =============================================================================
#  3. GET BY ID
# =============================================================================

class TestGetById:

    def test_mevcut_kayit_getirilir(self, repo):
        repo.insert({"Kayitid": "G1", "Ad": "Bulunacak"})
        row = repo.get_by_id("G1")
        assert row is not None
        assert row["Kayitid"] == "G1"

    def test_olmayan_kayit_none_doner(self, repo):
        result = repo.get_by_id("YOK")
        assert result is None

    def test_donus_dict_tipinde(self, repo):
        repo.insert({"Kayitid": "G2", "Ad": "Dict Test"})
        row = repo.get_by_id("G2")
        assert isinstance(row, dict)

    def test_composite_pk_tekli_deger(self, repo_composite):
        repo_composite.insert({"PersonelId": "P3", "Yil": 2024, "Donem": 3, "Deger": 50.0})
        row = repo_composite.get_by_id(["P3", 2024, 3])
        assert row is not None
        assert row["Deger"] == 50.0

    def test_composite_pk_yanlis_deger_none(self, repo_composite):
        row = repo_composite.get_by_id(["P999", 2024, 1])
        assert row is None

    def test_composite_pk_dict_ile(self, repo_composite):
        repo_composite.insert({"PersonelId": "P4", "Yil": 2025, "Donem": 1, "Deger": 75.0})
        row = repo_composite.get_by_id({"PersonelId": "P4", "Yil": 2025, "Donem": 1})
        assert row is not None
        assert row["Deger"] == 75.0


# =============================================================================
#  4. GET ALL
# =============================================================================

class TestGetAll:

    def test_bos_tablo(self, repo):
        rows = repo.get_all()
        assert rows == []

    def test_tek_kayit(self, repo):
        repo.insert({"Kayitid": "A1", "Ad": "Tek"})
        rows = repo.get_all()
        assert len(rows) == 1

    def test_coklu_kayit(self, repo):
        for i in range(5):
            repo.insert({"Kayitid": f"A{i}", "Ad": f"Kayit{i}"})
        rows = repo.get_all()
        assert len(rows) == 5

    def test_donus_list_of_dict(self, repo):
        repo.insert({"Kayitid": "A10", "Ad": "Test"})
        rows = repo.get_all()
        assert isinstance(rows, list)
        assert isinstance(rows[0], dict)


# =============================================================================
#  5. GET DIRTY / MARK CLEAN
# =============================================================================

class TestSyncOperations:

    def test_get_dirty_yeni_kayit(self, repo):
        """insert sonrası kayıt dirty olmalı."""
        repo.insert({"Kayitid": "S1", "Ad": "Test"})
        dirty = repo.get_dirty()
        assert len(dirty) == 1
        assert dirty[0]["Kayitid"] == "S1"

    def test_get_dirty_clean_sonrasi_bos(self, repo):
        repo.insert({"Kayitid": "S2", "Ad": "Test"})
        repo.mark_clean("S2")
        dirty = repo.get_dirty()
        assert len(dirty) == 0

    def test_mark_clean(self, repo):
        repo.insert({"Kayitid": "S3", "Ad": "Test"})
        repo.mark_clean("S3")
        row = repo.get_by_id("S3")
        assert row["sync_status"] == "clean"

    def test_birden_fazla_dirty_filtreleme(self, repo):
        repo.insert({"Kayitid": "S4", "Ad": "A", "sync_status": "clean"})
        repo.insert({"Kayitid": "S5", "Ad": "B"})  # dirty
        repo.insert({"Kayitid": "S6", "Ad": "C"})  # dirty
        dirty = repo.get_dirty()
        ids = {r["Kayitid"] for r in dirty}
        assert "S5" in ids
        assert "S6" in ids
        assert "S4" not in ids

    def test_nosync_get_dirty_bos_doner(self, repo_no_sync):
        repo_no_sync.insert({"Tarih": "2025-01-01", "Mesaj": "log"})
        dirty = repo_no_sync.get_dirty()
        assert dirty == []

    def test_nosync_mark_clean_calisir(self, repo_no_sync):
        """has_sync=False'da mark_clean çağrısı hata vermemeli."""
        repo_no_sync.mark_clean("herhangi_bir_deger")  # sessizce geçmeli

    def test_composite_pk_mark_clean(self, repo_composite):
        repo_composite.insert({"PersonelId": "P5", "Yil": 2024, "Donem": 4, "Deger": 10.0})
        repo_composite.mark_clean(["P5", 2024, 4])
        row = repo_composite.get_by_id(["P5", 2024, 4])
        assert row["sync_status"] == "clean"


# =============================================================================
#  6. PK HELPERS
# =============================================================================

class TestPkHelpers:

    def test_pk_property_tekli(self, repo):
        assert repo.pk == "Kayitid"

    def test_pk_property_composite(self, repo_composite):
        assert repo_composite.pk == ["PersonelId", "Yil", "Donem"]

    def test_is_composite_tekli(self, repo):
        assert repo.is_composite is False

    def test_is_composite_composite(self, repo_composite):
        assert repo_composite.is_composite is True

    def test_pk_key_tekli(self, repo):
        key = repo._pk_key({"Kayitid": "K1", "Ad": "Test"})
        assert key == "K1"

    def test_pk_key_composite(self, repo_composite):
        key = repo_composite._pk_key({"PersonelId": "P1", "Yil": 2024, "Donem": 1})
        assert key == "P1|2024|1"

    def test_resolve_pk_params_string(self, repo):
        params = repo._resolve_pk_params("K1")
        assert params == ["K1"]

    def test_resolve_pk_params_list(self, repo_composite):
        params = repo_composite._resolve_pk_params(["P1", 2024, 1])
        assert params == ["P1", 2024, 1]

    def test_resolve_pk_params_dict(self, repo_composite):
        params = repo_composite._resolve_pk_params(
            {"PersonelId": "P1", "Yil": 2024, "Donem": 1}
        )
        assert params == ["P1", 2024, 1]
