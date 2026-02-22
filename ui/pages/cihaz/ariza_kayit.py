# -*- coding: utf-8 -*-
"""Ariza Kayit — ariza listesi + detay gorunum."""
from typing import List, Dict, Any, Optional

from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex, Signal, QDate
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QTableView,
    QHeaderView, QLabel, QGridLayout, QTextEdit, QLineEdit,
    QComboBox, QDateEdit, QPushButton
)

from core.date_utils import to_ui_date
from core.logger import logger
from database.repository_registry import RepositoryRegistry
from ui.styles.components import STYLES as S
from ui.styles.icons import IconRenderer
from ui.styles import DarkTheme
from datetime import datetime


ARIZA_COLUMNS = [
    ("Arizaid", "Ariza No", 90),
    ("Cihazid", "Cihaz ID", 140),
    ("BaslangicTarihi", "Baslangic", 110),
    ("Saat", "Saat", 70),
    ("ArizaTipi", "Ariza Tipi", 140),
    ("Oncelik", "Oncelik", 90),
    ("Baslik", "Baslik", 220),
    ("Durum", "Durum", 100),
]


class ArizaTableModel(QAbstractTableModel):
    def __init__(self, rows: Optional[List[Dict[str, Any]]] = None, parent=None):
        super().__init__(parent)
        self._rows = rows or []
        self._keys = [c[0] for c in ARIZA_COLUMNS]
        self._headers = [c[1] for c in ARIZA_COLUMNS]

    def rowCount(self, parent=QModelIndex()):
        return len(self._rows)

    def columnCount(self, parent=QModelIndex()):
        return len(ARIZA_COLUMNS)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        row = self._rows[index.row()]
        key = self._keys[index.column()]

        if role == Qt.DisplayRole:
            value = row.get(key, "")
            if key == "BaslangicTarihi":
                return to_ui_date(value, "")
            return str(value)

        if role == Qt.TextAlignmentRole:
            if key in ("BaslangicTarihi", "Saat", "Oncelik", "Durum"):
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


class ArizaKayitForm(QWidget):
    saved = Signal()

    def __init__(self, db=None, cihaz_id: Optional[str] = None, parent=None):
        super().__init__(parent)
        self._db = db
        self._cihaz_id = cihaz_id
        self._setup_ui()

    def set_cihaz_id(self, cihaz_id: Optional[str]):
        self._cihaz_id = cihaz_id

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(10)

        form = QGroupBox("Ariza Kaydi")
        form.setStyleSheet(S["group"])
        grid = QGridLayout(form)
        grid.setContentsMargins(12, 12, 12, 12)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(8)

        # Row 0
        self.dt_baslangic = QDateEdit(QDate.currentDate())
        self.dt_baslangic.setCalendarPopup(True)
        self.dt_baslangic.setDisplayFormat("dd.MM.yyyy")
        self.dt_baslangic.setStyleSheet(S["date"])
        self._add_row(grid, 0, "Baslangic Tarihi", self.dt_baslangic)

        self.txt_saat = QLineEdit()
        self.txt_saat.setPlaceholderText("HH:MM")
        self.txt_saat.setStyleSheet(S["input"])
        self._add_row(grid, 1, "Saat", self.txt_saat)

        self.txt_bildiren = QLineEdit()
        self.txt_bildiren.setStyleSheet(S["input"])
        self._add_row(grid, 2, "Bildiren", self.txt_bildiren)

        self.cmb_tip = QComboBox()
        self.cmb_tip.setEditable(True)
        self.cmb_tip.setStyleSheet(S["combo"])
        self.cmb_tip.addItems(["Elektrik", "Mekanik", "Yazilim", "Diger"])
        self._add_row(grid, 3, "Ariza Tipi", self.cmb_tip)

        self.cmb_oncelik = QComboBox()
        self.cmb_oncelik.setStyleSheet(S["combo"])
        self.cmb_oncelik.addItems(["Dusuk", "Orta", "Yuksek"])
        self._add_row(grid, 4, "Oncelik", self.cmb_oncelik)

        self.txt_baslik = QLineEdit()
        self.txt_baslik.setStyleSheet(S["input"])
        self._add_row(grid, 5, "Baslik", self.txt_baslik)

        self.txt_aciklama = QTextEdit()
        self.txt_aciklama.setStyleSheet(S["input_text"])
        self.txt_aciklama.setFixedHeight(80)
        self._add_row(grid, 6, "Ariza Aciklamasi", self.txt_aciklama)

        self.cmb_durum = QComboBox()
        self.cmb_durum.setStyleSheet(S["combo"])
        self.cmb_durum.addItems(["Acik", "Kapali"])
        self._add_row(grid, 7, "Durum", self.cmb_durum)

        self.txt_rapor = QTextEdit()
        self.txt_rapor.setStyleSheet(S["input_text"])
        self.txt_rapor.setFixedHeight(70)
        self._add_row(grid, 8, "Rapor", self.txt_rapor)

        root.addWidget(form)

        btns = QHBoxLayout()
        btns.addStretch()

        self.btn_clear = QPushButton("Temizle")
        self.btn_clear.setStyleSheet(S["btn_refresh"])
        self.btn_clear.clicked.connect(self._clear)
        btns.addWidget(self.btn_clear)

        self.btn_save = QPushButton("Kaydet")
        self.btn_save.setStyleSheet(S["action_btn"])
        try:
            IconRenderer.set_button_icon(self.btn_save, "save", color=DarkTheme.BTN_PRIMARY_TEXT, size=14)
        except Exception:
            pass
        self.btn_save.clicked.connect(self._save)
        btns.addWidget(self.btn_save)

        root.addLayout(btns)

    def _add_row(self, grid, row, label, widget):
        lbl = QLabel(label)
        lbl.setStyleSheet(S["label"])
        grid.addWidget(lbl, row, 0)
        grid.addWidget(widget, row, 1)

    def _save(self):
        if not self._db or not self._cihaz_id:
            return

        baslik = self.txt_baslik.text().strip()
        if not baslik:
            return

        ariza_id = f"{self._cihaz_id}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        data = {
            "Arizaid": ariza_id,
            "Cihazid": self._cihaz_id,
            "BaslangicTarihi": self.dt_baslangic.date().toString("yyyy-MM-dd"),
            "Saat": self.txt_saat.text().strip(),
            "Bildiren": self.txt_bildiren.text().strip(),
            "ArizaTipi": self.cmb_tip.currentText().strip(),
            "Oncelik": self.cmb_oncelik.currentText().strip(),
            "Baslik": baslik,
            "ArizaAcikla": self.txt_aciklama.toPlainText().strip(),
            "Durum": self.cmb_durum.currentText().strip(),
            "Rapor": self.txt_rapor.toPlainText().strip(),
        }

        try:
            repo = RepositoryRegistry(self._db).get("Cihaz_Ariza")
            repo.insert(data)
            self.saved.emit()
            self._clear()
        except Exception as e:
            logger.error(f"Ariza kaydi kaydedilemedi: {e}")

    def _clear(self):
        self.dt_baslangic.setDate(QDate.currentDate())
        self.txt_saat.clear()
        self.txt_bildiren.clear()
        self.cmb_tip.setCurrentIndex(0)
        self.cmb_oncelik.setCurrentIndex(0)
        self.txt_baslik.clear()
        self.txt_aciklama.clear()
        self.cmb_durum.setCurrentIndex(0)
        self.txt_rapor.clear()

class ArizaKayitPenceresi(QWidget):
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
        grp_table = QGroupBox("Cihaza Ait Ariza Kayitlari")
        grp_table.setStyleSheet(S["group"])
        tl = QVBoxLayout(grp_table)
        tl.setContentsMargins(10, 10, 10, 10)
        tl.setSpacing(6)

        self._model = ArizaTableModel()
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
        for i, (_, _, w) in enumerate(ARIZA_COLUMNS):
            if i == len(ARIZA_COLUMNS) - 2:
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
        grp_detail = QGroupBox("Ariza Ayrintilari")
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

        add_row(0, 0, "Ariza No", "Arizaid")
        add_row(0, 2, "Cihaz ID", "Cihazid")
        add_row(1, 0, "Baslangic Tarihi", "BaslangicTarihi")
        add_row(1, 2, "Saat", "Saat")
        add_row(2, 0, "Bildiren", "Bildiren")
        add_row(2, 2, "Ariza Tipi", "ArizaTipi")
        add_row(3, 0, "Oncelik", "Oncelik")
        add_row(3, 2, "Durum", "Durum")
        add_row(4, 0, "Baslik", "Baslik")
        add_row(5, 0, "Ariza Aciklamasi", "ArizaAcikla", multiline=True)
        add_row(6, 0, "Rapor", "Rapor", multiline=True)

        root.addWidget(grp_detail, 0)

    def _load_data(self):
        if not self._db:
            self._model.set_rows([])
            self.lbl_count.setText("0 kayit")
            return

        try:
            repo = RepositoryRegistry(self._db).get("Cihaz_Ariza")
            rows = repo.get_all()
            if self._cihaz_id:
                rows = [r for r in rows if str(r.get("Cihazid", "")) == str(self._cihaz_id)]
            rows.sort(key=lambda r: (r.get("BaslangicTarihi") or ""), reverse=True)

            self._rows = rows
            self._model.set_rows(rows)
            self.lbl_count.setText(f"{len(rows)} kayit")

            if rows:
                self.table.selectRow(0)
                self._populate_details(rows[0])
            else:
                self._clear_details()

        except Exception as e:
            logger.error(f"Ariza kayitlari yuklenemedi: {e}")
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
            if key == "BaslangicTarihi":
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
