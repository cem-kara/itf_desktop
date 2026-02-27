# -*- coding: utf-8 -*-
"""
Personel Overview Panel — Refactored View
==========================================
Temiz MVP: View katmanı sadece UI'dan sorumlu.
Form yapısı, dosya yönetimi ayrı modüllere taşınmıştır.
"""
from typing import Dict, Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, 
    QScrollArea, QGroupBox, QGridLayout, QPushButton, QMessageBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap

from core.logger import logger
from ui.styles import DarkTheme
from ui.styles.components import STYLES

from .personel_form_fields import create_form_field, FormSection
from .personel_file_manager import PersonelFileManager


C = DarkTheme


# ─────────────────────────────────────────────────────────────────────────────
# Personel Overview Panel (Refactored)
# ─────────────────────────────────────────────────────────────────────────────

class PersonelOverviewPanel(QWidget):
    """
    Personel merkez ekranı Genel Bakış sekmesi.
    
    Features:
        - Personel bilgileri görüntüleme
        - Form düzenlemesi
        - Dosya yönetimi (upload, preview)
    
    Signals:
        data_changed(dict): Veri değişti
        file_uploaded(str, str): Dosya yüklendi (alan_adi, link)
    """

    data_changed = Signal(dict)
    file_uploaded = Signal(str, str)

    def __init__(self, personel_data: dict, db=None, parent=None):
        super().__init__(parent)
        self.setStyleSheet(STYLES["page"])
        
        # State
        self.personel_data = personel_data or {}
        self._db = db
        self._file_manager = PersonelFileManager()
        self._form_sections: Dict[str, FormSection] = {}
        self._edit_mode = False
        
        # UI
        self._setup_ui()

    def _setup_ui(self):
        """UI bileşenleri oluştur."""
        main = QVBoxLayout(self)
        main.setContentsMargins(0, 0, 0, 0)
        main.setSpacing(0)

        # Scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        content = QWidget()
        content.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        if not self.personel_data:
            layout.addWidget(QLabel("Personel verisi bulunamadı."))
            scroll.setWidget(content)
            main.addWidget(scroll)
            return

        # ── Header (Fotoğraf + Temel Bilgiler) ──────────────────────────────
        header_frame = QFrame()
        header_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {C.BG_SECONDARY};
                border: 1px solid {C.BORDER_PRIMARY};
                border-radius: 8px;
            }}
        """)
        header_lay = QHBoxLayout(header_frame)
        header_lay.setContentsMargins(15, 15, 15, 15)
        header_lay.setSpacing(20)

        # Fotoğraf
        self.lbl_resim = QLabel()
        self.lbl_resim.setFixedSize(80, 100)
        self.lbl_resim.setAlignment(Qt.AlignCenter)
        self.lbl_resim.setStyleSheet(
            f"border: 1px solid {C.BORDER_PRIMARY}; border-radius: 6px; "
            f"background: {C.BG_SECONDARY}; color: {C.TEXT_DISABLED};"
        )
        self._load_photo()
        header_lay.addWidget(self.lbl_resim)

        # Temel bilgiler (salt okunur)
        info_lay = QGridLayout()
        info_lay.setSpacing(8)

        tc = self.personel_data.get("TCKN", "—")
        unvan = self.personel_data.get("Unvan", "—")
        birim = self.personel_data.get("Birim", "—")

        info_lay.addWidget(QLabel("TC No:"), 0, 0)
        info_lay.addWidget(QLabel(tc), 0, 1)
        info_lay.addWidget(QLabel("Ünvan:"), 1, 0)
        info_lay.addWidget(QLabel(unvan), 1, 1)
        info_lay.addWidget(QLabel("Birim:"), 2, 0)
        info_lay.addWidget(QLabel(birim), 2, 1)

        header_lay.addLayout(info_lay, 1)

        # Edit button
        self.btn_edit = QPushButton("✏️ Düzenle")
        self.btn_edit.setFixedSize(90, 36)
        self.btn_edit.setStyleSheet(f"""
            QPushButton {{
                background-color: {C.ACCENT_PRIMARY};
                color: white;
                border: none;
                border-radius: 4px;
                font-weight: 600;
            }}
        """)
        self.btn_edit.clicked.connect(self._toggle_edit_mode)
        header_lay.addWidget(self.btn_edit)

        layout.addWidget(header_frame)

        # ── Form Bölümleri ──────────────────────────────────────────────────
        self._build_form_sections(layout)

        layout.addStretch()
        scroll.setWidget(content)
        main.addWidget(scroll)

    def _build_form_sections(self, parent_layout: QVBoxLayout):
        """Form bölümlerini oluştur."""
        
        # Kişisel Bilgiler
        personal_section = QGroupBox("Kişisel Bilgiler")
        personal_lay = QGridLayout(personal_section)
        
        ad = create_form_field("Ad", editable=True)
        ad.setText(self.personel_data.get("Ad", ""))
        personal_lay.addWidget(QLabel("Ad:"), 0, 0)
        personal_lay.addWidget(ad, 0, 1)
        
        soyad = create_form_field("Soyad", editable=True)
        soyad.setText(self.personel_data.get("Soyad", ""))
        personal_lay.addWidget(QLabel("Soyad:"), 1, 0)
        personal_lay.addWidget(soyad, 1, 1)
        
        telefon = create_form_field("Telefon", editable=True)
        telefon.setText(self.personel_data.get("CepTelefonu", ""))
        personal_lay.addWidget(QLabel("Telefon:"), 2, 0)
        personal_lay.addWidget(telefon, 2, 1)
        
        self._form_sections["personal"] = FormSection("Kişisel Bilgiler")
        self._form_sections["personal"].add_field("Ad", "Ad", ad, True)
        self._form_sections["personal"].add_field("Soyad", "Soyad", soyad, True)
        self._form_sections["personal"].add_field("CepTelefonu", "Telefon", telefon, True)
        
        personal_section.setStyleSheet(f"""
            QGroupBox {{
                color: {C.TEXT_PRIMARY};
                border: 1px solid {C.BORDER_PRIMARY};
                border-radius: 6px;
                margin-top: 8px;
                padding-top: 8px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 3px 0 3px;
            }}
        """)
        
        parent_layout.addWidget(personal_section)

        # İş Bilgileri
        work_section = QGroupBox("İş Bilgileri")
        work_lay = QGridLayout(work_section)
        
        unvan_field = create_form_field("Ünvan", editable=False)
        unvan_field.setText(self.personel_data.get("Unvan", ""))
        work_lay.addWidget(QLabel("Ünvan:"), 0, 0)
        work_lay.addWidget(unvan_field, 0, 1)
        
        birim_field = create_form_field("Birim", editable=False)
        birim_field.setText(self.personel_data.get("Birim", ""))
        work_lay.addWidget(QLabel("Birim:"), 1, 0)
        work_lay.addWidget(birim_field, 1, 1)
        
        work_section.setStyleSheet(personal_section.styleSheet())
        parent_layout.addWidget(work_section)

    def _load_photo(self):
        """Fotoğraf yükle."""
        photo_url = self.personel_data.get("PhotoURL")
        if photo_url:
            # Not: Gerçek implementasyon URL'den resim indirecek
            self.lbl_resim.setText("📷")
        else:
            self.lbl_resim.setText("Resim yok")

    def _toggle_edit_mode(self):
        """Düzenleme modunu aç/kapat."""
        self._edit_mode = not self._edit_mode
        self.btn_edit.setText("💾 Kaydet" if self._edit_mode else "✏️ Düzenle")
        
        if self._edit_mode:
            logger.debug("Edit mode: ON")
            # Form alanlarını editable yap
        else:
            logger.debug("Edit mode: OFF")
            # Değişiklikleri kaydet
            self._save_changes()

    def _save_changes(self):
        """Değişiklikleri kaydet."""
        try:
            data = {}
            for section in self._form_sections.values():
                data.update(section.get_values())
            
            self.data_changed.emit(data)
            QMessageBox.information(self, "Başarı", "Değişiklikler kaydedildi.")
            logger.info("Personel bilgileri güncellendi")
        except Exception as e:
            logger.error(f"Kaydetme hatası: {e}")
            QMessageBox.critical(self, "Hata", f"Kaydetme başarısız: {e}")
