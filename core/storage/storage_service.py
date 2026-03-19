# core/storage/storage_service.py
"""
Hibrit dosya yükleme servisi.

- Drive varsa yükler
- Yoksa local (offline_uploads) klasörüne kopyalar
"""
import os
import shutil
from typing import Dict, Optional

from core.logger import logger

from core.paths import DATA_DIR
from database.google.utils import resolve_storage_target


class StorageService:
    def __init__(self, db=None, sabitler_cache: Optional[list] = None):
        self._db = db
        self._sabitler_cache = sabitler_cache

    def _get_sabitler(self) -> list:
        if self._sabitler_cache is not None:
            return self._sabitler_cache
        if not self._db:
            return []
        try:
            from database.repository_registry import RepositoryRegistry
            return RepositoryRegistry(self._db).get("Sabitler").get_all()
        except Exception as e:
            logger.warning(f"Sabitler yüklenemedi: {e}")
            return []

    def resolve_target(self, folder_name: str) -> Dict[str, str]:
        """Drive/Offline hedefini Sabitler üzerinden çözer."""
        return resolve_storage_target(self._get_sabitler(), folder_name)

    def _save_local(self, file_path: str, folder_name: str, custom_name: Optional[str] = None) -> Optional[str]:
        try:
            if not os.path.exists(file_path):
                logger.warning(f"Dosya bulunamadı: {file_path}")
                return None

            base_dir = os.path.join(DATA_DIR, "offline_uploads", folder_name)
            os.makedirs(base_dir, exist_ok=True)

            name = custom_name if custom_name else os.path.basename(file_path)
            dest_path = os.path.join(base_dir, name)
            shutil.copy2(file_path, dest_path)
            logger.info(f"Dosya lokal klasöre kopyalandı: {dest_path}")
            return dest_path
        except Exception as e:
            logger.error(f"Lokal dosya kaydetme hatası: {e}")
            return None

    def upload(self, file_path: str, folder_name: str, custom_name: Optional[str] = None) -> Dict[str, str]:
        """
        Dosyayı hibrit olarak yükler.

        Returns:
            {
              "mode": "drive" | "local" | "none",
              "drive_link": "...",
              "local_path": "...",
              "error": "..."
            }
        """
        result = {"mode": "none", "drive_link": "", "local_path": "", "error": ""}

        if not file_path or not os.path.exists(file_path):
            result["error"] = "Dosya bulunamadı"
            logger.warning(result["error"])
            return result

        target = self.resolve_target(folder_name)
        drive_id = target.get("drive_folder_id", "")
        offline_folder = target.get("offline_folder_name", "") or folder_name

        if drive_id:
            try:
                from database.google.drive import get_drive_service
                drive = get_drive_service()
                link = drive.upload_file(file_path, drive_id, custom_name=custom_name)
                if link:
                    result.update({"mode": "drive", "drive_link": link})
                    return result
            except Exception as e:
                logger.warning(f"Drive yükleme başarısız, local'e düşülecek: {e}")

        local_path = self._save_local(file_path, offline_folder, custom_name=custom_name)
        if local_path:
            result.update({"mode": "local", "local_path": local_path})
        else:
            result["error"] = "Local kopyalama başarısız"
        return result
