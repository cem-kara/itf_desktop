#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
test_log_rotation.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Log rotasyonunu test etmek için basit örnek script.

Kullanım:
  python test_log_rotation.py [--generate]
  --generate: Çok sayıda log yazarak rotasyonu test et (simülasyon)
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.logger import logger
from core.log_manager import LogStatistics, LogCleanup, LogMonitor
from core.paths import LOG_DIR


def test_basic_logging():
    """Basit logging test."""
    print("\n" + "="*70)
    print("1. BASIC LOGGING TEST")
    print("="*70)
    
    logger.info("ℹ️  Bu bir info mesajıdır")
    logger.warning("⚠️  Bu bir uyarı mesajıdır")
    logger.error("❌ Bu bir hata mesajıdır")
    
    print("✓ Logger başarıyla yazıyor\n")


def test_log_statistics():
    """Log istatistikleri test."""
    print("="*70)
    print("2. LOG STATISTICS")
    print("="*70)
    
    stats = LogStatistics.get_log_stats()
    total_size = LogStatistics.get_total_log_size()
    
    print(f"\nToplam boyut: {total_size:.2f} MB\n")
    print(f"{'Dosya Adı':<30} {'Boyut (MB)':<15} {'Satırlar':<10} {'Son Güncelleme':<20}")
    print("-" * 75)
    
    for name, info in sorted(stats.items()):
        print(
            f"{name:<30} {info['size_mb']:<15.2f} {info['lines']:<10} {info['last_modified']:<20}"
        )


def test_log_health():
    """Log sağlık durumu test."""
    print("\n" + "="*70)
    print("3. LOG HEALTH CHECK")
    print("="*70 + "\n")
    
    health = LogMonitor.check_log_health()
    
    print(f"Status: {health['status']}")
    print(f"Total Size: {health['total_size_mb']:.2f} MB\n")
    
    if health['messages']:
        print("Mesajlar:")
        for msg in health['messages']:
            print(f"  {msg}")
    else:
        print("✓ Log sağlığı iyi\n")


def test_cleanup():
    """Cleanup işlemlerini test."""
    print("\n" + "="*70)
    print("4. LOG CLEANUP")
    print("="*70)
    
    # Eski logları temizle (test: 0 gün, yani çok eski)
    print("\nOld log cleanup (7+ gün)...")
    deleted, freed = LogCleanup.cleanup_old_logs(days=7)
    print(f"Silinen: {deleted} dosya, Boşaltılan: {freed/(1024*1024):.2f} MB")
    
    # Disk alanını yönet (100 MB limit)
    print("\nSpace management (100 MB limit)...")
    deleted, freed = LogCleanup.cleanup_by_space(max_size_mb=100)
    print(f"Silinen: {deleted} dosya, Boşaltılan: {freed/(1024*1024):.2f} MB")


def test_generate_logs(count=50):
    """
    Çok sayıda log üretarak rotasyonu test et.
    (Not: RotatingFileHandler'ın boyut-based rotasyonunu test için)
    """
    print("\n" + "="*70)
    print(f"5. GENERATING {count} TEST LOGS (Rotasyonu tetikle)")
    print("="*70 + "\n")
    
    for i in range(count):
        logger.info(f"Test log #{i+1}: " + "x" * 100)
        if (i+1) % 10 == 0:
            print(f"✓ {i+1} log yazıldı...")
    
    # Rotasyon sonrası istatistikleri göster
    print("\nRotasyon sonrası istatistikleri:")
    test_log_statistics()


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Log rotasyonu test scripti")
    parser.add_argument("--generate", action="store_true", help="Test logları oluştur (rotasyonu tetikle)")
    parser.add_argument("--count", type=int, default=50, help="Üretilecek test log sayısı (default: 50)")
    
    args = parser.parse_args()
    
    print("\n" + "🔍 LOG ROTATION TEST ".center(70, "="))
    print(f"Log Dizini: {LOG_DIR}\n")
    
    # Test 1: Basic logging
    test_basic_logging()
    
    # Test 2: İstatistikler
    test_log_statistics()
    
    # Test 3: Sağlık kontrolü
    test_log_health()
    
    # Test 4: Cleanup
    test_cleanup()
    
    # Test 5: Rotasyonu tetikle (isteğe bağlı)
    if args.generate:
        test_generate_logs(count=args.count)
    
    print("\n" + "="*70)
    print("✓ TÜM TESTLER TAMAMLANDI")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()
