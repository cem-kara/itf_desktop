# -*- coding: utf-8 -*-
"""
nobet_merkez.py — Nöbet Yönetimi Ana Sayfası

Sekmeler:
  BIRIM    → Birim & Vardiya tanımları
  PLAN     → Takvim görünümü + otomatik planlama
  OZET     → Personel nöbet yükü özeti
  RAPOR    → PDF / Excel çıktı
"""
from __future__ import annotations
from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel,
    QPushButton, QStackedWidget,
)

from core.di import get_nobet_service
from core.logger import logger
from core.hata_yonetici import hata_goster
from ui.styles.icons import IconRenderer, IconColors

_TABS = [
    ("BIRIM",  "settings",   "Birim Tanımları"),
    ("PLAN",   "calendar",   "Nöbet Planı"),
    ("OZET",   "bar_chart",  "Personel Özeti"),
    ("RAPOR",  "file_text",  "Raporlar"),
]


class NobetMerkezPage(QWidget):

    def __init__(self, db=None, action_guard=None, parent=None):
        super().__init__(parent)
        self._db           = db
        self._action_guard = action_guard
        self._modules:  dict[str, QWidget] = {}
        self._nav_btns: dict[str, QPushButton] = {}
        self._active    = ""
        self._setup_ui()
        self._switch_tab("BIRIM")

    def _setup_ui(self):
        self.setProperty("bg-role", "page")
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._build_header())
        self._stack = QStackedWidget()
        root.addWidget(self._stack, 1)

    def _build_header(self) -> QFrame:
        outer = QFrame()
        outer.setProperty("bg-role", "panel")
        outer.setFixedHeight(44)
        lay = QHBoxLayout(outer)
        lay.setContentsMargins(16, 0, 16, 0)
        lay.setSpacing(0)

        ico = QLabel()
        IconRenderer.set_label_icon(ico, "clock", color="#3d8ef5", size=18)
        lay.addWidget(ico)

        lbl = QLabel("  Nöbet Yönetimi")
        lbl.setProperty("style-role", "title")
        lbl.setProperty("color-role", "primary")
        lay.addWidget(lbl)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setFixedHeight(22)
        sep.setProperty("bg-role", "separator")
        lay.addSpacing(16)
        lay.addWidget(sep)
        lay.addSpacing(4)

        for code, icon, label in _TABS:
            btn = QPushButton(f"  {label}")
            btn.setFixedHeight(44)
            btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            btn.setFlat(True)
            btn.setStyleSheet(self._tab_qss(False))
            IconRenderer.set_button_icon(btn, icon, color="#4d6070", size=14)
            btn.clicked.connect(lambda _, c=code: self._switch_tab(c))
            self._nav_btns[code] = btn
            lay.addWidget(btn)

        lay.addStretch()

        btn_yenile = QPushButton()
        btn_yenile.setFixedSize(32, 32)
        btn_yenile.setToolTip("Yenile")
        btn_yenile.setProperty("style-role", "secondary")
        btn_yenile.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        IconRenderer.set_button_icon(btn_yenile, "refresh", color="#4d6070", size=15)
        btn_yenile.clicked.connect(self._yenile)
        lay.addWidget(btn_yenile)
        return outer

    def _switch_tab(self, code: str):
        if code == self._active:
            return
        self._active = code
        for c, btn in self._nav_btns.items():
            active = c == code
            btn.setStyleSheet(self._tab_qss(active))
            icon = next(ic for cd, ic, _ in _TABS if cd == c)
            IconRenderer.set_button_icon(
                btn, icon,
                color="#3d8ef5" if active else "#4d6070",
                size=14,
            )
        if code not in self._modules:
            w = self._create_module(code)
            self._modules[code] = w
            self._stack.addWidget(w)
        self._stack.setCurrentWidget(self._modules[code])

    def _create_module(self, code: str) -> QWidget:
        try:
            if code == "BIRIM":
                from ui.pages.nobet.nobet_birim_page import NobetBirimPage
                return NobetBirimPage(db=self._db,
                                      action_guard=self._action_guard)
            elif code == "PLAN":
                from ui.pages.nobet.nobet_plan_page import NobetPlanPage
                return NobetPlanPage(db=self._db,
                                     action_guard=self._action_guard)
            elif code == "OZET":
                from ui.pages.nobet.nobet_ozet_page import NobetOzetPage
                return NobetOzetPage(db=self._db,
                                     action_guard=self._action_guard)
            elif code == "RAPOR":
                from ui.pages.nobet.nobet_rapor_page import NobetRaporPage
                return NobetRaporPage(db=self._db,
                                      action_guard=self._action_guard)
            else:
                raise ValueError(f"Bilinmeyen sekme: {code}")
        except Exception as e:
            logger.error(f"Nöbet modül yükleme hatası ({code}): {e}")
            err = QLabel(f"Modül yüklenemedi: {code}\n{e}")
            err.setAlignment(Qt.AlignmentFlag.AlignCenter)
            err.setProperty("color-role", "err")
            return err

    def _yenile(self):
        w = self._modules.get(self._active)
        if w and hasattr(w, "load_data"):
            w.load_data()

    def load_data(self):
        self._yenile()

    @staticmethod
    def _tab_qss(active: bool) -> str:
        if active:
            return ("QPushButton{background:transparent;border:none;"
                    "border-bottom:2px solid #3d8ef5;color:#e8edf5;"
                    "font-size:13px;font-weight:700;padding:0 14px;}")
        return ("QPushButton{background:transparent;border:none;"
                "border-bottom:2px solid transparent;color:#4d6070;"
                "font-size:13px;font-weight:600;padding:0 14px;}"
                "QPushButton:hover{color:#e8edf5;}")
