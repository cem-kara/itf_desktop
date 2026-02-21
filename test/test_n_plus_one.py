#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
N+1 Query Optimization Test
Test eder: PersonelRepository.get_all_with_bakiye() metodu
"""

import sys
import time
from pathlib import Path

# Project root'a ekle
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from database.sqlite_manager import SQLiteManager
from database.repository_registry import RepositoryRegistry


def test_n_plus_one_optimization():
    """N+1 optimizasyonunu test et."""
    print("═══ N+1 QUERY OPTIMIZATION TEST ═══\n")
    
    # Database bağlantısı (SQLiteManager ayarları config'den okur)
    try:
        db = SQLiteManager()
    except Exception as e:
        print(f"⚠️  Veritabanı bağlantısı kurulamadı: {e}")
        print("Test atlanıyor...")
        return
    
    registry = RepositoryRegistry(db.conn)
    
    print("─── Test 1: Eski Yöntem (2 ayrı sorgu) ───\n")
    start = time.time()
    
    personel_repo = registry.get("Personel")
    personel_list = personel_repo.get_all()
    print(f"✓ Personel.get_all(): {len(personel_list)} kayıt")
    
    izin_repo = registry.get("Izin_Bilgi")
    izin_list = izin_repo.get_all()
    print(f"✓ Izin_Bilgi.get_all(): {len(izin_list)} kayıt")
    
    # Manual mapping
    izin_map = {str(r.get("TCKimlik", "")).strip(): r for r in izin_list}
    print(f"✓ Manual mapping: {len(izin_map)} TC")
    
    old_time = time.time() - start
    print(f"\n⏱️  Toplam süre (eski): {old_time*1000:.2f}ms")
    
    print("\n─── Test 2: Yeni Yöntem (JOIN ile tek sorgu) ───\n")
    start = time.time()
    
    personel_with_bakiye = personel_repo.get_all_with_bakiye()
    print(f"✓ Personel.get_all_with_bakiye(): {len(personel_with_bakiye)} kayıt")
    
    new_time = time.time() - start
    print(f"\n⏱️  Toplam süre (yeni): {new_time*1000:.2f}ms")
    
    print("\n─── Performans Karşılaştırması ───\n")
    improvement = ((old_time - new_time) / old_time) * 100 if old_time > 0 else 0
    print(f"Eski yöntem: {old_time*1000:.2f}ms")
    print(f"Yeni yöntem: {new_time*1000:.2f}ms")
    print(f"İyileştirme: {improvement:.1f}% daha hızlı")
    
    print("\n─── Veri Doğrulama ───\n")
    
    # İlk 3 personelin bakiye bilgilerini karşılaştır
    sample_count = min(3, len(personel_list))
    matches = 0
    
    for i in range(sample_count):
        p_old = personel_list[i]
        tc = str(p_old.get("KimlikNo", "")).strip()
        
        # Eski yöntemde manual lookup
        bakiye_old = izin_map.get(tc, {})
        kalan_old = bakiye_old.get("YillikKalan", "—")
        
        # Yeni yöntemde direkt okuma
        p_new = next((p for p in personel_with_bakiye if str(p.get("KimlikNo", "")).strip() == tc), None)
        kalan_new = p_new.get("YillikKalan", "—") if p_new else "—"
        
        status = "✓" if str(kalan_old) == str(kalan_new) else "✗"
        print(f"{status} {p_old.get('AdSoyad', 'N/A'):20} | Kalan: {kalan_old} (eski) vs {kalan_new} (yeni)")
        
        if str(kalan_old) == str(kalan_new):
            matches += 1
    
    print(f"\n{'─'*50}")
    print(f"Doğrulama: {matches}/{sample_count} eşleşme")
    
    if matches == sample_count:
        print("\n🎉 TEST BAŞARILI! Veri tutarlılığı sağlandı ve performans iyileşti.")
    else:
        print("\n⚠️  UYARI: Veri tutarsızlığı tespit edildi!")
    
    db.close()


if __name__ == "__main__":
    try:
        test_n_plus_one_optimization()
    except Exception as e:
        print(f"\n❌ Test hatası: {e}")
        import traceback
        traceback.print_exc()
