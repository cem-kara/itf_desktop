# -*- coding: utf-8 -*-
"""
nobet_yonetim_page.py â€” BirleÅŸik NÃ¶bet YÃ¶netim EkranÄ±

Eski iki dosyanÄ±n (nobet_birim_yonetim.py + nobet_vardiya_page.py) iÅŸlevselliÄŸi
tek, tutarlÄ± bir ekranda birleÅŸtirildi.

YerleÅŸim:
  Sol kenar Ã§ubuÄŸu  (200px) â€” Birim listesi + "Yeni Birim" butonu
  Ana alan  (esnek) â€” BaÅŸlÄ±k + 4 sekme:
      [Vardiyalar]  [Personel]  [NÃ¶bet Tercihleri]  [Birim AyarlarÄ±]

Ã–zellikler:
  - Birim: ekle / dÃ¼zenle / aktif-pasif toggle / soft-delete
  - Vardiya Grubu: ekle / dÃ¼zenle / sil, ÅŸablon desteÄŸi
  - Vardiya: ekle / dÃ¼zenle / sil (ad, bas/bit saat, sÃ¼re, rol, minPersonel)
  - Personel: ata / GorevYeri'nden aktar / gÃ¶revden al
  - NÃ¶bet Tercihleri: ay bazlÄ± FM GÃ¶nÃ¼llÃ¼ + HedefTipi
  - Birim AyarlarÄ±: slot, FM maks, hafta sonu/tatil parametreleri
"""
from __future__ import annotations

import uuid
from datetime import date, datetime

from PySide6.QtCore import Qt, QTime
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QFrame, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QGroupBox, QFormLayout, QSpinBox,
    QLineEdit, QComboBox, QTabWidget, QDialog, QDialogButtonBox,
    QMessageBox, QSplitter, QCheckBox, QTimeEdit, QScrollArea,
)

from core.di import get_registry, get_nb_birim_service
from core.logger import logger

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
#  Sabitler
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

_AY_TR = [
    "", "Ocak", "Åubat", "Mart", "Nisan", "MayÄ±s", "Haziran",
    "Temmuz", "AÄŸustos", "EylÃ¼l", "Ekim", "KasÄ±m", "AralÄ±k",
]

BIRIM_TIPLERI = ["radyoloji", "nÃ¼kleer_tÄ±p", "patoloji", "diÄŸer"]

HEDEF_TIPLER = [
    ("normal",  "Normal  (7.0 s/gÃ¼n)"),
    ("emzirme", "Emzirme (5.5 s/gÃ¼n)"),
    ("sendika", "Sendika (6.2 s/gÃ¼n)"),
    ("sua",     "Åua Ä°zni (0 s/gÃ¼n)"),
    ("rapor",   "Raporlu (7.0 s/gÃ¼n)"),
    ("yillik",  "YÄ±llÄ±k Ä°zin (7.0 s/gÃ¼n)"),
    ("idari",   "Ä°dari Ä°zin (7.0 s/gÃ¼n)"),
]

_simdi   = lambda: datetime.now().isoformat(sep=" ", timespec="seconds")
_yeni_id = lambda: str(uuid.uuid4())


def _it(text: str, user=None) -> QTableWidgetItem:
    """OrtalanmÄ±ÅŸ, opsiyonel UserRole'lu tablo hÃ¼cresi."""
    itm = QTableWidgetItem(str(text))
    if user is not None:
        itm.setData(Qt.ItemDataRole.UserRole, user)
    itm.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
    return itm


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
#  FORM DÄ°ALOGLARI
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

class _BirimDialog(QDialog):
    """Birim ekle / dÃ¼zenle formu."""

    def __init__(self, kayit: dict = None, parent=None):
        super().__init__(parent)
        self._kayit = kayit or {}
        self.setWindowTitle("Yeni Birim" if not kayit else "Birim DÃ¼zenle")
        self.setModal(True)
        self.setMinimumWidth(460)
        self.setProperty("bg-role", "page")
        self._build()

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setSpacing(12)
        lay.setContentsMargins(24, 24, 24, 24)

        def _satir(lbl_text, widget, zorunlu=False):
            row = QHBoxLayout()
            lbl = QLabel(lbl_text + (" *" if zorunlu else ""))
            lbl.setFixedWidth(120)
            lbl.setProperty("color-role", "primary")
            row.addWidget(lbl)
            row.addWidget(widget)
            lay.addLayout(row)
            return widget

        self._inp_adi = _satir("Birim AdÄ±", QLineEdit(
            self._kayit.get("BirimAdi", "")), zorunlu=True)
        self._inp_adi.setPlaceholderText("Ã¶r: Acil Radyoloji")

        self._inp_kodu = _satir("Birim Kodu", QLineEdit(
            self._kayit.get("BirimKodu", "")))
        self._inp_kodu.setPlaceholderText("BoÅŸ bÄ±rakÄ±lÄ±rsa otomatik Ã¼retilir")

        self._cmb_tip = QComboBox()
        for t in BIRIM_TIPLERI:
            self._cmb_tip.addItem(t)
        idx = self._cmb_tip.findText(
            self._kayit.get("BirimTipi", "radyoloji"))
        if idx >= 0:
            self._cmb_tip.setCurrentIndex(idx)
        _satir("TÃ¼r", self._cmb_tip)

        self._spn_sira = QSpinBox()
        self._spn_sira.setRange(1, 999)
        self._spn_sira.setValue(int(self._kayit.get("Sira", 99)))
        _satir("SÄ±ra", self._spn_sira)

        self._inp_aciklama = _satir("AÃ§Ä±klama", QLineEdit(
            self._kayit.get("Aciklama", "")))
        self._inp_aciklama.setPlaceholderText("Ä°steÄŸe baÄŸlÄ±")

        lay.addSpacing(8)
        not_lbl = QLabel("* Zorunlu alan")
        not_lbl.setProperty("color-role", "muted")
        not_lbl.setStyleSheet("font-size: 11px;")
        lay.addWidget(not_lbl)
        lay.addSpacing(8)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_iptal = QPushButton("Ä°ptal")
        btn_iptal.setProperty("style-role", "secondary")
        btn_iptal.setFixedWidth(90)
        btn_iptal.clicked.connect(self.reject)
        btn_row.addWidget(btn_iptal)
        btn_kaydet = QPushButton("Kaydet")
        btn_kaydet.setProperty("style-role", "action")
        btn_kaydet.setFixedWidth(90)
        btn_kaydet.clicked.connect(self._kaydet)
        btn_row.addWidget(btn_kaydet)
        lay.addLayout(btn_row)

    def _kaydet(self):
        if not self._inp_adi.text().strip():
            QMessageBox.warning(self, "UyarÄ±", "Birim adÄ± boÅŸ olamaz.")
            self._inp_adi.setFocus()
            return
        self.accept()

    def get_data(self) -> dict:
        return {
            "BirimAdi":  self._inp_adi.text().strip(),
            "BirimKodu": self._inp_kodu.text().strip().upper(),
            "BirimTipi": self._cmb_tip.currentText(),
            "Sira":      self._spn_sira.value(),
            "Aciklama":  self._inp_aciklama.text().strip(),
        }


class _GrupDialog(QDialog):
    """Vardiya grubu ekle / dÃ¼zenle formu."""

    def __init__(self, kayit: dict = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Grup DÃ¼zenle" if kayit else "Yeni Grup")
        self.setModal(True)
        self.setMinimumWidth(340)
        self.setProperty("bg-role", "page")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 20, 20, 20)
        form = QFormLayout()

        self._adi = QLineEdit((kayit or {}).get("GrupAdi", ""))
        self._adi.setPlaceholderText("Ã¶r: Sabah Grubu")
        form.addRow("Grup AdÄ± *:", self._adi)

        self._sira = QSpinBox()
        self._sira.setRange(1, 20)
        self._sira.setValue(int((kayit or {}).get("Sira", 1)))
        form.addRow("SÄ±ra:", self._sira)

        self._aktif = QCheckBox("Aktif")
        self._aktif.setChecked(bool(int((kayit or {}).get("Aktif", 1))))
        form.addRow("", self._aktif)

        lay.addLayout(form)
        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self._kabul)
        btns.rejected.connect(self.reject)
        lay.addWidget(btns)

    def _kabul(self):
        if not self._adi.text().strip():
            QMessageBox.warning(self, "UyarÄ±", "Grup adÄ± boÅŸ olamaz.")
            return
        self.accept()

    def get_data(self) -> dict:
        return {
            "GrupAdi": self._adi.text().strip(),
            "Sira":    self._sira.value(),
            "Aktif":   1 if self._aktif.isChecked() else 0,
        }


class _VardiyaDialog(QDialog):
    """Vardiya ekle / dÃ¼zenle formu."""

    def __init__(self, kayit: dict = None, birim_ayar: dict = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Vardiya DÃ¼zenle" if kayit else "Yeni Vardiya")
        self.setModal(True)
        self.setMinimumWidth(380)
        self.setProperty("bg-role", "page")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 20, 20, 20)
        form = QFormLayout()

        self._adi = QLineEdit((kayit or {}).get("VardiyaAdi", ""))
        self._adi.setPlaceholderText("Ã¶r: Sabah VardiyasÄ±")
        form.addRow("Vardiya AdÄ± *:", self._adi)

        def _time_w(val: str, default: str) -> QTimeEdit:
            w = QTimeEdit()
            w.setDisplayFormat("HH:mm")
            t = val or default
            w.setTime(QTime(*[int(x) for x in t.split(":")[:2]]))
            return w

        self._bas = _time_w((kayit or {}).get("BasSaat", ""), "08:00")
        form.addRow("BaÅŸlangÄ±Ã§:", self._bas)

        self._bit = _time_w((kayit or {}).get("BitSaat", ""), "20:00")
        form.addRow("BitiÅŸ:", self._bit)

        self._sure = QSpinBox()
        self._sure.setRange(0, 1440)
        self._sure.setSuffix(" dk")
        self._sure.setValue(int((kayit or {}).get("SureDakika", 720)))
        form.addRow("SÃ¼re:", self._sure)

        self._min_p = QSpinBox()
        self._min_p.setRange(1, 20)
        self._min_p.setValue(int((kayit or {}).get("MinPersonel", 1)))
        form.addRow("Min. Personel:", self._min_p)

        self._rol = QComboBox()
        self._rol.addItem("Ana Vardiya",  userData="ana")
        self._rol.addItem("YardÄ±mcÄ±",     userData="yardimci")
        self._rol.setCurrentIndex(
            0 if (kayit or {}).get("Rol", "ana") == "ana" else 1)
        form.addRow("Rol:", self._rol)

        self._sira = QSpinBox()
        self._sira.setRange(1, 20)
        self._sira.setValue(int((kayit or {}).get("Sira", 1)))
        form.addRow("SÄ±ra:", self._sira)

        self._aktif = QCheckBox("Aktif")
        self._aktif.setChecked(bool(int((kayit or {}).get("Aktif", 1))))
        form.addRow("", self._aktif)

        # Birim ayar alanlarÄ± (vardiya formunda hÄ±zlÄ± eriÅŸim)
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setProperty("bg-role", "elevated")

        self._haftasonu = QCheckBox("Bu birimde hafta sonu Ã§alÄ±ÅŸma var")
        self._haftasonu.setChecked(
            bool(int((birim_ayar or {}).get("HaftasonuNobetZorunlu", 1))))
        form.addRow("Hafta Sonu:", self._haftasonu)

        self._tatil = QCheckBox("Bu birimde tatil gÃ¼nlerinde Ã§alÄ±ÅŸma var")
        self._tatil.setChecked(
            bool(int((birim_ayar or {}).get("DiniBayramAtama", 1))))
        form.addRow("Tatiller:", self._tatil)

        lay.addLayout(form)
        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self._kabul)
        btns.rejected.connect(self.reject)
        lay.addWidget(btns)

    def _kabul(self):
        if not self._adi.text().strip():
            QMessageBox.warning(self, "UyarÄ±", "Vardiya adÄ± boÅŸ olamaz.")
            return
        self.accept()

    def get_data(self) -> dict:
        return {
            "VardiyaAdi": self._adi.text().strip(),
            "BasSaat":    self._bas.time().toString("HH:mm"),
            "BitSaat":    self._bit.time().toString("HH:mm"),
            "SureDakika": self._sure.value(),
            "MinPersonel": self._min_p.value(),
            "Rol":        self._rol.currentData(),
            "Sira":       self._sira.value(),
            "Aktif":      1 if self._aktif.isChecked() else 0,
        }

    def get_birim_ayar_data(self) -> dict:
        return {
            "HaftasonuNobetZorunlu": 1 if self._haftasonu.isChecked() else 0,
            "DiniBayramAtama":       1 if self._tatil.isChecked() else 0,
        }


class _PersonelAtaDialog(QDialog):
    """Personel listesinden birden fazla seÃ§im."""

    def __init__(self, pid_listesi: list, p_map: dict,
                 mevcutlar: set, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Personel Ata")
        self.setModal(True)
        self.setMinimumSize(420, 520)
        self.setProperty("bg-role", "page")

        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.setSpacing(8)

        ara = QLineEdit()
        ara.setPlaceholderText("Ä°simle araâ€¦")
        ara.textChanged.connect(self._filtrele)
        lay.addWidget(ara)

        self._tbl = QTableWidget(0, 3)
        self._tbl.setHorizontalHeaderLabels(["Ad Soyad", "Rol", "Durum"])
        self._tbl.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch)
        self._tbl.setColumnWidth(1, 90)
        self._tbl.setColumnWidth(2, 80)
        self._tbl.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows)
        self._tbl.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers)
        self._tbl.verticalHeader().setVisible(False)
        lay.addWidget(self._tbl, 1)

        self._tum = [
            (pid, p_map.get(pid, pid), pid in mevcutlar)
            for pid in pid_listesi
        ]
        self._filtrele("")

        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        lay.addWidget(btns)

    def _filtrele(self, metin: str):
        self._tbl.setRowCount(0)
        metin = metin.lower()
        for pid, ad, mevcut in self._tum:
            if metin and metin not in ad.lower():
                continue
            ri = self._tbl.rowCount()
            self._tbl.insertRow(ri)

            ad_i = QTableWidgetItem(ad)
            ad_i.setData(Qt.ItemDataRole.UserRole, pid)
            ad_i.setCheckState(
                Qt.CheckState.Checked if mevcut
                else Qt.CheckState.Unchecked)
            if mevcut:
                ad_i.setForeground(QColor("#2ec98e"))
            self._tbl.setItem(ri, 0, ad_i)
            self._tbl.setItem(ri, 1, QTableWidgetItem("teknisyen"))
            self._tbl.setItem(ri, 2,
                QTableWidgetItem("AtanmÄ±ÅŸ" if mevcut else "â€”"))

    def get_secilen(self) -> list:
        mevcutlar = {pid for pid, _, m in self._tum if m}
        return [
            self._tbl.item(ri, 0).data(Qt.ItemDataRole.UserRole)
            for ri in range(self._tbl.rowCount())
            if (self._tbl.item(ri, 0)
                and self._tbl.item(ri, 0).checkState() == Qt.CheckState.Checked
                and self._tbl.item(ri, 0).data(Qt.ItemDataRole.UserRole)
                    not in mevcutlar)
        ]


class _TercihDialog(QDialog):
    """AylÄ±k nÃ¶bet tercihi: FM GÃ¶nÃ¼llÃ¼ + HedefTipi."""

    def __init__(self, pid: str, ad: str, yil: int, ay: int,
                 kayit: dict = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"NÃ¶bet Tercihi â€” {ad}")
        self.setModal(True)
        self.setMinimumWidth(380)
        self.setProperty("bg-role", "page")

        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.setSpacing(12)

        baslik = QLabel(f"<b>{ad}</b>  â€”  {_AY_TR[ay]} {yil}")
        baslik.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(baslik)

        form = QFormLayout()

        self._chk_fm = QCheckBox("FM GÃ¶nÃ¼llÃ¼sÃ¼")
        self._chk_fm.setChecked(
            (kayit or {}).get("NobetTercihi", "") == "fazla_mesai_gonullu")
        self._chk_fm.setToolTip(
            "Ä°ÅŸaretliyse boÅŸ slotlara fazla mesai olarak atanabilir")
        form.addRow("Fazla Mesai:", self._chk_fm)

        self._cmb_tip = QComboBox()
        for val, lbl in HEDEF_TIPLER:
            self._cmb_tip.addItem(lbl, userData=val)
        mevcut = (kayit or {}).get("HedefTipi", "normal")
        idx = next(
            (i for i, (v, _) in enumerate(HEDEF_TIPLER) if v == mevcut), 0)
        self._cmb_tip.setCurrentIndex(idx)
        form.addRow("Hedef Tipi:", self._cmb_tip)

        lay.addLayout(form)
        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        lay.addWidget(btns)

    def get_data(self) -> dict:
        return {
            "NobetTercihi": (
                "fazla_mesai_gonullu"
                if self._chk_fm.isChecked() else "zorunlu"),
            "HedefTipi": self._cmb_tip.currentData(),
        }


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
#  NÃ–BET YÃ–NETÄ°M SAYFA (Ana Widget)
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

class NobetYonetimPage(QWidget):
    """
    BirleÅŸik nÃ¶bet yÃ¶netim ekranÄ±.

    Eski NobetBirimYonetimPage + NobetVardiyaPage'in tÃ¼m iÅŸlevselliÄŸini
    tek bir ekranda toplar.
    """

    def __init__(self, db=None, action_guard=None, parent=None):
        super().__init__(parent)
        self._db  = db
        self._ag  = action_guard
        self._yil = date.today().year
        self._ay  = date.today().month

        # SeÃ§ili kayÄ±t izi
        self._secili_birim_id:  str = ""
        self._secili_birim_adi: str = ""
        self._secili_grup_id:   str = ""

        self.setProperty("bg-role", "page")
        self._build()

        if db:
            self._birimleri_yukle()

    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    #  YardÄ±mcÄ±
    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def _reg(self):
        return get_registry(self._db)

    def _birim_svc(self):
        try:
            return get_nb_birim_service(self._db)
        except Exception as e:
            logger.error(f"NbBirimService: {e}")
            return None

    def _btn(self, metin: str, stil: str = "secondary",
             h: int = 26) -> QPushButton:
        b = QPushButton(metin)
        b.setProperty("style-role", stil)
        b.setFixedHeight(h)
        return b

    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    #  UI Ä°nÅŸasÄ±
    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def _build(self):
        ana = QHBoxLayout(self)
        ana.setContentsMargins(0, 0, 0, 0)
        ana.setSpacing(0)

        spl = QSplitter(Qt.Orientation.Horizontal)
        spl.addWidget(self._build_sidebar())
        spl.addWidget(self._build_main())
        spl.setSizes([210, 800])
        spl.setCollapsible(0, False)
        spl.setCollapsible(1, False)
        ana.addWidget(spl)

    # â”€â”€ Sol kenar Ã§ubuÄŸu: Birim listesi â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def _build_sidebar(self) -> QWidget:
        w = QWidget()
        w.setProperty("bg-role", "panel")
        lay = QVBoxLayout(w)
        lay.setContentsMargins(8, 10, 8, 8)
        lay.setSpacing(6)

        # BaÅŸlÄ±k + butonlar
        hdr = QHBoxLayout()
        lbl = QLabel("NÃ¶bet Birimleri")
        lbl.setProperty("style-role", "section-title")
        hdr.addWidget(lbl)
        hdr.addStretch()

        self._btn_b_yeni = self._btn("+", "action")
        self._btn_b_yeni.setFixedWidth(28)
        self._btn_b_yeni.setToolTip("Yeni birim ekle")
        self._btn_b_yeni.clicked.connect(self._birim_yeni)
        hdr.addWidget(self._btn_b_yeni)

        self._btn_b_dup = self._btn("âœ")
        self._btn_b_dup.setFixedWidth(28)
        self._btn_b_dup.setEnabled(False)
        self._btn_b_dup.setToolTip("SeÃ§ili birimi dÃ¼zenle")
        self._btn_b_dup.clicked.connect(self._birim_duzenle)
        hdr.addWidget(self._btn_b_dup)
        lay.addLayout(hdr)

        # Birim tablosu
        self._tbl_birim = QTableWidget(0, 1)
        self._tbl_birim.horizontalHeader().setVisible(False)
        self._tbl_birim.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch)
        self._tbl_birim.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows)
        self._tbl_birim.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers)
        self._tbl_birim.verticalHeader().setVisible(False)
        self._tbl_birim.setShowGrid(False)
        self._tbl_birim.setAlternatingRowColors(True)
        self._tbl_birim.selectionModel().selectionChanged.connect(
            self._on_birim_sec)
        lay.addWidget(self._tbl_birim, 1)

        # Alt durum satÄ±rÄ±
        self._lbl_b_ozet = QLabel("")
        self._lbl_b_ozet.setProperty("color-role", "muted")
        self._lbl_b_ozet.setStyleSheet("font-size: 10px;")
        lay.addWidget(self._lbl_b_ozet)

        return w

    # â”€â”€ Ana alan â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def _build_main(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # BaÅŸlÄ±k ÅŸeridi
        self._hdr_widget = self._build_header()
        lay.addWidget(self._hdr_widget)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setProperty("bg-role", "elevated")
        lay.addWidget(sep)

        # Sekmeler
        self._tabs = QTabWidget()
        self._tabs.addTab(self._build_tab_vardiya(),  "Vardiyalar")
        self._tabs.addTab(self._build_tab_personel(), "Personel")
        self._tabs.addTab(self._build_tab_tercih(),   "NÃ¶bet Tercihleri")
        self._tabs.addTab(self._build_tab_ayar(),     "Birim AyarlarÄ±")
        lay.addWidget(self._tabs, 1)

        # BaÅŸlangÄ±Ã§ta sekmeleri gizle
        self._tabs.setVisible(False)
        return w

    def _build_header(self) -> QWidget:
        w = QWidget()
        w.setFixedHeight(48)
        lay = QHBoxLayout(w)
        lay.setContentsMargins(16, 8, 16, 8)

        self._lbl_birim_adi = QLabel("LÃ¼tfen bir birim seÃ§in")
        self._lbl_birim_adi.setProperty("style-role", "section-title")
        lay.addWidget(self._lbl_birim_adi)

        self._lbl_birim_tip = QLabel("")
        self._lbl_birim_tip.setProperty("color-role", "muted")
        self._lbl_birim_tip.setStyleSheet("font-size: 11px;")
        lay.addWidget(self._lbl_birim_tip)

        lay.addStretch()

        self._btn_toggle = self._btn("â¸  Pasife Al", h=28)
        self._btn_toggle.setEnabled(False)
        self._btn_toggle.clicked.connect(self._birim_toggle)
        lay.addWidget(self._btn_toggle)

        self._btn_b_sil = self._btn("âœ•  Sil", "danger", h=28)
        self._btn_b_sil.setEnabled(False)
        self._btn_b_sil.clicked.connect(self._birim_sil)
        lay.addWidget(self._btn_b_sil)

        return w

    # â”€â”€ Sekme: Vardiyalar â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def _build_tab_vardiya(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(12, 10, 12, 10)
        lay.setSpacing(8)

        # Splitter: gruplar solda, vardiyalar saÄŸda
        spl = QSplitter(Qt.Orientation.Horizontal)
        spl.addWidget(self._build_grup_paneli())
        spl.addWidget(self._build_vardiya_paneli())
        spl.setSizes([260, 540])
        lay.addWidget(spl)
        return w

    def _build_grup_paneli(self) -> QWidget:
        w = QWidget()
        w.setProperty("bg-role", "panel")
        lay = QVBoxLayout(w)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.setSpacing(4)

        hdr = QHBoxLayout()
        lbl = QLabel("Vardiya GruplarÄ±")
        lbl.setProperty("style-role", "section-title")
        hdr.addWidget(lbl)
        hdr.addStretch()

        self._btn_grup_yeni = self._btn("+", "action")
        self._btn_grup_yeni.setFixedWidth(28)
        self._btn_grup_yeni.setEnabled(False)
        self._btn_grup_yeni.setToolTip("Yeni grup ekle")
        self._btn_grup_yeni.clicked.connect(self._grup_yeni)
        hdr.addWidget(self._btn_grup_yeni)

        self._btn_sablon = self._btn("âŠ Åablon")
        self._btn_sablon.setEnabled(False)
        self._btn_sablon.setToolTip("HazÄ±r ÅŸablondan grup oluÅŸtur")
        self._btn_sablon.clicked.connect(self._grup_sablon)
        hdr.addWidget(self._btn_sablon)
        lay.addLayout(hdr)

        self._tbl_grup = QTableWidget(0, 3)
        self._tbl_grup.setHorizontalHeaderLabels(["Grup AdÄ±", "SÄ±ra", "Aktif"])
        self._tbl_grup.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch)
        self._tbl_grup.setColumnWidth(1, 45)
        self._tbl_grup.setColumnWidth(2, 50)
        self._tbl_grup.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows)
        self._tbl_grup.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers)
        self._tbl_grup.verticalHeader().setVisible(False)
        self._tbl_grup.setShowGrid(False)
        self._tbl_grup.setAlternatingRowColors(True)
        self._tbl_grup.selectionModel().selectionChanged.connect(
            self._on_grup_sec)
        lay.addWidget(self._tbl_grup, 1)

        alt = QHBoxLayout()
        self._btn_grup_dup = self._btn("âœ")
        self._btn_grup_dup.setFixedWidth(28)
        self._btn_grup_dup.setEnabled(False)
        self._btn_grup_dup.clicked.connect(self._grup_duzenle)
        alt.addWidget(self._btn_grup_dup)

        self._btn_grup_sil = self._btn("âœ•", "danger")
        self._btn_grup_sil.setFixedWidth(28)
        self._btn_grup_sil.setEnabled(False)
        self._btn_grup_sil.clicked.connect(self._grup_sil)
        alt.addWidget(self._btn_grup_sil)
        alt.addStretch()
        lay.addLayout(alt)
        return w

    def _build_vardiya_paneli(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.setSpacing(4)

        hdr = QHBoxLayout()
        self._lbl_grup_adi = QLabel("â€” Grup seÃ§in â€”")
        self._lbl_grup_adi.setProperty("style-role", "section-title")
        hdr.addWidget(self._lbl_grup_adi)
        hdr.addStretch()

        self._btn_v_yeni = self._btn("+ Vardiya", "action")
        self._btn_v_yeni.setEnabled(False)
        self._btn_v_yeni.clicked.connect(self._vardiya_yeni)
        hdr.addWidget(self._btn_v_yeni)
        lay.addLayout(hdr)

        self._tbl_v = QTableWidget(0, 6)
        self._tbl_v.setHorizontalHeaderLabels(
            ["Vardiya AdÄ±", "BaÅŸlangÄ±Ã§", "BitiÅŸ", "SÃ¼re", "Rol", "Min P."])
        self._tbl_v.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch)
        for i in range(1, 6):
            self._tbl_v.setColumnWidth(i, 72)
        self._tbl_v.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows)
        self._tbl_v.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers)
        self._tbl_v.verticalHeader().setVisible(False)
        self._tbl_v.setShowGrid(False)
        self._tbl_v.setAlternatingRowColors(True)
        self._tbl_v.doubleClicked.connect(self._vardiya_duzenle)
        self._tbl_v.selectionModel().selectionChanged.connect(self._on_v_sec)
        lay.addWidget(self._tbl_v, 1)

        alt = QHBoxLayout()
        self._btn_v_dup = self._btn("âœ")
        self._btn_v_dup.setFixedWidth(28)
        self._btn_v_dup.setEnabled(False)
        self._btn_v_dup.clicked.connect(self._vardiya_duzenle)
        alt.addWidget(self._btn_v_dup)

        self._btn_v_sil = self._btn("âœ•", "danger")
        self._btn_v_sil.setFixedWidth(28)
        self._btn_v_sil.setEnabled(False)
        self._btn_v_sil.clicked.connect(self._vardiya_sil)
        alt.addWidget(self._btn_v_sil)
        alt.addStretch()

        self._lbl_v_ozet = QLabel("")
        self._lbl_v_ozet.setProperty("color-role", "muted")
        self._lbl_v_ozet.setStyleSheet("font-size: 10px;")
        alt.addWidget(self._lbl_v_ozet)
        lay.addLayout(alt)
        return w

    # â”€â”€ Sekme: Personel â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def _build_tab_personel(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(12, 10, 12, 10)
        lay.setSpacing(6)

        tb = QHBoxLayout()
        self._btn_p_ata = self._btn("+ Personel Ata", "action", h=28)
        self._btn_p_ata.setEnabled(False)
        self._btn_p_ata.clicked.connect(self._personel_ata)
        tb.addWidget(self._btn_p_ata)

        self._btn_p_migrate = self._btn("âŸ³  GorevYeri'nden Aktar", h=28)
        self._btn_p_migrate.setEnabled(False)
        self._btn_p_migrate.setToolTip(
            "Personel.GorevYeri = birim adÄ±yla eÅŸleÅŸen personeli aktar")
        self._btn_p_migrate.clicked.connect(self._personel_migrate)
        tb.addWidget(self._btn_p_migrate)
        tb.addStretch()
        lay.addLayout(tb)

        self._tbl_p = QTableWidget(0, 4)
        self._tbl_p.setHorizontalHeaderLabels(
            ["Ad Soyad", "Rol", "GÃ¶rev BaÅŸlangÄ±Ã§", "Durum"])
        self._tbl_p.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch)
        for i in range(1, 4):
            self._tbl_p.setColumnWidth(i, 100)
        self._tbl_p.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows)
        self._tbl_p.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers)
        self._tbl_p.verticalHeader().setVisible(False)
        self._tbl_p.setShowGrid(False)
        self._tbl_p.setAlternatingRowColors(True)
        self._tbl_p.selectionModel().selectionChanged.connect(self._on_p_sec)
        lay.addWidget(self._tbl_p, 1)

        alt = QHBoxLayout()
        self._btn_p_cikar = self._btn("âœ•  GÃ¶revden Al", "danger", h=28)
        self._btn_p_cikar.setEnabled(False)
        self._btn_p_cikar.clicked.connect(self._personel_cikar)
        alt.addWidget(self._btn_p_cikar)
        alt.addStretch()

        self._lbl_p_ozet = QLabel("")
        self._lbl_p_ozet.setProperty("color-role", "muted")
        self._lbl_p_ozet.setStyleSheet("font-size: 10px;")
        alt.addWidget(self._lbl_p_ozet)
        lay.addLayout(alt)
        return w

    # â”€â”€ Sekme: NÃ¶bet Tercihleri â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def _build_tab_tercih(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(12, 10, 12, 10)
        lay.setSpacing(6)

        nav = QHBoxLayout()
        btn_g = self._btn("â€¹", h=26)
        btn_g.setFixedWidth(28)
        btn_g.clicked.connect(self._tercih_ay_geri)
        nav.addWidget(btn_g)

        self._lbl_tercih_ay = QLabel(f"{_AY_TR[self._ay]} {self._yil}")
        self._lbl_tercih_ay.setFixedWidth(120)
        self._lbl_tercih_ay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._lbl_tercih_ay.setProperty("style-role", "section-title")
        nav.addWidget(self._lbl_tercih_ay)

        btn_i = self._btn("â€º", h=26)
        btn_i.setFixedWidth(28)
        btn_i.clicked.connect(self._tercih_ay_ileri)
        nav.addWidget(btn_i)
        nav.addStretch()

        hint = QLabel("Ã‡ift tÄ±kla â†’ dÃ¼zenle")
        hint.setProperty("color-role", "muted")
        hint.setStyleSheet("font-size: 10px;")
        nav.addWidget(hint)
        lay.addLayout(nav)

        self._tbl_tercih = QTableWidget(0, 3)
        self._tbl_tercih.setHorizontalHeaderLabels(
            ["Ad Soyad", "FM GÃ¶nÃ¼llÃ¼", "Hedef Tipi"])
        self._tbl_tercih.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch)
        self._tbl_tercih.setColumnWidth(1, 110)
        self._tbl_tercih.setColumnWidth(2, 150)
        self._tbl_tercih.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows)
        self._tbl_tercih.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers)
        self._tbl_tercih.verticalHeader().setVisible(False)
        self._tbl_tercih.setShowGrid(False)
        self._tbl_tercih.setAlternatingRowColors(True)
        self._tbl_tercih.doubleClicked.connect(self._tercih_duzenle)
        self._tbl_tercih.selectionModel().selectionChanged.connect(
            self._on_tercih_sec)
        lay.addWidget(self._tbl_tercih, 1)

        alt = QHBoxLayout()
        self._btn_tercih_dup = self._btn("âœ  DÃ¼zenle", h=28)
        self._btn_tercih_dup.setEnabled(False)
        self._btn_tercih_dup.clicked.connect(self._tercih_duzenle)
        alt.addWidget(self._btn_tercih_dup)
        alt.addStretch()

        self._lbl_tercih_ozet = QLabel("")
        self._lbl_tercih_ozet.setProperty("color-role", "muted")
        self._lbl_tercih_ozet.setStyleSheet("font-size: 10px;")
        alt.addWidget(self._lbl_tercih_ozet)
        lay.addLayout(alt)
        return w

    # â”€â”€ Sekme: Birim AyarlarÄ± â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def _build_tab_ayar(self) -> QWidget:
        w = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        inner = QWidget()
        lay_outer = QVBoxLayout(w)
        lay_outer.setContentsMargins(0, 0, 0, 0)
        lay_outer.addWidget(scroll)
        scroll.setWidget(inner)

        lay = QVBoxLayout(inner)
        lay.setContentsMargins(16, 12, 16, 12)
        lay.setSpacing(14)

        # Vardiya parametreleri
        grp_var = QGroupBox("Vardiya Parametreleri")
        grp_var.setProperty("style-role", "group")
        form_v = QFormLayout(grp_var)
        form_v.setSpacing(8)

        self._spn_slot = QSpinBox()
        self._spn_slot.setRange(1, 10)
        self._spn_slot.setValue(4)
        self._spn_slot.setToolTip(
            "Her vardiya iÃ§in gÃ¼nlÃ¼k kaÃ§ farklÄ± kiÅŸi atanÄ±r")
        form_v.addRow("GÃ¼nlÃ¼k Slot SayÄ±sÄ±:", self._spn_slot)

        self._spn_fm_max = QSpinBox()
        self._spn_fm_max.setRange(0, 300)
        self._spn_fm_max.setSuffix(" saat")
        self._spn_fm_max.setValue(60)
        self._spn_fm_max.setToolTip("AylÄ±k FM Ã¼st sÄ±nÄ±rÄ±")
        form_v.addRow("FM Maks. (aylÄ±k):", self._spn_fm_max)

        self._spn_max_gun = QSpinBox()
        self._spn_max_gun.setRange(1, 2)
        self._spn_max_gun.setValue(1)
        self._spn_max_gun.setToolTip(
            "1 = tek vardiya/gÃ¼n (720 dk), 2 = Ã§ift vardiya (1440 dk)")
        form_v.addRow("GÃ¼nlÃ¼k Maks. Vardiya:", self._spn_max_gun)
        lay.addWidget(grp_var)

        # Ã‡alÄ±ÅŸma takvimi
        grp_tak = QGroupBox("Ã‡alÄ±ÅŸma Takvimi")
        grp_tak.setProperty("style-role", "group")
        form_t = QFormLayout(grp_tak)
        form_t.setSpacing(8)

        self._chk_hafta_sonu = QCheckBox("Hafta sonu nÃ¶bet atanÄ±r")
        self._chk_hafta_sonu.setChecked(True)
        form_t.addRow("Hafta Sonu:", self._chk_hafta_sonu)

        self._chk_resmi_tatil = QCheckBox("Resmi tatillerde nÃ¶bet atanÄ±r")
        self._chk_resmi_tatil.setChecked(True)
        form_t.addRow("Resmi Tatil:", self._chk_resmi_tatil)

        self._chk_dini_bayram = QCheckBox("Dini bayramlarda nÃ¶bet atanÄ±r")
        self._chk_dini_bayram.setChecked(False)
        form_t.addRow("Dini Bayram:", self._chk_dini_bayram)

        self._chk_ardisik = QCheckBox("Ardışık günlerde atama yapılabilir")
        self._chk_ardisik.setChecked(False)
        self._chk_ardisik.setToolTip(
            "Açıksa dün nöbette olan kişi bugün de atanabilir")
        form_t.addRow("Ardışık Gün:", self._chk_ardisik)
        lay.addWidget(grp_tak)

        # Kaydet butonu
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self._btn_ayar_kaydet = self._btn("ğŸ’¾  AyarlarÄ± Kaydet", "action", h=30)
        self._btn_ayar_kaydet.setEnabled(False)
        self._btn_ayar_kaydet.clicked.connect(self._birim_ayar_kaydet)
        btn_row.addWidget(self._btn_ayar_kaydet)
        lay.addLayout(btn_row)
        lay.addStretch()

        return w

    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    #  Veri YÃ¼kleme
    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def _birimleri_yukle(self):
        try:
            rows = sorted(
                self._reg().get("NB_Birim").get_all() or [],
                key=lambda r: (int(r.get("Sira", 99)), r.get("BirimAdi", "")))
            self._tbl_birim.setRowCount(0)
            aktif_say = 0
            for r in rows:
                if int(r.get("is_deleted", 0)):
                    continue
                ri  = self._tbl_birim.rowCount()
                bid = r["BirimID"]
                self._tbl_birim.insertRow(ri)
                itm = QTableWidgetItem(r.get("BirimAdi", ""))
                itm.setData(Qt.ItemDataRole.UserRole, bid)
                if not int(r.get("Aktif", 1)):
                    itm.setForeground(QColor("#e85555"))
                else:
                    aktif_say += 1
                self._tbl_birim.setItem(ri, 0, itm)
            toplam = self._tbl_birim.rowCount()
            self._lbl_b_ozet.setText(
                f"{toplam} birim  ({aktif_say} aktif)")
        except Exception as e:
            logger.error(f"Birim yÃ¼kle: {e}")

    def _gruplari_yukle(self, birim_id: str):
        try:
            rows = sorted(
                [r for r in (self._reg().get("NB_VardiyaGrubu").get_all() or [])
                 if str(r.get("BirimID", "")) == birim_id],
                key=lambda r: int(r.get("Sira", 1)))
            self._tbl_grup.setRowCount(0)
            self._tbl_v.setRowCount(0)
            self._secili_grup_id = ""
            self._lbl_grup_adi.setText("â€” Grup seÃ§in â€”")
            for r in rows:
                ri  = self._tbl_grup.rowCount()
                gid = r["GrupID"]
                self._tbl_grup.insertRow(ri)
                itm = QTableWidgetItem(r.get("GrupAdi", ""))
                itm.setData(Qt.ItemDataRole.UserRole, gid)
                self._tbl_grup.setItem(ri, 0, itm)
                self._tbl_grup.setItem(ri, 1, _it(r.get("Sira", 1), gid))
                aktif = int(r.get("Aktif", 1))
                a_itm = QTableWidgetItem("âœ”" if aktif else "âœ•")
                a_itm.setForeground(
                    QColor("#2ec98e" if aktif else "#e85555"))
                a_itm.setData(Qt.ItemDataRole.UserRole, gid)
                self._tbl_grup.setItem(ri, 2, a_itm)
        except Exception as e:
            logger.error(f"Grup yÃ¼kle: {e}")

    def _vardiyeleri_yukle(self, grup_id: str):
        try:
            rows = sorted(
                [r for r in (self._reg().get("NB_Vardiya").get_all() or [])
                 if str(r.get("GrupID", "")) == grup_id],
                key=lambda r: int(r.get("Sira", 1)))
            self._tbl_v.setRowCount(0)
            toplam_dk = 0
            for r in rows:
                ri  = self._tbl_v.rowCount()
                vid = r["VardiyaID"]
                dk  = int(r.get("SureDakika", 0))
                self._tbl_v.insertRow(ri)
                self._tbl_v.setItem(ri, 0, _it(r.get("VardiyaAdi", ""), vid))
                self._tbl_v.setItem(ri, 1, _it(r.get("BasSaat", ""), vid))
                self._tbl_v.setItem(ri, 2, _it(r.get("BitSaat", ""), vid))
                self._tbl_v.setItem(
                    ri, 3,
                    _it(f"{dk // 60}s {dk % 60:02d}dk" if dk else "â€”", vid))
                rol_itm = _it(r.get("Rol", "ana"), vid)
                if r.get("Rol", "ana") == "yardimci":
                    rol_itm.setForeground(QColor("#e8a030"))
                self._tbl_v.setItem(ri, 4, rol_itm)
                self._tbl_v.setItem(ri, 5, _it(r.get("MinPersonel", 1), vid))
                if r.get("Rol", "ana") == "ana":
                    toplam_dk += dk
            self._lbl_v_ozet.setText(
                f"{len(rows)} vardiya  |  "
                f"Toplam ana: {toplam_dk // 60}s {toplam_dk % 60:02d}dk")
        except Exception as e:
            logger.error(f"Vardiya yÃ¼kle: {e}")

    def _personelleri_yukle(self, birim_id: str):
        try:
            reg   = self._reg()
            bp    = reg.get("NB_BirimPersonel").get_all() or []
            p_all = reg.get("Personel").get_all() or []
            p_map = {str(p["KimlikNo"]): p.get("AdSoyad", "") for p in p_all}
            bp = sorted(
                [r for r in bp
                 if str(r.get("BirimID", "")) == birim_id
                 and int(r.get("Aktif", 1))],
                key=lambda r: p_map.get(str(r.get("PersonelID", "")), ""))
            self._tbl_p.setRowCount(0)
            for r in bp:
                ri      = self._tbl_p.rowCount()
                pid     = str(r.get("PersonelID", ""))
                ata_id  = r.get("ID", "")
                self._tbl_p.insertRow(ri)
                ad_i = QTableWidgetItem(p_map.get(pid, pid))
                ad_i.setData(Qt.ItemDataRole.UserRole, ata_id)
                self._tbl_p.setItem(ri, 0, ad_i)
                self._tbl_p.setItem(ri, 1, _it(r.get("Rol", "teknisyen")))
                self._tbl_p.setItem(ri, 2,
                    _it(str(r.get("GorevBaslangic", ""))[:10]))
                aktif   = int(r.get("Aktif", 1))
                a_itm   = QTableWidgetItem("Aktif" if aktif else "Pasif")
                a_itm.setForeground(
                    QColor("#2ec98e" if aktif else "#e85555"))
                a_itm.setData(Qt.ItemDataRole.UserRole, ata_id)
                self._tbl_p.setItem(ri, 3, a_itm)
            self._lbl_p_ozet.setText(f"{len(bp)} personel")
        except Exception as e:
            logger.error(f"Personel yÃ¼kle: {e}")

    def _tercihleri_yukle(self):
        if not self._secili_birim_id:
            return
        try:
            reg   = self._reg()
            bp    = reg.get("NB_BirimPersonel").get_all() or []
            p_all = reg.get("Personel").get_all() or []
            p_map = {str(p["KimlikNo"]): p.get("AdSoyad", "") for p in p_all}

            pid_list = sorted(
                [str(r.get("PersonelID", "")) for r in bp
                 if str(r.get("BirimID", "")) == self._secili_birim_id
                 and int(r.get("Aktif", 1))],
                key=lambda p: p_map.get(p, ""))

            tercih_map = {
                str(r.get("PersonelID", "")): r
                for r in (reg.get("NB_PersonelTercih").get_all() or [])
                if str(r.get("BirimID", "")) == self._secili_birim_id
                and int(r.get("Yil", 0)) == self._yil
                and int(r.get("Ay", 0))  == self._ay
            }

            self._tbl_tercih.setRowCount(0)
            fm_sayi = 0
            for pid in pid_list:
                ad    = p_map.get(pid, pid)
                kayit = tercih_map.get(pid, {})
                nobet = kayit.get("NobetTercihi", "zorunlu")
                tip   = kayit.get("HedefTipi", "normal")
                fm    = (nobet == "fazla_mesai_gonullu")
                if fm:
                    fm_sayi += 1
                tip_lbl = next(
                    (l for v, l in HEDEF_TIPLER if v == tip), "Normal")

                ri = self._tbl_tercih.rowCount()
                self._tbl_tercih.insertRow(ri)

                ad_i = QTableWidgetItem(ad)
                ad_i.setData(Qt.ItemDataRole.UserRole, pid)
                self._tbl_tercih.setItem(ri, 0, ad_i)

                fm_itm = QTableWidgetItem("â— FM GÃ¶nÃ¼llÃ¼" if fm else "â—‹")
                fm_itm.setForeground(
                    QColor("#4d9ee8" if fm else "#6b7280"))
                fm_itm.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                fm_itm.setData(Qt.ItemDataRole.UserRole, pid)
                self._tbl_tercih.setItem(ri, 1, fm_itm)

                tip_itm = QTableWidgetItem(tip_lbl)
                tip_itm.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if tip not in ("normal", "rapor", "yillik", "idari"):
                    tip_itm.setForeground(QColor("#f59e0b"))
                tip_itm.setData(Qt.ItemDataRole.UserRole, pid)
                self._tbl_tercih.setItem(ri, 2, tip_itm)

            self._lbl_tercih_ozet.setText(
                f"{len(pid_list)} personel  |  {fm_sayi} FM GÃ¶nÃ¼llÃ¼")
        except Exception as e:
            logger.error(f"Tercih yÃ¼kle: {e}")

    def _birim_ayar_yukle(self, birim_id: str):
        try:
            rows = self._reg().get("NB_BirimAyar").get_all() or []
            ayar = next(
                (r for r in rows
                 if str(r.get("BirimID", "")) == birim_id), None)
            if not ayar:
                return
            self._spn_slot.setValue(int(ayar.get("GunlukSlotSayisi", 4)))
            self._spn_fm_max.setValue(int(ayar.get("FmMaxSaat", 60)))
            max_dk = int(ayar.get("MaxGunlukSureDakika", 720))
            self._spn_max_gun.setValue(2 if max_dk >= 1440 else 1)
            self._chk_hafta_sonu.setChecked(
                bool(int(ayar.get("HaftasonuCalismaVar", 1))))
            self._chk_resmi_tatil.setChecked(
                bool(int(ayar.get("ResmiTatilCalismaVar", 1))))
            dini = ayar.get("DiniBayramCalismaVar",
                            ayar.get("DiniBayramAtama", 0))
            self._chk_dini_bayram.setChecked(bool(int(dini)))
            self._chk_ardisik.setChecked(
                bool(int(ayar.get("ArdisikGunIzinli", 0))))
        except Exception as e:
            logger.error(f"Birim ayar yÃ¼kle: {e}")

    def _birim_ayar_getir(self, birim_id: str) -> dict:
        try:
            rows = self._reg().get("NB_BirimAyar").get_all() or []
            return next(
                (r for r in rows
                 if str(r.get("BirimID", "")) == birim_id), {})
        except Exception as e:
            logger.error(f"Birim ayar getir: {e}")
            return {}

    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    #  SeÃ§im Sinyalleri
    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def _on_birim_sec(self):
        row = self._tbl_birim.currentRow()
        itm = self._tbl_birim.item(row, 0) if row >= 0 else None
        bid = itm.data(Qt.ItemDataRole.UserRole) if itm else ""
        self._secili_birim_id  = bid
        self._secili_birim_adi = itm.text() if itm else ""
        aktif = bool(bid)

        # Header butonlarÄ±
        self._btn_b_dup.setEnabled(aktif)
        self._btn_toggle.setEnabled(aktif)
        self._btn_b_sil.setEnabled(aktif)
        self._tabs.setVisible(aktif)

        # Sekme butonlarÄ±
        for b in [self._btn_grup_yeni, self._btn_sablon,
                  self._btn_p_ata, self._btn_p_migrate,
                  self._btn_ayar_kaydet]:
            b.setEnabled(aktif)

        if not aktif:
            self._lbl_birim_adi.setText("LÃ¼tfen bir birim seÃ§in")
            self._lbl_birim_tip.setText("")
            return

        # Birim bilgisini baÅŸlÄ±ÄŸa yaz
        try:
            rows = self._reg().get("NB_Birim").get_all() or []
            b_data = next(
                (r for r in rows if str(r.get("BirimID", "")) == bid), {})
            tip  = b_data.get("BirimTipi", "")
            kod  = b_data.get("BirimKodu", "")
            aktif_durum = int(b_data.get("Aktif", 1))
            self._lbl_birim_adi.setText(self._secili_birim_adi)
            self._lbl_birim_tip.setText(
                f"{tip}  Â·  {kod}"
                + ("  [PASÄ°F]" if not aktif_durum else ""))
            self._btn_toggle.setText(
                "â¸  Pasife Al" if aktif_durum else "â–¶  Aktife Al")
        except Exception:
            pass

        self._gruplari_yukle(bid)
        self._personelleri_yukle(bid)
        self._tercihleri_yukle()
        self._birim_ayar_yukle(bid)

    def _on_grup_sec(self):
        row = self._tbl_grup.currentRow()
        itm = self._tbl_grup.item(row, 0) if row >= 0 else None
        gid = itm.data(Qt.ItemDataRole.UserRole) if itm else ""
        self._secili_grup_id = gid
        aktif = bool(gid)
        for b in [self._btn_grup_dup, self._btn_grup_sil, self._btn_v_yeni]:
            b.setEnabled(aktif)
        if aktif:
            self._lbl_grup_adi.setText(itm.text() if itm else "")
            self._vardiyeleri_yukle(gid)

    def _on_v_sec(self):
        var = self._tbl_v.currentRow() >= 0
        self._btn_v_dup.setEnabled(var)
        self._btn_v_sil.setEnabled(var)

    def _on_p_sec(self):
        self._btn_p_cikar.setEnabled(self._tbl_p.currentRow() >= 0)

    def _on_tercih_sec(self):
        self._btn_tercih_dup.setEnabled(
            self._tbl_tercih.currentRow() >= 0)

    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    #  Birim AksiyonlarÄ±
    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def _birim_sec_by_id(self, birim_id: str):
        for row in range(self._tbl_birim.rowCount()):
            itm = self._tbl_birim.item(row, 0)
            if itm and itm.data(Qt.ItemDataRole.UserRole) == birim_id:
                self._tbl_birim.setCurrentCell(row, 0)
                break

    def _birim_yeni(self):
        dialog = _BirimDialog(parent=self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        svc = self._birim_svc()
        if not svc:
            QMessageBox.critical(self, "Hata", "Birim servisine eriÅŸilemedi.")
            return
        veri  = dialog.get_data()
        sonuc = svc.birim_ekle(
            birim_adi  = veri["BirimAdi"],
            birim_kodu = veri["BirimKodu"],
            birim_tipi = veri["BirimTipi"],
            sira       = veri["Sira"],
            aciklama   = veri["Aciklama"],
        )
        if sonuc.basarili:
            self._birimleri_yukle()
            self._birim_sec_by_id((sonuc.veri or {}).get("BirimID", ""))
        else:
            QMessageBox.critical(self, "Hata", str(sonuc.hata))

    def _birim_duzenle(self):
        bid = self._secili_birim_id
        if not bid:
            return
        svc = self._birim_svc()
        if not svc:
            QMessageBox.critical(self, "Hata", "Birim servisine eriÅŸilemedi.")
            return
        kayit_s = svc.get_birim(bid)
        if not kayit_s.basarili:
            QMessageBox.critical(self, "Hata", "Birim bilgisi alÄ±namadÄ±.")
            return
        dialog = _BirimDialog(kayit=kayit_s.veri, parent=self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        veri  = dialog.get_data()
        sonuc = svc.birim_guncelle(
            birim_id   = bid,
            birim_adi  = veri["BirimAdi"],
            birim_kodu = veri["BirimKodu"],
            birim_tipi = veri["BirimTipi"],
            sira       = veri["Sira"],
            aciklama   = veri["Aciklama"],
        )
        if sonuc.basarili:
            self._birimleri_yukle()
            self._birim_sec_by_id(bid)
        else:
            QMessageBox.critical(self, "Hata", str(sonuc.hata))

    def _birim_toggle(self):
        bid = self._secili_birim_id
        if not bid:
            return
        svc   = self._birim_svc()
        sonuc = svc.birim_aktif_toggle(bid)
        if sonuc.basarili:
            self._birimleri_yukle()
            self._birim_sec_by_id(bid)
        else:
            QMessageBox.critical(self, "Hata", str(sonuc.hata))

    def _birim_sil(self):
        bid = self._secili_birim_id
        if not bid:
            return
        cevap = QMessageBox.question(
            self, "Onay",
            f"'{self._secili_birim_adi}' birimi silinsin mi?\n\n"
            "BaÄŸlÄ± vardiya grubu yoksa silinir. Bu iÅŸlem geri alÄ±nabilir.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if cevap != QMessageBox.StandardButton.Yes:
            return
        svc   = self._birim_svc()
        sonuc = svc.birim_sil(bid)
        if sonuc.basarili:
            self._secili_birim_id  = ""
            self._secili_birim_adi = ""
            self._birimleri_yukle()
        else:
            QMessageBox.critical(self, "Hata", str(sonuc.hata))

    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    #  Birim AyarlarÄ±
    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def _birim_ayar_kaydet(self):
        bid = self._secili_birim_id
        if not bid:
            return
        try:
            reg  = self._reg()
            rows = reg.get("NB_BirimAyar").get_all() or []
            ayar = next(
                (r for r in rows
                 if str(r.get("BirimID", "")) == bid), None)
            max_dk = 1440 if self._spn_max_gun.value() >= 2 else 720
            veri = {
                "GunlukSlotSayisi":      self._spn_slot.value(),
                "FmMaxSaat":             self._spn_fm_max.value(),
                "MaxGunlukSureDakika":   max_dk,
                "HaftasonuCalismaVar":   1 if self._chk_hafta_sonu.isChecked() else 0,
                "ResmiTatilCalismaVar":  1 if self._chk_resmi_tatil.isChecked() else 0,
                "DiniBayramCalismaVar":  1 if self._chk_dini_bayram.isChecked() else 0,
                "ArdisikGunIzinli":      1 if self._chk_ardisik.isChecked() else 0,
                "updated_at":            _simdi(),
            }
            if ayar:
                reg.get("NB_BirimAyar").update(ayar["AyarID"], veri)
            else:
                reg.get("NB_BirimAyar").insert({
                    "AyarID":   _yeni_id(),
                    "BirimID":  bid,
                    "created_at": _simdi(),
                    **veri,
                })
            QMessageBox.information(self, "Tamam", "Ayarlar kaydedildi.")
        except Exception as e:
            logger.error(f"Birim ayar kaydet: {e}")
            QMessageBox.critical(self, "Hata", str(e))

    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    #  Grup AksiyonlarÄ±
    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def _grup_yeni(self):
        dialog = _GrupDialog(parent=self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            self._reg().get("NB_VardiyaGrubu").insert({
                "GrupID":  _yeni_id(),
                "BirimID": self._secili_birim_id,
                "created_at": _simdi(),
                **dialog.get_data(),
            })
            self._gruplari_yukle(self._secili_birim_id)
        except Exception as e:
            QMessageBox.critical(self, "Hata", str(e))

    def _grup_duzenle(self):
        row = self._tbl_grup.currentRow()
        if row < 0:
            return
        itm = self._tbl_grup.item(row, 0)
        gid = itm.data(Qt.ItemDataRole.UserRole)
        try:
            rows  = self._reg().get("NB_VardiyaGrubu").get_all() or []
            kayit = next((r for r in rows if r["GrupID"] == gid), None)
            dialog = _GrupDialog(kayit=kayit, parent=self)
            if dialog.exec() != QDialog.DialogCode.Accepted:
                return
            self._reg().get("NB_VardiyaGrubu").update(
                gid, {**dialog.get_data(), "updated_at": _simdi()})
            self._gruplari_yukle(self._secili_birim_id)
        except Exception as e:
            QMessageBox.critical(self, "Hata", str(e))

    def _grup_sil(self):
        row = self._tbl_grup.currentRow()
        if row < 0:
            return
        itm  = self._tbl_grup.item(row, 0)
        gid  = itm.data(Qt.ItemDataRole.UserRole)
        isim = itm.text()
        if QMessageBox.question(
            self, "Grup Sil",
            f"'{isim}' ve baÄŸlÄ± tÃ¼m vardiyalar silinecek. Emin misiniz?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        ) != QMessageBox.StandardButton.Yes:
            return
        try:
            reg = self._reg()
            for v in (reg.get("NB_Vardiya").get_all() or []):
                if str(v.get("GrupID", "")) == gid:
                    reg.get("NB_Vardiya").delete(v["VardiyaID"])
            reg.get("NB_VardiyaGrubu").delete(gid)
            self._gruplari_yukle(self._secili_birim_id)
        except Exception as e:
            QMessageBox.critical(self, "Hata", str(e))

    def _grup_sablon(self):
        """SÄ±k kullanÄ±lan ÅŸablonlardan hÄ±zlÄ± grup + vardiya oluÅŸtur."""
        sablonlar = {
            "GÃ¼ndÃ¼z / Gece (2 vardiya)": [
                ("GÃ¼ndÃ¼z VardiyasÄ±", "08:00", "20:00", 720, "ana"),
                ("Gece VardiyasÄ±",   "20:00", "08:00", 720, "ana"),
            ],
            "Sabah / Ã–ÄŸle / AkÅŸam (3 vardiya)": [
                ("Sabah VardiyasÄ±",  "07:00", "15:00", 480, "ana"),
                ("Ã–ÄŸle VardiyasÄ±",   "15:00", "23:00", 480, "ana"),
                ("Gece VardiyasÄ±",   "23:00", "07:00", 480, "ana"),
            ],
            "Tek Vardiya (08-17)": [
                ("Mesai VardiyasÄ±",  "08:00", "17:00", 540, "ana"),
            ],
        }
        sablon_adi, ok = _secim_dialog(
            list(sablonlar.keys()), "Åablon SeÃ§",
            "OluÅŸturulacak ÅŸablonu seÃ§in:", parent=self)
        if not ok or not sablon_adi:
            return
        try:
            reg    = self._reg()
            gid    = _yeni_id()
            reg.get("NB_VardiyaGrubu").insert({
                "GrupID":  gid,
                "BirimID": self._secili_birim_id,
                "GrupAdi": sablon_adi,
                "Sira":    1,
                "Aktif":   1,
                "created_at": _simdi(),
            })
            for i, (adi, bas, bit, sure, rol) in enumerate(
                    sablonlar[sablon_adi], start=1):
                reg.get("NB_Vardiya").insert({
                    "VardiyaID": _yeni_id(),
                    "GrupID":   gid,
                    "BirimID":  self._secili_birim_id,
                    "VardiyaAdi": adi,
                    "BasSaat":  bas,
                    "BitSaat":  bit,
                    "SureDakika": sure,
                    "Rol":      rol,
                    "MinPersonel": 1,
                    "Sira":     i,
                    "Aktif":    1,
                    "created_at": _simdi(),
                })
            self._gruplari_yukle(self._secili_birim_id)
        except Exception as e:
            QMessageBox.critical(self, "Hata", str(e))

    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    #  Vardiya AksiyonlarÄ±
    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def _vardiya_yeni(self):
        birim_ayar = self._birim_ayar_getir(self._secili_birim_id)
        dialog = _VardiyaDialog(birim_ayar=birim_ayar, parent=self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            self._reg().get("NB_Vardiya").insert({
                "VardiyaID": _yeni_id(),
                "GrupID":   self._secili_grup_id,
                "BirimID":  self._secili_birim_id,
                "created_at": _simdi(),
                **dialog.get_data(),
            })
            self._vardiya_icin_birim_ayar_kaydet(
                self._secili_birim_id,
                dialog.get_birim_ayar_data())
            self._vardiyeleri_yukle(self._secili_grup_id)
        except Exception as e:
            QMessageBox.critical(self, "Hata", str(e))

    def _vardiya_duzenle(self):
        row = self._tbl_v.currentRow()
        if row < 0:
            return
        itm = self._tbl_v.item(row, 0)
        vid = itm.data(Qt.ItemDataRole.UserRole)
        try:
            rows  = self._reg().get("NB_Vardiya").get_all() or []
            kayit = next((r for r in rows if r["VardiyaID"] == vid), None)
            birim_ayar = self._birim_ayar_getir(self._secili_birim_id)
            dialog = _VardiyaDialog(kayit=kayit, birim_ayar=birim_ayar,
                                    parent=self)
            if dialog.exec() != QDialog.DialogCode.Accepted:
                return
            self._reg().get("NB_Vardiya").update(
                vid, {**dialog.get_data(), "updated_at": _simdi()})
            self._vardiya_icin_birim_ayar_kaydet(
                self._secili_birim_id,
                dialog.get_birim_ayar_data())
            self._vardiyeleri_yukle(self._secili_grup_id)
        except Exception as e:
            QMessageBox.critical(self, "Hata", str(e))

    def _vardiya_sil(self):
        row = self._tbl_v.currentRow()
        if row < 0:
            return
        itm  = self._tbl_v.item(row, 0)
        vid  = itm.data(Qt.ItemDataRole.UserRole)
        isim = itm.text()
        if QMessageBox.question(
            self, "Vardiya Sil",
            f"'{isim}' silinecek. Emin misiniz?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        ) != QMessageBox.StandardButton.Yes:
            return
        try:
            self._reg().get("NB_Vardiya").delete(vid)
            self._vardiyeleri_yukle(self._secili_grup_id)
        except Exception as e:
            QMessageBox.critical(self, "Hata", str(e))

    def _vardiya_icin_birim_ayar_kaydet(
            self, birim_id: str, secim: dict):
        """Vardiya formundaki hafta sonu / tatil seÃ§imini NB_BirimAyar'a yansÄ±t."""
        if not birim_id:
            return
        try:
            reg  = self._reg()
            rows = reg.get("NB_BirimAyar").get_all() or []
            ayar = next(
                (r for r in rows
                 if str(r.get("BirimID", "")) == birim_id), None)
            veri = {
                "HaftasonuNobetZorunlu": int(secim.get("HaftasonuNobetZorunlu", 1)),
                "DiniBayramAtama":       int(secim.get("DiniBayramAtama", 1)),
                "updated_at":            _simdi(),
            }
            if ayar:
                reg.get("NB_BirimAyar").update(ayar["AyarID"], veri)
            else:
                reg.get("NB_BirimAyar").insert({
                    "AyarID":   _yeni_id(),
                    "BirimID":  birim_id,
                    "GunlukSlotSayisi": self._spn_slot.value(),
                    "FmMaxSaat":        self._spn_fm_max.value(),
                    "MaxGunlukSureDakika": (
                        1440 if self._spn_max_gun.value() >= 2 else 720),
                    "created_at": _simdi(),
                    **veri,
                })
        except Exception as e:
            logger.error(f"Vardiya birim ayar kaydet: {e}")

    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    #  Personel AksiyonlarÄ±
    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def _personel_ata(self):
        try:
            reg   = self._reg()
            p_all = reg.get("Personel").get_all() or []
            p_map = {str(p["KimlikNo"]): p.get("AdSoyad", "") for p in p_all}
            pid_list = sorted(
                [str(p["KimlikNo"]) for p in p_all
                 if str(p.get("Durum", "Aktif")).strip() == "Aktif"],
                key=lambda p: p_map.get(p, ""))
            bp = reg.get("NB_BirimPersonel").get_all() or []
            mevcutlar = {
                str(r.get("PersonelID", "")) for r in bp
                if str(r.get("BirimID", "")) == self._secili_birim_id
                and int(r.get("Aktif", 1))
            }
            dialog = _PersonelAtaDialog(
                pid_list, p_map, mevcutlar, parent=self)
            if dialog.exec() != QDialog.DialogCode.Accepted:
                return
            for pid in dialog.get_secilen():
                reg.get("NB_BirimPersonel").insert({
                    "ID":             _yeni_id(),
                    "BirimID":        self._secili_birim_id,
                    "PersonelID":     pid,
                    "Rol":            "teknisyen",
                    "AnabirimMi":     1,
                    "Aktif":          1,
                    "GorevBaslangic": date.today().isoformat(),
                    "created_at":     _simdi(),
                })
            self._personelleri_yukle(self._secili_birim_id)
            self._tercihleri_yukle()
        except Exception as e:
            QMessageBox.critical(self, "Hata", str(e))

    def _personel_migrate(self):
        """GorevYeri = birim adÄ± olan tÃ¼m personeli aktar."""
        if not self._secili_birim_adi:
            return
        try:
            reg   = self._reg()
            p_all = reg.get("Personel").get_all() or []
            bp    = reg.get("NB_BirimPersonel").get_all() or []
            mevcutlar = {
                str(r.get("PersonelID", "")) for r in bp
                if str(r.get("BirimID", "")) == self._secili_birim_id
            }
            eklendi = 0
            for p in p_all:
                pid = str(p["KimlikNo"])
                if (str(p.get("GorevYeri", "")).strip() == self._secili_birim_adi
                        and pid not in mevcutlar):
                    reg.get("NB_BirimPersonel").insert({
                        "ID":             _yeni_id(),
                        "BirimID":        self._secili_birim_id,
                        "PersonelID":     pid,
                        "Rol":            "teknisyen",
                        "AnabirimMi":     1,
                        "Aktif":          1,
                        "GorevBaslangic": date.today().isoformat(),
                        "created_at":     _simdi(),
                    })
                    eklendi += 1
            QMessageBox.information(
                self, "TamamlandÄ±", f"{eklendi} personel aktarÄ±ldÄ±.")
            self._personelleri_yukle(self._secili_birim_id)
            self._tercihleri_yukle()
        except Exception as e:
            QMessageBox.critical(self, "Hata", str(e))

    def _personel_cikar(self):
        row = self._tbl_p.currentRow()
        if row < 0:
            return
        itm    = self._tbl_p.item(row, 0)
        ata_id = itm.data(Qt.ItemDataRole.UserRole)
        isim   = itm.text()
        if QMessageBox.question(
            self, "GÃ¶revden Al",
            f"'{isim}' bu birimden gÃ¶revden alÄ±nacak. Emin misiniz?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        ) != QMessageBox.StandardButton.Yes:
            return
        try:
            self._reg().get("NB_BirimPersonel").update(
                ata_id, {"Aktif": 0, "updated_at": _simdi()})
            self._personelleri_yukle(self._secili_birim_id)
            self._tercihleri_yukle()
        except Exception as e:
            QMessageBox.critical(self, "Hata", str(e))

    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    #  NÃ¶bet Tercihleri AksiyonlarÄ±
    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def _tercih_ay_geri(self):
        if self._ay == 1:
            self._ay, self._yil = 12, self._yil - 1
        else:
            self._ay -= 1
        self._lbl_tercih_ay.setText(f"{_AY_TR[self._ay]} {self._yil}")
        self._tercihleri_yukle()

    def _tercih_ay_ileri(self):
        if self._ay == 12:
            self._ay, self._yil = 1, self._yil + 1
        else:
            self._ay += 1
        self._lbl_tercih_ay.setText(f"{_AY_TR[self._ay]} {self._yil}")
        self._tercihleri_yukle()

    def _tercih_duzenle(self):
        row = self._tbl_tercih.currentRow()
        if row < 0:
            return
        itm = self._tbl_tercih.item(row, 0)
        pid = itm.data(Qt.ItemDataRole.UserRole)
        ad  = itm.text()
        try:
            reg    = self._reg()
            t_rows = reg.get("NB_PersonelTercih").get_all() or []
            kayit  = next(
                (r for r in t_rows
                 if str(r.get("PersonelID", "")) == pid
                 and str(r.get("BirimID", ""))   == self._secili_birim_id
                 and int(r.get("Yil", 0))         == self._yil
                 and int(r.get("Ay", 0))           == self._ay),
                None)
            dialog = _TercihDialog(
                pid, ad, self._yil, self._ay, kayit, parent=self)
            if dialog.exec() != QDialog.DialogCode.Accepted:
                return
            veri = dialog.get_data()
            if kayit:
                reg.get("NB_PersonelTercih").update(
                    kayit["TercihID"],
                    {**veri, "updated_at": _simdi()})
            else:
                reg.get("NB_PersonelTercih").insert({
                    "TercihID":   _yeni_id(),
                    "PersonelID": pid,
                    "BirimID":    self._secili_birim_id,
                    "Yil":        self._yil,
                    "Ay":         self._ay,
                    "created_at": _simdi(),
                    **veri,
                })
            self._tercihleri_yukle()
        except Exception as e:
            QMessageBox.critical(self, "Hata", str(e))

    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    #  DÄ±ÅŸ ArayÃ¼z
    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def load_data(self):
        """DÄ±ÅŸarÄ±dan tetiklenen yenileme (sekme deÄŸiÅŸimi, vb.)."""
        if self._db:
            self._birimleri_yukle()
            if self._secili_birim_id:
                self._gruplari_yukle(self._secili_birim_id)
                self._personelleri_yukle(self._secili_birim_id)
                self._tercihleri_yukle()


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
#  YardÄ±mcÄ±: Basit seÃ§im dialogu (ÅŸablon vs.)
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

def _secim_dialog(secenekler: list[str], baslik: str,
                  mesaj: str, parent=None) -> tuple[str, bool]:
    """Bir ComboBox iÃ§eren kÃ¼Ã§Ã¼k seÃ§im dialogu. (seÃ§im, tamam) dÃ¶ner."""
    dlg = QDialog(parent)
    dlg.setWindowTitle(baslik)
    dlg.setModal(True)
    dlg.setMinimumWidth(320)
    dlg.setProperty("bg-role", "page")
    lay = QVBoxLayout(dlg)
    lay.setContentsMargins(20, 20, 20, 20)
    lay.setSpacing(10)
    lay.addWidget(QLabel(mesaj))
    cmb = QComboBox()
    for s in secenekler:
        cmb.addItem(s)
    lay.addWidget(cmb)
    btns = QDialogButtonBox(
        QDialogButtonBox.StandardButton.Ok |
        QDialogButtonBox.StandardButton.Cancel)
    btns.accepted.connect(dlg.accept)
    btns.rejected.connect(dlg.reject)
    lay.addWidget(btns)
    ok = (dlg.exec() == QDialog.DialogCode.Accepted)
    return cmb.currentText(), ok
