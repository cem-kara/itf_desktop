# -*- coding: utf-8 -*-
from PySide6.QtWidgets import QPushButton
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QCursor

from ui.theme_manager import ThemeManager
from ui.pages.cihaz.cihaz_ekle import CihazEklePage

# Merkezi stil
S = ThemeManager.get_all_component_styles()

class CihazDetayPage(CihazEklePage):
    """
    Cihaz Detay Sayfası (Form Görünümü)
    - CihazEklePage altyapısını kullanır.
    - Başlangıçta read-only (pasif).
    - Düzenle butonu ile aktif hale gelir.
    - Silme butonu YOKTUR.
    """
    back_requested = Signal()        # Listeye geri dön

    def __init__(self, db=None, data=None, on_saved=None, parent=None):
        # CihazEklePage edit_data bekler
        super().__init__(db=db, edit_data=data, on_saved=on_saved, parent=parent)
        
        self._setup_detail_mode()

    def _setup_detail_mode(self):
        # 1. Footer butonlarını düzenle (Önce butonlar oluşmalı)
        layout = self.layout()
        if layout:
            count = layout.count()
            if count > 0:
                footer_item = layout.itemAt(count - 1)
                if footer_item and footer_item.layout():
                    self._customize_footer(footer_item.layout())

        # 2. Sonra form elemanlarını pasif yap
        self._set_form_enabled(False)

    def _customize_footer(self, footer_layout):
        # Mevcut butonları gizle (Kaydet, İptal)
        for i in range(footer_layout.count()):
            item = footer_layout.itemAt(i)
            if item.widget():
                item.widget().setVisible(False)
        
        # Yeni butonlar ekle
        
        # ← Listeye Dön
        self.btn_back = QPushButton("← Listeye Dön")
        self.btn_back.setStyleSheet(S["back_btn"])
        self.btn_back.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_back.setFixedHeight(42)
        self.btn_back.clicked.connect(self.back_requested.emit)
        footer_layout.addWidget(self.btn_back)
        
        footer_layout.addStretch()

        # ✏️ Düzenle
        self.btn_edit = QPushButton("✏️ Düzenle")
        self.btn_edit.setStyleSheet(S["edit_btn"])
        self.btn_edit.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_edit.setFixedHeight(42)
        self.btn_edit.clicked.connect(self._enable_edit)
        footer_layout.addWidget(self.btn_edit)

        # ✓ Kaydet (Başlangıçta gizli)
        self.btn_save_custom = QPushButton("✓ Değişiklikleri Kaydet")
        self.btn_save_custom.setStyleSheet(S["save_btn"])
        self.btn_save_custom.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_save_custom.setFixedHeight(42)
        self.btn_save_custom.clicked.connect(self._on_save) # Base method
        self.btn_save_custom.setVisible(False)
        footer_layout.addWidget(self.btn_save_custom)

        # İptal (Düzenleme modundan çıkmak için)
        self.btn_cancel_edit = QPushButton("✕ Vazgeç")
        self.btn_cancel_edit.setStyleSheet(S["cancel_btn"])
        self.btn_cancel_edit.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_cancel_edit.setFixedHeight(42)
        self.btn_cancel_edit.clicked.connect(self._disable_edit)
        self.btn_cancel_edit.setVisible(False)
        footer_layout.insertWidget(footer_layout.count()-1, self.btn_cancel_edit)

    def _set_form_enabled(self, enabled):
        # self.ui içindeki widgetlar
        for widget in self.ui.values():
            widget.setEnabled(enabled)
            
        # Diğer butonlar (Resim seç, dosya seç)
        for btn in self.findChildren(QPushButton):
            # Footer butonlarını hariç tut
            if btn in [self.btn_back, self.btn_edit, self.btn_save_custom, self.btn_cancel_edit]:
                continue
            # Base class'ın gizli butonlarını atla
            if not btn.isVisible():
                continue
            
            btn.setEnabled(enabled)

    def _enable_edit(self):
        self._set_form_enabled(True)
        self.btn_edit.setVisible(False)
        self.btn_back.setVisible(False)
        self.btn_save_custom.setVisible(True)
        self.btn_cancel_edit.setVisible(True)

    def _disable_edit(self):
        # Değişiklikleri geri al
        self._fill_form(self._edit_data)
        
        self._set_form_enabled(False)
        self.btn_edit.setVisible(True)
        self.btn_back.setVisible(True)
        self.btn_save_custom.setVisible(False)
        self.btn_cancel_edit.setVisible(False)
