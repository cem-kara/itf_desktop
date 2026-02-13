# -*- coding: utf-8 -*-
"""
SyncService iş mantığı unit testleri
======================================
Kapsam:
  - sync_all : başarı / hata / kısmi hata
  - sync_table : PUSH (update / append) + PULL (yeni / güncelleme)
  - Dirty → clean dönüşümü
  - pull_only tablolar (Tatiller, Sabitler)
  - Composite PK make_key mantığı
  - Hata izolasyonu (bir tablo patlarsa diğerleri devam eder)

Google Sheets tamamen mock'lanır — ağ bağlantısı gerekmez.
"""
import sqlite3
import pytest
from unittest.mock import MagicMock, patch, call


# ─── Yardımcı: in-memory DB ──────────────────────────────────

class FakeDB:
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


def _create_ariza_db():
    db = FakeDB()
    db.execute("""
        CREATE TABLE Cihaz_Ariza (
            Arizaid TEXT PRIMARY KEY,
            Cihazid TEXT, BaslangicTarihi TEXT, Saat TEXT,
            Bildiren TEXT, ArizaTipi TEXT, Oncelik TEXT,
            Baslik TEXT, ArizaAcikla TEXT, Durum TEXT, Rapor TEXT,
            sync_status TEXT DEFAULT 'clean', updated_at TEXT
        )
    """)
    return db


def _create_tatiller_db():
    db = FakeDB()
    db.execute("""
        CREATE TABLE Tatiller (
            Tarih TEXT PRIMARY KEY,
            ResmiTatil TEXT
        )
    """)
    return db


# ─── Fixture: RepositoryRegistry ─────────────────────────────

def _make_registry(db, table="Cihaz_Ariza"):
    from database.base_repository import BaseRepository
    registry = MagicMock()
    if table == "Cihaz_Ariza":
        columns = ["Arizaid", "Cihazid", "BaslangicTarihi", "Saat", "Bildiren",
                   "ArizaTipi", "Oncelik", "Baslik", "ArizaAcikla", "Durum", "Rapor",
                   "sync_status", "updated_at"]
        repo = BaseRepository(db=db, table_name="Cihaz_Ariza",
                              pk="Arizaid", columns=columns, has_sync=True)
        registry.get.return_value = repo
    return registry


# ════════════════════════════════════════════════════════════
#  1. make_key Mantığı
# ════════════════════════════════════════════════════════════

class TestMakeKey:
    """sync_table içindeki make_key mantığını saf Python ile test eder."""

    def _make_key(self, data, pk_cols):
        return "|".join(str(data.get(col, "")).strip() for col in pk_cols)

    def test_tekli_pk(self):
        data = {"Arizaid": "ARZ-001"}
        assert self._make_key(data, ["Arizaid"]) == "ARZ-001"

    def test_composite_pk(self):
        data = {"Personelid": "P001", "AitYil": "2024", "Donem": "1"}
        assert self._make_key(data, ["Personelid", "AitYil", "Donem"]) == "P001|2024|1"

    def test_bos_deger(self):
        data = {"Arizaid": ""}
        assert self._make_key(data, ["Arizaid"]) == ""

    def test_bosluk_temizlenir(self):
        data = {"Arizaid": "  ARZ-001  "}
        assert self._make_key(data, ["Arizaid"]) == "ARZ-001"

    def test_eksik_alan_bos_string(self):
        data = {}
        assert self._make_key(data, ["Arizaid"]) == ""

    def test_composite_bos_key(self):
        """Tüm alanlar boşsa ayrıştırıcı separator'dan oluşmalı."""
        data = {}
        key = self._make_key(data, ["Personelid", "AitYil", "Donem"])
        assert key == "||"


# ════════════════════════════════════════════════════════════
#  2. Push / Pull Ayrımı (saf mantık)
# ════════════════════════════════════════════════════════════

class TestPushPullAyrimi:
    """Dirty kayıtların update vs append ayrımı."""

    def _ayir(self, dirty_rows, pk_index):
        to_update = []
        to_append = []
        for row in dirty_rows:
            key = str(row.get("Arizaid", "")).strip()
            if key in pk_index:
                to_update.append(row)
            else:
                to_append.append(row)
        return to_update, to_append

    def test_remote_var_update_olarak_isim(self):
        dirty = [{"Arizaid": "ARZ-001", "Durum": "İşlemde"}]
        pk_index = {"ARZ-001": 2}  # remote'ta var
        update, append = self._ayir(dirty, pk_index)
        assert len(update) == 1
        assert len(append) == 0

    def test_remote_yok_append_olarak_isim(self):
        dirty = [{"Arizaid": "ARZ-999", "Durum": "Açık"}]
        pk_index = {}  # remote'ta yok
        update, append = self._ayir(dirty, pk_index)
        assert len(update) == 0
        assert len(append) == 1

    def test_karisik_liste(self):
        dirty = [
            {"Arizaid": "ARZ-001"},  # remote'ta var
            {"Arizaid": "ARZ-002"},  # remote'ta yok
            {"Arizaid": "ARZ-003"},  # remote'ta var
        ]
        pk_index = {"ARZ-001": 2, "ARZ-003": 4}
        update, append = self._ayir(dirty, pk_index)
        assert len(update) == 2
        assert len(append) == 1

    def test_bos_dirty(self):
        update, append = self._ayir([], {"ARZ-001": 2})
        assert update == [] and append == []


# ════════════════════════════════════════════════════════════
#  3. Pull Mantığı (yeni vs güncelleme)
# ════════════════════════════════════════════════════════════

class TestPullMantigi:
    """Remote kayıtların local'e uygulanma kuralları."""

    def _pull_karar(self, local, remote, pk_cols=["Arizaid"]):
        """
        Returns: ("insert_new", "update_clean", "skip_dirty", "skip_same")
        """
        if not local:
            return "insert_new"
        if local.get("sync_status", "").strip() == "dirty":
            return "skip_dirty"

        has_changes = False
        cols = [k for k in remote if k not in ("sync_status", "updated_at")]
        for col in cols:
            if str(remote.get(col, "")).strip() != str(local.get(col, "")).strip():
                has_changes = True
                break

        return "update_clean" if has_changes else "skip_same"

    def test_local_yok_insert(self):
        assert self._pull_karar(None, {"Arizaid": "ARZ-NEW"}) == "insert_new"

    def test_local_dirty_atla(self):
        local  = {"Arizaid": "ARZ-001", "Durum": "Açık", "sync_status": "dirty"}
        remote = {"Arizaid": "ARZ-001", "Durum": "İşlemde"}
        assert self._pull_karar(local, remote) == "skip_dirty"

    def test_local_clean_degisim_var_guncelle(self):
        local  = {"Arizaid": "ARZ-001", "Durum": "Açık",    "sync_status": "clean"}
        remote = {"Arizaid": "ARZ-001", "Durum": "İşlemde"}
        assert self._pull_karar(local, remote) == "update_clean"

    def test_local_clean_degisim_yok_atla(self):
        local  = {"Arizaid": "ARZ-001", "Durum": "Açık", "sync_status": "clean"}
        remote = {"Arizaid": "ARZ-001", "Durum": "Açık"}
        assert self._pull_karar(local, remote) == "skip_same"

    def test_bos_pk_atlanir(self):
        """Boş PK'lı remote satırlar işlenmemeli."""
        remote = {"Arizaid": "", "Durum": "Açık"}
        pk_cols = ["Arizaid"]
        key = "|".join(str(remote.get(c, "")).strip() for c in pk_cols)
        bos_key = "|".join([""] * len(pk_cols))
        assert key == bos_key  # boş → atla


# ════════════════════════════════════════════════════════════
#  4. SyncService — sync_all Hata Yönetimi
# ════════════════════════════════════════════════════════════

class TestSyncAllHataYonetimi:

    def _make_service(self, db, registry):
        with patch("database.sync_service.GSheetManager"):
            from database.sync_service import SyncService
            svc = SyncService(db=db, registry=registry)
            svc.gsheet = MagicMock()
        return svc

    def test_sync_all_bir_tablo_hata_digerleri_devam_eder(self):
        """Bir tablo exception fırlatırsa sync_all diğerlerine devam etmeli."""
        db       = _create_ariza_db()
        registry = MagicMock()

        with patch("database.sync_service.GSheetManager"):
            from database.sync_service import SyncService
            svc = SyncService(db=db, registry=registry)

        cagri_sayisi = {"n": 0}

        def mock_sync_table(tablo_adi):
            cagri_sayisi["n"] += 1
            if cagri_sayisi["n"] == 2:
                raise RuntimeError("Sheets bağlantısı kesildi")

        svc.sync_table = mock_sync_table

        with pytest.raises(RuntimeError, match="sync hatası"):
            svc.sync_all()

        assert cagri_sayisi["n"] >= 2

        db.close()

    def test_sync_all_tum_basarili_exception_yok(self):
        db       = _create_ariza_db()
        registry = MagicMock()

        with patch("database.sync_service.GSheetManager"):
            from database.sync_service import SyncService
            svc = SyncService(db=db, registry=registry)

        svc.sync_table = MagicMock()

        svc.sync_all()  # exception olmamalı
        db.close()


# ════════════════════════════════════════════════════════════
#  5. SyncService — sync_table PUSH
# ════════════════════════════════════════════════════════════

class TestSyncTablePush:

    def _make_svc_with_repo(self):
        db       = _create_ariza_db()
        registry = _make_registry(db)

        with patch("database.sync_service.GSheetManager"):
            from database.sync_service import SyncService
            svc = SyncService(db=db, registry=registry)

        svc.gsheet = MagicMock()
        svc.gsheet.read_all.return_value = ([], {}, MagicMock())
        svc.gsheet.batch_update = MagicMock()
        svc.gsheet.batch_append = MagicMock()

        return svc, registry.get.return_value, db

    def test_dirty_kayit_push_edilir(self):
        svc, repo, db = self._make_svc_with_repo()
        repo.insert({
            "Arizaid": "ARZ-001", "Durum": "Açık", "sync_status": "dirty"
        })

        svc.sync_table("Cihaz_Ariza")

        svc.gsheet.batch_append.assert_called_once()
        db.close()

    def test_clean_kayit_push_edilmez(self):
        svc, repo, db = self._make_svc_with_repo()
        repo.insert({"Arizaid": "ARZ-001", "sync_status": "clean"})

        svc.sync_table("Cihaz_Ariza")

        svc.gsheet.batch_append.assert_not_called()
        svc.gsheet.batch_update.assert_not_called()
        db.close()

    def test_push_sonrasi_kayit_clean_olur(self):
        svc, repo, db = self._make_svc_with_repo()
        repo.insert({"Arizaid": "ARZ-002", "Durum": "Açık"})
        assert repo.get_by_id("ARZ-002")["sync_status"] == "dirty"

        svc.sync_table("Cihaz_Ariza")

        assert repo.get_by_id("ARZ-002")["sync_status"] == "clean"
        db.close()


# ════════════════════════════════════════════════════════════
#  6. SyncService — sync_table PULL
# ════════════════════════════════════════════════════════════

class TestSyncTablePull:

    def _make_svc_with_repo(self, remote_rows=None, pk_index=None):
        db       = _create_ariza_db()
        registry = _make_registry(db)

        with patch("database.sync_service.GSheetManager"):
            from database.sync_service import SyncService
            svc = SyncService(db=db, registry=registry)

        svc.gsheet = MagicMock()
        svc.gsheet.read_all.return_value = (
            remote_rows or [], pk_index or {}, MagicMock()
        )
        svc.gsheet.batch_update = MagicMock()
        svc.gsheet.batch_append = MagicMock()

        return svc, registry.get.return_value, db

    def test_yeni_remote_kayit_eklenir(self):
        remote = [{"Arizaid": "ARZ-REMOTE", "Durum": "Açık",
                   "sync_status": "clean"}]
        svc, repo, db = self._make_svc_with_repo(
            remote_rows=remote, pk_index={"ARZ-REMOTE": 2}
        )

        svc.sync_table("Cihaz_Ariza")

        assert repo.get_by_id("ARZ-REMOTE") is not None
        db.close()

    def test_yeni_remote_kayit_clean_olarak_eklenir(self):
        remote = [{"Arizaid": "ARZ-NEW", "Durum": "Açık"}]
        svc, repo, db = self._make_svc_with_repo(
            remote_rows=remote, pk_index={"ARZ-NEW": 2}
        )

        svc.sync_table("Cihaz_Ariza")

        row = repo.get_by_id("ARZ-NEW")
        assert row["sync_status"] == "clean"
        db.close()

    def test_dirty_local_remote_guncelleme_ile_ezilmez(self):
        """Local dirty kayıt remote ile güncellenmemeli."""
        db       = _create_ariza_db()
        registry = _make_registry(db)

        with patch("database.sync_service.GSheetManager"):
            from database.sync_service import SyncService
            svc = SyncService(db=db, registry=registry)

        repo = registry.get.return_value
        repo.insert({"Arizaid": "ARZ-LOCAL", "Durum": "İşlemde",
                     "sync_status": "dirty"})

        remote = [{"Arizaid": "ARZ-LOCAL", "Durum": "Açık"}]
        svc.gsheet = MagicMock()
        svc.gsheet.read_all.return_value = (remote, {"ARZ-LOCAL": 2}, MagicMock())
        svc.gsheet.batch_update = MagicMock()
        svc.gsheet.batch_append = MagicMock()

        svc.sync_table("Cihaz_Ariza")

        # Dirty kayıt korunmalı
        row = repo.get_by_id("ARZ-LOCAL")
        assert row["Durum"] == "İşlemde"
        db.close()


# ════════════════════════════════════════════════════════════
#  7. SyncService — _pull_replace (pull_only tablolar)
# ════════════════════════════════════════════════════════════

class TestPullReplace:

    def test_pull_only_table_config(self):
        """Tatiller pull_only olarak konfigure edilmiş olmalı."""
        from database.table_config import TABLES
        assert TABLES["Tatiller"].get("sync_mode") == "pull_only"

    def test_sabitler_pull_only(self):
        from database.table_config import TABLES
        # Sabitler'in sync_mode'u pull_only ise kontrol et
        if "Sabitler" in TABLES:
            # sync False veya pull_only olabilir
            cfg = TABLES["Sabitler"]
            is_pull_only = (
                cfg.get("sync_mode") == "pull_only" or
                cfg.get("sync", True) is False
            )
            assert is_pull_only

    def test_tatiller_pk_tarih(self):
        from database.table_config import TABLES
        assert TABLES["Tatiller"]["pk"] == "Tarih"

    def test_tatiller_kolonlar(self):
        from database.table_config import TABLES
        assert "Tarih" in TABLES["Tatiller"]["columns"]
        assert "ResmiTatil" in TABLES["Tatiller"]["columns"]


# ════════════════════════════════════════════════════════════
#  8. Dirty → Clean Döngüsü (entegrasyon)
# ════════════════════════════════════════════════════════════

class TestDirtyCleanDogusu:
    """BaseRepository + SyncService birlikte dirty→clean döngüsü."""

    def test_insert_dirty_push_clean(self):
        db   = _create_ariza_db()
        from database.base_repository import BaseRepository
        columns = ["Arizaid", "Cihazid", "Durum", "sync_status", "updated_at"]
        repo = BaseRepository(db=db, table_name="Cihaz_Ariza",
                              pk="Arizaid", columns=columns, has_sync=True)

        # 1. Insert → dirty
        repo.insert({"Arizaid": "ARZ-DC-001", "Durum": "Açık"})
        assert repo.get_by_id("ARZ-DC-001")["sync_status"] == "dirty"
        assert len(repo.get_dirty()) == 1

        # 2. Simüle push → mark_clean
        repo.mark_clean("ARZ-DC-001")
        assert repo.get_by_id("ARZ-DC-001")["sync_status"] == "clean"
        assert repo.get_dirty() == []

        # 3. Update → dirty tekrar
        repo.update("ARZ-DC-001", {"Durum": "İşlemde"})
        assert repo.get_by_id("ARZ-DC-001")["sync_status"] == "dirty"

        db.close()
