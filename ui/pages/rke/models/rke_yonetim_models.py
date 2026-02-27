# -*- coding: utf-8 -*-
"""RKE Yönetim Modülü — Tablo Modelleri."""
from typing import List, Dict, Optional
from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex
from PySide6.QtGui import QColor
from ui.styles.colors import DarkTheme


# ════════════════════════════════════════════════════════════════════
#  SABITLER
# ════════════════════════════════════════════════════════════════════
RKE_YONETIM_COLS = [
    ("EkipmanNo",        "EKİPMAN NO",  120),
    ("KoruyucuNumarasi", "KORUYUCU NO", 140),
    ("AnaBilimDali",     "ABD",         110),
    ("Birim",            "BİRİM",       110),
    ("KoruyucuCinsi",    "CİNS",        110),
    ("KursunEsdegeri",   "Pb",           70),
    ("HizmetYili",       "YIL",          60),
    ("Bedeni",           "BEDEN",        70),
    ("KontrolTarihi",    "KONTROL T.",  100),
    ("Durum",            "DURUM",       120),
]
RKE_YONETIM_KEYS = [c[0] for c in RKE_YONETIM_COLS]
RKE_YONETIM_HEADERS = [c[1] for c in RKE_YONETIM_COLS]
RKE_YONETIM_WIDTHS = [c[2] for c in RKE_YONETIM_COLS]


# ════════════════════════════════════════════════════════════════════
#  TABLO MODELLERİ
# ════════════════════════════════════════════════════════════════════
class RKETableModel(QAbstractTableModel):
    """RKE Envanter Tablosu Modeli."""
    def __init__(self, rows=None, parent=None):
        super().__init__(parent)
        self._rows: List[Dict] = rows or []

    def rowCount(self, p=QModelIndex()):
        return len(self._rows)

    def columnCount(self, p=QModelIndex()):
        return len(RKE_YONETIM_COLS)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        row = self._rows[index.row()]
        key = RKE_YONETIM_KEYS[index.column()]
        
        if role == Qt.DisplayRole:
            return str(row.get(key, ""))
        
        if role == Qt.ForegroundRole and key == "Durum":
            v = row.get(key, "")
            if "Değil" in v or "Hurda" in v:
                return QColor(DarkTheme.STATUS_ERROR)
            if "Uygun" in v:
                return QColor(DarkTheme.STATUS_SUCCESS)
            if "Tamirde" in v:
                return QColor(DarkTheme.STATUS_WARNING)
        
        if role == Qt.TextAlignmentRole:
            return (Qt.AlignCenter if key in ("KontrolTarihi", "HizmetYili", "Durum", "KursunEsdegeri", "Bedeni")
                    else Qt.AlignVCenter | Qt.AlignLeft)
        
        if role == Qt.UserRole:
            return row
        
        return None

    def headerData(self, s, o, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and o == Qt.Horizontal:
            return RKE_YONETIM_HEADERS[s]
        return None

    def set_rows(self, rows):
        self.beginResetModel()
        self._rows = rows or []
        self.endResetModel()

    def get_row(self, i) -> Optional[Dict]:
        return self._rows[i] if 0 <= i < len(self._rows) else None


class RKEGecmisModel(QAbstractTableModel):
    """Muayene Geçmiş Tablosu Modeli."""
    _COLS = ["Tarih", "Sonuç", "Açıklama"]
    _HEADERS = ["TARİH", "SONUÇ", "AÇIKLAMA"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._rows: List[Dict] = []

    def rowCount(self, p=QModelIndex()):
        return len(self._rows)

    def columnCount(self, p=QModelIndex()):
        return 3

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        row = self._rows[index.row()]
        
        if role == Qt.DisplayRole:
            return str(row.get(self._COLS[index.column()], ""))
        
        if role == Qt.ForegroundRole and index.column() == 1:
            v = row.get("Sonuç", "")
            if "Değil" in v:
                return QColor(DarkTheme.STATUS_ERROR)
            if "Uygun" in v:
                return QColor(DarkTheme.STATUS_SUCCESS)
        
        return None

    def headerData(self, s, o, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and o == Qt.Horizontal:
            return self._HEADERS[s]
        return None

    def set_rows(self, rows):
        self.beginResetModel()
        self._rows = rows or []
        self.endResetModel()
