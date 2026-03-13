# ui/pages/fhsz/dis_alan_merkez_page.py
# -*- coding: utf-8 -*-
"""
Dış Alan Merkez — Import ve Puantaj Raporu birleşik sayfa
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTabWidget
)
from ui.pages.fhsz.dis_alan_import_page import DisAlanImportPage
from ui.pages.fhsz.puantaj_rapor_page import DisAlanPuantajRaporPage

class DisAlanMerkezPage(QWidget):
    def __init__(self, db=None, parent=None):
        super().__init__(parent)
        self._db = db
        self._setup_ui()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        
        self.tabs = QTabWidget()
        self.tabs.addTab(DisAlanImportPage(db=self._db), "Excel Import")
        self.tabs.addTab(DisAlanPuantajRaporPage(db=self._db), "Puantaj Raporu")
        root.addWidget(self.tabs)
