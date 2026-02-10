# database/google/sheets.py
"""
Google Sheets işlemleri.

Bu modül Google Sheets ile etkileşim için fonksiyonlar sağlar.
"""

import logging
from typing import Optional
import gspread

from .auth import get_sheets_client
from .exceptions import VeritabaniBulunamadiHatasi
from .utils import (
    db_ayarlarini_yukle,
    TABLE_TO_SHEET_MAP,
    DB_FALLBACK_MAP
)


logger = logging.getLogger(__name__)


class GoogleSheetsManager:
    """Google Sheets işlemleri için yönetici sınıf"""
    
    def __init__(self):
        self.db_config = db_ayarlarini_yukle()
    
    def get_spreadsheet_name(self, vt_tipi: str) -> str:
        """
        Veritabanı tipine göre spreadsheet adını döndürür.
        
        Args:
            vt_tipi: Veritabanı tipi (personel, cihaz, rke, sabit, user)
            
        Returns:
            str: Spreadsheet dosya adı
            
        Raises:
            ValueError: Tanımsız vt_tipi
        """
        # Önce config'den bak
        if vt_tipi in self.db_config:
            return self.db_config[vt_tipi]["dosya"]
        
        # Fallback map'e bak
        if vt_tipi in DB_FALLBACK_MAP:
            logger.warning(
                f"'{vt_tipi}' için config bulunamadı, "
                f"fallback kullanılıyor: {DB_FALLBACK_MAP[vt_tipi]}"
            )
            return DB_FALLBACK_MAP[vt_tipi]
        
        raise ValueError(f"'{vt_tipi}' için veritabanı tanımı bulunamadı")
    
    def get_worksheet(
        self, 
        vt_tipi: str, 
        sayfa_adi: str
    ) -> gspread.Worksheet:
        """
        Belirtilen veritabanı ve sayfa için worksheet döndürür.
        
        Args:
            vt_tipi: Veritabanı tipi
            sayfa_adi: Sayfa adı (worksheet name)
            
        Returns:
            gspread.Worksheet: Worksheet nesnesi
            
        Raises:
            VeritabaniBulunamadiHatasi: Spreadsheet veya worksheet bulunamadı
        """
        try:
            client = get_sheets_client()
            spreadsheet_name = self.get_spreadsheet_name(vt_tipi)
            
            # Spreadsheet'i aç
            try:
                sh = client.open(spreadsheet_name)
                logger.debug(f"Spreadsheet açıldı: {spreadsheet_name}")
            except gspread.SpreadsheetNotFound:
                raise VeritabaniBulunamadiHatasi(
                    f"Spreadsheet bulunamadı: {spreadsheet_name}"
                )
            
            # Worksheet'i al
            try:
                ws = sh.worksheet(sayfa_adi)
                logger.debug(f"Worksheet bulundu: {sayfa_adi}")
                return ws
            except gspread.WorksheetNotFound:
                raise VeritabaniBulunamadiHatasi(
                    f"Worksheet bulunamadı: {sayfa_adi} "
                    f"(Spreadsheet: {spreadsheet_name})"
                )
        
        except Exception as e:
            logger.error(
                f"Worksheet erişim hatası ({vt_tipi}/{sayfa_adi}): {e}"
            )
            raise
    
    def get_worksheet_by_table(self, table_name: str) -> gspread.Worksheet:
        """
        Tablo adına göre worksheet döndürür.
        
        Args:
            table_name: Tablo adı (örn: Personel, Cihazlar)
            
        Returns:
            gspread.Worksheet: Worksheet nesnesi
            
        Raises:
            ValueError: Tanımsız tablo adı
            VeritabaniBulunamadiHatasi: Worksheet bulunamadı
        """
        mapping = TABLE_TO_SHEET_MAP.get(table_name)
        
        if not mapping:
            raise ValueError(
                f"'{table_name}' için Google Sheets eşlemesi bulunamadı. "
                f"Geçerli tablolar: {list(TABLE_TO_SHEET_MAP.keys())}"
            )
        
        vt_tipi, sayfa_adi = mapping
        return self.get_worksheet(vt_tipi, sayfa_adi)


# Global instance
_sheets_manager: Optional[GoogleSheetsManager] = None


def get_sheets_manager() -> GoogleSheetsManager:
    """Global GoogleSheetsManager instance döndürür"""
    global _sheets_manager
    if _sheets_manager is None:
        _sheets_manager = GoogleSheetsManager()
    return _sheets_manager


# Convenience functions (backward compatibility)
def veritabani_getir(vt_tipi: str, sayfa_adi: str) -> gspread.Worksheet:
    """
    Eski API için geriye dönük uyumluluk.
    
    DEPRECATED: get_sheets_manager().get_worksheet() kullanın
    """
    return get_sheets_manager().get_worksheet(vt_tipi, sayfa_adi)


def get_worksheet(table_name: str) -> gspread.Worksheet:
    """
    Tablo adına göre worksheet döndürür.
    
    Args:
        table_name: Tablo adı
        
    Returns:
        gspread.Worksheet: Worksheet nesnesi
    """
    return get_sheets_manager().get_worksheet_by_table(table_name)
