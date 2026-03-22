# -*- coding: utf-8 -*-
"""Vardiya Ekle / Düzenle Dialog."""
from PySide6.QtCore import Qt
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QDoubleSpinBox, QSpinBox,
    QPushButton, QFrame,
)
from core.di import get_nobet_service
from core.hata_yonetici import hata_goster
from ui.styles.icons import IconRenderer, IconColors


class NobetVardiyaDialog(QDialog):

    def __init__(self, birim_adi: str, db=None,
                 mevcut: dict = None, parent=None):
        super().__init__(parent)
        self._db       = db
        self._birim_adi = birim_adi
        self._mevcut   = mevcut
        self.setWindowTitle(
            f"{'Düzenle' if mevcut else 'Yeni Vardiya'} — {birim_adi}")
        self.setModal(True)
        self.resize(360, 280)
        self._build_ui()
        if mevcut:
            self._doldur(mevcut)

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(12)

        form = QFormLayout()
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight |
                               Qt.AlignmentFlag.AlignVCenter)

        def _lbl(t, z=False):
            l = QLabel(("★ " if z else "") + t)
            l.setProperty("color-role", "muted")
            return l

        self.inp_adi = QLineEdit()
        self.inp_adi.setPlaceholderText("Örn: Sabah, Gece, 24 Saat")
        form.addRow(_lbl("Vardiya Adı", True), self.inp_adi)

        self.inp_bas = QLineEdit()
        self.inp_bas.setPlaceholderText("08:00")
        self.inp_bas.setMaxLength(5)
        form.addRow(_lbl("Başlangıç Saati", True), self.inp_bas)

        self.inp_bit = QLineEdit()
        self.inp_bit.setPlaceholderText("16:00")
        self.inp_bit.setMaxLength(5)
        form.addRow(_lbl("Bitiş Saati", True), self.inp_bit)

        self.spn_sure = QDoubleSpinBox()
        self.spn_sure.setRange(0.5, 24.0)
        self.spn_sure.setSingleStep(0.5)
        self.spn_sure.setValue(8.0)
        self.spn_sure.setSuffix(" saat")
        form.addRow(_lbl("Süre", True), self.spn_sure)

        self.spn_min = QSpinBox()
        self.spn_min.setRange(1, 10)
        self.spn_min.setValue(1)
        self.spn_min.setSuffix(" kişi")
        form.addRow(_lbl("Min. Personel", True), self.spn_min)

        root.addLayout(form)
        root.addStretch()

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_iptal = QPushButton("İptal")
        btn_iptal.setProperty("style-role", "secondary")
        btn_iptal.clicked.connect(self.reject)
        btn_row.addWidget(btn_iptal)

        self.btn_kaydet = QPushButton("Kaydet")
        self.btn_kaydet.setProperty("style-role", "action")
        self.btn_kaydet.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        IconRenderer.set_button_icon(self.btn_kaydet, "save",
                                     color=IconColors.PRIMARY, size=14)
        self.btn_kaydet.clicked.connect(self._kaydet)
        btn_row.addWidget(self.btn_kaydet)
        root.addLayout(btn_row)

    def _doldur(self, v: dict):
        self.inp_adi.setText(str(v.get("VardiyaAdi", "")))
        self.inp_bas.setText(str(v.get("BasSaat", "")))
        self.inp_bit.setText(str(v.get("BitSaat", "")))
        self.spn_sure.setValue(float(v.get("SaatSuresi", 8.0)))
        self.spn_min.setValue(int(v.get("MinPersonel", 1)))

    def _kaydet(self):
        adi = self.inp_adi.text().strip()
        bas = self.inp_bas.text().strip()
        bit = self.inp_bit.text().strip()
        if not all([adi, bas, bit]):
            hata_goster(self, "Vardiya adı, başlangıç ve bitiş saati zorunludur.")
            return
        veri = {
            "BirimAdi":    self._birim_adi,
            "VardiyaAdi":  adi,
            "BasSaat":     bas,
            "BitSaat":     bit,
            "SaatSuresi":  self.spn_sure.value(),
            "MinPersonel": self.spn_min.value(),
            "Aktif":       1,
        }
        try:
            svc = get_nobet_service(self._db)
            if self._mevcut:
                sonuc = svc.vardiya_guncelle(self._mevcut["VardiyaID"], veri)
            else:
                sonuc = svc.vardiya_ekle(veri)
            if sonuc.basarili:
                self.accept()
            else:
                hata_goster(self, sonuc.mesaj)
        except Exception as e:
            hata_goster(self, str(e))
