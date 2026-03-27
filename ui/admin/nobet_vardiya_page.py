# -*- coding: utf-8 -*-
"""
nobet_vardiya_page.py — Birim & Vardiya & Personel Yönetimi

Yerleşim:
  Sol   (200px) — Birim listesi + Birim Ayarları (Slot, FM Max)
  Orta  (260px) — Vardiya Grupları
  Sağ   (esnek) — Sekmeler: Vardiyalar | Personel | Nöbet Tercihleri

Özellikler:
  - Birim: ekle/düzenle, slot sayısı ve FM max saat ayarı
  - Vardiya grubu: ekle/düzenle/sil, hazır şablon
  - Vardiya: ekle/düzenle/sil (VardiyaAdi, BasSaat, BitSaat, Süre, Rol)
  - Personel: ata / GorevYeri'nden aktar / görevden al
  - Nöbet Tercihleri: ay bazlı FM Gönüllü + HedefTipi (Normal/Emzirme/Sendika/Şua...)
"""
from __future__ import annotations

import uuid
from datetime import date, datetime

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QFrame, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QGroupBox, QFormLayout, QSpinBox,
    QLineEdit, QComboBox, QTabWidget, QDialog, QDialogButtonBox,
    QMessageBox, QSplitter, QCheckBox, QTimeEdit,
)
from PySide6.QtCore import QTime

from core.di import get_registry
from core.logger import logger

_simdi  = lambda: datetime.now().isoformat(sep=" ", timespec="seconds")
_yeni_id = lambda: str(uuid.uuid4())

_AY_TR = ["","Ocak","Şubat","Mart","Nisan","Mayıs","Haziran",
           "Temmuz","Ağustos","Eylül","Ekim","Kasım","Aralık"]

HEDEF_TIPLER = [
    ("normal",  "Normal  (7.0 s/gün)"),
    ("emzirme", "Emzirme (5.5 s/gün)"),
    ("sendika", "Sendika (6.2 s/gün)"),
    ("sua",     "Şua İzni (0 s/gün)"),
    ("rapor",   "Raporlu (7.0 s/gün)"),
    ("yillik",  "Yıllık İzin (7.0 s/gün)"),
    ("idari",   "İdari İzin (7.0 s/gün)"),
]


def _it(text: str, user=None) -> QTableWidgetItem:
    it = QTableWidgetItem(str(text))
    if user is not None:
        it.setData(Qt.ItemDataRole.UserRole, user)
    it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
    return it


# ══════════════════════════════════════════════════════════════
#  Dialoglar
# ══════════════════════════════════════════════════════════════

class _BirimDialog(QDialog):
    def __init__(self, kayit: dict = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Birim Düzenle" if kayit else "Yeni Birim")
        self.setModal(True)
        self.setMinimumWidth(320)
        self.setProperty("bg-role", "page")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 20, 20, 20)
        form = QFormLayout()
        self._adi = QLineEdit((kayit or {}).get("BirimAdi", ""))
        self._adi.setPlaceholderText("Birim adı")
        form.addRow("Birim Adı:", self._adi)
        self._aciklama = QLineEdit((kayit or {}).get("Aciklama", ""))
        form.addRow("Açıklama:", self._aciklama)
        lay.addLayout(form)
        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        lay.addWidget(btns)

    def get_data(self) -> dict:
        return {"BirimAdi": self._adi.text().strip(),
                "Aciklama": self._aciklama.text().strip()}


class _GrupDialog(QDialog):
    def __init__(self, kayit: dict = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Grup Düzenle" if kayit else "Yeni Grup")
        self.setModal(True)
        self.setMinimumWidth(320)
        self.setProperty("bg-role", "page")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 20, 20, 20)
        form = QFormLayout()
        self._adi = QLineEdit((kayit or {}).get("GrupAdi", ""))
        form.addRow("Grup Adı:", self._adi)
        self._sira = QSpinBox()
        self._sira.setRange(1, 20)
        self._sira.setValue(int((kayit or {}).get("Sira", 1)))
        form.addRow("Sıra:", self._sira)
        self._aktif = QCheckBox("Aktif")
        self._aktif.setChecked(bool(int((kayit or {}).get("Aktif", 1))))
        form.addRow("", self._aktif)
        lay.addLayout(form)
        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        lay.addWidget(btns)

    def get_data(self) -> dict:
        return {
            "GrupAdi": self._adi.text().strip(),
            "Sira":    self._sira.value(),
            "Aktif":   1 if self._aktif.isChecked() else 0,
        }


class _VardiyaDialog(QDialog):
    def __init__(self, kayit: dict = None, birim_ayar: dict = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Vardiya Düzenle" if kayit else "Yeni Vardiya")
        self.setModal(True)
        self.setMinimumWidth(360)
        self.setProperty("bg-role", "page")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 20, 20, 20)
        form = QFormLayout()

        self._adi = QLineEdit((kayit or {}).get("VardiyaAdi", ""))
        form.addRow("Vardiya Adı:", self._adi)

        def _time_widget(val: str, default: str) -> QTimeEdit:
            w = QTimeEdit()
            w.setDisplayFormat("HH:mm")
            t = val or default
            w.setTime(QTime(*[int(x) for x in t.split(":")[:2]]))
            return w

        self._bas = _time_widget((kayit or {}).get("BasSaat", ""), "08:00")
        form.addRow("Başlangıç:", self._bas)

        self._bit = _time_widget((kayit or {}).get("BitSaat", ""), "20:00")
        form.addRow("Bitiş:", self._bit)

        self._sure = QSpinBox()
        self._sure.setRange(0, 1440)
        self._sure.setSuffix(" dk")
        self._sure.setValue(int((kayit or {}).get("SureDakika", 720)))
        form.addRow("Süre:", self._sure)

        self._rol = QComboBox()
        self._rol.addItem("Ana Vardiya", userData="ana")
        self._rol.addItem("Yardımcı", userData="yardimci")
        self._rol.setCurrentIndex(
            0 if (kayit or {}).get("Rol","ana") == "ana" else 1)
        form.addRow("Rol:", self._rol)

        self._sira = QSpinBox()
        self._sira.setRange(1, 20)
        self._sira.setValue(int((kayit or {}).get("Sira", 1)))
        form.addRow("Sıra:", self._sira)

        self._aktif = QCheckBox("Aktif")
        self._aktif.setChecked(bool(int((kayit or {}).get("Aktif", 1))))
        form.addRow("", self._aktif)

        self._haftasonu = QCheckBox("Bu birimde hafta sonu çalışma var")
        self._haftasonu.setChecked(
            bool(int((birim_ayar or {}).get("HaftasonuNobetZorunlu", 1))))
        form.addRow("Hafta Sonu:", self._haftasonu)

        self._tatil = QCheckBox("Bu birimde tatil günlerinde çalışma var")
        self._tatil.setChecked(
            bool(int((birim_ayar or {}).get("DiniBayramAtama", 1))))
        form.addRow("Tatiller:", self._tatil)

        lay.addLayout(form)
        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        lay.addWidget(btns)

    def get_data(self) -> dict:
        return {
            "VardiyaAdi": self._adi.text().strip(),
            "BasSaat":    self._bas.time().toString("HH:mm"),
            "BitSaat":    self._bit.time().toString("HH:mm"),
            "SureDakika": self._sure.value(),
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
    def __init__(self, pid_listesi: list, p_map: dict,
                 mevcutlar: set, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Personel Ata")
        self.setModal(True)
        self.setMinimumSize(400, 500)
        self.setProperty("bg-role", "page")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.setSpacing(8)

        ara = QLineEdit()
        ara.setPlaceholderText("Ara...")
        ara.textChanged.connect(self._filtrele)
        lay.addWidget(ara)

        self._tbl = QTableWidget(0, 2)
        self._tbl.setHorizontalHeaderLabels(["Ad Soyad", "Durum"])
        self._tbl.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch)
        self._tbl.setColumnWidth(1, 80)
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
            self._tbl.setItem(ri, 1,
                QTableWidgetItem("Atanmış" if mevcut else "—"))

    def get_secilen(self) -> list:
        mevcutlar = {pid for pid, _, m in self._tum if m}
        sonuc = []
        for ri in range(self._tbl.rowCount()):
            itm = self._tbl.item(ri, 0)
            if (itm and itm.checkState() == Qt.CheckState.Checked):
                pid = itm.data(Qt.ItemDataRole.UserRole)
                if pid not in mevcutlar:
                    sonuc.append(pid)
        return sonuc


class _TercihDialog(QDialog):
    """Aylık nöbet tercihi: FM Gönüllü + HedefTipi."""
    def __init__(self, pid: str, ad: str, yil: int, ay: int,
                 kayit: dict = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Nöbet Tercihi — {ad}")
        self.setModal(True)
        self.setMinimumWidth(380)
        self.setProperty("bg-role", "page")

        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.setSpacing(12)

        baslik = QLabel(f"<b>{ad}</b>  —  {_AY_TR[ay]} {yil}")
        baslik.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(baslik)

        form = QFormLayout()

        self._chk_fm = QCheckBox("FM Gönüllüsü")
        self._chk_fm.setChecked(
            (kayit or {}).get("NobetTercihi","") == "fazla_mesai_gonullu")
        self._chk_fm.setToolTip(
            "İşaretliyse boş slotlara fazla mesai olarak atanabilir")
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


# ══════════════════════════════════════════════════════════════
#  Ana Sayfa
# ══════════════════════════════════════════════════════════════

class NobetVardiyaPage(QWidget):

    def __init__(self, db=None, action_guard=None, parent=None):
        super().__init__(parent)
        self._db   = db
        self._ag   = action_guard
        self._yil  = date.today().year
        self._ay   = date.today().month
        self._secili_birim_id  = ""
        self._secili_birim_adi = ""
        self._secili_grup_id   = ""
        self.setProperty("bg-role", "page")
        self._build()
        if db:
            self._birimleri_yukle()

    def _reg(self):
        return get_registry(self._db)

    def _btn(self, metin: str, stil: str = "secondary",
             h: int = 26) -> QPushButton:
        b = QPushButton(metin)
        b.setProperty("style-role", stil)
        b.setFixedHeight(h)
        return b

    # ──────────────────────────────────────────────────────────
    #  UI
    # ──────────────────────────────────────────────────────────

    def _build(self):
        ana = QHBoxLayout(self)
        ana.setContentsMargins(0, 0, 0, 0)
        ana.setSpacing(0)
        spl = QSplitter(Qt.Orientation.Horizontal)
        spl.addWidget(self._build_sol())
        spl.addWidget(self._build_orta())
        spl.addWidget(self._build_sag())
        spl.setSizes([200, 260, 600])
        ana.addWidget(spl)

    # ── Sol: Birimler + Ayarlar ────────────────────────────────

    def _build_sol(self) -> QWidget:
        w = QWidget()
        w.setProperty("bg-role", "panel")
        lay = QVBoxLayout(w)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.setSpacing(6)

        tb = QHBoxLayout()
        self._btn_birim_yeni = self._btn("+ Birim", "action")
        self._btn_birim_yeni.clicked.connect(self._birim_yeni)
        tb.addWidget(self._btn_birim_yeni)
        self._btn_birim_dup = self._btn("✎")
        self._btn_birim_dup.setFixedWidth(28)
        self._btn_birim_dup.setEnabled(False)
        self._btn_birim_dup.clicked.connect(self._birim_duzenle)
        tb.addWidget(self._btn_birim_dup)
        lay.addLayout(tb)

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

        # Birim Ayarları
        grp = QGroupBox("Birim Ayarları")
        grp.setProperty("style-role", "group")
        gl = QVBoxLayout(grp)
        gl.setContentsMargins(6, 8, 6, 6)
        form = QFormLayout()
        form.setSpacing(6)

        self._spn_slot = QSpinBox()
        self._spn_slot.setRange(1, 10)
        self._spn_slot.setValue(4)
        self._spn_slot.setToolTip("Her vardiya için günlük kaç farklı kişi atanır")
        form.addRow("Günlük Slot:", self._spn_slot)

        self._spn_fm_max = QSpinBox()
        self._spn_fm_max.setRange(0, 300)
        self._spn_fm_max.setValue(60)
        self._spn_fm_max.setSuffix(" saat")
        self._spn_fm_max.setToolTip("FM Gönüllünün aylık max fazla mesai saati")
        form.addRow("FM Max:", self._spn_fm_max)

        self._spn_max_gun = QSpinBox()
        self._spn_max_gun.setRange(1, 2)
        self._spn_max_gun.setValue(1)
        self._spn_max_gun.setSuffix(" vardiya/gün")
        self._spn_max_gun.setToolTip(
            "1 = Personel günde sadece 1 vardiya tutabilir (12s)\n"
            "2 = Personel aynı günde gündüz+gece tutabilir (24s)")
        form.addRow("Max Günlük:", self._spn_max_gun)

        self._chk_hafta_sonu = QCheckBox("Atama yapılır")
        self._chk_hafta_sonu.setChecked(True)
        self._chk_hafta_sonu.setToolTip(
            "Kapalıysa Cumartesi/Pazar günlerinde bu birim için atama yapılmaz.")
        form.addRow("Hafta Sonu:", self._chk_hafta_sonu)

        self._chk_resmi_tatil = QCheckBox("Atama yapılır")
        self._chk_resmi_tatil.setChecked(True)
        self._chk_resmi_tatil.setToolTip(
            "Kapalıysa resmi/idari tatillerde bu birim için atama yapılmaz.")
        form.addRow("Resmi Tatil:", self._chk_resmi_tatil)

        self._chk_dini_bayram = QCheckBox("Atama yapılır")
        self._chk_dini_bayram.setChecked(False)
        self._chk_dini_bayram.setToolTip(
            "Kapalıysa dini bayram günlerinde bu birim için atama yapılmaz.")
        form.addRow("Dini Bayram:", self._chk_dini_bayram)

        gl.addLayout(form)
        self._btn_ayar_kaydet = self._btn("Kaydet", "action")
        self._btn_ayar_kaydet.setEnabled(False)
        self._btn_ayar_kaydet.clicked.connect(self._birim_ayar_kaydet)
        gl.addWidget(self._btn_ayar_kaydet)
        lay.addWidget(grp)
        return w

    # ── Orta: Vardiya Grupları ─────────────────────────────────

    def _build_orta(self) -> QWidget:
        w = QWidget()
        w.setProperty("bg-role", "page")
        lay = QVBoxLayout(w)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.setSpacing(4)

        lbl = QLabel("Vardiya Grupları")
        lbl.setProperty("style-role", "section-title")
        lay.addWidget(lbl)

        tb = QHBoxLayout()
        self._btn_grup_yeni = self._btn("+ Grup", "action")
        self._btn_grup_yeni.setEnabled(False)
        self._btn_grup_yeni.clicked.connect(self._grup_yeni)
        tb.addWidget(self._btn_grup_yeni)
        self._btn_sablon = self._btn("⚡ Şablon")
        self._btn_sablon.setEnabled(False)
        self._btn_sablon.clicked.connect(self._sablon_uygula)
        tb.addWidget(self._btn_sablon)
        tb.addStretch()
        lay.addLayout(tb)

        self._tbl_grup = QTableWidget(0, 3)
        self._tbl_grup.setHorizontalHeaderLabels(["Grup Adı", "Sıra", "Aktif"])
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
        self._tbl_grup.doubleClicked.connect(self._grup_duzenle)
        self._tbl_grup.selectionModel().selectionChanged.connect(
            self._on_grup_sec)
        lay.addWidget(self._tbl_grup, 1)

        alt = QHBoxLayout()
        self._btn_grup_dup = self._btn("✎")
        self._btn_grup_dup.setFixedWidth(28)
        self._btn_grup_dup.setEnabled(False)
        self._btn_grup_dup.clicked.connect(self._grup_duzenle)
        alt.addWidget(self._btn_grup_dup)
        self._btn_grup_sil = self._btn("✕", "danger")
        self._btn_grup_sil.setFixedWidth(28)
        self._btn_grup_sil.setEnabled(False)
        self._btn_grup_sil.clicked.connect(self._grup_sil)
        alt.addWidget(self._btn_grup_sil)
        alt.addStretch()
        lay.addLayout(alt)
        return w

    # ── Sağ: Sekmeler ─────────────────────────────────────────

    def _build_sag(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        self._tabs = QTabWidget()
        self._tabs.addTab(self._build_vardiya_tab(), "Vardiyalar")
        self._tabs.addTab(self._build_personel_tab(), "Personel")
        self._tabs.addTab(self._build_tercih_tab(), "Nöbet Tercihleri")
        lay.addWidget(self._tabs)
        return w

    def _build_vardiya_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.setSpacing(4)

        self._lbl_grup_adi = QLabel("— Grup seçin —")
        self._lbl_grup_adi.setProperty("style-role", "section-title")
        lay.addWidget(self._lbl_grup_adi)

        tb = QHBoxLayout()
        self._btn_v_yeni = self._btn("+ Vardiya", "action")
        self._btn_v_yeni.setEnabled(False)
        self._btn_v_yeni.clicked.connect(self._vardiya_yeni)
        tb.addWidget(self._btn_v_yeni)
        tb.addStretch()
        lay.addLayout(tb)

        self._tbl_v = QTableWidget(0, 6)
        self._tbl_v.setHorizontalHeaderLabels(
            ["Vardiya Adı", "Başlangıç", "Bitiş", "Süre", "Rol", "Min P."])
        self._tbl_v.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch)
        for i in range(1, 6):
            self._tbl_v.setColumnWidth(i, 70)
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
        self._btn_v_dup = self._btn("✎")
        self._btn_v_dup.setFixedWidth(28)
        self._btn_v_dup.setEnabled(False)
        self._btn_v_dup.clicked.connect(self._vardiya_duzenle)
        alt.addWidget(self._btn_v_dup)
        self._btn_v_sil = self._btn("✕", "danger")
        self._btn_v_sil.setFixedWidth(28)
        self._btn_v_sil.setEnabled(False)
        self._btn_v_sil.clicked.connect(self._vardiya_sil)
        alt.addWidget(self._btn_v_sil)
        alt.addStretch()
        self._lbl_v_ozet = QLabel("")
        self._lbl_v_ozet.setProperty("color-role", "muted")
        self._lbl_v_ozet.setStyleSheet("font-size:10px;")
        alt.addWidget(self._lbl_v_ozet)
        lay.addLayout(alt)
        return w

    def _build_personel_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.setSpacing(4)

        tb = QHBoxLayout()
        self._btn_p_ata = self._btn("+ Personel Ata", "action")
        self._btn_p_ata.setEnabled(False)
        self._btn_p_ata.clicked.connect(self._personel_ata)
        tb.addWidget(self._btn_p_ata)
        self._btn_p_migrate = self._btn("⟳ GorevYeri'nden Aktar")
        self._btn_p_migrate.setEnabled(False)
        self._btn_p_migrate.clicked.connect(self._personel_migrate)
        tb.addWidget(self._btn_p_migrate)
        tb.addStretch()
        lay.addLayout(tb)

        self._tbl_p = QTableWidget(0, 4)
        self._tbl_p.setHorizontalHeaderLabels(
            ["Ad Soyad", "Rol", "Görev Başlangıç", "Durum"])
        self._tbl_p.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch)
        for i in range(1, 4):
            self._tbl_p.setColumnWidth(i, 90)
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
        self._btn_p_cikar = self._btn("✕  Görevden Al", "danger")
        self._btn_p_cikar.setEnabled(False)
        self._btn_p_cikar.clicked.connect(self._personel_cikar)
        alt.addWidget(self._btn_p_cikar)
        alt.addStretch()
        self._lbl_p_ozet = QLabel("")
        self._lbl_p_ozet.setProperty("color-role", "muted")
        self._lbl_p_ozet.setStyleSheet("font-size:10px;")
        alt.addWidget(self._lbl_p_ozet)
        lay.addLayout(alt)
        return w

    def _build_tercih_tab(self) -> QWidget:
        """Ay bazlı: FM Gönüllü + HedefTipi."""
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.setSpacing(4)

        nav = QHBoxLayout()
        btn_g = QPushButton("‹")
        btn_g.setFixedSize(28, 26)
        btn_g.setProperty("style-role", "secondary")
        btn_g.clicked.connect(self._tercih_ay_geri)
        nav.addWidget(btn_g)
        self._lbl_tercih_ay = QLabel(f"{_AY_TR[self._ay]} {self._yil}")
        self._lbl_tercih_ay.setFixedWidth(110)
        self._lbl_tercih_ay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._lbl_tercih_ay.setProperty("style-role", "section-title")
        nav.addWidget(self._lbl_tercih_ay)
        btn_i = QPushButton("›")
        btn_i.setFixedSize(28, 26)
        btn_i.setProperty("style-role", "secondary")
        btn_i.clicked.connect(self._tercih_ay_ileri)
        nav.addWidget(btn_i)
        nav.addStretch()
        h_lbl = QLabel("Çift tıkla → düzenle")
        h_lbl.setProperty("color-role", "muted")
        h_lbl.setStyleSheet("font-size:10px;")
        nav.addWidget(h_lbl)
        lay.addLayout(nav)

        self._tbl_tercih = QTableWidget(0, 3)
        self._tbl_tercih.setHorizontalHeaderLabels(
            ["Ad Soyad", "FM Gönüllü", "Hedef Tipi"])
        self._tbl_tercih.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch)
        self._tbl_tercih.setColumnWidth(1, 100)
        self._tbl_tercih.setColumnWidth(2, 140)
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
        self._btn_tercih_dup = self._btn("✎  Düzenle")
        self._btn_tercih_dup.setEnabled(False)
        self._btn_tercih_dup.clicked.connect(self._tercih_duzenle)
        alt.addWidget(self._btn_tercih_dup)
        alt.addStretch()
        self._lbl_tercih_ozet = QLabel("")
        self._lbl_tercih_ozet.setProperty("color-role", "muted")
        self._lbl_tercih_ozet.setStyleSheet("font-size:10px;")
        alt.addWidget(self._lbl_tercih_ozet)
        lay.addLayout(alt)
        return w

    # ──────────────────────────────────────────────────────────
    #  Veri Yükleme
    # ──────────────────────────────────────────────────────────

    def _birimleri_yukle(self):
        try:
            rows = sorted(
                self._reg().get("NB_Birim").get_all() or [],
                key=lambda r: r.get("BirimAdi",""))
            self._tbl_birim.setRowCount(0)
            for r in rows:
                ri  = self._tbl_birim.rowCount()
                self._tbl_birim.insertRow(ri)
                itm = QTableWidgetItem(r.get("BirimAdi",""))
                itm.setData(Qt.ItemDataRole.UserRole, r["BirimID"])
                self._tbl_birim.setItem(ri, 0, itm)
        except Exception as e:
            logger.error(f"Birim yükle: {e}")

    def _gruplari_yukle(self, birim_id: str):
        try:
            rows = sorted(
                [r for r in (self._reg().get("NB_VardiyaGrubu").get_all() or [])
                 if str(r.get("BirimID","")) == birim_id],
                key=lambda r: int(r.get("Sira", 1)))
            self._tbl_grup.setRowCount(0)
            self._tbl_v.setRowCount(0)
            self._secili_grup_id = ""
            self._lbl_grup_adi.setText("— Grup seçin —")
            for r in rows:
                ri  = self._tbl_grup.rowCount()
                gid = r["GrupID"]
                self._tbl_grup.insertRow(ri)
                itm = QTableWidgetItem(r.get("GrupAdi",""))
                itm.setData(Qt.ItemDataRole.UserRole, gid)
                self._tbl_grup.setItem(ri, 0, itm)
                self._tbl_grup.setItem(ri, 1, _it(r.get("Sira",1), gid))
                aktif = int(r.get("Aktif",1))
                a_itm = QTableWidgetItem("✔" if aktif else "✕")
                a_itm.setForeground(QColor(
                    "#2ec98e" if aktif else "#e85555"))
                a_itm.setData(Qt.ItemDataRole.UserRole, gid)
                self._tbl_grup.setItem(ri, 2, a_itm)
        except Exception as e:
            logger.error(f"Grup yükle: {e}")

    def _vardiyeleri_yukle(self, grup_id: str):
        try:
            rows = sorted(
                [r for r in (self._reg().get("NB_Vardiya").get_all() or [])
                 if str(r.get("GrupID","")) == grup_id],
                key=lambda r: int(r.get("Sira", 1)))
            self._tbl_v.setRowCount(0)
            toplam_dk = 0
            for r in rows:
                ri  = self._tbl_v.rowCount()
                vid = r["VardiyaID"]
                dk  = int(r.get("SureDakika", 0))
                self._tbl_v.insertRow(ri)
                self._tbl_v.setItem(ri, 0, _it(r.get("VardiyaAdi",""), vid))
                self._tbl_v.setItem(ri, 1, _it(r.get("BasSaat",""), vid))
                self._tbl_v.setItem(ri, 2, _it(r.get("BitSaat",""), vid))
                self._tbl_v.setItem(ri, 3,
                    _it(f"{dk//60}s {dk%60:02d}dk" if dk else "—", vid))
                rol_itm = _it(r.get("Rol","ana"), vid)
                if r.get("Rol","ana") == "yardimci":
                    rol_itm.setForeground(QColor("#e8a030"))
                self._tbl_v.setItem(ri, 4, rol_itm)
                self._tbl_v.setItem(ri, 5, _it(r.get("MinPersonel",1), vid))
                if r.get("Rol","ana") == "ana":
                    toplam_dk += dk
            self._lbl_v_ozet.setText(
                f"{len(rows)} vardiya | "
                f"Toplam: {toplam_dk//60}s {toplam_dk%60:02d}dk")
        except Exception as e:
            logger.error(f"Vardiya yükle: {e}")

    def _personelleri_yukle(self, birim_id: str):
        try:
            reg   = self._reg()
            bp    = reg.get("NB_BirimPersonel").get_all() or []
            p_all = reg.get("Personel").get_all() or []
            p_map = {str(p["KimlikNo"]): p.get("AdSoyad","") for p in p_all}
            bp = sorted(
                [r for r in bp if str(r.get("BirimID",""))==birim_id],
                key=lambda r: p_map.get(str(r.get("PersonelID","")),""))
            self._tbl_p.setRowCount(0)
            for r in bp:
                ri  = self._tbl_p.rowCount()
                pid = str(r.get("PersonelID",""))
                self._tbl_p.insertRow(ri)
                atama_id = r.get("ID", "")
                ad_i = QTableWidgetItem(p_map.get(pid, pid))
                ad_i.setData(Qt.ItemDataRole.UserRole, atama_id)
                self._tbl_p.setItem(ri, 0, ad_i)
                self._tbl_p.setItem(ri, 1, _it(r.get("Rol","teknisyen")))
                self._tbl_p.setItem(ri, 2,
                    _it(str(r.get("GorevBaslangic",""))[:10]))
                aktif = int(r.get("Aktif", 1))
                a_itm = QTableWidgetItem("Aktif" if aktif else "Pasif")
                a_itm.setForeground(QColor(
                    "#2ec98e" if aktif else "#e85555"))
                a_itm.setData(Qt.ItemDataRole.UserRole, atama_id)
                self._tbl_p.setItem(ri, 3, a_itm)
            self._lbl_p_ozet.setText(f"{len(bp)} personel")
        except Exception as e:
            logger.error(f"Personel yükle: {e}")

    def _tercihleri_yukle(self):
        if not self._secili_birim_id:
            return
        try:
            reg   = self._reg()
            bp    = reg.get("NB_BirimPersonel").get_all() or []
            p_all = reg.get("Personel").get_all() or []
            p_map = {str(p["KimlikNo"]): p.get("AdSoyad","") for p in p_all}
            pid_list = sorted(
                [str(r.get("PersonelID","")) for r in bp
                 if str(r.get("BirimID","")) == self._secili_birim_id
                 and int(r.get("Aktif",1))],
                key=lambda p: p_map.get(p,""))

            t_rows = reg.get("NB_PersonelTercih").get_all() or []
            tercih_map = {
                str(r.get("PersonelID","")): r
                for r in t_rows
                if str(r.get("BirimID","")) == self._secili_birim_id
                and int(r.get("Yil",0)) == self._yil
                and int(r.get("Ay",0)) == self._ay
            }

            self._tbl_tercih.setRowCount(0)
            fm_sayi = 0
            for pid in pid_list:
                ad    = p_map.get(pid, pid)
                kayit = tercih_map.get(pid, {})
                nobet = kayit.get("NobetTercihi","zorunlu")
                tip   = kayit.get("HedefTipi","normal")
                fm    = nobet == "fazla_mesai_gonullu"
                if fm:
                    fm_sayi += 1
                tip_lbl = next(
                    (l for v,l in HEDEF_TIPLER if v == tip), "Normal")

                ri = self._tbl_tercih.rowCount()
                self._tbl_tercih.insertRow(ri)

                ad_i = QTableWidgetItem(ad)
                ad_i.setData(Qt.ItemDataRole.UserRole, pid)
                self._tbl_tercih.setItem(ri, 0, ad_i)

                fm_itm = QTableWidgetItem("● FM Gönüllü" if fm else "○")
                fm_itm.setForeground(QColor(
                    "#4d9ee8" if fm else "#6b7280"))
                fm_itm.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                fm_itm.setData(Qt.ItemDataRole.UserRole, pid)
                self._tbl_tercih.setItem(ri, 1, fm_itm)

                tip_itm = QTableWidgetItem(tip_lbl)
                tip_itm.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if tip not in ("normal","rapor","yillik","idari"):
                    tip_itm.setForeground(QColor("#f59e0b"))
                tip_itm.setData(Qt.ItemDataRole.UserRole, pid)
                self._tbl_tercih.setItem(ri, 2, tip_itm)

            self._lbl_tercih_ozet.setText(
                f"{len(pid_list)} personel | {fm_sayi} FM Gönüllü")
        except Exception as e:
            logger.error(f"Tercih yükle: {e}")

    def _birim_ayar_yukle(self, birim_id: str):
        try:
            rows = self._reg().get("NB_BirimAyar").get_all() or []
            ayar = next(
                (r for r in rows if str(r.get("BirimID","")) == birim_id), None)
            self._spn_slot.setValue(
                int((ayar or {}).get("GunlukSlotSayisi", 4)))
            self._spn_fm_max.setValue(
                int((ayar or {}).get("FmMaxSaat", 60)))
            # MaxGunlukSureDakika → 720=1 vardiya, 1440=2 vardiya
            max_dk = int((ayar or {}).get("MaxGunlukSureDakika", 720))
            self._spn_max_gun.setValue(2 if max_dk >= 1440 else 1)
            self._chk_hafta_sonu.setChecked(
                bool(int((ayar or {}).get("HaftasonuCalismaVar", 1))))
            self._chk_resmi_tatil.setChecked(
                bool(int((ayar or {}).get("ResmiTatilCalismaVar", 1))))
            # Geriye uyumluluk: yeni kolon yoksa eski DiniBayramAtama'yı oku
            dini_var = (ayar or {}).get("DiniBayramCalismaVar", None)
            if dini_var is None:
                dini_var = (ayar or {}).get("DiniBayramAtama", 0)
            self._chk_dini_bayram.setChecked(bool(int(dini_var)))
        except Exception as e:
            logger.error(f"Birim ayar yükle: {e}")

    def _birim_ayar_getir(self, birim_id: str) -> dict:
        try:
            rows = self._reg().get("NB_BirimAyar").get_all() or []
            return next(
                (r for r in rows if str(r.get("BirimID", "")) == birim_id),
                None,
            ) or {}
        except Exception as e:
            logger.error(f"Birim ayar getir: {e}")
            return {}

    def _vardiya_icin_birim_ayar_kaydet(self, birim_id: str, secim: dict):
        if not birim_id:
            return
        try:
            reg = self._reg()
            rows = reg.get("NB_BirimAyar").get_all() or []
            ayar = next(
                (r for r in rows if str(r.get("BirimID", "")) == birim_id),
                None,
            )
            veri = {
                "HaftasonuNobetZorunlu": int(secim.get("HaftasonuNobetZorunlu", 1)),
                "DiniBayramAtama": int(secim.get("DiniBayramAtama", 1)),
                "updated_at": _simdi(),
            }
            if ayar:
                reg.get("NB_BirimAyar").update(ayar["AyarID"], veri)
            else:
                reg.get("NB_BirimAyar").insert({
                    "AyarID": _yeni_id(),
                    "BirimID": birim_id,
                    "GunlukSlotSayisi": self._spn_slot.value(),
                    "FmMaxSaat": self._spn_fm_max.value(),
                    "MaxGunlukSureDakika": (
                        1440 if self._spn_max_gun.value() >= 2 else 720),
                    "created_at": _simdi(),
                    **veri,
                })
        except Exception as e:
            logger.error(f"Vardiya birim ayar kaydet: {e}")

    # ──────────────────────────────────────────────────────────
    #  Seçim Sinyalleri
    # ──────────────────────────────────────────────────────────

    def _on_birim_sec(self):
        row = self._tbl_birim.currentRow()
        itm = self._tbl_birim.item(row, 0) if row >= 0 else None
        bid = itm.data(Qt.ItemDataRole.UserRole) if itm else ""
        self._secili_birim_id  = bid
        self._secili_birim_adi = itm.text() if itm else ""
        aktif = bool(bid)
        for b in [self._btn_birim_dup, self._btn_grup_yeni,
                  self._btn_sablon, self._btn_p_ata,
                  self._btn_p_migrate, self._btn_ayar_kaydet]:
            b.setEnabled(aktif)
        if aktif:
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

    # ──────────────────────────────────────────────────────────
    #  Birim Aksiyonları
    # ──────────────────────────────────────────────────────────

    def _birim_yeni(self):
        dialog = _BirimDialog(parent=self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        veri = dialog.get_data()
        if not veri["BirimAdi"]:
            QMessageBox.warning(self, "Uyarı", "Birim adı boş olamaz.")
            return
        try:
            self._reg().get("NB_Birim").insert({
                "BirimID":    _yeni_id(),
                "BirimAdi":   veri["BirimAdi"],
                "Aciklama":   veri["Aciklama"],
                "Aktif":      1,
                "created_at": _simdi(),
            })
            self._birimleri_yukle()
        except Exception as e:
            QMessageBox.critical(self, "Hata", str(e))

    def _birim_duzenle(self):
        row = self._tbl_birim.currentRow()
        if row < 0:
            return
        itm = self._tbl_birim.item(row, 0)
        bid = itm.data(Qt.ItemDataRole.UserRole)
        try:
            reg   = self._reg()
            rows  = reg.get("NB_Birim").get_all() or []
            kayit = next((r for r in rows if r["BirimID"]==bid), None)
            dialog = _BirimDialog(kayit, parent=self)
            if dialog.exec() != QDialog.DialogCode.Accepted:
                return
            reg.get("NB_Birim").update(
                bid, {**dialog.get_data(), "updated_at": _simdi()})
            self._birimleri_yukle()
        except Exception as e:
            QMessageBox.critical(self, "Hata", str(e))

    def _birim_ayar_kaydet(self):
        bid = self._secili_birim_id
        if not bid:
            return
        try:
            reg   = self._reg()

            # Yeni ayar kolonları yoksa migration çalıştır
            try:
                test_rows = reg.get("NB_BirimAyar").get_all() or []
                if test_rows:
                    ilk = test_rows[0]
                    gerekenler = [
                        "MaxGunlukSureDakika",
                        "HaftasonuCalismaVar",
                        "ResmiTatilCalismaVar",
                        "DiniBayramCalismaVar",
                    ]
                    if any(ilk.get(k, None) is None for k in gerekenler):
                        raise KeyError("kolon yok")
            except Exception:
                try:
                    from database.migrations import MigrationManager
                    db_path = getattr(self._db, "db_path", self._db)
                    MigrationManager(db_path).run_migrations()
                    logger.info("Migration çalıştırıldı (NB_BirimAyar kolonları)")
                except Exception as me:
                    logger.error(f"Migration hatası: {me}")

            rows  = reg.get("NB_BirimAyar").get_all() or []
            ayar  = next(
                (r for r in rows if str(r.get("BirimID",""))==bid), None)
            veri  = {
                "GunlukSlotSayisi":    self._spn_slot.value(),
                "FmMaxSaat":           self._spn_fm_max.value(),
                "MaxGunlukSureDakika": 1440 if self._spn_max_gun.value() >= 2 else 720,
                "HaftasonuCalismaVar": 1 if self._chk_hafta_sonu.isChecked() else 0,
                "ResmiTatilCalismaVar": 1 if self._chk_resmi_tatil.isChecked() else 0,
                "DiniBayramCalismaVar": 1 if self._chk_dini_bayram.isChecked() else 0,
                "updated_at":          _simdi(),
            }
            if ayar:
                reg.get("NB_BirimAyar").update(ayar["AyarID"], veri)
                logger.info(f"BirimAyar güncellendi: {veri}")
            else:
                veri["AyarID"]     = _yeni_id()
                veri["BirimID"]    = bid
                veri["created_at"] = _simdi()
                reg.get("NB_BirimAyar").insert(veri)
                logger.info(f"BirimAyar eklendi: {veri}")
            QMessageBox.information(
                self, "Kaydedildi",
                f"Slot: {self._spn_slot.value()}  |  "
                f"FM Max: {self._spn_fm_max.value()} saat  |  "
                f"Max günlük: {'24 saat (2 vardiya)' if self._spn_max_gun.value()>=2 else '12 saat (1 vardiya)'}\n"
                f"Hafta sonu: {'Açık' if self._chk_hafta_sonu.isChecked() else 'Kapalı'}  |  "
                f"Resmi tatil: {'Açık' if self._chk_resmi_tatil.isChecked() else 'Kapalı'}  |  "
                f"Dini bayram: {'Açık' if self._chk_dini_bayram.isChecked() else 'Kapalı'}")
        except Exception as e:
            QMessageBox.critical(self, "Hata", str(e))
            logger.error(f"_birim_ayar_kaydet: {e}")

    # ──────────────────────────────────────────────────────────
    #  Grup Aksiyonları
    # ──────────────────────────────────────────────────────────

    def _grup_yeni(self):
        dialog = _GrupDialog(parent=self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        veri = dialog.get_data()
        if not veri["GrupAdi"]:
            QMessageBox.warning(self, "Uyarı", "Grup adı boş olamaz.")
            return
        try:
            self._reg().get("NB_VardiyaGrubu").insert({
                "GrupID":    _yeni_id(),
                "BirimID":   self._secili_birim_id,
                "GrupAdi":   veri["GrupAdi"],
                "GrupTuru":  "zorunlu",
                "Sira":      veri["Sira"],
                "Aktif":     veri["Aktif"],
                "created_at": _simdi(),
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
            reg   = self._reg()
            rows  = reg.get("NB_VardiyaGrubu").get_all() or []
            kayit = next((r for r in rows if r["GrupID"]==gid), None)
            dialog = _GrupDialog(kayit, parent=self)
            if dialog.exec() != QDialog.DialogCode.Accepted:
                return
            reg.get("NB_VardiyaGrubu").update(
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
            f"'{isim}' grubu ve tüm vardiyaları silinecek.\nEmin misiniz?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        ) != QMessageBox.StandardButton.Yes:
            return
        try:
            reg  = self._reg()
            for v in (reg.get("NB_Vardiya").get_all() or []):
                if str(v.get("GrupID","")) == gid:
                    reg.get("NB_Vardiya").delete(v["VardiyaID"])
            reg.get("NB_VardiyaGrubu").delete(gid)
            self._gruplari_yukle(self._secili_birim_id)
        except Exception as e:
            QMessageBox.critical(self, "Hata", str(e))

    def _sablon_uygula(self):
        secenekler = [
            ("tam_gun_24h",       "7/24 — Gündüz(08-20) + Gece(20-08)"),
            ("sadece_gunduz_12h", "Sadece Gündüz(08-20)"),
            ("uc_vardiya_8h",     "3 Vardiya 8s — Sabah/Akşam/Gece"),
        ]
        dialog = QDialog(self)
        dialog.setWindowTitle("Şablon Seç")
        dialog.setModal(True)
        dialog.setProperty("bg-role", "page")
        lay = QVBoxLayout(dialog)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.setSpacing(10)
        cmb = QComboBox()
        for val, lbl in secenekler:
            cmb.addItem(lbl, userData=val)
        lay.addWidget(QLabel("Şablon:"))
        lay.addWidget(cmb)
        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(dialog.accept)
        btns.rejected.connect(dialog.reject)
        lay.addWidget(btns)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            from core.di import get_nb_vardiya_service
            svc = get_nb_vardiya_service(self._db)
            s   = svc.sablon_yukle(self._secili_birim_id, cmb.currentData())
            if s.basarili:
                QMessageBox.information(self, "Şablon Yüklendi", s.mesaj)
                self._gruplari_yukle(self._secili_birim_id)
            else:
                QMessageBox.critical(self, "Hata", s.mesaj)
        except Exception as e:
            QMessageBox.critical(self, "Hata", str(e))

    # ──────────────────────────────────────────────────────────
    #  Vardiya Aksiyonları
    # ──────────────────────────────────────────────────────────

    def _vardiya_yeni(self):
        if not self._secili_birim_id or not self._secili_grup_id:
            QMessageBox.warning(
                self,
                "Uyarı",
                "Önce bir birim ve vardiya grubu seçin.",
            )
            return
        birim_ayar = self._birim_ayar_getir(self._secili_birim_id)
        dialog = _VardiyaDialog(birim_ayar=birim_ayar, parent=self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        veri = dialog.get_data()
        if not veri["VardiyaAdi"]:
            QMessageBox.warning(self, "Uyarı", "Vardiya adı boş olamaz.")
            return
        try:
            self._reg().get("NB_Vardiya").insert({
                "VardiyaID":   _yeni_id(),
                "GrupID":      self._secili_grup_id,
                "BirimID":     self._secili_birim_id,
                "MinPersonel": 1,
                "created_at":  _simdi(),
                **veri,
            })
            self._vardiya_icin_birim_ayar_kaydet(
                self._secili_birim_id,
                dialog.get_birim_ayar_data(),
            )
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
            reg   = self._reg()
            rows  = reg.get("NB_Vardiya").get_all() or []
            kayit = next((r for r in rows if r["VardiyaID"]==vid), None)
            birim_ayar = self._birim_ayar_getir(self._secili_birim_id)
            dialog = _VardiyaDialog(kayit, birim_ayar=birim_ayar, parent=self)
            if dialog.exec() != QDialog.DialogCode.Accepted:
                return
            reg.get("NB_Vardiya").update(
                vid, {**dialog.get_data(), "updated_at": _simdi()})
            self._vardiya_icin_birim_ayar_kaydet(
                self._secili_birim_id,
                dialog.get_birim_ayar_data(),
            )
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

    # ──────────────────────────────────────────────────────────
    #  Personel Aksiyonları
    # ──────────────────────────────────────────────────────────

    def _personel_ata(self):
        try:
            reg   = self._reg()
            p_all = reg.get("Personel").get_all() or []
            p_map = {str(p["KimlikNo"]): p.get("AdSoyad","") for p in p_all}
            pid_list = sorted(
                [str(p["KimlikNo"]) for p in p_all
                 if str(p.get("Durum","Aktif")).strip() == "Aktif"],
                key=lambda p: p_map.get(p,""))
            bp = reg.get("NB_BirimPersonel").get_all() or []
            mevcutlar = {
                str(r.get("PersonelID","")) for r in bp
                if str(r.get("BirimID","")) == self._secili_birim_id
                and int(r.get("Aktif",1))}
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
        if not self._secili_birim_adi:
            return
        try:
            reg   = self._reg()
            p_all = reg.get("Personel").get_all() or []
            bp    = reg.get("NB_BirimPersonel").get_all() or []
            mevcutlar = {
                str(r.get("PersonelID","")) for r in bp
                if str(r.get("BirimID","")) == self._secili_birim_id}
            eklendi = 0
            for p in p_all:
                pid = str(p["KimlikNo"])
                if (str(p.get("GorevYeri","")).strip() == self._secili_birim_adi
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
                self, "Tamamlandı",
                f"{eklendi} personel aktarıldı.")
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
            self, "Görevden Al",
            f"'{isim}' bu birimden görevden alınacak.\nEmin misiniz?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        ) != QMessageBox.StandardButton.Yes:
            return
        try:
            self._reg().get("NB_BirimPersonel").update(
                ata_id, {"Aktif": 0, "updated_at": _simdi()})
            self._personelleri_yukle(self._secili_birim_id)
        except Exception as e:
            QMessageBox.critical(self, "Hata", str(e))

    # ──────────────────────────────────────────────────────────
    #  Nöbet Tercihleri Aksiyonları
    # ──────────────────────────────────────────────────────────

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
                 if str(r.get("PersonelID","")) == pid
                 and str(r.get("BirimID","")) == self._secili_birim_id
                 and int(r.get("Yil",0)) == self._yil
                 and int(r.get("Ay",0)) == self._ay),
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

    def load_data(self):
        """Dış çağrı desteği."""
        if self._db:
            self._birimleri_yukle()
