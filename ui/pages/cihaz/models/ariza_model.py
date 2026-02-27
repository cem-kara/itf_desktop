# -*- coding: utf-8 -*-
"""Arıza Kayıt — Tablo Modeli & Stil."""
from typing import List, Dict, Optional, Any
from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex
from PySide6.QtGui import QColor
from core.date_utils import to_ui_date
from ui.styles.colors import DarkTheme

# ════════════════════════════════════════════════════════════════════
#  TABLO SÜTUNLARI
# ════════════════════════════════════════════════════════════════════
ARIZA_COLUMNS = [
    ("Arizaid", "Arıza No", 90),
    ("Cihazid", "Cihaz", 110),
    ("BaslangicTarihi", "Tarih", 100),
    ("ArizaTipi", "Tip", 120),
    ("Oncelik", "Öncelik", 90),
    ("Baslik", "Başlık", 220),
    ("Durum", "Durum", 110),
]

ARIZA_KEYS = [c[0] for c in ARIZA_COLUMNS]
ARIZA_HEADERS = [c[1] for c in ARIZA_COLUMNS]
ARIZA_WIDTHS = [c[2] for c in ARIZA_COLUMNS]

# ════════════════════════════════════════════════════════════════════
#  RENKLERİ
# ════════════════════════════════════════════════════════════════════
DURUM_COLOR = {
    "Açık": getattr(DarkTheme, "DANGER", "#f75f5f"),
    "Acik": getattr(DarkTheme, "DANGER", "#f75f5f"),
    "Devam Ediyor": getattr(DarkTheme, "WARNING", "#f5a623"),
    "Kapalı": getattr(DarkTheme, "SUCCESS", "#3ecf8e"),
    "Kapali": getattr(DarkTheme, "SUCCESS", "#3ecf8e"),
}

DURUM_BG_COLOR = {
    "Açık": "rgba(247, 95, 95, 0.20)",
    "Acik": "rgba(247, 95, 95, 0.20)",
    "Devam Ediyor": "rgba(245, 166, 35, 0.20)",
    "Kapalı": "rgba(62, 207, 142, 0.20)",
    "Kapali": "rgba(62, 207, 142, 0.20)",
}

ONCELIK_COLOR = {
    "Kritik": getattr(DarkTheme, "DANGER", "#f75f5f"),
    "Yüksek": getattr(DarkTheme, "WARNING", "#f5a623"),
    "Orta": getattr(DarkTheme, "ACCENT", "#4f8ef7"),
    "Düşük": getattr(DarkTheme, "TEXT_MUTED", "#5a6278"),
}

ONCELIK_BG_COLOR = {
    "Kritik": "rgba(247, 95, 95, 0.20)",
    "Yüksek": "rgba(245, 166, 35, 0.20)",
    "Orta": "rgba(79, 142, 247, 0.20)",
    "Düşük": "rgba(90, 98, 120, 0.15)",
}


# ════════════════════════════════════════════════════════════════════
#  TABLO MODELİ
# ════════════════════════════════════════════════════════════════════
class ArizaTableModel(QAbstractTableModel):
    """Arıza listesi tablo modeli."""
    
    def __init__(self, rows: Optional[List[Dict[str, Any]]] = None, parent=None):
        super().__init__(parent)
        self._rows = rows or []

    def rowCount(self, parent=QModelIndex()):
        return len(self._rows)

    def columnCount(self, parent=QModelIndex()):
        return len(ARIZA_COLUMNS)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        row = self._rows[index.row()]
        key = ARIZA_KEYS[index.column()]

        if role == Qt.DisplayRole:
            val = row.get(key, "")
            if key == "BaslangicTarihi":
                return to_ui_date(val, "")
            return str(val) if val else ""

        if role == Qt.TextAlignmentRole:
            if key in ("BaslangicTarihi", "Oncelik", "Durum"):
                return Qt.AlignCenter
            return Qt.AlignVCenter | Qt.AlignLeft

        # Metin rengi
        if role == Qt.ForegroundRole:
            if key == "Durum":
                c = DURUM_COLOR.get(row.get("Durum", ""))
                return QColor(c) if c else None
            if key == "Oncelik":
                c = ONCELIK_COLOR.get(row.get("Oncelik", ""))
                return QColor(c) if c else None

        # Arka plan rengi
        if role == Qt.BackgroundRole:
            if key == "Durum":
                bg = DURUM_BG_COLOR.get(row.get("Durum", ""))
                return QColor(bg) if bg else None
            if key == "Oncelik":
                bg = ONCELIK_BG_COLOR.get(row.get("Oncelik", ""))
                return QColor(bg) if bg else None

        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return ARIZA_HEADERS[section]
        return None

    def set_rows(self, rows: List[Dict[str, Any]]):
        self.beginResetModel()
        self._rows = rows or []
        self.endResetModel()

    def get_row(self, row_idx: int) -> Optional[Dict[str, Any]]:
        if 0 <= row_idx < len(self._rows):
            return self._rows[row_idx]
        return None

    def all_rows(self) -> List[Dict[str, Any]]:
        return list(self._rows)
