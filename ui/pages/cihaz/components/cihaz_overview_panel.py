# -*- coding: utf-8 -*-
"""
Cihaz Overview Panel
─────────────────────────────────────
Genel Bakış sekmesi için cihaz detaylarını gösterir ve düzenleme imkanı sunar.
Her grup için ayrı düzenle/kaydet/iptal butonları vardır.
"""
import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QGridLayout,
    QScrollArea, QGroupBox, QLineEdit, QComboBox, QDateEdit, QPushButton,
    QFileDialog, QMessageBox
)
from PySide6.QtCore import Qt, QDate, Signal
from PySide6.QtGui import QPixmap, QCursor

from ui.styles import DarkTheme, Colors
from ui.styles.components import STYLES as S
from ui.styles.icons import IconRenderer
from core.logger import logger
from database.repository_registry import RepositoryRegistry

C = DarkTheme


class CihazOverviewPanel(QWidget):
    """
    Cihaz Merkez ekranı için 'Genel Bakış' sekmesi içeriği.
    Cihaz detaylarını gösterir ve her grup için ayrı düzenleme imkanı sunar.
    """
    saved = Signal()
    
    def __init__(self, cihaz_data, db=None, sabitler_cache=None, parent=None):
        super().__init__(parent)
        self.cihaz_data = cihaz_data or {}
        self.db = db
        self.sabitler_cache = sabitler_cache
        self._widgets = {}  # Alan adı -> Widget
        self._groups = {}   # Grup ID -> {widget, btn_edit, btn_save, btn_cancel, fields}
        self._file_buttons = {}  # Alan adı -> dosya seç butonu
        
        self._setup_ui()
        self._load_sabitler()
        self._load_data()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Scroll Area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet(S["scroll"])

        content = QWidget()
        content.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # Form grid
        form_grid = QGridLayout()
        form_grid.setHorizontalSpacing(16)
        form_grid.setVerticalSpacing(16)
        form_grid.setColumnStretch(0, 1)
        form_grid.setColumnStretch(1, 1)
        layout.addLayout(form_grid)

        # 1. Medya ve Dosyalar grubu
        grp_media = self._create_editable_group("Medya ve Dosyalar", "media")
        media_content_widget = self._groups["media"]["widget"]
        grid_media = QGridLayout(media_content_widget)
        grid_media.setHorizontalSpacing(12)
        grid_media.setVerticalSpacing(10)

        self._add_line(grid_media, 0, 0, "Cihaz ID", "Cihazid", "media", read_only=True)
        self._add_combo(grid_media, 0, 1, "Cihaz Tipi", "CihazTipi", "media", "Cihaz_Tipi")
        self._add_combo(grid_media, 1, 0, "Ana Bilim Dali", "AnaBilimDali", "media", "AnaBilimDali")
        self._add_combo(grid_media, 1, 1, "Kaynak", "Kaynak", "media", "Kaynak")

        form_grid.addWidget(grp_media, 0, 0)

        # 2. Kimlik Bilgileri grubu
        grp_kimlik = self._create_editable_group("Kimlik Bilgileri", "kimlik")
        kimlik_content_widget = self._groups["kimlik"]["widget"]
        grid_kimlik = QGridLayout(kimlik_content_widget)
        grid_kimlik.setHorizontalSpacing(12)
        grid_kimlik.setVerticalSpacing(10)

        self._add_combo(grid_kimlik, 0, 0, "Marka", "Marka", "kimlik", "Marka")
        self._add_line(grid_kimlik, 0, 1, "Model", "Model", "kimlik")
        self._add_line(grid_kimlik, 1, 0, "Seri No", "SeriNo", "kimlik")
        self._add_combo(grid_kimlik, 1, 1, "Amac", "Amac", "kimlik", "Amac")
        self._add_combo(grid_kimlik, 2, 0, "Birim", "Birim", "kimlik", "Birim")
        self._add_line(grid_kimlik, 2, 1, "Bulundugu Bina", "BulunduguBina", "kimlik")

        form_grid.addWidget(grp_kimlik, 0, 1)

        # 3. NDK Lisans Bilgileri grubu
        grp_lisans = self._create_editable_group("NDK Lisans Bilgileri", "lisans")
        lisans_content_widget = self._groups["lisans"]["widget"]
        grid_lisans = QGridLayout(lisans_content_widget)
        grid_lisans.setHorizontalSpacing(12)
        grid_lisans.setVerticalSpacing(10)

        self._add_line(grid_lisans, 0, 0, "Lisans No", "NDKLisansNo", "lisans")
        self._add_line(grid_lisans, 0, 1, "NDK Seri No", "NDKSeriNo", "lisans")
        self._add_combo(grid_lisans, 1, 0, "Lisans Durum", "LisansDurum", "lisans", "Lisans_Durum")
        self._add_date(grid_lisans, 1, 1, "Lisans Bitis", "BitisTarihi", "lisans")
        self._add_line(grid_lisans, 2, 0, "Sorumlu", "Sorumlusu", "lisans")
        self._add_line(grid_lisans, 2, 1, "RKS", "RKS", "lisans")
        self._add_file(grid_lisans, 3, 0, "Lisans Belgesi", "NDKLisansBelgesi", "lisans", colspan=2)

        form_grid.addWidget(grp_lisans, 1, 0)

        # 4. Teknik Hizmetler grubu
        grp_teknik = self._create_editable_group("Teknik Hizmetler", "teknik")
        teknik_content_widget = self._groups["teknik"]["widget"]
        grid_teknik = QGridLayout(teknik_content_widget)
        grid_teknik.setHorizontalSpacing(12)
        grid_teknik.setVerticalSpacing(10)

        self._add_date(grid_teknik, 0, 0, "Hizmete Giris", "HizmeteGirisTarihi", "teknik", colspan=2)
        self._add_combo(grid_teknik, 1, 0, "Garanti Durum", "GarantiDurumu", "teknik", "Garanti_Durum")
        self._add_date(grid_teknik, 1, 1, "Garanti Bitis", "GarantiBitisTarihi", "teknik")
        self._add_combo(grid_teknik, 2, 0, "Periyodik Bakim", "BakimDurum", "teknik", "Bakim_Durum")
        self._add_combo(grid_teknik, 2, 1, "Kalibrasyon", "KalibrasyonGereklimi", "teknik", "Kalibrasyon_Durum")

        form_grid.addWidget(grp_teknik, 1, 1)

        layout.addStretch()
        scroll.setWidget(content)
        main_layout.addWidget(scroll)

    def _create_editable_group(self, title, group_id):
        """Düzenlenebilir grup kutusu oluştur."""
        grp = QGroupBox()
        grp.setStyleSheet(f"""
            QGroupBox {{
                background-color: {C.BG_SECONDARY};
                border: 1px solid {C.BORDER_PRIMARY};
                border-radius: 8px;
                margin-top: 0px;
                font-weight: bold;
                color: {C.TEXT_PRIMARY};
            }}
        """)
        
        vbox = QVBoxLayout(grp)
        vbox.setContentsMargins(10, 10, 10, 10)
        
        # Header Satırı (Başlık + Butonlar)
        header_row = QHBoxLayout()
        
        lbl_title = QLabel(title)
        lbl_title.setStyleSheet(
            f"color: {C.ACCENT}; font-weight: bold; font-size: 13px;"
        )
        header_row.addWidget(lbl_title)
        header_row.addStretch()

        # Butonlar
        btn_edit = self._create_icon_btn("edit", "Düzenle", lambda: self._toggle_edit(group_id, True))
        btn_save = self._create_icon_btn("save", "Kaydet", lambda: self._save_group(group_id), visible=False)
        btn_cancel = self._create_icon_btn("x", "İptal", lambda: self._toggle_edit(group_id, False), visible=False)
        
        # Stil özelleştirme
        btn_save.setStyleSheet(
            f"background: {Colors.GREEN_600}; color: {C.TEXT_PRIMARY}; border-radius: 4px; padding: 4px 8px;"
        )
        btn_cancel.setStyleSheet(
            f"background: {Colors.RED_600}; color: {C.TEXT_PRIMARY}; border-radius: 4px; padding: 4px 8px;"
        )

        header_row.addWidget(btn_edit)
        header_row.addWidget(btn_save)
        header_row.addWidget(btn_cancel)
        
        vbox.addLayout(header_row)
        
        # İçerik için placeholder widget
        content_widget = QWidget()
        vbox.addWidget(content_widget)
        
        # Referansları sakla
        self._groups[group_id] = {
            "widget": content_widget,
            "btn_edit": btn_edit,
            "btn_save": btn_save,
            "btn_cancel": btn_cancel,
            "fields": []
        }
        
        return grp

    def _create_icon_btn(self, icon_name, tooltip, callback, visible=True):
        """İkon butonu oluştur."""
        btn = QPushButton("")
        btn.setToolTip(tooltip)
        btn.setCursor(QCursor(Qt.PointingHandCursor))
        btn.setFixedSize(30, 26)
        btn.setVisible(visible)
        IconRenderer.set_button_icon(btn, icon_name, color=C.TEXT_SECONDARY, size=14)
        btn.setStyleSheet("""
            QPushButton {
                background: rgba(255,255,255,0.1); 
                border: none; border-radius: 4px; color: #ccc;
            }
            QPushButton:hover { background: rgba(255,255,255,0.2); color: white; }
        """)
        btn.clicked.connect(callback)
        return btn

    def _add_line(self, grid, row, col, label, key, group_id, read_only=False, colspan=1):
        """LineEdit ekle."""
        lbl = QLabel(label)
        lbl.setStyleSheet(S["label_form"])
        edit = QLineEdit()
        edit.setReadOnly(True)
        edit.setProperty("initial_readonly", read_only)
        edit.setStyleSheet(f"background: transparent; border: none; color: {C.TEXT_PRIMARY}; font-weight: 500;")
        self._widgets[key] = edit
        self._groups[group_id]["fields"].append(key)
        grid.addWidget(lbl, row * 2, col, 1, colspan)
        grid.addWidget(edit, row * 2 + 1, col, 1, colspan)

    def _add_combo(self, grid, row, col, label, key, group_id, db_kodu, colspan=1):
        """ComboBox ekle."""
        lbl = QLabel(label)
        lbl.setStyleSheet(S["label_form"])
        combo = QComboBox()
        combo.setEnabled(False)
        combo.setProperty("db_kodu", db_kodu)
        combo.setStyleSheet(
            f"background: transparent; border: none; color: {C.TEXT_PRIMARY}; "
            "font-size: 13px; font-weight: 500; padding: 4px;"
        )
        self._widgets[key] = combo
        self._groups[group_id]["fields"].append(key)
        grid.addWidget(lbl, row * 2, col, 1, colspan)
        grid.addWidget(combo, row * 2 + 1, col, 1, colspan)

    def _add_date(self, grid, row, col, label, key, group_id, colspan=1):
        """DateEdit ekle."""
        lbl = QLabel(label)
        lbl.setStyleSheet(S["label_form"])
        date = QDateEdit()
        date.setCalendarPopup(True)
        date.setDisplayFormat("dd.MM.yyyy")
        date.setEnabled(False)
        date.setStyleSheet(
            f"background: transparent; border: none; color: {C.TEXT_PRIMARY}; "
            "font-size: 13px; font-weight: 500; padding: 4px;"
        )
        self._widgets[key] = date
        self._groups[group_id]["fields"].append(key)
        grid.addWidget(lbl, row * 2, col, 1, colspan)
        grid.addWidget(date, row * 2 + 1, col, 1, colspan)

    def _add_file(self, grid, row, col, label, key, group_id, colspan=1):
        """Dosya seçim alanı ekle."""
        lbl = QLabel(label)
        lbl.setStyleSheet(S["label_form"])
        wrap = QHBoxLayout()
        line = QLineEdit()
        line.setReadOnly(True)
        line.setStyleSheet(f"background: transparent; border: none; color: {C.TEXT_PRIMARY}; font-weight: 500;")
        btn = QPushButton("Sec")
        btn.setStyleSheet(S["btn_refresh"])
        btn.setEnabled(False)
        btn.clicked.connect(lambda: self._pick_file(line))
        wrap.addWidget(line)
        wrap.addWidget(btn)
        container = QWidget()
        container.setLayout(wrap)
        self._widgets[key] = line
        self._file_buttons[key] = btn
        self._groups[group_id]["fields"].append(key)
        grid.addWidget(lbl, row * 2, col, 1, colspan)
        grid.addWidget(container, row * 2 + 1, col, 1, colspan)

    def _pick_file(self, line: QLineEdit):
        """Dosya seç."""
        path, _ = QFileDialog.getOpenFileName(self, "Dosya Sec", "", "Tumu (*.*)")
        if path:
            line.setText(path)

    def _load_sabitler(self):
        """Sabitler tablosundan verileri yükle."""
        if not self.db:
            return
        try:
            registry = RepositoryRegistry(self.db)
            sabitler = registry.get("Sabitler").get_all()

            grouped = {}
            for row in sabitler:
                kod = str(row.get("Kod", "")).strip()
                eleman = str(row.get("MenuEleman", "")).strip()
                if not kod or not eleman:
                    continue
                grouped.setdefault(kod, []).append(eleman)

            for key, widget in self._widgets.items():
                if isinstance(widget, QComboBox):
                    kod = widget.property("db_kodu")
                    if kod and kod in grouped:
                        widget.clear()
                        widget.addItem("")
                        widget.addItems(sorted(grouped[kod]))

        except Exception as e:
            logger.error(f"Sabitler yuklenemedi: {e}")

    def _load_data(self):
        """Cihaz verilerini alanlara yükle."""
        for key, widget in self._widgets.items():
            value = self.cihaz_data.get(key, "")
            
            if isinstance(widget, QLineEdit):
                widget.setText(str(value or ""))
            elif isinstance(widget, QComboBox):
                idx = widget.findText(str(value or ""))
                if idx >= 0:
                    widget.setCurrentIndex(idx)
            elif isinstance(widget, QDateEdit):
                if value:
                    date_str = str(value).strip()
                    if date_str and date_str != "—":
                        try:
                            parts = date_str.split("-")
                            if len(parts) == 3:
                                widget.setDate(QDate(int(parts[0]), int(parts[1]), int(parts[2])))
                            else:
                                widget.setDate(QDate.currentDate())
                        except Exception:
                            widget.setDate(QDate.currentDate())
                else:
                    widget.setDate(QDate.currentDate())

    def _toggle_edit(self, group_id, edit_mode):
        """Grup düzenleme modunu aç/kapat."""
        grp = self._groups[group_id]
        grp["btn_edit"].setVisible(not edit_mode)
        grp["btn_save"].setVisible(edit_mode)
        grp["btn_cancel"].setVisible(edit_mode)
        
        style_edit = (
            f"background: {C.BG_SECONDARY}; border: 1px solid {C.INPUT_BORDER_FOCUS}; "
            f"border-radius: 4px; padding: 4px; color: {C.TEXT_PRIMARY};"
        )
        style_read = f"background: transparent; border: none; color: {C.TEXT_PRIMARY}; font-weight: 500;"
        style_combo_read = (
            f"background: transparent; border: none; color: {C.TEXT_PRIMARY}; "
            "font-size: 13px; font-weight: 500; padding: 4px;"
        )
        style_date_read = (
            f"background: transparent; border: none; color: {C.TEXT_PRIMARY}; "
            "font-size: 13px; font-weight: 500; padding: 4px;"
        )
        
        for key in grp["fields"]:
            widget = self._widgets[key]
            if isinstance(widget, QLineEdit):
                if not widget.property("initial_readonly"):
                    widget.setReadOnly(not edit_mode)
                    widget.setStyleSheet(style_edit if edit_mode else style_read)
            elif isinstance(widget, QComboBox):
                widget.setEnabled(edit_mode)
                widget.setStyleSheet(S["combo"] if edit_mode else style_combo_read)
            elif isinstance(widget, QDateEdit):
                widget.setEnabled(edit_mode)
                widget.setStyleSheet(S["date"] if edit_mode else style_date_read)
            
            # Dosya seçim butonları
            if key in self._file_buttons:
                self._file_buttons[key].setEnabled(edit_mode)
            
            # İptal edilirse eski veriyi geri yükle
            if not edit_mode:
                val = self.cihaz_data.get(key, "")
                if isinstance(widget, QLineEdit):
                    widget.setText(str(val) if val else "")
                elif isinstance(widget, QComboBox):
                    idx = widget.findText(str(val) if val else "")
                    if idx >= 0:
                        widget.setCurrentIndex(idx)
                elif isinstance(widget, QDateEdit):
                    if val:
                        date_str = str(val).strip()
                        try:
                            parts = date_str.split("-")
                            if len(parts) == 3:
                                widget.setDate(QDate(int(parts[0]), int(parts[1]), int(parts[2])))
                            else:
                                widget.setDate(QDate.currentDate())
                        except Exception:
                            widget.setDate(QDate.currentDate())
                    else:
                        widget.setDate(QDate.currentDate())

    def _save_group(self, group_id):
        """Grup verilerini kaydet."""
        if not self.db:
            QMessageBox.warning(self, "Hata", "Veritabanı bağlantısı yok.")
            return

        grp = self._groups[group_id]
        update_data = {}
        
        # Verileri topla
        for key in grp["fields"]:
            widget = self._widgets[key]
            val = ""
            if isinstance(widget, QLineEdit):
                val = widget.text().strip()
            elif isinstance(widget, QComboBox):
                val = widget.currentText().strip()
            elif isinstance(widget, QDateEdit):
                val = widget.date().toString("yyyy-MM-dd")
            update_data[key] = val
            
        try:
            registry = RepositoryRegistry(self.db)
            repo = registry.get("Cihazlar")

            cihaz_id = self.cihaz_data.get("Cihazid")
            if not cihaz_id:
                raise ValueError("Cihaz ID bulunamadı.")

            # Güncelle
            update_data["Cihazid"] = cihaz_id  # PK ekle
            repo.update(update_data)
            
            # Local veriyi güncelle
            self.cihaz_data.update(update_data)
            
            # Düzenleme modunu kapat
            self._toggle_edit(group_id, False)
            
            # Signal gönder
            self.saved.emit()
            
            logger.info(f"Cihaz güncellendi ({group_id}): {cihaz_id}")
            QMessageBox.information(self, "Başarılı", "Değişiklikler kaydedildi.")
            
        except Exception as e:
            logger.error(f"Cihaz guncelleme hatasi ({group_id}): {e}")
            QMessageBox.critical(self, "Hata", f"Kaydetme hatasi: {e}")

    def load_data(self):
        """Veri yenileme (gerekirse)."""
        if self.db and self.cihaz_data.get("Cihazid"):
            try:
                registry = RepositoryRegistry(self.db)
                cihaz_repo = registry.get("Cihazlar")
                cihazlar = cihaz_repo.get_by_kod(self.cihaz_data.get("Cihazid"), "Cihazid")
                if cihazlar:
                    self.cihaz_data = cihazlar[0]
                    self._load_data()
            except Exception as e:
                logger.error(f"Veri yenileme hatasi: {e}")

    def set_embedded_mode(self, embedded: bool):
        """Gömülü mod ayarı."""
        pass
