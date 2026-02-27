# -*- coding: utf-8 -*-
"""
Personel Overview — Form Fields
================================
Personel bilgisi form alanları.
"""
from typing import Dict, List, Optional

from PySide6.QtWidgets import QLineEdit, QComboBox, QDateEdit, QWidget, QHBoxLayout
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QFont

from ui.styles import DarkTheme

C = DarkTheme


# ─────────────────────────────────────────────────────────────────────────────
# Form Fields
# ─────────────────────────────────────────────────────────────────────────────

def create_form_field(label_text: str, editable: bool = False) -> QLineEdit:
    """
    Form input alanı oluştur.
    
    Args:
        label_text: Field etiketi
        editable: Düzenlenebilir mi
    
    Returns:
        QLineEdit widget
    """
    field = QLineEdit()
    field.setReadOnly(not editable)
    field.setFixedHeight(36)
    
    if editable:
        field.setStyleSheet(f"""
            QLineEdit {{
                background-color: {C.BG_PRIMARY};
                color: {C.TEXT_PRIMARY};
                border: 1px solid {C.BORDER_PRIMARY};
                padding: 8px;
                border-radius: 4px;
                selection-background-color: {C.ACCENT_PRIMARY};
            }}
            QLineEdit:focus {{
                border: 1px solid {C.ACCENT_PRIMARY};
                background-color: {C.BG_PRIMARY};
            }}
        """)
    else:
        field.setStyleSheet(f"""
            QLineEdit {{
                background-color: {C.BG_TERTIARY};
                color: {C.TEXT_SECONDARY};
                border: 1px solid {C.BORDER_PRIMARY};
                padding: 8px;
                border-radius: 4px;
            }}
            QLineEdit:focus {{
                border: 1px solid {C.BORDER_PRIMARY};
            }}
        """)
    
    return field


def create_combo_field(options: List[str], default: str = "") -> QComboBox:
    """
    Combo box alanı oluştur.
    
    Args:
        options: Combo seçenekleri
        default: Varsayılan seçenek
    
    Returns:
        QComboBox widget
    """
    combo = QComboBox()
    combo.addItems(options)
    combo.setFixedHeight(36)
    
    if default and default in options:
        combo.setCurrentText(default)
    
    combo.setStyleSheet(f"""
        QComboBox {{
            background-color: {C.BG_PRIMARY};
            color: {C.TEXT_PRIMARY};
            border: 1px solid {C.BORDER_PRIMARY};
            padding: 6px;
            border-radius: 4px;
        }}
        QComboBox::drop-down {{
            border: none;
            padding-right: 8px;
        }}
        QComboBox QAbstractItemView {{
            background-color: {C.BG_SECONDARY};
            color: {C.TEXT_PRIMARY};
            border: 1px solid {C.BORDER_PRIMARY};
            selection-background-color: {C.ACCENT_PRIMARY};
        }}
    """)
    
    return combo


def create_date_field(date_str: str = "") -> QDateEdit:
    """
    Tarih seçici alanı oluştur.
    
    Args:
        date_str: Tarih string'i (yyyy-MM-dd)
    
    Returns:
        QDateEdit widget
    """
    date_edit = QDateEdit()
    date_edit.setCalendarPopup(True)
    date_edit.setDate(QDate.fromString(date_str, "yyyy-MM-dd") if date_str else QDate.currentDate())
    date_edit.setFixedHeight(36)
    
    date_edit.setStyleSheet(f"""
        QDateEdit {{
            background-color: {C.BG_PRIMARY};
            color: {C.TEXT_PRIMARY};
            border: 1px solid {C.BORDER_PRIMARY};
            padding: 6px;
            border-radius: 4px;
        }}
        QDateEdit::drop-down {{
            border: none;
            padding-right: 8px;
        }}
    """)
    
    return date_edit


def create_readonly_field(value: str = "") -> QLineEdit:
    """
    Salt-okunur alan oluştur.
    
    Args:
        value: Alan değeri
    
    Returns:
        QLineEdit widget
    """
    field = QLineEdit(value)
    field.setReadOnly(True)
    field.setFixedHeight(36)
    field.setStyleSheet(f"""
        QLineEdit {{
            background-color: {C.BG_TERTIARY};
            color: {C.TEXT_SECONDARY};
            border: 1px solid {C.BORDER_PRIMARY};
            padding: 8px;
            border-radius: 4px;
        }}
    """)
    return field


# ─────────────────────────────────────────────────────────────────────────────
# Form Builder
# ─────────────────────────────────────────────────────────────────────────────

class FormSection:
    """
    Form bölümü (başlık + alanlar).
    
    Attributes:
        title: Başlık
        fields: {field_key: (label, widget, editable)}
    """

    def __init__(self, title: str):
        self.title = title
        self.fields: Dict[str, tuple] = {}

    def add_field(self, key: str, label: str, widget: QWidget, editable: bool = False):
        """Alan ekle."""
        self.fields[key] = (label, widget, editable)

    def get_values(self) -> Dict[str, str]:
        """Tüm field değerlerini al."""
        values = {}
        for key, (label, widget, _) in self.fields.items():
            if isinstance(widget, QLineEdit):
                values[key] = widget.text()
            elif isinstance(widget, QComboBox):
                values[key] = widget.currentText()
            elif isinstance(widget, QDateEdit):
                values[key] = widget.date().toString("yyyy-MM-dd")
        return values

    def set_values(self, data: Dict[str, str]):
        """Alan değerlerini set et."""
        for key, value in data.items():
            if key in self.fields:
                _, widget, _ = self.fields[key]
                if isinstance(widget, QLineEdit):
                    widget.setText(str(value))
                elif isinstance(widget, QComboBox):
                    widget.setCurrentText(str(value))
                elif isinstance(widget, QDateEdit):
                    widget.setDate(QDate.fromString(str(value), "yyyy-MM-dd"))
