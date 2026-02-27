"""
Personel Dosya Yukleme Servisi
===============================

Drive yukleme islemlerini arka planda yurutur ve
Dokumanlar tablosuna gerekli kayitlari ekler.
"""

import os
from datetime import datetime
from typing import Dict, Any

from PySide6.QtCore import QObject, QThread, Signal

from core.logger import logger
from core.hata_yonetici import exc_logla
from database.repository_registry import RepositoryRegistry
from database.google.utils import resolve_storage_target


class DriveUploadWorker(QThread):
    """Drive'a dosya yukler."""

    finished = Signal(str, str)   # (alan_adi, webViewLink)
    error = Signal(str, str)      # (alan_adi, hata_mesaji)

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
                offline_folder_name=self._offline_folder_name
            )
            if link:
                self.finished.emit(self._alan_adi, str(link))
            else:
                self.error.emit(self._alan_adi, "Yukleme basarisiz")
        except Exception as e:
            exc_logla("PersonelUploadService", e)
            self.error.emit(self._alan_adi, str(e))


class PersonelUploadManager(QObject):
    """Drive yukleme surecini yoneten servis."""

    progress = Signal(int)                # yuzde
    finished = Signal(dict, list)         # (drive_links, errors)

    def __init__(self, db_path: str, all_sabit: list):
        super().__init__()
        self._db = db_path
        self._all_sabit = all_sabit or []
        self._workers = []
        self._drive_links: Dict[str, str] = {}
        self._errors = []
        self._meta: Dict[str, Dict[str, Any]] = {}
        self._total = 0
        self._done = 0

    def start_uploads(self, file_paths: dict, tc_no: str):
        """Dosyalari Drive'a yukle."""
        self._drive_links = {}
        self._errors = []
        self._meta = {}
        self._workers = []
        self._total = 0
        self._done = 0

        if not file_paths:
            self.finished.emit({}, [])
            return

        upload_map = {
            "Resim": ("Personel_Resim", "Resim"),
            "Diploma1": ("Personel_Diploma", "Diploma1"),
            "Diploma2": ("Personel_Diploma", "Diploma2"),
        }

        for file_key, file_path in file_paths.items():
            if file_key not in upload_map:
                continue

            folder_name, db_field = upload_map[file_key]
            target = resolve_storage_target(self._all_sabit, folder_name)
            folder_id = target.get("drive_folder_id")
            offline_folder_name = target.get("offline_folder_name")

            ext = os.path.splitext(file_path)[1]
            custom_name = f"{tc_no}_{db_field}{ext}"

            self._meta[db_field] = {
                "tc_no": tc_no,
                "file_path": file_path,
                "custom_name": custom_name,
                "folder_name": folder_name,
                "belge_turu": db_field,
            }

            self._total += 1
            worker = DriveUploadWorker(file_path, folder_id, custom_name, db_field, offline_folder_name)
            worker.finished.connect(self._on_worker_finished)
            worker.error.connect(self._on_worker_error)
            self._workers.append(worker)
            worker.start()

        if self._total == 0:
            self.finished.emit({}, [])

    def _on_worker_finished(self, alan_adi: str, link: str):
        """Tek dosya yukleme tamamlandi."""
        self._drive_links[alan_adi] = link
        self._insert_dokuman_kaydi(alan_adi, link)
        self._done += 1
        self._emit_progress()
        self._check_complete()

    def _on_worker_error(self, alan_adi: str, hata: str):
        """Tek dosya yukleme hatasi."""
        self._errors.append(f"{alan_adi}: {hata}")
        logger.error(f"Drive yukleme hatasi: {alan_adi} -> {hata}")
        self._done += 1
        self._emit_progress()
        self._check_complete()

    def _emit_progress(self):
        if self._total <= 0:
            self.progress.emit(0)
            return
        percent = int((self._done / self._total) * 100)
        self.progress.emit(percent)

    def _check_complete(self):
        if self._done >= self._total:
            self._workers.clear()
            self.finished.emit(self._drive_links, self._errors)

    def _insert_dokuman_kaydi(self, alan_adi: str, link: str) -> None:
        """Dokumanlar tablosuna kayit ekler (personel icin)."""
        try:
            if alan_adi not in ("Diploma1", "Diploma2"):
                return

            meta = self._meta.get(alan_adi, {})
            tc_no = meta.get("tc_no")
            if not tc_no:
                return

            file_path = meta.get("file_path", "")
            custom_name = meta.get("custom_name", "")
            folder_name = meta.get("folder_name", "")
            belge_turu = meta.get("belge_turu", alan_adi)

            drive_path = link if str(link).startswith("http") else ""
            local_path = "" if drive_path else str(link or "")

            repo = RepositoryRegistry(self._db).get("Dokumanlar")
            repo.insert({
                "EntityType": "personel",
                "EntityId": str(tc_no),
                "BelgeTuru": str(belge_turu),
                "Belge": str(custom_name or os.path.basename(file_path) or link),
                "DocType": str(folder_name),
                "DisplayName": os.path.basename(file_path) if file_path else str(custom_name),
                "LocalPath": local_path,
                "DrivePath": drive_path,
                "BelgeAciklama": "",
                "YuklenmeTarihi": datetime.now().isoformat(),
                "IliskiliBelgeID": None,
                "IliskiliBelgeTipi": None,
            })
        except Exception as e:
            logger.warning(f"Dokumanlar kaydi eklenemedi ({alan_adi}): {e}")
