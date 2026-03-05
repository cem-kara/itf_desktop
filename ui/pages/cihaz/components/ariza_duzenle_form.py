from core.di import get_cihaz_service as _get_cihaz_service
# -*- coding: utf-8 -*-
from typing import Dict, cast, Any

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QGroupBox, QGridLayout, QComboBox, QLineEdit,
    QTextEdit, QLabel, QHBoxLayout, QPushButton, QMessageBox,
)

from core.logger import logger

from ui.styles.components import STYLES as S


class ArizaDuzenleForm(QWidget):
    """Mevcut arızayı düzenleme formu."""
    saved = Signal()

    def __init__(self, db=None, ariza_data: Dict | None = None, parent=None):
        super().__init__(parent)
        self._db = db
        self._ariza_data = ariza_data or {}
        self._ariza_id = self._ariza_data.get("Arizaid", "")
        self._setup_ui()
        self._load_form()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(10)

        form = QGroupBox("Arıza Düzenleme")
        form.setStyleSheet(S["group"])
        grid = QGridLayout(form)
        grid.setContentsMargins(12, 12, 12, 12)
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(8)

        row = 0

        grid.addWidget(self._lbl("Arıza ID"), row, 0)
        self.lbl_arizaid = QLabel(self._ariza_id)
        self.lbl_arizaid.setStyleSheet(S["label"] + "font-weight:600;")
        grid.addWidget(self.lbl_arizaid, row, 1)
        row += 1

        grid.addWidget(self._lbl("Arıza Tipi *"), row, 0)
        self.cmb_ariza_tipi = QComboBox()
        self.cmb_ariza_tipi.setEditable(True)
        self.cmb_ariza_tipi.setStyleSheet(S["combo"])
        self.cmb_ariza_tipi.addItems([
            "Elektrik Arızası", "Mekanik Arızası", "Yazılım Arızası",
            "Kalibrasyonu Yapılması Gerek", "Diğer",
        ])
        grid.addWidget(self.cmb_ariza_tipi, row, 1)
        row += 1

        grid.addWidget(self._lbl("Öncelik *"), row, 0)
        self.cmb_oncelik = QComboBox()
        self.cmb_oncelik.setStyleSheet(S["combo"])
        self.cmb_oncelik.addItems(["Düşük", "Orta", "Yüksek", "Kritik"])
        grid.addWidget(self.cmb_oncelik, row, 1)
        row += 1

        grid.addWidget(self._lbl("Başlık *"), row, 0)
        self.txt_baslik = QLineEdit()
        self.txt_baslik.setStyleSheet(S["input"])
        grid.addWidget(self.txt_baslik, row, 1)
        row += 1

        grid.addWidget(self._lbl("Açıklama"), row, 0)
        self.txt_aciklama = QTextEdit()
        self.txt_aciklama.setStyleSheet(S["input_text"])
        self.txt_aciklama.setFixedHeight(100)
        grid.addWidget(self.txt_aciklama, row, 1)
        row += 1

        grid.addWidget(self._lbl("Durum"), row, 0)
        self.cmb_durum = QComboBox()
        self.cmb_durum.setStyleSheet(S["combo"])
        self.cmb_durum.addItems(["Açık", "Devam Ediyor", "Kapalı", "Hatalı Giriş"])
        grid.addWidget(self.cmb_durum, row, 1)

        root.addWidget(form)

        btn_lay = QHBoxLayout()
        btn_lay.setSpacing(8)

        btn_kaydet = QPushButton("Kaydet")
        btn_kaydet.setStyleSheet(cast(str, S.get("success_btn") or S.get("refresh_btn", "")))
        btn_kaydet.clicked.connect(self._save)
        btn_lay.addWidget(btn_kaydet)

        btn_iptal = QPushButton("İptal")
        btn_iptal.setStyleSheet(cast(str, S.get("cancel_btn", "") or ""))
        btn_iptal.clicked.connect(self._cancel)
        btn_lay.addWidget(btn_iptal)

        root.addLayout(btn_lay)

    def _lbl(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet(S["label"])
        return lbl

    def _load_form(self):
        self.cmb_ariza_tipi.setCurrentText(self._ariza_data.get("ArizaTipi", "Diğer"))
        self.cmb_oncelik.setCurrentText(self._ariza_data.get("Oncelik", "Orta"))
        self.txt_baslik.setText(self._ariza_data.get("Baslik", ""))
        self.txt_aciklama.setPlainText(self._ariza_data.get("Aciklama", ""))
        self.cmb_durum.setCurrentText(self._ariza_data.get("Durum", "Açık"))

    def _save(self):
        if not self._ariza_id or not self._db:
            return

        ariza_tipi = self.cmb_ariza_tipi.currentText().strip()
        oncelik = self.cmb_oncelik.currentText().strip()
        baslik = self.txt_baslik.text().strip()
        aciklama = self.txt_aciklama.toPlainText().strip()
        durum = self.cmb_durum.currentText().strip()

        if not baslik:
            QMessageBox.warning(self, "Hata", "Lütfen başlık girin.")
            return

        data = {
            "ArizaTipi": ariza_tipi,
            "Oncelik": oncelik,
            "Baslik": baslik,
            "Aciklama": aciklama,
            "Durum": durum,
        }

        try:
            svc = _get_cihaz_service(self._db)
            svc.ariza_guncelle(self._ariza_id, data)
            logger.info(f"Arıza düzenlemesi kaydedildi: {self._ariza_id}")
            self.saved.emit()
        except Exception as e:
            logger.error(f"Arıza düzenlemesi kaydedilemedi: {e}")
            QMessageBox.critical(self, "Hata", f"Kayıt başarısız: {e}")

    def _cancel(self):
        parent = self.parentWidget()
        if parent and hasattr(parent, "_close_form"):
            cast(Any, parent)._close_form()
