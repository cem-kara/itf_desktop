#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Belgeler paneli test scripti."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QApplication
from database.sqlite_manager import SQLiteManager
from ui.pages.cihaz.components.cihaz_dokuman_panel import CihazDokumanPanel

# Test senaryoları
print("=" * 60)
print("CihazDokumanPanel Test")
print("=" * 60)

# Test 1: Cihaz ID ile panel oluşturma
print("\n1. Cihaz ID ile panel oluşturma (cihaz_merkez gibi)")
try:
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    
    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'veritabani.db')
    db = SQLiteManager(db_path)
    
    # Test cihaz ID'si (varsa RAD-001, yoksa TEST-001)
    from database.repository_registry import RepositoryRegistry
    repo = RepositoryRegistry(db).get("Cihazlar")
    all_cihazlar = repo.get_all()
    
    if all_cihazlar:
        test_id = all_cihazlar[0].get("Cihazid", "TEST-001")
        print(f"   ✓ Test cihaz ID: {test_id}")
    else:
        print("   ⚠ Veritabanında cihaz yok, TEST-001 kullanılıyor")
        test_id = "TEST-001"
    
    # Panel oluştur
    panel = CihazDokumanPanel(cihaz_id=test_id, db=db)
    print(f"   ✓ Panel oluşturuldu (cihaz_id={test_id})")
    print(f"   ✓ Belge türleri yüklü: {len(panel.belge_turleri)} adet")
    print(f"   ✓ Mevcut belgeler: {len(panel.dokumanlari)} adet")
    
    # Widget'ların enabled olduğunu kontrol et
    if panel.combo_type.isEnabled():
        print("   ✓ ComboBox enabled")
    else:
        print("   ✗ ComboBox disabled (HATA!)")
    
    db.close()
    
except Exception as e:
    print(f"   ✗ Panel oluşturma hatası: {e}")
    import traceback
    traceback.print_exc()

# Test 2: Boş cihaz ID ile panel
print("\n2. Boş cihaz ID ile panel oluşturma (cihaz_ekle gibi)")
try:
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    
    db = SQLiteManager(db_path)
    panel2 = CihazDokumanPanel(cihaz_id="", db=db)
    
    print(f"   ✓ Panel oluşturuldu (cihaz_id='')")
    
    # Widget'ların disabled olduğunu kontrol et
    if not panel2.combo_type.isEnabled():
        print("   ✓ ComboBox disabled (beklenen)")
    else:
        print("   ✗ ComboBox enabled (HATA! Disabled olmalı)")
    
    # set_cihaz_id çağır
    panel2.set_cihaz_id("RAD-002")
    if panel2.combo_type.isEnabled():
        print("   ✓ set_cihaz_id sonrası ComboBox enabled")
    else:
        print("   ✗ set_cihaz_id sonrası ComboBox disabled (HATA!)")
    
    db.close()
    
except Exception as e:
    print(f"   ✗ Panel oluşturma hatası: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("✅ Test tamamlandı")
print("=" * 60)
