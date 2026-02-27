# -*- coding: utf-8 -*-
"""RKE Muayene Girisi - Refactored."""

import os
import time
import datetime
from typing import List, Dict

from PySide6.QtCore import Qt, QDate, QModelIndex, QUrl
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QAbstractItemView,
    QTableView, QHeaderView, QLabel, QPushButton, QComboBox,
    QDateEdit, QLineEdit, QProgressBar, QScrollArea,
    QFrame, QGridLayout, QMessageBox, QDialog, QListWidget,
    QGroupBox,
    QFileDialog
)
from PySide6.QtGui import QCursor, QDesktopServices

from ui.styles.colors import DarkTheme
from ui.styles.components import STYLES

from .components.rke_field_group import FieldGroup
from .components.rke_checkable_combo import CheckableComboBox
from .models.rke_envanter_model import RKEEnvanterModel, RKE_WIDTHS, RKE_COLS
from .models.rke_gecmis_model import GecmisModel
from .services.rke_muayene_workers import VeriYukleyici, KayitWorker, TopluKayitWorker

_S_PAGE = STYLES["page"]
_S_INPUT = STYLES["input"]
_S_DATE = STYLES["input_date"]
_S_COMBO = STYLES["input_combo"]
_S_TABLE = STYLES["table"]
_S_SCROLL = STYLES["scrollbar"]
_S_PBAR = STYLES["progress"]


class TopluMuayeneDialog(QDialog):
    def __init__(self, secilen_ekipmanlar, teknik_aciklamalar,
                 kontrol_listesi, sorumlu_listesi, kullanici_adi=None, parent=None,
                 db_path=None, use_sheets=True):
        super().__init__(parent)
        self._db_path = db_path
        self._use_sheets = use_sheets
        self.ekipmanlar = secilen_ekipmanlar
        self.teknik_aciklamalar = teknik_aciklamalar
        self.kontrol_listesi = kontrol_listesi
        self.sorumlu_listesi = sorumlu_listesi
        self.kullanici_adi = kullanici_adi
        self.dosya_yolu = None
        self.setWindowTitle(f"Toplu Muayene — {len(self.ekipmanlar)} Ekipman")
        self.resize(640, 600)
        self.setStyleSheet(_S_PAGE)
        self._setup_ui()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        grp_list = QGroupBox(f"Secili Ekipmanlar ({len(self.ekipmanlar)})")
        grp_list.setStyleSheet(
            f"QGroupBox{{background:{DarkTheme.BG_SECONDARY};border:1px solid {DarkTheme.BORDER_PRIMARY};"
            f"border-radius:5px;padding-top:16px;}}"
            f"QGroupBox::title{{color:{DarkTheme.TEXT_SECONDARY};font-family:{DarkTheme.MONOSPACE};font-size:10px;}}"
        )
        gl = QVBoxLayout(grp_list)
        lst = QListWidget()
        lst.setStyleSheet(_S_TABLE)
        lst.setFixedHeight(90)
        lst.addItems(self.ekipmanlar)
        gl.addWidget(lst)
        root.addWidget(grp_list)

        self.grp_fiz = QGroupBox("Fiziksel Muayene")
        self.grp_fiz.setCheckable(True)
        self.grp_fiz.setChecked(True)
        self.grp_fiz.setStyleSheet(
            f"QGroupBox{{background:{DarkTheme.BG_SECONDARY};border:1px solid {DarkTheme.BORDER_PRIMARY};"
            f"border-radius:5px;padding-top:16px;}}"
            f"QGroupBox::title{{color:{DarkTheme.TEXT_SECONDARY};font-family:{DarkTheme.MONOSPACE};font-size:10px;}}"
        )
        hf = QHBoxLayout(self.grp_fiz)
        hf.setSpacing(12)
        self.dt_fiz = QDateEdit(QDate.currentDate())
        self.dt_fiz.setCalendarPopup(True)
        self.dt_fiz.setStyleSheet(_S_DATE)
        self.dt_fiz.setFixedHeight(28)
        self.cmb_fiz = QComboBox()
        self.cmb_fiz.setStyleSheet(_S_COMBO)
        self.cmb_fiz.setFixedHeight(28)
        self.cmb_fiz.addItems(["Kullanima Uygun", "Kullanima Uygun Degil"])
        lbl_t = QLabel("Tarih:")
        lbl_t.setStyleSheet(f"color:{DarkTheme.TEXT_MUTED};font-family:{DarkTheme.MONOSPACE};font-size:10px;")
        lbl_d = QLabel("Durum:")
        lbl_d.setStyleSheet(f"color:{DarkTheme.TEXT_MUTED};font-family:{DarkTheme.MONOSPACE};font-size:10px;")
        hf.addWidget(lbl_t)
        hf.addWidget(self.dt_fiz)
        hf.addWidget(lbl_d)
        hf.addWidget(self.cmb_fiz)
        root.addWidget(self.grp_fiz)
        self.chk_fiz = self.grp_fiz

        self.grp_sko = QGroupBox("Skopi Muayene")
        self.grp_sko.setCheckable(True)
        self.grp_sko.setChecked(False)
        self.grp_sko.setStyleSheet(
            f"QGroupBox{{background:{DarkTheme.BG_SECONDARY};border:1px solid {DarkTheme.BORDER_PRIMARY};"
            f"border-radius:5px;padding-top:16px;}}"
            f"QGroupBox::title{{color:{DarkTheme.TEXT_SECONDARY};font-family:{DarkTheme.MONOSPACE};font-size:10px;}}"
        )
        hs = QHBoxLayout(self.grp_sko)
        hs.setSpacing(12)
        self.dt_sko = QDateEdit(QDate.currentDate())
        self.dt_sko.setCalendarPopup(True)
        self.dt_sko.setStyleSheet(_S_DATE)
        self.dt_sko.setFixedHeight(28)
        self.cmb_sko = QComboBox()
        self.cmb_sko.setStyleSheet(_S_COMBO)
        self.cmb_sko.setFixedHeight(28)
        self.cmb_sko.addItems(["Kullanima Uygun", "Kullanima Uygun Degil", "Yapilmadi"])
        lbl_t2 = QLabel("Tarih:")
        lbl_t2.setStyleSheet(f"color:{DarkTheme.TEXT_MUTED};font-family:{DarkTheme.MONOSPACE};font-size:10px;")
        lbl_d2 = QLabel("Durum:")
        lbl_d2.setStyleSheet(f"color:{DarkTheme.TEXT_MUTED};font-family:{DarkTheme.MONOSPACE};font-size:10px;")
        hs.addWidget(lbl_t2)
        hs.addWidget(self.dt_sko)
        hs.addWidget(lbl_d2)
        hs.addWidget(self.cmb_sko)
        root.addWidget(self.grp_sko)
        self.chk_sko = self.grp_sko

        grp_ortak = QGroupBox("Ortak Bilgiler")
        grp_ortak.setStyleSheet(
            f"QGroupBox{{background:{DarkTheme.BG_SECONDARY};border:1px solid {DarkTheme.BORDER_PRIMARY};"
            f"border-radius:5px;padding-top:16px;}}"
            f"QGroupBox::title{{color:{DarkTheme.TEXT_SECONDARY};font-family:{DarkTheme.MONOSPACE};font-size:10px;}}"
        )
        og = QGridLayout(grp_ortak)
        og.setContentsMargins(8, 8, 8, 8)
        og.setSpacing(8)

        lbl_ke = QLabel("Kontrol Eden:")
        lbl_ke.setStyleSheet(f"color:{DarkTheme.TEXT_MUTED};font-family:{DarkTheme.MONOSPACE};font-size:10px;")
        self.cmb_kontrol = QComboBox()
        self.cmb_kontrol.setEditable(True)
        self.cmb_kontrol.setStyleSheet(_S_COMBO)
        self.cmb_kontrol.setFixedHeight(28)
        self.cmb_kontrol.addItems(self.kontrol_listesi)
        if self.kullanici_adi:
            self.cmb_kontrol.setCurrentText(self.kullanici_adi)

        lbl_bs = QLabel("Birim Sorumlusu:")
        lbl_bs.setStyleSheet(f"color:{DarkTheme.TEXT_MUTED};font-family:{DarkTheme.MONOSPACE};font-size:10px;")
        self.cmb_sorumlu = QComboBox()
        self.cmb_sorumlu.setEditable(True)
        self.cmb_sorumlu.setStyleSheet(_S_COMBO)
        self.cmb_sorumlu.setFixedHeight(28)
        self.cmb_sorumlu.addItems(self.sorumlu_listesi)

        og.addWidget(lbl_ke, 0, 0)
        og.addWidget(self.cmb_kontrol, 0, 1)
        og.addWidget(lbl_bs, 0, 2)
        og.addWidget(self.cmb_sorumlu, 0, 3)

        lbl_acik = QLabel("Teknik Aciklama:")
        lbl_acik.setStyleSheet(f"color:{DarkTheme.TEXT_MUTED};font-family:{DarkTheme.MONOSPACE};font-size:10px;")
        self.cmb_aciklama = CheckableComboBox()
        self.cmb_aciklama.setStyleSheet(_S_COMBO)
        self.cmb_aciklama.setFixedHeight(28)
        self.cmb_aciklama.addItems(self.teknik_aciklamalar)
        og.addWidget(lbl_acik, 1, 0, 1, 1)
        og.addWidget(self.cmb_aciklama, 1, 1, 1, 3)

        file_row = QHBoxLayout()
        self.lbl_file = QLabel("Dosya secilmedi")
        self.lbl_file.setStyleSheet(f"color:{DarkTheme.TEXT_MUTED};font-size:10px;")
        btn_file = QPushButton("Ortak Rapor")
        btn_file.setStyleSheet(
            f"QPushButton{{background:{DarkTheme.BG_SECONDARY};border:1px solid {DarkTheme.BORDER_PRIMARY};border-radius:4px;"
            f"color:{DarkTheme.TEXT_SECONDARY};padding:0 12px;}}QPushButton:hover{{color:{DarkTheme.TEXT_PRIMARY};}}"
        )
        btn_file.setFixedHeight(28)
        btn_file.clicked.connect(self._dosya_sec)
        file_row.addWidget(self.lbl_file, 1)
        file_row.addWidget(btn_file)
        og.addLayout(file_row, 2, 0, 1, 4)
        root.addWidget(grp_ortak)

        self.pbar = QProgressBar()
        self.pbar.setVisible(False)
        self.pbar.setFixedHeight(3)
        self.pbar.setStyleSheet(_S_PBAR)
        root.addWidget(self.pbar)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_iptal = QPushButton("Iptal")
        btn_iptal.setStyleSheet(
            f"QPushButton{{background:transparent;border:1px solid {DarkTheme.BORDER_PRIMARY};border-radius:5px;"
            f"color:{DarkTheme.TEXT_MUTED};font-family:{DarkTheme.MONOSPACE};font-size:10px;padding:0 16px;}}"
        )
        btn_iptal.setFixedHeight(36)
        btn_iptal.setCursor(QCursor(Qt.PointingHandCursor))
        btn_iptal.clicked.connect(self.reject)
        self.btn_kaydet = QPushButton("Baslat")
        self.btn_kaydet.setStyleSheet(
            f"QPushButton{{background:{DarkTheme.STATUS_SUCCESS};border:none;border-radius:5px;"
            f"color:#051a10;font-family:{DarkTheme.MONOSPACE};font-size:10px;font-weight:800;padding:0 16px;}}"
        )
        self.btn_kaydet.setFixedHeight(36)
        self.btn_kaydet.setFixedWidth(120)
        self.btn_kaydet.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_kaydet.clicked.connect(self.kaydet)
        btn_row.addWidget(btn_iptal)
        btn_row.addWidget(self.btn_kaydet)
        root.addLayout(btn_row)

    def _dosya_sec(self):
        yol, _ = QFileDialog.getOpenFileName(self, "Rapor", "", "PDF/Resim (*.pdf *.jpg)")
        if yol:
            self.dosya_yolu = yol
            self.lbl_file.setText(os.path.basename(yol))

    def kaydet(self):
        if not self.chk_fiz.isChecked() and not self.chk_sko.isChecked():
            QMessageBox.warning(self, "Uyari", "En az bir muayene turu secin.")
            return
        ortak_veri = {
            "F_MuayeneTarihi": self.dt_fiz.date().toString("yyyy-MM-dd"),
            "FizikselDurum": self.cmb_fiz.currentText(),
            "S_MuayeneTarihi": self.dt_sko.date().toString("yyyy-MM-dd"),
            "SkopiDurum": self.cmb_sko.currentText(),
            "Aciklamalar": self.cmb_aciklama.getCheckedItems(),
            "KontrolEden": self.cmb_kontrol.currentText(),
            "BirimSorumlusu": self.cmb_sorumlu.currentText(),
            "Not": "Toplu Kayit",
        }
        self.btn_kaydet.setEnabled(False)
        self.pbar.setVisible(True)
        self.pbar.setRange(0, len(self.ekipmanlar))
        self.worker = TopluKayitWorker(
            self.ekipmanlar, ortak_veri, self.dosya_yolu,
            self.chk_fiz.isChecked(), self.chk_sko.isChecked(),
            db_path=self._db_path, use_sheets=self._use_sheets
        )
        self.worker.progress.connect(self.pbar.setValue)
        self.worker.finished.connect(self.accept)
        self.worker.error.connect(lambda e: QMessageBox.critical(self, "Hata", e))
        self.worker.start()


class RKEMuayenePage(QWidget):
    def __init__(self, db=None, action_guard=None, parent=None, yetki="viewer", kullanici_adi=None):
        super().__init__(parent)
        self._db = db
        self._action_guard = action_guard
        self._db_path = None
        if db and hasattr(db, "db_path"):
            self._db_path = db.db_path
        self._use_sheets = False if self._db else True
        self.yetki = yetki
        self.kullanici_adi = kullanici_adi
        self.setWindowTitle("RKE Muayene Girisi")
        self.resize(1200, 820)
        self.setStyleSheet(_S_PAGE)

        self.rke_data: List[Dict] = []
        self.rke_dict: Dict = {}
        self.tum_muayeneler = []
        self.teknik_aciklamalar = []
        self.kontrol_listesi = []
        self.sorumlu_listesi = []
        self.secilen_dosya = None
        self.header_map: Dict = {}
        self._kpi_labels: Dict[str, QLabel] = {}
        self.btn_kapat = None

        self._setup_ui()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._build_kpi_bar())
        root.addWidget(self._build_body(), 1)

    def _build_kpi_bar(self) -> QWidget:
        bar = QWidget()
        bar.setFixedHeight(68)
        bar.setStyleSheet(f"background:{DarkTheme.BG_PRIMARY};border-bottom:1px solid {DarkTheme.BORDER_PRIMARY};")
        hl = QHBoxLayout(bar)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setSpacing(1)

        specs = [
            ("toplam", "TOPLAM EKIPMAN", "0", DarkTheme.ACCENT),
            ("uygun", "KULLANIMA UYGUN", "0", DarkTheme.STATUS_SUCCESS),
            ("uygun_d", "UYGUN DEGIL", "0", DarkTheme.STATUS_ERROR),
            ("bekleyen", "KONTROL BEKLEYEN", "0", DarkTheme.STATUS_WARNING),
        ]
        for key, title, val, color in specs:
            hl.addWidget(self._mk_kpi_card(key, title, val, color), 1)
        return bar

    def _mk_kpi_card(self, key, title, val, color) -> QWidget:
        w = QWidget()
        w.setStyleSheet(f"background:{DarkTheme.BG_PRIMARY};")
        hl = QHBoxLayout(w)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setSpacing(0)

        accent = QFrame()
        accent.setFixedWidth(3)
        accent.setStyleSheet(f"background:{color};border:none;")
        hl.addWidget(accent)

        content = QWidget()
        content.setStyleSheet(f"background:{DarkTheme.BG_PRIMARY};")
        vl = QVBoxLayout(content)
        vl.setContentsMargins(14, 8, 14, 8)
        vl.setSpacing(2)

        lt = QLabel(title)
        lt.setStyleSheet(
            f"color:{DarkTheme.TEXT_MUTED};background:transparent;font-family:{DarkTheme.MONOSPACE};"
            f"font-size:8px;font-weight:700;letter-spacing:2px;"
        )
        lv = QLabel(val)
        lv.setStyleSheet(
            f"color:{color};background:transparent;font-family:{DarkTheme.MONOSPACE};"
            f"font-size:20px;font-weight:700;"
        )
        vl.addWidget(lt)
        vl.addWidget(lv)
        hl.addWidget(content, 1)
        self._kpi_labels[key] = lv
        return w

    def _build_body(self) -> QWidget:
        body = QWidget()
        body.setStyleSheet(f"background:{DarkTheme.BG_PRIMARY};")
        hl = QHBoxLayout(body)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setSpacing(0)

        self._form_panel = self._build_form_panel()
        self._form_panel.setFixedWidth(390)
        hl.addWidget(self._form_panel)

        sep = QFrame()
        sep.setFixedWidth(1)
        sep.setStyleSheet(f"background:{DarkTheme.BORDER_PRIMARY};")
        hl.addWidget(sep)

        hl.addWidget(self._build_list_panel(), 1)
        return body

    def _build_form_panel(self) -> QWidget:
        panel = QWidget()
        panel.setStyleSheet(f"background:{DarkTheme.BG_PRIMARY};")
        vl = QVBoxLayout(panel)
        vl.setContentsMargins(0, 0, 0, 0)
        vl.setSpacing(0)

        hdr = QWidget()
        hdr.setFixedHeight(36)
        hdr.setStyleSheet(f"background:{DarkTheme.BG_PRIMARY};border-bottom:1px solid {DarkTheme.BORDER_PRIMARY};")
        hh = QHBoxLayout(hdr)
        hh.setContentsMargins(14, 0, 14, 0)
        t1 = QLabel("MUAYENE FORMU")
        t1.setStyleSheet(
            f"color:{DarkTheme.TEXT_MUTED};font-family:{DarkTheme.MONOSPACE};font-size:9px;font-weight:700;letter-spacing:2px;"
        )
        hh.addWidget(t1)
        hh.addStretch()
        vl.addWidget(hdr)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet(_S_SCROLL)

        inner = QWidget()
        inner.setStyleSheet("background:transparent;")
        il = QVBoxLayout(inner)
        il.setContentsMargins(12, 12, 12, 16)
        il.setSpacing(10)

        grp_ekipman = FieldGroup("Ekipman Secimi", DarkTheme.STATUS_WARNING)
        g = QGridLayout()
        g.setContentsMargins(0, 0, 0, 0)
        g.setHorizontalSpacing(10)
        g.setVerticalSpacing(6)
        g.addWidget(self._lbl("EKIPMAN NO"), 0, 0, 1, 2)
        self.cmb_rke = QComboBox()
        self.cmb_rke.setEditable(True)
        self.cmb_rke.setStyleSheet(_S_COMBO)
        self.cmb_rke.setFixedHeight(28)
        self.cmb_rke.setPlaceholderText("Ara veya secin...")
        self.cmb_rke.currentIndexChanged.connect(self.ekipman_secildi)
        g.addWidget(self.cmb_rke, 1, 0, 1, 2)
        grp_ekipman.add_layout(g)
        il.addWidget(grp_ekipman)

        grp_fiz = FieldGroup("Fiziksel Muayene", DarkTheme.STATUS_SUCCESS)
        gf = QGridLayout()
        gf.setContentsMargins(0, 0, 0, 0)
        gf.setHorizontalSpacing(10)
        gf.setVerticalSpacing(6)
        gf.addWidget(self._lbl("MUAYENE TARIHI"), 0, 0)
        gf.addWidget(self._lbl("DURUM"), 0, 1)
        self.dt_fiziksel = QDateEdit(QDate.currentDate())
        self.dt_fiziksel.setCalendarPopup(True)
        self.dt_fiziksel.setStyleSheet(_S_DATE)
        self.dt_fiziksel.setFixedHeight(28)
        self.cmb_fiziksel = QComboBox()
        self.cmb_fiziksel.setStyleSheet(_S_COMBO)
        self.cmb_fiziksel.setFixedHeight(28)
        self.cmb_fiziksel.addItems(["Kullanima Uygun", "Kullanima Uygun Degil"])
        gf.addWidget(self.dt_fiziksel, 1, 0)
        gf.addWidget(self.cmb_fiziksel, 1, 1)
        grp_fiz.add_layout(gf)
        il.addWidget(grp_fiz)

        grp_sko = FieldGroup("Skopi Muayene", DarkTheme.ACCENT2)
        gs = QGridLayout()
        gs.setContentsMargins(0, 0, 0, 0)
        gs.setHorizontalSpacing(10)
        gs.setVerticalSpacing(6)
        gs.addWidget(self._lbl("MUAYENE TARIHI"), 0, 0)
        gs.addWidget(self._lbl("DURUM"), 0, 1)
        self.dt_skopi = QDateEdit(QDate.currentDate())
        self.dt_skopi.setCalendarPopup(True)
        self.dt_skopi.setStyleSheet(_S_DATE)
        self.dt_skopi.setFixedHeight(28)
        self.cmb_skopi = QComboBox()
        self.cmb_skopi.setStyleSheet(_S_COMBO)
        self.cmb_skopi.setFixedHeight(28)
        self.cmb_skopi.addItems(["Kullanima Uygun", "Kullanima Uygun Degil", "Yapilmadi"])
        gs.addWidget(self.dt_skopi, 1, 0)
        gs.addWidget(self.cmb_skopi, 1, 1)
        grp_sko.add_layout(gs)
        il.addWidget(grp_sko)

        grp_sonuc = FieldGroup("Sonuc ve Raporlama", DarkTheme.ACCENT)
        go = QGridLayout()
        go.setContentsMargins(0, 0, 0, 0)
        go.setHorizontalSpacing(10)
        go.setVerticalSpacing(6)
        go.addWidget(self._lbl("KONTROL EDEN"), 0, 0)
        go.addWidget(self._lbl("BIRIM SORUMLUSU"), 0, 1)
        self.cmb_kontrol = QComboBox()
        self.cmb_kontrol.setEditable(True)
        self.cmb_kontrol.setStyleSheet(_S_COMBO)
        self.cmb_kontrol.setFixedHeight(28)
        if self.kullanici_adi:
            self.cmb_kontrol.setCurrentText(str(self.kullanici_adi))
        self.cmb_sorumlu = QComboBox()
        self.cmb_sorumlu.setEditable(True)
        self.cmb_sorumlu.setStyleSheet(_S_COMBO)
        self.cmb_sorumlu.setFixedHeight(28)
        go.addWidget(self.cmb_kontrol, 1, 0)
        go.addWidget(self.cmb_sorumlu, 1, 1)
        go.addWidget(self._lbl("TEKNIK ACIKLAMA (Coklu Secim)"), 2, 0, 1, 2)
        self.cmb_aciklama = CheckableComboBox()
        self.cmb_aciklama.setStyleSheet(_S_COMBO)
        self.cmb_aciklama.setFixedHeight(28)
        go.addWidget(self.cmb_aciklama, 3, 0, 1, 2)

        file_row = QHBoxLayout()
        self.lbl_dosya = QLabel("Rapor secilmedi")
        self.lbl_dosya.setStyleSheet(f"color:{DarkTheme.TEXT_MUTED};font-size:10px;")
        btn_dosya = QPushButton("Rapor Yukle")
        btn_dosya.setStyleSheet(
            f"QPushButton{{background:{DarkTheme.BG_SECONDARY};border:1px solid {DarkTheme.BORDER_PRIMARY};border-radius:4px;"
            f"color:{DarkTheme.TEXT_SECONDARY};padding:0 12px;}}QPushButton:hover{{color:{DarkTheme.TEXT_PRIMARY};}}"
        )
        btn_dosya.setFixedHeight(28)
        btn_dosya.setCursor(QCursor(Qt.PointingHandCursor))
        btn_dosya.clicked.connect(self.dosya_sec)
        file_row.addWidget(self.lbl_dosya, 1)
        file_row.addWidget(btn_dosya)
        go.addLayout(file_row, 4, 0, 1, 2)
        grp_sonuc.add_layout(go)
        il.addWidget(grp_sonuc)

        grp_gecmis = FieldGroup("Secili Ekipmanin Gecmisi", DarkTheme.RKE_PURP)
        self._gecmis_model = GecmisModel()
        self.tbl_gecmis = QTableView()
        self.tbl_gecmis.setModel(self._gecmis_model)
        self.tbl_gecmis.setStyleSheet(_S_TABLE)
        self.tbl_gecmis.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tbl_gecmis.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tbl_gecmis.verticalHeader().setVisible(False)
        self.tbl_gecmis.setShowGrid(False)
        self.tbl_gecmis.setAlternatingRowColors(True)
        self.tbl_gecmis.setFixedHeight(140)
        self.tbl_gecmis.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tbl_gecmis.doubleClicked.connect(self._gecmis_satir_tiklandi)
        grp_gecmis.add_widget(self.tbl_gecmis)
        il.addWidget(grp_gecmis)

        il.addStretch()
        scroll.setWidget(inner)
        vl.addWidget(scroll, 1)

        self.pbar = QProgressBar()
        self.pbar.setVisible(False)
        self.pbar.setFixedHeight(3)
        self.pbar.setStyleSheet(_S_PBAR)
        vl.addWidget(self.pbar)

        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(12, 8, 12, 12)
        btn_row.setSpacing(8)
        self.btn_temizle = QPushButton("TEMIZLE")
        self.btn_temizle.setFixedHeight(34)
        self.btn_temizle.setStyleSheet(
            f"QPushButton{{background:transparent;border:1px solid {DarkTheme.BORDER_PRIMARY};"
            f"border-radius:5px;color:{DarkTheme.TEXT_MUTED};font-family:{DarkTheme.MONOSPACE};"
            f"font-size:10px;letter-spacing:1px;}}"
        )
        self.btn_temizle.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_temizle.clicked.connect(self.temizle)
        self.btn_kaydet = QPushButton("KAYDET")
        self.btn_kaydet.setFixedHeight(34)
        self.btn_kaydet.setStyleSheet(
            f"QPushButton{{background:{DarkTheme.STATUS_SUCCESS};border:none;border-radius:5px;"
            f"color:#051a10;font-family:{DarkTheme.MONOSPACE};font-size:10px;font-weight:800;"
            f"letter-spacing:1px;}}"
        )
        self.btn_kaydet.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_kaydet.clicked.connect(self.kaydet)
        if self._action_guard:
            self._action_guard.disable_if_unauthorized(self.btn_kaydet, "cihaz.write")
        btn_row.addWidget(self.btn_temizle)
        btn_row.addWidget(self.btn_kaydet)
        vl.addLayout(btn_row)
        return panel

    def _build_list_panel(self) -> QWidget:
        panel = QWidget()
        panel.setStyleSheet(f"background:{DarkTheme.BG_PRIMARY};")
        vl = QVBoxLayout(panel)
        vl.setContentsMargins(0, 0, 0, 0)
        vl.setSpacing(0)

        fbar = QWidget()
        fbar.setFixedHeight(52)
        fbar.setStyleSheet(f"background:{DarkTheme.BG_PRIMARY};border-bottom:1px solid {DarkTheme.BORDER_PRIMARY};")
        fl = QHBoxLayout(fbar)
        fl.setContentsMargins(12, 10, 12, 10)
        fl.setSpacing(8)

        self.cmb_filtre_abd = QComboBox()
        self.cmb_filtre_abd.setStyleSheet(_S_COMBO)
        self.cmb_filtre_abd.setFixedHeight(28)
        self.cmb_filtre_abd.setMinimumWidth(160)
        self.cmb_filtre_abd.addItem("Tum ABD")
        self.cmb_filtre_abd.currentIndexChanged.connect(self.tabloyu_filtrele)

        self.txt_ara = QLineEdit()
        self.txt_ara.setStyleSheet(_S_INPUT)
        self.txt_ara.setFixedHeight(28)
        self.txt_ara.setPlaceholderText("Ara...")
        self.txt_ara.textChanged.connect(self.tabloyu_filtrele)

        btn_yenile = QPushButton("Yenile")
        btn_yenile.setFixedSize(60, 28)
        btn_yenile.setStyleSheet(
            f"QPushButton{{background:{DarkTheme.BG_SECONDARY};border:1px solid {DarkTheme.BORDER_PRIMARY};border-radius:4px;"
            f"color:{DarkTheme.TEXT_SECONDARY};}}QPushButton:hover{{color:{DarkTheme.TEXT_PRIMARY};}}"
        )
        btn_yenile.setCursor(QCursor(Qt.PointingHandCursor))
        btn_yenile.clicked.connect(self.verileri_yukle)

        btn_toplu = QPushButton("Toplu Muayene")
        btn_toplu.setFixedHeight(28)
        btn_toplu.setStyleSheet(
            f"QPushButton{{background:{DarkTheme.ACCENT};border:none;border-radius:4px;"
            f"color:#0a1420;font-family:{DarkTheme.MONOSPACE};font-size:9px;font-weight:700;padding:0 12px;}}"
        )
        btn_toplu.setCursor(QCursor(Qt.PointingHandCursor))
        btn_toplu.clicked.connect(self.ac_toplu_dialog)

        fl.addWidget(self.cmb_filtre_abd)
        fl.addWidget(self.txt_ara, 1)
        fl.addWidget(btn_yenile)
        fl.addWidget(btn_toplu)
        vl.addWidget(fbar)

        self._model = RKEEnvanterModel()
        self.tablo = QTableView()
        self.tablo.setModel(self._model)
        self.tablo.setStyleSheet(_S_TABLE)
        self.tablo.setAlternatingRowColors(True)
        self.tablo.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tablo.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.tablo.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tablo.verticalHeader().setVisible(False)
        self.tablo.setShowGrid(False)
        hdr = self.tablo.horizontalHeader()
        for i, w in enumerate(RKE_WIDTHS):
            if i == len(RKE_COLS) - 1:
                hdr.setSectionResizeMode(i, QHeaderView.Stretch)
            else:
                hdr.setSectionResizeMode(i, QHeaderView.Interactive)
                hdr.resizeSection(i, w)
        self.tablo.clicked.connect(self._sag_tablo_tiklandi)
        vl.addWidget(self.tablo, 1)

        footer = QWidget()
        footer.setFixedHeight(44)
        footer.setStyleSheet(f"background:{DarkTheme.BG_SECONDARY};border-top:1px solid {DarkTheme.BORDER_PRIMARY};")
        fl = QHBoxLayout(footer)
        fl.setContentsMargins(12, 8, 12, 8)
        fl.setSpacing(8)
        self.lbl_sayi = QLabel("0 kayit")
        self.lbl_sayi.setStyleSheet(
            f"color:{DarkTheme.TEXT_MUTED};font-family:{DarkTheme.MONOSPACE};font-size:10px;font-weight:500;"
        )
        fl.addStretch()
        fl.addWidget(self.lbl_sayi)
        vl.addWidget(footer)
        return panel

    @staticmethod
    def _lbl(text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet(
            f"color:{DarkTheme.TEXT_MUTED};font-family:{DarkTheme.MONOSPACE};"
            f"font-size:10px;font-weight:500;letter-spacing:0.3px;"
        )
        return lbl

    def _update_kpi(self, rows: List[Dict]):
        toplam, uygun, uygun_d, bekleyen = len(rows), 0, 0, 0
        today = datetime.date.today()
        for r in rows:
            d = str(r.get("Durum", ""))
            if "Degil" in d:
                uygun_d += 1
            elif "Uygun" in d:
                uygun += 1
            kt = str(r.get("KontrolTarihi", ""))
            if kt and len(kt) >= 10:
                try:
                    dt_obj = datetime.datetime.strptime(kt[:10], "%Y-%m-%d").date()
                    if dt_obj <= today:
                        bekleyen += 1
                except Exception:
                    pass
        for k, v in [
            ("toplam", toplam),
            ("uygun", uygun),
            ("uygun_d", uygun_d),
            ("bekleyen", bekleyen),
        ]:
            if k in self._kpi_labels:
                self._kpi_labels[k].setText(str(v))

    def dosya_sec(self):
        yol, _ = QFileDialog.getOpenFileName(self, "Rapor", "", "PDF/Resim (*.pdf *.jpg)")
        if yol:
            self.secilen_dosya = yol
            self.lbl_dosya.setText(os.path.basename(yol))

    def verileri_yukle(self):
        self.pbar.setVisible(True)
        self.pbar.setRange(0, 0)
        self.loader = VeriYukleyici(self._db_path, use_sheets=self._use_sheets)
        self.loader.veri_hazir.connect(self.veriler_geldi)
        self.loader.hata_olustu.connect(lambda e: QMessageBox.critical(self, "Hata", e))
        self.loader.finished.connect(lambda: self.pbar.setVisible(False))
        self.loader.start()

    def veriler_geldi(self, rke_data, rke_combo, rke_dict, muayene_list,
                      headers, teknik_aciklamalar, kontrol_edenler, birim_sorumlulari):
        self.rke_data = rke_data
        self.rke_dict = rke_dict
        self.tum_muayeneler = muayene_list
        self.header_map = {h.strip(): i for i, h in enumerate(headers)}
        self.teknik_aciklamalar = teknik_aciklamalar
        self.kontrol_listesi = kontrol_edenler
        self.sorumlu_listesi = birim_sorumlulari

        self.cmb_rke.blockSignals(True)
        self.cmb_rke.clear()
        self.cmb_rke.addItems(rke_combo)
        self.cmb_rke.blockSignals(False)

        self.cmb_aciklama.clear()
        self.cmb_aciklama.addItems(teknik_aciklamalar)

        self.cmb_kontrol.clear()
        self.cmb_kontrol.addItems(kontrol_edenler)
        if self.kullanici_adi:
            self.cmb_kontrol.setCurrentText(str(self.kullanici_adi))

        self.cmb_sorumlu.clear()
        self.cmb_sorumlu.addItems(birim_sorumlulari)

        abd = sorted({str(r.get("AnaBilimDali", "")).strip() for r in rke_data
                      if str(r.get("AnaBilimDali", "")).strip()})
        self.cmb_filtre_abd.blockSignals(True)
        self.cmb_filtre_abd.clear()
        self.cmb_filtre_abd.addItem("Tum ABD")
        self.cmb_filtre_abd.addItems(abd)
        self.cmb_filtre_abd.blockSignals(False)

        self.tabloyu_filtrele()

    def tabloyu_filtrele(self):
        secilen_abd = self.cmb_filtre_abd.currentText()
        ara = self.txt_ara.text().lower()
        filtered = []
        for row in self.rke_data:
            abd = str(row.get("AnaBilimDali", "")).strip()
            if secilen_abd != "Tum ABD" and abd != secilen_abd:
                continue
            if ara and ara not in " ".join([str(v) for v in row.values()]).lower():
                continue
            filtered.append(row)
        self._model.set_rows(filtered)
        self.lbl_sayi.setText(f"{len(filtered)} kayit")
        self._update_kpi(filtered)

    def _sag_tablo_tiklandi(self, index: QModelIndex):
        row_data = self._model.get_row(index.row())
        if not row_data:
            return
        ekipman_no = str(row_data.get("EkipmanNo", ""))
        idx = self.cmb_rke.findText(ekipman_no, Qt.MatchContains)
        if idx >= 0:
            self.cmb_rke.setCurrentIndex(idx)

    def ekipman_secildi(self):
        secilen_text = self.cmb_rke.currentText()
        if not secilen_text:
            return
        ekipman_no = self.rke_dict.get(secilen_text, secilen_text.split("|")[0].strip())
        rows = []
        idx_ekipman = self.header_map.get("EkipmanNo", -1)
        if idx_ekipman == -1:
            return
        for row in self.tum_muayeneler:
            if len(row) > idx_ekipman and row[idx_ekipman] == ekipman_no:
                def get_v(key):
                    i = self.header_map.get(key, -1)
                    return row[i] if i != -1 and len(row) > i else ""
                rows.append({
                    "F_MuayeneTarihi": get_v("F_MuayeneTarihi"),
                    "S_MuayeneTarihi": get_v("S_MuayeneTarihi"),
                    "Aciklamalar": get_v("Aciklamalar"),
                    "Rapor": get_v("Rapor"),
                })
        self._gecmis_model.set_rows(rows)

    def _gecmis_satir_tiklandi(self, index: QModelIndex):
        if index.column() == 3:
            row_data = self._gecmis_model.get_row(index.row())
            if row_data:
                link = str(row_data.get("Rapor", ""))
                if "http" in link:
                    QDesktopServices.openUrl(QUrl(link))

    def temizle(self):
        self.cmb_rke.setCurrentIndex(-1)
        self.dt_fiziksel.setDate(QDate.currentDate())
        self.dt_skopi.setDate(QDate.currentDate())
        self.cmb_kontrol.setCurrentText(str(self.kullanici_adi) if self.kullanici_adi else "")
        self.cmb_sorumlu.setCurrentText("")
        self.cmb_fiziksel.setCurrentIndex(0)
        self.cmb_skopi.setCurrentIndex(0)
        self.cmb_aciklama.setCheckedItems([])
        self.lbl_dosya.setText("Rapor secilmedi")
        self.secilen_dosya = None
        self._gecmis_model.set_rows([])

    def kaydet(self):
        if self._action_guard and not self._action_guard.check_and_warn(
            self, "cihaz.write", "RKE Muayene Kaydetme"
        ):
            return
        rke_text = self.cmb_rke.currentText()
        if not rke_text:
            QMessageBox.warning(self, "Uyari", "Ekipman secin.")
            return
        ekipman_no = self.rke_dict.get(rke_text, rke_text.split("|")[0].strip())
        unique_id = f"M-{int(time.time())}"
        veri = {
            "KayitNo": unique_id,
            "EkipmanNo": ekipman_no,
            "F_MuayeneTarihi": self.dt_fiziksel.date().toString("yyyy-MM-dd"),
            "FizikselDurum": self.cmb_fiziksel.currentText(),
            "S_MuayeneTarihi": self.dt_skopi.date().toString("yyyy-MM-dd"),
            "SkopiDurum": self.cmb_skopi.currentText(),
            "Aciklamalar": self.cmb_aciklama.getCheckedItems(),
            "KontrolEden": self.cmb_kontrol.currentText(),
            "BirimSorumlusu": self.cmb_sorumlu.currentText(),
            "Not": "",
        }
        self.pbar.setVisible(True)
        self.pbar.setRange(0, 0)
        self.btn_kaydet.setEnabled(False)
        self.saver = KayitWorker(veri, self.secilen_dosya, db_path=self._db_path, use_sheets=self._use_sheets)
        self.saver.finished.connect(self.islem_basarili)
        self.saver.error.connect(lambda e: QMessageBox.critical(self, "Hata", e))
        self.saver.start()

    def islem_basarili(self, msg: str):
        self.pbar.setVisible(False)
        self.btn_kaydet.setEnabled(True)
        QMessageBox.information(self, "Basarili", msg)
        self.temizle()
        self.verileri_yukle()

    def ac_toplu_dialog(self):
        secili = self.tablo.selectionModel().selectedRows()
        if not secili:
            QMessageBox.warning(self, "Uyari", "Tabloda satir secin.")
            return
        ekipmanlar = sorted({
            str(self._model.get_row(i.row()).get("EkipmanNo", ""))
            for i in secili
            if self._model.get_row(i.row())
        })
        dlg = TopluMuayeneDialog(
            ekipmanlar, self.teknik_aciklamalar,
            self.kontrol_listesi, self.sorumlu_listesi,
            self.kullanici_adi, self,
            db_path=self._db_path, use_sheets=self._use_sheets
        )
        if dlg.exec() == QDialog.Accepted:
            QMessageBox.information(self, "Bilgi", "Toplu kayit basarili.")
            self.verileri_yukle()

    def load_data(self):
        self.verileri_yukle()

    def closeEvent(self, event):
        for attr in ("loader", "saver"):
            t = getattr(self, attr, None)
            if t and t.isRunning():
                t.quit()
                t.wait(500)
        event.accept()
