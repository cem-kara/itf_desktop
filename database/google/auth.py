# database/google/auth.py
"""
Google OAuth kimlik doğrulama yönetimi.

Bu modül Google API'lerine erişim için kimlik doğrulama işlemlerini yönetir.
Thread-safe singleton pattern kullanır.
"""

import os
import logging
import threading
from typing import Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.exceptions import TransportError, RefreshError
import gspread

from .exceptions import (
    InternetBaglantiHatasi,
    KimlikDogrulamaHatasi
)
from .utils import internet_kontrol


logger = logging.getLogger(__name__)


# Google API izinleri
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]


class GoogleAuthManager:
    """
    Google kimlik doğrulama yöneticisi.
    
    Thread-safe singleton pattern ile tek instance garanti eder.
    OAuth token'ları yönetir ve gspread client döndürür.
    """
    
    _instance: Optional['GoogleAuthManager'] = None
    _lock = threading.Lock()
    
    def __init__(self):
        """Doğrudan instance oluşturmayın, get_instance() kullanın"""
        self._sheets_client: Optional[gspread.Client] = None
        self._client_lock = threading.Lock()
        
        # Token ve credentials dosya yolları
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.token_path = os.path.join(base_dir, 'token.json')
        self.credentials_path = os.path.join(base_dir, 'credentials.json')
    
    @classmethod
    def get_instance(cls) -> 'GoogleAuthManager':
        """Thread-safe singleton instance döndürür"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = GoogleAuthManager()
        return cls._instance
    
    def get_credentials(self) -> Credentials:
        """
        Google API credentials döndürür.
        
        Akış:
        1. token.json'dan mevcut credentials'ı yükle
        2. Geçerli değilse refresh et
        3. Refresh edilemezse yeni auth flow başlat
        
        Returns:
            Credentials: Geçerli Google OAuth credentials
            
        Raises:
            KimlikDogrulamaHatasi: Auth işlemi başarısız
            InternetBaglantiHatasi: İnternet bağlantısı yok
        """
        creds = None
        
        # Mevcut token'ı yükle
        if os.path.exists(self.token_path):
            try:
                creds = Credentials.from_authorized_user_file(
                    self.token_path, 
                    SCOPES
                )
                logger.debug("Token dosyasından credentials yüklendi")
            except Exception as e:
                logger.warning(f"Token dosyası bozuk: {e}")
                creds = None
        
        # Token geçerli mi kontrol et
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                # Token süre dolmuş ama refresh token var
                try:
                    if not internet_kontrol():
                        raise InternetBaglantiHatasi(
                            "Token yenilemek için internet gerekli"
                        )
                    
                    logger.info("Token yenileniyor...")
                    creds.refresh(Request())
                    logger.info("Token başarıyla yenilendi")
                    
                except (TransportError, RefreshError) as e:
                    logger.error(f"Token yenileme hatası: {e}")
                    raise KimlikDogrulamaHatasi(
                        "Oturum süresi doldu. Lütfen tekrar giriş yapın."
                    )
            else:
                # Yeni auth flow gerekli
                if not os.path.exists(self.credentials_path):
                    raise FileNotFoundError(
                        f"credentials.json bulunamadı: {self.credentials_path}"
                    )
                
                logger.info("Yeni auth flow başlatılıyor...")
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_path, 
                    SCOPES
                )
                creds = flow.run_local_server(port=0)
                logger.info("Auth flow tamamlandı")
            
            # Token'ı kaydet
            with open(self.token_path, 'w') as token:
                token.write(creds.to_json())
            logger.debug("Token dosyasına kaydedildi")
        
        return creds
    
    def get_sheets_client(self) -> gspread.Client:
        """
        Thread-safe gspread client döndürür.
        
        Returns:
            gspread.Client: Yetkilendirilmiş gspread client
            
        Raises:
            InternetBaglantiHatasi: İnternet bağlantısı yok
            KimlikDogrulamaHatasi: Yetkilendirme başarısız
        """
        if not internet_kontrol():
            raise InternetBaglantiHatasi("İnternet bağlantısı yok")
        
        # Double-checked locking
        if self._sheets_client is None:
            with self._client_lock:
                if self._sheets_client is None:
                    try:
                        creds = self.get_credentials()
                        self._sheets_client = gspread.authorize(creds)
                        logger.info("Gspread client oluşturuldu")
                    except Exception as e:
                        msg = f"Google Sheets yetkilendirme hatası: {e}"
                        logger.error(msg)
                        raise KimlikDogrulamaHatasi(msg)
        
        return self._sheets_client
    
    def reset_client(self):
        """
        Client'ı sıfırla (yeniden auth için).
        
        Kullanım: Token expire olduğunda veya manuel reset gerektiğinde
        """
        with self._client_lock:
            self._sheets_client = None
        logger.info("Sheets client sıfırlandı")


# Convenience functions
def get_credentials() -> Credentials:
    """Global credentials döndürür"""
    return GoogleAuthManager.get_instance().get_credentials()


def get_sheets_client() -> gspread.Client:
    """Global sheets client döndürür"""
    return GoogleAuthManager.get_instance().get_sheets_client()


def reset_auth():
    """Auth'u sıfırla"""
    GoogleAuthManager.get_instance().reset_client()
