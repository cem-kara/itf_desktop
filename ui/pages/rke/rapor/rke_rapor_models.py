# -*- coding: utf-8 -*-
"""
RKE Rapor Tablo Modeli
ï¿½ï¿½ï¿½ï¿½ï¿½ï¿½ï¿½ï¿½ï¿½ï¿½ï¿½ï¿½ï¿½ï¿½ï¿½ï¿½ï¿½ï¿½ï¿½ï¿½ï¿½ï¿½ï¿½
ï¿½ RaporTableModel ï¿½ Birleï¿½ik muayene + envanter verisi gï¿½rï¿½nï¿½mï¿½
"""
from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex
from PySide6.QtGui import QColor

from ui.styles import DarkTheme

COLUMNS = [
    ("EkipmanNo",   "Ekipman No",    110),
    ("Cins",        "Cins",          120),
    ("Pb",          "Pb (mm)",        80),
    ("Birim",       "Birim",         130),
    ("Tarih",       "Tarih",          90),
    ("Sonuc",       "Sonuï¿½",         140),
    ("Aciklama",    "Aï¿½ï¿½klama",      200),
    ("KontrolEden", "Kontrol Eden",  140),
]

SONUC_RENK = {
    "Kullanï¿½ma Uygun":       QColor(DarkTheme.STATUS_SUCCESS),
    "Kullanï¿½ma Uygun Deï¿½il": QColor(DarkTheme.STATUS_ERROR),
}


class RaporTableModel(QAbstractTableModel):

    def __init__(self, data=None, parent=None):
        super().__init__(parent)
        self._data    = data or []
        self._keys    = [c[0] for c in COLUMNS]
        self._headers = [c[1] for c in COLUMNS]

    def rowCount(self, parent=QModelIndex()):    return len(self._data)
    def columnCount(self, parent=QModelIndex()): return len(COLUMNS)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        row = self._data[index.row()]
        col = self._keys[index.column()]

        if role == Qt.DisplayRole:
            return str(row.get(col, ""))
        if role == Qt.ForegroundRole and col == "Sonuc":
            return SONUC_RENK.get(str(row.get(col, "")), QColor(DarkTheme.TEXT_MUTED))
        if role == Qt.TextAlignmentRole:
            return (
                Qt.AlignCenter
                if col in ("Tarih", "Pb", "Sonuc")
                else Qt.AlignVCenter | Qt.AlignLeft
            )
        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self._headers[section]
        return None

    def get_row(self, row_idx):
        return self._data[row_idx] if 0 <= row_idx < len(self._data) else None

    def set_data(self, data):
        self.beginResetModel()
        self._data = data or []
        self.endResetModel()
