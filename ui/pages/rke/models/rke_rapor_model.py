# -*- coding: utf-8 -*-
"""RKE Raporlama — Tablo Modeli."""
from typing import List, Dict, Optional
from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex
from PySide6.QtGui import QColor
from ui.styles.colors import DarkTheme


# ════════════════════════════════════════════════════════════════════
#  SABITLER
# ════════════════════════════════════════════════════════════════════
RAPOR_COLS = [
    ("EkipmanNo", "EKİPMAN NO", 130),
    ("Cins", "CİNS", 110),
    ("Pb", "Pb", 70),
    ("Birim", "BİRİM", 110),
    ("Tarih", "TARİH", 100),
    ("Sonuc", "SONUÇ", 130),
    ("Aciklama", "AÇIKLAMA", 160),
]
RAPOR_KEYS = [c[0] for c in RAPOR_COLS]
RAPOR_HEADERS = [c[1] for c in RAPOR_COLS]
RAPOR_WIDTHS = [c[2] for c in RAPOR_COLS]


# ════════════════════════════════════════════════════════════════════
#  TABLO MODELİ
# ════════════════════════════════════════════════════════════════════
class RaporTableModel(QAbstractTableModel):
    """RKE Raporlama Tablosu Modeli."""
    def __init__(self, rows=None, parent=None):
        super().__init__(parent)
        self._rows: List[Dict] = rows or []

    def rowCount(self, p=QModelIndex()):
        return len(self._rows)

    def columnCount(self, p=QModelIndex()):
        return len(RAPOR_COLS)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        row = self._rows[index.row()]
        key = RAPOR_KEYS[index.column()]
        
        if role == Qt.DisplayRole:
            return str(row.get(key, ""))
        
        if role == Qt.ForegroundRole and key == "Sonuc":
            return QColor(DarkTheme.STATUS_ERROR) if "Değil" in row.get(key, "") else QColor(DarkTheme.STATUS_SUCCESS)
        
        if role == Qt.TextAlignmentRole:
            return Qt.AlignCenter if key in ("Tarih", "Sonuc", "Pb") else Qt.AlignVCenter | Qt.AlignLeft
        
        if role == Qt.UserRole:
            return row
        
        return None

    def headerData(self, s, o, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and o == Qt.Horizontal:
            return RAPOR_HEADERS[s]
        return None

    def set_rows(self, rows):
        self.beginResetModel()
        self._rows = rows or []
        self.endResetModel()

    def get_row(self, i) -> Optional[Dict]:
        return self._rows[i] if 0 <= i < len(self._rows) else None
