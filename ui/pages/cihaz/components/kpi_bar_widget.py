# -*- coding: utf-8 -*-
"""
Cihaz Modülü - KPI Bar Widget
==============================
Bakım ve Kalibrasyon sayfalarında KPI şeridi (metrik kartları).
"""
from typing import Optional, Dict, List
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel
from PySide6.QtGui import QFont

from core.logger import logger


class KPICard(QWidget):
    """
    Tek KPI kartı (başlık + değer + renk)
    
    Args:
        title: Kart başlığı ("TOPLAM BAKIM", vb.)
        value: Gösterilecek değer (str veya int)
        subtitle: Alt metin (opsiyonel)
        color: Renk ("red", "amber", "green", "blue", "muted")
        size: Kart boyutu ("small", "medium", "large")
    """
    
    COLOR_PALETTE = {
        "red": "#f75f5f",
        "amber": "#f5a623",
        "green": "#3ecf8e",
        "blue": "#4f8ef7",
        "muted": "#5a6278",
    }
    
    def __init__(self, title: str, value: str = "0", subtitle: str = "",
                 color: str = "blue", size: str = "medium", parent=None):
        super().__init__(parent)
        self._title = title
        self._value = str(value)
        self._subtitle = subtitle
        self._color = color
        self._size = size
        
        # Renk şeması
        self._color_hex = self.COLOR_PALETTE.get(color, self.COLOR_PALETTE["blue"])
        
        self._setup_ui()
    
    def _setup_ui(self):
        """UI inşa et"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(2)
        
        # Başlık
        lbl_title = QLabel(self._title)
        lbl_title.setStyleSheet(
            f"font-size:9px; font-weight:600; letter-spacing:0.06em; "
            f"color:{self._color_hex}; text-transform:uppercase;"
        )
        layout.addWidget(lbl_title)
        
        # Değer
        lbl_value = QLabel(self._value)
        font = QFont()
        if self._size == "large":
            font.setPointSize(18)
        elif self._size == "small":
            font.setPointSize(12)
        else:  # medium
            font.setPointSize(16)
        font.setBold(True)
        lbl_value.setFont(font)
        lbl_value.setStyleSheet(f"color:{self._color_hex};")
        layout.addWidget(lbl_value)
        
        # Alt metin (opsiyonel)
        if self._subtitle:
            lbl_sub = QLabel(self._subtitle)
            lbl_sub.setStyleSheet(f"font-size:8px; color:#999; margin-top:2px;")
            layout.addWidget(lbl_sub)
        
        # Arka plan
        self.setStyleSheet(
            f"QWidget{{background:#191d26; border-radius:6px; margin:0 2px;}}"
            f"QWidget:hover{{background:#242938;}}"
        )
    
    def set_value(self, value):
        """Değeri güncelle"""
        self._value = str(value)
        # TODO: UI güncelle
    
    def set_color(self, color: str):
        """Rengi değiştir"""
        if color not in self.COLOR_PALETTE:
            logger.warning(f"Geçersiz renk: {color}")
            return
        self._color = color
        self._color_hex = self.COLOR_PALETTE[color]
        # TODO: UI güncelle


class KPIBar(QWidget):
    """
    KPI şeridi (birden fazla card)
    
    Bakım sayfasında:
    - Toplam Bakım
    - Yapılan Bu Ay
    - Ort. Aralık (gün)
    - Overdue (kırmızı)
    - Planlanan Sonraki
    
    Kalibrasyon sayfasında:
    - Toplam Kalibrasyon
    - Geçen Bu Yıl
    - Sonraki Tarih
    - Overdue
    - Hassas Aletler
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(68)
        self.setStyleSheet("background:#13161d;")  # Dark bg
        
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(12, 8, 12, 8)
        self._layout.setSpacing(1)
        
        self._cards: Dict[str, QLabel] = {}
    
    def add_card(self, key: str, title: str, value: str = "0",
                 color: str = "blue", size: str = "medium"):
        """KPI kartı ekle"""
        card = KPICard(title, value, color=color, size=size, parent=self)
        self._layout.addWidget(card, 1)
        self._cards[key] = card
    
    def update_value(self, key: str, value):
        """Kart değerini güncelle"""
        if key in self._cards:
            self._cards[key].set_value(value)


class BakimKPIBar(KPIBar):
    """Bakım sayfası için KPI şeridi"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.add_card("toplam", "TOPLAM BAKIM", "0", color="blue")
        self.add_card("ayda", "YAPILAN BU AY", "0", color="green")
        self.add_card("ort_aralık", "ORT. ARALIK", "— gün", color="amber")
        self.add_card("overdue", "GEÇİKEN", "0", color="red")
        self.add_card("sonraki", "SONRAKI TARIH", "—", color="blue")


class KalibrasyonKPIBar(KPIBar):
    """Kalibrasyon sayfası için KPI şeridi"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.add_card("toplam", "TOPLAM KALİBRASYON", "0", color="blue")
        self.add_card("bu_yil", "GECEN BU YIL", "0", color="green")
        self.add_card("sonraki", "SONRAKI TARIH", "—", color="amber")
        self.add_card("overdue", "GEÇMİŞ TARİH", "0", color="red")
        self.add_card("hassas", "HASSAS ALETLER", "0", color="blue")


# ─────────────────────────────────────────────────────────
# Utility: Duration-based color
# ─────────────────────────────────────────────────────────

def get_duration_color_name(days: int) -> str:
    """
    Bakım aralığı (gün) → renk adı
    - 0-90 gün: green
    - 91-180 gün: amber
    - 181+ gün: red
    """
    if days < 0:
        return "muted"
    elif days <= 90:
        return "green"
    elif days <= 180:
        return "amber"
    else:
        return "red"
