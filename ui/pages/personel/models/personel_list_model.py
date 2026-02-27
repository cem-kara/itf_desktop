# -*- coding: utf-8 -*-
"""
Personel Listesi - Table Model
===============================
Personel tablosu veri modeli, lazy-loading pagination ile.
"""
from PySide6.QtCore import (
    Qt, QAbstractTableModel, QModelIndex, QSize
)
from PySide6.QtGui import QPixmap

from core.logger import logger
from ui.styles import DarkTheme

C = DarkTheme


# ─────────────────────────────────────────────────────────────────────────────
# Sütun Tanımları
# ─────────────────────────────────────────────────────────────────────────────

COLUMNS = [
    ("_avatar",     "",               60),      # Avatar resim
    ("AdSoyad",     "Ad Soyad",      100),     # Ad + Soyad
    ("_tc_sicil",   "TC / Sicil",    100),     # TC no / Sicil
    ("_birim",      "Birim · Ünvan", 100),     # Birim + Ünvan
    ("CepTelefonu", "Telefon",       120),     # Cep telefonu
    ("_izin_bar",   "İzin Bakiye",   160),     # Progress bar
    ("Durum",       "Durum",          100),     # Aktif/Pasif
    ("_actions",    "",               190),     # Detay + İzin butonları
]

COL_IDX = {c[0]: i for i, c in enumerate(COLUMNS)}


# ─────────────────────────────────────────────────────────────────────────────
# Personel Tablo Modeli
# ─────────────────────────────────────────────────────────────────────────────

class PersonelTableModel(QAbstractTableModel):
    """
    Personel tablosu için veri modeli.
    
    Custom Roles:
        - RAW_ROW_ROLE: Orijinal dict
        - IZIN_PCT_ROLE: İzin yüzde (0.0-1.0)
        - IZIN_TXT_ROLE: "13 / 20" şeklinde metin
        - AVATAR_ROLE: QPixmap avatar resmi
    
    Attributes:
        _data: Personel kayıtları
        _izin_map: İzin bakiye dict
        _avatars: Avatar cache (TC → QPixmap)
    """

    # Custom roles
    RAW_ROW_ROLE = Qt.UserRole + 1
    IZIN_PCT_ROLE = Qt.UserRole + 2
    IZIN_TXT_ROLE = Qt.UserRole + 3
    AVATAR_ROLE = Qt.UserRole + 4

    def __init__(self, parent=None):
        super().__init__(parent)
        self._data: list[dict] = []
        self._izin_map: dict[str, dict] = {}
        self._avatars: dict[str, QPixmap] = {}
        self._keys = [c[0] for c in COLUMNS]
        self._headers = [c[1] for c in COLUMNS]

    # ────────────────────────────────────────────────────────────────────────
    # Model Interface
    # ────────────────────────────────────────────────────────────────────────

    def rowCount(self, parent=QModelIndex()) -> int:
        """Satır sayısı."""
        return len(self._data)

    def columnCount(self, parent=QModelIndex()) -> int:
        """Sütun sayısı."""
        return len(COLUMNS)

    def headerData(self, section: int, orientation, role=Qt.DisplayRole):
        """Header veri."""
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self._headers[section] if section < len(self._headers) else ""
        if role == Qt.SizeHintRole and orientation == Qt.Horizontal:
            return QSize(COLUMNS[section][2], 40)
        return None

    def data(self, index: QModelIndex, role=Qt.DisplayRole):
        """Cell veri."""
        if not index.isValid():
            return None

        row, col = index.row(), index.column()
        if row >= len(self._data):
            return None

        row_data = self._data[row]
        key = self._keys[col]

        # ── Display Role ────────────────────────────────────────────────────
        if role == Qt.DisplayRole:
            if key == "_avatar":
                return ""  # Avatar pixmap ayrı renderlanacak
            elif key == "_tc_sicil":
                tc = row_data.get("TCKN", "")
                sicil = row_data.get("CalisanNo", "")
                return f"{tc[:5]}/...  ({sicil})" if tc or sicil else ""
            elif key == "_birim":
                birim = row_data.get("Birim", "")
                unvan = row_data.get("Unvan", "")
                return f"{birim} · {unvan}" if birim and unvan else birim or unvan or ""
            elif key == "_izin_bar":
                return self.data(index, self.IZIN_TXT_ROLE)
            elif key == "_actions":
                return ""  # Button'lar ayrı renderlanacak
            else:
                return str(row_data.get(key, ""))

        # ── Custom Roles ────────────────────────────────────────────────────
        if role == self.RAW_ROW_ROLE:
            return row_data

        if role == self.IZIN_PCT_ROLE:
            tc = row_data.get("TCKN", "")
            if tc in self._izin_map:
                bakiye = self._izin_map[tc].get("bakiye", 0)
                toplam = self._izin_map[tc].get("toplam", 20)
                if toplam > 0:
                    return bakiye / toplam
            return -1  # Veri yok

        if role == self.IZIN_TXT_ROLE:
            tc = row_data.get("TCKN", "")
            if tc in self._izin_map:
                bakiye = self._izin_map[tc].get("bakiye", 0)
                toplam = self._izin_map[tc].get("toplam", 20)
                return f"{int(bakiye)} / {int(toplam)}"
            return "— / —"

        if role == self.AVATAR_ROLE:
            tc = row_data.get("TCKN", "")
            return self._avatars.get(tc)

        # ── Foreground/Background ───────────────────────────────────────────
        if role == Qt.ForegroundRole:
            status = row_data.get("Durum", "")
            if status == "Pasif":
                return Qt.gray
            return None

        return None

    # ────────────────────────────────────────────────────────────────────────
    # Data Methods
    # ────────────────────────────────────────────────────────────────────────

    def set_data(self, data: list[dict]):
        """Tablo verisi set et."""
        self.beginResetModel()
        self._data = data or []
        self.endResetModel()
        logger.debug(f"Model verisi güncellendi: {len(self._data)} satır")

    def set_izin_map(self, izin_map: dict[str, dict]):
        """İzin bakiye haritası set et."""
        self._izin_map = izin_map or {}
        # Tüm hücreleri yenile (izin sütunları)
        if self._data:
            top_left = self.index(0, 0)
            bottom_right = self.index(len(self._data) - 1, len(COLUMNS) - 1)
            self.dataChanged.emit(top_left, bottom_right)
        logger.debug(f"İzin haritası güncellendi: {len(self._izin_map)} TC")

    def set_avatar(self, tc: str, pixmap: QPixmap):
        """Belli bir TC için avatar set et."""
        if tc in self._avatars:
            return  # Zaten var
        
        self._avatars[tc] = pixmap
        
        # Model'de bu TC'nin satırını bul ve yenile
        for row, row_data in enumerate(self._data):
            if row_data.get("TCKN") == tc:
                idx = self.index(row, COL_IDX.get("_avatar", 0))
                self.dataChanged.emit(idx, idx)
                break

    def get_row_data(self, row: int) -> dict:
        """Satır verisi al."""
        if 0 <= row < len(self._data):
            return self._data[row]
        return {}

    # ────────────────────────────────────────────────────────────────────────
    # Filtering / Searching
    # ────────────────────────────────────────────────────────────────────────

    def filter_by_durum(self, durum: str) -> list[int]:
        """
        Duruma göre filtrelenmiş satır indisleri döndür.
        
        Args:
            durum: "Aktif", "Pasif", veya "Tüm"
        
        Returns:
            Uyuşan satır indisleri
        """
        if durum == "Tüm":
            return list(range(len(self._data)))
        
        return [
            i for i, row in enumerate(self._data)
            if row.get("Durum") == durum
        ]

    def search(self, search_text: str) -> list[int]:
        """
        Metin araması (Ad, TC, Telefon).
        
        Args:
            search_text: Aranacak metin
        
        Returns:
            Uyuşan satır indisleri
        """
        if not search_text.strip():
            return list(range(len(self._data)))
        
        search_text_lower = search_text.lower()
        matching_rows = []
        
        for i, row in enumerate(self._data):
            ad_soyad = str(row.get("AdSoyad", "")).lower()
            tc = str(row.get("TCKN", "")).lower()
            telefon = str(row.get("CepTelefonu", "")).lower()
            sicil = str(row.get("CalisanNo", "")).lower()
            
            if (search_text_lower in ad_soyad or
                search_text_lower in tc or
                search_text_lower in telefon or
                search_text_lower in sicil):
                matching_rows.append(i)
        
        return matching_rows

    def filter_by_combo(self, key: str, value: str) -> list[int]:
        """
        Combo filtresi (Birim, Ünvan, vb).
        
        Args:
            key: Field anahtarı
            value: Filter değeri ("Tüm" = hiçbir şey filtreleme)
        
        Returns:
            Uyuşan satır indisleri
        """
        if value == "Tüm":
            return list(range(len(self._data)))
        
        return [
            i for i, row in enumerate(self._data)
            if row.get(key) == value
        ]
