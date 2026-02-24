# -*- coding: utf-8 -*-
"""Cihaz Arıza Paneli — ArizaKayitForm wrapper."""
from typing import Optional

from PySide6.QtWidgets import QWidget, QVBoxLayout

from ui.pages.cihaz.ariza_kayit import ArizaKayitForm


class CihazArizaPanel(QWidget):
    """Cihaz bazlı arıza kayıt paneli (ArizaKayitForm wrapper)."""

    def __init__(self, db, cihaz_id: Optional[str] = None, parent=None):
        super().__init__(parent)
        self._db = db
        self._cihaz_id = cihaz_id

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.ariza_form = ArizaKayitForm(db=self._db, cihaz_id=self._cihaz_id)
        layout.addWidget(self.ariza_form)

        # CihazMerkez uyumlulugu: islem_penceresi'ni disariya ac
        self.islem_penceresi = getattr(self.ariza_form, "islem_penceresi", None)

    def set_cihaz_id(self, cihaz_id: Optional[str]):
        self._cihaz_id = cihaz_id
        if hasattr(self.ariza_form, "set_cihaz_id"):
            self.ariza_form.set_cihaz_id(cihaz_id)

    def load_data(self):
        if hasattr(self.ariza_form, "_load_data"):
            self.ariza_form._load_data()
