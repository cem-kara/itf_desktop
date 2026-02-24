# -*- coding: utf-8 -*-
"""Kalibrasyon Panel — cihaz bazli kalibrasyon formu wrapper."""
from typing import Optional

from PySide6.QtWidgets import QWidget, QVBoxLayout

from ui.pages.cihaz.kalibrasyon_form import KalibrasyonKayitForm


class KalibrasyonDetailPanel(QWidget):
    """Cihaz merkez icin KalibrasyonKayitForm sarmalayici."""

    def __init__(self, db, cihaz_id: Optional[str] = None, parent=None):
        super().__init__(parent)
        self._db = db
        self._cihaz_id = cihaz_id

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.kalibrasyon_form = KalibrasyonKayitForm(db=self._db, cihaz_id=self._cihaz_id)
        layout.addWidget(self.kalibrasyon_form)

    def set_cihaz_id(self, cihaz_id: Optional[str]):
        self._cihaz_id = cihaz_id
        if hasattr(self.kalibrasyon_form, "set_cihaz_id"):
            self.kalibrasyon_form.set_cihaz_id(cihaz_id)

    def load_data(self):
        if hasattr(self.kalibrasyon_form, "_load_data"):
            self.kalibrasyon_form._load_data()
