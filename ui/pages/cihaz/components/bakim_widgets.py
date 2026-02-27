# -*- coding: utf-8 -*-
"""Bakım Form Components — Custom Widgets."""
from typing import List, Tuple
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox, QLabel
from PySide6.QtCore import Qt
from ui.styles.components import STYLES as S
from ui.styles.colors import DarkTheme


# ════════════════════════════════════════════════════════════════════
#  FORM PANEL
# ════════════════════════════════════════════════════════════════════
class FormPanel(QGroupBox):
    """Bakım formu için panel widget."""
    
    def __init__(self, title: str, parent=None):
        super().__init__(title, parent)
        self.setStyleSheet(S.get("group", ""))
        self.layout_main = QGridLayout(self)
        self.layout_main.setContentsMargins(12, 12, 12, 12)
        self.layout_main.setHorizontalSpacing(16)
        self.layout_main.setVerticalSpacing(8)
        self.row_counter = 0
    
    def add_field(self, label_text: str, widget: QWidget, colspan: int = 1):
        """Etiket + widget satırı ekle."""
        lbl = QLabel(label_text)
        lbl.setStyleSheet(S.get("label", "font-weight:600;"))
        self.layout_main.addWidget(lbl, self.row_counter, 0)
        self.layout_main.addWidget(widget, self.row_counter, 1, 1, colspan)
        self.row_counter += 1
    
    def add_row_fields(self, fields: List[Tuple]):
        """Aynı satırda birden fazla alan ekle."""
        col = 0
        for label_text, widget, colspan in fields:
            lbl = QLabel(label_text)
            lbl.setStyleSheet(S.get("label", "font-weight:600;"))
            self.layout_main.addWidget(lbl, self.row_counter, col)
            col += 1
            self.layout_main.addWidget(widget, self.row_counter, col, 1, colspan)
            col += colspan
        self.row_counter += 1
    
    def add_full_width_field(self, label_text: str, widget: QWidget):
        """Tam genişlikte alan ekle."""
        self.add_field(label_text, widget, colspan=3)


# ════════════════════════════════════════════════════════════════════
#  FIELD WIDGET
# ════════════════════════════════════════════════════════════════════
def create_field_label(title: str, value: str = "—", bg_panel: str = None) -> QWidget:
    """Detail view alanı oluştur."""
    w = QWidget()
    bg = bg_panel or getattr(DarkTheme, "PANEL", "#191d26")
    w.setStyleSheet(f"background:{bg};")
    vl = QVBoxLayout(w)
    vl.setContentsMargins(0, 0, 0, 0)
    vl.setSpacing(1)
    
    muted = getattr(DarkTheme, "TEXT_MUTED", "#5a6278")
    t = QLabel(title.upper())
    t.setStyleSheet(
        f"font-size:9px;letter-spacing:0.06em;color:{muted};font-weight:600;"
    )
    v = QLabel(value)
    v.setObjectName("val")
    text_pr = getattr(DarkTheme, "TEXT_PRIMARY", "#eef0f5")
    v.setStyleSheet(f"font-size:12px;color:{text_pr};")
    v.setWordWrap(True)
    vl.addWidget(t)
    vl.addWidget(v)
    return w


def set_field_value(widget: QWidget, value: str):
    """Field label'ı güncelle."""
    lbl = widget.findChild(QLabel, "val")
    if lbl:
        lbl.setText(value or "—")
