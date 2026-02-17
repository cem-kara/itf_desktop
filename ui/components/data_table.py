from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit,
    QTableView, QLabel, QHeaderView, QPushButton, QComboBox
)
from PySide6.QtCore import (
    Qt, QSortFilterProxyModel, QAbstractTableModel, QModelIndex
)
from ui.styles import DarkTheme


class DictTableModel(QAbstractTableModel):
    """
    list[dict] verisini QTableView'da gösterir.

    Kullanım:
        model = DictTableModel(
            data=[{"Ad": "Ali", "Soyad": "Yılmaz"}, ...],
            headers=["Ad", "Soyad"]
        )
    """

    def __init__(self, data=None, headers=None, display_headers=None, parent=None):
        super().__init__(parent)
        self._data = data or []
        self._headers = headers or []
        # Gösterim başlıkları (opsiyonel: "KimlikNo" → "Kimlik No")
        self._display_headers = display_headers or self._headers

    def rowCount(self, parent=QModelIndex()):
        return len(self._data)

    def columnCount(self, parent=QModelIndex()):
        return len(self._headers)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None

        if role == Qt.DisplayRole:
            col_key = self._headers[index.column()]
            return str(self._data[index.row()].get(col_key, ""))

        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            if section < len(self._display_headers):
                return self._display_headers[section]
        return None

    def get_row_data(self, row_index):
        """Satır verisini dict olarak döner."""
        if 0 <= row_index < len(self._data):
            return self._data[row_index]
        return None

    def set_data(self, data):
        """Veriyi tamamen değiştirir."""
        self.beginResetModel()
        self._data = data or []
        self.endResetModel()

    def all_data(self):
        return self._data


class DataTableWidget(QWidget):
    """
    Ortak tablo bileşeni.

    Özellikler:
    - Arama (tüm kolonlarda)
    - Sıralama (kolon başlığına tıkla)
    - Satır sayısı gösterimi
    - Kolon genişliği otomatik

    Kullanım:
        table = DataTableWidget()
        table.set_data(
            data=[...],
            headers=["KimlikNo", "AdSoyad"],
            display_headers=["Kimlik No", "Ad Soyad"]
        )
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # ── Üst toolbar: arama + bilgi ──
        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)

        self.search_input = QLineEdit()
        self.search_input.setObjectName("search_input")
        self.search_input.setPlaceholderText("Ara...")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.textChanged.connect(self._on_search)
        toolbar.addWidget(self.search_input, 1)

        self.count_label = QLabel("0 kayıt")
        self.count_label.setStyleSheet(f"color: {DarkTheme.TEXT_MUTED}; font-size: 12px; padding-right: 4px;")
        toolbar.addWidget(self.count_label)

        layout.addLayout(toolbar)

        # ── Tablo ──
        self.table_view = QTableView()
        self.table_view.setAlternatingRowColors(True)
        self.table_view.setSelectionBehavior(QTableView.SelectRows)
        self.table_view.setSelectionMode(QTableView.SingleSelection)
        self.table_view.setSortingEnabled(True)
        self.table_view.verticalHeader().setVisible(False)
        self.table_view.horizontalHeader().setStretchLastSection(True)
        self.table_view.horizontalHeader().setSectionResizeMode(
            QHeaderView.Interactive
        )
        self.table_view.setShowGrid(True)

        # ── Model + Proxy ──
        self._model = DictTableModel()
        self._proxy = QSortFilterProxyModel()
        self._proxy.setSourceModel(self._model)
        self._proxy.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self._proxy.setFilterKeyColumn(-1)  # Tüm kolonlarda ara
        self.table_view.setModel(self._proxy)

        layout.addWidget(self.table_view, 1)

    # ════════════════ PUBLIC API ════════════════

    def set_data(self, data, headers, display_headers=None):
        """
        Tabloyu doldurur.

        Args:
            data            : list[dict]
            headers         : list[str]  → dict key'leri
            display_headers : list[str]  → gösterim başlıkları (opsiyonel)
        """
        self._model = DictTableModel(data, headers, display_headers)
        self._proxy = QSortFilterProxyModel()
        self._proxy.setSourceModel(self._model)
        self._proxy.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self._proxy.setFilterKeyColumn(-1)
        self.table_view.setModel(self._proxy)

        self._update_count()
        self._auto_resize()

    def get_selected_data(self):
        """Seçili satırın dict verisini döner."""
        indexes = self.table_view.selectionModel().selectedRows()
        if indexes:
            source_idx = self._proxy.mapToSource(indexes[0])
            return self._model.get_row_data(source_idx.row())
        return None

    def refresh_data(self, data):
        """Veriyi günceller (headers aynı kalır)."""
        self._model.set_data(data)
        self._update_count()

    # ════════════════ PRIVATE ════════════════

    def _on_search(self, text):
        self._proxy.setFilterFixedString(text)
        self._update_count()

    def _update_count(self):
        visible = self._proxy.rowCount()
        total = self._model.rowCount()
        if visible == total:
            self.count_label.setText(f"{total} kayıt")
        else:
            self.count_label.setText(f"{visible} / {total} kayıt")

    def _auto_resize(self):
        header = self.table_view.horizontalHeader()
        for i in range(self._model.columnCount()):
            header.setSectionResizeMode(i, QHeaderView.ResizeToContents)
        # Son kolonu stretch yap
        if self._model.columnCount() > 0:
            header.setSectionResizeMode(
                self._model.columnCount() - 1,
                QHeaderView.Stretch
            )
