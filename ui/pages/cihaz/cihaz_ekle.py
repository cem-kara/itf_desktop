# -*- coding: utf-8 -*-
"""Cihaz Ekle — placeholder (Cihaz modülü başlangıcı)."""
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton
from PySide6.QtCore import Qt, Signal

from ui.styles.components import STYLES
from ui.styles import DarkTheme


class CihazEklePage(QWidget):
    saved = Signal(dict)

    def __init__(self, db=None, on_saved=None, parent=None):
        super().__init__(parent)
        self._db = db
        self._on_saved = on_saved
        self.setStyleSheet(STYLES["page"])
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        title = QLabel("Cihaz Ekle")
        title.setStyleSheet(f"font-size:16px; font-weight:700; color:{DarkTheme.TEXT_PRIMARY};")
        layout.addWidget(title)

        info = QLabel("Cihaz ekleme formu bir sonraki adimda tasarlanacak.")
        info.setStyleSheet(f"font-size:12px; color:{DarkTheme.TEXT_SECONDARY};")
        info.setWordWrap(True)
        layout.addWidget(info)

        layout.addStretch()

        btn = QPushButton("Kaydet (Placeholder)")
        btn.setStyleSheet(STYLES["action_btn"])
        btn.setEnabled(False)
        layout.addWidget(btn)
