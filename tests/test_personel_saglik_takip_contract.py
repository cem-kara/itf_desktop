# -*- coding: utf-8 -*-
"""
Personel_Saglik_Takip tablo sozlesme testleri.

Kapsam:
- table_config pk/columns/date_fields dogrulamasi
- migration sonrasi SQLite semasinda kolon ve PK dogrulamasi
"""

from database.migrations import MigrationManager
from database.table_config import TABLES


EXPECTED_BUSINESS_COLUMNS = [
    "KayitNo",
    "Personelid",
    "AdSoyad",
    "Birim",
    "Yil",
    "MuayeneTarihi",
    "SonrakiKontrolTarihi",
    "Sonuc",
    "Durum",
    "RaporDosya",
    "Notlar",
    "DermatolojiMuayeneTarihi",
    "DermatolojiDurum",
    "DermatolojiAciklama",
    "DahiliyeMuayeneTarihi",
    "DahiliyeDurum",
    "DahiliyeAciklama",
    "GozMuayeneTarihi",
    "GozDurum",
    "GozAciklama",
    "GoruntulemeMuayeneTarihi",
    "GoruntulemeDurum",
    "GoruntulemeAciklama",
]

EXPECTED_DATE_FIELDS = [
    "MuayeneTarihi",
    "SonrakiKontrolTarihi",
    "DermatolojiMuayeneTarihi",
    "DahiliyeMuayeneTarihi",
    "GozMuayeneTarihi",
    "GoruntulemeMuayeneTarihi",
]


def test_table_config_personel_saglik_takip_contract():
    cfg = TABLES["Personel_Saglik_Takip"]
    assert cfg["pk"] == "KayitNo"
    assert cfg["columns"] == EXPECTED_BUSINESS_COLUMNS
    assert cfg["date_fields"] == EXPECTED_DATE_FIELDS


def test_migration_personel_saglik_takip_schema_contract(tmp_path):
    db_path = str(tmp_path / "pst_contract.db")
    migrator = MigrationManager(db_path)
    assert migrator.run_migrations() is True

    conn = migrator.connect()
    try:
        cur = conn.execute("PRAGMA table_info(Personel_Saglik_Takip)")
        rows = cur.fetchall()
    finally:
        conn.close()

    schema_columns = [r[1] for r in rows]
    pk_columns = [r[1] for r in rows if r[5] > 0]

    expected_schema_columns = EXPECTED_BUSINESS_COLUMNS + ["sync_status", "updated_at"]
    assert schema_columns == expected_schema_columns
    assert pk_columns == ["KayitNo"]
