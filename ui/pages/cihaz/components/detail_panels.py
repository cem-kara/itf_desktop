# -*- coding: utf-8 -*-
"""Cihaz Detail Panels — Form wrapper'ları."""
from typing import Optional

from PySide6.QtWidgets import QWidget, QVBoxLayout

from ui.pages.cihaz.ariza_form_new import ArizaKayitForm
from ui.pages.cihaz.bakim_form_new import BakimKayitForm
from ui.pages.cihaz.kalibrasyon_form import KalibrasyonKayitForm


class CihazArizaPanel(QWidget):
    """Cihaz bazlı arıza kayıt paneli (ArizaKayitForm wrapper)."""

    def __init__(self, db, cihaz_id: Optional[str] = None, action_guard=None, parent=None):
        super().__init__(parent)
        self._db = db
        self._cihaz_id = cihaz_id
        self._action_guard = action_guard

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.ariza_form = ArizaKayitForm(
            db=self._db,
            cihaz_id=self._cihaz_id,
            action_guard=self._action_guard
        )
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


class BakimDetailPanel(QWidget):
    """Cihaz merkez icin BakimKayitForm sarmalayici."""

    def __init__(self, db, cihaz_id: Optional[str] = None, action_guard=None, parent=None):
        super().__init__(parent)
        self._db = db
        self._cihaz_id = cihaz_id
        self._action_guard = action_guard

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.bakim_form = BakimKayitForm(
            db=self._db,
            cihaz_id=self._cihaz_id,
            action_guard=self._action_guard
        )
        layout.addWidget(self.bakim_form)

    def set_cihaz_id(self, cihaz_id: Optional[str]):
        self._cihaz_id = cihaz_id
        if hasattr(self.bakim_form, "set_cihaz_id"):
            self.bakim_form.set_cihaz_id(cihaz_id)

    def load_data(self):
        if hasattr(self.bakim_form, "_load_data"):
            self.bakim_form._load_data()


class KalibrasyonDetailPanel(QWidget):
    """Cihaz merkez icin KalibrasyonKayitForm sarmalayici."""

    def __init__(self, db, cihaz_id: Optional[str] = None, action_guard=None, parent=None):
        super().__init__(parent)
        self._db = db
        self._cihaz_id = cihaz_id
        self._action_guard = action_guard

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.kalibrasyon_form = KalibrasyonKayitForm(
            db=self._db,
            cihaz_id=self._cihaz_id,
            action_guard=self._action_guard
        )
        layout.addWidget(self.kalibrasyon_form)

    def set_cihaz_id(self, cihaz_id: Optional[str]):
        self._cihaz_id = cihaz_id
        if hasattr(self.kalibrasyon_form, "set_cihaz_id"):
            self.kalibrasyon_form.set_cihaz_id(cihaz_id)

    def load_data(self):
        if hasattr(self.kalibrasyon_form, "_load_data"):
            self.kalibrasyon_form._load_data()
