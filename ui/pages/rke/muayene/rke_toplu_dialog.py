# -*- coding: utf-8 -*-
"""
Toplu Muayene Dialog
─────────────────────
Listeden seçilen birden fazla ekipmana aynı anda muayene kaydı ekler.
rke_muayene.py tarafından açılır; bağımsız QDialog penceresidir.
"""
import os

from PySide6.QtCore import Qt, QDate
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QProgressBar, QComboBox, QGroupBox, QListWidget,
    QFileDialog, QMessageBox, QWidget,
)
from PySide6.QtGui import QCursor

from ui.theme_manager import ThemeManager
from ui.styles import DarkTheme
from ui.styles.icons import IconRenderer

from ui.pages.rke.shared.checkable_combo import CheckableComboBox
from ui.pages.rke.muayene.rke_muayene_workers import TopluKayitWorkerThread

S = ThemeManager.get_all_component_styles()


class TopluMuayeneDialog(QDialog):
    """
    Seçili ekipmanlara aynı anda muayene kaydı ekler.

    Parametreler
    ────────────
    secilen_ekipmanlar  : ["RKE-001", "RKE-002", ...] listesi
    teknik_aciklamalar  : Sabitler tablosundan gelen RKE_Teknik listesi
    kontrol_listesi     : Daha önce kullanılmış KontrolEdenUnvani değerleri
    sorumlu_listesi     : Daha önce kullanılmış BirimSorumlusuUnvani değerleri
    kullanici_adi       : Oturum açık kullanıcı adı (opsiyonel)
    """

    def __init__(
        self,
        secilen_ekipmanlar: list,
        teknik_aciklamalar: list,
        kontrol_listesi: list,
        sorumlu_listesi: list,
        kullanici_adi: str = None,
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowTitle(f"Toplu Muayene — {len(secilen_ekipmanlar)} Ekipman")
        self.resize(680, 640)

        self._ekipmanlar         = secilen_ekipmanlar
        self._teknik_aciklamalar = teknik_aciklamalar
        self._kontrol_listesi    = kontrol_listesi
        self._sorumlu_listesi    = sorumlu_listesi
        self._kullanici_adi      = kullanici_adi
        self._dosya_yolu         = None

        self._setup_ui()

    # ═══════════════════════════════════════════
    #  UI
    # ═══════════════════════════════════════════

    def _setup_ui(self):
        main = QVBoxLayout(self)
        main.setSpacing(12)

        # Ekipman listesi özeti
        grp_list = QGroupBox(f"Ekipmanlar ({len(self._ekipmanlar)})")
        grp_list.setStyleSheet(S.get("group", ""))
        v_list = QVBoxLayout(grp_list)
        lst = QListWidget()
        lst.addItems(self._ekipmanlar)
        lst.setFixedHeight(80)
        v_list.addWidget(lst)
        main.addWidget(grp_list)

        # Fiziksel Muayene
        self._grp_fiz = QGroupBox("Fiziksel Muayene")
        self._grp_fiz.setCheckable(True)
        self._grp_fiz.setChecked(True)
        self._grp_fiz.setStyleSheet(S.get("group", ""))
        h_fiz = QHBoxLayout(self._grp_fiz)
        self._dt_fiz  = self._make_date("Tarih")
        self._cmb_fiz = self._make_combo("Durum", ["Kullanıma Uygun", "Kullanıma Uygun Değil"])
        h_fiz.addWidget(self._dt_fiz["widget"])
        h_fiz.addWidget(self._cmb_fiz["widget"])
        main.addWidget(self._grp_fiz)

        # Skopi Muayene
        self._grp_sko = QGroupBox("Skopi Muayene")
        self._grp_sko.setCheckable(True)
        self._grp_sko.setChecked(False)
        self._grp_sko.setStyleSheet(S.get("group", ""))
        h_sko = QHBoxLayout(self._grp_sko)
        self._dt_sko  = self._make_date("Tarih")
        self._cmb_sko = self._make_combo("Durum", ["Kullanıma Uygun", "Kullanıma Uygun Değil", "Yapılmadı"])
        h_sko.addWidget(self._dt_sko["widget"])
        h_sko.addWidget(self._cmb_sko["widget"])
        main.addWidget(self._grp_sko)

        # Ortak Bilgiler
        grp_ortak = QGroupBox("Ortak Bilgiler")
        grp_ortak.setStyleSheet(S.get("group", ""))
        v_ortak = QVBoxLayout(grp_ortak)

        h_pers = QHBoxLayout()
        self._cmb_kontrol = QComboBox()
        self._cmb_kontrol.setEditable(True)
        self._cmb_kontrol.setStyleSheet(S.get("combo", ""))
        self._cmb_kontrol.addItems(self._kontrol_listesi)
        if self._kullanici_adi:
            self._cmb_kontrol.setCurrentText(self._kullanici_adi)
        h_pers.addWidget(self._labeled("Kontrol Eden", self._cmb_kontrol))

        self._cmb_sorumlu = QComboBox()
        self._cmb_sorumlu.setEditable(True)
        self._cmb_sorumlu.setStyleSheet(S.get("combo", ""))
        self._cmb_sorumlu.addItems(self._sorumlu_listesi)
        h_pers.addWidget(self._labeled("Birim Sorumlusu", self._cmb_sorumlu))
        v_ortak.addLayout(h_pers)

        self._cmb_aciklama = CheckableComboBox()
        self._cmb_aciklama.setStyleSheet(S.get("combo", ""))
        self._cmb_aciklama.addItems(self._teknik_aciklamalar)
        v_ortak.addWidget(self._labeled("Teknik Açıklama (Çoklu Seçim)", self._cmb_aciklama))

        h_dosya = QHBoxLayout()
        self._lbl_dosya = QLabel("Dosya seçilmedi")
        self._lbl_dosya.setStyleSheet("color:#8b8fa3; font-size:11px;")
        btn_dosya = QPushButton("Ortak Rapor Seç")
        btn_dosya.setStyleSheet(S.get("file_btn", ""))
        btn_dosya.clicked.connect(self._sec_dosya)
        IconRenderer.set_button_icon(btn_dosya, "upload", color=DarkTheme.TEXT_PRIMARY, size=14)
        h_dosya.addWidget(self._lbl_dosya)
        h_dosya.addWidget(btn_dosya)
        v_ortak.addLayout(h_dosya)

        main.addWidget(grp_ortak)

        # Progress + Butonlar
        self._pbar = QProgressBar()
        self._pbar.setFixedHeight(4)
        self._pbar.setTextVisible(False)
        self._pbar.setVisible(False)
        main.addWidget(self._pbar)

        h_btn = QHBoxLayout()
        h_btn.addStretch()

        btn_iptal = QPushButton("İptal")
        btn_iptal.setStyleSheet(S.get("cancel_btn", ""))
        btn_iptal.setCursor(QCursor(Qt.PointingHandCursor))
        btn_iptal.clicked.connect(self.reject)
        IconRenderer.set_button_icon(btn_iptal, "x", color=DarkTheme.TEXT_PRIMARY, size=14)

        self._btn_baslat = QPushButton("Başlat")
        self._btn_baslat.setStyleSheet(S.get("save_btn", ""))
        self._btn_baslat.setCursor(QCursor(Qt.PointingHandCursor))
        self._btn_baslat.clicked.connect(self._on_save)
        IconRenderer.set_button_icon(self._btn_baslat, "save", color=DarkTheme.TEXT_PRIMARY, size=14)

        h_btn.addWidget(btn_iptal)
        h_btn.addWidget(self._btn_baslat)
        main.addLayout(h_btn)

    # ═══════════════════════════════════════════
    #  YARDIMCI FABRİKALAR
    # ═══════════════════════════════════════════

    def _labeled(self, label_text: str, widget) -> QWidget:
        c = QWidget()
        c.setStyleSheet("background: transparent;")
        lay = QVBoxLayout(c)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)
        lbl = QLabel(label_text)
        lbl.setStyleSheet(S.get("label", ""))
        lay.addWidget(lbl)
        lay.addWidget(widget)
        return c

    def _make_date(self, label: str) -> dict:
        from PySide6.QtWidgets import QDateEdit
        c = QWidget()
        c.setStyleSheet("background: transparent;")
        lay = QVBoxLayout(c)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)
        lbl = QLabel(label)
        lbl.setStyleSheet(S.get("label", ""))
        de = QDateEdit(QDate.currentDate())
        de.setCalendarPopup(True)
        de.setDisplayFormat("yyyy-MM-dd")
        de.setStyleSheet(S.get("date", ""))
        ThemeManager.setup_calendar_popup(de)
        lay.addWidget(lbl)
        lay.addWidget(de)
        return {"widget": c, "date": de}

    def _make_combo(self, label: str, items: list) -> dict:
        c = QWidget()
        c.setStyleSheet("background: transparent;")
        lay = QVBoxLayout(c)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)
        lbl = QLabel(label)
        lbl.setStyleSheet(S.get("label", ""))
        cmb = QComboBox()
        cmb.setStyleSheet(S.get("combo", ""))
        cmb.addItems(items)
        lay.addWidget(lbl)
        lay.addWidget(cmb)
        return {"widget": c, "combo": cmb}

    # ═══════════════════════════════════════════
    #  DOSYA / KAYDET
    # ═══════════════════════════════════════════

    def _sec_dosya(self):
        yol, _ = QFileDialog.getOpenFileName(
            self, "Rapor Seç", "", "PDF / Resim (*.pdf *.jpg *.jpeg *.png)"
        )
        if yol:
            self._dosya_yolu = yol
            self._lbl_dosya.setText(os.path.basename(yol))

    def _on_save(self):
        ortak_veri = {
            "FMuayeneTarihi":       self._dt_fiz["date"].date().toString("yyyy-MM-dd") if self._grp_fiz.isChecked() else "",
            "FizikselDurum":        self._cmb_fiz["combo"].currentText()               if self._grp_fiz.isChecked() else "",
            "SMuayeneTarihi":       self._dt_sko["date"].date().toString("yyyy-MM-dd") if self._grp_sko.isChecked() else "",
            "SkopiDurum":           self._cmb_sko["combo"].currentText()               if self._grp_sko.isChecked() else "",
            "Aciklamalar":          self._cmb_aciklama.get_checked_items(),
            "KontrolEdenUnvani":    self._cmb_kontrol.currentText(),
            "BirimSorumlusuUnvani": self._cmb_sorumlu.currentText(),
            "Notlar":               "Toplu Kayıt",
        }
        self._btn_baslat.setEnabled(False)
        self._pbar.setVisible(True)
        self._pbar.setRange(0, 0)

        self._worker = TopluKayitWorkerThread(self._ekipmanlar, ortak_veri, self._dosya_yolu)
        self._worker.kayit_tamam.connect(lambda _: self.accept())
        self._worker.hata_olustu.connect(self._on_hata)
        self._worker.start()

    def _on_hata(self, msg: str):
        self._pbar.setVisible(False)
        self._btn_baslat.setEnabled(True)
        QMessageBox.critical(self, "Hata", msg)
