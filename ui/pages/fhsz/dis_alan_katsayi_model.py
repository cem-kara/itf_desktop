# ui/pages/fhsz/dis_alan_katsayi_model.py
# -*- coding: utf-8 -*-
from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex, QPersistentModelIndex
from PySide6.QtGui import QColor

KAT_SAYI_COLUMNS = [
    ("AnaBilimDali",       "Ana Bilim Dalı",    160),
    ("Birim",              "Birim",             140),
    ("Katsayi",            "Katsayı",            80),
    ("OrtSureDk",          "Ort. Süre (dk)",     95),
    ("AlanTipAciklama",    "Alan Tipi",         180),
    ("ProtokolRef",        "Protokol Ref",      140),
    ("GecerlilikBaslangic","Başlangıç",          95),
    ("GecerlilikBitis",    "Bitiş",              95),
    ("Aktif",              "Aktif",              60),
]

_KEYS   = [c[0] for c in KAT_SAYI_COLUMNS]
_LABELS = [c[1] for c in KAT_SAYI_COLUMNS]
_WIDTHS = [c[2] for c in KAT_SAYI_COLUMNS]

_CENTER = frozenset({"Katsayi", "OrtSureDk", "Aktif",
                     "GecerlilikBaslangic", "GecerlilikBitis"})


class DisAlanKatsayiModel(QAbstractTableModel):

    def __init__(self, rows=None, parent=None):
        super().__init__(parent)
        self._rows: list[dict] = rows or []

    # ── QAbstractTableModel arayüzü ──────────────────────────

    def rowCount(self, parent: QModelIndex | QPersistentModelIndex = QModelIndex()) -> int:
        return len(self._rows)

    def columnCount(self, parent: QModelIndex | QPersistentModelIndex = QModelIndex()) -> int:
        return len(KAT_SAYI_COLUMNS)

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole):
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return _LABELS[section]
        return None

    def data(self, index: QModelIndex | QPersistentModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        row  = self._rows[index.row()]
        key  = _KEYS[index.column()]
        val  = row.get(key)

        if role == Qt.ItemDataRole.DisplayRole:
            if key == "Aktif":
                return "Aktif" if val else "Pasif"
            if key == "Katsayi" and val is not None:
                return f"{float(val):.2f}"
            return str(val) if val is not None else ""

        if role == Qt.ItemDataRole.TextAlignmentRole:
            if key in _CENTER:
                return int(Qt.AlignmentFlag.AlignCenter)
            return int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)

        if role == Qt.ItemDataRole.ForegroundRole:
            if key == "Aktif":
                return QColor("#81C784") if val else QColor("#EF9A9A")

        if role == Qt.ItemDataRole.BackgroundRole:
            if key == "Aktif":
                return QColor("#1B5E20") if val else QColor("#3E2020")

        return None

    # ── Yardımcı metodlar ────────────────────────────────────

    def set_data(self, rows: list[dict]):
        self.beginResetModel()
        self._rows = rows or []
        self.endResetModel()

    def row_data(self, row: int) -> dict | None:
        if 0 <= row < len(self._rows):
            return self._rows[row]
        return None

    def setup_columns(self, view):
        """Kolon genişliklerini QTableView'a uygular."""
        from PySide6.QtWidgets import QHeaderView
        header = view.horizontalHeader()
        for i, w in enumerate(_WIDTHS):
            if w == 0:
                header.setSectionResizeMode(i, QHeaderView.ResizeMode.Stretch)
            elif i == len(_WIDTHS) - 1:
                header.setSectionResizeMode(i, QHeaderView.ResizeMode.Stretch)
            else:
                header.setSectionResizeMode(i, QHeaderView.ResizeMode.Fixed)
                view.setColumnWidth(i, w)
