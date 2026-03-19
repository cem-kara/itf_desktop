# -*- coding: utf-8 -*-
"""
Veri doğrulama fonksiyonları.
TC Kimlik No, email, telefon vb. validasyonlar içerir.
"""
import re
from typing import Optional
from core.logger import logger



def validate_tc_kimlik_no(tc_str: str) -> bool:
    """
    TC Kimlik No algoritması uygulaması.
    
    Kurallar:
    - 11 rakam olmalı
    - İlk basamak 0 olamaz
    - Kontrol hanesi algoritması geçerli olmalı
    
    Algoritma:
    1. Pozisyonlar 1,3,5,7,9 (indices 0,2,4,6,8) topla → S1
    2. Pozisyonlar 2,4,6,8 (indices 1,3,5,7) topla → S2
    3. 10.basamak = (S1 * 7 - S2) % 10
    4. 11.basamak = (S1 + S2 + 10.basamak) % 10
    
    Args:
        tc_str: TC Kimlik No string (11 haneli rakam)
        
    Returns:
        True: Geçerli TC Kimlik No
        False: Geçersiz
        
    Examples:
        >>> validate_tc_kimlik_no("12345678901")
        False
        >>> validate_tc_kimlik_no("10000000146")
        True
    """
    if not tc_str or len(tc_str) != 11 or not tc_str.isdigit():
        return False
    
    if tc_str[0] == '0':
        return False
    
    # Tek pozisyonlar (1, 3, 5, 7, 9) = indices (0, 2, 4, 6, 8)
    sum_odd = sum(int(tc_str[i]) for i in range(0, 9, 2))
    # Çift pozisyonlar (2, 4, 6, 8) = indices (1, 3, 5, 7)
    sum_even = sum(int(tc_str[i]) for i in range(1, 9, 2))
    
    # 10. basamak (index 9) hesaplama
    expected_10th = (sum_odd * 7 - sum_even) % 10
    # 11. basamak (index 10) hesaplama
    expected_11th = (sum_odd + sum_even + expected_10th) % 10
    
    actual_10th = int(tc_str[9])
    actual_11th = int(tc_str[10])
    
    is_valid = actual_10th == expected_10th and actual_11th == expected_11th
    
    # Debug log (sadece hata durumunda)
    if not is_valid:
        logger.debug(f"TC kontrol hatası: {tc_str}")
        logger.debug(f"  Tek pozisyonlar (1,3,5,7,9): {sum_odd}")
        logger.debug(f"  Çift pozisyonlar (2,4,6,8,10): {sum_even}")
        logger.debug(f"  10. basamak: beklenen={expected_10th}, gerçek={actual_10th}")
        logger.debug(f"  11. basamak: beklenen={expected_11th}, gerçek={actual_11th}")
    
    return is_valid


def validate_email(email_str: str) -> bool:
    """
    Email format doğrulaması.
    
    Args:
        email_str: Email adresi
        
    Returns:
        True: Geçerli email formatı
        False: Geçersiz
        
    Examples:
        >>> validate_email("test@example.com")
        True
        >>> validate_email("invalid-email")
        False
        >>> validate_email("")
        True  # Opsiyonel alan
    """
    if not email_str:
        return True  # Opsiyonel alan
    
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email_str))


def validate_phone_number(phone_str: str) -> bool:
    """
    Telefon numarası format doğrulaması.
    Türkiye GSM formatı: 05XX XXX XX XX veya 5XXXXXXXXX
    
    Args:
        phone_str: Telefon numarası
        
    Returns:
        True: Geçerli telefon formatı
        False: Geçersiz
        
    Examples:
        >>> validate_phone_number("05551234567")
        True
        >>> validate_phone_number("0555 123 45 67")
        True
        >>> validate_phone_number("123456")
        False
    """
    if not phone_str:
        return True  # Opsiyonel alan
    
    # Sadece rakamları al
    digits = ''.join(c for c in phone_str if c.isdigit())
    
    # 10 veya 11 haneli olmalı
    if len(digits) == 10:
        # 5XX formatı
        return digits[0] == '5'
    elif len(digits) == 11:
        # 05XX formatı
        return digits[0] == '0' and digits[1] == '5'
    
    return False


def validate_not_empty(value: str) -> bool:
    """
    Değerin boş olmadığını kontrol eder.
    
    Args:
        value: Kontrol edilecek değer
        
    Returns:
        True: Değer dolu
        False: Değer boş
    """
    return bool(value and value.strip())


def validate_length(value: str, min_len: int = 0, max_len: Optional[int] = None) -> bool:
    """
    Değerin uzunluk kontrolü.
    
    Args:
        value: Kontrol edilecek değer
        min_len: Minimum uzunluk (varsayılan: 0)
        max_len: Maximum uzunluk (varsayılan: None - sınırsız)
        
    Returns:
        True: Uzunluk geçerli
        False: Uzunluk geçersiz
    """
    if not value:
        return min_len == 0
    
    length = len(value)
    
    if length < min_len:
        return False
    
    if max_len is not None and length > max_len:
        return False
    
    return True


def validate_numeric(value: str) -> bool:
    """
    Değerin sadece rakam içerip içermediğini kontrol eder.
    
    Args:
        value: Kontrol edilecek değer
        
    Returns:
        True: Sadece rakam içeriyor
        False: Rakam dışı karakter var
    """
    if not value:
        return True  # Opsiyonel alan
    
    return value.isdigit()


def validate_alphanumeric(value: str) -> bool:
    """
    Değerin alfanumerik (harf ve rakam) olup olmadığını kontrol eder.
    
    Args:
        value: Kontrol edilecek değer
        
    Returns:
        True: Alfanumerik
        False: Özel karakter içeriyor
    """
    if not value:
        return True  # Opsiyonel alan
    
    return value.replace(' ', '').isalnum()


def validate_date_format(date_str: str, format_pattern: str = r'^\d{2}\.\d{2}\.\d{4}$') -> bool:
    """
    Tarih format kontrolü.
    
    Args:
        date_str: Tarih string
        format_pattern: Regex pattern (varsayılan: DD.MM.YYYY)
        
    Returns:
        True: Format geçerli
        False: Format geçersiz
    """
    if not date_str:
        return True  # Opsiyonel alan
    
    return bool(re.match(format_pattern, date_str))
