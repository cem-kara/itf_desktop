#!/usr/bin/env python3
"""
Test migration - yeni DB oluştur ve sabitler/tatilleri kontrol et
"""

import sys
from pathlib import Path

# Test için geçici bir DB dosyası oluştur
test_db = Path("data/test_migration.db")
if test_db.exists():
    test_db.unlink()

# System path'e ekle
sys.path.insert(0, str(Path.cwd()))

# Migration'ı test et
from database.migrations import MigrationManager


mgr = MigrationManager(str(test_db))
print("1. Migration başlatılıyor...")
mgr.run_migrations()

# Sabitler tablosunu kontrol et
import sqlite3
conn = sqlite3.connect(str(test_db))
cur = conn.cursor()

print("\n2. Sabitler tablosu kontrol:")
cur.execute("SELECT COUNT(*) as cnt FROM Sabitler")
count = cur.fetchone()[0]
print(f"  - Toplam kayıt: {count}")

cur.execute("SELECT DISTINCT Kod FROM Sabitler ORDER BY Kod")
kodlar = [row[0] for row in cur]
print(f"  - Farklı kod sayısı: {len(kodlar)}")
print(f"  - Örnek kodlar: {', '.join(kodlar[:5])}")

print("\n3. Tatiller tablosu kontrol:")
cur.execute("SELECT COUNT(*) as cnt FROM Tatiller")
tatil_count = cur.fetchone()[0]
print(f"  - Toplam tatil sayısı: {tatil_count}")

cur.execute("SELECT Tarih, ResmiTatil FROM Tatiller ORDER BY Tarih")
for row in cur:
    print(f"  - {row[0]}: {row[1]}")

conn.close()

print("\n✓ Migration test başarılı!")
if count > 0 and tatil_count > 0:
    print("✓ Sabitler ve tatiller başarılı şekilde yüklendi!")
else:
    print("✗ Uyarı: Veri yüklenmemiş!")

# Cleanup
test_db.unlink()
