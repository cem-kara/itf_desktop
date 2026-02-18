# -*- coding: utf-8 -*-
"""
RKE Muayene Form Widget'ı
------------------------------------------
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
   ------------------------------------------  ------------------------------------------
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

    # ===========================================
    #  DIŞ ARABIRIM
    # ===========================================

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

        # Teknik Açıklama
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

    # ===========================================
    #  UI KURULUMU
    # ===========================================

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
        form_lay.setContentsMargins(0, 0, 8, 4)
        form_lay.setSpacing(8)

        # === HIZLI MUAYENE FORMU (Kompakt) ===
        # 1. Ekipman Seçimi
        h_ekip = QHBoxLayout()
        h_ekip.setSpacing(8)
        lbl_ekip = QLabel("Ekipman:")
        lbl_ekip.setStyleSheet(S.get("label", ""))
        lbl_ekip.setFixedWidth(80)
        self._cmb_rke = QComboBox()
        self._cmb_rke.setEditable(True)
        self._cmb_rke.setPlaceholderText("Ara...")
        self._cmb_rke.setStyleSheet(S.get("combo", ""))
        h_ekip.addWidget(lbl_ekip)
        h_ekip.addWidget(self._cmb_rke)
        form_lay.addLayout(h_ekip)

        # 2. Fiziksel Muayene (Tarih + Durum, tek satır)
        h_fiz = QHBoxLayout()
        h_fiz.setSpacing(8)
        lbl_fiz = QLabel("Fiziksel:")
        lbl_fiz.setStyleSheet(S.get("label", ""))
        lbl_fiz.setFixedWidth(80)
        self._dt_fiziksel = QDateEdit(QDate.currentDate())
        self._dt_fiziksel.setCalendarPopup(True)
        self._dt_fiziksel.setDisplayFormat("yyyy-MM-dd")
        self._dt_fiziksel.setStyleSheet(S.get("date", ""))
        self._dt_fiziksel.setMaximumWidth(140)
        ThemeManager.setup_calendar_popup(self._dt_fiziksel)
        
        self._cmb_fiziksel = QComboBox()
        self._cmb_fiziksel.addItems(["Kullanıma Uygun", "Kullanıma Uygun Değil"])
        self._cmb_fiziksel.setStyleSheet(S.get("combo", ""))
        h_fiz.addWidget(lbl_fiz)
        h_fiz.addWidget(self._dt_fiziksel)
        h_fiz.addWidget(self._cmb_fiziksel)
        h_fiz.addStretch()
        form_lay.addLayout(h_fiz)

        # 3. Skopi Muayene (Tarih + Durum, tek satır)
        h_sko = QHBoxLayout()
        h_sko.setSpacing(8)
        lbl_sko = QLabel("Skopi:")
        lbl_sko.setStyleSheet(S.get("label", ""))
        lbl_sko.setFixedWidth(80)
        self._dt_skopi = QDateEdit(QDate.currentDate())
        self._dt_skopi.setCalendarPopup(True)
        self._dt_skopi.setDisplayFormat("yyyy-MM-dd")
        self._dt_skopi.setStyleSheet(S.get("date", ""))
        self._dt_skopi.setMaximumWidth(140)
        ThemeManager.setup_calendar_popup(self._dt_skopi)
        
        self._cmb_skopi = QComboBox()
        self._cmb_skopi.addItems(["Kullanıma Uygun", "Kullanıma Uygun Değil", "Yapılmadı"])
        self._cmb_skopi.setStyleSheet(S.get("combo", ""))
        h_sko.addWidget(lbl_sko)
        h_sko.addWidget(self._dt_skopi)
        h_sko.addWidget(self._cmb_skopi)
        h_sko.addStretch()
        form_lay.addLayout(h_sko)

        # 4. Kontrol Eden + Birim Sorumlusu (tek satır)
        h_pers = QHBoxLayout()
        h_pers.setSpacing(8)
        lbl_pers = QLabel("Personel:")
        lbl_pers.setStyleSheet(S.get("label", ""))
        lbl_pers.setFixedWidth(80)
        self._cmb_kontrol = QComboBox()
        self._cmb_kontrol.setEditable(True)
        self._cmb_kontrol.setStyleSheet(S.get("combo", ""))
        self._cmb_sorumlu = QComboBox()
        self._cmb_sorumlu.setEditable(True)
        self._cmb_sorumlu.setStyleSheet(S.get("combo", ""))
        h_pers.addWidget(lbl_pers)
        h_pers.addWidget(QLabel("Kontrol Eden:"))
        h_pers.addWidget(self._cmb_kontrol, 1)
        h_pers.addWidget(QLabel("Sorumlu:"))
        h_pers.addWidget(self._cmb_sorumlu, 1)
        form_lay.addLayout(h_pers)

        # 5. Teknik Açıklama
        h_acik = QHBoxLayout()
        h_acik.setSpacing(8)
        lbl_acik = QLabel("Açıklama:")
        lbl_acik.setStyleSheet(S.get("label", ""))
        lbl_acik.setFixedWidth(80)
        self._cmb_aciklama = CheckableComboBox()
        self._cmb_aciklama.setStyleSheet(S.get("combo", ""))
        h_acik.addWidget(lbl_acik)
        h_acik.addWidget(self._cmb_aciklama)
        form_lay.addLayout(h_acik)

        # 6. Rapor Dosyası
        h_dosya = QHBoxLayout()
        h_dosya.setSpacing(8)
        lbl_dosya_label = QLabel("Rapor:")
        lbl_dosya_label.setStyleSheet(S.get("label", ""))
        lbl_dosya_label.setFixedWidth(80)
        self._lbl_dosya = QLabel("seçilmedi")
        self._lbl_dosya.setStyleSheet(f"color:{DarkTheme.TEXT_MUTED}; font-size:10px;")
        btn_dosya = QPushButton("Seç")
        btn_dosya.setStyleSheet(S.get("file_btn", ""))
        btn_dosya.setMaximumWidth(60)
        btn_dosya.setCursor(QCursor(Qt.PointingHandCursor))
        btn_dosya.clicked.connect(self._sec_dosya)
        IconRenderer.set_button_icon(btn_dosya, "upload", color=DarkTheme.TEXT_PRIMARY, size=12)
        h_dosya.addWidget(lbl_dosya_label)
        h_dosya.addWidget(self._lbl_dosya)
        h_dosya.addWidget(btn_dosya)
        h_dosya.addStretch()
        form_lay.addLayout(h_dosya)

        # === GEÇMIŞ MUAYENELER (Minimal) ===
        lbl_gecmis = QLabel("Geçmiş Muayeneler")
        lbl_gecmis.setStyleSheet(S.get("label", ""))
        form_lay.addWidget(lbl_gecmis)

        self._gecmis_model = GecmisMuayeneModel()
        self._gecmis_view = QTableView()
        self._gecmis_view.setModel(self._gecmis_model)
        self._gecmis_view.setStyleSheet(S.get("table", ""))
        self._gecmis_view.verticalHeader().setVisible(False)
        self._gecmis_view.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._gecmis_view.setFixedHeight(100)
        self._gecmis_view.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        form_lay.addWidget(self._gecmis_view)

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

    # ===========================================
    #  YARDIMCI FABRİKALAR
    # ===========================================

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

    # ===========================================
    #  SİNYALLER
    # ===========================================

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

    # ===========================================
    #  KAYDET / TEMİZLE
    # ===========================================

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

    # ===========================================
    #  DOSYA SEÇİMİ
    # ===========================================

    def _sec_dosya(self):
        yol, _ = QFileDialog.getOpenFileName(
            self, "Rapor Seç", "", "PDF / Resim (*.pdf *.jpg *.jpeg *.png)"
        )
        if yol:
            self._secilen_dosya = yol
            self._lbl_dosya.setText(os.path.basename(yol))
