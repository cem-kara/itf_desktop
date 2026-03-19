#!/usr/bin/env python3
"""
Mevcut DB'deki sabitlərəri export et ve migration dosyasına uygun format ile yazdır.
"""
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.paths import DB_PATH


def export_sabitler():
    """Mevcut DB'deki sabitlərəri export et."""
    if not Path(DB_PATH).exists():
        print(f"Veritabanı bulunamadı: {DB_PATH}")
        return
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    # Tüm sabitlərəri al (belge türləri hariç - onlar zaten seedli)
    cur.execute('''
    SELECT Rowid, Kod, MenuEleman, Aciklama
    FROM Sabitler
    WHERE Kod NOT IN ('Cihaz_Belge_Tur', 'Personel_Belge_Tur')
    ORDER BY CAST(Rowid AS INTEGER)
    ''')
    
    rows = cur.fetchall()
    print(f"Toplam {len(rows)} sabit bulundu (belge türləri hariç)")
    print()
    print("# Python format (migrations.py içinde kullanılacak):")
    print()
    print("sistem_sabitler = [")
    
    for row in rows:
        rowid = row[0]
        kod = row[1]
        menu = row[2]
        aciklama = row[3]
        
        # Escape quotes
        menu = menu.replace('"', '\\"')
        aciklama = aciklama.replace('"', '\\"')
        
        print(f'    ("{rowid}", "{kod}", "{menu}", "{aciklama}"),')
    
    print("]")
    print()
    
    # Tatillər
    print("# Tatiller (örnek):")
    print("tatiller = [")
    print('    ("2025-01-01", "Yeni Yıl"),')
    print('    ("2025-04-23", "Ulusal Egemenlik Günü"),')
    print('    ("2025-05-01", "Emek ve Dayanışma Günü"),')
    print('    ("2025-07-15", "Demokrasi ve Milli Birlik Günü"),')
    print('    ("2025-08-30", "Zafer Bayramı"),')
    print('    ("2025-10-29", "Cumhuriyet Bayramı"),')
    print("]")
    
    conn.close()

if __name__ == "__main__":
    export_sabitler()
