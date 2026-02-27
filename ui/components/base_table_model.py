# -*- coding: utf-8 -*-
"""BaseTableModel - Tüm table model'ler için temel sınıf."""

from PySide6.QtCore import Qt, QModelIndex, QAbstractTableModel, QSortFilterProxyModel


class BaseTableModel(QAbstractTableModel):
    """
    Tüm custom table model'ler için temel sınıf.
    
    Subclass'lar şu metodları override etmeli:
    - get_row_display(row, col, key, raw_row) - hücre metnini döndür
    - get_row_color(row, col, key, raw_row) - hücre rengini döndür (opsiyonel)
    """
    
    RAW_ROW_ROLE = Qt.UserRole + 1

    def __init__(self, columns: list, data=None, parent=None):
        """
        Args:
            columns: [("key1", "Header 1", width1), ("key2", "Header 2", width2), ...]
            data: [dict, dict, ...] (default ise boş liste)
        """
        super().__init__(parent)
        self.columns = columns  # [("_key", "Display", width), ...]
        self._keys = [c[0] for c in columns]
        self._headers = [c[1] for c in columns]
        self._widths = [c[2] for c in columns]
        self._data: list[dict] = data or []
        self._raw_data = None  # Filtered olmayan orijinal data

    def rowCount(self, parent=QModelIndex()):
        return len(self._data)

    def columnCount(self, parent=QModelIndex()):
        return len(self.columns)

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self._headers[section]
        return None

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        
        row = self._data[index.row()]
        key = self._keys[index.column()]

        if role == self.RAW_ROW_ROLE:
            return row

        if role == Qt.DisplayRole:
            return self.get_row_display(index.row(), index.column(), key, row)

        return None

    # ─────────────────────────────────────────────────────────
    # Subclass'lar tarafından override edilmesi gereken metodlar
    # ─────────────────────────────────────────────────────────

    def get_row_display(self, row: int, col: int, key: str, raw_row: dict) -> str:
        """
        Hücre display metnini döndür.
        
        Default: raw_row[key] basit şekilde döndür.
        Override: Custom formatting (tarih, sayı, composite fields)
        """
        return str(raw_row.get(key, ""))

    def get_row_color(self, row: int, col: int, key: str, raw_row: dict) -> str:
        """
        Hücre arkaplan rengini döndür (opsiyonel).
        
        Returns: "#RRGGBB" veya None
        """
        return None

    # ─────────────────────────────────────────────────────────
    # Data manipulation metodları
    # ─────────────────────────────────────────────────────────

    def set_data(self, data: list):
        """Model verisi güncelle."""
        self.beginResetModel()
        self._data = data or []
        self._raw_data = None
        self.endResetModel()

    def get_row(self, row: int) -> dict:
        """Satırı dict olarak döndür."""
        if 0 <= row < len(self._data):
            return self._data[row]
        return {}

    def add_row(self, row_dict: dict):
        """Sona yeni satır ekle."""
        self.beginInsertRows(QModelIndex(), len(self._data), len(self._data))
        self._data.append(row_dict)
        self.endInsertRows()

    def remove_row(self, row: int):
        """Satırı sil."""
        if 0 <= row < len(self._data):
            self.beginRemoveRows(QModelIndex(), row, row)
            self._data.pop(row)
            self.endRemoveRows()

    def update_row(self, row: int, row_dict: dict):
        """Satırı güncelle."""
        if 0 <= row < len(self._data):
            self._data[row] = row_dict
            idx_start = self.index(row, 0)
            idx_end = self.index(row, len(self.columns) - 1)
            self.dataChanged.emit(idx_start, idx_end)

    def filter(self, predicate) -> list:
        """
        Veri üzerinde filter uygula.
        
        Args:
            predicate: lambda row: bool
            
        Returns:
            Filtered data list
        """
        self._raw_data = self._data.copy()
        self.beginResetModel()
        self._data = [row for row in self._raw_data if predicate(row)]
        self.endResetModel()
        return self._data

    def reset_filter(self):
        """Filter'i sıfırla ve tüm veriyi geri getir."""
        if self._raw_data is not None:
            self.beginResetModel()
            self._data = self._raw_data
            self._raw_data = None
            self.endResetModel()

    def sort(self, column: int, order=Qt.AscendingOrder):
        """Sütuna göre sırala (subclass override edebilir)."""
        pass

    def get_column_width(self, col: int) -> int:
        """Sütun genişliğini döndür."""
        return self._widths[col] if col < len(self._widths) else 100

    def get_all_data(self) -> list:
        """Tüm veriyi döndür."""
        return self._data
