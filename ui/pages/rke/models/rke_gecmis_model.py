# -*- coding: utf-8 -*-
"""RKE gecmis model."""

from typing import List, Dict

from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex
from PySide6.QtGui import QColor

from ui.styles.colors import DarkTheme

GECMIS_COLS = [
    ("F_MuayeneTarihi", "Fiz. Tarih"),
    ("S_MuayeneTarihi", "Skopi Tarih"),
    ("Aciklamalar", "Aciklama"),
    ("Rapor", "Rapor"),
]


class GecmisModel(QAbstractTableModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._rows: List[Dict] = []

    def rowCount(self, parent=QModelIndex()):
        return len(self._rows)

    def columnCount(self, parent=QModelIndex()):
        return len(GECMIS_COLS)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        row = self._rows[index.row()]
        key = GECMIS_COLS[index.column()][0]

        if role == Qt.DisplayRole:
            val = str(row.get(key, ""))
            if key == "Rapor":
                return "Link" if "http" in val else "-"
            return val
        if role == Qt.ForegroundRole and key == "Rapor":
            if "http" in str(row.get(key, "")):
                return QColor(DarkTheme.ACCENT)
        if role == Qt.UserRole:
            return row
        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return GECMIS_COLS[section][1]
        return None

    def set_rows(self, rows):
        self.beginResetModel()
        self._rows = rows or []
        self.endResetModel()

    def get_row(self, idx):
        return self._rows[idx] if 0 <= idx < len(self._rows) else None
