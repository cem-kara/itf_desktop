"""
nobet_ayarlar_page.py — Admin Panel > Nöbet Ayarları sekmesi

Birim yönetimi ve vardiya tanımlarını tek ekranda toplar.
  Sekme 1: Birimler      — NB_Birim CRUD
  Sekme 2: Vardiyalar    — NB_VardiyaGrubu + NB_Vardiya
"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTabWidget,
)

from core.logger import logger


class NobetAyarlarPage(QWidget):
    """Admin Panel > Nöbet Ayarları."""

    def __init__(self, db=None, parent=None):
        super().__init__(parent)
        self._db = db
        self.setProperty("bg-role", "page")
        self._build()

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        tabs = QTabWidget()

        # ── Sekme 1: Birimler ─────────────────────────────────
        try:
            from ui.admin.nobet_birim_yonetim import NobetBirimYonetimPage
            self._birim_page = NobetBirimYonetimPage(db=self._db, parent=self)
            tabs.addTab(self._birim_page, "Birimler")
        except Exception as e:
            logger.error(f"Birimler sekmesi yüklenemedi: {e}")

        # ── Sekme 2: Vardiya Grupları & Vardiyalar ────────────
        try:
            from ui.admin.nobet_vardiya_page import NobetVardiyaPage
            self._vardiya_page = NobetVardiyaPage(db=self._db, parent=self)
            tabs.addTab(self._vardiya_page, "Vardiyalar")
        except Exception as e:
            logger.error(f"Vardiyalar sekmesi yüklenemedi: {e}")

        lay.addWidget(tabs)
