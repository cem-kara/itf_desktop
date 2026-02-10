# database/google/utils.py
"""
Google modülleri için yardımcı fonksiyonlar ve sabitler.
"""

import os
import json
import socket
import logging
import re
from typing import Optional, Dict, Tuple


logger = logging.getLogger(__name__)


# =============================================================================
# İNTERNET KONTROL
# =============================================================================
def internet_kontrol(timeout: int = 3) -> bool:
    """İnternet bağlantısı var mı kontrol et"""
    try:
        socket.create_connection(("www.google.com", 80), timeout=timeout)
        return True
    except OSError:
        return False


# =============================================================================
# AYARLAR / DB CONFIG
# =============================================================================
def db_ayarlarini_yukle() -> Dict:
    """
    ayarlar.json içinden veritabani_yapisi bölümünü okur.
    """
    try:
        base_dir = os.path.dirname(
            os.path.dirname(os.path.abspath(__file__))
        )
        config_path = os.path.join(base_dir, "ayarlar.json")

        if not os.path.exists(config_path):
            logger.warning("ayarlar.json bulunamadı")
            return {}

        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("veritabani_yapisi", {})

    except Exception as e:
        logger.error(f"ayarlar.json okunamadı: {e}")
        return {}


# =============================================================================
# TABLO → SHEET EŞLEME
# =============================================================================
TABLE_TO_SHEET_MAP: Dict[str, Tuple[str, str]] = {
    # personel
    "Personel":     ("personel", "Personel"),
    "Izin_Giris":   ("personel", "Izin_Giris"),
    "Izin_Bilgi":   ("personel", "Izin_Bilgi"),
    "FHSZ_Puantaj": ("personel", "FHSZ_Puantaj"),

    # cihaz
    "Cihazlar":        ("cihaz", "Cihazlar"),
    "Cihaz_Ariza":     ("cihaz", "Cihaz_Ariza"),
    "Ariza_Islem":     ("cihaz", "Ariza_Islem"),
    "Periyodik_Bakim": ("cihaz", "Periyodik_Bakim"),
    "Kalibrasyon":     ("cihaz", "Kalibrasyon"),

    # rke
    "RKE_List":     ("rke", "RKE_List"),
    "RKE_Muayene":  ("rke", "RKE_Muayene"),

    # sabit
    "Sabitler":     ("sabit", "Sabitler"),
    "Tatiller":     ("sabit", "Tatiller"),
}


DB_FALLBACK_MAP: Dict[str, str] = {
    "personel": "itf_personel_vt",
    "sabit":    "itf_sabit_vt",
    "cihaz":    "itf_cihaz_vt",
    "user":     "itf_user_vt",
    "rke":      "itf_rke_vt",
}


# =============================================================================
# DRIVE LINK → FILE ID
# =============================================================================
def extract_file_id_from_link(drive_link: str) -> Optional[str]:
    """
    Google Drive linkinden file ID çıkarır.
    """
    if not drive_link:
        return None

    match = re.search(r"/d/([a-zA-Z0-9_-]+)", drive_link)
    if match:
        return match.group(1)

    match = re.search(r"id=([a-zA-Z0-9_-]+)", drive_link)
    if match:
        return match.group(1)

    return None
