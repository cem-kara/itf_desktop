# -*- coding: utf-8 -*-
"""RKE envanter table model."""

from typing import List, Dict

from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex
from PySide6.QtGui import QColor

from ui.styles.colors import DarkTheme

RKE_COLS = [
    ("EkipmanNo", "EKIPMAN NO", 120),
    ("KoruyucuNumarasi", "KORUYUCU NO", 140),
    ("AnaBilimDali", "ABD", 110),
    ("Birim", "BIRIM", 110),
    ("KoruyucuCinsi", "CINS", 110),
    ("KursunEsdegeri", "Pb", 70),
    ("HizmetYili", "YIL", 60),
    ("Bedeni", "BEDEN", 70),
    ("KontrolTarihi", "KONTROL T.", 100),
    ("Durum", "DURUM", 120),
]
RKE_KEYS = [c[0] for c in RKE_COLS]
RKE_HEADERS = [c[1] for c in RKE_COLS]
RKE_WIDTHS = [c[2] for c in RKE_COLS]

_COLOR_MAP = {
    "red": DarkTheme.STATUS_ERROR,
    "green": DarkTheme.STATUS_SUCCESS,
}


class RKEEnvanterModel(QAbstractTableModel):
    def __init__(self, rows=None, parent=None):
        super().__init__(parent)
        self._rows: List[Dict] = rows or []

    def rowCount(self, parent=QModelIndex()):
        return len(self._rows)

    def columnCount(self, parent=QModelIndex()):
        return len(RKE_COLS)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        row = self._rows[index.row()]
        key = RKE_KEYS[index.column()]

        if role == Qt.DisplayRole:
            return str(row.get(key, ""))
        if role == Qt.ForegroundRole and key == "Durum":
            v = row.get(key, "")
            if "Degil" in v or "Hurda" in v:
                return QColor(_COLOR_MAP["red"])
            if "Uygun" in v:
                return QColor(_COLOR_MAP["green"])
        if role == Qt.TextAlignmentRole:
            if key in ("KontrolTarihi", "Durum"):
                return Qt.AlignCenter
            return Qt.AlignVCenter | Qt.AlignLeft
        if role == Qt.UserRole:
            return row
        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return RKE_HEADERS[section]
        return None

    def set_rows(self, rows):
        self.beginResetModel()
        self._rows = rows or []
        self.endResetModel()

    def get_row(self, idx):
        return self._rows[idx] if 0 <= idx < len(self._rows) else None
