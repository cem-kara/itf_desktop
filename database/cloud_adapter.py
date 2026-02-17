# -*- coding: utf-8 -*-
"""
Cloud adapter katmanı.

Amaç:
- Uygulamanın online/offline modda aynı arayüzle çalışması
- Google servislerine doğrudan bağımlılığı tek noktada toplamak
"""

from abc import ABC, abstractmethod

from core.config import AppConfig
from core.logger import logger


class CloudAdapter(ABC):
    """Online/offline ortak arayüzü."""

    def __init__(self, mode):
        self.mode = mode

    @property
    def is_online(self):
        return self.mode == AppConfig.MODE_ONLINE

    @abstractmethod
    def health_check(self):
        """(ok: bool, message: str)"""
        raise NotImplementedError

    @abstractmethod
    def upload_file(self, file_path, parent_folder_id=None, custom_name=None):
        raise NotImplementedError

    @abstractmethod
    def find_or_create_folder(self, folder_name, parent_folder_id=None):
        raise NotImplementedError

    @abstractmethod
    def get_folder_id(self, folder_name):
        raise NotImplementedError

    @abstractmethod
    def get_worksheet(self, table_name):
        raise NotImplementedError


class OnlineCloudAdapter(CloudAdapter):
    """Google servislerini kullanan online adapter."""

    def __init__(self):
        super().__init__(AppConfig.MODE_ONLINE)
        self._drive = None

    def _get_drive(self):
        if self._drive is None:
            from database.google import GoogleDriveService
            self._drive = GoogleDriveService()
        return self._drive

    def health_check(self):
        try:
            self._get_drive()
            return True, "online"
        except Exception as e:
            logger.error(f"Cloud health_check hatasi: {e}")
            return False, str(e)

    def upload_file(self, file_path, parent_folder_id=None, custom_name=None):
        drive = self._get_drive()
        return drive.upload_file(
            file_path,
            parent_folder_id=parent_folder_id,
            custom_name=custom_name
        )

    def find_or_create_folder(self, folder_name, parent_folder_id=None):
        drive = self._get_drive()
        return drive.find_or_create_folder(folder_name, parent_folder_id)

    def get_folder_id(self, folder_name):
        drive = self._get_drive()
        return drive.get_folder_id(folder_name)

    def get_worksheet(self, table_name):
        from database.google import get_worksheet
        return get_worksheet(table_name)


class OfflineCloudAdapter(CloudAdapter):
    """Bulut işlemlerini devre dışı bırakan offline adapter."""

    def __init__(self):
        super().__init__(AppConfig.MODE_OFFLINE)

    def health_check(self):
        return False, "offline_mode"

    def upload_file(self, file_path, parent_folder_id=None, custom_name=None):
        logger.info("Offline mod: upload_file atlandi")
        return None

    def find_or_create_folder(self, folder_name, parent_folder_id=None):
        logger.info("Offline mod: find_or_create_folder atlandi")
        return None

    def get_folder_id(self, folder_name):
        logger.info("Offline mod: get_folder_id atlandi")
        return None

    def get_worksheet(self, table_name):
        logger.info(f"Offline mod: get_worksheet atlandi ({table_name})")
        return None


_adapter_cache = {}


def get_cloud_adapter(mode=None):
    """
    Çalışma moduna göre uygun cloud adapter döndürür.
    """
    selected_mode = mode or AppConfig.get_app_mode()
    if selected_mode not in _adapter_cache:
        if selected_mode == AppConfig.MODE_OFFLINE:
            _adapter_cache[selected_mode] = OfflineCloudAdapter()
        else:
            _adapter_cache[selected_mode] = OnlineCloudAdapter()
    return _adapter_cache[selected_mode]
