"""
İzin Takip - Tablo Model
========================

IzinTableModel: Durum renklendirmesi, sıralama, filtreleme desteği
"""

from datetime import datetime
from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex, QDate
from PySide6.QtGui import QColor, QBrush, QFont
from core.log_manager import get_logger
from ui.styles import DarkTheme

logger = get_logger(__name__)


class IzinTableModel(QAbstractTableModel):
    """
    İzin Giris tablosu için model.

    Sütunlar:
    0. AdSoyad (kişi adı)
    1. IzinTipi (Yıllık, Şua, vb.)
    2. BaslamaTarihi (dd.MM.yyyy)
    3. Gun (gün sayısı)
    4. BitisTarihi (dd.MM.yyyy)
    5. Durum (Onaylandı, Beklemede, İptal)
    """

    COLUMNS = [
        "AdSoyad",
        "İzin Tipi",
        "Başlama",
        "Gün",
        "Bitiş",
        "Durum"
    ]

    # Durum renkleri
    DURUM_COLORS = {
        "Onaylandı": (QColor("#4CAF50"), QColor(255, 255, 255)),  # Yeşil
        "Beklemede": (QColor("#FFC107"), QColor(0, 0, 0)),  # Sarı
        "İptal": (QColor("#F44336"), QColor(255, 255, 255)),  # Kırmızı
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self._data = []

    def rowCount(self, parent=QModelIndex()) -> int:
        return len(self._data)

    def columnCount(self, parent=QModelIndex()) -> int:
        return len(self.COLUMNS)

    def headerData(self, section: int, orientation: Qt.Orientation, role: int):
        """Başlık satırını döndür."""
        if role != Qt.DisplayRole:
            return None
        if orientation == Qt.Horizontal:
            return self.COLUMNS[section]
        return None

    def data(self, index: QModelIndex, role: int):
        """Hücre verisi döndür."""
        if not index.isValid():
            return None

        row = index.row()
        col = index.column()

        if row < 0 or row >= len(self._data):
            return None

        record = self._data[row]

        # ── DISPLAY ROLE ──
        if role == Qt.DisplayRole:
            if col == 0:
                return str(record.get("AdSoyad", ""))
            elif col == 1:
                return str(record.get("IzinTipi", ""))
            elif col == 2:
                bas = record.get("BaslamaTarihi", "")
                return self._format_date(bas)
            elif col == 3:
                return str(record.get("Gun", ""))
            elif col == 4:
                bit = record.get("BitisTarihi", "")
                return self._format_date(bit)
            elif col == 5:
                return str(record.get("Durum", ""))

        # ── BACKGROUND COLOR (Durum'a göre) ──
        elif role == Qt.BackgroundRole:
            if col == 5:  # Son sütun (Durum)
                durum = str(record.get("Durum", "")).strip()
                if durum in self.DURUM_COLORS:
                    return self.DURUM_COLORS[durum][0]  # QColor
                return QColor(DarkTheme.BG_TERTIARY)

        # ── TEXT COLOR ──
        elif role == Qt.ForegroundRole:
            if col == 5:  # Durum sütunu
                durum = str(record.get("Durum", "")).strip()
                if durum in self.DURUM_COLORS:
                    return self.DURUM_COLORS[durum][1]  # Yazı rengi
                return QColor(DarkTheme.TEXT_PRIMARY)

        # ── FONT ──
        elif role == Qt.FontRole:
            if col == 5:  # Durum sütunu bold
                font = QFont()
                font.setBold(True)
                return font

        # ── ALIGNMENT ──
        elif role == Qt.TextAlignmentRole:
            if col in (3,):  # Gün sütunu sağa hizalı
                return Qt.AlignRight | Qt.AlignVCenter
            if col == 5:  # Durum sütunu ortalı
                return Qt.AlignCenter | Qt.AlignVCenter
            return Qt.AlignLeft | Qt.AlignVCenter

        return None

    def set_data(self, records: list) -> None:
        """
        Tablo verisi ayarla.

        Args:
            records: İzin_Giris tablosundan gelen kayıtlar listesi
        """
        self.beginResetModel()
        self._data = records or []
        self.endResetModel()
        logger.debug(f"İzin tablosu güncellendi: {len(self._data)} kayıt")

    def get_row(self, row: int) -> dict:
        """Belirtilen satırın verisini döndür."""
        if 0 <= row < len(self._data):
            return self._data[row]
        return {}

    def get_all_data(self) -> list:
        """Tüm verileri döndür."""
        return self._data.copy()

    def get_row_by_id(self, izin_id: str) -> dict:
        """İzin ID'sine göre satırı bul."""
        for record in self._data:
            if str(record.get("Izinid", "")).strip() == str(izin_id).strip():
                return record
        return {}

    @staticmethod
    def _format_date(date_str: str) -> str:
        """Tarih string'ini dd.MM.yyyy formatına çevir."""
        if not date_str:
            return "—"

        date_str = str(date_str).strip()

        # Zaten dd.MM.yyyy formatında mı?
        if len(date_str) == 10 and date_str[2] == "." and date_str[5] == ".":
            return date_str

        # ISO formatından çevir
        if len(date_str) == 10 and date_str[4] == "-":
            try:
                dt = datetime.strptime(date_str, "%Y-%m-%d")
                return dt.strftime("%d.%m.%Y")
            except ValueError:
                return date_str

        return date_str

    def sort_by_durum(self, reverse: bool = False) -> None:
        """Durum'a göre sırala (Onaylandı > Beklemede > İptal)."""
        durum_order = {"Onaylandı": 0, "Beklemede": 1, "İptal": 2}

        self.beginResetModel()
        self._data.sort(
            key=lambda r: durum_order.get(str(r.get("Durum", "")).strip(), 999),
            reverse=reverse
        )
        self.endResetModel()

    def sort_by_tarih(self, reverse: bool = False) -> None:
        """Başlama tarihine göre sırala."""
        def parse_date(d_str):
            try:
                if len(d_str) == 10 and d_str[4] == "-":
                    return datetime.strptime(d_str, "%Y-%m-%d").date()
                elif len(d_str) == 10 and d_str[2] == ".":
                    return datetime.strptime(d_str, "%d.%m.%Y").date()
            except (ValueError, TypeError):
                pass
            return None

        self.beginResetModel()
        self._data.sort(
            key=lambda r: parse_date(str(r.get("BaslamaTarihi", ""))) or datetime.min.date(),
            reverse=reverse
        )
        self.endResetModel()
