# -*- coding: utf-8 -*-
"""Ariza Kayit — placeholder."""
from PySide6.QtWidgets import QWidget, QVBoxLayout
from ui.pages.placeholder import PlaceholderPage
from ui.styles.components import STYLES


class ArizaKayitPenceresi(QWidget):
    def __init__(self, db=None, parent=None):
        super().__init__(parent)
        self._db = db
        self.setStyleSheet(STYLES["page"])
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(PlaceholderPage("Ariza Kayit", "Bu sayfa cihaz modulu icin hazirlaniyor."))
