#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TC Kimlik No Validator Test Utility
"""

def validate_tc_kimlik_no(tc_str: str) -> tuple[bool, dict]:
    """
    TC Kimlik No algoritması uygulaması.
    Returns: (is_valid, debug_info)
    """
    debug_info = {}
    
    if not tc_str or len(tc_str) != 11 or not tc_str.isdigit():
        return False, {"error": "11 rakamdan oluşmalı"}
    if tc_str[0] == '0':
        return False, {"error": "İlk basamak 0 olamaz"}
    
    # Tek pozisyonlar (1, 3, 5, 7, 9) = indices (0, 2, 4, 6, 8)
    sum_odd = sum(int(tc_str[i]) for i in range(0, 10, 2))
    debug_info["odd_positions"] = f"{tc_str[0]}+{tc_str[2]}+{tc_str[4]}+{tc_str[6]}+{tc_str[8]} = {sum_odd}"
    
    # Çift pozisyonlar (2, 4, 6, 8, 10) = indices (1, 3, 5, 7, 9)
    sum_even = sum(int(tc_str[i]) for i in range(1, 10, 2))
    debug_info["even_positions"] = f"{tc_str[1]}+{tc_str[3]}+{tc_str[5]}+{tc_str[7]}+{tc_str[9]} = {sum_even}"
    
    # 10. basamak (index 9) hesaplama
    calc_10th = (sum_odd * 7 - sum_even) % 10
    actual_10th = int(tc_str[9])
    debug_info["digit_10"] = f"({sum_odd}*7 - {sum_even}) % 10 = {calc_10th}, gerçek: {actual_10th}"
    
    # 11. basamak (index 10) hesaplama
    calc_11th = (sum_odd + sum_even + calc_10th) % 10
    actual_11th = int(tc_str[10])
    debug_info["digit_11"] = f"({sum_odd} + {sum_even} + {calc_10th}) % 10 = {calc_11th}, gerçek: {actual_11th}"
    
    is_valid = actual_10th == calc_10th and actual_11th == calc_11th
    debug_info["result"] = "GEÇERLI" if is_valid else "GEÇERSİZ"
    
    return is_valid, debug_info


if __name__ == "__main__":
    test_cases = [
        "13033117556",  # Bilinen geçerli TC
        "12345678901",  # Test
        "99999999999",  # Test
    ]
    
    for tc in test_cases:
        valid, info = validate_tc_kimlik_no(tc)
        print(f"\n{'='*50}")
        print(f"TC: {tc}")
        for key, value in info.items():
            print(f"  {key}: {value}")
