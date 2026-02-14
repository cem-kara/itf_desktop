# -*- coding: utf-8 -*-
"""
database/migrations.py ve sqlite_manager.py unit testleri
===========================================================
Kapsam:
  - DatabaseMigrator : get_schema_version, set_schema_version,
                       CURRENT_VERSION sabiti, run_migrations,
                       backup_database, _cleanup_old_backups
  - Tablo oluşturma  : create_tables sonrası beklenen tablolar var mı
  - SQLiteManager    : execute, executemany, row_factory
"""
import os
import sqlite3
import tempfile
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock


# ════════════════════════════════════════════════════════════
# 1. MigrationManager — get/set schema version
# ════════════════════════════════════════════════════════════

class TestSchemaVersion:

    @pytest.fixture
    def migrator(self, tmp_path):
        from database.migrations import MigrationManager as DatabaseMigrator
        db_path = str(tmp_path / "test.db")
        return DatabaseMigrator(db_path)

    def test_yeni_db_versiyon_sifir(self, migrator):
        assert migrator.get_schema_version() == 0

    def test_set_schema_version(self, migrator):
        # schema_version tablosunu oluşturmak için önce get çağır
        migrator.get_schema_version()
        migrator.set_schema_version(1, "v1 oluşturuldu")
        assert migrator.get_schema_version() == 1

    def test_set_multiple_versions(self, migrator):
        migrator.get_schema_version()
        migrator.set_schema_version(1, "v1")
        migrator.set_schema_version(2, "v2")
        assert migrator.get_schema_version() == 2

    def test_current_version_sabit_6(self, migrator):
        assert migrator.CURRENT_VERSION == 6

    def test_schema_version_tablo_olusur(self, migrator):
        migrator.get_schema_version()
        conn = migrator.connect()
        cur = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_version'"
        )
        assert cur.fetchone() is not None
        conn.close()


# ════════════════════════════════════════════════════════════
# 2. MigrationManager — run_migrations
# ════════════════════════════════════════════════════════════

class TestRunMigrations:

    @pytest.fixture
    def migrator(self, tmp_path):
        from database.migrations import MigrationManager as DatabaseMigrator
        db_path = str(tmp_path / "migrate_test.db")
        return DatabaseMigrator(db_path)

    def test_fresh_db_run_migrations(self, migrator):
        """Yeni DB'de migration başarıyla tamamlanmalı."""
        result = migrator.run_migrations()
        assert result is True

    def test_after_migration_version_current(self, migrator):
        migrator.run_migrations()
        assert migrator.get_schema_version() == migrator.CURRENT_VERSION

    def test_zaten_guncel_true_donus(self, migrator):
        """Zaten güncel DB'de run_migrations True dönmeli."""
        migrator.run_migrations()
        result = migrator.run_migrations()  # ikinci kez çağır
        assert result is True

    def test_migration_sonrasi_tablolar_mevcut(self, migrator):
        """Migration sonrası temel tablolar mevcut olmalı."""
        migrator.run_migrations()
        conn = migrator.connect()
        cur = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
        tablolar = {r[0] for r in cur.fetchall()}
        conn.close()

        beklenen = {
            "Personel", "Cihazlar", "Cihaz_Ariza", "Ariza_Islem",
            "Periyodik_Bakim", "Tatiller", "schema_version"
        }
        for t in beklenen:
            assert t in tablolar, f"'{t}' tablosu yok"

    def test_cihaz_ariza_kolonlar(self, migrator):
        migrator.run_migrations()
        conn = migrator.connect()
        cur = conn.execute("PRAGMA table_info(Cihaz_Ariza)")
        kolonlar = {r[1] for r in cur.fetchall()}
        conn.close()
        for k in ["Arizaid", "Cihazid", "Baslik", "Durum", "sync_status"]:
            assert k in kolonlar, f"'{k}' kolonu yok"

    def test_periyodik_bakim_kolonlar(self, migrator):
        migrator.run_migrations()
        conn = migrator.connect()
        cur = conn.execute("PRAGMA table_info(Periyodik_Bakim)")
        kolonlar = {r[1] for r in cur.fetchall()}
        conn.close()
        for k in ["Planid", "Cihazid", "BakimPeriyodu", "Durum",
                  "YapilanIslemler", "Aciklama", "Teknisyen", "sync_status"]:
            assert k in kolonlar, f"'{k}' kolonu yok"

    def test_tatiller_kolonlar(self, migrator):
        migrator.run_migrations()
        conn = migrator.connect()
        cur = conn.execute("PRAGMA table_info(Tatiller)")
        kolonlar = {r[1] for r in cur.fetchall()}
        conn.close()
        assert "Tarih"      in kolonlar
        assert "ResmiTatil" in kolonlar

    def test_fhsz_puantaj_composite_pk(self, migrator):
        """FHSZ_Puantaj composite PRIMARY KEY olmalı."""
        migrator.run_migrations()
        conn = migrator.connect()
        cur = conn.execute("PRAGMA table_info(FHSZ_Puantaj)")
        pk_kolonlar = [r[1] for r in cur.fetchall() if r[5] > 0]  # pk sıfır değilse
        conn.close()
        assert "Personelid" in pk_kolonlar
        assert "AitYil"     in pk_kolonlar
        assert "Donem"      in pk_kolonlar


# ════════════════════════════════════════════════════════════
#  3. DatabaseMigrator — backup
# ════════════════════════════════════════════════════════════

class TestBackup:

    @pytest.fixture
    def migrator(self, tmp_path):
        from database.migrations import MigrationManager as DatabaseMigrator
        db_path = str(tmp_path / "backup_test.db")
        # DB oluştur
        conn = sqlite3.connect(db_path)
        conn.execute("CREATE TABLE test (id INTEGER)")
        conn.commit()
        conn.close()
        return DatabaseMigrator(db_path)

    def test_backup_dosya_olusur(self, migrator):
        backup_path = migrator.backup_database()
        assert backup_path is not None
        assert Path(str(backup_path)).exists()

    def test_backup_db_icerigi_ayni(self, migrator):
        backup_path = migrator.backup_database()
        orig_size = os.path.getsize(migrator.db_path)
        back_size = os.path.getsize(str(backup_path))
        assert orig_size == back_size

    def test_backup_olmayan_db_none(self, tmp_path):
        from database.migrations import MigrationManager as DatabaseMigrator
        m = DatabaseMigrator(str(tmp_path / "yok.db"))
        result = m.backup_database()
        assert result is None

    def test_cleanup_old_backups(self, migrator):
        """11 yedek oluşturulup cleanup çağrılınca 10 kalmalı."""
        for i in range(11):
            (migrator.backup_dir / f"db_backup_202401{i:02d}_120000.db").write_text("x")
        migrator._cleanup_old_backups(keep_count=10)
        backups = list(migrator.backup_dir.glob("db_backup_*.db"))
        assert len(backups) <= 10


# ════════════════════════════════════════════════════════════
#  4. SQLiteManager — execute / executemany / row_factory
# ════════════════════════════════════════════════════════════

class TestSQLiteManagerLogic:
    """
    SQLiteManager gerçek DB_PATH'e bağlandığından,
    sadece iş mantığını (execute, row_factory, close) test ederiz.
    DB_PATH'i tmp dosyayla değiştiririz.
    """

    @pytest.fixture
    def manager(self, tmp_path, monkeypatch):
        db_file = str(tmp_path / "sm_test.db")
        from importlib import reload
        import database.sqlite_manager as sm_mod
        reload(sm_mod)
        sm_mod.DB_PATH = db_file   # reload sonrası set et (monkeypatch sırasına göre)
        mgr = sm_mod.SQLiteManager()
        yield mgr
        mgr.close()

    def test_execute_create_insert_select(self, manager):
        manager.execute("CREATE TABLE t (id INTEGER, ad TEXT)")
        manager.execute("INSERT INTO t VALUES (?, ?)", (1, "Ali"))
        cur = manager.execute("SELECT * FROM t")
        rows = cur.fetchall()
        assert len(rows) == 1

    def test_row_factory_dict_erisim(self, manager):
        manager.execute("CREATE TABLE t2 (ad TEXT, yas INTEGER)")
        manager.execute("INSERT INTO t2 VALUES (?, ?)", ("Veli", 30))
        cur = manager.execute("SELECT * FROM t2")
        row = cur.fetchone()
        assert row["ad"] == "Veli"
        assert row["yas"] == 30

    def test_executemany(self, manager):
        manager.execute("CREATE TABLE t3 (val INTEGER)")
        manager.executemany("INSERT INTO t3 VALUES (?)", [(i,) for i in range(5)])
        cur = manager.execute("SELECT COUNT(*) FROM t3")
        count = cur.fetchone()[0]
        assert count == 5

    def test_execute_commit_otomatik(self, manager):
        """execute sonrası commit çağrılmadan veri kalıcı olmalı."""
        manager.execute("CREATE TABLE t4 (x INTEGER)")
        manager.execute("INSERT INTO t4 VALUES (42)")
        # Yeni cursor ile oku
        cur = manager.execute("SELECT x FROM t4")
        assert cur.fetchone()[0] == 42
