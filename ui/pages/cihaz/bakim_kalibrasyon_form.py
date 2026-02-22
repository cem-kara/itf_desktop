# -*- coding: utf-8 -*-
"""Bakim ve Kalibrasyon kayit formlari."""
from typing import Optional
from datetime import datetime

from PySide6.QtCore import QDate, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QGridLayout,
    QLabel, QLineEdit, QComboBox, QDateEdit, QTextEdit, QPushButton
)

from core.logger import logger
from database.repository_registry import RepositoryRegistry
from ui.styles import DarkTheme
from ui.styles.components import STYLES as S
from ui.styles.icons import IconRenderer


class BakimKayitForm(QWidget):
    saved = Signal()

    def __init__(self, db=None, cihaz_id: Optional[str] = None, parent=None):
        super().__init__(parent)
        self._db = db
        self._cihaz_id = cihaz_id
        self._setup_ui()

    def set_cihaz_id(self, cihaz_id: Optional[str]):
        self._cihaz_id = cihaz_id

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(10)

        form = QGroupBox("Bakim Kaydi")
        form.setStyleSheet(S["group"])
        grid = QGridLayout(form)
        grid.setContentsMargins(12, 12, 12, 12)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(8)

        self.txt_periyot = QLineEdit()
        self.txt_periyot.setStyleSheet(S["input"])
        self._add_row(grid, 0, "Bakim Periyodu", self.txt_periyot)

        self.txt_sira = QLineEdit()
        self.txt_sira.setStyleSheet(S["input"])
        self._add_row(grid, 1, "Bakim Sirasi", self.txt_sira)

        self.dt_plan = QDateEdit(QDate.currentDate())
        self.dt_plan.setCalendarPopup(True)
        self.dt_plan.setDisplayFormat("dd.MM.yyyy")
        self.dt_plan.setStyleSheet(S["date"])
        self._add_row(grid, 2, "Planlanan Tarih", self.dt_plan)

        self.txt_bakim = QLineEdit()
        self.txt_bakim.setStyleSheet(S["input"])
        self._add_row(grid, 3, "Bakim", self.txt_bakim)

        self.cmb_durum = QComboBox()
        self.cmb_durum.setStyleSheet(S["combo"])
        self.cmb_durum.addItems(["Planli", "Yapildi", "Gecikmis"])
        self._add_row(grid, 4, "Durum", self.cmb_durum)

        self.dt_bakim = QDateEdit(QDate.currentDate())
        self.dt_bakim.setCalendarPopup(True)
        self.dt_bakim.setDisplayFormat("dd.MM.yyyy")
        self.dt_bakim.setStyleSheet(S["date"])
        self._add_row(grid, 5, "Bakim Tarihi", self.dt_bakim)

        self.txt_tip = QLineEdit()
        self.txt_tip.setStyleSheet(S["input"])
        self._add_row(grid, 6, "Bakim Tipi", self.txt_tip)

        self.txt_islemler = QTextEdit()
        self.txt_islemler.setStyleSheet(S["input_text"])
        self.txt_islemler.setFixedHeight(70)
        self._add_row(grid, 7, "Yapilan Islemler", self.txt_islemler)

        self.txt_aciklama = QTextEdit()
        self.txt_aciklama.setStyleSheet(S["input_text"])
        self.txt_aciklama.setFixedHeight(60)
        self._add_row(grid, 8, "Aciklama", self.txt_aciklama)

        self.txt_teknisyen = QLineEdit()
        self.txt_teknisyen.setStyleSheet(S["input"])
        self._add_row(grid, 9, "Teknisyen", self.txt_teknisyen)

        self.txt_rapor = QTextEdit()
        self.txt_rapor.setStyleSheet(S["input_text"])
        self.txt_rapor.setFixedHeight(60)
        self._add_row(grid, 10, "Rapor", self.txt_rapor)

        root.addWidget(form)

        btns = QHBoxLayout()
        btns.addStretch()

        self.btn_clear = QPushButton("Temizle")
        self.btn_clear.setStyleSheet(S["btn_refresh"])
        self.btn_clear.clicked.connect(self._clear)
        btns.addWidget(self.btn_clear)

        self.btn_save = QPushButton("Kaydet")
        self.btn_save.setStyleSheet(S["action_btn"])
        try:
            IconRenderer.set_button_icon(self.btn_save, "save",
                                         color=DarkTheme.BTN_PRIMARY_TEXT, size=14)
        except Exception:
            pass
        self.btn_save.clicked.connect(self._save)
        btns.addWidget(self.btn_save)

        root.addLayout(btns)

    def _add_row(self, grid, row, label, widget):
        lbl = QLabel(label)
        lbl.setStyleSheet(S["label"])
        grid.addWidget(lbl, row, 0)
        grid.addWidget(widget, row, 1)

    def _save(self):
        if not self._db or not self._cihaz_id:
            return

        planid = f"{self._cihaz_id}-BK-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        data = {
            "Planid": planid,
            "Cihazid": self._cihaz_id,
            "BakimPeriyodu": self.txt_periyot.text().strip(),
            "BakimSirasi": self.txt_sira.text().strip(),
            "PlanlananTarih": self.dt_plan.date().toString("yyyy-MM-dd"),
            "Bakim": self.txt_bakim.text().strip(),
            "Durum": self.cmb_durum.currentText().strip(),
            "BakimTarihi": self.dt_bakim.date().toString("yyyy-MM-dd"),
            "BakimTipi": self.txt_tip.text().strip(),
            "YapilanIslemler": self.txt_islemler.toPlainText().strip(),
            "Aciklama": self.txt_aciklama.toPlainText().strip(),
            "Teknisyen": self.txt_teknisyen.text().strip(),
            "Rapor": self.txt_rapor.toPlainText().strip(),
        }

        try:
            repo = RepositoryRegistry(self._db).get("Periyodik_Bakim")
            repo.insert(data)
            self.saved.emit()
            self._clear()
        except Exception as e:
            logger.error(f"Bakim kaydi kaydedilemedi: {e}")

    def _clear(self):
        self.txt_periyot.clear()
        self.txt_sira.clear()
        self.dt_plan.setDate(QDate.currentDate())
        self.txt_bakim.clear()
        self.cmb_durum.setCurrentIndex(0)
        self.dt_bakim.setDate(QDate.currentDate())
        self.txt_tip.clear()
        self.txt_islemler.clear()
        self.txt_aciklama.clear()
        self.txt_teknisyen.clear()
        self.txt_rapor.clear()


class KalibrasyonKayitForm(QWidget):
    saved = Signal()

    def __init__(self, db=None, cihaz_id: Optional[str] = None, parent=None):
        super().__init__(parent)
        self._db = db
        self._cihaz_id = cihaz_id
        self._setup_ui()

    def set_cihaz_id(self, cihaz_id: Optional[str]):
        self._cihaz_id = cihaz_id

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(10)

        form = QGroupBox("Kalibrasyon Kaydi")
        form.setStyleSheet(S["group"])
        grid = QGridLayout(form)
        grid.setContentsMargins(12, 12, 12, 12)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(8)

        self.txt_firma = QLineEdit()
        self.txt_firma.setStyleSheet(S["input"])
        self._add_row(grid, 0, "Firma", self.txt_firma)

        self.txt_sertifika = QLineEdit()
        self.txt_sertifika.setStyleSheet(S["input"])
        self._add_row(grid, 1, "Sertifika No", self.txt_sertifika)

        self.dt_yapilan = QDateEdit(QDate.currentDate())
        self.dt_yapilan.setCalendarPopup(True)
        self.dt_yapilan.setDisplayFormat("dd.MM.yyyy")
        self.dt_yapilan.setStyleSheet(S["date"])
        self._add_row(grid, 2, "Yapilan Tarih", self.dt_yapilan)

        self.txt_gecerlilik = QLineEdit()
        self.txt_gecerlilik.setStyleSheet(S["input"])
        self._add_row(grid, 3, "Gecerlilik", self.txt_gecerlilik)

        self.dt_bitis = QDateEdit(QDate.currentDate())
        self.dt_bitis.setCalendarPopup(True)
        self.dt_bitis.setDisplayFormat("dd.MM.yyyy")
        self.dt_bitis.setStyleSheet(S["date"])
        self._add_row(grid, 4, "Bitis Tarihi", self.dt_bitis)

        self.cmb_durum = QComboBox()
        self.cmb_durum.setStyleSheet(S["combo"])
        self.cmb_durum.addItems(["Gecerli", "Gecersiz"])
        self._add_row(grid, 5, "Durum", self.cmb_durum)

        self.txt_dosya = QLineEdit()
        self.txt_dosya.setStyleSheet(S["input"])
        self._add_row(grid, 6, "Dosya", self.txt_dosya)

        self.txt_aciklama = QTextEdit()
        self.txt_aciklama.setStyleSheet(S["input_text"])
        self.txt_aciklama.setFixedHeight(80)
        self._add_row(grid, 7, "Aciklama", self.txt_aciklama)

        root.addWidget(form)

        btns = QHBoxLayout()
        btns.addStretch()

        self.btn_clear = QPushButton("Temizle")
        self.btn_clear.setStyleSheet(S["btn_refresh"])
        self.btn_clear.clicked.connect(self._clear)
        btns.addWidget(self.btn_clear)

        self.btn_save = QPushButton("Kaydet")
        self.btn_save.setStyleSheet(S["action_btn"])
        try:
            IconRenderer.set_button_icon(self.btn_save, "save",
                                         color=DarkTheme.BTN_PRIMARY_TEXT, size=14)
        except Exception:
            pass
        self.btn_save.clicked.connect(self._save)
        btns.addWidget(self.btn_save)

        root.addLayout(btns)

    def _add_row(self, grid, row, label, widget):
        lbl = QLabel(label)
        lbl.setStyleSheet(S["label"])
        grid.addWidget(lbl, row, 0)
        grid.addWidget(widget, row, 1)

    def _save(self):
        if not self._db or not self._cihaz_id:
            return

        kalid = f"{self._cihaz_id}-KL-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        data = {
            "Kalid": kalid,
            "Cihazid": self._cihaz_id,
            "Firma": self.txt_firma.text().strip(),
            "SertifikaNo": self.txt_sertifika.text().strip(),
            "YapilanTarih": self.dt_yapilan.date().toString("yyyy-MM-dd"),
            "Gecerlilik": self.txt_gecerlilik.text().strip(),
            "BitisTarihi": self.dt_bitis.date().toString("yyyy-MM-dd"),
            "Durum": self.cmb_durum.currentText().strip(),
            "Dosya": self.txt_dosya.text().strip(),
            "Aciklama": self.txt_aciklama.toPlainText().strip(),
        }

        try:
            repo = RepositoryRegistry(self._db).get("Kalibrasyon")
            repo.insert(data)
            self.saved.emit()
            self._clear()
        except Exception as e:
            logger.error(f"Kalibrasyon kaydi kaydedilemedi: {e}")

    def _clear(self):
        self.txt_firma.clear()
        self.txt_sertifika.clear()
        self.dt_yapilan.setDate(QDate.currentDate())
        self.txt_gecerlilik.clear()
        self.dt_bitis.setDate(QDate.currentDate())
        self.cmb_durum.setCurrentIndex(0)
        self.txt_dosya.clear()
        self.txt_aciklama.clear()
