# -*- coding: utf-8 -*-
"""Teknik Hizmetler — Arıza, Bakım, Kalibrasyon yönetimi."""
from PySide6.QtWidgets import QWidget, QVBoxLayout, QTabWidget
from ui.pages.cihaz.ariza_kayit import ArizaKayitForm
from ui.pages.cihaz.bakim_form import BakimKayitForm
from ui.pages.cihaz.kalibrasyon_form import KalibrasyonKayitForm


class TeknikHizmetlerPage(QWidget):
    def __init__(self, db=None, action_guard=None, parent=None):
        super().__init__(parent)
        self._db = db
        self._action_guard = action_guard
        self.setProperty("bg-role", "page")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Tab widget oluştur
        self.tab_widget = QTabWidget()
        
        # Arıza Kayıt tab
        self.ariza_form = ArizaKayitForm(db=self._db, action_guard=self._action_guard)
        self.tab_widget.addTab(self.ariza_form, "Arıza Kayıt")
        
        # Bakım tab
        self.bakim_form = BakimKayitForm(db=self._db, action_guard=self._action_guard)
        self.tab_widget.addTab(self.bakim_form, "Bakım")
        
        # Kalibrasyon tab
        self.kalibrasyon_form = KalibrasyonKayitForm(db=self._db, action_guard=self._action_guard)
        self.tab_widget.addTab(self.kalibrasyon_form, "Kalibrasyon")
        
        layout.addWidget(self.tab_widget)
