# -*- coding: utf-8 -*-
"""Kalibrasyon Kayıt — Tablo Modeli & Stil."""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex
from PySide6.QtGui import QColor

from core.date_utils import to_ui_date
from ui.styles.colors import DarkTheme


KAL_COLUMNS = [
    ("Kalid", "Kal. No", 90),
    ("Cihazid", "Cihaz", 110),
    ("Firma", "Firma", 130),
    ("SertifikaNo", "Sertifika", 110),
    ("YapilanTarih", "Yapılan", 100),
    ("BitisTarihi", "Geçerlilik", 100),
    ("Durum", "Durum", 100),
]

KAL_KEYS = [c[0] for c in KAL_COLUMNS]
KAL_HEADERS = [c[1] for c in KAL_COLUMNS]

_DURUM_COLOR = {
    "Gecerli": getattr(DarkTheme, "SUCCESS", "#3ecf8e"),
    "Geçerli": getattr(DarkTheme, "SUCCESS", "#3ecf8e"),
    "Gecersiz": getattr(DarkTheme, "DANGER", "#f75f5f"),
    "Geçersiz": getattr(DarkTheme, "DANGER", "#f75f5f"),
}


def _bitis_rengi(bitis_raw: str) -> str:
    red = getattr(DarkTheme, "DANGER", "#f75f5f")
    amber = getattr(DarkTheme, "WARNING", "#f5a623")
    green = getattr(DarkTheme, "SUCCESS", "#3ecf8e")
    muted = getattr(DarkTheme, "TEXT_MUTED", "#5a6278")

    if not bitis_raw or len(bitis_raw) < 10:
        return muted
    try:
        bt = datetime.strptime(bitis_raw[:10], "%Y-%m-%d").date()
        bugun = datetime.now().date()
        if bt < bugun:
            return red
        if bt <= bugun + timedelta(days=30):
            return amber
        return green
    except ValueError:
        return muted


class KalibrasyonTableModel(QAbstractTableModel):
    """Kalibrasyon listesi tablo modeli."""

    def __init__(self, rows: Optional[List[Dict[str, Any]]] = None, parent=None):
        super().__init__(parent)
        self._rows = rows or []

    def rowCount(self, parent=QModelIndex()):
        return len(self._rows)

    def columnCount(self, parent=QModelIndex()):
        return len(KAL_COLUMNS)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        row = self._rows[index.row()]
        key = KAL_KEYS[index.column()]

        if role == Qt.DisplayRole:
            val = row.get(key, "")
            if key in ("YapilanTarih", "BitisTarihi"):
                return to_ui_date(val, "")
            return str(val) if val else ""

        if role == Qt.TextAlignmentRole:
            if key in ("YapilanTarih", "BitisTarihi", "Durum"):
                return Qt.AlignCenter
            return Qt.AlignVCenter | Qt.AlignLeft

        if role == Qt.ForegroundRole:
            if key == "Durum":
                c = _DURUM_COLOR.get(row.get("Durum", ""))
                return QColor(c) if c else None
            if key == "BitisTarihi":
                return QColor(_bitis_rengi(row.get("BitisTarihi", "")))

        if role == Qt.BackgroundRole and key == "Durum":
            durum = row.get("Durum", "")
            if durum in ("Gecerli", "Geçerli"):
                return QColor(getattr(DarkTheme, "SUCCESS", "#3ecf8e") + "22")
            if durum in ("Gecersiz", "Geçersiz"):
                return QColor(getattr(DarkTheme, "DANGER", "#f75f5f") + "22")
        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return KAL_HEADERS[section]
        return None

    def set_rows(self, rows: List[Dict[str, Any]]):
        self.beginResetModel()
        self._rows = rows or []
        self.endResetModel()

    def get_row(self, row_idx: int) -> Optional[Dict[str, Any]]:
        if 0 <= row_idx < len(self._rows):
            return self._rows[row_idx]
        return None
