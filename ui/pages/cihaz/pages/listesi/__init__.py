# -*- coding: utf-8 -*-
"""Cihaz Listesi - MVP Pattern Implementation"""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget, QVBoxLayout

from core.logger import logger
from .listesi_view import CihazListesiView
from .listesi_presenter import CihazListesiPresenter
from .listesi_service import CihazListesiService
from .listesi_state import CihazListesiState


class CihazListesiPage(QWidget):
    """Uyumlanmış cihaz listesi sayfası - yeni MVP mimaresine geçiş."""

    detay_requested = Signal(dict)
    edit_requested = Signal(dict)
    periodic_maintenance_requested = Signal(dict)
    add_requested = Signal()

    def __init__(self, db=None, action_guard=None, parent=None):
        super().__init__(parent)
        
        # Yeni MVP mimaresi
        self.service = CihazListesiService(db=db)
        self.presenter = CihazListesiPresenter(service=self.service, db=db)
        self.view = CihazListesiView(
            presenter=self.presenter,
            action_guard=action_guard,
            parent=self
        )
        
        # Signals'ları forward et
        self.view.detay_requested.connect(self.detay_requested.emit)
        self.view.edit_requested.connect(self.edit_requested.emit)
        self.view.periodic_maintenance_requested.connect(self.periodic_maintenance_requested.emit)
        self.view.add_requested.connect(self.add_requested.emit)
        self.view.refresh_requested.connect(self.load_data)
        
        # Layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.view)

    def load_data(self):
        """Veri yükle"""
        try:
            self.presenter.refresh_data()
        except Exception as e:
            logger.error(f"CihazListesiPage.load_data: {e}")

    # ─── Uyumluluk Metodları (eski API) ───────────────────

    def get_presenter(self):
        """old API uyumluluğu"""
        return self.presenter

    def get_model(self):
        """old API uyumluluğu"""
        return self.presenter.model


__all__ = [
    "CihazListesiPage",
    "CihazListesiView",
    "CihazListesiPresenter",
    "CihazListesiService",
    "CihazListesiState",
]
