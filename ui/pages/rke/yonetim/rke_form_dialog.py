# -*- coding: utf-8 -*-
"""
RKE Form Dialog – Modal Pencere
─────────────────────────────────
Envanter Yönetimi sayfasından "Yeni RKE Ekle" veya "Düzenle" için modal dialog.
RKEFormWidget'ı içinde barındırır.

Sinyaller:
    kaydet_istendi(str mod, dict veri)  – "INSERT" veya "UPDATE"
    iptal_istendi()
"""
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QMessageBox
)
from PySide6.QtGui import QCursor

from ui.theme_manager import ThemeManager
from ui.styles import DarkTheme
from ui.styles.icons import IconRenderer

from ui.pages.rke.yonetim.rke_form_widget import RKEFormWidget

S = ThemeManager.get_all_component_styles()


class RKEFormDialog(QDialog):
    """
    RKE Ekleme/Düzenleme Modal Dialog.
    
    Sinyaller:
        kaydet_istendi(mod, veri)   Kaydet butonuna basıldığında
        iptal_istendi()             İptal butonuna basıldığında
    """
    kaydet_istendi = Signal(str, dict)
    iptal_istendi  = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Ekipman Ekle / Düzenle")
        self.setModal(True)
        self.setMinimumWidth(600)
        self.setMinimumHeight(700)
        self.setStyleSheet(S.get("dialog", f"background-color: {DarkTheme.SURFACE_PRIMARY};"))
        
        self._form = RKEFormWidget()
        self._rke_listesi = []
        self._kisaltma = {}
        self._mod = "INSERT"  # INSERT | UPDATE
        
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 12)
        layout.setSpacing(12)

        # Form widget
        layout.addWidget(self._form, 1)

        # Butonlar
        h_btn = QHBoxLayout()
        h_btn.setSpacing(8)
        
        btn_iptal = QPushButton("İptal")
        btn_iptal.setStyleSheet(S.get("cancel_btn", ""))
        btn_iptal.setCursor(QCursor(Qt.PointingHandCursor))
        btn_iptal.clicked.connect(self.reject)
        IconRenderer.set_button_icon(btn_iptal, "x", color=DarkTheme.TEXT_PRIMARY, size=14)
        
        btn_kaydet = QPushButton("Kaydet")
        btn_kaydet.setStyleSheet(S.get("save_btn", ""))
        btn_kaydet.setCursor(QCursor(Qt.PointingHandCursor))
        btn_kaydet.clicked.connect(self._on_save_clicked)
        IconRenderer.set_button_icon(btn_kaydet, "save", color=DarkTheme.TEXT_PRIMARY, size=14)
        
        h_btn.addStretch()
        h_btn.addWidget(btn_iptal)
        h_btn.addWidget(btn_kaydet)
        layout.addLayout(h_btn)
        
        # Dialog button'larını sakla (form buttonlarını kullan)
        self._form.btn_kaydet.hide()
        self._form.btn_temizle.hide()

    def _connect_signals(self):
        # Form sinyalleri
        self._form.kaydet_istendi.connect(self._on_form_kaydet)
        self._form.temizle_istendi.connect(lambda: None)
        
        # Dialog sinyalleri
        self.rejected.connect(self._on_dialog_reject)

    # ═══════════════════════════════════════════
    #  DIALOG KONTROLÜ
    # ═══════════════════════════════════════════

    def open_new(self, rke_listesi: list, kisaltma: dict, sabitler: dict):
        """Yeni kayıt modunda dialog'u aç."""
        self.setWindowTitle("Yeni Ekipman Ekle")
        self._mod = "INSERT"
        self._rke_listesi = rke_listesi
        self._kisaltma = kisaltma
        
        self._form.set_context(rke_listesi, kisaltma)
        self._form.fill_combos(sabitler)
        self._form.open_new()
        
        self.exec()

    def open_edit(self, row_data: dict, rke_listesi: list, kisaltma: dict, sabitler: dict):
        """Düzenleme modunda dialog'u aç."""
        self.setWindowTitle("Ekipman Düzenle")
        self._mod = "UPDATE"
        self._rke_listesi = rke_listesi
        self._kisaltma = kisaltma
        
        self._form.set_context(rke_listesi, kisaltma)
        self._form.fill_combos(sabitler)
        self._form.load_row(row_data)
        
        self.exec()

    # ═══════════════════════════════════════════
    #  SINYAL YÖNETIMI
    # ═══════════════════════════════════════════

    def _on_form_kaydet(self, mod: str, veri: dict):
        """Form'dan kaydet sinyali geldiğinde."""
        self.kaydet_istendi.emit(self._mod, veri)

    def _on_save_clicked(self):
        """Dialog'daki Kaydet butonuna basıldığında."""
        # Form'daki kaydet butonundan sinyali emit ettir
        self._form._on_save()

    def _on_dialog_reject(self):
        """Dialog kapatıldığında."""
        self.iptal_istendi.emit()

    def set_busy(self, busy: bool):
        """Kaydetme sırasında busy state'i ayarla."""
        self._form.set_busy(busy)
        self.setEnabled(not busy)
