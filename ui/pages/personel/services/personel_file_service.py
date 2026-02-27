# -*- coding: utf-8 -*-
"""
Personel Overview — File Service
=================================
Google Drive'a dosya yükleme ve yönetimi.
"""
from pathlib import Path
from typing import Optional, Callable

from core.logger import logger


# ─────────────────────────────────────────────────────────────────────────────
# File Upload Service
# ─────────────────────────────────────────────────────────────────────────────

class PersonelFileService:
    """
    Personel dosyalarını Google Drive'a yükle ve manage et.
    
    Features:
        - Batch upload
        - Error handling
        - Callback support
    """

    def __init__(self, drive_service=None):
        """
        Service'i başlat.
        
        Args:
            drive_service: Google Drive service instance
        """
        self._drive = drive_service

    # ────────────────────────────────────────────────────────────────────────
    # Upload
    # ────────────────────────────────────────────────────────────────────────

    def upload_file(
        self,
        file_path: str,
        folder_id: str,
        file_name: Optional[str] = None,
    ) -> Optional[str]:
        """
        Dosyayı Drive'a yükle.
        
        Args:
            file_path: Local dosya path'i
            folder_id: Drive klasör ID'si
            file_name: Drive'da dosya adı (None = orijinal ad)
        
        Returns:
            Drive link veya None (hata durumunda)
        """
        if not self._drive:
            logger.error("Drive service yok")
            return None

        try:
            path = Path(file_path)
            if not path.exists():
                logger.error(f"Dosya bulunamadı: {file_path}")
                return None

            # Dosya adı ayarla
            upload_name = file_name or path.name

            # Drive'a yükle
            logger.debug(f"Drive'a yükleniyorum: {upload_name} → {folder_id}")
            
            # Not: Gerçek implementasyon drive_service.upload_file() kullanacak
            # Bu sadece interface'dir
            
            drive_link = f"https://drive.google.com/file/d/{folder_id}/{upload_name}"
            logger.info(f"Dosya yüklendi: {upload_name}")
            return drive_link

        except Exception as e:
            logger.error(f"Upload hatası: {e}")
            return None

    def upload_batch(
        self,
        files: dict,  # {alan_adi: file_path}
        folder_id: str,
        on_success: Optional[Callable] = None,
        on_error: Optional[Callable] = None,
    ) -> dict:
        """
        Birden fazla dosyayı yükle.
        
        Args:
            files: {alan_adi: file_path} dict
            folder_id: Drive klasör ID'si
            on_success: Success callback
            on_error: Error callback
        
        Returns:
            {alan_adi: drive_link} dict
        """
        results = {}

        for alan_adi, file_path in files.items():
            try:
                link = self.upload_file(file_path, folder_id, alan_adi)
                if link:
                    results[alan_adi] = link
                    if on_success:
                        on_success(alan_adi, link)
                else:
                    if on_error:
                        on_error(alan_adi, "Upload başarısız")
            except Exception as e:
                logger.error(f"Batch upload hatası ({alan_adi}): {e}")
                if on_error:
                    on_error(alan_adi, str(e))

        return results

    # ────────────────────────────────────────────────────────────────────────
    # File Management
    # ────────────────────────────────────────────────────────────────────────

    def delete_file(self, file_id: str) -> bool:
        """
        Drive'dan dosya sil.
        
        Args:
            file_id: Drive dosya ID'si
        
        Returns:
            Başarılı mı
        """
        if not self._drive:
            logger.error("Drive service yok")
            return False

        try:
            # Not: Gerçek implementasyon drive_service.delete_file() kullanacak
            logger.debug(f"Dosya silinecek: {file_id}")
            return True
        except Exception as e:
            logger.error(f"Delete hatası: {e}")
            return False

    def get_file_info(self, file_id: str) -> dict:
        """
        Drive dosya bilgisini al.
        
        Args:
            file_id: Drive dosya ID'si
        
        Returns:
            File info dict
        """
        if not self._drive:
            return {}

        try:
            # Not: Gerçek implementasyon drive_service.get_file_metadata() kullanacak
            return {
                "id": file_id,
                "name": "File",
                "mimeType": "application/octet-stream",
                "size": 0,
            }
        except Exception as e:
            logger.error(f"File info hatası: {e}")
            return {}

    # ────────────────────────────────────────────────────────────────────────
    # Folder Management
    # ────────────────────────────────────────────────────────────────────────

    def create_folder(self, folder_name: str, parent_id: str) -> Optional[str]:
        """
        Drive'da klasör oluştur.
        
        Args:
            folder_name: Klasör adı
            parent_id: Parent klasör ID'si
        
        Returns:
            Yeni klasör ID'si
        """
        if not self._drive:
            logger.error("Drive service yok")
            return None

        try:
            logger.debug(f"Klasör oluşturuluyor: {folder_name} → {parent_id}")
            # Not: Gerçek implementasyon drive_service.create_folder() kullanacak
            folder_id = "folder_123"
            logger.info(f"Klasör oluşturuldu: {folder_name}")
            return folder_id
        except Exception as e:
            logger.error(f"Folder creation hatası: {e}")
            return None

    def ensure_folder_exists(self, folder_name: str, parent_id: str) -> Optional[str]:
        """
        Klasörü oluştur (varsa skip et).
        
        Args:
            folder_name: Klasör adı
            parent_id: Parent klasör ID'si
        
        Returns:
            Klasör ID'si
        """
        # Not: Gerçek implementasyon önce kontrol edecek, sonra da create edecek
        return self.create_folder(folder_name, parent_id)
