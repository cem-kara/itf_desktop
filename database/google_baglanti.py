# -*- coding: utf-8 -*-
import os
import json
import logging
import socket
import threading
import gspread
from pathlib import Path
from typing import Optional, List, Dict, Any

# PySide6 Sinyalleri için
from PySide6.QtCore import QObject, Signal

# Google Auth Kütüphaneleri
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.auth.exceptions import TransportError, RefreshError


# Loglama Ayarları
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("GoogleService")

SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

# =============================================================================
# 1. ÖZEL HATA SINIFLARI
# =============================================================================
class GoogleServisHatasi(Exception):
    pass

class InternetBaglantiHatasi(GoogleServisHatasi):
    pass

class KimlikDogrulamaHatasi(GoogleServisHatasi):
    pass

class VeritabaniBulunamadiHatasi(GoogleServisHatasi):
    pass

# =============================================================================
# 2. HATA BİLDİRİM SİNYALCISI
# =============================================================================
class GoogleBaglantiSinyalleri(QObject):
    hata_olustu = Signal(str, str) # (Baslik, Mesaj)

    _instance = None
    _lock = threading.Lock() # Sinyalci için de Lock

    @classmethod
    def get_instance(cls):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = GoogleBaglantiSinyalleri()
        return cls._instance

# =============================================================================
# 3. YARDIMCI ARAÇLAR
# =============================================================================
def db_ayarlarini_yukle():
    mevcut_dizin = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(mevcut_dizin, 'ayarlar.json')
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get("veritabani_yapisi", {})
    except Exception as e:
        logger.error(f"ayarlar.json okunamadı: {e}")
        return {}

def internet_kontrol():
    try:
        socket.create_connection(("www.google.com", 80), timeout=3)
        return True
    except OSError:
        return False

DB_CONFIG = db_ayarlarini_yukle()

# =============================================================================
# 4. KİMLİK DOĞRULAMA YÖNETİMİ (THREAD-SAFE)
# =============================================================================
_sheets_client = None
_client_lock = threading.Lock() # İstemci oluşturma kilidi

def _get_credentials():
    creds = None
    base_dir = os.path.dirname(os.path.abspath(__file__))
    token_path = os.path.join(base_dir, 'token.json')
    cred_path = os.path.join(base_dir, 'credentials.json')

    if os.path.exists(token_path):
        try:
            creds = Credentials.from_authorized_user_file(token_path, SCOPES)
        except Exception:
            logger.warning("Token dosyası bozuk.")
            creds = None
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                if not internet_kontrol():
                    raise InternetBaglantiHatasi("Token yenilemek için internet gerekli.")
                creds.refresh(Request())
            except (TransportError, RefreshError) as e:
                logger.error(f"Token yenileme hatası: {e}")
                raise KimlikDogrulamaHatasi("Oturum süresi doldu.")
        else:
            if not os.path.exists(cred_path):
                raise FileNotFoundError("credentials.json bulunamadı!")
            
            flow = InstalledAppFlow.from_client_secrets_file(cred_path, SCOPES)
            creds = flow.run_local_server(port=0)
        
        with open(token_path, 'w') as token:
            token.write(creds.to_json())

    return creds

def _get_sheets_client():
    """Gspread istemcisini Thread-Safe Singleton olarak döndürür."""
    global _sheets_client
    
    if not internet_kontrol():
        GoogleBaglantiSinyalleri.get_instance().hata_olustu.emit("Bağlantı Hatası", "İnternet yok.")
        raise InternetBaglantiHatasi("İnternet bağlantısı yok.")

    # Çift Kontrollü Kilitleme (Double-Checked Locking)
    if not _sheets_client:
        with _client_lock:
            if not _sheets_client:
                try:
                    creds = _get_credentials()
                    _sheets_client = gspread.authorize(creds)
                except Exception as e:
                    msg = f"Google Sheets yetkilendirme hatası: {str(e)}"
                    logger.error(msg)
                    raise KimlikDogrulamaHatasi(msg)
            
    return _sheets_client

# =============================================================================
# 5. VERİTABANI ERİŞİM FONKSİYONLARI
# =============================================================================

def veritabani_getir(vt_tipi: str, sayfa_adi: str):
    """
    KLASİK YÖNTEM: Worksheet nesnesini döndürür.
    Veri yazma (append_row, update_cell) işlemleri için bunu kullanın.
    Cache KULLANMAZ (Worksheet nesnesi hafiftir, asıl yük get_all_records'tadır).
    """
    spreadsheet_name = None
    try:
        client = _get_sheets_client()
        
        if vt_tipi in DB_CONFIG:
            spreadsheet_name = DB_CONFIG[vt_tipi]["dosya"]
        else:
            db_map = {
                'personel': 'itf_personel_vt',
                'sabit':    'itf_sabit_vt',
                'cihaz':    'itf_cihaz_vt',
                'user':     'itf_user_vt',
                'rke':      'itf_rke_vt'
            }
            spreadsheet_name = db_map.get(vt_tipi)
            
        if not spreadsheet_name:
            raise ValueError(f"'{vt_tipi}' için veritabanı tanımı bulunamadı.")

        try:
            sh = client.open(spreadsheet_name)
        except gspread.SpreadsheetNotFound:
            raise VeritabaniBulunamadiHatasi(f"Dosya bulunamadı: {spreadsheet_name}")

        try:
            ws = sh.worksheet(sayfa_adi)
            return ws
        except gspread.WorksheetNotFound:
            raise VeritabaniBulunamadiHatasi(f"Sayfa bulunamadı: {sayfa_adi}")

    except Exception as e:
        logger.error(f"DB Hatası ({vt_tipi}/{sayfa_adi}): {str(e)}")
        raise e

# =============================================================================
# 6. GOOGLE DRIVE SERVİSİ
# =============================================================================
class GoogleDriveService:
    def __init__(self):
        try:
            self.creds = _get_credentials()
            self.service = build('drive', 'v3', credentials=self.creds)
        except Exception as e:
            logger.error(f"Drive servisi başlatılamadı: {e}")
            raise GoogleServisHatasi(f"Drive bağlantı hatası: {e}")

    def upload_file(self, file_path: str, parent_folder_id: str = None, custom_name: str = None) -> Optional[str]:
        if not os.path.exists(file_path):
            return None

        try:
            path_obj = Path(file_path)
            dosya_adi = custom_name if custom_name else path_obj.name
            
            file_metadata = {
                'name': dosya_adi, 
                'parents': [parent_folder_id] if parent_folder_id else []
            }
            
            media = MediaFileUpload(str(path_obj), resumable=True)
            
            file = self.service.files().create(
                body=file_metadata, 
                media_body=media, 
                fields='id, webViewLink'
            ).execute()
            
            self.service.permissions().create(
                fileId=file.get('id'), 
                body={'role': 'reader', 'type': 'anyone'}
            ).execute()
            
            return file.get('webViewLink')

        except Exception as e:
            logger.error(f"Drive yükleme hatası: {e}")
            if not internet_kontrol():
                raise InternetBaglantiHatasi("Drive yüklemesi sırasında internet koptu.")
            raise GoogleServisHatasi(f"Dosya yüklenemedi: {e}")

    def download_file(self, file_id: str, dest_path: str) -> bool:
        """Drive'dan dosya indir."""
        try:
            from googleapiclient.http import MediaIoBaseDownload
            import io
            request = self.service.files().get_media(fileId=file_id)
            fh = io.FileIO(dest_path, 'wb')
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()
            fh.close()
            logger.info(f"Drive dosya indirildi: {file_id} → {dest_path}")
            return True
        except Exception as e:
            logger.error(f"Drive indirme hatası ({file_id}): {e}")
            return False

    def delete_file(self, file_id: str) -> bool:
        """Drive'dan dosya sil."""
        try:
            self.service.files().delete(fileId=file_id).execute()
            logger.info(f"Drive dosya silindi: {file_id}")
            return True
        except Exception as e:
            logger.error(f"Drive silme hatası ({file_id}): {e}")
            return False

    @staticmethod
    def extract_file_id(drive_link: str) -> Optional[str]:
        """Drive linkinden file ID çıkar."""
        import re
        if not drive_link:
            return None
        match = re.search(r'/d/([a-zA-Z0-9_-]+)', drive_link)
        if match:
            return match.group(1)
        match = re.search(r'id=([a-zA-Z0-9_-]+)', drive_link)
        if match:
            return match.group(1)
        return None
    

# ═══════════════════════════════════════════════════════
# 7. GSHEET_MANAGER KÖPRÜSÜ
# ═══════════════════════════════════════════════════════

# Tablo adından → (vt_tipi, sayfa_adi) eşlemesi
_TABLE_TO_SHEET_MAP = {
    # personel vt
    "Personel":      ("personel", "Personel"),
    "Izin_Giris":    ("personel", "Izin_Giris"),
    "Izin_Bilgi":    ("personel", "Izin_Bilgi"),
    "FHSZ_Puantaj":  ("personel", "FHSZ_Puantaj"),

    # cihaz vt
    "Cihazlar":       ("cihaz", "Cihazlar"),
    "Cihaz_Ariza":    ("cihaz", "Cihaz_Ariza"),
    "Ariza_Islem":    ("cihaz", "Ariza_Islem"),
    "Periyodik_Bakim":("cihaz", "Periyodik_Bakim"),
    "Kalibrasyon":    ("cihaz", "Kalibrasyon"),

    # rke vt
    "RKE_List":       ("rke", "RKE_List"),
    "RKE_Muayene":    ("rke", "RKE_Muayene"),

    # sabit vt
    "Sabitler":       ("sabit", "Sabitler"),
    "Tatiller":       ("sabit", "Tatiller"),
}


def get_worksheet(table_name):
    """
    Tablo adına göre Google Sheets worksheet nesnesini döner.
    gsheet_manager.py tarafından kullanılır.
    """
    mapping = _TABLE_TO_SHEET_MAP.get(table_name)

    if not mapping:
        raise ValueError(f"'{table_name}' için Google Sheets eşlemesi bulunamadı")

    vt_tipi, sayfa_adi = mapping
    return veritabani_getir(vt_tipi, sayfa_adi)