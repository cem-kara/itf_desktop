# -*- coding: utf-8 -*-
from PySide6.QtCore import QThread, Signal

from core.hata_yonetici import exc_logla


class DriveUploadWorker(QThread):
    finished = Signal(str, str)
    error = Signal(str, str)
    progress = Signal(int)

    def __init__(self, file_path, folder_id, custom_name, alan_adi, offline_folder_name=None):
        super().__init__()
        self._file_path = file_path
        self._folder_id = folder_id
        self._custom_name = custom_name
        self._alan_adi = alan_adi
        self._offline_folder_name = offline_folder_name

    def run(self):
        try:
            from core.di import get_cloud_adapter
            cloud = get_cloud_adapter()
            link = cloud.upload_file(
                self._file_path,
                parent_folder_id=self._folder_id,
                custom_name=self._custom_name,
                offline_folder_name=self._offline_folder_name,
            )
            if link:
                self.finished.emit(self._alan_adi, str(link))
            else:
                self.error.emit(self._alan_adi, "Yükleme başarısız (Offline modda hedef klasör tanımlı olmayabilir)")
        except Exception as e:
            exc_logla("PersonelEkle.DosyaYukleyici", e)
            self.error.emit(self._alan_adi, str(e))