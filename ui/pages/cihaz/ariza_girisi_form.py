# -*- coding: utf-8 -*-
"""Ariza Girisi Form — Yeni arıza kaydı."""
from typing import Optional
from datetime import datetime

from PySide6.QtCore import Qt, QDate, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QGridLayout, QLabel, QLineEdit,
    QDateEdit, QTimeEdit, QComboBox, QTextEdit, QPushButton,
    QMessageBox, QGroupBox
)

from core.date_utils import to_ui_date
from core.logger import logger
from database.repository_registry import RepositoryRegistry
from ui.styles.components import STYLES as S


class ArizaGirisForm(QWidget):
    """Yeni arıza girişi formu."""
    saved = Signal()

    def __init__(self, db=None, parent=None):
        super().__init__(parent)
        self._db = db
        self._setup_ui()
        self._load_cihaz_list()

    def _setup_ui(self):
        """Form UI'sini oluştur."""
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(10)

        form = QGroupBox("Yeni Arıza Kaydı")
        form.setStyleSheet(S["group"])
        grid = QGridLayout(form)
        grid.setContentsMargins(12, 12, 12, 12)
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(8)

        row = 0

        # Cihazid (ComboBox - Cihaz tablosundan)
        lbl = QLabel("Cihazid *")
        lbl.setStyleSheet(S["label"])
        grid.addWidget(lbl, row, 0)

        self.cmb_cihazid = QComboBox()
        self.cmb_cihazid.setStyleSheet(S["combo"])
        grid.addWidget(self.cmb_cihazid, row, 1)
        row += 1

        # BaslangicTarihi
        lbl = QLabel("Başlangıç Tarihi *")
        lbl.setStyleSheet(S["label"])
        grid.addWidget(lbl, row, 0)

        self.dt_baslangi = QDateEdit()
        self.dt_baslangi.setDate(QDate.currentDate())
        self.dt_baslangi.setCalendarPopup(True)
        self.dt_baslangi.setStyleSheet(S["input"])
        grid.addWidget(self.dt_baslangi, row, 1)
        row += 1

        # Saat
        lbl = QLabel("Saat *")
        lbl.setStyleSheet(S["label"])
        grid.addWidget(lbl, row, 0)

        self.txt_saat = QLineEdit()
        self.txt_saat.setStyleSheet(S["input"])
        self.txt_saat.setPlaceholderText("HH:MM")
        grid.addWidget(self.txt_saat, row, 1)
        row += 1

        # Bildiren
        lbl = QLabel("Bildiren")
        lbl.setStyleSheet(S["label"])
        grid.addWidget(lbl, row, 0)

        self.txt_bildiren = QLineEdit()
        self.txt_bildiren.setStyleSheet(S["input"])
        grid.addWidget(self.txt_bildiren, row, 1)
        row += 1

        # ArizaTipi
        lbl = QLabel("Arıza Tipi *")
        lbl.setStyleSheet(S["label"])
        grid.addWidget(lbl, row, 0)

        self.cmb_ariza_tipi = QComboBox()
        self.cmb_ariza_tipi.setEditable(True)
        self.cmb_ariza_tipi.setStyleSheet(S["combo"])
        self.cmb_ariza_tipi.addItems([
            "Elektrik Arızası",
            "Mekanik Arızası",
            "Yazılım Arızası",
            "Kalibrasyonu Yapılması Gerek",
            "Diğer"
        ])
        grid.addWidget(self.cmb_ariza_tipi, row, 1)
        row += 1

        # Oncelik
        lbl = QLabel("Öncelik *")
        lbl.setStyleSheet(S["label"])
        grid.addWidget(lbl, row, 0)

        self.cmb_oncelik = QComboBox()
        self.cmb_oncelik.setStyleSheet(S["combo"])
        self.cmb_oncelik.addItems(["Düşük", "Orta", "Yüksek", "Kritik"])
        self.cmb_oncelik.setCurrentText("Orta")
        grid.addWidget(self.cmb_oncelik, row, 1)
        row += 1

        # Baslik
        lbl = QLabel("Başlık *")
        lbl.setStyleSheet(S["label"])
        grid.addWidget(lbl, row, 0)

        self.txt_baslik = QLineEdit()
        self.txt_baslik.setStyleSheet(S["input"])
        self.txt_baslik.setPlaceholderText("Arıza açıklaması başlığı...")
        grid.addWidget(self.txt_baslik, row, 1)
        row += 1

        # ArizaAcikla
        lbl = QLabel("Arıza Açıklaması")
        lbl.setStyleSheet(S["label"])
        grid.addWidget(lbl, row, 0)

        self.txt_aciklama = QTextEdit()
        self.txt_aciklama.setStyleSheet(S["input_text"])
        self.txt_aciklama.setFixedHeight(80)
        grid.addWidget(self.txt_aciklama, row, 1)
        row += 1

        # Durum
        lbl = QLabel("Durum *")
        lbl.setStyleSheet(S["label"])
        grid.addWidget(lbl, row, 0)

        self.cmb_durum = QComboBox()
        self.cmb_durum.setStyleSheet(S["combo"])
        self.cmb_durum.addItems(["Açık", "Yakında Kapanacak", "Kapalı"])
        self.cmb_durum.setCurrentText("Açık")
        grid.addWidget(self.cmb_durum, row, 1)
        row += 1

        root.addWidget(form)

        # Butonlar
        btn_layout = QVBoxLayout()
        btn_layout.setSpacing(8)

        btn_kaydet = QPushButton("Kaydet")
        btn_kaydet.setStyleSheet(S["success_btn"] if "success_btn" in S else S["refresh_btn"])
        btn_kaydet.clicked.connect(self._save)
        btn_layout.addWidget(btn_kaydet)

        btn_temizle = QPushButton("Temizle")
        btn_temizle.setStyleSheet(S["cancel_btn"] if "cancel_btn" in S else "")
        btn_temizle.clicked.connect(self._clear)
        btn_layout.addWidget(btn_temizle)

        root.addLayout(btn_layout)

    def _load_cihaz_list(self):
        """Cihaz listesini yükle."""
        if not self._db:
            return

        try:
            repo = RepositoryRegistry(self._db).get("Cihaz")
            cihazlar = repo.get_all()
            
            cihaz_list = []
            for cihaz in cihazlar:
                cihaz_id = cihaz.get("Cihazid", "")
                if cihaz_id:
                    cihaz_list.append(cihaz_id)
            
            self.cmb_cihazid.addItems(sorted(cihaz_list))
        except Exception as e:
            logger.error(f"Cihaz listesi yüklenemedi: {e}")

    def _save(self):
        """Arıza kaydını kaydet."""
        # Validasyon
        if not self.cmb_cihazid.currentText().strip():
            QMessageBox.warning(self, "Hata", "Lütfen bir cihaz seçin!")
            return

        if not self.txt_baslik.text().strip():
            QMessageBox.warning(self, "Hata", "Lütfen arıza başlığını girin!")
            return

        if not self.txt_saat.text().strip():
            QMessageBox.warning(self, "Hata", "Lütfen saati girin (HH:MM formatında)!")
            return

        if not self.cmb_ariza_tipi.currentText().strip():
            QMessageBox.warning(self, "Hata", "Lütfen arıza türünü seçin!")
            return

        try:
            if not self._db:
                raise Exception("Veritabanı bağlantısı yok!")

            repo = RepositoryRegistry(self._db).get("Cihaz_Ariza")
            
            # Arıza ID oluştur (Cihazid-Timestamp)
            cihaz_id = self.cmb_cihazid.currentText().strip()
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            ariza_id = f"{cihaz_id}-{timestamp}"
            
            # Tarih ve saati birleştir
            tarih = self.dt_baslangi.date().toString("yyyy-MM-dd")
            saat = self.txt_saat.text().strip()
            
            # Yeni kayıt
            record = {
                "Arizaid": ariza_id,
                "Cihazid": cihaz_id,
                "BaslangicTarihi": tarih,
                "Saat": saat,
                "Bildiren": self.txt_bildiren.text().strip() or "",
                "ArizaTipi": self.cmb_ariza_tipi.currentText().strip(),
                "Oncelik": self.cmb_oncelik.currentText().strip(),
                "Baslik": self.txt_baslik.text().strip(),
                "ArizaAcikla": self.txt_aciklama.toPlainText().strip() or "",
                "Durum": self.cmb_durum.currentText().strip(),
                "Rapor": ""  # İleride doldurulabilir
            }
            
            repo.insert(record)
            self._db.commit()
            
            logger.info(f"Arıza kaydedildi: {ariza_id}")
            self._clear()
            self.saved.emit()

        except Exception as e:
            logger.error(f"Arıza kaydedilemedi: {e}")
            QMessageBox.critical(self, "Hata", f"Arıza kaydedilemedi:\n{str(e)}")

    def _clear(self):
        """Form alanlarını temizle."""
        self.cmb_cihazid.setCurrentIndex(0) if self.cmb_cihazid.count() > 0 else None
        self.dt_baslangi.setDate(QDate.currentDate())
        self.txt_saat.clear()
        self.txt_bildiren.clear()
        self.cmb_ariza_tipi.setCurrentIndex(0)
        self.cmb_oncelik.setCurrentText("Orta")
        self.txt_baslik.clear()
        self.txt_aciklama.clear()
        self.cmb_durum.setCurrentText("Açık")
