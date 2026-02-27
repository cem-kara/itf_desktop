# -*- coding: utf-8 -*-
"""
Personel Listesi - Filter Panel Component
==========================================
Arama, durum filtresi ve combo filtreleri.
"""
from typing import Dict, List

from PySide6.QtCore import Qt, Signal, QTimer, QPoint
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QLineEdit, QComboBox, QLabel,
    QPushButton, QMenu, QFrame
)
from PySide6.QtGui import QCursor

from ui.styles import DarkTheme
from ui.styles.components import ComponentStyles

C = DarkTheme


# ─────────────────────────────────────────────────────────────────────────────
# Personel Filter Panel
# ─────────────────────────────────────────────────────────────────────────────

class PersonelFilterPanel(QWidget):
    """
    Personel listesi filtre paneli.
    
    Signals:
        filter_changed(durum, combo_filters, search_text)
            durum: "Aktif", "Pasif", "Tüm"
            combo_filters: {"Birim": value, "Unvan": value, ...}
            search_text: Arama metni
    """

    filter_changed = Signal(str, dict, str)  # durum, combo_filters, search_text

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background-color: {C.BG_SECONDARY};")
        
        # State
        self._active_filter = "Aktif"
        self._combo_filters: Dict[str, str] = {}
        self._last_search_text = ""
        
        # Search debounce
        self._search_timer = QTimer()
        self._search_timer.setInterval(300)
        self._search_timer.setSingleShot(True)
        self._search_timer.timeout.connect(self._on_search_timeout)
        
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        """UI bileşenleri oluştur."""
        lay = QHBoxLayout(self)
        lay.setContentsMargins(16, 12, 16, 12)
        lay.setSpacing(12)

        # ── Durum Filtre Pill Butonları ─────────────────────────────────────
        durum_options = ["Aktif", "Pasif", "Tüm"]
        self._durum_btns = {}

        for durum in durum_options:
            btn = QPushButton(durum)
            btn.setCursor(QCursor(Qt.PointingHandCursor))
            btn.setFixedHeight(36)
            btn.setCheckable(True)
            btn.setChecked(durum == "Aktif")
            
            # Stil
            status_color = ComponentStyles.get_status_color(durum) if durum != "Tüm" else C.TEXT_SECONDARY
            text_color = ComponentStyles.get_status_text_color(durum) if durum != "Tüm" else C.TEXT_PRIMARY
            
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {status_color};
                    color: {text_color};
                    border: none;
                    padding: 8px 16px;
                    border-radius: 6px;
                    font-weight: 600;
                    font-size: 12px;
                }}
                QPushButton:checked {{
                    border: 2px solid {C.ACCENT_PRIMARY};
                    padding: 6px 14px;
                }}
                QPushButton:hover {{
                    opacity: 0.85;
                }}
            """)
            
            btn.clicked.connect(lambda checked, d=durum: self._on_durum_clicked(d))
            lay.addWidget(btn)
            self._durum_btns[durum] = btn

        lay.addStretch(1)

        # ── Combo Filtreler (Placeholder) ───────────────────────────────────
        # Not: Bu combo'lar _populate_combos() ile dolu edilecek
        self._combos: Dict[str, QComboBox] = {}

        # ── Arama Inputu ────────────────────────────────────────────────────
        search_label = QLabel("🔍")
        search_label.setStyleSheet(f"color: {C.TEXT_SECONDARY}; font-size: 12px;")
        lay.addWidget(search_label)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Ad, TC, telefon, sicil...")
        self.search_input.setFixedWidth(250)
        self.search_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {C.BG_PRIMARY};
                color: {C.TEXT_PRIMARY};
                border: 1px solid {C.BORDER_PRIMARY};
                padding: 8px;
                border-radius: 4px;
            }}
            QLineEdit:focus {{
                border: 1px solid {C.ACCENT_PRIMARY};
            }}
        """)
        lay.addWidget(self.search_input)

    def _connect_signals(self):
        """Sinyal bağlantıları oluştur."""
        self.search_input.textChanged.connect(self._on_search_changed)

    # ────────────────────────────────────────────────────────────────────────
    # Filter Methods
    # ────────────────────────────────────────────────────────────────────────

    def _on_durum_clicked(self, durum: str):
        """Durum filtre pill tıklandı."""
        # Seçili butonları güncelle
        for d, btn in self._durum_btns.items():
            btn.setChecked(d == durum)
        
        self._active_filter = durum
        self._emit_filter_changed()

    def _on_search_changed(self):
        """Arama metni değişti (debounce ile)."""
        self._search_timer.stop()
        self._search_timer.start()

    def _on_search_timeout(self):
        """Arama timeout - filter emit et."""
        search_text = self.search_input.text().strip()
        if search_text != self._last_search_text:
            self._last_search_text = search_text
            self._emit_filter_changed()

    def _on_combo_changed(self):
        """Combo filtre değişti."""
        self._emit_filter_changed()

    def _emit_filter_changed(self):
        """Filter değişikliği sinyali emit et."""
        search_text = self.search_input.text().strip()
        
        combo_filters = {}
        for key, combo in self._combos.items():
            combo_filters[key] = combo.currentText()
        
        self.filter_changed.emit(self._active_filter, combo_filters, search_text)

    # ────────────────────────────────────────────────────────────────────────
    # Combo Management
    # ────────────────────────────────────────────────────────────────────────

    def add_combo_filter(self, key: str, options: List[str]):
        """
        Combo filtre ekle.
        
        Args:
            key: Filter key (db field adı)
            options: Combo seçenekleri
        """
        # İlk seçenek daima "Tüm"
        if "Tüm" not in options:
            options = ["Tüm"] + options

        combo = QComboBox()
        combo.addItems(options)
        combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {C.BG_PRIMARY};
                color: {C.TEXT_PRIMARY};
                border: 1px solid {C.BORDER_PRIMARY};
                padding: 6px;
                border-radius: 4px;
            }}
            QComboBox::drop-down {{
                border: none;
            }}
        """)
        combo.currentTextChanged.connect(self._on_combo_changed)
        
        # Layout'a ekle (search inputundan hemen sonra)
        parent_lay = self.layout()
        insert_pos = parent_lay.count() - 2  # search inputundan önce
        parent_lay.insertWidget(insert_pos, combo)
        
        self._combos[key] = combo

    def get_active_filter(self) -> str:
        """Aktif durum filtresi."""
        return self._active_filter

    def get_combo_filter(self, key: str) -> str:
        """Combo filtre değeri."""
        if key in self._combos:
            return self._combos[key].currentText()
        return "Tüm"

    def get_search_text(self) -> str:
        """Arama metni."""
        return self.search_input.text().strip()

    def clear(self):
        """Filtreleri sıfırla."""
        self._active_filter = "Aktif"
        self._durum_btns["Aktif"].setChecked(True)
        self.search_input.clear()
        for combo in self._combos.values():
            combo.setCurrentIndex(0)
        self._emit_filter_changed()
