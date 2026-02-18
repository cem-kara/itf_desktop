# -*- coding: utf-8 -*-
"""
RKE Envanter Yönetimi – Ana Sayfa (Yeniden Tasarım)
─────────────────────────────────────────────────────
Kullanım frekansı düşük olduğundan sayfa %100 tablo modunda çalışır.
Ekipman ekleme / düzenleme işlemleri RKEFormDialog üzerinden yapılır.

Alt modüller değişmedi:
  rke/yonetim/rke_table_models  → RKETableModel, GecmisTableModel
  rke/yonetim/rke_workers       → VeriYukleyiciThread, IslemKaydediciThread
  rke/yonetim/rke_form_widget   → RKEFormWidget
"""
from PySide6.QtCore import Qt, QSortFilterProxyModel
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QProgressBar, QFrame, QComboBox, QLineEdit, QDialog,
    QMessageBox, QTableView, QHeaderView, QAbstractItemView, QMenu,
    QDialogButtonBox,
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


# ═══════════════════════════════════════════════════════════
#  FORM DİALOG  –  RKEFormWidget'ı modal pencerede sarmalar
# ═══════════════════════════════════════════════════════════

class RKEFormDialog(QDialog):
    """
    RKEFormWidget'ı modal QDialog içinde sunar.
    Mevcut widget API'si (fill_combos, load_row, open_new,
    set_busy, kaydet_istendi) hiç değişmeden kullanılır.
    """

    def __init__(self, sabitler: dict, rke_listesi: list, kisaltma: dict,
                 row_data: dict = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Ekipman Düzenle" if row_data else "Yeni Ekipman Ekle")
        self.setMinimumSize(640, 600)
        self.setStyleSheet(S.get("dialog", f"background:{DarkTheme.BG_PRIMARY};"))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 12)
        layout.setSpacing(12)

        # Başlık
        lbl = QLabel("Ekipman Düzenle" if row_data else "Yeni Ekipman Ekle")
        lbl.setStyleSheet(
            f"font-size:15px; font-weight:600; color:{DarkTheme.TEXT_PRIMARY};"
            "background:transparent; padding-bottom:4px;"
        )
        layout.addWidget(lbl)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet(S.get("separator", ""))
        layout.addWidget(sep)

        # Form widget — doğrudan embed
        self.form = RKEFormWidget(self)
        self.form.fill_combos(sabitler)
        self.form.set_context(rke_listesi, kisaltma)

        # Buton satırını dialog'dan yönetmek için form butonlarını gizle
        self.form.btn_kaydet.setVisible(False)
        self.form.btn_temizle.setVisible(False)
        self.form._btn_vazgec.setVisible(False)

        if row_data:
            self.form.load_row(row_data)
        else:
            self.form.open_new()

        layout.addWidget(self.form, 1)

        # Progress bar
        self._pbar = QProgressBar()
        self._pbar.setFixedHeight(4)
        self._pbar.setTextVisible(False)
        self._pbar.setStyleSheet(S.get("progress", ""))
        self._pbar.setVisible(False)
        layout.addWidget(self._pbar)

        # Dialog butonları
        btn_box = QDialogButtonBox()
        btn_box.setStyleSheet("background: transparent;")

        self._btn_kaydet = QPushButton("Güncelle" if row_data else "Kaydet")
        self._btn_kaydet.setStyleSheet(S.get("save_btn", ""))
        self._btn_kaydet.setCursor(QCursor(Qt.PointingHandCursor))
        IconRenderer.set_button_icon(self._btn_kaydet, "save", color=DarkTheme.TEXT_PRIMARY, size=14)

        btn_iptal = QPushButton("İptal")
        btn_iptal.setStyleSheet(S.get("cancel_btn", ""))
        btn_iptal.setCursor(QCursor(Qt.PointingHandCursor))
        IconRenderer.set_button_icon(btn_iptal, "x", color=DarkTheme.TEXT_PRIMARY, size=14)

        btn_box.addButton(btn_iptal,       QDialogButtonBox.RejectRole)
        btn_box.addButton(self._btn_kaydet, QDialogButtonBox.AcceptRole)
        btn_box.rejected.connect(self.reject)
        btn_box.accepted.connect(self._on_kaydet_tiklandi)
        layout.addWidget(btn_box)

        # Form'un kaydet sinyalini yakala
        self.form.kaydet_istendi.connect(self._on_form_kaydet)
        self.form.kapat_istendi.connect(self.reject)

        self._worker = None

    # ── Kaydetme akışı ───────────────────────────────────────────────────────

    def _on_kaydet_tiklandi(self):
        """Dialog butonuna basılınca form'un kendi kaydet metodunu tetikler."""
        self.form._on_save()

    def _on_form_kaydet(self, mod: str, veri: dict):
        """Form'un kaydet_istendi sinyalini alır, worker'ı başlatır."""
        self._set_busy(True)
        self._worker = IslemKaydediciThread(mod, veri)
        self._worker.islem_tamam.connect(self._on_basarili)
        self._worker.hata_olustu.connect(self._on_hata)
        self._worker.start()

    def _on_basarili(self):
        self._set_busy(False)
        self.accept()

    def _on_hata(self, msg: str):
        self._set_busy(False)
        QMessageBox.critical(self, "Hata", msg)

    def _set_busy(self, busy: bool):
        self._pbar.setVisible(busy)
        self._pbar.setRange(0, 0 if busy else 1)
        self._btn_kaydet.setEnabled(not busy)
        self.form.set_busy(busy)


# ═══════════════════════════════════════════════════════════
#  ANA SAYFA
# ═══════════════════════════════════════════════════════════

class RKEYonetimPage(QWidget):
    """
    RKE Envanter Yönetimi sayfası.
    Sayfa her zaman %100 tablo modunda çalışır.
    Ekleme / düzenleme RKEFormDialog ile yapılır.
    """

    def __init__(self, db=None, parent=None):
        super().__init__(parent)
        self.setStyleSheet(S.get("page", "background-color: transparent;"))
        self._db          = db
        self._rke_listesi = []
        self._sabitler    = {}
        self._kisaltma    = {}

        self._setup_ui()
        self._connect_signals()
        self.load_data()

    # ═══════════════════════════════════════════
    #  UI KURULUMU
    # ═══════════════════════════════════════════

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(8)

        # ── Filtre / Araç Çubuğu ──
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
        for d in ["Tüm Durumlar", "Kullanıma Uygun", "Kullanıma Uygun Değil", "Hurda", "Tamirde", "Kayıp"]:
            self._cmb_durum.addItem(d)
        fl.addWidget(self._cmb_durum)

        self._txt_ara = QLineEdit()
        self._txt_ara.setPlaceholderText("Ekipman ara…")
        self._txt_ara.setClearButtonEnabled(True)
        self._txt_ara.setStyleSheet(S.get("search", ""))
        self._txt_ara.setMinimumWidth(180)
        fl.addWidget(self._txt_ara)

        fl.addStretch()

        self._btn_yenile = QPushButton("Yenile")
        self._btn_yenile.setToolTip("Listeyi Yenile")
        self._btn_yenile.setStyleSheet(S.get("refresh_btn", ""))
        self._btn_yenile.setCursor(QCursor(Qt.PointingHandCursor))
        IconRenderer.set_button_icon(self._btn_yenile, "sync", color=DarkTheme.TEXT_PRIMARY, size=14)
        fl.addWidget(self._btn_yenile)

        # Ayraç
        _sep = QFrame()
        _sep.setFrameShape(QFrame.VLine)
        _sep.setFixedHeight(22)
        _sep.setStyleSheet(S.get("separator", ""))
        fl.addWidget(_sep)

        self._btn_yeni = QPushButton("Yeni Ekipman")
        self._btn_yeni.setStyleSheet(S.get("save_btn", ""))
        self._btn_yeni.setCursor(QCursor(Qt.PointingHandCursor))
        IconRenderer.set_button_icon(self._btn_yeni, "plus", color=DarkTheme.TEXT_PRIMARY, size=14)
        fl.addWidget(self._btn_yeni)

        # Ayraç
        _sep2 = QFrame()
        _sep2.setFrameShape(QFrame.VLine)
        _sep2.setFixedHeight(22)
        _sep2.setStyleSheet(S.get("separator", ""))
        fl.addWidget(_sep2)

        self.btn_kapat = QPushButton("Kapat")
        self.btn_kapat.setToolTip("Pencereyi Kapat")
        self.btn_kapat.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_kapat.setStyleSheet(S.get("close_btn", ""))
        IconRenderer.set_button_icon(self.btn_kapat, "x", color=DarkTheme.TEXT_PRIMARY, size=14)
        fl.addWidget(self.btn_kapat)

        root.addWidget(toolbar)

        # ── Tablo ──
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
        self._table.doubleClicked.connect(self._on_double_click)
        self._table.verticalHeader().setDefaultSectionSize(26)

        hdr = self._table.horizontalHeader()
        hdr.setSectionResizeMode(QHeaderView.Stretch)
        hdr.setSectionResizeMode(len(COLUMNS) - 1, QHeaderView.ResizeToContents)

        root.addWidget(self._table, 1)

        # ── Footer ──
        footer = QHBoxLayout()

        self._lbl_sayi = QLabel("0 kayıt")
        self._lbl_sayi.setStyleSheet(
            S.get("footer_label", f"color:{DarkTheme.TEXT_MUTED}; font-size:11px;")
        )
        footer.addWidget(self._lbl_sayi)
        footer.addStretch()

        lbl_ipucu = QLabel("Düzenlemek için çift tıklayın veya sağ tık yapın")
        lbl_ipucu.setStyleSheet(f"color:{DarkTheme.TEXT_MUTED}; font-size:10px; font-style:italic;")
        footer.addWidget(lbl_ipucu)

        self._pbar = QProgressBar()
        self._pbar.setFixedHeight(4)
        self._pbar.setTextVisible(False)
        self._pbar.setStyleSheet(S.get("progress", ""))
        self._pbar.setVisible(False)
        footer.addWidget(self._pbar)

        root.addLayout(footer)

    # ═══════════════════════════════════════════
    #  SİNYALLER
    # ═══════════════════════════════════════════

    def _connect_signals(self):
        self._btn_yenile.clicked.connect(self.load_data)
        self._btn_yeni.clicked.connect(self._ac_yeni_dialog)

        self._txt_ara.textChanged.connect(self._proxy.setFilterFixedString)
        self._cmb_abd.currentTextChanged.connect(self._apply_filter)
        self._cmb_birim.currentTextChanged.connect(self._apply_filter)
        self._cmb_cins.currentTextChanged.connect(self._apply_filter)
        self._cmb_durum.currentTextChanged.connect(self._apply_filter)

        self._table.customContextMenuRequested.connect(self._show_context_menu)

    # ═══════════════════════════════════════════
    #  DİALOG AÇMA
    # ═══════════════════════════════════════════

    def _ac_yeni_dialog(self):
        dlg = RKEFormDialog(
            self._sabitler, self._rke_listesi, self._kisaltma,
            row_data=None, parent=self
        )
        if dlg.exec() == QDialog.Accepted:
            QMessageBox.information(self, "Başarılı", "Ekipman eklendi.")
            self.load_data()

    def _ac_duzenle_dialog(self, row_data: dict):
        dlg = RKEFormDialog(
            self._sabitler, self._rke_listesi, self._kisaltma,
            row_data=row_data, parent=self
        )
        if dlg.exec() == QDialog.Accepted:
            QMessageBox.information(self, "Başarılı", "Ekipman güncellendi.")
            self.load_data()

    def _on_double_click(self, index):
        src_idx  = self._proxy.mapToSource(index)
        row_data = self._model.get_row(src_idx.row())
        if row_data:
            self._ac_duzenle_dialog(row_data)

    def _show_context_menu(self, pos):
        idx = self._table.indexAt(pos)
        if not idx.isValid():
            return
        src_idx  = self._proxy.mapToSource(idx)
        row_data = self._model.get_row(src_idx.row())
        if not row_data:
            return
        menu = QMenu(self)
        menu.setStyleSheet(S.get("context_menu", ""))
        act_duzenle = menu.addAction("✏  Düzenle")
        act_duzenle.triggered.connect(lambda: self._ac_duzenle_dialog(row_data))
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

        abd_set   = {str(r.get("AnaBilimDali",  "")).strip() for r in rke_data if r.get("AnaBilimDali")}
        birim_set = {str(r.get("Birim",         "")).strip() for r in rke_data if r.get("Birim")}
        cins_set  = {str(r.get("KoruyucuCinsi", "")).strip() for r in rke_data if r.get("KoruyucuCinsi")}

        self._fill_filter(self._cmb_abd,   abd_set,   "Tüm Bölümler")
        self._fill_filter(self._cmb_birim, birim_set, "Tüm Birimler")
        self._fill_filter(self._cmb_cins,  cins_set,  "Tüm Cinsler")

        self._apply_filter()

    @staticmethod
    def _fill_filter(widget: QComboBox, items: set, default_text: str):
        widget.blockSignals(True)
        curr = widget.currentText()
        widget.clear()
        widget.addItem(default_text)
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
            r for r in self._rke_listesi
            if (f_abd   == "Tüm Bölümler" or str(r.get("AnaBilimDali",  "")).strip() == f_abd)
            and (f_birim == "Tüm Birimler" or str(r.get("Birim",         "")).strip() == f_birim)
            and (f_cins  == "Tüm Cinsler"  or str(r.get("KoruyucuCinsi", "")).strip() == f_cins)
            and (f_durum == "Tüm Durumlar" or str(r.get("Durum",         "")).strip() == f_durum)
        ]

        self._model.set_data(filtered)
        self._lbl_sayi.setText(f"{len(filtered)} kayıt")

    # ═══════════════════════════════════════════
    #  HATA
    # ═══════════════════════════════════════════

    def _on_error(self, msg: str):
        self._pbar.setVisible(False)
        logger.error(f"RKEYonetim hatası: {msg}")
        QMessageBox.critical(self, "Hata", msg)
