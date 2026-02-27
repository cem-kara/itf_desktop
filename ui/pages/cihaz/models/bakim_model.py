# -*- coding: utf-8 -*-
"""Bakım Formu — Tablo Modeli."""
from typing import List, Dict, Optional
from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex
from PySide6.QtGui import QColor
from ui.styles.colors import DarkTheme

# ════════════════════════════════════════════════════════════════════
#  TABLO SÜTUNLARI
# ════════════════════════════════════════════════════════════════════
BAKIM_COLUMNS = [
    ("Planid",         "Plan No",      90),
    ("Cihazid",        "Cihaz",        110),
    ("PlanlananTarih", "Plan Tarihi",  100),
    ("BakimTarihi",    "Bakım Tarihi", 100),
    ("BakimPeriyodu",  "Periyot",      110),
    ("BakimTipi",      "Tip",          110),
    ("Teknisyen",      "Teknisyen",    130),
    ("Durum",          "Durum",        100),
]

BAKIM_KEYS = [c[0] for c in BAKIM_COLUMNS]
BAKIM_HEADERS = [c[1] for c in BAKIM_COLUMNS]
BAKIM_WIDTHS = [c[2] for c in BAKIM_COLUMNS]

# ════════════════════════════════════════════════════════════════════
#  DURUM RENKLERİ
# ════════════════════════════════════════════════════════════════════
DURUM_COLOR = {
    "Planlandı": getattr(DarkTheme, "ACCENT", "#4f8ef7"),
    "Planlandi": getattr(DarkTheme, "ACCENT", "#4f8ef7"),
    "Yapıldı": getattr(DarkTheme, "STATUS_SUCCESS", "#3ecf8e"),
    "Yapildi": getattr(DarkTheme, "STATUS_SUCCESS", "#3ecf8e"),
    "Gecikmiş": getattr(DarkTheme, "STATUS_ERROR", "#f75f5f"),
    "Gecikmis": getattr(DarkTheme, "STATUS_ERROR", "#f75f5f"),
}


# ════════════════════════════════════════════════════════════════════
#  TABLO MODELİ
# ════════════════════════════════════════════════════════════════════
class BakimTableModel(QAbstractTableModel):
    """Bakım planları tablosu modeli."""
    def __init__(self, rows=None, parent=None):
        super().__init__(parent)
        self._rows: List[Dict] = rows or []

    def rowCount(self, p=QModelIndex()):
        return len(self._rows)

    def columnCount(self, p=QModelIndex()):
        return len(BAKIM_COLUMNS)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        row = self._rows[index.row()]
        key = BAKIM_KEYS[index.column()]
        
        if role == Qt.DisplayRole:
            return str(row.get(key, ""))
        
        if role == Qt.ForegroundRole and key == "Durum":
            durum = row.get(key, "")
            color = DURUM_COLOR.get(durum, "#5a6278")
            return QColor(color)
        
        if role == Qt.UserRole:
            return row
        
        return None

    def headerData(self, s, o, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and o == Qt.Horizontal:
            return BAKIM_HEADERS[s]
        return None

    def set_rows(self, rows):
        self.beginResetModel()
        self._rows = rows or []
        self.endResetModel()

    def get_row(self, i) -> Optional[Dict]:
        return self._rows[i] if 0 <= i < len(self._rows) else None
