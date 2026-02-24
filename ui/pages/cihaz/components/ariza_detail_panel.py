# -*- coding: utf-8 -*-
"""Cihaz Arıza Kartı — arıza ve işlem yönetimi modülü."""
from typing import Optional, Dict, Any
import os
import subprocess
import platform
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel,
    QPushButton, QTextEdit, QGridLayout, QScrollArea, QListWidget, QMessageBox
)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QCursor

from core.logger import logger
from core.date_utils import to_ui_date
from core.paths import DATA_DIR
from ui.styles import DarkTheme
from ui.styles.components import STYLES
from ui.styles.icons import IconRenderer
from ui.pages.cihaz.ariza_kayit import ArizaKayitForm

C = DarkTheme


class CihazArizaKart(QWidget):
    """Cihaz merkez içinde ARIZA sekmesi ve detay paneli yönetimi."""
    
    ariza_islem_form_istegi = Signal(str)  # ariza_id
    islem_secildi = Signal(dict)            # islem_data

    def __init__(self, db, cihaz_id: str, parent=None):
        super().__init__(parent)
        self.db = db
        self.cihaz_id = cihaz_id
        self._islem_detail_labels = {}
        self._lbl_yapilan = None
        self._lbl_rapor = None
        self.islem_detail_container = None

    def build_detail_panel(self) -> QFrame:
        """İşlem detayları paneli + açılır/kapanır UI."""
        self.islem_detail_container = QFrame()
        self.islem_detail_container.setVisible(False)
        self.islem_detail_container.setStyleSheet(
            f"background:{C.BG_TERTIARY}; border-bottom:1px solid {C.BORDER_PRIMARY};"
        )
        detail_lay = QVBoxLayout(self.islem_detail_container)
        detail_lay.setContentsMargins(12, 10, 12, 10)
        detail_lay.setSpacing(8)
        
        # Başlık + Kapat butonu
        detail_hdr = QHBoxLayout()
        detail_hdr.setSpacing(6)
        lbl_detail_title = QLabel("İşlem Detayları")
        lbl_detail_title.setStyleSheet(STYLES["section_label"])
        detail_hdr.addWidget(lbl_detail_title)
        detail_hdr.addStretch()
        
        btn_detail_kapat = QPushButton()
        btn_detail_kapat.setFixedSize(20, 20)
        btn_detail_kapat.setStyleSheet("background:transparent; border:none;")
        btn_detail_kapat.setCursor(QCursor(Qt.PointingHandCursor))
        btn_detail_kapat.clicked.connect(lambda: self.islem_detail_container.setVisible(False))
        try:
            IconRenderer.set_button_icon(btn_detail_kapat, "x", color=C.TEXT_MUTED, size=11)
        except Exception:
            btn_detail_kapat.setText("✕")
        detail_hdr.addWidget(btn_detail_kapat)
        detail_lay.addLayout(detail_hdr)
        
        # Detay alanları
        detail_grid = QGridLayout()
        detail_grid.setContentsMargins(0, 0, 0, 0)
        detail_grid.setHorizontalSpacing(10)
        detail_grid.setVerticalSpacing(6)
        
        self._islem_detail_labels = {}
        for i, key in enumerate(["Tarih", "Saat", "IslemYapan", "IslemTuru", "YeniDurum"]):
            label_name = {
                "Tarih": "Tarih",
                "Saat": "Saat",
                "IslemYapan": "İşlem Yapan",
                "IslemTuru": "İşlem Türü",
                "YeniDurum": "Yeni Durum"
            }.get(key, key)
            lbl_header = QLabel(label_name)
            lbl_header.setStyleSheet(STYLES.get("label", "font-weight:600; font-size:11px;"))
            lbl_value = QLabel("—")
            lbl_value.setStyleSheet(STYLES.get("info_label", "font-size:11px;"))
            lbl_value.setWordWrap(True)
            detail_grid.addWidget(lbl_header, i, 0)
            detail_grid.addWidget(lbl_value, i, 1)
            self._islem_detail_labels[key] = lbl_value
        
        # Yapılan İşlem
        lbl_yapilan_h = QLabel("Yapılan İşlem")
        lbl_yapilan_h.setStyleSheet(STYLES.get("label", "font-weight:600; font-size:11px;"))
        detail_grid.addWidget(lbl_yapilan_h, 5, 0, 1, 2)
        
        self._lbl_yapilan = QTextEdit()
        self._lbl_yapilan.setReadOnly(True)
        self._lbl_yapilan.setStyleSheet(STYLES.get("input_text", ""))
        self._lbl_yapilan.setFixedHeight(60)
        detail_grid.addWidget(self._lbl_yapilan, 6, 0, 1, 2)
        
        # Rapor
        lbl_rapor_h = QLabel("Rapor")
        lbl_rapor_h.setStyleSheet(STYLES.get("label", "font-weight:600; font-size:11px;"))
        detail_grid.addWidget(lbl_rapor_h, 7, 0, 1, 2)
        
        self._lbl_rapor = QTextEdit()
        self._lbl_rapor.setReadOnly(True)
        self._lbl_rapor.setStyleSheet(STYLES.get("input_text", ""))
        self._lbl_rapor.setFixedHeight(60)
        detail_grid.addWidget(self._lbl_rapor, 8, 0, 1, 2)
        
        # Belgeler
        lbl_belgeler_h = QLabel("İlgili Belgeler (Çift tıkla: Aç)")
        lbl_belgeler_h.setStyleSheet(STYLES.get("label", "font-weight:600; font-size:11px;"))
        detail_grid.addWidget(lbl_belgeler_h, 9, 0, 1, 2)
        
        self.list_belgeler = QListWidget()
        self.list_belgeler.setStyleSheet(STYLES.get("input", ""))
        self.list_belgeler.setFixedHeight(70)
        self.list_belgeler.itemDoubleClicked.connect(self._open_belge)
        detail_grid.addWidget(self.list_belgeler, 10, 0, 1, 2)
        
        detail_lay.addLayout(detail_grid)
        
        return self.islem_detail_container

    def on_ariza_islem_form_istegi(self, ariza_id: str):
        """Arıza tablosundan sağ tık → form açılması."""
        self.ariza_islem_form_istegi.emit(ariza_id)

    def on_islem_secildi(self, islem_data: Dict[str, Any]):
        """İşlem tablosundan seçilince detayları panelde göster."""
        if not self.islem_detail_container:
            return
        
        self.islem_detail_container.setVisible(True)
        
        # Detay alanlarını doldur
        for key, lbl in self._islem_detail_labels.items():
            value = islem_data.get(key, "")
            if key == "Tarih":
                value = to_ui_date(value, "—")
            lbl.setText(str(value) if value else "—")
        
        # Yapılan İşlem
        yapilan = islem_data.get("YapilanIslem", "")
        self._lbl_yapilan.setText(str(yapilan) if yapilan else "—")
        
        # Rapor
        rapor = islem_data.get("Rapor", "")
        self._lbl_rapor.setText(str(rapor) if rapor else "—")
        
        # İlgili belgeleri yükle
        islem_id = islem_data.get("IslemID", "")
        self._load_belgeler_for_islem(islem_id)

    def hide_detail_panel(self):
        """Detail panelini gizle."""
        if self.islem_detail_container:
            self.islem_detail_container.setVisible(False)
    
    def _load_belgeler_for_islem(self, islem_id: str):
        """işlem ID'sine göre ilgili belgeleri Cihaz_Belgeler tablosundan yükle."""
        self.list_belgeler.clear()
        if not self.db or not islem_id:
            return
        
        try:
            repo = self.db.get_repository("Cihaz_Belgeler")
            all_belgeler = repo.get_all()
            
            # BelgeAciklama'da işlem ID'si geçen belgeleri filtrele
            related = [b for b in all_belgeler if islem_id in str(b.get("BelgeAciklama", ""))]
            
            for belge in related:
                belge_adi = belge.get("BelgeAdi", "")
                belge_path = belge.get("BelgePath", "")
                # Liste item'ına belge adı göster, data olarak tam yol sakla
                item_text = f"{belge_adi} ({belge.get('BelgeTuru', '')})"
                item = self.list_belgeler.addItem(item_text)
                # Item'a full path'i userData olarak ekle
                item_widget = self.list_belgeler.item(self.list_belgeler.count() - 1)
                item_widget.setData(Qt.UserRole, belge_path)
                
        except Exception as e:
            logger.error(f"Belgeler yüklenemedi: {e}")
    
    def _open_belge(self, item):
        """Belgeyi sistem varsayılan uygulamasıyla aç."""
        belge_path = item.data(Qt.UserRole)
        if not belge_path:
            return
        
        full_path = Path(DATA_DIR) / "offline_uploads" / "cihazlar" / belge_path
        
        if not full_path.exists():
            QMessageBox.warning(self, "Hata", f"Belge bulunamadı:\n{full_path}")
            return
        
        try:
            if platform.system() == "Windows":
                os.startfile(str(full_path))
            elif platform.system() == "Darwin":  # macOS
                subprocess.run(["open", str(full_path)], check=True)
            else:  # Linux
                subprocess.run(["xdg-open", str(full_path)], check=True)
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Belge açılamadı:\n{e}")
            logger.error(f"Belge açma hatası: {e}")


class CihazArizaPanel(QWidget):
    """Cihaz bazlı arıza kayıt paneli (ArizaKayitForm wrapper)."""

    def __init__(self, db, cihaz_id: Optional[str], parent=None):
        super().__init__(parent)
        self._db = db
        self._cihaz_id = cihaz_id

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.ariza_form = ArizaKayitForm(db=self._db, cihaz_id=self._cihaz_id)
        layout.addWidget(self.ariza_form)

        # CihazMerkez uyumlulugu: islem_penceresi'ni disariya ac
        self.islem_penceresi = getattr(self.ariza_form, "islem_penceresi", None)

    def set_cihaz_id(self, cihaz_id: Optional[str]):
        self._cihaz_id = cihaz_id
        if hasattr(self.ariza_form, "set_cihaz_id"):
            self.ariza_form.set_cihaz_id(cihaz_id)

    def load_data(self):
        if hasattr(self.ariza_form, "_load_data"):
            self.ariza_form._load_data()
