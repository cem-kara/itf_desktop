# database/google/exceptions.py
"""
Google servis katmanı için özel hata sınıfları.

Bu modül tüm Google işlemleri için ortak hata tiplerini tanımlar.
"""


class GoogleServisHatasi(Exception):
    """Google servis katmanı için temel hata sınıfı"""
    pass


class InternetBaglantiHatasi(GoogleServisHatasi):
    """İnternet bağlantısı yokken yapılan işlemler için"""
    pass


class KimlikDogrulamaHatasi(GoogleServisHatasi):
    """OAuth kimlik doğrulama hataları için"""
    pass


class VeritabaniBulunamadiHatasi(GoogleServisHatasi):
    """Google Sheets dosyası veya sayfası bulunamadığında"""
    pass


class APIKotaHatasi(GoogleServisHatasi):
    """Google API quota aşıldığında"""
    pass


class YetkiHatasi(GoogleServisHatasi):
    """Erişim yetkisi yokken"""
    pass
