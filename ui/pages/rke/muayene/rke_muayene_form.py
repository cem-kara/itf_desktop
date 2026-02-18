# -*- coding: utf-8 -*-
"""
RKE Muayene Form Widget'ı
──────────────────────────
Sol panel: tekli muayene giriş formu + geçmiş muayene tablosu.

Sinyaller (dışarıya):
    kaydet_istendi(veri: dict, dosya_yolu: str | None)
    temizle_istendi()
"""
import os

from PySide6.QtCore import Qt, QDate, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QProgressBar, QFrame, QComboBox,
    QDateEdit, QGroupBox, QMessageBox, QTableView, QHeaderView,
    QAbstractItemView, QFileDialog,
)
from PySide6.QtGui import QCursor

from ui.theme_manager import ThemeManager
from ui.styles import DarkTheme
from ui.styles.icons import IconRenderer

from ui.pages.rke.shared.checkable_combo import CheckableComboBox
from ui.pages.rke.muayene.rke_muayene_models import GecmisMuayeneModel

S = ThemeManager.get_all_component_styles()


class RKEMuayeneFormWidget(QWidget):
    """
    Sol panel widget'ı.

    Sinyal              Açıklama
    ──────────────────  ──────────────────────────────────────
    kaydet_istendi      Kaydet tuşuna basıldığında (veri, dosya_yolu)
    temizle_istendi     Temizle tuşuna basıldığında
    """
    kaydet_istendi  = Signal(dict, object)   # veri dict, dosya_yolu str|None
    temizle_istendi = Signal()

    def __init__(self, kullanici_adi: str = None, parent=None):
        super().__init__(parent)
        self._kullanici_adi  = kullanici_adi
        self._secilen_dosya  = None
        self._tum_muayeneler = []

        self._setup_ui()
        self._connect_signals()

    # ═══════════════════════════════════════════
    #  DIŞ ARABIRIM
    # ═══════════════════════════════════════════

    def set_context(
        self,
        rke_data: list,
        teknik: list,
        kontrol_listesi: list,
        sorumlu_listesi: list,
        tum_muayene: list,
    ):
        """Ana sayfa tarafından her veri yüklemesinden sonra çağrılır."""
        self._tum_muayeneler = tum_muayene

        # Ekipman combo
        self._cmb_rke.blockSignals(True)
        self._cmb_rke.clear()
        items = sorted([
            f"{str(r.get('EkipmanNo', '')).strip()} | {str(r.get('KoruyucuCinsi', '')).strip()}"
            for r in rke_data if r.get("EkipmanNo")
        ])
        self._cmb_rke.addItems(items)
        self._cmb_rke.setCurrentIndex(-1)
        self._cmb_rke.blockSignals(False)

        # Teknik açıklama
        self._cmb_aciklama.clear()
        self._cmb_aciklama.addItems(teknik)

        # Kontrol Eden
        self._cmb_kontrol.blockSignals(True)
        mevcut_kontrol = self._cmb_kontrol.currentText()
        self._cmb_kontrol.clear()
        self._cmb_kontrol.addItems(kontrol_listesi)
        if self._kullanici_adi:
            self._cmb_kontrol.setCurrentText(self._kullanici_adi)
        elif mevcut_kontrol:
            self._cmb_kontrol.setCurrentText(mevcut_kontrol)
        self._cmb_kontrol.blockSignals(False)

        # Birim Sorumlusu
        self._cmb_sorumlu.blockSignals(True)
        mevcut_sorumlu = self._cmb_sorumlu.currentText()
        self._cmb_sorumlu.clear()
        self._cmb_sorumlu.addItems(sorumlu_listesi)
        if mevcut_sorumlu:
            self._cmb_sorumlu.setCurrentText(mevcut_sorumlu)
        self._cmb_sorumlu.blockSignals(False)

    def set_busy(self, busy: bool):
        self._pbar.setVisible(busy)
        self._pbar.setRange(0, 0 if busy else 1)
        self._btn_kaydet.setEnabled(not busy)

    def goster_gecmis_ekipman(self, ekipman_no: str):
        """Ana sayfa tablodaki seçime göre geçmişi senkronize etmek için çağırır."""
        idx = self._cmb_rke.findText(ekipman_no, Qt.MatchContains)
        if idx >= 0:
            self._cmb_rke.blockSignals(True)
            self._cmb_rke.setCurrentIndex(idx)
            self._cmb_rke.blockSignals(False)
        gecmis = [
            m for m in self._tum_muayeneler
            if str(m.get("EkipmanNo", "")).strip() == ekipman_no
        ]
        self._gecmis_model.set_data(gecmis)

    # ═══════════════════════════════════════════
    #  UI KURULUMU
    # ═══════════════════════════════════════════

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet(S.get("scroll", ""))

        form_inner = QWidget()
        form_inner.setStyleSheet("background: transparent;")
        form_lay = QVBoxLayout(form_inner)
        form_lay.setContentsMargins(0, 0, 8, 0)
        form_lay.setSpacing(12)

        # 1. Ekipman Seçimi
        grp_ekipman = QGroupBox("Ekipman Seçimi")
        grp_ekipman.setStyleSheet(S.get("group", ""))
        v_ekip = QVBoxLayout(grp_ekipman)
        self._cmb_rke = QComboBox()
        self._cmb_rke.setEditable(True)
        self._cmb_rke.setPlaceholderText("Ekipman Ara...")
        self._cmb_rke.setStyleSheet(S.get("combo", ""))
        v_ekip.addWidget(self._labeled("Ekipman No | Cinsi", self._cmb_rke))
        form_lay.addWidget(grp_ekipman)

        # 2. Muayene Detayları
        grp_detay = QGroupBox("Muayene Detayları")
        grp_detay.setStyleSheet(S.get("group", ""))
        v_detay = QVBoxLayout(grp_detay)

        h_fiz = QHBoxLayout()
        self._dt_fiziksel  = self._make_date_widget("Fiziksel Muayene Tarihi", h_fiz)
        self._cmb_fiziksel = self._make_combo_widget(
            "Fiziksel Durum", ["Kullanıma Uygun", "Kullanıma Uygun Değil"], h_fiz
        )
        v_detay.addLayout(h_fiz)

        h_sko = QHBoxLayout()
        self._dt_skopi  = self._make_date_widget("Skopi Muayene Tarihi", h_sko)
        self._cmb_skopi = self._make_combo_widget(
            "Skopi Durumu", ["Kullanıma Uygun", "Kullanıma Uygun Değil", "Yapılmadı"], h_sko
        )
        v_detay.addLayout(h_sko)

        form_lay.addWidget(grp_detay)

        # 3. Sonuç ve Raporlama
        grp_sonuc = QGroupBox("Sonuç ve Raporlama")
        grp_sonuc.setStyleSheet(S.get("group", ""))
        v_sonuc = QVBoxLayout(grp_sonuc)

        h_pers = QHBoxLayout()
        self._cmb_kontrol = QComboBox()
        self._cmb_kontrol.setEditable(True)
        self._cmb_kontrol.setStyleSheet(S.get("combo", ""))
        h_pers.addWidget(self._labeled("Kontrol Eden", self._cmb_kontrol))

        self._cmb_sorumlu = QComboBox()
        self._cmb_sorumlu.setEditable(True)
        self._cmb_sorumlu.setStyleSheet(S.get("combo", ""))
        h_pers.addWidget(self._labeled("Birim Sorumlusu", self._cmb_sorumlu))
        v_sonuc.addLayout(h_pers)

        self._cmb_aciklama = CheckableComboBox()
        self._cmb_aciklama.setStyleSheet(S.get("combo", ""))
        v_sonuc.addWidget(self._labeled("Teknik Açıklama (Çoklu Seçim)", self._cmb_aciklama))

        h_dosya = QHBoxLayout()
        self._lbl_dosya = QLabel("Rapor seçilmedi")
        self._lbl_dosya.setStyleSheet(f"color:{DarkTheme.TEXT_MUTED}; font-size:11px; font-style:italic;")
        btn_dosya = QPushButton("Rapor Seç")
        btn_dosya.setStyleSheet(S.get("file_btn", ""))
        btn_dosya.setCursor(QCursor(Qt.PointingHandCursor))
        btn_dosya.clicked.connect(self._sec_dosya)
        IconRenderer.set_button_icon(btn_dosya, "upload", color=DarkTheme.TEXT_PRIMARY, size=14)
        h_dosya.addWidget(self._lbl_dosya)
        h_dosya.addWidget(btn_dosya)
        v_sonuc.addLayout(h_dosya)

        form_lay.addWidget(grp_sonuc)

        # 4. Geçmiş Muayeneler
        grp_gecmis = QGroupBox("Geçmiş Muayeneler")
        grp_gecmis.setStyleSheet(S.get("group", ""))
        v_gec = QVBoxLayout(grp_gecmis)

        self._gecmis_model = GecmisMuayeneModel()
        self._gecmis_view  = QTableView()
        self._gecmis_view.setModel(self._gecmis_model)
        self._gecmis_view.setStyleSheet(S.get("table", ""))
        self._gecmis_view.verticalHeader().setVisible(False)
        self._gecmis_view.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._gecmis_view.setFixedHeight(140)
        self._gecmis_view.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        v_gec.addWidget(self._gecmis_view)

        form_lay.addWidget(grp_gecmis)
        form_lay.addStretch()

        scroll.setWidget(form_inner)
        root.addWidget(scroll, 1)

        # Progress
        self._pbar = QProgressBar()
        self._pbar.setFixedHeight(4)
        self._pbar.setTextVisible(False)
        self._pbar.setStyleSheet(S.get("progress", ""))
        self._pbar.setVisible(False)
        root.addWidget(self._pbar)

        # Butonlar
        h_btn = QHBoxLayout()
        h_btn.setSpacing(8)
        self._btn_temizle = QPushButton("TEMİZLE")
        self._btn_temizle.setStyleSheet(S.get("cancel_btn", ""))
        self._btn_temizle.setCursor(QCursor(Qt.PointingHandCursor))
        IconRenderer.set_button_icon(self._btn_temizle, "x", color=DarkTheme.TEXT_PRIMARY, size=14)

        self._btn_kaydet = QPushButton("KAYDET")
        self._btn_kaydet.setStyleSheet(S.get("save_btn", ""))
        self._btn_kaydet.setCursor(QCursor(Qt.PointingHandCursor))
        IconRenderer.set_button_icon(self._btn_kaydet, "save", color=DarkTheme.TEXT_PRIMARY, size=14)

        h_btn.addWidget(self._btn_temizle)
        h_btn.addWidget(self._btn_kaydet)
        root.addLayout(h_btn)

    # ═══════════════════════════════════════════
    #  YARDIMCI FABRİKALAR
    # ═══════════════════════════════════════════

    def _labeled(self, text: str, widget) -> QWidget:
        c = QWidget()
        c.setStyleSheet("background: transparent;")
        lay = QVBoxLayout(c)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)
        lbl = QLabel(text)
        lbl.setStyleSheet(S.get("label", ""))
        lay.addWidget(lbl)
        lay.addWidget(widget)
        return c

    def _make_date_widget(self, label_text: str, parent_layout) -> QDateEdit:
        c = QWidget()
        c.setStyleSheet("background: transparent;")
        lay = QVBoxLayout(c)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)
        lbl = QLabel(label_text)
        lbl.setStyleSheet(S.get("label", ""))
        de = QDateEdit(QDate.currentDate())
        de.setCalendarPopup(True)
        de.setDisplayFormat("yyyy-MM-dd")
        de.setStyleSheet(S.get("date", ""))
        ThemeManager.setup_calendar_popup(de)
        lay.addWidget(lbl)
        lay.addWidget(de)
        parent_layout.addWidget(c)
        return de

    def _make_combo_widget(self, label_text: str, items: list, parent_layout) -> QComboBox:
        c = QWidget()
        c.setStyleSheet("background: transparent;")
        lay = QVBoxLayout(c)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)
        lbl = QLabel(label_text)
        lbl.setStyleSheet(S.get("label", ""))
        cmb = QComboBox()
        cmb.setStyleSheet(S.get("combo", ""))
        cmb.addItems(items)
        lay.addWidget(lbl)
        lay.addWidget(cmb)
        parent_layout.addWidget(c)
        return cmb

    # ═══════════════════════════════════════════
    #  SİNYALLER
    # ═══════════════════════════════════════════

    def _connect_signals(self):
        self._btn_kaydet.clicked.connect(self._on_save)
        self._btn_temizle.clicked.connect(self._on_clear)
        self._cmb_rke.currentIndexChanged.connect(self._on_ekipman_secildi)

    def _on_ekipman_secildi(self):
        txt = self._cmb_rke.currentText()
        if not txt:
            return
        ekipman_no = txt.split("|")[0].strip()
        gecmis = [
            m for m in self._tum_muayeneler
            if str(m.get("EkipmanNo", "")).strip() == ekipman_no
        ]
        self._gecmis_model.set_data(gecmis)

    # ═══════════════════════════════════════════
    #  KAYDET / TEMİZLE
    # ═══════════════════════════════════════════

    def _on_save(self):
        import time
        txt = self._cmb_rke.currentText()
        if not txt:
            QMessageBox.warning(self, "Eksik Bilgi", "Lütfen bir ekipman seçin.")
            return

        ekipman_no = txt.split("|")[0].strip()
        veri = {
            "KayitNo":              f"M-{int(time.time())}",
            "EkipmanNo":            ekipman_no,
            "FMuayeneTarihi":       self._dt_fiziksel.date().toString("yyyy-MM-dd"),
            "FizikselDurum":        self._cmb_fiziksel.currentText(),
            "SMuayeneTarihi":       self._dt_skopi.date().toString("yyyy-MM-dd"),
            "SkopiDurum":           self._cmb_skopi.currentText(),
            "Aciklamalar":          self._cmb_aciklama.get_checked_items(),
            "KontrolEdenUnvani":    self._cmb_kontrol.currentText(),
            "BirimSorumlusuUnvani": self._cmb_sorumlu.currentText(),
            "Notlar":               "",
        }
        self.kaydet_istendi.emit(veri, self._secilen_dosya)

    def _on_clear(self):
        self._cmb_rke.setCurrentIndex(-1)
        self._dt_fiziksel.setDate(QDate.currentDate())
        self._dt_skopi.setDate(QDate.currentDate())
        self._cmb_fiziksel.setCurrentIndex(0)
        self._cmb_skopi.setCurrentIndex(0)
        self._cmb_aciklama.set_checked_items([])
        if self._kullanici_adi:
            self._cmb_kontrol.setCurrentText(self._kullanici_adi)
        else:
            self._cmb_kontrol.clearEditText()
        self._cmb_sorumlu.clearEditText()
        self._lbl_dosya.setText("Rapor seçilmedi")
        self._secilen_dosya = None
        self._gecmis_model.set_data([])
        self.temizle_istendi.emit()

    # ═══════════════════════════════════════════
    #  DOSYA SEÇİMİ
    # ═══════════════════════════════════════════

    def _sec_dosya(self):
        yol, _ = QFileDialog.getOpenFileName(
            self, "Rapor Seç", "", "PDF / Resim (*.pdf *.jpg *.jpeg *.png)"
        )
        if yol:
            self._secilen_dosya = yol
            self._lbl_dosya.setText(os.path.basename(yol))
