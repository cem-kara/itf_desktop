# -*- coding: utf-8 -*-
"""
RKE Muayene Merkezi
────────────────────
Ekipman listesinden bir satır seçildiğinde sol muayene paneli
animasyonlu biçimde kayarak açılır (slide-in drawer).

Alt modüller değişmedi:
  rke/muayene/rke_muayene_models  → RKEListTableModel, GecmisMuayeneModel
  rke/muayene/rke_muayene_workers → VeriYukleyiciThread, KayitWorkerThread
  rke/muayene/rke_muayene_form    → RKEMuayeneFormWidget
  rke/muayene/rke_toplu_dialog    → TopluMuayeneDialog
"""
from PySide6.QtCore import (
    Qt, QSortFilterProxyModel,
    QPropertyAnimation, QEasingCurve,
)
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QProgressBar, QFrame, QComboBox, QLineEdit,
    QMessageBox, QTableView, QHeaderView,
    QAbstractItemView, QDialog, QSizePolicy,
)
from PySide6.QtGui import QCursor

from core.logger import logger
from ui.theme_manager import ThemeManager
from ui.styles import DarkTheme
from ui.styles.icons import IconRenderer

from ui.pages.rke.muayene.rke_muayene_models import RKEListTableModel, RKE_COLUMNS
from ui.pages.rke.muayene.rke_muayene_workers import VeriYukleyiciThread, KayitWorkerThread
from ui.pages.rke.muayene.rke_muayene_form import RKEMuayeneFormWidget
from ui.pages.rke.muayene.rke_toplu_dialog import TopluMuayeneDialog

S = ThemeManager.get_all_component_styles()

_PANEL_GENISLIK = 420   # açık panel genişliği (px)
_ANIM_SURE      = 280   # animasyon süresi (ms)


# ═══════════════════════════════════════════════════════════
#  SLIDE-IN DRAWER
# ═══════════════════════════════════════════════════════════

class SlidePanel(QWidget):
    """
    maximumWidth animasyonu ile yatay kayarak açılıp kapanan panel.
    İçindeki widget sabit genişlikte render edilir; panel onu kırpar.
    Sağ üst köşede "×" kapatma butonu bulunur.
    """

    def __init__(self, icerik: QWidget, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        self.setMaximumWidth(0)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # ── Başlık çubuğu (ekipman adı + kapat butonu) ──
        header = QFrame()
        header.setFixedWidth(_PANEL_GENISLIK)
        header.setStyleSheet(
            f"background:{DarkTheme.BG_SECONDARY};"
            f"border-bottom: 1px solid {DarkTheme.BORDER_PRIMARY};"
        )
        h_lay = QHBoxLayout(header)
        h_lay.setContentsMargins(12, 6, 8, 6)
        h_lay.setSpacing(8)

        self.lbl_ekipman = QLabel("Muayene Formu")
        self.lbl_ekipman.setStyleSheet(
            f"color:{DarkTheme.TEXT_PRIMARY}; font-size:12px;"
            "font-weight:600; background:transparent; border:none;"
        )
        h_lay.addWidget(self.lbl_ekipman, 1)

        self.btn_kapat = QPushButton("✕")
        self.btn_kapat.setFixedSize(26, 26)
        self.btn_kapat.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_kapat.setToolTip("Paneli Kapat")
        self.btn_kapat.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {DarkTheme.TEXT_MUTED};
                border: none;
                border-radius: 4px;
                font-size: 14px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background: {DarkTheme.STATUS_ERROR};
                color: #ffffff;
            }}
        """)
        h_lay.addWidget(self.btn_kapat)
        lay.addWidget(header)

        icerik.setFixedWidth(_PANEL_GENISLIK)
        lay.addWidget(icerik)

        self._anim = QPropertyAnimation(self, b"maximumWidth")
        self._anim.setEasingCurve(QEasingCurve.InOutQuart)
        self._anim.setDuration(_ANIM_SURE)

    def ac(self):
        self._anim.stop()
        self._anim.setStartValue(self.maximumWidth())
        self._anim.setEndValue(_PANEL_GENISLIK)
        self._anim.start()

    def kapat(self, bitis_cb=None):
        self._anim.stop()
        self._anim.setStartValue(self.maximumWidth())
        self._anim.setEndValue(0)
        if bitis_cb:
            self._anim.finished.connect(bitis_cb)
        self._anim.start()

    def acik_mi(self) -> bool:
        return self.maximumWidth() > 0


# ═══════════════════════════════════════════════════════════
#  ANA SAYFA
# ═══════════════════════════════════════════════════════════

class RKEMuayenePage(QWidget):
    """
    RKE Muayene Merkezi.
    kullanici_adi: Kontrol Eden alanına otomatik yazılır.
    """

    def __init__(self, db=None, kullanici_adi: str = None, parent=None):
        super().__init__(parent)
        self.setStyleSheet(S.get("page", "background-color: transparent;"))
        self._db             = db
        self._rke_data       = []
        self._tum_muayeneler = []
        self._teknik_acik    = []
        self._kontrol_list   = []
        self._sorumlu_list   = []

        self._setup_ui(kullanici_adi)
        self._connect_signals()
        self.load_data()

    # ═══════════════════════════════════════════
    #  UI KURULUMU
    # ═══════════════════════════════════════════

    def _setup_ui(self, kullanici_adi: str):
        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(8)

        # ── Araç Çubuğu ──────────────────────────────────────────────────────
        toolbar = QFrame()
        toolbar.setStyleSheet(S.get("filter_panel", ""))
        fl = QHBoxLayout(toolbar)
        fl.setContentsMargins(12, 8, 12, 8)
        fl.setSpacing(8)

        self._cmb_abd = QComboBox()
        self._cmb_abd.addItem("Tüm Bölümler")
        self._cmb_abd.setStyleSheet(S.get("combo", ""))
        self._cmb_abd.setMinimumWidth(150)
        fl.addWidget(self._cmb_abd)

        self._cmb_birim = QComboBox()
        self._cmb_birim.addItem("Tüm Birimler")
        self._cmb_birim.setStyleSheet(S.get("combo", ""))
        self._cmb_birim.setMinimumWidth(130)
        fl.addWidget(self._cmb_birim)

        self._cmb_cins = QComboBox()
        self._cmb_cins.addItem("Tüm Cinsler")
        self._cmb_cins.setStyleSheet(S.get("combo", ""))
        self._cmb_cins.setMinimumWidth(130)
        fl.addWidget(self._cmb_cins)

        self._cmb_durum = QComboBox()
        self._cmb_durum.setStyleSheet(S.get("combo", ""))
        self._cmb_durum.setMinimumWidth(130)
        for d in ["Tüm Durumlar", "Kullanıma Uygun", "Kullanıma Uygun Değil", "Hurda"]:
            self._cmb_durum.addItem(d)
        fl.addWidget(self._cmb_durum)

        self._txt_ara = QLineEdit()
        self._txt_ara.setPlaceholderText("Ekipman ara…")
        self._txt_ara.setClearButtonEnabled(True)
        self._txt_ara.setStyleSheet(S.get("search", ""))
        self._txt_ara.setMinimumWidth(160)
        fl.addWidget(self._txt_ara)

        fl.addStretch()

        self._btn_toplu = QPushButton("Toplu Muayene")
        self._btn_toplu.setStyleSheet(S.get("action_btn", ""))
        self._btn_toplu.setCursor(QCursor(Qt.PointingHandCursor))
        self._btn_toplu.setToolTip(
            "Listeden birden fazla ekipman seçin (Ctrl/Shift), sonra tıklayın."
        )
        IconRenderer.set_button_icon(
            self._btn_toplu, "clipboard", color=DarkTheme.TEXT_PRIMARY, size=14
        )
        fl.addWidget(self._btn_toplu)

        _sep = QFrame()
        _sep.setFrameShape(QFrame.VLine)
        _sep.setFixedHeight(22)
        _sep.setStyleSheet(S.get("separator", ""))
        fl.addWidget(_sep)

        self._btn_yenile = QPushButton("Yenile")
        self._btn_yenile.setStyleSheet(S.get("refresh_btn", ""))
        self._btn_yenile.setCursor(QCursor(Qt.PointingHandCursor))
        IconRenderer.set_button_icon(
            self._btn_yenile, "sync", color=DarkTheme.TEXT_PRIMARY, size=14
        )
        fl.addWidget(self._btn_yenile)

        _sep2 = QFrame()
        _sep2.setFrameShape(QFrame.VLine)
        _sep2.setFixedHeight(22)
        _sep2.setStyleSheet(S.get("separator", ""))
        fl.addWidget(_sep2)

        self.btn_kapat = QPushButton("Kapat")
        self.btn_kapat.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_kapat.setStyleSheet(S.get("close_btn", ""))
        IconRenderer.set_button_icon(
            self.btn_kapat, "x", color=DarkTheme.TEXT_PRIMARY, size=14
        )
        fl.addWidget(self.btn_kapat)

        root.addWidget(toolbar)

        # ── Ana İçerik ────────────────────────────────────────────────────────
        icerik = QWidget()
        icerik.setStyleSheet("background: transparent;")
        self._icerik_lay = QHBoxLayout(icerik)
        self._icerik_lay.setContentsMargins(0, 0, 0, 0)
        self._icerik_lay.setSpacing(0)

        # Slide panel (başta genişliği 0 = kapalı)
        self._form = RKEMuayeneFormWidget(kullanici_adi=kullanici_adi)
        self._slide = SlidePanel(self._form)
        self._icerik_lay.addWidget(self._slide)

        # İnce ayraç — panel açıkken görünür
        self._ayrac = QFrame()
        self._ayrac.setFrameShape(QFrame.VLine)
        self._ayrac.setStyleSheet(S.get("separator", ""))
        self._ayrac.setVisible(False)
        self._icerik_lay.addWidget(self._ayrac)

        # Sağ: liste
        sag = QWidget()
        sag.setStyleSheet("background: transparent;")
        sag_lay = QVBoxLayout(sag)
        sag_lay.setContentsMargins(8, 0, 0, 0)
        sag_lay.setSpacing(6)

        self._list_model = RKEListTableModel()
        self._list_proxy = QSortFilterProxyModel()
        self._list_proxy.setSourceModel(self._list_model)
        self._list_proxy.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self._list_proxy.setFilterKeyColumn(-1)

        self._list_view = QTableView()
        self._list_view.setModel(self._list_proxy)
        self._list_view.setStyleSheet(S.get("table", ""))
        self._list_view.verticalHeader().setVisible(False)
        self._list_view.setAlternatingRowColors(True)
        self._list_view.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._list_view.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self._list_view.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._list_view.setSortingEnabled(True)

        hdr = self._list_view.horizontalHeader()
        hdr.setSectionResizeMode(QHeaderView.Stretch)
        hdr.setSectionResizeMode(len(RKE_COLUMNS) - 1, QHeaderView.ResizeToContents)
        sag_lay.addWidget(self._list_view, 1)

        # Footer
        footer = QHBoxLayout()
        self._lbl_sayi = QLabel("0 ekipman")
        self._lbl_sayi.setStyleSheet(
            S.get("footer_label", f"color:{DarkTheme.TEXT_MUTED}; font-size:11px;")
        )
        self._lbl_secili = QLabel("")
        self._lbl_secili.setStyleSheet(
            f"color:{DarkTheme.STATUS_SUCCESS}; font-size:11px; font-weight:600;"
        )
        self._pbar = QProgressBar()
        self._pbar.setFixedHeight(4)
        self._pbar.setTextVisible(False)
        self._pbar.setStyleSheet(S.get("progress", ""))
        self._pbar.setVisible(False)
        footer.addWidget(self._lbl_sayi)
        footer.addWidget(self._lbl_secili)
        footer.addStretch()
        footer.addWidget(self._pbar)
        sag_lay.addLayout(footer)

        self._icerik_lay.addWidget(sag, 1)
        root.addWidget(icerik, 1)

    # ═══════════════════════════════════════════
    #  SİNYALLER
    # ═══════════════════════════════════════════

    def _connect_signals(self):
        self._btn_yenile.clicked.connect(self.load_data)
        self._btn_toplu.clicked.connect(self._ac_toplu_dialog)

        self._txt_ara.textChanged.connect(self._list_proxy.setFilterFixedString)
        self._cmb_abd.currentTextChanged.connect(self._apply_filter)
        self._cmb_birim.currentTextChanged.connect(self._apply_filter)
        self._cmb_cins.currentTextChanged.connect(self._apply_filter)
        self._cmb_durum.currentTextChanged.connect(self._apply_filter)

        self._list_view.selectionModel().selectionChanged.connect(self._on_secim_degisti)
        self._list_view.doubleClicked.connect(self._on_cift_tiklama)
        self._form.kaydet_istendi.connect(self._on_kaydet_istendi)
        self._slide.btn_kapat.clicked.connect(self._panel_kapat)

    # ═══════════════════════════════════════════
    #  VERİ YÜKLEME
    # ═══════════════════════════════════════════

    def load_data(self):
        if hasattr(self, "_loader") and self._loader.isRunning():
            return
        self._pbar.setVisible(True)
        self._pbar.setRange(0, 0)
        self._loader = VeriYukleyiciThread()
        self._loader.veri_hazir.connect(self._on_data_ready)
        self._loader.hata_olustu.connect(self._on_error)
        self._loader.finished.connect(lambda: self._pbar.setVisible(False))
        self._loader.start()

    def _on_data_ready(self, rke_data, teknik, kontrol_listesi, sorumlu_listesi, tum_muayene):
        self._rke_data       = rke_data
        self._tum_muayeneler = tum_muayene
        self._teknik_acik    = teknik
        self._kontrol_list   = kontrol_listesi
        self._sorumlu_list   = sorumlu_listesi

        self._form.set_context(rke_data, teknik, kontrol_listesi, sorumlu_listesi, tum_muayene)

        abd_set   = {str(r.get("AnaBilimDali",  "")).strip() for r in rke_data if r.get("AnaBilimDali")}
        birim_set = {str(r.get("Birim",         "")).strip() for r in rke_data if r.get("Birim")}
        cins_set  = {str(r.get("KoruyucuCinsi", "")).strip() for r in rke_data if r.get("KoruyucuCinsi")}

        self._fill_filter(self._cmb_abd,   abd_set,   "Tüm Bölümler")
        self._fill_filter(self._cmb_birim, birim_set, "Tüm Birimler")
        self._fill_filter(self._cmb_cins,  cins_set,  "Tüm Cinsler")

        self._apply_filter()

    @staticmethod
    def _fill_filter(widget: QComboBox, items: set, default: str):
        widget.blockSignals(True)
        curr = widget.currentText()
        widget.clear()
        widget.addItem(default)
        widget.addItems(sorted(items))
        idx = widget.findText(curr)
        widget.setCurrentIndex(idx if idx >= 0 else 0)
        widget.blockSignals(False)

    def _apply_filter(self):
        f_abd   = self._cmb_abd.currentText()
        f_birim = self._cmb_birim.currentText()
        f_cins  = self._cmb_cins.currentText()
        f_durum = self._cmb_durum.currentText()

        filtered = [
            r for r in self._rke_data
            if (f_abd   == "Tüm Bölümler" or str(r.get("AnaBilimDali",  "")).strip() == f_abd)
            and (f_birim == "Tüm Birimler" or str(r.get("Birim",         "")).strip() == f_birim)
            and (f_cins  == "Tüm Cinsler"  or str(r.get("KoruyucuCinsi", "")).strip() == f_cins)
            and (f_durum == "Tüm Durumlar" or str(r.get("Durum",         "")).strip() == f_durum)
        ]

        self._list_model.set_data(filtered)
        self._lbl_sayi.setText(f"{len(filtered)} ekipman")

    # ═══════════════════════════════════════════
    #  SEÇİM → SLIDE PANEL
    # ═══════════════════════════════════════════

    def _on_secim_degisti(self):
        """Seçim değişince sadece toplu muayene butonunu günceller."""
        secili_sayi = len(self._list_view.selectionModel().selectedRows())
        if secili_sayi > 1:
            self._btn_toplu.setText(f"Toplu Muayene  ({secili_sayi} seçili)")
            self._lbl_secili.setText(f"{secili_sayi} ekipman seçili")
        else:
            self._btn_toplu.setText("Toplu Muayene")
            self._lbl_secili.setText("")

    def _on_cift_tiklama(self, index):
        """Çift tıklamada muayene panelini o ekipman için açar."""
        src_idx  = self._list_proxy.mapToSource(index)
        row_data = self._list_model.get_row(src_idx.row())
        if not row_data:
            return
        ekipman_no = str(row_data.get("EkipmanNo", "")).strip()
        self._form.goster_gecmis_ekipman(ekipman_no)
        self._slide.lbl_ekipman.setText(f"Muayene  —  {ekipman_no}")
        if not self._slide.acik_mi():
            self._ayrac.setVisible(True)
            self._slide.ac()

    def _panel_kapat(self):
        """Kapatma butonu: paneli animasyonla kapatır."""
        self._slide.kapat(bitis_cb=self._ayrac_gizle)
        self._slide.lbl_ekipman.setText("Muayene Formu")

    def _ayrac_gizle(self):
        if not self._slide.acik_mi():
            self._ayrac.setVisible(False)
        try:
            self._slide._anim.finished.disconnect(self._ayrac_gizle)
        except RuntimeError:
            pass

    # ═══════════════════════════════════════════
    #  KAYDETME
    # ═══════════════════════════════════════════

    def _on_kaydet_istendi(self, veri: dict, dosya_yolu):
        self._form.set_busy(True)
        self._saver = KayitWorkerThread(veri, dosya_yolu)
        self._saver.kayit_tamam.connect(self._on_save_success)
        self._saver.hata_olustu.connect(self._on_error)
        self._saver.start()

    def _on_save_success(self, msg: str):
        self._form.set_busy(False)
        QMessageBox.information(self, "Başarılı", msg)
        self.load_data()

    # ═══════════════════════════════════════════
    #  TOPLU MUAYENE
    # ═══════════════════════════════════════════

    def _ac_toplu_dialog(self):
        indexes = self._list_view.selectionModel().selectedRows()
        if not indexes:
            QMessageBox.warning(
                self, "Uyarı",
                "Listeden en az bir ekipman seçin.\n"
                "(Ctrl veya Shift ile çoklu seçim yapabilirsiniz.)"
            )
            return

        ekipmanlar = sorted({
            str(self._list_model.get_row(
                self._list_proxy.mapToSource(idx).row()
            ).get("EkipmanNo", "")).strip()
            for idx in indexes
        })

        dlg = TopluMuayeneDialog(
            ekipmanlar,
            self._teknik_acik,
            self._kontrol_list,
            self._sorumlu_list,
            self._form._kullanici_adi,
            self,
        )
        if dlg.exec() == QDialog.Accepted:
            QMessageBox.information(
                self, "Bilgi",
                f"{len(ekipmanlar)} ekipman için kayıt tamamlandı."
            )
            self.load_data()

    # ═══════════════════════════════════════════
    #  HATA
    # ═══════════════════════════════════════════

    def _on_error(self, msg: str):
        self._pbar.setVisible(False)
        self._form.set_busy(False)
        logger.error(f"RKEMuayene hatası: {msg}")
        QMessageBox.critical(self, "Hata", msg)
