# database/google/exceptions.py
"""
Google servis katmanı için özel hata sınıfları.

Bu modül tüm Google işlemleri için ortak hata tiplerini tanımlar.
"""


class GoogleServisHatasi(Exception):
    """Google servis katmanı için temel hata sınıfı"""


class InternetBaglantiHatasi(GoogleServisHatasi):
    """İnternet bağlantısı yokken yapılan işlemler için"""


class KimlikDogrulamaHatasi(GoogleServisHatasi):
    """OAuth kimlik doğrulama hataları için"""


class VeritabaniBulunamadiHatasi(GoogleServisHatasi):
    """Google Sheets dosyası veya sayfası bulunamadığında"""


class APIKotaHatasi(GoogleServisHatasi):
    """Google API quota aşıldığında"""


class YetkiHatasi(GoogleServisHatasi):
    """Erişim yetkisi yokken"""
