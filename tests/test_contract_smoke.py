# -*- coding: utf-8 -*-
"""
Central contract smoke tests for migration/config alignment.

Scope:
- Schema version contract
- PK contracts (table_config vs real migrated SQLite schema)
- Sync mode contracts for Sabitler/Tatiller/Loglar
"""

import pytest

from database.migrations import MigrationManager
from database.table_config import TABLES


EXPECTED_SCHEMA_VERSION = 7

EXPECTED_PK = {
    "RKE_List": ["EkipmanNo"],
    "RKE_Muayene": ["KayitNo"],
    "Personel_Saglik_Takip": ["KayitNo"],
    "Sabitler": ["Rowid"],
    "Tatiller": ["Tarih"],
    "FHSZ_Puantaj": ["Personelid", "AitYil", "Donem"],
}


def _pk_list_from_config(pk_value):
    if pk_value is None:
        return []
    return pk_value if isinstance(pk_value, list) else [pk_value]


def _pk_list_from_schema(conn, table_name):
    cur = conn.execute(f"PRAGMA table_info({table_name})")
    rows = cur.fetchall()
    # PRAGMA column 5 is pk order (0 means not in PK)
    pk_rows = sorted((r for r in rows if r[5] > 0), key=lambda r: r[5])
    return [r[1] for r in pk_rows]


def test_current_version_contract():
    assert MigrationManager.CURRENT_VERSION == EXPECTED_SCHEMA_VERSION


@pytest.mark.parametrize("table_name,expected_pk", EXPECTED_PK.items())
def test_table_config_pk_contract(table_name, expected_pk):
    assert table_name in TABLES, f"Missing table in TABLES: {table_name}"
    cfg_pk = _pk_list_from_config(TABLES[table_name].get("pk"))
    assert cfg_pk == expected_pk


def test_sync_mode_contract():
    sabitler = TABLES["Sabitler"]
    tatiller = TABLES["Tatiller"]
    loglar = TABLES["Loglar"]

    assert sabitler.get("sync_mode") != "pull_only"
    assert sabitler.get("sync", True) is not False

    assert tatiller.get("sync_mode") != "pull_only"
    assert tatiller.get("sync", True) is not False

    assert loglar.get("sync") is False


def test_migration_schema_contract(tmp_path):
    db_path = str(tmp_path / "contract_smoke.db")
    migrator = MigrationManager(db_path)

    assert migrator.run_migrations() is True
    assert migrator.get_schema_version() == migrator.CURRENT_VERSION

    conn = migrator.connect()
    try:
        for table_name, expected_pk in EXPECTED_PK.items():
            assert _pk_list_from_schema(conn, table_name) == expected_pk
    finally:
        conn.close()
