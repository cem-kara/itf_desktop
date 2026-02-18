# -*- coding: utf-8 -*-
"""
RKE Muayene Tablo Modelleri

• RKEListTableModel    → Sağ paneldeki ekipman listesi
• GecmisMuayeneModel   → Sol formdaki muayene geçmişi
"""
from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex
from PySide6.QtGui import QColor

from ui.styles import DarkTheme

# ─── Sütun tanımları 

RKE_COLUMNS = [
    ("EkipmanNo",     "Ekipman No",   120),
    ("AnaBilimDali",  "ABD",          140),
    ("Birim",         "Birim",        130),
    ("KoruyucuCinsi", "Cinsi",        130),
    ("KontrolTarihi", "Son Kontrol",  110),
    ("Durum",         "Durum",         90),
]

_GECMIS_COLS = [
    ("FMuayeneTarihi", "Fiz. Tarih"),
    ("SMuayeneTarihi", "Skopi Tarih"),
    ("Aciklamalar",    "Açıklama"),
    ("FizikselDurum",  "Sonuç"),
]

DURUM_RENK = {
    "Kullanıma Uygun":       QColor(DarkTheme.STATUS_SUCCESS),
    "Kullanıma Uygun Değil": QColor(DarkTheme.STATUS_ERROR),
    "Hurda":                 QColor(DarkTheme.STATUS_ERROR),
}


# ===============================================
#  EKİPMAN LİSTE MODELİ
# ===============================================

class RKEListTableModel(QAbstractTableModel):

    def __init__(self, data=None, parent=None):
        super().__init__(parent)
        self._data    = data or []
        self._keys    = [c[0] for c in RKE_COLUMNS]
        self._headers = [c[1] for c in RKE_COLUMNS]

    def rowCount(self, parent=QModelIndex()):    return len(self._data)
    def columnCount(self, parent=QModelIndex()): return len(RKE_COLUMNS)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        row = self._data[index.row()]
        col = self._keys[index.column()]

        if role == Qt.DisplayRole:
            return str(row.get(col, ""))
        if role == Qt.ForegroundRole and col == "Durum":
            return DURUM_RENK.get(str(row.get(col, "")), QColor(DarkTheme.TEXT_MUTED))
        if role == Qt.TextAlignmentRole:
            return Qt.AlignCenter if col in ("KontrolTarihi", "Durum") else Qt.AlignVCenter | Qt.AlignLeft
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


# ===============================================
#  GEÇMİŞ MUAYENE MODELİ
# ===============================================

class GecmisMuayeneModel(QAbstractTableModel):

    def __init__(self, parent=None):
        super().__init__(parent)
        self._data    = []
        self._keys    = [c[0] for c in _GECMIS_COLS]
        self._headers = [c[1] for c in _GECMIS_COLS]

    def rowCount(self, parent=QModelIndex()):    return len(self._data)
    def columnCount(self, parent=QModelIndex()): return len(_GECMIS_COLS)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        row = self._data[index.row()]
        col = self._keys[index.column()]

        if role == Qt.DisplayRole:
            return str(row.get(col, ""))
        if role == Qt.ForegroundRole and col == "FizikselDurum":
            val = str(row.get(col, ""))
            return QColor(DarkTheme.STATUS_ERROR) if "Değil" in val else QColor(DarkTheme.STATUS_SUCCESS)
        if role == Qt.TextAlignmentRole:
            return (
                Qt.AlignCenter
                if col in ("FMuayeneTarihi", "SMuayeneTarihi", "FizikselDurum")
                else Qt.AlignVCenter | Qt.AlignLeft
            )
        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self._headers[section]
        return None

    def set_data(self, data):
        self.beginResetModel()
        self._data = data or []
        self.endResetModel()
