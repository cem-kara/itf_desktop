"""
SettingsService — Sabitler ve Tatiller Yönetimi

Sorumluluklar:
- Sabitler CRUD işlemleri
- Tatiller CRUD işlemleri
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from core.logger import logger
from database.sqlite_manager import SQLiteManager


class SettingsService:
    """Ayarlar servisi"""
    
    def __init__(self):
        """Settings servisi oluştur"""
        self._db = SQLiteManager()
    
    # ============== SABİTLER ==============
    
    def get_sabitler(self) -> list[dict]:
        """
        Tüm sabitleri getir.
        
        Returns:
            List[Dict]: [{"Rowid": str, "Kod": str, "MenuEleman": str, "Aciklama": str}, ...]
        """
        try:
            query = "SELECT Rowid, Kod, MenuEleman, Aciklama FROM Sabitler ORDER BY MenuEleman"
            cur = self._db.execute(query)
            rows = cur.fetchall()
            return [dict(row) for row in rows] if rows else []
        except Exception as e:
            logger.error(f"Sabitler yükleme hatası: {e}")
            return []
    
    def add_sabit(self, kod: str, menu_eleman: str, aciklama: str) -> dict:
        """
        Yeni sabit ekle.
        
        Args:
            kod: Sabit kodu
            menu_eleman: Menü elemanı adı
            aciklama: Açıklama
        
        Returns:
            Dict: {"success": bool, "message": str, "rowid": str}
        """
        try:
            if not kod or not menu_eleman:
                return {
                    "success": False,
                    "message": "Kod ve Menü Elemanı zorunludur",
                    "rowid": ""
                }
            
            # Rowid oluştur (guid benzeri)
            rowid = f"{menu_eleman}_{int(datetime.now().timestamp() * 1000)}"
            
            query = """
                INSERT INTO Sabitler (Rowid, Kod, MenuEleman, Aciklama, sync_status, updated_at)
                VALUES (?, ?, ?, ?, 'dirty', ?)
            """
            
            self._db.execute(query, (rowid, kod, menu_eleman, aciklama or "", datetime.now().isoformat()))
            
            logger.info(f"Sabit eklendi: {menu_eleman} ({kod})")
            
            return {
                "success": True,
                "message": f"Sabit başarıyla eklendi: {menu_eleman}",
                "rowid": rowid
            }
            
        except Exception as e:
            error_msg = f"Sabit ekleme hatası: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                "success": False,
                "message": error_msg,
                "rowid": ""
            }
    
    def update_sabit(self, rowid: str, kod: str, menu_eleman: str, aciklama: str) -> dict:
        """
        Sabiti güncelle.
        
        Args:
            rowid: Sabit ID
            kod: Sabit kodu
            menu_eleman: Menü elemanı adı
            aciklama: Açıklama
        
        Returns:
            Dict: {"success": bool, "message": str}
        """
        try:
            if not kod or not menu_eleman:
                return {
                    "success": False,
                    "message": "Kod ve Menü Elemanı zorunludur"
                }
            
            query = """
                UPDATE Sabitler
                SET Kod = ?, MenuEleman = ?, Aciklama = ?, sync_status = 'dirty', updated_at = ?
                WHERE Rowid = ?
            """
            
            self._db.execute(query, (kod, menu_eleman, aciklama or "", datetime.now().isoformat(), rowid))
            
            logger.info(f"Sabit güncellendi: {rowid}")
            
            return {
                "success": True,
                "message": "Sabit başarıyla güncellendi"
            }
            
        except Exception as e:
            error_msg = f"Sabit güncelleme hatası: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                "success": False,
                "message": error_msg
            }
    
    def delete_sabit(self, rowid: str) -> dict:
        """
        Sabiti sil.
        
        Args:
            rowid: Sabit ID
        
        Returns:
            Dict: {"success": bool, "message": str}
        """
        try:
            query = "DELETE FROM Sabitler WHERE Rowid = ?"
            self._db.execute(query, (rowid,))
            
            logger.info(f"Sabit silindi: {rowid}")
            
            return {
                "success": True,
                "message": "Sabit başarıyla silindi"
            }
            
        except Exception as e:
            error_msg = f"Sabit silme hatası: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                "success": False,
                "message": error_msg
            }
    
    # ============== TATİLLER ==============
    
    def get_tatiller(self) -> list[dict]:
        """
        Tüm tatilleri getir.
        
        Returns:
            List[Dict]: [{"Tarih": str, "ResmiTatil": str}, ...]
        """
        try:
            query = "SELECT Tarih, ResmiTatil FROM Tatiller ORDER BY Tarih"
            cur = self._db.execute(query)
            rows = cur.fetchall()
            return [dict(row) for row in rows] if rows else []
        except Exception as e:
            logger.error(f"Tatiller yükleme hatası: {e}")
            return []
    
    def add_tatil(self, tarih: str, resmi_tatil: str) -> dict:
        """
        Yeni tatil ekle.
        
        Args:
            tarih: Tatil tarihi (YYYY-MM-DD format)
            resmi_tatil: Tatil adı
        
        Returns:
            Dict: {"success": bool, "message": str}
        """
        try:
            if not tarih or not resmi_tatil:
                return {
                    "success": False,
                    "message": "Tarih ve Tatil Adı zorunludur"
                }
            
            # Tarih formatı kontrolü
            try:
                datetime.strptime(tarih, "%Y-%m-%d")
            except ValueError:
                return {
                    "success": False,
                    "message": "Geçersiz tarih formatı (YYYY-MM-DD)"
                }
            
            query = """
                INSERT INTO Tatiller (Tarih, ResmiTatil, sync_status, updated_at)
                VALUES (?, ?, 'dirty', ?)
            """
            
            self._db.execute(query, (tarih, resmi_tatil, datetime.now().isoformat()))
            
            logger.info(f"Tatil eklendi: {tarih} ({resmi_tatil})")
            
            return {
                "success": True,
                "message": f"Tatil başarıyla eklendi: {resmi_tatil}"
            }
            
        except Exception as e:
            error_msg = f"Tatil ekleme hatası: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                "success": False,
                "message": error_msg
            }
    
    def update_tatil(self, tarih: str, resmi_tatil: str) -> dict:
        """
        Tatili güncelle.
        
        Args:
            tarih: Tatil tarihi (YYYY-MM-DD format, primary key)
            resmi_tatil: Tatil adı
        
        Returns:
            Dict: {"success": bool, "message": str}
        """
        try:
            if not tarih or not resmi_tatil:
                return {
                    "success": False,
                    "message": "Tarih ve Tatil Adı zorunludur"
                }
            
            query = """
                UPDATE Tatiller
                SET ResmiTatil = ?, sync_status = 'dirty', updated_at = ?
                WHERE Tarih = ?
            """
            
            self._db.execute(query, (resmi_tatil, datetime.now().isoformat(), tarih))
            
            logger.info(f"Tatil güncellendi: {tarih}")
            
            return {
                "success": True,
                "message": "Tatil başarıyla güncellendi"
            }
            
        except Exception as e:
            error_msg = f"Tatil güncelleme hatası: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                "success": False,
                "message": error_msg
            }
    
    def delete_tatil(self, tarih: str) -> dict:
        """
        Tatili sil.
        
        Args:
            tarih: Tatil tarihi
        
        Returns:
            Dict: {"success": bool, "message": str}
        """
        try:
            query = "DELETE FROM Tatiller WHERE Tarih = ?"
            self._db.execute(query, (tarih,))
            
            logger.info(f"Tatil silindi: {tarih}")
            
            return {
                "success": True,
                "message": "Tatil başarıyla silindi"
            }
            
        except Exception as e:
            error_msg = f"Tatil silme hatası: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                "success": False,
                "message": error_msg
            }
