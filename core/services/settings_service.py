"""
SettingsService — Sabitler ve Tatiller Yönetimi

Sorumluluklar:
- Sabitler CRUD işlemleri
- Tatiller CRUD işlemleri
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional
from core.hata_yonetici import SonucYonetici

from core.logger import logger
from database.sqlite_manager import SQLiteManager


class SettingsService:
    """Ayarlar servisi"""
    
    def __init__(self, db):
        """Settings servisi oluştur (thread-safe db parametresi ile)"""
        self._db = db
    
    # ============== SABİTLER ============== # SonucYonetici.data için list[dict] döndür

    def get_sabitler(self) -> SonucYonetici:
        """
        Tüm sabitleri getir.
        
        Returns:
            List[Dict]: [{"Rowid": str, "Kod": str, "MenuEleman": str, "Aciklama": str}, ...]
        """
        try:
            query = "SELECT Rowid, Kod, MenuEleman, Aciklama FROM Sabitler ORDER BY MenuEleman"
            cur = self._db.execute(query)
            data = [dict(row) for row in cur.fetchall()] if cur else []
            return SonucYonetici.tamam(data=data)
        except Exception as e:
            return SonucYonetici.hata(e, "SettingsService.get_sabitler")

    def add_sabit(self, kod: str, menu_eleman: str, aciklama: str) -> SonucYonetici:
        """
        Yeni sabit ekle.
        
        Args:
            kod: Sabit kodu
            menu_eleman: Menü elemanı adı
            aciklama: Açıklama
        
        Returns:
            Dict: {"success": bool, "message": str, "rowid": str}
        """
        if not kod or not menu_eleman:
            return SonucYonetici.hata(Exception("Kod ve Menü Elemanı zorunludur"), "SettingsService.add_sabit")

        try:
            # Rowid oluştur (guid benzeri)
            rowid = f"{menu_eleman}_{int(datetime.now().timestamp() * 1000)}"
            
            query = """
                INSERT INTO Sabitler (Rowid, Kod, MenuEleman, Aciklama, sync_status, updated_at)
                VALUES (?, ?, ?, ?, 'dirty', ?)
            """
            
            self._db.execute(query, (rowid, kod, menu_eleman, aciklama or "", datetime.now().isoformat()))
            
            logger.info(f"Sabit eklendi: {menu_eleman} ({kod})")
            
            return SonucYonetici.tamam(f"Sabit başarıyla eklendi: {menu_eleman}", data={"rowid": rowid})
            
        except Exception as e:
            return SonucYonetici.hata(e, "SettingsService.add_sabit")

    def update_sabit(self, rowid: str, kod: str, menu_eleman: str, aciklama: str) -> SonucYonetici:
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
        if not kod or not menu_eleman:
            return SonucYonetici.hata(Exception("Kod ve Menü Elemanı zorunludur"), "SettingsService.update_sabit")

        try:
            query = """
                UPDATE Sabitler
                SET Kod = ?, MenuEleman = ?, Aciklama = ?, sync_status = 'dirty', updated_at = ?
                WHERE Rowid = ?
            """
            
            self._db.execute(query, (kod, menu_eleman, aciklama or "", datetime.now().isoformat(), rowid))
            
            return SonucYonetici.tamam("Sabit başarıyla güncellendi.")
            
        except Exception as e:
            return SonucYonetici.hata(e, "SettingsService.update_sabit")

    def delete_sabit(self, rowid: str) -> SonucYonetici:
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
            
            return SonucYonetici.tamam("Sabit başarıyla silindi.")
            
        except Exception as e:
            return SonucYonetici.hata(e, "SettingsService.delete_sabit")

    # ============== TATİLLER ============== # SonucYonetici.data için list[dict] döndür

    def get_tatiller(self) -> SonucYonetici:
        """
        Tüm tatilleri getir.
        
        Returns:
            List[Dict]: [{"Tarih": str, "ResmiTatil": str}, ...]
        """
        try:
            query = "SELECT Tarih, ResmiTatil FROM Tatiller ORDER BY Tarih"
            cur = self._db.execute(query)
            data = [dict(row) for row in cur.fetchall()] if cur else []
            return SonucYonetici.tamam(data=data)
        except Exception as e:
            return SonucYonetici.hata(e, "SettingsService.get_tatiller")

    def add_tatil(self, tarih: str, resmi_tatil: str) -> SonucYonetici:
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
                return SonucYonetici.hata(Exception("Tarih ve Tatil Adı zorunludur"), "SettingsService.add_tatil")

            # Tarih formatı kontrolü
            try:
                datetime.strptime(tarih, "%Y-%m-%d")
            except ValueError:
                return SonucYonetici.hata(Exception("Geçersiz tarih formatı (YYYY-MM-DD)"), "SettingsService.add_tatil")

            # Duplicate tarih kontrolü
            check_query = "SELECT COUNT(*) FROM Tatiller WHERE Tarih = ?"
            if self._db and self._db.execute(check_query, (tarih,)).fetchone()[0] > 0:
                return SonucYonetici.hata(Exception(f"Bu tarih zaten tatil olarak kaydedilmiş: {tarih}"), "SettingsService.add_tatil")

            query = """
                INSERT INTO Tatiller (Tarih, ResmiTatil, sync_status, updated_at)
                VALUES (?, ?, 'dirty', ?)
            """
            
            self._db.execute(query, (tarih, resmi_tatil, datetime.now().isoformat()))
            
            return SonucYonetici.tamam(f"Tatil başarıyla eklendi: {resmi_tatil}")
            
        except Exception as e:
            return SonucYonetici.hata(e, "SettingsService.add_tatil")

    def update_tatil(self, tarih: str, resmi_tatil: str) -> SonucYonetici:
        """
        Tatili güncelle.
        
        Args:
            tarih: Tatil tarihi (YYYY-MM-DD format, primary key)
            resmi_tatil: Tatil adı
        
        Returns:
            Dict: {"success": bool, "message": str}
        """
        if not tarih or not resmi_tatil:
            return SonucYonetici.hata(Exception("Tarih ve Tatil Adı zorunludur"), "SettingsService.update_tatil")
        try:
            query = """
                UPDATE Tatiller
                SET ResmiTatil = ?, sync_status = 'dirty', updated_at = ?
                WHERE Tarih = ?
            """
            
            self._db.execute(query, (resmi_tatil, datetime.now().isoformat(), tarih))
            
            return SonucYonetici.tamam("Tatil başarıyla güncellendi.")
            
        except Exception as e:
            return SonucYonetici.hata(e, "SettingsService.update_tatil")

    def delete_tatil(self, tarih: str) -> SonucYonetici:
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
            
            return SonucYonetici.tamam("Tatil başarıyla silindi.")
            
        except Exception as e:
            return SonucYonetici.hata(e, "SettingsService.delete_tatil")
