# -*- coding: utf-8 -*-
"""Bakim Panel — cihaz bazli bakim formu wrapper."""
from typing import Optional

from PySide6.QtWidgets import QWidget, QVBoxLayout

from ui.pages.cihaz.bakim_form import BakimKayitForm


class BakimDetailPanel(QWidget):
    """Cihaz merkez icin BakimKayitForm sarmalayici."""

    def __init__(self, db, cihaz_id: Optional[str] = None, parent=None):
        super().__init__(parent)
        self._db = db
        self._cihaz_id = cihaz_id

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.bakim_form = BakimKayitForm(db=self._db, cihaz_id=self._cihaz_id)
        layout.addWidget(self.bakim_form)

    def set_cihaz_id(self, cihaz_id: Optional[str]):
        self._cihaz_id = cihaz_id
        if hasattr(self.bakim_form, "set_cihaz_id"):
            self.bakim_form.set_cihaz_id(cihaz_id)

    def load_data(self):
        if hasattr(self.bakim_form, "_load_data"):
            self.bakim_form._load_data()
