# -*- coding: utf-8 -*-
"""
RKE Tablo Modelleri
────────────────────
• RKETableModel      – Ana ekipman listesi (QAbstractTableModel)
• _GecmisTableModel  – Muayene geçmişi (QAbstractTableModel)
"""
from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex
from PySide6.QtGui import QColor

from ui.styles import Colors, DarkTheme

# ─── Sütun tanımları ───
COLUMNS = [
    ("KayitNo",          "ID",           80),
    ("EkipmanNo",        "Ekipman No",  120),
    ("KoruyucuNumarasi", "Koruyucu No", 130),
    ("AnaBilimDali",     "ABD",         140),
    ("Birim",            "Birim",       130),
    ("KoruyucuCinsi",    "Cins",        130),
    ("KontrolTarihi",    "Son Kontrol", 110),
    ("Durum",            "Durum",        90),
]

DURUM_RENK = {
    "Kullanıma Uygun":       QColor(Colors.GREEN_400),
    "Kullanıma Uygun Değil": QColor(Colors.RED_400),
    "Hurda":                 QColor(Colors.RED_500),
    "Tamirde":               QColor(Colors.YELLOW_400),
    "Kayıp":                 QColor(Colors.GRAY_400),
}

_GECMIS_COLS = [
    ("FMuayeneTarihi", "Fiz. Tarih"),
    ("FizikselDurum",  "Fiziksel Sonuç"),
    ("Aciklamalar",    "Açıklama"),
]


# ═══════════════════════════════════════════════
#  ANA LİSTE MODELİ
# ═══════════════════════════════════════════════

class RKETableModel(QAbstractTableModel):

    def __init__(self, data=None, parent=None):
        super().__init__(parent)
        self._data    = data or []
        self._keys    = [c[0] for c in COLUMNS]
        self._headers = [c[1] for c in COLUMNS]

    def rowCount(self, parent=QModelIndex()):
        return len(self._data)

    def columnCount(self, parent=QModelIndex()):
        return len(COLUMNS)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        row     = self._data[index.row()]
        col_key = self._keys[index.column()]

        if role == Qt.DisplayRole:
            return str(row.get(col_key, ""))

        if role == Qt.ForegroundRole and col_key == "Durum":
            durum = str(row.get("Durum", ""))
            return DURUM_RENK.get(durum, QColor(DarkTheme.TEXT_MUTED))

        if role == Qt.TextAlignmentRole:
            if col_key in ("KayitNo", "KontrolTarihi", "Durum"):
                return Qt.AlignCenter
            return Qt.AlignVCenter | Qt.AlignLeft

        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self._headers[section]
        return None

    def get_row(self, row_idx):
        if 0 <= row_idx < len(self._data):
            return self._data[row_idx]
        return None

    def set_data(self, data):
        self.beginResetModel()
        self._data = data or []
        self.endResetModel()


# ═══════════════════════════════════════════════
#  MUAYENe GEÇMİŞİ MODELİ
# ═══════════════════════════════════════════════

class GecmisTableModel(QAbstractTableModel):

    def __init__(self, parent=None):
        super().__init__(parent)
        self._data    = []
        self._keys    = [c[0] for c in _GECMIS_COLS]
        self._headers = [c[1] for c in _GECMIS_COLS]

    def rowCount(self, parent=QModelIndex()):
        return len(self._data)

    def columnCount(self, parent=QModelIndex()):
        return len(_GECMIS_COLS)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        row = self._data[index.row()]
        col = self._keys[index.column()]

        if role == Qt.DisplayRole:
            return str(row.get(col, ""))

        if role == Qt.ForegroundRole and col == "FizikselDurum":
            val = str(row.get(col, ""))
            return QColor(Colors.RED_400) if "Değil" in val else QColor(Colors.GREEN_400)

        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self._headers[section]
        return None

    def set_data(self, data):
        self.beginResetModel()
        self._data = data or []
        self.endResetModel()
