#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""TC Kimlik No algoritma test scripti."""

def validate_tc_kimlik_no(tc_str: str) -> bool:
    """Düzeltilmiş TC Kimlik No algoritması."""
    if not tc_str or len(tc_str) != 11 or not tc_str.isdigit():
        return False
    if tc_str[0] == '0':
        return False
    
    # İLK 9 HANE kullanılır (10. hane zaten kontrol hanesi)
    sum_odd = sum(int(tc_str[i]) for i in range(0, 9, 2))   # indices: 0,2,4,6,8
    sum_even = sum(int(tc_str[i]) for i in range(1, 9, 2))  # indices: 1,3,5,7
    
    expected_10th = (sum_odd * 7 - sum_even) % 10
    expected_11th = (sum_odd + sum_even + expected_10th) % 10
    
    actual_10th = int(tc_str[9])
    actual_11th = int(tc_str[10])
    
    return actual_10th == expected_10th and actual_11th == expected_11th


if __name__ == "__main__":
    print("═══ TC KİMLİK NO DOĞRULAMA TESTİ ═══\n")
    
    test_cases = [
        ("60142116854", True,  "Gerçek TC #1"),
        ("42166877898", True,  "Gerçek TC #2"),
        ("16619330100", True,  "Gerçek TC #3"),
        ("11111111111", False, "Fake TC (hepsi 1)"),
        ("01234567890", False, "İlk hane 0"),
        ("123",         False, "Çok kısa"),
    ]
    
    passed = 0
    failed = 0
    
    for tc, expected, desc in test_cases:
        result = validate_tc_kimlik_no(tc)
        status = "✓ PASS" if result == expected else "✗ FAIL"
        outcome = "GEÇERLİ" if result else "GEÇERSİZ"
        
        if result == expected:
            passed += 1
        else:
            failed += 1
            
        print(f"{status} | {tc} → {outcome:9} | {desc}")
    
    print(f"\n{'─'*50}")
    print(f"Toplam: {len(test_cases)} | Başarılı: {passed} | Başarısız: {failed}")
    
    if failed == 0:
        print("\n🎉 TÜM TESTLER GEÇTİ! Algoritma doğru çalışıyor.")
    else:
        print(f"\n⚠️  {failed} test başarısız!")
