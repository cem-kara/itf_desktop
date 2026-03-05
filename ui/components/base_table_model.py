"""
BaseTableModel — Tüm QTableView modellerinin ortak tabanı.

Kullanım
--------
COLUMNS = [
    ("DbAlani",  "Başlık",   120),   # (db_key, header, genişlik_px)
    ("Tarih",    "Tarih",     90),
    ("Durum",    "Durum",     80),
]

class BenimModelim(BaseTableModel):
    DATE_KEYS    = frozenset({"Tarih", "BitisTarihi"})
    ALIGN_CENTER = frozenset({"Durum", "Tarih"})

    def _fg(self, key, row):
        if key == "Durum":
            return self.status_fg(row.get("Durum", ""))
        return None

Alt sınıflar sadece değişen şeyi override eder.
"""
from __future__ import annotations

from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex, QSize, QPersistentModelIndex
from PySide6.QtGui import QColor

from core.date_utils import to_ui_date


# ── Ortak durum renk paleti ──────────────────────────────────────

_STATUS_FG: dict[str, str] = {
    "Aktif":             "#4ade80",
    "Pasif":             "#f87171",
    "İzinli":            "#facc15",
    "Açık":              "#f87171",
    "İşlemde":           "#fb923c",
    "Beklemede":         "#facc15",
    "Planlandı":         "#facc15",
    "Tamamlandı":        "#4ade80",
    "Onaylandı":         "#4ade80",
    "Kapalı (Çözüldü)": "#4ade80",
    "İptal":             "#94a3b8",
    "Geçerli":           "#4ade80",
    "Gecerli":           "#4ade80",
    "Geçersiz":          "#f87171",
    "Gecersiz":          "#f87171",
    "Uygun":             "#4ade80",
    "Uygun Değil":       "#f87171",
    "Hurda":             "#f87171",
    "Tamirde":           "#facc15",
}

_STATUS_BG: dict[str, str] = {
    "Aktif":             "#4ade8022",
    "Pasif":             "#f8717122",
    "İzinli":            "#facc1522",
    "Açık":              "#f8717122",
    "Tamamlandı":        "#4ade8022",
    "Onaylandı":         "#4ade8022",
    "Kapalı (Çözüldü)": "#4ade8022",
    "Geçerli":           "#4ade8022",
    "Gecerli":           "#4ade8022",
    "Geçersiz":          "#f8717122",
    "Gecersiz":          "#f8717122",
}


class BaseTableModel(QAbstractTableModel):
    """
    Tüm tablolar bunu extend eder.

    columns = [("DbAlani", "Başlık", genişlik_px), ...]

    Alt sınıf override noktaları
    ----------------------------
    DATE_KEYS    : frozenset[str]  — to_ui_date() ile formatlanacak alanlar
    ALIGN_CENTER : frozenset[str]  — merkez hizalanacak sütunlar
    _display(key, row) → str
    _fg(key, row)      → QColor | None
    _bg(key, row)      → QColor | None
    """

    RAW_ROW_ROLE: int = Qt.ItemDataRole.UserRole + 1
    DATE_KEYS:    frozenset = frozenset()
    ALIGN_CENTER: frozenset = frozenset()

    def __init__(self, columns: list, data=None, parent=None):
        super().__init__(parent)
        self._columns: list = columns
        self._data:    list = data or []
        self._keys:    list = [c[0] for c in columns]

    # ── Qt zorunlu ───────────────────────────────────────────────

    def rowCount(self, parent: QModelIndex | QPersistentModelIndex | None = None) -> int:
        return len(self._data)

    def columnCount(self, parent: QModelIndex | QPersistentModelIndex | None = None) -> int:
        return len(self._columns)

    def data(self, index: QModelIndex | QPersistentModelIndex, role: int = 0):
        if not index.isValid():
            return None
        row = self._data[index.row()]
        key = self._keys[index.column()]

        if role == Qt.ItemDataRole.DisplayRole:
            return self._display(key, row)
        if role == Qt.ItemDataRole.ForegroundRole:
            return self._fg(key, row)
        if role == Qt.ItemDataRole.BackgroundRole:
            return self._bg(key, row)
        if role == Qt.ItemDataRole.TextAlignmentRole:
            return self._align(key)
        if role == Qt.ItemDataRole.UserRole:
            return row
        return None

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = 0):
        if orientation != Qt.Orientation.Horizontal:
            return None
        if role == Qt.ItemDataRole.DisplayRole:
            return self._columns[section][1]
        if role == Qt.ItemDataRole.SizeHintRole and len(self._columns[section]) >= 3:
            return QSize(self._columns[section][2], 28)
        return None

    # ── Sıralama ─────────────────────────────────────────────────

    def sort(self, column: int, order=Qt.SortOrder.AscendingOrder) -> None:
        if column < 0 or column >= len(self._keys):
            return
        key = self._keys[column]
        reverse = (order == Qt.SortOrder.DescendingOrder)
        self.layoutAboutToBeChanged.emit()
        self._data.sort(key=lambda r: str(r.get(key, "") or ""), reverse=reverse)
        self.layoutChanged.emit()

    # ── Override noktaları ───────────────────────────────────────

    def _display(self, key: str, row: dict) -> str:
        val = row.get(key, "")
        if key in self.DATE_KEYS:
            return to_ui_date(val, "")
        return str(val) if val is not None else ""

    def _fg(self, key: str, row: dict) -> QColor | None:
        return None

    def _bg(self, key: str, row: dict) -> QColor | None:
        return None

    def _align(self, key: str):
        if key in self.ALIGN_CENTER:
            return Qt.AlignmentFlag.AlignCenter
        return Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft

    # ── Durum renk yardımcıları ──────────────────────────────────

    @staticmethod
    def status_fg(durum: str):
        c = _STATUS_FG.get(str(durum).strip())
        return QColor(c) if c else None

    @staticmethod
    def status_bg(durum: str):
        c = _STATUS_BG.get(str(durum).strip())
        return QColor(c) if c else None

    # ── Veri metodları ───────────────────────────────────────────

    def set_data(self, data: list) -> None:
        self.beginResetModel()
        self._data = data or []
        self.endResetModel()

    def set_rows(self, rows: list) -> None:
        """set_data() alias — geriye uyumluluk."""
        self.set_data(rows)

    def clear(self) -> None:
        self.set_data([])

    def append_rows(self, rows: list) -> None:
        """Sayfalama için veri ekle — resetlemeden."""
        if not rows:
            return
        first = len(self._data)
        last  = first + len(rows) - 1
        self.beginInsertRows(QModelIndex(), first, last)
        self._data.extend(rows)
        self.endInsertRows()

    def get_row(self, idx: int):
        return self._data[idx] if 0 <= idx < len(self._data) else None

    def all_data(self) -> list:
        return list(self._data)

    def __len__(self) -> int:
        return len(self._data)

    # ── QTableView entegrasyonu ──────────────────────────────────

    def setup_columns(self, view, stretch_keys: list | None = None) -> None:
        """
        columns içindeki genişlik bilgisini QTableView'a uygular.

        Args:
            view:         Hedef QTableView
            stretch_keys: Stretch modunda olacak kolon key listesi.
                          Belirtilmezse son kolon stretch olur.
        """
        from PySide6.QtWidgets import QHeaderView
        hdr = view.horizontalHeader()
        for i, col in enumerate(self._columns):
            w = col[2] if len(col) > 2 else None
            if w is not None:
                hdr.setSectionResizeMode(i, QHeaderView.ResizeMode.Fixed)
                view.setColumnWidth(i, w)
            else:
                hdr.setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)

        if stretch_keys:
            for key in stretch_keys:
                if key in self._keys:
                    idx = self._keys.index(key)
                    hdr.setSectionResizeMode(idx, QHeaderView.ResizeMode.Stretch)
        else:
            last = len(self._columns) - 1
            if last >= 0:
                hdr.setSectionResizeMode(last, QHeaderView.ResizeMode.Stretch)

    # ── Tarih formatlama yardımcısı ──────────────────────────────

    @staticmethod
    def _fmt_date(val, fallback: str = "") -> str:
        """Çeşitli tarih formatlarını 'GG.AA.YYYY' biçimine çevirir."""
        if not val:
            return fallback
        from datetime import datetime, date as date_type
        try:
            from PySide6.QtCore import QDate
            if isinstance(val, datetime):
                return val.strftime("%d.%m.%Y")
            if isinstance(val, date_type):
                return val.strftime("%d.%m.%Y")
            if isinstance(val, QDate):
                return val.toString("dd.MM.yyyy")
            s = str(val).strip().split(" ")[0]
            if "-" in s:
                return datetime.strptime(s, "%Y-%m-%d").strftime("%d.%m.%Y")
            if "." in s and len(s) == 10:
                return s
        except (ValueError, TypeError):
            pass
        return fallback or str(val)
