# database/google/drive.py
"""
Google Drive işlemleri.

Bu modül Google Drive ile dosya upload/download/delete işlemlerini yönetir.
"""

import os
import logging
from pathlib import Path
from typing import Optional

from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
import io

from .auth import get_credentials
from .exceptions import GoogleServisHatasi, InternetBaglantiHatasi
from .utils import internet_kontrol, extract_file_id_from_link


logger = logging.getLogger(__name__)


class GoogleDriveService:
    """
    Google Drive işlemleri için servis sınıfı.
    
    Özellikler:
    - Dosya yükleme (public link ile)
    - Dosya indirme
    - Dosya silme
    - Link'ten file ID çıkarma
    """
    
    def __init__(self):
        """
        Drive servisini başlatır.
        
        Raises:
            GoogleServisHatasi: Servis başlatılamazsa
        """
        try:
            creds = get_credentials()
            self.service = build('drive', 'v3', credentials=creds)
            logger.info("Google Drive servisi başlatıldı")
        except Exception as e:
            logger.error(f"Drive servisi başlatılamadı: {e}")
            raise GoogleServisHatasi(f"Drive bağlantı hatası: {e}")
    
    def upload_file(
        self,
        file_path: str,
        parent_folder_id: Optional[str] = None,
        custom_name: Optional[str] = None,
        make_public: bool = True
    ) -> Optional[str]:
        """
        Dosyayı Google Drive'a yükler.
        
        Args:
            file_path: Yüklenecek dosyanın yolu
            parent_folder_id: Hedef klasör ID (None ise root)
            custom_name: Özel dosya adı (None ise orijinal ad)
            make_public: Public link oluştur mu?
            
        Returns:
            str: Dosyanın web link'i (public ise) veya file ID
            None: Dosya yoksa
            
        Raises:
            GoogleServisHatasi: Yükleme başarısız
            InternetBaglantiHatasi: İnternet bağlantısı koptu
        """
        if not os.path.exists(file_path):
            logger.warning(f"Dosya bulunamadı: {file_path}")
            return None
        
        try:
            path_obj = Path(file_path)
            dosya_adi = custom_name if custom_name else path_obj.name
            
            # Metadata hazırla
            file_metadata = {'name': dosya_adi}
            if parent_folder_id:
                file_metadata['parents'] = [parent_folder_id]
            
            # Dosyayı yükle
            media = MediaFileUpload(str(path_obj), resumable=True)
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, webViewLink, name'
            ).execute()
            
            file_id = file.get('id')
            logger.info(f"Dosya yüklendi: {dosya_adi} (ID: {file_id})")
            
            # Public yap
            if make_public:
                self.service.permissions().create(
                    fileId=file_id,
                    body={'role': 'reader', 'type': 'anyone'}
                ).execute()
                logger.debug(f"Dosya public yapıldı: {file_id}")
                return file.get('webViewLink')
            
            return file_id
        
        except Exception as e:
            logger.error(f"Drive yükleme hatası: {e}")
            
            if not internet_kontrol():
                raise InternetBaglantiHatasi(
                    "Drive yüklemesi sırasında internet koptu"
                )
            
            raise GoogleServisHatasi(f"Dosya yüklenemedi: {e}")
    
    def download_file(self, file_id: str, dest_path: str) -> bool:
        """
        Drive'dan dosya indir.
        
        Args:
            file_id: Google Drive file ID
            dest_path: Hedef dosya yolu
            
        Returns:
            bool: Başarılı ise True
        """
        try:
            request = self.service.files().get_media(fileId=file_id)
            fh = io.FileIO(dest_path, 'wb')
            downloader = MediaIoBaseDownload(fh, request)
            
            done = False
            while not done:
                status, done = downloader.next_chunk()
                if status:
                    progress = int(status.progress() * 100)
                    logger.debug(f"İndirme: %{progress}")
            
            fh.close()
            logger.info(f"Dosya indirildi: {file_id} → {dest_path}")
            return True
        
        except Exception as e:
            logger.error(f"Drive indirme hatası ({file_id}): {e}")
            return False
    
    def delete_file(self, file_id: str) -> bool:
        """
        Drive'dan dosya sil.
        
        Args:
            file_id: Silinecek dosyanın ID'si
            
        Returns:
            bool: Başarılı ise True
        """
        try:
            self.service.files().delete(fileId=file_id).execute()
            logger.info(f"Dosya silindi: {file_id}")
            return True
        
        except Exception as e:
            logger.error(f"Drive silme hatası ({file_id}): {e}")
            return False
    
    def get_file_metadata(self, file_id: str) -> Optional[dict]:
        """
        Dosya metadata'sını getir.
        
        Args:
            file_id: File ID
            
        Returns:
            dict: Dosya bilgileri (name, mimeType, size, vb.)
            None: Dosya bulunamazsa
        """
        try:
            file = self.service.files().get(
                fileId=file_id,
                fields='id, name, mimeType, size, createdTime, modifiedTime'
            ).execute()
            return file
        
        except Exception as e:
            logger.error(f"Metadata getirme hatası ({file_id}): {e}")
            return None
    
    def find_or_create_folder(
        self,
        folder_name: str,
        parent_folder_id: Optional[str] = None
    ) -> str:
        """
        Drive'da klasör bul, yoksa oluştur.

        Args:
            folder_name: Klasör adı
            parent_folder_id: Üst klasör ID (None → Drive root)

        Returns:
            str: Klasör ID'si

        Raises:
            GoogleServisHatasi: Drive erişimi başarısız
        """
        try:
            # Önce mevcut klasörü ara
            query = (
                f"name='{folder_name}' "
                f"and mimeType='application/vnd.google-apps.folder' "
                f"and trashed=false"
            )
            if parent_folder_id:
                query += f" and '{parent_folder_id}' in parents"

            results = self.service.files().list(
                q=query,
                fields="files(id, name)",
                spaces="drive",
            ).execute()

            files = results.get("files", [])
            if files:
                folder_id = files[0]["id"]
                logger.debug(f"Klasör bulundu: '{folder_name}' (ID: {folder_id})")
                return folder_id

            # Yoksa oluştur
            metadata = {
                "name": folder_name,
                "mimeType": "application/vnd.google-apps.folder",
            }
            if parent_folder_id:
                metadata["parents"] = [parent_folder_id]

            folder = self.service.files().create(
                body=metadata,
                fields="id",
            ).execute()

            folder_id = folder["id"]
            logger.info(f"Klasör oluşturuldu: '{folder_name}' (ID: {folder_id})")
            return folder_id

        except Exception as e:
            logger.error(f"find_or_create_folder hatası ('{folder_name}'): {e}")
            raise GoogleServisHatasi(f"Klasör oluşturulamadı: {e}")

    @staticmethod
    def extract_file_id(drive_link: str) -> Optional[str]:
        """
        Drive linkinden file ID çıkar.
        
        Args:
            drive_link: Google Drive linki
            
        Returns:
            str: File ID veya None
        """
        return extract_file_id_from_link(drive_link)


# Global instance
_drive_service: Optional[GoogleDriveService] = None


def get_drive_service() -> GoogleDriveService:
    """Global GoogleDriveService instance döndürür"""
    global _drive_service
    if _drive_service is None:
        _drive_service = GoogleDriveService()
    return _drive_service
