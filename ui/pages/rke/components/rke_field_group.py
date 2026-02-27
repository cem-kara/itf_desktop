# -*- coding: utf-8 -*-
"""RKE FieldGroup component."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel

from ui.styles.colors import DarkTheme


class FieldGroup(QWidget):
    """Renkli sol serit + monospace baslik + icerik karti."""

    def __init__(self, title: str, color: str, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet(
            f"FieldGroup{{background:{DarkTheme.BG_SECONDARY};border:1px solid {DarkTheme.BORDER_PRIMARY};border-radius:6px;}}"
        )
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        hdr = QWidget()
        hdr.setFixedHeight(30)
        hdr.setAttribute(Qt.WA_StyledBackground, True)
        hdr.setStyleSheet(
            f"QWidget{{background:rgba(255,255,255,12);border-bottom:1px solid {DarkTheme.BORDER_PRIMARY};"
            f"border-top-left-radius:6px;border-top-right-radius:6px;}}"
        )
        hh = QHBoxLayout(hdr)
        hh.setContentsMargins(10, 0, 10, 0)
        hh.setSpacing(8)

        bar = QFrame()
        bar.setFixedSize(3, 14)
        bar.setStyleSheet(f"background:{color};border-radius:2px;border:none;")

        lbl = QLabel(title.upper())
        lbl.setStyleSheet(
            f"color:{color};background:transparent;font-size:9px;font-weight:700;"
            f"letter-spacing:2px;font-family:{DarkTheme.MONOSPACE};"
        )
        hh.addWidget(bar)
        hh.addWidget(lbl)
        hh.addStretch()
        root.addWidget(hdr)

        self._body = QWidget()
        self._body.setStyleSheet("background:transparent;")
        self._bl = QVBoxLayout(self._body)
        self._bl.setContentsMargins(10, 10, 10, 12)
        self._bl.setSpacing(8)
        root.addWidget(self._body)

    def add_widget(self, widget):
        self._bl.addWidget(widget)

    def add_layout(self, layout):
        self._bl.addLayout(layout)

    def body_layout(self) -> QVBoxLayout:
        return self._bl
