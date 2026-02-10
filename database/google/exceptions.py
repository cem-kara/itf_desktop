# database/google/exceptions.py
"""
Google servisleri için özel exception tanımları.
"""

class GoogleServisHatasi(Exception):
    """Google servisleri ile ilgili genel hata"""
    pass


class InternetBaglantiHatasi(GoogleServisHatasi):
    """İnternet bağlantısı yok veya koptu"""
    pass


class KimlikDogrulamaHatasi(GoogleServisHatasi):
    """Google OAuth kimlik doğrulama hatası"""
    pass


class VeritabaniBulunamadiHatasi(GoogleServisHatasi):
    """Google Sheets dosyası veya worksheet bulunamadı"""
    pass
