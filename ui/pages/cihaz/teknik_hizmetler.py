# -*- coding: utf-8 -*-
"""Teknik Hizmetler — Arıza, Bakım, Kalibrasyon yönetimi."""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QTabWidget
from ui.styles.components import STYLES
from ui.pages.cihaz.pages.ariza import ArizaView
from ui.pages.cihaz.pages.bakim import BakimView
from ui.pages.cihaz.pages.kalibrasyon import KalibrasyonView


class TeknikHizmetlerPage(QWidget):
    def __init__(self, db=None, action_guard=None, parent=None):
        super().__init__(parent)
        self._db = db
        self._action_guard = action_guard

        self._tabs = None
        self.ariza_form = None
        self.bakim_form = None
        self.kalibrasyon_form = None

        self._setup_ui()

    def _setup_ui(self):
        """Ana düzen ve sekmeleri oluştur."""
        self.setStyleSheet(STYLES["page"])

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._tabs = QTabWidget()
        self._tabs.setStyleSheet(STYLES.get("tab", ""))

        self.ariza_form = ArizaView(db=self._db, action_guard=self._action_guard)
        self._tabs.addTab(self.ariza_form, "Arıza Kayıt")

        self.bakim_form = BakimView(db=self._db, action_guard=self._action_guard)
        self._tabs.addTab(self.bakim_form, "Bakım")

        self.kalibrasyon_form = KalibrasyonView(db=self._db, action_guard=self._action_guard)
        self._tabs.addTab(self.kalibrasyon_form, "Kalibrasyon")

        layout.addWidget(self._tabs)

    @property
    def tab_widget(self):
        """Geriye dönük uyumluluk için sekme widget'ını döndür."""
        return self._tabs
