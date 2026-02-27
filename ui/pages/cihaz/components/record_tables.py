# -*- coding: utf-8 -*-
"""
Cihaz Modülü - Shared Record Table Components
==============================================
Bakım, Kalibrasyon, vb. kayıt tabloları için temel model ve delegate.
"""
from typing import List, Dict, Any, Optional, Callable
from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex, QRect, QSize
from PySide6.QtWidgets import QStyledItemDelegate
from PySide6.QtGui import QColor, QPainter, QFont

from core.logger import logger


# ═════════════════════════════════════════════════════════════════════
#  RECORD TABLE MODEL
# ═════════════════════════════════════════════════════════════════════

class RecordTableModel(QAbstractTableModel):
    """
    Kayıt tablosu modelinin base sınıfı (Bakım, Kalibrasyon, vb.)
    
    Subclass'lar şunları override etmeli:
    - COLUMNS: tuple listesi ((key, header, width), ...)
    - COLOR_MAPPING (opsiyonel): durum/tip → renk eşlemesi
    """
    
    COLUMNS = []  # Subclass'lar tanımlamalı
    COLOR_MAPPING = {}  # {column_key: {value: color_hex}}
    BG_COLOR_MAPPING = {}  # {column_key: {value: bg_color_hex}}
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._rows = []
        self._sort_column = None
        self._sort_order = Qt.AscendingOrder
        
        # COLUMNS'dan türet
        if self.COLUMNS:
            self._headers = [c[1] for c in self.COLUMNS]
            self._keys = [c[0] for c in self.COLUMNS]
            self._widths = [c[2] if len(c) > 2 else 100 for c in self.COLUMNS]
        else:
            self._headers = []
            self._keys = []
            self._widths = []
    
    # ──────────────────────────────────────────────────────
    # Core Model Methods (QAbstractTableModel)
    # ──────────────────────────────────────────────────────
    
    def rowCount(self, parent=QModelIndex()) -> int:
        """Satır sayısı"""
        return len(self._rows)
    
    def columnCount(self, parent=QModelIndex()) -> int:
        """Kolon sayısı"""
        return len(self._keys)
    
    def headerData(self, section: int, orientation, role=Qt.DisplayRole):
        """Üstbilgi"""
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            if 0 <= section < len(self._headers):
                return self._headers[section]
        
        if role == Qt.TextAlignmentRole and orientation == Qt.Horizontal:
            return Qt.AlignCenter
        
        return None
    
    def data(self, index: QModelIndex, role=Qt.DisplayRole):
        """Hücre verisi"""
        if not index.isValid():
            return None
        
        row = self._rows[index.row()]
        key = self._keys[index.column()]
        val = row.get(key, "")
        
        # ── Display Role ──────────────────────────────────
        if role == Qt.DisplayRole:
            return self._format_display(val, key)
        
        # ── Alignment Role ────────────────────────────────
        if role == Qt.TextAlignmentRole:
            return self._get_alignment(key)
        
        # ── Foreground Color (Text Color) ─────────────────
        if role == Qt.ForegroundRole:
            return self._get_foreground_color(row, key)
        
        # ── Background Color ──────────────────────────────
        if role == Qt.BackgroundRole:
            return self._get_background_color(row, key)
        
        return None
    
    # ──────────────────────────────────────────────────────
    # Formatting & Styling Methods (Override in Subclass)
    # ──────────────────────────────────────────────────────
    
    def _format_display(self, val: Any, key: str) -> str:
        """
        Hücre değerini format et.
        Tarih, sayı, vb. özel formatlar için override et.
        """
        if not val:
            return ""
        
        # Tarih formatlaması (ISO → UI format)
        if key.endswith("Tarihi") or key.endswith("Tarihi".lower()):
            from core.date_utils import to_ui_date
            return to_ui_date(str(val), "")
        
        return str(val)
    
    def _get_alignment(self, key: str) -> int:
        """Hücre hizalama"""
        # Tarih ve sayılar ortalanmış
        if key.endswith("Tarihi") or key.endswith("Tarihi".lower()):
            return Qt.AlignCenter
        if key in ("Durum", "Tip", "Oncelik"):
            return Qt.AlignCenter
        return Qt.AlignVCenter | Qt.AlignLeft
    
    def _get_foreground_color(self, row: Dict[str, Any], key: str) -> Optional[QColor]:
        """Metin rengi (COLOR_MAPPING'den)"""
        if key not in self.COLOR_MAPPING:
            return None
        
        val = row.get(key, "")
        if not val:
            return None
        
        color_hex = self.COLOR_MAPPING[key].get(val)
        if color_hex:
            return QColor(color_hex)
        
        return None
    
    def _get_background_color(self, row: Dict[str, Any], key: str) -> Optional[QColor]:
        """Arka plan rengi (BG_COLOR_MAPPING'den)"""
        if key not in self.BG_COLOR_MAPPING:
            return None
        
        val = row.get(key, "")
        if not val:
            return None
        
        bg_hex = self.BG_COLOR_MAPPING[key].get(val)
        if bg_hex:
            return QColor(bg_hex)
        
        return None
    
    # ──────────────────────────────────────────────────────
    # Data Manipulation
    # ──────────────────────────────────────────────────────
    
    def set_rows(self, rows: List[Dict[str, Any]]):
        """Tüm verileri ayarla"""
        self.beginResetModel()
        self._rows = rows or []
        self.endResetModel()
    
    def append_row(self, row: Dict[str, Any]):
        """Satır ekle"""
        self.beginInsertRows(QModelIndex(), len(self._rows), len(self._rows))
        self._rows.append(row)
        self.endInsertRows()
    
    def remove_row(self, row_idx: int) -> bool:
        """Satırı sil"""
        if not (0 <= row_idx < len(self._rows)):
            return False
        
        self.beginRemoveRows(QModelIndex(), row_idx, row_idx)
        self._rows.pop(row_idx)
        self.endRemoveRows()
        return True
    
    def update_row(self, row_idx: int, row: Dict[str, Any]):
        """Satırı güncelle"""
        if 0 <= row_idx < len(self._rows):
            self._rows[row_idx] = row
            top_left = self.index(row_idx, 0)
            bottom_right = self.index(row_idx, len(self._keys) - 1)
            self.dataChanged.emit(top_left, bottom_right)
    
    def get_row(self, row_idx: int) -> Optional[Dict[str, Any]]:
        """Satırı dict olarak al"""
        if 0 <= row_idx < len(self._rows):
            return self._rows[row_idx]
        return None
    
    def get_column_value(self, row_idx: int, key: str) -> Any:
        """Hücre değerini al"""
        row = self.get_row(row_idx)
        if row:
            return row.get(key)
        return None
    
    def all_rows(self) -> List[Dict[str, Any]]:
        """Tüm satırları al"""
        return list(self._rows)
    
    # ──────────────────────────────────────────────────────
    # Filtering & Sorting
    # ──────────────────────────────────────────────────────
    
    def filter_rows(self, predicate: Callable[[Dict[str, Any]], bool]) -> List[Dict[str, Any]]:
        """
        Satırları filtrele (predicate fonksiyonu dönüp false olanları sil)
        
        Args:
            predicate: (row_dict) -> bool
        
        Returns:
            Filtrelenmiş satırlar
        """
        return [row for row in self._rows if predicate(row)]
    
    def sort(self, column: int, order=Qt.AscendingOrder):
        """Sıralama (subclass override edebilir)"""
        if not (0 <= column < len(self._keys)):
            return
        
        key = self._keys[column]
        reverse = (order == Qt.DescendingOrder)
        
        try:
            self.layoutAboutToChange.emit()
            self._rows.sort(key=lambda r: r.get(key, ""), reverse=reverse)
            self.layoutChanged.emit()
        except Exception as e:
            logger.warning(f"Sıralama hatası: {e}")
    
    def search(self, search_text: str, search_keys: List[str] = None) -> List[Dict[str, Any]]:
        """
        Metin araması
        
        Args:
            search_text: Aranacak metin
            search_keys: Aranan kolonlar (None = tüm kolonlar)
        
        Returns:
            Eşleşen satırlar
        """
        if not search_text:
            return self._rows
        
        search_lower = search_text.lower()
        search_keys = search_keys or self._keys
        
        results = []
        for row in self._rows:
            for key in search_keys:
                if search_lower in str(row.get(key, "")).lower():
                    results.append(row)
                    break
        
        return results
    
    # ──────────────────────────────────────────────────────
    # Utility Methods
    # ──────────────────────────────────────────────────────
    
    def get_key_by_index(self, col_idx: int) -> Optional[str]:
        """Kolon indexinden key al"""
        if 0 <= col_idx < len(self._keys):
            return self._keys[col_idx]
        return None
    
    def get_column_width(self, col_idx: int) -> int:
        """Kolon genişliği al"""
        if 0 <= col_idx < len(self._widths):
            return self._widths[col_idx]
        return 100


# ═════════════════════════════════════════════════════════════════════
#  RECORD TABLE DELEGATE
# ═════════════════════════════════════════════════════════════════════

class RecordTableDelegate(QStyledItemDelegate):
    """
    Kayıt tablosu delegate'inin base sınıfı.
    
    Subclass'lar şunları tanımlayabilir:
    - STATUS_COLORS: {status_value: color_hex}
    - TYPE_COLORS: {type_value: color_hex}
    - Custom paint() override
    """
    
    STATUS_COLORS = {}  # Subclass'lar override et
    TYPE_COLORS = {}
    
    def __init__(self, parent=None):
        super().__init__(parent)
    
    # ──────────────────────────────────────────────────────
    # Rendering
    # ──────────────────────────────────────────────────────
    
    def paint(self, painter: QPainter, option, index):
        """
        Hücre painting (base: standard + arka plan rengi)
        Subclass'lar override edebilir daha özel effektler için.
        """
        # Standard painting
        super().paint(painter, option, index)
    
    def sizeHint(self, option, index) -> QSize:
        """Hücre boyutu ipucu"""
        size = super().sizeHint(option, index)
        size.setHeight(max(size.height(), 28))  # Min height
        return size
    
    # ──────────────────────────────────────────────────────
    # Color Helpers
    # ──────────────────────────────────────────────────────
    
    def get_status_color(self, status: str) -> Optional[str]:
        """Durum değerinden rengi al"""
        if not status:
            return None
        return self.STATUS_COLORS.get(status)
    
    def get_type_color(self, type_val: str) -> Optional[str]:
        """Tip değerinden renği al"""
        if not type_val:
            return None
        return self.TYPE_COLORS.get(type_val)
    
    # ──────────────────────────────────────────────────────
    # Status Color Mappers (Subclass Integration)
    # ──────────────────────────────────────────────────────
    
    @staticmethod
    def get_duration_color(days: int) -> str:
        """
        Süreye göre KPI rengi (3-6-12 ay kuralı)
        - 0-90 gün: YEŞIL
        - 91-180 gün: SARI (AMBER)
        - 181+ gün: KIRMIZI
        """
        if days < 0:
            return "#999999"  # Geçersiz
        elif days <= 90:
            return "#3ecf8e"  # Yeşil (iyi)
        elif days <= 180:
            return "#f5a623"  # Sarı (uyarı)
        else:
            return "#f75f5f"  # Kırmızı (kritik)
    
    @staticmethod
    def get_status_color_cihaz(status: str) -> str:
        """Cihaz durumuna göre renk"""
        status_colors = {
            "Açık": "#f75f5f",
            "Acik": "#f75f5f",
            "Devam Ediyor": "#f5a623",
            "Kapalı": "#3ecf8e",
            "Kapali": "#3ecf8e",
        }
        return status_colors.get(status, "#999999")
    
    @staticmethod
    def get_priority_color(priority: str) -> str:
        """Önceliğe göre renk"""
        priority_colors = {
            "Kritik": "#f75f5f",
            "Yüksek": "#f5a623",
            "Orta": "#4f8ef7",
            "Düşük": "#5a6278",
        }
        return priority_colors.get(priority, "#999999")


class BakimTableDelegate(RecordTableDelegate):
    """Bakım tablosu için özel delegate"""
    
    # Bakım durumları
    STATUS_COLORS = {
        "Planlandı": "#4f8ef7",  # Mavi
        "Yapılıyor": "#f5a623",  # Amber
        "Tamamlandı": "#3ecf8e",  # Yeşil
        "Beklemede": "#5a6278",  # Gri
        "Hatalı": "#f75f5f",  # Kırmızı
    }
    
    # Bakım tipleri
    TYPE_COLORS = {
        "Rutin": "#3ecf8e",  # Yeşil
        "Acil": "#f75f5f",  # Kırmızı
        "Preventif": "#4f8ef7",  # Mavi
        "Aydınlatma": "#f5a623",  # Amber
    }


class KalibrasyonTableDelegate(RecordTableDelegate):
    """Kalibrasyon tablosu için özel delegate"""
    
    # Kalibrasyon durumları
    STATUS_COLORS = {
        "Geçti": "#3ecf8e",  # Yeşil
        "İnceleme": "#f5a623",  # Amber
        "Başarısız": "#f75f5f",  # Kırmızı
        "Bekleniyor": "#5a6278",  # Gri
    }
    
    # Kalibrasyon tipleri
    TYPE_COLORS = {
        "Standart": "#4f8ef7",  # Mavi
        "Hassas": "#f75f5f",  # Kırmızı (kritik)
        "Rutin": "#3ecf8e",  # Yeşil
    }


# ─────────────────────────────────────────────────────────
# Renk sabitleri (Global shared colors)
# ─────────────────────────────────────────────────────────

THEME_COLORS = {
    "success": "#3ecf8e",    # Yeşil
    "warning": "#f5a623",    # Amber
    "danger": "#f75f5f",     # Kırmızı
    "info": "#4f8ef7",       # Mavi
    "secondary": "#5a6278",  # Gri
}

DURATION_COLORS_3_6_12 = {
    "0-90": "#3ecf8e",    # YeşilG (İyi)
    "91-180": "#f5a623",  # Amber (Uyarı)
    "181+": "#f75f5f",    # Kırmızı (Kritik)
}
