#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test için örnek cihaz ekle."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.sqlite_manager import SQLiteManager
from database.repository_registry import RepositoryRegistry
from datetime import datetime

db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'veritabani.db')
db = SQLiteManager(db_path)

try:
    repo = RepositoryRegistry(db).get("Cihazlar")
    
    # Test cihazı ekle
    test_cihaz = {
        "Cihazid": "TEST-2026-001",
        "CihazTipi": "Radyoloji",
        "Marka": "Siemens",
        "Model": "Axiom Artis",
        "Birim": "Radyoloji Servisi",
        "HizmeteGirisTarihi": datetime.now().strftime("%Y-%m-%d"),
        "Amac": "Test cihazı",
        "AnaBilimDali": "Radyoloji",
        "Kaynak": "Test",
    }
    
    # Kontrol: aynı ID var mı?
    existing = repo.get_by_id("TEST-2026-001")
    if existing:
        print("⚠ TEST-2026-001 zaten mevcut, güncelleniyor...")
        repo.update("TEST-2026-001", test_cihaz)
    else:
        print("✓ Yeni test cihazı ekleniyor...")
        repo.insert(test_cihaz)
    
    print(f"✅ Test cihazı hazır: {test_cihaz['Cihazid']}")
    print(f"   Marka: {test_cihaz['Marka']}")
    print(f"   Model: {test_cihaz['Model']}")
    print(f"   Birim: {test_cihaz['Birim']}")
    
except Exception as e:
    print(f"✗ Hata: {e}")
    import traceback
    traceback.print_exc()
finally:
    db.close()
