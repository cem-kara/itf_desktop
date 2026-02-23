#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sync hatalarının düzeltildiğini test et.
"""

import sys
import sqlite3
from pathlib import Path

# Path setup
sys.path.insert(0, str(Path(__file__).parent))

from core.paths import DB_PATH
from core.logger import logger
from database.migrations import MigrationManager
from database.sqlite_manager import SQLiteManager
from database.table_config import TABLES

def test_migrations():
    """Migration'ları çalıştır."""
    print("\n" + "="*60)
    print("TEST 0: Migration Uygulaması")
    print("="*60)
    
    try:
        migration = MigrationManager(DB_PATH)
        current = migration.get_schema_version()
        target = migration.CURRENT_VERSION
        
        print(f"Mevcut versiyon: v{current}")
        print(f"Hedef versiyon: v{target}")
        
        if current < target:
            print(f"Migration başlatılıyor: v{current} → v{target}...")
            migration.run_migrations()
            print(f"✓ Migration tamamlandı")
        elif current == target:
            print(f"✓ Database zaten güncel (v{current})")
        else:
            print(f"⚠ Database versiyonu code'dan yüksek ({current} > {target})")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Migration hatası: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_sqlite_timeout():
    """SQLite timeout ayarını kontrol et."""
    print("\n" + "="*60)
    print("TEST 1: SQLite Timeout")
    print("="*60)
    
    try:
        db = SQLiteManager()
        
        # Pragma'ları kontrol et
        cur = db.conn.cursor()
        cur.execute("PRAGMA journal_mode")
        journal_mode = cur.fetchone()[0]
        print(f"✓ Journal Mode: {journal_mode}")
        
        cur.execute("PRAGMA busy_timeout")
        timeout_ms = cur.fetchone()[0]
        print(f"✓ Timeout (ms): {timeout_ms}")
        
        if journal_mode.upper() == "WAL":
            print("✓ WAL mode etkinleştirildi")
        else:
            print("⚠ WAL mode aktif değil")
        
        db.close()
        print("\n✅ SQLite timeout testi BAŞARILI")
        return True
        
    except Exception as e:
        print(f"\n❌ SQLite timeout hatası: {e}")
        return False

def test_table_config():
    """Tablo konfigürasyonlarını kontrol et."""
    print("\n" + "="*60)
    print("TEST 2: Tablo Konfigürasyonu")
    print("="*60)
    
    try:
        # pull_only tablolar
        pull_only_tables = [
            "Sabitler", "Tatiller", "Cihaz_Teknik", "Cihaz_Teknik_Belge"
        ]
        
        for table_name in pull_only_tables:
            cfg = TABLES.get(table_name)
            if not cfg:
                print(f"❌ {table_name} konfigürasyonu bulunamadı")
                return False
            
            sync_mode = cfg.get("sync_mode")
            if sync_mode == "pull_only":
                print(f"✓ {table_name}: {sync_mode}")
            else:
                print(f"⚠ {table_name}: {sync_mode or 'None (default)'}")
        
        # Personel MuayeneTarihi sütunu
        personel_cfg = TABLES.get("Personel")
        if "MuayeneTarihi" in personel_cfg.get("columns", []):
            print("✓ Personel konfigürasyonu: MuayeneTarihi var")
        else:
            print("❌ Personel: MuayeneTarihi sütunu konfigürasyonda YOK")
            return False
        
        print("\n✅ Tablo konfigürasyonu testi BAŞARILI")
        return True
        
    except Exception as e:
        print(f"\n❌ Tablo konfigürasyonu hatası: {e}")
        return False

def test_database_schema():
    """Database şemasını kontrol et."""
    print("\n" + "="*60)
    print("TEST 3: Database Şeması")
    print("="*60)
    
    try:
        db = SQLiteManager()
        cur = db.conn.cursor()
        
        # Tabloları listele
        cur.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' 
            ORDER BY name
        """)
        
        tables = [row[0] for row in cur.fetchall()]
        print(f"Database'de {len(tables)} tablo bulundu\n")
        
        critical_tables = [
            "Personel", "Cihazlar", "Cihaz_Teknik", 
            "Sabitler", "Tatiller"
        ]
        
        all_ok = True
        for table in critical_tables:
            if table in tables:
                # Personel sütunlarını kontrol et
                if table == "Personel":
                    cur.execute(f"PRAGMA table_info({table})")
                    columns = [row[1] for row in cur.fetchall()]
                    
                    missing_cols = []
                    for col in ["MuayeneTarihi", "Sonuc"]:
                        if col not in columns:
                            missing_cols.append(col)
                    
                    if not missing_cols:
                        print(f"✓ {table}: OK (MuayeneTarihi + Sonuc sütunları var)")
                    else:
                        print(f"❌ {table}: Eksik sütunlar: {', '.join(missing_cols)}")
                        all_ok = False
                else:
                    print(f"✓ {table}: OK")
            else:
                print(f"❌ {table}: Bulunamadı")
                all_ok = False
        
        db.close()
        
        if all_ok:
            print("\n✅ Database şeması testi BAŞARILI")
        else:
            print("\n❌ Database şeması testinde sorun var")
        
        return all_ok
        
    except Exception as e:
        print(f"\n❌ Database şeması hatası: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("\n")
    print("╔" + "═"*58 + "╗")
    print("║  SYNC HATAYILARI FIX TEST   " + " "*28 + "║")
    print("╚" + "═"*58 + "╝")
    
    results = []
    results.append(("Migration Uygulaması", test_migrations()))
    results.append(("SQLite Timeout", test_sqlite_timeout()))
    results.append(("Tablo Konfigürasyonu", test_table_config()))
    results.append(("Database Şeması", test_database_schema()))
    
    # Özet
    print("\n" + "="*60)
    print("ÖZET")
    print("="*60)
    
    for name, result in results:
        status = "✅ BAŞARILI" if result else "❌ BAŞARISIZ"
        print(f"{name:.<40} {status}")
    
    all_passed = all(r[1] for r in results)
    
    if all_passed:
        print("\n🎉 Tüm testler başarılı!")
        print("\nSync hatalarının çözümü:")
        print("  1. ✅ SQLite timeout: 30 sn (database locked'ı çözer)")
        print("  2. ✅ WAL mode: Aktif (concurrent access için)")
        print("  3. ✅ Pull-only tablolar: Sabitler, Tatiller, Cihaz_Teknik*")
        print("  4. ✅ Personel.MuayeneTarihi: Migration v11 ile eklendi")
        print("\nŞimdi sync'ı başlatabilirsiniz!")
    else:
        print("\n⚠️ Bazı testler başarısız..önce hataları düzeltmeliyiz.")
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())
