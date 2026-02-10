# database/google/__init__.py
"""
Google servis katmanı.

Bu paket Google Sheets ve Google Drive işlemleri için modülerleştirilmiş
bir arayüz sağlar.

Modüller:
    - exceptions: Özel hata sınıfları
    - auth: OAuth kimlik doğrulama
    - sheets: Google Sheets işlemleri
    - drive: Google Drive işlemleri
    - signals: Qt sinyalleri
    - utils: Yardımcı fonksiyonlar

Kullanım:
    from database.google import get_worksheet, GoogleDriveService
    
    # Worksheet al
    ws = get_worksheet("Personel")
    
    # Drive servisi
    drive = GoogleDriveService()
    link = drive.upload_file("dosya.pdf")
"""

# Hata sınıfları
from .exceptions import (
    GoogleServisHatasi,
    InternetBaglantiHatasi,
    KimlikDogrulamaHatasi,
    VeritabaniBulunamadiHatasi,
    APIKotaHatasi,
    YetkiHatasi
)

# Auth
from .auth import (
    GoogleAuthManager,
    get_credentials,
    get_sheets_client,
    reset_auth
)

# Sheets
from .sheets import (
    GoogleSheetsManager,
    get_sheets_manager,
    get_worksheet,
    veritabani_getir  # Backward compatibility
)

# Drive
from .drive import (
    GoogleDriveService,
    get_drive_service
)

# Signals
from .signals import GoogleBaglantiSinyalleri

# Utils
from .utils import (
    internet_kontrol,
    db_ayarlarini_yukle,
    extract_file_id_from_link,
    TABLE_TO_SHEET_MAP
)


__all__ = [
    # Exceptions
    'GoogleServisHatasi',
    'InternetBaglantiHatasi',
    'KimlikDogrulamaHatasi',
    'VeritabaniBulunamadiHatasi',
    'APIKotaHatasi',
    'YetkiHatasi',
    
    # Auth
    'GoogleAuthManager',
    'get_credentials',
    'get_sheets_client',
    'reset_auth',
    
    # Sheets
    'GoogleSheetsManager',
    'get_sheets_manager',
    'get_worksheet',
    'veritabani_getir',
    
    # Drive
    'GoogleDriveService',
    'get_drive_service',
    
    # Signals
    'GoogleBaglantiSinyalleri',
    
    # Utils
    'internet_kontrol',
    'db_ayarlarini_yukle',
    'extract_file_id_from_link',
    'TABLE_TO_SHEET_MAP',
]


__version__ = '2.0.0'
__author__ = 'ITF Team'
