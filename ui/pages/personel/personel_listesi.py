# -*- coding: utf-8 -*-
from PySide6.QtCore import Qt, QSortFilterProxyModel, QModelIndex, QAbstractTableModel
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QFrame, QProgressBar, QPushButton, QHeaderView,
    QTableView, QComboBox, QLineEdit
)
from PySide6.QtGui import QColor

from core.logger import logger


# ─── Tablo sütun tanımları ───
COLUMNS = [
    # (db_key,           başlık,           genişlik)
    ("KimlikNo",         "TC Kimlik No",   120),
    ("AdSoyad",          "Ad Soyad",       160),
    ("HizmetSinifi",     "Hizmet Sınıfı",  120),
    ("KadroUnvani",      "Ünvan",           130),
    ("GorevYeri",        "Görev Yeri",      140),
    ("CepTelefonu",      "Telefon",         120),
    ("Eposta",           "E-posta",         170),
    ("Durum",            "Durum",            80),
]

# ─── Stiller ───
STYLES = {
    "filter_panel": """
        QFrame {
            background-color: #ffffff;
            border: 1px solid #e2e8f0;
            border-radius: 10px;
        }
    """,
    "filter_btn": """
        QPushButton {
            background-color: #e2e8f0; color: #334155;
            border: none; border-radius: 6px;
            padding: 6px 14px; font-size: 12px; font-weight: 600;
        }
        QPushButton:hover { background-color: #cbd5e1; }
        QPushButton:checked {
            background-color: #2563eb; color: #ffffff;
        }
    """,
    "filter_btn_all": """
        QPushButton {
            background-color: #e2e8f0; color: #334155;
            border: none; border-radius: 6px;
            padding: 6px 14px; font-size: 12px; font-weight: 600;
        }
        QPushButton:hover { background-color: #cbd5e1; }
        QPushButton:checked {
            background-color: #0f172a; color: #ffffff;
        }
    """,
    "action_btn": """
        QPushButton {
            background-color: #2563eb; color: #ffffff;
            border: none; border-radius: 6px;
            padding: 7px 16px; font-size: 12px; font-weight: 600;
        }
        QPushButton:hover { background-color: #1d4ed8; }
    """,
    "refresh_btn": """
        QPushButton {
            background-color: #f1f5f9; color: #334155;
            border: 1px solid #cbd5e1; border-radius: 6px;
            padding: 7px 12px; font-size: 12px;
        }
        QPushButton:hover { background-color: #e2e8f0; }
    """,
    "search": """
        QLineEdit {
            background-color: #ffffff;
            border: 1px solid #cbd5e1; border-radius: 8px;
            padding: 7px 12px; font-size: 13px;
        }
        QLineEdit:focus { border: 2px solid #2563eb; }
    """,
    "combo": """
        QComboBox {
            background-color: #ffffff;
            border: 1px solid #cbd5e1; border-radius: 6px;
            padding: 5px 10px; font-size: 12px; min-height: 22px;
        }
        QComboBox:focus { border: 2px solid #2563eb; }
        QComboBox::drop-down {
            border: none; width: 24px;
        }
    """,
    "footer_label": "color: #64748b; font-size: 12px;",
    "excel_btn": """
        QPushButton {
            background-color: #059669; color: #ffffff;
            border: none; border-radius: 6px;
            padding: 6px 14px; font-size: 12px; font-weight: 600;
        }
        QPushButton:hover { background-color: #047857; }
    """,
    "section_label": "color: #64748b; font-size: 11px; font-weight: bold;",
}

# Durum hücre renkleri
DURUM_COLORS = {
    "Aktif":    QColor("#dcfce7"),
    "Pasif":    QColor("#fee2e2"),
    "İzinli":   QColor("#fef9c3"),
}


# ═══════════════════════════════════════════════
#  TABLE MODEL
# ═══════════════════════════════════════════════

class PersonelTableModel(QAbstractTableModel):
    """Personel verisi için tablo modeli."""

    def __init__(self, data=None, parent=None):
        super().__init__(parent)
        self._data = data or []
        self._keys = [c[0] for c in COLUMNS]
        self._headers = [c[1] for c in COLUMNS]

    def rowCount(self, parent=QModelIndex()):
        return len(self._data)

    def columnCount(self, parent=QModelIndex()):
        return len(COLUMNS)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None

        row = self._data[index.row()]
        col_key = self._keys[index.column()]

        if role == Qt.DisplayRole:
            return str(row.get(col_key, ""))

        if role == Qt.BackgroundRole and col_key == "Durum":
            durum = str(row.get("Durum", ""))
            return DURUM_COLORS.get(durum)

        if role == Qt.TextAlignmentRole:
            if col_key in ("KimlikNo", "CepTelefonu", "Durum"):
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
#  ANA SAYFA WİDGET
# ═══════════════════════════════════════════════

class PersonelListesiPage(QWidget):
    """
    Personel Listesi sayfası.
    MainWindow stack'ine eklenir.
    """

    def __init__(self, db=None, parent=None):
        super().__init__(parent)
        self._db = db
        self._all_data = []
        self._active_filter = "Tümü"

        self._setup_ui()
        self._connect_signals()

    # ───────────────────────────────────────

    def _setup_ui(self):
        main = QVBoxLayout(self)
        main.setContentsMargins(20, 12, 20, 12)
        main.setSpacing(12)

        # ── 1. FILTER PANEL ──
        filter_frame = QFrame()
        filter_frame.setStyleSheet(STYLES["filter_panel"])
        fp = QVBoxLayout(filter_frame)
        fp.setContentsMargins(16, 12, 16, 12)
        fp.setSpacing(10)

        # Üst satır: Durum filtreleri + Arama
        row1 = QHBoxLayout()
        row1.setSpacing(8)

        lbl = QLabel("Durum")
        lbl.setStyleSheet(STYLES["section_label"])
        row1.addWidget(lbl)

        self._filter_btns = {}
        for text in ["Aktif", "Pasif", "İzinli", "Tümü"]:
            btn = QPushButton(text)
            btn.setCheckable(True)
            btn.setStyleSheet(STYLES["filter_btn_all"] if text == "Tümü" else STYLES["filter_btn"])
            btn.setFixedHeight(30)
            if text == "Tümü":
                btn.setChecked(True)
            row1.addWidget(btn)
            self._filter_btns[text] = btn

        row1.addSpacing(16)

        # Arama
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍  İsim, TC veya telefon ara...")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.setStyleSheet(STYLES["search"])
        self.search_input.setFixedWidth(260)
        row1.addWidget(self.search_input)

        row1.addStretch()

        fp.addLayout(row1)

        # Alt satır: Combobox filtreler + Aksiyon butonları
        row2 = QHBoxLayout()
        row2.setSpacing(8)

        lbl2 = QLabel("Birim")
        lbl2.setStyleSheet(STYLES["section_label"])
        row2.addWidget(lbl2)

        self.cmb_gorev_yeri = QComboBox()
        self.cmb_gorev_yeri.addItem("Tüm Birimler")
        self.cmb_gorev_yeri.setFixedWidth(180)
        self.cmb_gorev_yeri.setStyleSheet(STYLES["combo"])
        row2.addWidget(self.cmb_gorev_yeri)

        row2.addSpacing(8)

        lbl3 = QLabel("Sınıf")
        lbl3.setStyleSheet(STYLES["section_label"])
        row2.addWidget(lbl3)

        self.cmb_hizmet = QComboBox()
        self.cmb_hizmet.addItem("Tüm Sınıflar")
        self.cmb_hizmet.setFixedWidth(160)
        self.cmb_hizmet.setStyleSheet(STYLES["combo"])
        row2.addWidget(self.cmb_hizmet)

        row2.addStretch()

        self.btn_yenile = QPushButton("⟳ Yenile")
        self.btn_yenile.setStyleSheet(STYLES["refresh_btn"])
        self.btn_yenile.setFixedHeight(30)
        row2.addWidget(self.btn_yenile)

        self.btn_yeni = QPushButton("＋ Yeni Kayıt")
        self.btn_yeni.setStyleSheet(STYLES["action_btn"])
        self.btn_yeni.setFixedHeight(30)
        row2.addWidget(self.btn_yeni)

        fp.addLayout(row2)
        main.addWidget(filter_frame)

        # ── 2. TABLO ──
        self._model = PersonelTableModel()
        self._proxy = QSortFilterProxyModel()
        self._proxy.setSourceModel(self._model)
        self._proxy.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self._proxy.setFilterKeyColumn(-1)

        self.table = QTableView()
        self.table.setModel(self._proxy)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableView.SelectRows)
        self.table.setSelectionMode(QTableView.SingleSelection)
        self.table.setSortingEnabled(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(True)
        self.table.setStyleSheet("""
            QTableView {
                background-color: #ffffff;
                alternate-background-color: #f8fafc;
                border: 1px solid #e2e8f0;
                border-radius: 8px;
                gridline-color: #e2e8f0;
                selection-background-color: #dbeafe;
                selection-color: #1e293b;
                font-size: 13px;
            }
            QTableView::item { padding: 6px 8px; }
            QHeaderView::section {
                background-color: #f1f5f9; color: #334155;
                font-weight: 600; font-size: 12px;
                padding: 8px; border: none;
                border-bottom: 2px solid #cbd5e1;
                border-right: 1px solid #e2e8f0;
            }
        """)

        # Sütun genişlikleri
        header = self.table.horizontalHeader()
        header.setStretchLastSection(True)
        for i, (_, _, width) in enumerate(COLUMNS):
            header.setSectionResizeMode(i, QHeaderView.Interactive)
            self.table.setColumnWidth(i, width)

        # Son sütun stretch
        header.setSectionResizeMode(len(COLUMNS) - 1, QHeaderView.Stretch)

        main.addWidget(self.table, 1)

        # ── 3. FOOTER ──
        footer = QHBoxLayout()
        footer.setSpacing(8)

        self.lbl_info = QLabel("0 kayıt")
        self.lbl_info.setStyleSheet(STYLES["footer_label"])
        footer.addWidget(self.lbl_info)

        footer.addStretch()

        self.progress = QProgressBar()
        self.progress.setFixedWidth(150)
        self.progress.setFixedHeight(16)
        self.progress.setVisible(False)
        footer.addWidget(self.progress)

        self.btn_excel = QPushButton("📥 Excel'e Aktar")
        self.btn_excel.setStyleSheet(STYLES["excel_btn"])
        self.btn_excel.setFixedHeight(30)
        footer.addWidget(self.btn_excel)

        main.addLayout(footer)

    # ───────────────────────────────────────

    def _connect_signals(self):
        # Durum filtre butonları
        for text, btn in self._filter_btns.items():
            btn.clicked.connect(lambda checked, t=text: self._on_filter_click(t))

        # Arama
        self.search_input.textChanged.connect(self._on_search)

        # Combobox filtreler
        self.cmb_gorev_yeri.currentTextChanged.connect(lambda: self._apply_filters())
        self.cmb_hizmet.currentTextChanged.connect(lambda: self._apply_filters())

        # Yenile
        self.btn_yenile.clicked.connect(self.load_data)

        # Tablo çift tıklama
        self.table.doubleClicked.connect(self._on_row_double_click)

    # ═══════════════════════════════════════════
    #  VERİ İŞLEMLERİ
    # ═══════════════════════════════════════════

    def load_data(self):
        """Veritabanından personel verisini yükler."""
        if not self._db:
            logger.warning("Personel listesi: DB bağlantısı yok")
            return

        try:
            from database.repository_registry import RepositoryRegistry
            registry = RepositoryRegistry(self._db)
            repo = registry.get("Personel")
            self._all_data = repo.get_all()

            logger.info(f"Personel yüklendi: {len(self._all_data)} kayıt")

            # Combobox'ları doldur
            self._populate_combos()

            # Tabloyu güncelle
            self._apply_filters()

        except Exception as e:
            logger.error(f"Personel yükleme hatası: {e}")

    def _populate_combos(self):
        """Combobox'ları Sabitler tablosundan doldurur."""
        from database.repository_registry import RepositoryRegistry
        registry = RepositoryRegistry(self._db)
        sabitler = registry.get("Sabitler")
        all_sabit = sabitler.get_all()

        # Görev Yeri
        gorev_yerleri = sorted([
            str(r.get("MenuEleman", "")).strip()
            for r in all_sabit
            if r.get("Kod") == "Gorev_Yeri" and r.get("MenuEleman", "").strip()
        ])
        self.cmb_gorev_yeri.clear()
        self.cmb_gorev_yeri.addItem("Tüm Birimler")
        self.cmb_gorev_yeri.addItems(gorev_yerleri)

        # Hizmet Sınıfı
        siniflar = sorted([
            str(r.get("MenuEleman", "")).strip()
            for r in all_sabit
            if r.get("Kod") == "Hizmet_Sinifi" and r.get("MenuEleman", "").strip()
        ])
        self.cmb_hizmet.clear()
        self.cmb_hizmet.addItem("Tüm Sınıflar")
        self.cmb_hizmet.addItems(siniflar)

    # ───────────────────────────────────────

    def _on_filter_click(self, filter_text):
        """Durum filtre butonu tıklandığında."""
        self._active_filter = filter_text

        # Sadece tıklananı aktif yap
        for text, btn in self._filter_btns.items():
            btn.setChecked(text == filter_text)

        self._apply_filters()

    def _on_search(self, text):
        """Arama kutusu değiştiğinde."""
        self._proxy.setFilterFixedString(text)
        self._update_count()

    def _apply_filters(self):
        """Tüm filtreleri uygular ve tabloyu günceller."""
        filtered = self._all_data

        # Durum filtresi
        if self._active_filter != "Tümü":
            filtered = [
                r for r in filtered
                if str(r.get("Durum", "")).strip() == self._active_filter
            ]

        # Birim filtresi
        birim = self.cmb_gorev_yeri.currentText()
        if birim and birim != "Tüm Birimler":
            filtered = [
                r for r in filtered
                if str(r.get("GorevYeri", "")).strip() == birim
            ]

        # Sınıf filtresi
        sinif = self.cmb_hizmet.currentText()
        if sinif and sinif != "Tüm Sınıflar":
            filtered = [
                r for r in filtered
                if str(r.get("HizmetSinifi", "")).strip() == sinif
            ]

        self._model.set_data(filtered)
        self._update_count()

    def _update_count(self):
        """Footer'daki kayıt sayısını günceller."""
        visible = self._proxy.rowCount()
        total = len(self._all_data)
        self.lbl_info.setText(f"{visible} / {total} kayıt gösteriliyor")

    # ───────────────────────────────────────

    def _on_row_double_click(self, index):
        """Satıra çift tıklandığında detay açar."""
        source_idx = self._proxy.mapToSource(index)
        row_data = self._model.get_row(source_idx.row())
        if row_data:
            kimlik = row_data.get("KimlikNo", "")
            ad = row_data.get("AdSoyad", "")
            logger.info(f"Personel seçildi: {kimlik} — {ad}")
            # TODO: Personel detay sayfası açılacak

    # ───────────────────────────────────────

    def get_selected(self):
        """Seçili satırın verisini döner."""
        indexes = self.table.selectionModel().selectedRows()
        if indexes:
            source_idx = self._proxy.mapToSource(indexes[0])
            return self._model.get_row(source_idx.row())
        return None