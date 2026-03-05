# -*- coding: utf-8 -*-
"""
Metin formatlama yardımcı fonksiyonları.
Türkçe karakter desteği ile çeşitli formatlama işlemleri sağlar.
"""


def turkish_title_case(text: str) -> str:
    """
    Türkçe karakterleri destekleyen Title Case formatter.
    Her kelimenin ilk harfini büyük, geri kalanını küçük yapar.
    Baştaki ve sondaki boşlukları KORUR, ortadaki boşlukları normalize eder.
    
    Args:
        text: Formatlanacak metin
        
    Returns:
        Formatlanmış metin
        
    Examples:
        >>> turkish_title_case("ahmet cem KARA")
        "Ahmet Cem Kara"
        >>> turkish_title_case("istanbul üniversitesi")
        "İstanbul Üniversitesi"
    """
    if not text:
        return text
    
    # Baştaki/sondaki boşluk korunduğu için, sadece üst/alt boşlukları tut
    # Ama formatlama için strip() yapıp sonra sonda boşluk varsa geri ekle
    leading_spaces = len(text) - len(text.lstrip())
    trailing_spaces = len(text) - len(text.rstrip())
    
    # Formatlama için strip'le
    text_stripped = text.strip()
    
    if not text_stripped:
        # Sadece boşluk ise orijinali döndür
        return text
    
    # Türkçe karakter dönüşüm haritası
    turkish_upper = {
        'i': 'İ', 'ı': 'I', 'ş': 'Ş', 'ğ': 'Ğ', 'ü': 'Ü', 'ö': 'Ö', 'ç': 'Ç',
        'İ': 'İ', 'I': 'I', 'Ş': 'Ş', 'Ğ': 'Ğ', 'Ü': 'Ü', 'Ö': 'Ö', 'Ç': 'Ç'
    }
    turkish_lower = {
        'İ': 'i', 'I': 'ı', 'Ş': 'ş', 'Ğ': 'ğ', 'Ü': 'ü', 'Ö': 'ö', 'Ç': 'ç',
        'i': 'i', 'ı': 'ı', 'ş': 'ş', 'ğ': 'ğ', 'ü': 'ü', 'ö': 'ö', 'ç': 'ç'
    }
    
    def upper_first(char: str) -> str:
        """İlk karakteri büyük yap (Türkçe destekli)."""
        return turkish_upper.get(char, char.upper())
    
    def lower_char(char: str) -> str:
        """Karakteri küçük yap (Türkçe destekli)."""
        return turkish_lower.get(char, char.lower())
    
    def format_word(word: str) -> str:
        """Tek bir kelimeyi formatla."""
        if not word:
            return word
        return upper_first(word[0]) + ''.join(lower_char(c) for c in word[1:])
    
    # Kelimeleri ayır (boşlukları normalize et)
    import re
    words = re.split(r'\s+', text_stripped)
    # Boş stringler varsa kaldır
    words = [w for w in words if w]
    
    # Her kelimeyi formatla
    formatted_words = [format_word(word) for word in words]
    
    # Tek boşluk ile birleştir
    formatted = ' '.join(formatted_words)
    
    # Baş/sonda boşlukları geri ekle
    formatted = ' ' * leading_spaces + formatted + ' ' * trailing_spaces
    
    return formatted


def turkish_upper(text: str) -> str:
    """
    Türkçe karakterleri destekleyen uppercase dönüşümü.
    
    Args:
        text: Dönüştürülecek metin
        
    Returns:
        Büyük harfli metin
        
    Examples:
        >>> turkish_upper("istanbul")
        "İSTANBUL"
    """
    if not text:
        return text
    
    tr_map = {
        'i': 'İ', 'ı': 'I', 'ş': 'Ş', 'ğ': 'Ğ', 'ü': 'Ü', 'ö': 'Ö', 'ç': 'Ç'
    }
    
    result = []
    for char in text:
        result.append(tr_map.get(char, char.upper()))
    
    return ''.join(result)


def turkish_lower(text: str) -> str:
    """
    Türkçe karakterleri destekleyen lowercase dönüşümü.
    
    Args:
        text: Dönüştürülecek metin
        
    Returns:
        Küçük harfli metin
        
    Examples:
        >>> turkish_lower("İSTANBUL")
        "istanbul"
    """
    if not text:
        return text
    
    tr_map = {
        'İ': 'i', 'I': 'ı', 'Ş': 'ş', 'Ğ': 'ğ', 'Ü': 'ü', 'Ö': 'ö', 'Ç': 'ç'
    }
    
    result = []
    for char in text:
        result.append(tr_map.get(char, char.lower()))
    
    return ''.join(result)


def capitalize_first_letter(text: str) -> str:
    """
    Sadece ilk harfi büyük yapar (çok satırlı içerik için).
    Cümlenin ilk harfini büyük, geri kalanı olduğu gibi bırakır.
    
    Args:
        text: Formatlanacak metin
        
    Returns:
        İlk harfi büyük metin
        
    Examples:
        >>> capitalize_first_letter("merhaba dünya. bu bir test.")
        "Merhaba dünya. bu bir test."
    """
    if not text:
        return text
    
    # İlk geçerli karakteri bul
    for i, char in enumerate(text):
        if char.strip():  # Boşluk değilse
            # Türkçe karakter dönüşümü
            if char == 'i':
                return 'İ' + text[i+1:]
            elif char == 'ı':
                return 'I' + text[i+1:]
            else:
                return text[:i] + char.upper() + text[i+1:]
    
    return text


def normalize_whitespace(text: str) -> str:
    """
    Fazla boşlukları temizler ve normalize eder.
    
    Args:
        text: Temizlenecek metin
        
    Returns:
        Normalize edilmiş metin
        
    Examples:
        >>> normalize_whitespace("Ahmet   Cem  KARA")
        "Ahmet Cem KARA"
    """
    if not text:
        return text
    
    # Birden fazla boşluğu tek boşluğa çevir
    import re
    return re.sub(r'\s+', ' ', text).strip()


def format_phone_number(phone: str) -> str:
    """
    Telefon numarasını standart formata çevirir.
    
    Args:
        phone: Telefon numarası (sadece rakamlar veya formatlanmış)
        
    Returns:
        Formatlanmış telefon: "05XX XXX XX XX"
        
    Examples:
        >>> format_phone_number("05551234567")
        "0555 123 45 67"
        >>> format_phone_number("5551234567")
        "0555 123 45 67"
    """
    if not phone:
        return phone
    
    # Sadece rakamları al
    digits = ''.join(c for c in phone if c.isdigit())
    
    # 10 haneli ise başına 0 ekle
    if len(digits) == 10 and digits[0] != '0':
        digits = '0' + digits
    
    # 11 haneli değilse olduğu gibi dön
    if len(digits) != 11:
        return phone
    
    # Format: 0XXX XXX XX XX
    return f"{digits[:4]} {digits[4:7]} {digits[7:9]} {digits[9:]}"


def sanitize_filename(filename: str) -> str:
    """
    Dosya adını temizler (geçersiz karakterleri kaldırır).
    
    Args:
        filename: Temizlenecek dosya adı
        
    Returns:
        Temizlenmiş dosya adı
        
    Examples:
        >>> sanitize_filename("Rapor*2024?.pdf")
        "Rapor_2024.pdf"
    """
    if not filename:
        return filename
    
    import re
    # Windows'ta geçersiz karakterleri değiştir
    invalid_chars = r'[<>:"/\\|?*]'
    cleaned = re.sub(invalid_chars, '_', filename)
    
    # Boşlukları alt çizgi yap
    cleaned = cleaned.replace(' ', '_')
    
    # Türkçe karakterleri koru
    return cleaned
