# database/google/utils.py
"""
Google servis katmanı için yardımcı fonksiyonlar.
"""

import os
import json
import socket
import logging
from typing import Dict, Any, Optional


logger = logging.getLogger(__name__)


def internet_kontrol(timeout: int = 3) -> bool:
    """
    İnternet bağlantısını kontrol eder.
    
    Args:
        timeout: Bağlantı timeout süresi (saniye)
        
    Returns:
        bool: İnternet varsa True, yoksa False
    """
    try:
        socket.create_connection(("www.google.com", 80), timeout=timeout)
        return True
    except OSError:
        return False


def db_ayarlarini_yukle() -> Dict[str, Any]:
    """
    Database ayarlarını veritabani.json'dan yükler.
    
    Returns:
        dict: Veritabanı yapısı konfigürasyonu
    """
    mevcut_dizin = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config_path = os.path.join(mevcut_dizin, 'veritabani.json')
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get("veritabani_yapisi", {})
    except FileNotFoundError:
        logger.warning(f"veritabani.json bulunamadı: {config_path}")
        return {}
    except json.JSONDecodeError as e:
        logger.error(f"veritabani.json parse hatası: {e}")
        return {}
    except Exception as e:
        logger.error(f"veritabani.json yükleme hatası: {e}")
        return {}


def extract_file_id_from_link(drive_link: str) -> Optional[str]:
    """
    Google Drive linkinden file ID çıkarır.
    
    Args:
        drive_link: Google Drive linki
        
    Returns:
        str: File ID veya None
        
    Examples:
        >>> extract_file_id_from_link("https://drive.google.com/file/d/1ABC/view")
        '1ABC'
        >>> extract_file_id_from_link("https://drive.google.com/open?id=1XYZ")
        '1XYZ'
    """
    import re
    
    if not drive_link:
        return None
    
    # /d/FILE_ID pattern
    match = re.search(r'/d/([a-zA-Z0-9_-]+)', drive_link)
    if match:
        return match.group(1)
    
    # id=FILE_ID pattern
    match = re.search(r'id=([a-zA-Z0-9_-]+)', drive_link)
    if match:
        return match.group(1)
    
    return None


def resolve_storage_target(all_sabit: list, folder_name: str) -> Dict[str, str]:
    """
    Sistem_DriveID kayitlarini tarayip hedef klasor icin online/offline bilgi dondurur.

    Online: Aciklama -> Drive ID
    Offline: MenuEleman -> yerel klasor adi
    """
    drive_id = ""
    offline_name = ""
    for r in all_sabit or []:
        if str(r.get("Kod", "")).strip() != "Sistem_DriveID":
            continue
        if str(r.get("MenuEleman", "")).strip() == str(folder_name).strip():
            drive_id = str(r.get("Aciklama", "")).strip()
            offline_name = str(r.get("MenuEleman", "")).strip()
            break
    return {
        "drive_folder_id": drive_id,
        "offline_folder_name": offline_name or str(folder_name).strip()
    }


# Tablo adından (vt_tipi, sayfa_adi) eşlemesi
TABLE_TO_SHEET_MAP = {
    # personel vt
    "Personel":         ("personel", "Personel"),
    "Izin_Giris":       ("personel", "Izin_Giris"),
    "Izin_Bilgi":       ("personel", "Izin_Bilgi"),
    "FHSZ_Puantaj":     ("personel", "FHSZ_Puantaj"),
    "Personel_Saglik_Takip": ("personel", "Personel_Saglik_Takip"),

    # cihaz vt
    "Cihazlar":         ("cihaz", "Cihazlar"),
    "Cihaz_Ariza":      ("cihaz", "Cihaz_Ariza"),
    "Ariza_Islem":      ("cihaz", "Ariza_Islem"),
    "Periyodik_Bakim":  ("cihaz", "Periyodik_Bakim"),
    "Kalibrasyon":      ("cihaz", "Kalibrasyon"),

    # rke vt
    "RKE_List":         ("rke", "RKE_List"),
    "RKE_Muayene":      ("rke", "RKE_Muayene"),

    # sabit vt
    "Sabitler":         ("sabit", "Sabitler"),
    "Tatiller":         ("sabit", "Tatiller"),
}


# Fallback veritabanı mapping (ayarlar.json yoksa)
DB_FALLBACK_MAP = {
    'personel': 'itf_personel_vt',
    'sabit':    'itf_sabit_vt',
    'cihaz':    'itf_cihaz_vt',
    'user':     'itf_user_vt',
    'rke':      'itf_rke_vt'
}
