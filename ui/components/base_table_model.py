# ui/components/base_table_model.py
from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex
from PySide6.QtGui import QColor


class BaseTableModel(QAbstractTableModel):
    """
    Tüm tablolar bunu extend eder.
    columns = [("DbAlani", "Başlık", genişlik), ...]
    """

    def __init__(self, columns: list, data=None, parent=None):
        super().__init__(parent)
        self._columns = columns
        self._data = data or []
        self._keys = [c[0] for c in columns]

    def rowCount(self, parent=QModelIndex()):
        return len(self._data)

    def columnCount(self, parent=QModelIndex()):
        return len(self._columns)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        row = self._data[index.row()]
        key = self._keys[index.column()]
        if role == Qt.DisplayRole:
            return self._display(key, row)
        if role == Qt.ForegroundRole:
            return self._fg(key, row)
        if role == Qt.BackgroundRole:
            return self._bg(key, row)
        if role == Qt.TextAlignmentRole:
            return self._align(key)
        if role == Qt.UserRole:
            return row  # tüm satır dict'i
        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self._columns[section][1]
        return None

    # ── Alt sınıflar override eder ──────────────────────
    def _display(self, key, row):
        return str(row.get(key, "") or "")

    def _fg(self, key, row):
        return None

    def _bg(self, key, row):
        return None

    def _align(self, key):
        return Qt.AlignVCenter | Qt.AlignLeft

    # ── Ortak metodlar ──────────────────────────────────
    def set_data(self, data):
        self.beginResetModel()
        self._data = data or []
        self.endResetModel()

    def get_row(self, idx):
        return self._data[idx] if 0 <= idx < len(self._data) else None

    def all_data(self):
        return list(self._data)
