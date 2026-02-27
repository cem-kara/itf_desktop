# -*- coding: utf-8 -*-
"""Ariza Girisi Form — Yeni arıza kaydı."""
from datetime import datetime

from PySide6.QtCore import QDate, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QGridLayout, QLabel, QLineEdit,
    QDateEdit, QComboBox, QTextEdit, QPushButton,
    QMessageBox, QGroupBox
)

from core.logger import logger
from database.repository_registry import RepositoryRegistry
from ui.styles.components import STYLES as S


class ArizaGirisForm(QWidget):
    """Yeni arıza girişi formu."""
    saved = Signal()

    def __init__(self, db=None, cihaz_id: str = None, action_guard=None, parent=None):
        super().__init__(parent)
        self._db       = db
        self._cihaz_id = cihaz_id or ""
        self._action_guard = action_guard
        self._setup_ui()

    def _setup_ui(self):
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

        # Cihazid — salt-okunur label (combo yok)
        grid.addWidget(self._lbl("Cihazid"), row, 0)
        self.lbl_cihazid = QLabel(self._cihaz_id or "—")
        self.lbl_cihazid.setStyleSheet(S["label"] + "font-weight:600;")
        grid.addWidget(self.lbl_cihazid, row, 1)
        row += 1

        # Başlangıç Tarihi
        grid.addWidget(self._lbl("Başlangıç Tarihi *"), row, 0)
        self.dt_baslangi = QDateEdit(QDate.currentDate())
        self.dt_baslangi.setCalendarPopup(True)
        self.dt_baslangi.setStyleSheet(S["input"])
        grid.addWidget(self.dt_baslangi, row, 1)
        row += 1

        # Saat
        grid.addWidget(self._lbl("Saat *"), row, 0)
        self.txt_saat = QLineEdit()
        self.txt_saat.setStyleSheet(S["input"])
        self.txt_saat.setPlaceholderText("HH:MM")
        grid.addWidget(self.txt_saat, row, 1)
        row += 1

        # Bildiren
        grid.addWidget(self._lbl("Bildiren"), row, 0)
        self.txt_bildiren = QLineEdit()
        self.txt_bildiren.setStyleSheet(S["input"])
        grid.addWidget(self.txt_bildiren, row, 1)
        row += 1

        # Arıza Tipi
        grid.addWidget(self._lbl("Arıza Tipi *"), row, 0)
        self.cmb_ariza_tipi = QComboBox()
        self.cmb_ariza_tipi.setEditable(True)
        self.cmb_ariza_tipi.setStyleSheet(S["combo"])
        self.cmb_ariza_tipi.addItems([
            "Elektrik Arızası", "Mekanik Arızası", "Yazılım Arızası",
            "Kalibrasyonu Yapılması Gerek", "Diğer"
        ])
        grid.addWidget(self.cmb_ariza_tipi, row, 1)
        row += 1

        # Öncelik
        grid.addWidget(self._lbl("Öncelik *"), row, 0)
        self.cmb_oncelik = QComboBox()
        self.cmb_oncelik.setStyleSheet(S["combo"])
        self.cmb_oncelik.addItems(["Düşük", "Orta", "Yüksek", "Kritik"])
        self.cmb_oncelik.setCurrentText("Orta")
        grid.addWidget(self.cmb_oncelik, row, 1)
        row += 1

        # Başlık
        grid.addWidget(self._lbl("Başlık *"), row, 0)
        self.txt_baslik = QLineEdit()
        self.txt_baslik.setStyleSheet(S["input"])
        self.txt_baslik.setPlaceholderText("Arıza açıklaması başlığı...")
        grid.addWidget(self.txt_baslik, row, 1)
        row += 1

        # Arıza Açıklaması
        grid.addWidget(self._lbl("Arıza Açıklaması"), row, 0)
        self.txt_aciklama = QTextEdit()
        self.txt_aciklama.setStyleSheet(S["input_text"])
        self.txt_aciklama.setFixedHeight(80)
        grid.addWidget(self.txt_aciklama, row, 1)
        row += 1

        # Durum
        grid.addWidget(self._lbl("Durum *"), row, 0)
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
        btn_kaydet.setStyleSheet(S.get("success_btn", S["refresh_btn"]))
        btn_kaydet.clicked.connect(self._save)
        if self._action_guard:
            self._action_guard.disable_if_unauthorized(btn_kaydet, "cihaz.write")
        btn_layout.addWidget(btn_kaydet)
        btn_temizle = QPushButton("Temizle")
        btn_temizle.setStyleSheet(S.get("cancel_btn", ""))
        btn_temizle.clicked.connect(self._clear)
        btn_layout.addWidget(btn_temizle)
        root.addLayout(btn_layout)

    @staticmethod
    def _lbl(text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet(S["label"])
        return lbl

    def set_cihaz_id(self, cihaz_id: str):
        """Cihaz ID'yi dışarıdan güncelle."""
        self._cihaz_id = cihaz_id or ""
        self.lbl_cihazid.setText(self._cihaz_id or "—")

    def _save(self):
        if self._action_guard and not self._action_guard.check_and_warn(
            self, "cihaz.write", "Ariza Kaydetme"
        ):
            return
        cihaz_id = self._cihaz_id.strip()
        if not cihaz_id:
            QMessageBox.warning(self, "Hata", "Cihaz ID boş!")
            return
        if not self.txt_baslik.text().strip():
            QMessageBox.warning(self, "Hata", "Lütfen arıza başlığını girin!")
            return
        if not self.txt_saat.text().strip():
            QMessageBox.warning(self, "Hata", "Lütfen saati girin (HH:MM)!")
            return
        if not self.cmb_ariza_tipi.currentText().strip():
            QMessageBox.warning(self, "Hata", "Lütfen arıza türünü seçin!")
            return
        try:
            if not self._db:
                raise Exception("Veritabanı bağlantısı yok!")
            ariza_id = f"{cihaz_id}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
            record = {
                "Arizaid":         ariza_id,
                "Cihazid":         cihaz_id,
                "BaslangicTarihi": self.dt_baslangi.date().toString("yyyy-MM-dd"),
                "Saat":            self.txt_saat.text().strip(),
                "Bildiren":        self.txt_bildiren.text().strip(),
                "ArizaTipi":       self.cmb_ariza_tipi.currentText().strip(),
                "Oncelik":         self.cmb_oncelik.currentText().strip(),
                "Baslik":          self.txt_baslik.text().strip(),
                "ArizaAcikla":     self.txt_aciklama.toPlainText().strip(),
                "Durum":           self.cmb_durum.currentText().strip(),
                "Rapor":           "",
            }
            RepositoryRegistry(self._db).get("Cihaz_Ariza").insert(record)
            logger.info(f"Arıza kaydedildi: {ariza_id}")
            self._clear()
            self.saved.emit()
        except Exception as e:
            logger.error(f"Arıza kaydedilemedi: {e}")
            QMessageBox.critical(self, "Hata", f"Arıza kaydedilemedi:\n{e}")

    def _clear(self):
        self.dt_baslangi.setDate(QDate.currentDate())
        self.txt_saat.clear()
        self.txt_bildiren.clear()
        self.cmb_ariza_tipi.setCurrentIndex(0)
        self.cmb_oncelik.setCurrentText("Orta")
        self.txt_baslik.clear()
        self.txt_aciklama.clear()
        self.cmb_durum.setCurrentText("Açık")
