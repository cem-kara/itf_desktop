# -*- coding: utf-8 -*-
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QGridLayout,
    QGroupBox, QTableView, QHeaderView
)
from PySide6.QtCore import Qt, QDate, QAbstractTableModel, QModelIndex

from core.logger import logger
from ui.styles import Colors, DarkTheme
from ui.styles.components import STYLES as S
from datetime import datetime, date

SAGLIK_COLUMNS = [
    ("MuayeneTarihi", "Muayene Tarihi", 120),
    ("MuayeneTuru", "Muayene Türü", 150),
    ("Sonuc", "Sonuç", 150),
    ("Aciklama", "Açıklama", 250),
    ("SonrakiKontrolTarihi", "Sonraki Kontrol", 120),
]

class SaglikTableModel(QAbstractTableModel):
    def __init__(self, data=None, parent=None):
        super().__init__(parent)
        self._data = data or []
        self._keys = [c[0] for c in SAGLIK_COLUMNS]
        self._headers = [c[1] for c in SAGLIK_COLUMNS]

    def rowCount(self, parent=QModelIndex()):
        return len(self._data)

    def columnCount(self, parent=QModelIndex()):
        return len(SAGLIK_COLUMNS)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        row = self._data[index.row()]
        col_key = self._keys[index.column()]
        if role == Qt.DisplayRole:
            value = row.get(col_key, "")
            if "Tarihi" in col_key:
                return self._fmt_date(value)
            return str(value)
        if role == Qt.TextAlignmentRole:
            if "Tarihi" in col_key:
                return Qt.AlignCenter
            return Qt.AlignVCenter | Qt.AlignLeft
        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self._headers[section]
        return None

    def set_data(self, data):
        self.beginResetModel()
        self._data = data or []
        self.endResetModel()

    def _fmt_date(self, val):
        if not val: return "-"
        try:
            dt = None
            if isinstance(val, (datetime, date)):
                dt = val
            elif isinstance(val, QDate):
                dt = val.toPython()
            else:
                val_str = str(val).strip()
                if ' ' in val_str:
                    val_str = val_str.split(' ')[0]
                if '-' in val_str:
                    dt = datetime.strptime(val_str, "%Y-%m-%d")
            if dt:
                return dt.strftime("%d.%m.%Y")
        except Exception as e:
            logger.warning(f"Tarih formatlama hatası: {val} - {e}")
        return str(val)

class PersonelSaglikPanel(QWidget):
    def __init__(self, db, personel_id, parent=None):
        super().__init__(parent)
        self.db = db
        self.personel_id = personel_id
        self.saglik_records = []
        self._setup_ui()
        self.load_data()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)

        summary_group = QGroupBox("Sağlık Durum Özeti")
        summary_group.setStyleSheet(S["group"])
        summary_layout = QGridLayout(summary_group)
        summary_layout.setHorizontalSpacing(20)
        summary_layout.setVerticalSpacing(8)

        self.lbl_son_muayene = self._add_stat(summary_layout, 0, 0, "Son Muayene Tarihi")
        self.lbl_sonraki_muayene = self._add_stat(summary_layout, 0, 1, "Sonraki Muayene Tarihi")
        self.lbl_durum = self._add_stat(summary_layout, 0, 2, "Genel Sağlık Durumu")
        summary_layout.setColumnStretch(3, 1)
        main_layout.addWidget(summary_group)

        history_group = QGroupBox("Geçmiş Muayene Kayıtları")
        history_group.setStyleSheet(S["group"])
        history_layout = QVBoxLayout(history_group)

        self._table_model = SaglikTableModel()
        self._table_view = QTableView()
        self._table_view.setModel(self._table_model)
        self._table_view.setStyleSheet(S["table"])
        self._table_view.verticalHeader().setVisible(False)
        self._table_view.setEditTriggers(QTableView.NoEditTriggers)
        self._table_view.setSelectionBehavior(QTableView.SelectRows)
        self._table_view.setSelectionMode(QTableView.SingleSelection)
        self._table_view.setAlternatingRowColors(True)

        header = self._table_view.horizontalHeader()
        for i, col_info in enumerate(SAGLIK_COLUMNS):
            width = col_info[2]
            header.setSectionResizeMode(i, QHeaderView.Interactive)
            self._table_view.setColumnWidth(i, width)
        header.setSectionResizeMode(len(SAGLIK_COLUMNS) - 1, QHeaderView.Stretch)

        history_layout.addWidget(self._table_view)
        main_layout.addWidget(history_group, 1)

    def _add_stat(self, grid, row, col, text):
        container = QWidget()
        l = QVBoxLayout(container)
        l.setContentsMargins(0, 0, 0, 0)
        l.setSpacing(2)
        
        lbl_t = QLabel(text)
        lbl_t.setStyleSheet(f"color: {DarkTheme.TEXT_MUTED}; font-size: 11px;")
        l.addWidget(lbl_t)
        
        val = QLabel("—")
        val.setStyleSheet(f"color: {DarkTheme.TEXT_PRIMARY}; font-size: 14px; font-weight: 500;")
        l.addWidget(val)
        
        grid.addWidget(container, row, col)
        return val

    def load_data(self):
        if not self.db or not self.personel_id: return
        try:
            from database.repository_registry import RepositoryRegistry
            registry = RepositoryRegistry(self.db)
            repo = registry.get("Personel_Saglik_Takip")
            all_records = repo.get_all()
            
            self.saglik_records = [r for r in all_records if str(r.get("Personelid", "")).strip() == self.personel_id]
            self.saglik_records.sort(key=lambda x: x.get("MuayeneTarihi", ""), reverse=True)
            
            self._update_ui()
        except Exception as e:
            logger.error(f"Personel sağlık verisi yükleme hatası ({self.personel_id}): {e}")
            self._clear_ui()

    def _update_ui(self):
        self._table_model.set_data(self.saglik_records)
        if self.saglik_records:
            latest_record = self.saglik_records[0]
            self.lbl_son_muayene.setText(self._table_model._fmt_date(latest_record.get("MuayeneTarihi")))
            self.lbl_sonraki_muayene.setText(self._table_model._fmt_date(latest_record.get("SonrakiKontrolTarihi")))
            self.lbl_durum.setText(latest_record.get("Sonuc", "Belirsiz"))
            
            next_check_date_str = latest_record.get("SonrakiKontrolTarihi")
            if next_check_date_str:
                try:
                    next_check_date = datetime.strptime(str(next_check_date_str).split(' ')[0], '%Y-%m-%d').date()
                    if next_check_date < date.today():
                        self.lbl_sonraki_muayene.setStyleSheet(f"color: {Colors.RED_500}; font-size: 14px; font-weight: bold;")
                    else:
                        self.lbl_sonraki_muayene.setStyleSheet(f"color: {DarkTheme.TEXT_PRIMARY}; font-size: 14px; font-weight: 500;")
                except ValueError: pass
        else:
            self._clear_ui()

    def _clear_ui(self):
        self.lbl_son_muayene.setText("—")
        self.lbl_sonraki_muayene.setText("—")
        self.lbl_durum.setText("—")
        self._table_model.set_data([])

    def set_embedded_mode(self, mode):
        pass