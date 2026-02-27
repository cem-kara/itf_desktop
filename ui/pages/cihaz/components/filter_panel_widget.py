# -*- coding: utf-8 -*-
"""
Cihaz Modülü - Filter Panel Widget
===================================
Bakım, Kalibrasyon, vb. sayfalarında filtre paneli.
Arama + combo filtreler + apply button.
"""
from typing import Dict, List, Optional, Tuple
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QLineEdit, QComboBox, QPushButton, QLabel
)

from core.logger import logger


class FilterPanel(QWidget):
    """
    Genel filtre paneli (Bakım, Kalibrasyon, vb.)
    
    Signals:
        filter_changed: (search_text, filter_dict) → tetiklenir
    """
    
    filter_changed = Signal(str, dict)  # (search_text, filter_dict)
    
    def __init__(self, filters: Dict[str, List[str]] = None, parent=None):
        """
        Args:
            filters: {
                "durum": ["Açık", "Kapalı", ...],
                "tip": ["Elektrik", "Mekanik", ...],
                ...
            }
        """
        super().__init__(parent)
        self._filters_config = filters or {}
        self._combos: Dict[str, QComboBox] = {}
        
        self._setup_ui()
    
    def _setup_ui(self):
        """UI inşa et"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        
        # Filtreler grup
        filter_group = QGroupBox("Filtreler")
        fg_layout = QVBoxLayout(filter_group)
        fg_layout.setSpacing(6)
        
        # Arama kutusu
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Başlık, No, vb. ara...")
        self.search_input.textChanged.connect(self._on_filter_change)
        fg_layout.addWidget(QLabel("Arama:"))
        fg_layout.addWidget(self.search_input)
        
        # Dinamik combo filtreler
        for filter_name, options in self._filters_config.items():
            combo = QComboBox()
            combo.addItem("Tümü")
            combo.addItems(options)
            combo.currentTextChanged.connect(self._on_filter_change)
            
            fg_layout.addWidget(QLabel(f"{filter_name.capitalize()}:"))
            fg_layout.addWidget(combo)
            self._combos[filter_name] = combo
        
        layout.addWidget(filter_group)
        layout.addStretch()
        
        # Apply butonu
        self.apply_btn = QPushButton("Uygula")
        self.apply_btn.clicked.connect(self._on_filter_change)
        layout.addWidget(self.apply_btn)
    
    def _on_filter_change(self):
        """Filtre değişti → signal emit et"""
        search_text = self.search_input.text()
        filter_dict = {name: combo.currentText() for name, combo in self._combos.items()}
        self.filter_changed.emit(search_text, filter_dict)
    
    def get_filters(self) -> Tuple[str, Dict[str, str]]:
        """Aktif filtre değerlerini döndür"""
        search_text = self.search_input.text()
        filter_dict = {name: combo.currentText() for name, combo in self._combos.items()}
        return search_text, filter_dict
    
    def reset_filters(self):
        """Filtreleri sıfırla"""
        self.search_input.clear()
        for combo in self._combos.values():
            combo.setCurrentIndex(0)  # "Tümü"
    
    def set_filter_value(self, filter_name: str, value: str):
        """Filtre değeri ayarla"""
        if filter_name in self._combos:
            combo = self._combos[filter_name]
            idx = combo.findText(value)
            if idx >= 0:
                combo.setCurrentIndex(idx)


class BakimFilterPanel(FilterPanel):
    """Bakım sayfası için filtre paneli"""
    
    def __init__(self, parent=None):
        filters = {
            "durum": ["Planlandı", "Yapılıyor", "Tamamlandı", "Beklemede"],
            "tip": ["Rutin", "Acil", "Preventif", "Aydınlatma"],
        }
        super().__init__(filters, parent)


class KalibrasyonFilterPanel(FilterPanel):
    """Kalibrasyon sayfası için filtre paneli"""
    
    def __init__(self, parent=None):
        filters = {
            "durum": ["Geçti", "İnceleme", "Başarısız", "Bekleniyor"],
            "tip": ["Standart", "Hassas", "Rutin"],
        }
        super().__init__(filters, parent)


# ─────────────────────────────────────────────────────────
# Preset Filter Configurations
# ─────────────────────────────────────────────────────────

BAKIM_FILTER_CONFIG = {
    "durum": ["Planlandı", "Yapılıyor", "Tamamlandı", "Beklemede", "Hatalı"],
    "tip": ["Rutin", "Acil", "Preventif", "Aydınlatma"],
}

KALIBRASYON_FILTER_CONFIG = {
    "durum": ["Geçti", "İnceleme", "Başarısız", "Bekleniyor"],
    "tip": ["Standart", "Hassas", "Rutin"],
}

ARIZA_FILTER_CONFIG = {
    "durum": ["Açık", "Devam Ediyor", "Kapalı"],
    "oncelik": ["Kritik", "Yüksek", "Orta", "Düşük"],
    "tip": ["Elektrik", "Mekanik", "Yazılım", "Kontrol", "Diğer"],
}
