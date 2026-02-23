#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test schema ve repository yapısı."""

import sqlite3
import sys
sys.path.insert(0, '.')

# Test 1: Cihaz_Belgeler tablosu
print("=" * 60)
print("Test 1: Cihaz_Belgeler Tablosu")
print("=" * 60)

conn = sqlite3.connect('data/veritabani.db')
cur = conn.cursor()

cur.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='Cihaz_Belgeler'")
result = cur.fetchone()
if result:
    print("✓ Cihaz_Belgeler tablosu oluşturuldu")
    print(result[0])
else:
    print("✗ Cihaz_Belgeler tablosu bulunamadı")

# Test 2: Sabitler belge türleri
print("\n" + "=" * 60)
print("Test 2: Sabitler Belge Türleri")
print("=" * 60)

cur.execute("SELECT Rowid, Kod, MenuEleman FROM Sabitler WHERE Kod='Cihaz_Belge_Tur'")
rows = cur.fetchall()
print(f"✓ {len(rows)} belge türü yüklendi:\n")
for rowid, kod, menu in rows:
    print(f"  {rowid}. {menu}")

# Test 3: Repository yapısı
print("\n" + "=" * 60)
print("Test 3: Repository Yapısı")
print("=" * 60)

try:
    from database.repository_registry import RepositoryRegistry
    from database.repositories import CihazBelgelerRepository
    print("✓ CihazBelgelerRepository import başarılı")
    
    # Mock DB ile test (real DB connection gereksiz)
    registry = RepositoryRegistry(None)
    print("✓ RepositoryRegistry oluşturuldu")
except ImportError as e:
    print(f"✗ Import hatası: {e}")

# Test 4: Table config
print("\n" + "=" * 60)
print("Test 4: Table Config")
print("=" * 60)

try:
    from database.table_config import TABLES
    if 'Cihaz_Belgeler' in TABLES:
        print("✓ Cihaz_Belgeler table_config'te tanımlanmış")
        cfg = TABLES['Cihaz_Belgeler']
        print(f"  PK: {cfg.get('pk', [])}")
        print(f"  Colonlar: {len(cfg.get('columns', []))} adet")
        print(f"  Date fields: {cfg.get('date_fields', [])}")
        print(f"  Sync: {cfg.get('sync', True)}")
    else:
        print("✗ Cihaz_Belgeler table_config'te yok")
except Exception as e:
    print(f"✗ Hata: {e}")

cur.close()
conn.close()

print("\n" + "=" * 60)
print("✓ Tüm testler tamamlandı")
print("=" * 60)
