# -*- coding: utf-8 -*-
"""
RKE Muayene Girişi – Ana Sayfa
────────────────────────────────
• Sol : RKEMuayeneFormWidget  (tekli muayene formu + geçmiş)
• Sağ : QTableView            (RKEListTableModel + QSortFilterProxyModel)

Bu modül yalnızca koordinasyon ve sinyal bağlantılarından sorumludur.
İş mantığı alt modüllere taşınmıştır:
  rke_muayene_models  → RKEListTableModel, GecmisMuayeneModel
  rke_muayene_workers → VeriYukleyiciThread, KayitWorkerThread, TopluKayitWorkerThread
  rke_muayene_form    → RKEMuayeneFormWidget
  rke_toplu_dialog    → TopluMuayeneDialog
"""
from PySide6.QtCore import Qt, QSortFilterProxyModel
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QProgressBar, QFrame, QComboBox, QLineEdit,
    QMessageBox, QTableView, QHeaderView,
    QAbstractItemView, QDialog,
)
from PySide6.QtGui import QCursor

from core.logger import logger
from ui.theme_manager import ThemeManager
from ui.styles import DarkTheme
from ui.styles.icons import IconRenderer

from .rke_muayene_models import RKEListTableModel, RKE_COLUMNS
from .rke_muayene_workers import VeriYukleyiciThread, KayitWorkerThread
from .rke_muayene_form import RKEMuayeneFormWidget
from .rke_toplu_dialog import TopluMuayeneDialog

S = ThemeManager.get_all_component_styles()


class RKEMuayenePage(QWidget):
    """
    RKE Muayene Girişi sayfası.
    kullanici_adi: oturum açmış kullanıcı (Kontrol Eden alanına otomatik yazılır)
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
        root = QHBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(10)

        # ── SOL: FORM ──
        self._form = RKEMuayeneFormWidget(kullanici_adi=kullanici_adi)
        root.addWidget(self._form, 35)

        # Dikey ayraç
        sep = QFrame()
        sep.setFrameShape(QFrame.VLine)
        sep.setStyleSheet(S.get("separator", ""))
        root.addWidget(sep)

        # ── SAĞ: LİSTE ──
        sag_widget = QWidget()
        sag_lay = QVBoxLayout(sag_widget)
        sag_lay.setContentsMargins(0, 0, 0, 0)
        sag_lay.setSpacing(8)

        # Filtre paneli
        filter_frame = QFrame()
        filter_frame.setStyleSheet(S.get("filter_panel", ""))
        fl = QHBoxLayout(filter_frame)
        fl.setContentsMargins(12, 8, 12, 8)
        fl.setSpacing(8)

        self._cmb_filtre_abd = QComboBox()
        self._cmb_filtre_abd.addItem("Tüm Bölümler")
        self._cmb_filtre_abd.setStyleSheet(S.get("combo", ""))
        fl.addWidget(self._cmb_filtre_abd)

        self._txt_ara = QLineEdit()
        self._txt_ara.setPlaceholderText("Ekipman ara...")
        self._txt_ara.setClearButtonEnabled(True)
        self._txt_ara.setStyleSheet(S.get("search", ""))
        fl.addWidget(self._txt_ara)

        fl.addStretch()

        self._btn_yenile = QPushButton("Yenile")
        self._btn_yenile.setToolTip("Yenile")
        self._btn_yenile.setStyleSheet(S.get("refresh_btn", ""))
        self._btn_yenile.setCursor(QCursor(Qt.PointingHandCursor))
        IconRenderer.set_button_icon(self._btn_yenile, "sync", color=DarkTheme.TEXT_PRIMARY, size=14)
        fl.addWidget(self._btn_yenile)

        _sep_k = QFrame()
        _sep_k.setFrameShape(QFrame.VLine)
        _sep_k.setFixedHeight(20)
        _sep_k.setStyleSheet(S.get("separator", ""))
        fl.addWidget(_sep_k)

        self.btn_kapat = QPushButton("Kapat")
        self.btn_kapat.setToolTip("Pencereyi Kapat")
        self.btn_kapat.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_kapat.setStyleSheet(S.get("close_btn", ""))
        IconRenderer.set_button_icon(self.btn_kapat, "x", color=DarkTheme.TEXT_PRIMARY, size=14)
        fl.addWidget(self.btn_kapat)

        sag_lay.addWidget(filter_frame)

        # Tablo
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

        # Toplu İşlem Butonu
        self._btn_toplu = QPushButton("Seçili Ekipmanlara Toplu Muayene Ekle")
        self._btn_toplu.setStyleSheet(S.get("action_btn", ""))
        self._btn_toplu.setCursor(QCursor(Qt.PointingHandCursor))
        IconRenderer.set_button_icon(self._btn_toplu, "clipboard", color=DarkTheme.TEXT_PRIMARY, size=14)
        sag_lay.addWidget(self._btn_toplu)

        # Footer
        footer = QHBoxLayout()
        self._lbl_sayi = QLabel("0 kayıt")
        self._lbl_sayi.setStyleSheet(
            S.get("footer_label", f"color:{DarkTheme.TEXT_MUTED}; font-size:11px;")
        )
        self._pbar = QProgressBar()
        self._pbar.setFixedHeight(4)
        self._pbar.setTextVisible(False)
        self._pbar.setStyleSheet(S.get("progress", ""))
        self._pbar.setVisible(False)
        footer.addWidget(self._lbl_sayi)
        footer.addStretch()
        footer.addWidget(self._pbar)
        sag_lay.addLayout(footer)

        root.addWidget(sag_widget, 65)

    # ═══════════════════════════════════════════
    #  SİNYALLER
    # ═══════════════════════════════════════════

    def _connect_signals(self):
        self._btn_yenile.clicked.connect(self.load_data)
        self._btn_toplu.clicked.connect(self._ac_toplu_dialog)
        self._txt_ara.textChanged.connect(self._list_proxy.setFilterFixedString)
        self._cmb_filtre_abd.currentTextChanged.connect(self._apply_filter)
        self._list_view.selectionModel().selectionChanged.connect(self._on_list_selection)

        # Form sinyalleri
        self._form.kaydet_istendi.connect(self._on_kaydet_istendi)

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

        # ABD filtre combo
        abd_set = {str(r.get("AnaBilimDali", "")).strip() for r in rke_data if r.get("AnaBilimDali")}
        self._cmb_filtre_abd.blockSignals(True)
        self._cmb_filtre_abd.clear()
        self._cmb_filtre_abd.addItem("Tüm Bölümler")
        self._cmb_filtre_abd.addItems(sorted(abd_set))
        self._cmb_filtre_abd.blockSignals(False)

        self._apply_filter()

    def _apply_filter(self):
        f_abd = self._cmb_filtre_abd.currentText()
        filtered = [
            r for r in self._rke_data
            if f_abd == "Tüm Bölümler" or str(r.get("AnaBilimDali", "")).strip() == f_abd
        ]
        self._list_model.set_data(filtered)
        self._lbl_sayi.setText(f"{len(filtered)} Ekipman")

    # ═══════════════════════════════════════════
    #  TABLO SEÇİMİ
    # ═══════════════════════════════════════════

    def _on_list_selection(self):
        indexes = self._list_view.selectionModel().selectedRows()
        if len(indexes) != 1:
            return
        src_idx  = self._list_proxy.mapToSource(indexes[0])
        row_data = self._list_model.get_row(src_idx.row())
        if not row_data:
            return
        ekipman_no = str(row_data.get("EkipmanNo", "")).strip()
        self._form.goster_gecmis_ekipman(ekipman_no)

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
            QMessageBox.warning(self, "Uyarı", "Listeden en az bir ekipman seçin (Ctrl/Shift ile çoklu seçim).")
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
            QMessageBox.information(self, "Bilgi", "Toplu kayıt tamamlandı.")
            self.load_data()

    # ═══════════════════════════════════════════
    #  HATA
    # ═══════════════════════════════════════════

    def _on_error(self, msg: str):
        self._pbar.setVisible(False)
        self._form.set_busy(False)
        logger.error(f"RKEMuayene hatası: {msg}")
        QMessageBox.critical(self, "Hata", msg)
