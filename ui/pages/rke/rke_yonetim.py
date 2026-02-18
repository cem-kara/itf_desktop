# -*- coding: utf-8 -*-
"""
RKE Envanter Yönetimi – Ana Sayfa
──────────────────────────────────
• Sol : RKEFormWidget   (ekle / güncelle formu + muayene geçmişi)
• Sağ : QTableView      (RKETableModel + QSortFilterProxyModel)

Bu modül yalnızca koordinasyon ve sinyal bağlantılarından sorumludur;
iş mantığı alt modüllere taşınmıştır:
  rke/yonetim/rke_table_models  → RKETableModel, GecmisTableModel
  rke/yonetim/rke_workers       → VeriYukleyiciThread, IslemKaydediciThread, GecmisYukleyiciThread
  rke/yonetim/rke_form_widget   → RKEFormWidget
"""
from PySide6.QtCore import Qt, QSortFilterProxyModel
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QProgressBar, QFrame, QComboBox, QLineEdit,
    QMessageBox, QTableView, QHeaderView,
    QAbstractItemView, QMenu,
)
from PySide6.QtGui import QCursor

from core.logger import logger
from ui.theme_manager import ThemeManager
from ui.styles import DarkTheme
from ui.styles.icons import IconRenderer

from ui.pages.rke.yonetim.rke_table_models import RKETableModel, COLUMNS
from ui.pages.rke.yonetim.rke_workers import VeriYukleyiciThread, IslemKaydediciThread
from ui.pages.rke.yonetim.rke_form_widget import RKEFormWidget

S = ThemeManager.get_all_component_styles()


class RKEYonetimPage(QWidget):
    """
    RKE Envanter Yönetimi sayfası.
    db parametresi ileride doğrudan enjeksiyon için tutulmaktadır;
    thread'ler kendi bağlantılarını yönetir.
    """

    def __init__(self, db=None, parent=None):
        super().__init__(parent)
        self.setStyleSheet(S.get("page", "background-color: transparent;"))
        self._db          = db
        self._rke_listesi = []
        self._sabitler    = {}

        self._setup_ui()
        self._connect_signals()
        self.load_data()

    # ═══════════════════════════════════════════
    #  UI KURULUMU
    # ═══════════════════════════════════════════

    def _setup_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(10)

        # ── SOL: FORM ──
        self._form = RKEFormWidget()
        self._form.setVisible(False)
        root.addWidget(self._form, 30)

        # Dikey ayraç
        self._panel_sep = QFrame()
        self._panel_sep.setFrameShape(QFrame.VLine)
        self._panel_sep.setStyleSheet(S.get("separator", ""))
        self._panel_sep.setVisible(False)
        root.addWidget(self._panel_sep)

        # ── SAĞ: LİSTE ──
        list_container = QWidget()
        list_lay = QVBoxLayout(list_container)
        list_lay.setContentsMargins(0, 0, 0, 0)
        list_lay.setSpacing(8)

        # Filtre Paneli
        filter_frame = QFrame()
        filter_frame.setStyleSheet(S.get("filter_panel", ""))
        fl = QHBoxLayout(filter_frame)
        fl.setContentsMargins(12, 8, 12, 8)
        fl.setSpacing(8)

        self._cmb_filter_abd = QComboBox()
        self._cmb_filter_abd.addItem("Tüm Bölümler")
        self._cmb_filter_abd.setStyleSheet(S.get("combo", ""))
        fl.addWidget(self._cmb_filter_abd)

        self._cmb_filter_birim = QComboBox()
        self._cmb_filter_birim.addItem("Tüm Birimler")
        self._cmb_filter_birim.setStyleSheet(S.get("combo", ""))
        fl.addWidget(self._cmb_filter_birim)

        self._cmb_filter_cins = QComboBox()
        self._cmb_filter_cins.addItem("Tüm Cinsler")
        self._cmb_filter_cins.setStyleSheet(S.get("combo", ""))
        fl.addWidget(self._cmb_filter_cins)

        self._txt_ara = QLineEdit()
        self._txt_ara.setPlaceholderText("Ara...")
        self._txt_ara.setClearButtonEnabled(True)
        self._txt_ara.setStyleSheet(S.get("search", ""))
        self._txt_ara.setFixedWidth(180)
        fl.addWidget(self._txt_ara)

        fl.addStretch()

        self._btn_yenile = QPushButton("Yenile")
        self._btn_yenile.setToolTip("Listeyi Yenile")
        self._btn_yenile.setStyleSheet(S.get("refresh_btn", ""))
        self._btn_yenile.setCursor(QCursor(Qt.PointingHandCursor))
        IconRenderer.set_button_icon(self._btn_yenile, "sync", color=DarkTheme.TEXT_PRIMARY, size=14)
        fl.addWidget(self._btn_yenile)

        self._btn_yeni = QPushButton("Yeni")
        self._btn_yeni.setToolTip("Yeni kayıt aç")
        self._btn_yeni.setStyleSheet(S.get("action_btn", S.get("save_btn", "")))
        self._btn_yeni.setCursor(QCursor(Qt.PointingHandCursor))
        IconRenderer.set_button_icon(self._btn_yeni, "plus", color=DarkTheme.TEXT_PRIMARY, size=14)
        fl.addWidget(self._btn_yeni)

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

        list_lay.addWidget(filter_frame)

        # Tablo
        self._model = RKETableModel()
        self._proxy = QSortFilterProxyModel()
        self._proxy.setSourceModel(self._model)
        self._proxy.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self._proxy.setFilterKeyColumn(-1)

        self._table = QTableView()
        self._table.setModel(self._proxy)
        self._table.setStyleSheet(S.get("table", ""))
        self._table.verticalHeader().setVisible(False)
        self._table.setAlternatingRowColors(True)
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SingleSelection)
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._table.setSortingEnabled(True)
        self._table.setContextMenuPolicy(Qt.CustomContextMenu)

        hdr = self._table.horizontalHeader()
        hdr.setSectionResizeMode(QHeaderView.Stretch)
        self._table.setColumnHidden(0, True)                                          # KayitNo gizle
        hdr.setSectionResizeMode(len(COLUMNS) - 1, QHeaderView.ResizeToContents)     # Durum

        list_lay.addWidget(self._table, 1)

        # Footer
        footer = QHBoxLayout()
        self._lbl_sayi = QLabel("0 kayıt")
        self._lbl_sayi.setStyleSheet(
            S.get("footer_label", f"color:{DarkTheme.TEXT_MUTED}; font-size:11px;")
        )
        footer.addWidget(self._lbl_sayi)
        footer.addStretch()

        self._pbar = QProgressBar()
        self._pbar.setFixedHeight(4)
        self._pbar.setTextVisible(False)
        self._pbar.setStyleSheet(S.get("progress", ""))
        self._pbar.setVisible(False)
        footer.addWidget(self._pbar)

        list_lay.addLayout(footer)
        root.addWidget(list_container, 70)

    # ═══════════════════════════════════════════
    #  SİNYALLER
    # ═══════════════════════════════════════════

    def _connect_signals(self):
        # Toolbar
        self._btn_yenile.clicked.connect(self.load_data)
        self._btn_yeni.clicked.connect(self._on_new_clicked)

        # Filtreler
        self._txt_ara.textChanged.connect(self._proxy.setFilterFixedString)
        self._cmb_filter_abd.currentTextChanged.connect(self._apply_filter)
        self._cmb_filter_birim.currentTextChanged.connect(self._apply_filter)
        self._cmb_filter_cins.currentTextChanged.connect(self._apply_filter)

        # Tablo
        self._table.customContextMenuRequested.connect(self._show_context_menu)

        # Form sinyalleri
        self._form.kaydet_istendi.connect(self._on_kaydet_istendi)
        self._form.temizle_istendi.connect(lambda: None)   # ek işlem gerekmez
        self._form.kapat_istendi.connect(self._on_form_close)

    # ═══════════════════════════════════════════
    #  FORM AÇMA / KAPAMA
    # ═══════════════════════════════════════════

    def _on_new_clicked(self):
        self._form.set_context(self._rke_listesi, {})   # kisaltma ana sayfada tutulmaz
        self._form.open_new()
        self._panel_sep.setVisible(True)

    def _on_form_close(self):
        self._form.setVisible(False)
        self._panel_sep.setVisible(False)

    def _on_row_selected(self, index):
        src_idx  = self._proxy.mapToSource(index)
        row_data = self._model.get_row(src_idx.row())
        if not row_data:
            return
        self._form.set_context(self._rke_listesi, self._kisaltma)
        self._form.load_row(row_data)
        self._panel_sep.setVisible(True)

    def _show_context_menu(self, pos):
        idx = self._table.indexAt(pos)
        if not idx.isValid():
            return
        menu = QMenu(self)
        menu.setStyleSheet(S.get("context_menu", ""))
        act_sec = menu.addAction("Düzenle")
        act_sec.triggered.connect(lambda: self._on_row_selected(idx))
        menu.exec(self._table.viewport().mapToGlobal(pos))

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

    def _on_data_ready(self, sabitler, maps, rke_data, muayene_data):
        self._sabitler    = sabitler
        self._kisaltma    = maps
        self._rke_listesi = rke_data

        # Form combolarını güncelle
        self._form.fill_combos(sabitler)
        self._form.set_context(rke_data, maps)

        # Filtre combolarını doldur
        abd_set   = {str(r.get("AnaBilimDali",  "")).strip() for r in rke_data if r.get("AnaBilimDali")}
        birim_set = {str(r.get("Birim",         "")).strip() for r in rke_data if r.get("Birim")}
        cins_set  = {str(r.get("KoruyucuCinsi", "")).strip() for r in rke_data if r.get("KoruyucuCinsi")}

        self._fill_filter(self._cmb_filter_abd,   abd_set,   "Tüm Bölümler")
        self._fill_filter(self._cmb_filter_birim, birim_set, "Tüm Birimler")
        self._fill_filter(self._cmb_filter_cins,  cins_set,  "Tüm Cinsler")

        self._apply_filter()

    @staticmethod
    def _fill_filter(widget: QComboBox, items: set, default_text: str):
        widget.blockSignals(True)
        curr = widget.currentText()
        widget.clear()
        widget.addItem(default_text)
        widget.addItems(sorted(items))
        idx = widget.findText(curr)
        if idx >= 0:
            widget.setCurrentIndex(idx)
        widget.blockSignals(False)

    def _apply_filter(self):
        f_abd   = self._cmb_filter_abd.currentText()
        f_birim = self._cmb_filter_birim.currentText()
        f_cins  = self._cmb_filter_cins.currentText()

        filtered = [
            r for r in self._rke_listesi
            if (f_abd   == "Tüm Bölümler" or str(r.get("AnaBilimDali",  "")).strip() == f_abd)
            and (f_birim == "Tüm Birimler" or str(r.get("Birim",         "")).strip() == f_birim)
            and (f_cins  == "Tüm Cinsler"  or str(r.get("KoruyucuCinsi", "")).strip() == f_cins)
        ]

        self._model.set_data(filtered)
        self._lbl_sayi.setText(f"{len(filtered)} kayıt")

    # ═══════════════════════════════════════════
    #  KAYDETME
    # ═══════════════════════════════════════════

    def _on_kaydet_istendi(self, mod: str, veri: dict):
        self._form.set_busy(True)
        self._saver = IslemKaydediciThread(mod, veri)
        self._saver.islem_tamam.connect(self._on_save_success)
        self._saver.hata_olustu.connect(self._on_error)
        self._saver.start()

    def _on_save_success(self):
        self._form.set_busy(False)
        QMessageBox.information(self, "Başarılı", "İşlem tamamlandı.")
        self._on_form_close()
        self.load_data()

    def _on_error(self, msg: str):
        self._pbar.setVisible(False)
        self._form.set_busy(False)
        logger.error(f"RKEYonetim hatası: {msg}")
        QMessageBox.critical(self, "Hata", msg)
