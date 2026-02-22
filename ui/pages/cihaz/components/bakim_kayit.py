# -*- coding: utf-8 -*-
"""Bakim Kayit — bakim listesi + detay gorunum."""
from typing import List, Dict, Any, Optional

from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QGroupBox, QTableView, QHeaderView,
    QLabel, QGridLayout, QTextEdit
)

from core.date_utils import to_ui_date
from core.logger import logger
from database.repository_registry import RepositoryRegistry
from ui.styles.components import STYLES as S


BAKIM_COLUMNS = [
    ("Planid", "Plan No", 120),
    ("Cihazid", "Cihaz ID", 140),
    ("PlanlananTarih", "Planlanan", 110),
    ("BakimTarihi", "Bakim Tarihi", 110),
    ("BakimTipi", "Bakim Tipi", 140),
    ("Durum", "Durum", 100),
    ("Teknisyen", "Teknisyen", 140),
]


class BakimTableModel(QAbstractTableModel):
    def __init__(self, rows: Optional[List[Dict[str, Any]]] = None, parent=None):
        super().__init__(parent)
        self._rows = rows or []
        self._keys = [c[0] for c in BAKIM_COLUMNS]
        self._headers = [c[1] for c in BAKIM_COLUMNS]

    def rowCount(self, parent=QModelIndex()):
        return len(self._rows)

    def columnCount(self, parent=QModelIndex()):
        return len(BAKIM_COLUMNS)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        row = self._rows[index.row()]
        key = self._keys[index.column()]

        if role == Qt.DisplayRole:
            value = row.get(key, "")
            if key in ("PlanlananTarih", "BakimTarihi"):
                return to_ui_date(value, "")
            return str(value)

        if role == Qt.TextAlignmentRole:
            if key in ("PlanlananTarih", "BakimTarihi", "Durum"):
                return Qt.AlignCenter
            return Qt.AlignVCenter | Qt.AlignLeft

        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self._headers[section]
        return None

    def set_rows(self, rows: List[Dict[str, Any]]):
        self.beginResetModel()
        self._rows = rows or []
        self.endResetModel()

    def get_row(self, row_idx: int) -> Optional[Dict[str, Any]]:
        if 0 <= row_idx < len(self._rows):
            return self._rows[row_idx]
        return None


class BakimKayitPenceresi(QWidget):
    def __init__(self, db=None, cihaz_id: Optional[str] = None, parent=None):
        super().__init__(parent)
        self._db = db
        self._cihaz_id = cihaz_id
        self._rows: List[Dict[str, Any]] = []

        self.setStyleSheet(S["page"])
        self._setup_ui()
        self._load_data()

    def set_cihaz_id(self, cihaz_id: Optional[str]):
        self._cihaz_id = cihaz_id
        self._load_data()

    def load_data(self):
        self._load_data()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        # Tablo grubu
        grp_table = QGroupBox("Cihaza Ait Bakim Kayitlari")
        grp_table.setStyleSheet(S["group"])
        tl = QVBoxLayout(grp_table)
        tl.setContentsMargins(10, 10, 10, 10)
        tl.setSpacing(6)

        self._model = BakimTableModel()
        self.table = QTableView()
        self.table.setModel(self._model)
        self.table.setStyleSheet(S["table"])
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableView.SelectRows)
        self.table.setSelectionMode(QTableView.SingleSelection)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setSortingEnabled(True)

        header = self.table.horizontalHeader()
        header.setStretchLastSection(False)
        for i, (_, _, w) in enumerate(BAKIM_COLUMNS):
            if i == len(BAKIM_COLUMNS) - 2:
                header.setSectionResizeMode(i, QHeaderView.Stretch)
            else:
                header.setSectionResizeMode(i, QHeaderView.ResizeToContents)
            header.resizeSection(i, w)

        self.table.selectionModel().currentChanged.connect(self._on_row_selected)

        tl.addWidget(self.table)

        self.lbl_count = QLabel("0 kayit")
        self.lbl_count.setStyleSheet(S["footer_label"])
        tl.addWidget(self.lbl_count)

        root.addWidget(grp_table, 1)

        # Detay grubu
        grp_detail = QGroupBox("Bakim Ayrintilari")
        grp_detail.setStyleSheet(S["group"])
        dl = QGridLayout(grp_detail)
        dl.setContentsMargins(12, 12, 12, 12)
        dl.setHorizontalSpacing(16)
        dl.setVerticalSpacing(8)

        self._detail_labels = {}

        def add_row(r, c, label, key, multiline=False):
            lbl = QLabel(label)
            lbl.setStyleSheet(S["label"])
            dl.addWidget(lbl, r, c)

            if multiline:
                val = QTextEdit()
                val.setReadOnly(True)
                val.setStyleSheet(S["input_text"])
                val.setFixedHeight(80)
            else:
                val = QLabel("—")
                val.setStyleSheet(S["value"])
                val.setWordWrap(True)

            self._detail_labels[key] = val
            dl.addWidget(val, r, c + 1)

        add_row(0, 0, "Plan No", "Planid")
        add_row(0, 2, "Cihaz ID", "Cihazid")
        add_row(1, 0, "Planlanan Tarih", "PlanlananTarih")
        add_row(1, 2, "Bakim Tarihi", "BakimTarihi")
        add_row(2, 0, "Bakim", "Bakim")
        add_row(2, 2, "Bakim Tipi", "BakimTipi")
        add_row(3, 0, "Durum", "Durum")
        add_row(3, 2, "Teknisyen", "Teknisyen")
        add_row(4, 0, "Bakim Periyodu", "BakimPeriyodu")
        add_row(4, 2, "Bakim Sirasi", "BakimSirasi")
        add_row(5, 0, "Yapilan Islemler", "YapilanIslemler", multiline=True)
        add_row(6, 0, "Aciklama", "Aciklama", multiline=True)
        add_row(7, 0, "Rapor", "Rapor", multiline=True)

        root.addWidget(grp_detail, 0)

    def _load_data(self):
        if not self._db:
            self._model.set_rows([])
            self.lbl_count.setText("0 kayit")
            return

        try:
            repo = RepositoryRegistry(self._db).get("Periyodik_Bakim")
            rows = repo.get_all()
            if self._cihaz_id:
                rows = [r for r in rows if str(r.get("Cihazid", "")) == str(self._cihaz_id)]
            rows.sort(key=lambda r: (r.get("PlanlananTarih") or ""), reverse=True)

            self._rows = rows
            self._model.set_rows(rows)
            self.lbl_count.setText(f"{len(rows)} kayit")

            if rows:
                self.table.selectRow(0)
                self._populate_details(rows[0])
            else:
                self._clear_details()

        except Exception as e:
            logger.error(f"Bakim kayitlari yuklenemedi: {e}")
            self._model.set_rows([])
            self.lbl_count.setText("0 kayit")
            self._clear_details()

    def _on_row_selected(self, current, _previous):
        if not current.isValid():
            self._clear_details()
            return
        row = self._model.get_row(current.row())
        if row:
            self._populate_details(row)

    def _populate_details(self, row: Dict[str, Any]):
        for key, widget in self._detail_labels.items():
            val = row.get(key, "")
            if key in ("PlanlananTarih", "BakimTarihi"):
                val = to_ui_date(val, "")
            if isinstance(widget, QTextEdit):
                widget.setPlainText(str(val or ""))
            else:
                widget.setText(str(val or "—"))

    def _clear_details(self):
        for widget in self._detail_labels.values():
            if isinstance(widget, QTextEdit):
                widget.setPlainText("")
            else:
                widget.setText("—")
