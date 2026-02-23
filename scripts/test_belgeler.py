#!/usr/bin/env python3
# Quick test
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.sqlite_manager import SQLiteManager

# DB path
db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'veritabani.db')

print('✓ Belgeler tablosu ve Sabitler verificatisi:\n')
db = SQLiteManager(db_path)

# Test 1: Cihaz_Belgeler kontrol
cur = db.conn.cursor()
cur.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='Cihaz_Belgeler'")
count = cur.fetchone()[0]
print(f"1. Cihaz_Belgeler tablosu: {'✓' if count else '✗'}")

# Test 2: Belge türleri
cur.execute("SELECT COUNT(*) FROM Sabitler WHERE Kod='Cihaz_Belge_Tur'")
turler = cur.fetchone()[0]
print(f"2. Belge türleri: {'✓' if turler == 7 else '✗'} ({turler}/7)")

if turler > 0:
    cur.execute("SELECT MenuEleman FROM Sabitler WHERE Kod='Cihaz_Belge_Tur' ORDER BY Rowid")
    print("\n   Tanımlı türler:")
    for row in cur.fetchall():
        print(f"   • {row[0]}")

db.close()
print('\n✅ Tüm hazırlıklar tamamlandı!')
