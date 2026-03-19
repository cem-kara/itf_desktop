# -*- coding: utf-8 -*-
"""
import_center.py — Toplu Veri İçe Aktarma Merkezi
Tüm toplu Excel içe aktarma ekranlarını tek merkezde sekmeli olarak sunar.
"""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QTabWidget

from ui.pages.imports.personel_import_page    import PersonelImportPage
from ui.pages.imports.cihaz_import_page       import CihazImportPage
from ui.pages.imports.rke_import_page         import RkeListImportPage, RkeMuayeneImportPage
from ui.pages.imports.dozimetre_import_page   import DozimetreImportPage
from ui.pages.imports.dozimetre_pdf_import_page import DozimetrePdfImportPage
from ui.pages.imports.dis_alan_import_page    import DisAlanImportPage
from ui.pages.imports.izin_bilgi_import_page  import IzinBilgiImportPage
from ui.pages.imports.izin_giris_import_page  import IzinGirisImportPage


class ImportCenterPage(QWidget):
    def __init__(self, db=None, parent=None):
        super().__init__(parent)
        self._db = db
        self.setWindowTitle("Toplu Veri İçe Aktarma Merkezi")
        self.resize(1200, 750)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.tabs = QTabWidget()
        self.tabs.addTab(PersonelImportPage(db=self._db),      "👤  Personel")
        self.tabs.addTab(CihazImportPage(db=self._db),          "🔧  Cihaz")
        self.tabs.addTab(RkeListImportPage(db=self._db),        "📋  RKE Liste")
        self.tabs.addTab(RkeMuayeneImportPage(db=self._db),     "🔍  RKE Muayene")
        self.tabs.addTab(DozimetrePdfImportPage(db=self._db),   "☢️  Dozimetre (PDF)")
        self.tabs.addTab(DozimetreImportPage(db=self._db),      "☢️  Dozimetre (Excel)")
        self.tabs.addTab(DisAlanImportPage(db=self._db),        "🏗️  Dış Alan")
        self.tabs.addTab(IzinBilgiImportPage(db=self._db),      "📊  İzin Bakiye")
        self.tabs.addTab(IzinGirisImportPage(db=self._db),      "📅  İzin Giriş")

        layout.addWidget(self.tabs)
