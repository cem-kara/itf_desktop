"""
Personel Validasyon Araçları
=============================

- TC Kimlik No doğrulama
- E-posta doğrulama
- Kullanıcı adı üretme
"""

import re
from core.logger import logger


def validate_tc_kimlik_no(tc_str: str) -> bool:
    """
    TC Kimlik No algoritması.

    Kurallar:
    - 11 hane olmalı
    - İlk hane 0 olamaz
    - 10. ve 11. haneler kontrol algoritmasına uygun olmalı
    """
    if not tc_str or len(tc_str) != 11 or not tc_str.isdigit():
        return False
    if tc_str[0] == "0":
        return False

    sum_odd = sum(int(tc_str[i]) for i in range(0, 9, 2))
    sum_even = sum(int(tc_str[i]) for i in range(1, 9, 2))

    expected_10th = (sum_odd * 7 - sum_even) % 10
    expected_11th = (sum_odd + sum_even + expected_10th) % 10

    actual_10th = int(tc_str[9])
    actual_11th = int(tc_str[10])

    is_valid = actual_10th == expected_10th and actual_11th == expected_11th

    if not is_valid:
        logger.debug(f"TC kontrol hatasi: {tc_str}")

    return is_valid


def validate_email(email_str: str) -> bool:
    """Basit e-posta format kontrolu."""
    if not email_str:
        return True
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email_str))


def generate_username_from_name(ad_soyad: str) -> str:
    """
    Ad soyaddan kullanici adi uretir.

    Ornek:
    - "Cem Kara" -> "CKARA"
    - "Ahmet Cem Kara" -> "ACKARA"
    """
    if not ad_soyad or not ad_soyad.strip():
        return ""

    parts = ad_soyad.strip().split()
    if not parts:
        return ""

    surname = parts[-1]
    initials = "".join([p[0] for p in parts[:-1]])
    return (initials + surname).upper()
