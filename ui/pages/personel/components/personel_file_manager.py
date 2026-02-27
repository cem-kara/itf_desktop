# -*- coding: utf-8 -*-
"""
Personel Overview — File Manager
=================================
Dosya upload UI yönetimi (diplom, sertifika, vb).
"""
from typing import Dict, Optional
from pathlib import Path

from PySide6.QtWidgets import QPushButton, QFileDialog, QMessageBox, QWidget
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QCursor

from core.logger import logger
from ui.styles import DarkTheme

C = DarkTheme


# ─────────────────────────────────────────────────────────────────────────────
# File Upload Manager
# ─────────────────────────────────────────────────────────────────────────────

class PersonelFileManager:
    """
    Personel dosyaları yönetimi (upload, preview, cache).
    
    Attributes:
        _file_paths: {alan_adi: local_file_path}
        _drive_links: {alan_adi: drive_share_link}
    """

    # Desteklenen dosya tipleri
    SUPPORTED_EXTENSIONS = {
        "Resim": ("*.jpg", "*.jpeg", "*.png", "*.gif"),
        "Diploma": ("*.pdf", "*.docx", "*.doc", "*.jpg", "*.png"),
        "Sertifika": ("*.pdf", "*.docx", "*.doc", "*.jpg", "*.png"),
        "Özgeçmiş": ("*.pdf", "*.docx", "*.doc"),
    }

    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

    def __init__(self):
        """Manager'ı başlat."""
        self._file_paths: Dict[str, str] = {}
        self._drive_links: Dict[str, str] = {}

    # ────────────────────────────────────────────────────────────────────────
    # File Selection
    # ────────────────────────────────────────────────────────────────────────

    def select_file(
        self,
        alan_adi: str,
        parent: Optional[QWidget] = None,
    ) -> Optional[str]:
        """
        Kullanıcıdan dosya seç.
        
        Args:
            alan_adi: Field adı ("Resim", "Diploma", vb)
            parent: Parent widget
        
        Returns:
            Seçilen dosya path'i veya None
        """
        extensions = self.SUPPORTED_EXTENSIONS.get(alan_adi, ("*.*",))
        filter_str = f"{alan_adi} Dosyaları ({' '.join(extensions)});;Tüm Dosyalar (*.*)"

        file_path, _ = QFileDialog.getOpenFileName(
            parent,
            f"{alan_adi} Dosyası Seç",
            str(Path.home() / "Downloads"),
            filter_str,
        )

        if not file_path:
            return None

        # Validasyon
        if not self._validate_file(file_path, alan_adi):
            return None

        self._file_paths[alan_adi] = file_path
        logger.debug(f"Dosya seçildi ({alan_adi}): {file_path}")
        return file_path

    def _validate_file(self, file_path: str, alan_adi: str) -> bool:
        """
        Dosyayı validat et.
        
        Args:
            file_path: Dosya path'i
            alan_adi: Field adı
        
        Returns:
            Geçerli mi
        """
        path = Path(file_path)

        # Dosya var mı
        if not path.exists():
            logger.warning(f"Dosya bulunamadı: {file_path}")
            return False

        # Boyut kontrol
        file_size = path.stat().st_size
        if file_size > self.MAX_FILE_SIZE:
            logger.warning(f"Dosya çok büyük ({alan_adi}): {file_size / 1024 / 1024:.1f} MB")
            return False

        # Uzantı kontrol
        extensions = self.SUPPORTED_EXTENSIONS.get(alan_adi, [])
        if extensions and path.suffix.lower() not in [ext.replace("*", "") for ext in extensions]:
            logger.warning(f"Desteklenmeyen uzantı ({alan_adi}): {path.suffix}")
            return False

        return True

    # ────────────────────────────────────────────────────────────────────────
    # File Cache
    # ────────────────────────────────────────────────────────────────────────

    def get_file_path(self, alan_adi: str) -> Optional[str]:
        """
        Dosya path'ini al.
        
        Args:
            alan_adi: Field adı
        
        Returns:
            Dosya path'i veya None
        """
        return self._file_paths.get(alan_adi)

    def set_drive_link(self, alan_adi: str, drive_link: str):
        """
        Drive link'i set et (upload sonrası).
        
        Args:
            alan_adi: Field adı
            drive_link: Drive share link
        """
        self._drive_links[alan_adi] = drive_link
        logger.debug(f"Drive link set: {alan_adi} -> {drive_link[:50]}...")

    def get_drive_link(self, alan_adi: str) -> Optional[str]:
        """Drive link'ini al."""
        return self._drive_links.get(alan_adi)

    def clear(self, alan_adi: Optional[str] = None):
        """Cache'i temizle."""
        if alan_adi:
            self._file_paths.pop(alan_adi, None)
            self._drive_links.pop(alan_adi, None)
        else:
            self._file_paths.clear()
            self._drive_links.clear()

    # ────────────────────────────────────────────────────────────────────────
    # Helper Methods
    # ────────────────────────────────────────────────────────────────────────

    @staticmethod
    def create_upload_button(text: str = "Yükle") -> QPushButton:
        """
        Upload butonu oluştur.
        
        Args:
            text: Button metni
        
        Returns:
            QPushButton widget
        """
        btn = QPushButton(text)
        btn.setCursor(QCursor(Qt.PointingHandCursor))
        btn.setFixedSize(80, 28)
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {C.ACCENT_PRIMARY};
                color: white;
                border: none;
                border-radius: 4px;
                font-weight: 600;
                font-size: 11px;
                padding: 4px;
            }}
            QPushButton:hover {{
                background-color: {C.ACCENT_HOVER};
                opacity: 0.9;
            }}
            QPushButton:pressed {{
                background-color: {C.ACCENT_ACTIVE};
            }}
            QPushButton:disabled {{
                background-color: {C.TEXT_DISABLED};
                color: {C.BG_SECONDARY};
            }}
        """)
        return btn

    @staticmethod
    def create_view_button(text: str = "Görüntüle") -> QPushButton:
        """
        View butonu oluştur.
        
        Args:
            text: Button metni
        
        Returns:
            QPushButton widget
        """
        btn = QPushButton(text)
        btn.setCursor(QCursor(Qt.PointingHandCursor))
        btn.setFixedSize(90, 28)
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {C.BG_SECONDARY};
                color: {C.TEXT_PRIMARY};
                border: 1px solid {C.BORDER_PRIMARY};
                border-radius: 4px;
                font-weight: 600;
                font-size: 11px;
                padding: 4px;
            }}
            QPushButton:hover {{
                background-color: {C.BG_TERTIARY};
                border: 1px solid {C.ACCENT_PRIMARY};
            }}
            QPushButton:disabled {{
                color: {C.TEXT_DISABLED};
                border: 1px solid {C.BORDER_PRIMARY};
            }}
        """)
        return btn
