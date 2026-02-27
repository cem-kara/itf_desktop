# -*- coding: utf-8 -*-
"""Bakım Formu — Thread Workers."""
import time
from typing import List, Dict, Any, Optional
from PySide6.QtCore import QThread, Signal
from core.logger import logger
from database.repository_registry import RepositoryRegistry
from database.sqlite_manager import SQLiteManager
from database.google.drive import GoogleDriveService


# ════════════════════════════════════════════════════════════════════
#  THREAD WORKERS
# ════════════════════════════════════════════════════════════════════
class IslemKaydedici(QThread):
    """Bakım kayıt ekleme/güncelleme işlemlerini thread'de yapar."""
    islem_tamam = Signal()
    hata_olustu = Signal(str)

    def __init__(self, db, islem_tipi: str, veri: Any):
        super().__init__()
        self.db = db
        self._db_path = getattr(db, "db_path", None)
        self.tip = islem_tipi  # "INSERT" veya "UPDATE"
        self.veri = veri

    def run(self):
        local_db = None
        try:
            # QThread içinde yeni DB bağlantısı oluştur (thread-safe)
            local_db = SQLiteManager(db_path=self._db_path, check_same_thread=False)
            repo = RepositoryRegistry(local_db).get("Periyodik_Bakim")
            if self.tip == "INSERT":
                # veri: List[Dict] - birden fazla kayıt
                for kayit in self.veri:
                    repo.insert(kayit)
            elif self.tip == "UPDATE":
                # veri: Dict - tek kayıt güncelleme
                repo.update(self.veri)
            self.islem_tamam.emit()
        except Exception as e:
            logger.error(f"Bakım kaydı işlemi başarısız: {e}")
            self.hata_olustu.emit(str(e))
        finally:
            if local_db:
                local_db.close()


class DosyaYukleyici(QThread):
    """Google Drive'a dosya yükleme işlemini thread'de yapar."""
    yuklendi = Signal(str)  # webViewLink
    
    def __init__(self, yerel_yol: str, folder_id: Optional[str] = None):
        super().__init__()
        self.yol = yerel_yol
        self.folder_id = folder_id

    def run(self):
        try:
            drive = GoogleDriveService()
            link = drive.upload_file(self.yol, self.folder_id)
            self.yuklendi.emit(link if link else "-")
        except Exception as e:
            logger.error(f"Dosya yükleme hatası: {e}")
            self.yuklendi.emit("-")
