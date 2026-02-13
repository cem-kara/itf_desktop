# -*- coding: utf-8 -*-
"""
Arıza Listesi Sayfası
─────────────────────
• QAbstractTableModel + QSortFilterProxyModel  (personel_listesi.py deseni)
• Filtre: metin arama + durum + öncelik combobox
• Alt panel: seçili arızanın detayları (QTextBrowser)
• Çift tıklama → ariza_secildi(dict) sinyali
"""
from PySide6.QtCore import (
    Qt, QSortFilterProxyModel, QModelIndex, QAbstractTableModel, Signal
)
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QProgressBar, QHeaderView, QTableView,
    QComboBox, QLineEdit, QGroupBox, QSplitter, QTextBrowser,
    QAbstractItemView, QMenu
)
from PySide6.QtGui import QColor, QCursor, QAction

from core.logger import logger
from ui.theme_manager import ThemeManager
from ui.pages.cihaz.ariza_islem import ArizaIslemPenceresi


# ─── Tablo sütun tanımları  (DB_KOLON, Başlık, min-genişlik) ───
COLUMNS = [
    ("Arizaid",         "Arıza ID",    130),
    ("Cihazid",         "Cihaz ID",    110),
    ("BaslangicTarihi", "Tarih",        90),
    ("Bildiren",        "Bildiren",    130),
    ("Baslik",          "Konu",        200),
    ("Oncelik",         "Öncelik",      90),
    ("Durum",           "Durum",        90),
]

ONCELIK_RENK = {
    "Düşük":         QColor("#6b7280"),
    "Normal":        QColor("#60a5fa"),
    "Yüksek":        QColor("#fb923c"),
    "Acil (Kritik)": QColor("#f87171"),
}
DURUM_RENK = {
    "Açık":           QColor("#f87171"),
    "İşlemde":        QColor("#fb923c"),
    "Parça Bekliyor": QColor("#facc15"),
    "Dış Serviste":   QColor("#a78bfa"),
    "Kapalı (Çözüldü)": QColor("#4ade80"),
    "Kapalı (İptal)":   QColor("#9ca3af"),
}

S = ThemeManager.get_all_component_styles()


# ═══════════════════════════════════════════════
#  TABLO MODELİ
# ═══════════════════════════════════════════════

class ArizaTableModel(QAbstractTableModel):

    def __init__(self, data=None, parent=None):
        super().__init__(parent)
        self._data    = data or []
        self._keys    = [c[0] for c in COLUMNS]
        self._headers = [c[1] for c in COLUMNS]

    def rowCount(self, parent=QModelIndex()):
        return len(self._data)

    def columnCount(self, parent=QModelIndex()):
        return len(COLUMNS)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        row     = self._data[index.row()]
        col_key = self._keys[index.column()]

        if role == Qt.DisplayRole:
            return str(row.get(col_key, ""))

        if role == Qt.ForegroundRole:
            val = str(row.get(col_key, ""))
            if col_key == "Durum":
                return DURUM_RENK.get(val, QColor("#8b8fa3"))
            if col_key == "Oncelik":
                return ONCELIK_RENK.get(val, QColor("#8b8fa3"))
            return None

        if role == Qt.TextAlignmentRole:
            if col_key in ("BaslangicTarihi", "Oncelik", "Durum"):
                return Qt.AlignCenter
            return Qt.AlignVCenter | Qt.AlignLeft

        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self._headers[section]
        return None

    def get_row(self, row_idx):
        if 0 <= row_idx < len(self._data):
            return self._data[row_idx]
        return None

    def set_data(self, data):
        self.beginResetModel()
        self._data = data or []
        self.endResetModel()


# ═══════════════════════════════════════════════
#  ANA SAYFA
# ═══════════════════════════════════════════════

class ArizaListesiPage(QWidget):
    """Arıza listesi. Çift tıklama → ariza_secildi(dict) sinyali."""
    ariza_secildi = Signal(dict)

    def __init__(self, db=None, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background-color: transparent;")
        self._db       = db
        self._all_data = []
        self._setup_ui()
        self._connect_signals()

    # ─── UI ───────────────────────────────────────────────────

    def _setup_ui(self):
        # Root Layout (Yatay: Liste | İşlem Paneli)
        self.root_layout = QHBoxLayout(self)
        self.root_layout.setContentsMargins(0, 0, 0, 0)
        self.root_layout.setSpacing(0)

        # Sol Konteyner (Liste ve Detay)
        self.left_container = QWidget()
        main = QVBoxLayout(self.left_container)
        main.setContentsMargins(20, 12, 20, 12)
        main.setSpacing(10)

        # ── Filtre Paneli ──
        filter_frame = QFrame()
        filter_frame.setStyleSheet(S["filter_panel"])
        fl = QHBoxLayout(filter_frame)
        fl.setContentsMargins(15, 10, 15, 10)
        fl.setSpacing(12)

        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("🔍  Arıza ID, Cihaz ID, Konu ara...")
        self.txt_search.setStyleSheet(S["search"])
        self.txt_search.setFixedWidth(280)
        fl.addWidget(self.txt_search)

        self.cmb_durum = QComboBox()
        self.cmb_durum.setStyleSheet(S["combo"])
        self.cmb_durum.setFixedWidth(170)
        self.cmb_durum.addItems([
            "Tüm Durumlar", "Açık", "İşlemde",
            "Parça Bekliyor", "Dış Serviste",
            "Kapalı (Çözüldü)", "Kapalı (İptal)"
        ])
        fl.addWidget(self.cmb_durum)

        self.cmb_oncelik = QComboBox()
        self.cmb_oncelik.setStyleSheet(S["combo"])
        self.cmb_oncelik.setFixedWidth(150)
        self.cmb_oncelik.addItems(
            ["Tüm Öncelikler", "Düşük", "Normal", "Yüksek", "Acil (Kritik)"]
        )
        fl.addWidget(self.cmb_oncelik)

        fl.addStretch()

        self.btn_refresh = QPushButton("⟳")
        self.btn_refresh.setToolTip("Listeyi Yenile")
        self.btn_refresh.setFixedSize(36, 36)
        self.btn_refresh.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_refresh.setStyleSheet(S["refresh_btn"])
        fl.addWidget(self.btn_refresh)

        self.btn_kapat = QPushButton("✕ Kapat")
        self.btn_kapat.setToolTip("Kapat")
        self.btn_kapat.setFixedSize(100, 36)
        self.btn_kapat.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_kapat.setStyleSheet(S["close_btn"])
        fl.addWidget(self.btn_kapat)

        main.addWidget(filter_frame)

        # ── Progress ──
        self.progress = QProgressBar()
        self.progress.setFixedHeight(4)
        self.progress.setTextVisible(False)
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setStyleSheet(S.get("progress", ""))
        main.addWidget(self.progress)

        # ── Splitter: Liste üstte, Detay altta ──
        splitter = QSplitter(Qt.Vertical)
        splitter.setStyleSheet(S["splitter"])

        # Tablo
        self._model = ArizaTableModel()
        self._proxy = QSortFilterProxyModel()
        self._proxy.setSourceModel(self._model)
        self._proxy.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self._proxy.setFilterKeyColumn(-1)

        self.table = QTableView()
        self.table.setModel(self._proxy)
        self.table.setStyleSheet(S["table"])
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSortingEnabled(True)

        hdr = self.table.horizontalHeader()
        hdr.setSectionResizeMode(QHeaderView.Stretch)
        for i, (_, _, w) in enumerate(COLUMNS):
            if w < 150:
                hdr.setSectionResizeMode(i, QHeaderView.ResizeToContents)

        list_wrap = QWidget()
        lw_lay = QVBoxLayout(list_wrap)
        lw_lay.setContentsMargins(0, 0, 0, 0)
        lw_lay.addWidget(self.table)
        splitter.addWidget(list_wrap)

        # Detay paneli
        detail_box = QGroupBox("📋  Seçili Arıza Detayı")
        detail_box.setStyleSheet(S["group"])
        d_lay = QVBoxLayout(detail_box)
        d_lay.setContentsMargins(10, 10, 10, 10)

        self.lbl_detail = QTextBrowser()
        self.lbl_detail.setStyleSheet(
            "background:transparent; border:none; color:#e0e2ea;"
        )
        self.lbl_detail.setHtml(
            "<p style='color:#8b8fa3'>Listeden bir arıza seçiniz.</p>"
        )
        d_lay.addWidget(self.lbl_detail)

        h_det_btn = QHBoxLayout()
        h_det_btn.addStretch()
        self.btn_islem = QPushButton("🛠️  İşlem Ekle")
        self.btn_islem.setStyleSheet(S["action_btn"])
        self.btn_islem.setEnabled(False)
        h_det_btn.addWidget(self.btn_islem)
        d_lay.addLayout(h_det_btn)

        splitter.addWidget(detail_box)
        splitter.setSizes([520, 210])
        main.addWidget(splitter, 1)

        # ── Footer ──
        footer = QHBoxLayout()
        self.lbl_count = QLabel("Toplam: 0 kayıt")
        self.lbl_count.setStyleSheet(S["footer_label"])
        footer.addWidget(self.lbl_count)
        footer.addStretch()
        main.addLayout(footer)

        # Sol tarafı ana layout'a ekle
        self.root_layout.addWidget(self.left_container, 1)

        # ── Sağ Panel (Arıza İşlem) ──
        self.islem_panel = ArizaIslemPenceresi(db=self._db, ana_pencere=self)
        self.islem_panel.setVisible(False)
        self.islem_panel.setStyleSheet("border-left: 1px solid rgba(255, 255, 255, 0.1); background-color: #16172b;")
        self.islem_panel.kapanma_istegi.connect(lambda: self.islem_panel.setVisible(False))
        self.root_layout.addWidget(self.islem_panel, 0)

        # Context Menu Policy
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)

    # ─── Sinyaller ────────────────────────────────────────────

    def _connect_signals(self):
        self.txt_search.textChanged.connect(self._apply_filter)
        self.cmb_durum.currentTextChanged.connect(self._apply_filter)
        self.cmb_oncelik.currentTextChanged.connect(self._apply_filter)
        self.btn_refresh.clicked.connect(self.load_data)
        self.table.selectionModel().selectionChanged.connect(self._on_selection_changed)
        self.btn_islem.clicked.connect(self._on_islem_clicked)

    # ─── Veri ─────────────────────────────────────────────────

    def load_data(self):
        if not self._db:
            return
        self.progress.setRange(0, 0)
        try:
            from database.repository_registry import RepositoryRegistry
            registry       = RepositoryRegistry(self._db)
            repo           = registry.get("Cihaz_Ariza")
            self._all_data = repo.get_all()
            self._all_data.sort(
                key=lambda x: x.get("BaslangicTarihi", ""), reverse=True
            )
        except Exception as e:
            logger.error(f"Arıza listesi yükleme hatası: {e}")
            self._all_data = []
        finally:
            self.progress.setRange(0, 100)
            self.progress.setValue(100)

        self._model.set_data(self._all_data)
        self._apply_filter()

    # ─── Filtre ───────────────────────────────────────────────

    def _apply_filter(self):
        search  = self.txt_search.text().strip().lower()
        durum   = self.cmb_durum.currentText()
        oncelik = self.cmb_oncelik.currentText()

        filtered = []
        for row in self._all_data:
            haystack = " ".join([
                str(row.get("Arizaid",         "")),
                str(row.get("Cihazid",          "")),
                str(row.get("Baslik",           "")),
                str(row.get("Bildiren",         "")),
            ]).lower()
            if search and search not in haystack:
                continue
            if durum != "Tüm Durumlar" and row.get("Durum", "") != durum:
                continue
            if oncelik != "Tüm Öncelikler" and row.get("Oncelik", "") != oncelik:
                continue
            filtered.append(row)

        self._model.set_data(filtered)
        self.lbl_count.setText(f"Toplam: {len(filtered)} kayıt")

    # ─── Seçim & Detay ────────────────────────────────────────

    def _get_selected_row(self):
        indexes = self.table.selectionModel().selectedRows()
        if not indexes:
            return None
        src_idx = self._proxy.mapToSource(indexes[0])
        return self._model.get_row(src_idx.row())

    def _on_selection_changed(self):
        row = self._get_selected_row()
        self.btn_islem.setEnabled(row is not None)
        if row is None:
            self.lbl_detail.setHtml(
                "<p style='color:#8b8fa3'>Listeden bir arıza seçiniz.</p>"
            )
            return
        self._show_detail(row)

    def _show_context_menu(self, pos):
        menu = QMenu()
        menu.setStyleSheet(S["context_menu"])
        
        idx = self.table.indexAt(pos)
        if idx.isValid():
            action_islem = QAction("🛠️ İşlem Yap", self)
            action_islem.triggered.connect(self._on_islem_clicked)
            menu.addAction(action_islem)
            
        menu.exec(self.table.viewport().mapToGlobal(pos))

    def _on_islem_clicked(self):
        row = self._get_selected_row()
        if not row:
            return
            
        ariza_id = row.get("Arizaid")
        if ariza_id:
            self.islem_panel.yukle(ariza_id)
            self.islem_panel.setVisible(True)

    def _show_detail(self, data: dict):
        durum  = data.get("Durum", "Açık")
        d_renk = DURUM_RENK.get(durum, QColor("#8b8fa3")).name()
        onc    = data.get("Oncelik", "")
        o_renk = ONCELIK_RENK.get(onc, QColor("#8b8fa3")).name()

        html = f"""
        <h4 style="color:#4dabf7;margin-bottom:8px;">
            {data.get("Baslik","—")}
        </h3>
        <table width="100%" cellpadding="5" cellspacing="0" style="font-size:11px;">
            <tr>
                <td width="100" style="color:#8b8fa3;"><b>Arıza ID:</b></td>
                <td style="color:#e0e2ea;">{data.get("Arizaid","")}</td>
                <td width="100" style="color:#8b8fa3;"><b>Cihaz ID:</b></td>
                <td style="color:#e0e2ea;">{data.get("Cihazid","")}</td>
            </tr>
            <tr>
                <td style="color:#8b8fa3;"><b>Bildiren:</b></td>
                <td style="color:#e0e2ea;">{data.get("Bildiren","")}</td>
                <td style="color:#8b8fa3;"><b>Tarih / Saat:</b></td>
                <td style="color:#e0e2ea;">
                    {data.get("BaslangicTarihi","")} {data.get("Saat","")}
                </td>
            </tr>
            <tr>
                <td style="color:#8b8fa3;"><b>Arıza Tipi:</b></td>
                <td style="color:#e0e2ea;">{data.get("ArizaTipi","")}</td>
                <td style="color:#8b8fa3;"><b>Öncelik:</b></td>
                <td style="color:{o_renk};font-weight:bold;">{onc}</td>
            </tr>
            <tr>
                <td style="color:#8b8fa3;"><b>Durum:</b></td>
                <td style="color:{d_renk};font-weight:bold;">{durum}</td>
                <td></td><td></td>
            </tr>
        </table>
        <hr style="border:1px solid #333;margin:10px 0;">
        <p style="color:#8b8fa3;font-size:12px;"><b>Açıklama:</b></p>
        <p style="color:#e0e0e0;background:rgba(255,255,255,0.04);
                  padding:8px;border-radius:4px;font-size:11px;">
            {data.get("ArizaAcikla","—") or "—"}
        </p>
        """
        self.lbl_detail.setHtml(html)

    def verileri_yenile(self):
        """Arıza işlem penceresinden çağrılır."""
        self.load_data()
