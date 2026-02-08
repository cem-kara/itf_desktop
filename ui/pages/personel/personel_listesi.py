# -*- coding: utf-8 -*-
from PySide6.QtCore import Qt, QSortFilterProxyModel, QModelIndex, QAbstractTableModel, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QFrame, QProgressBar, QPushButton, QHeaderView,
    QTableView, QComboBox, QLineEdit, QMenu, QMessageBox
)
from PySide6.QtGui import QColor, QCursor, QAction

from core.logger import logger


# ─── Tablo sütun tanımları ───
COLUMNS = [
    ("KimlikNo",         "TC Kimlik No",   120),
    ("AdSoyad",          "Ad Soyad",       160),
    ("HizmetSinifi",     "Hizmet Sınıfı",  120),
    ("KadroUnvani",      "Ünvan",           130),
    ("GorevYeri",        "Görev Yeri",      140),
    ("CepTelefonu",      "Telefon",         120),
    ("Eposta",           "E-posta",         170),
    ("Durum",            "Durum",            80),
]

# ─── W11 Dark Glass Stiller ───
STYLES = {
    "filter_panel": """
        QFrame {
            background-color: rgba(30, 32, 44, 0.85);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 10px;
        }
    """,
    "filter_btn": """
        QPushButton {
            background-color: rgba(255, 255, 255, 0.06);
            color: #8b8fa3;
            border: 1px solid rgba(255, 255, 255, 0.06);
            border-radius: 6px;
            padding: 6px 14px; font-size: 12px; font-weight: 600;
        }
        QPushButton:hover {
            background-color: rgba(255, 255, 255, 0.10);
            color: #c8cad0;
        }
        QPushButton:checked {
            background-color: rgba(29, 117, 254, 0.35);
            color: #ffffff;
            border: 1px solid rgba(29, 117, 254, 0.5);
        }
    """,
    "filter_btn_all": """
        QPushButton {
            background-color: rgba(255, 255, 255, 0.06);
            color: #8b8fa3;
            border: 1px solid rgba(255, 255, 255, 0.06);
            border-radius: 6px;
            padding: 6px 14px; font-size: 12px; font-weight: 600;
        }
        QPushButton:hover {
            background-color: rgba(255, 255, 255, 0.10);
            color: #c8cad0;
        }
        QPushButton:checked {
            background-color: rgba(255, 255, 255, 0.12);
            color: #e0e2ea;
            border: 1px solid rgba(255, 255, 255, 0.15);
        }
    """,
    "action_btn": """
        QPushButton {
            background-color: rgba(29, 117, 254, 0.25);
            color: #6bd3ff;
            border: 1px solid rgba(29, 117, 254, 0.4);
            border-radius: 6px;
            padding: 7px 16px; font-size: 12px; font-weight: 600;
        }
        QPushButton:hover {
            background-color: rgba(29, 117, 254, 0.4);
            color: #ffffff;
        }
    """,
    "refresh_btn": """
        QPushButton {
            background-color: rgba(255, 255, 255, 0.05);
            color: #8b8fa3;
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 6px;
            padding: 7px 12px; font-size: 12px;
        }
        QPushButton:hover {
            background-color: rgba(255, 255, 255, 0.10);
            color: #c8cad0;
        }
    """,
    "search": """
        QLineEdit {
            background-color: #1e202c;
            border: 1px solid #292b41;
            border-bottom: 2px solid #9dcbe3;
            border-radius: 8px;
            padding: 7px 12px; font-size: 13px;
            color: #e0e2ea;
        }
        QLineEdit:focus {
            border: 1px solid rgba(29, 117, 254, 0.5);
            border-bottom: 2px solid #1d75fe;
        }
        QLineEdit::placeholder {
            color: #a2a5ae;
        }
    """,
    "combo": """
        QComboBox {
            background-color: #1e202c;
            border: 1px solid #292b41;
            border-bottom: 2px solid #9dcbe3;
            border-radius: 6px;
            padding: 5px 10px; font-size: 12px;
            color: #e0e2ea; min-height: 22px;
        }
        QComboBox:focus {
            border-bottom: 2px solid #1d75fe;
        }
        QComboBox::drop-down {
            border: none; width: 24px;
        }
        QComboBox QAbstractItemView {
            background-color: #1e202c;
            border: 1px solid rgba(255, 255, 255, 0.1);
            color: #c8cad0;
            selection-background-color: rgba(29, 117, 254, 0.3);
            selection-color: #ffffff;
        }
    """,
    "table": """
        QTableView {
            background-color: rgba(30, 32, 44, 0.7);
            alternate-background-color: rgba(255, 255, 255, 0.02);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 8px;
            gridline-color: rgba(255, 255, 255, 0.04);
            selection-background-color: rgba(29, 117, 254, 0.45);
            selection-color: #ffffff;
            color: #c8cad0;
            font-size: 13px;
        }
        QTableView::item {
            padding: 6px 8px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.02);
        }
        QTableView::item:selected {
            background-color: rgba(29, 117, 254, 0.45);
            color: #ffffff;
        }
        QTableView::item:hover:!selected {
            background-color: rgba(255, 255, 255, 0.04);
        }
        QHeaderView::section {
            background-color: rgba(255, 255, 255, 0.05);
            color: #8b8fa3;
            font-weight: 600; font-size: 12px;
            padding: 8px; border: none;
            border-bottom: 1px solid rgba(29, 117, 254, 0.3);
            border-right: 1px solid rgba(255, 255, 255, 0.03);
        }
    """,
    "footer_label": "color: #5a5d6e; font-size: 12px; background: transparent;",
    "excel_btn": """
        QPushButton {
            background-color: rgba(5, 150, 105, 0.25);
            color: #6ee7b7;
            border: 1px solid rgba(5, 150, 105, 0.4);
            border-radius: 6px;
            padding: 6px 14px; font-size: 12px; font-weight: 600;
        }
        QPushButton:hover {
            background-color: rgba(5, 150, 105, 0.4);
            color: #ffffff;
        }
    """,
    "section_label": "color: #5a5d6e; font-size: 11px; font-weight: bold; background: transparent;",
    "context_menu": """
        QMenu {
            background-color: #1e202c;
            border: 1px solid rgba(255, 255, 255, 0.12);
            border-radius: 8px;
            padding: 4px;
            color: #c8cad0; font-size: 13px;
        }
        QMenu::item {
            padding: 8px 24px 8px 12px;
            border-radius: 4px; margin: 2px;
        }
        QMenu::item:selected {
            background-color: rgba(29, 117, 254, 0.35);
            color: #ffffff;
        }
        QMenu::separator {
            height: 1px;
            background: rgba(255, 255, 255, 0.08);
            margin: 4px 8px;
        }
    """,
}

# Durum hücre renkleri (koyu tema uyumlu)
DURUM_COLORS = {
    "Aktif":    QColor(34, 197, 94, 40),     # yeşil şeffaf
    "Pasif":    QColor(239, 68, 68, 40),      # kırmızı şeffaf
    "İzinli":   QColor(234, 179, 8, 40),      # sarı şeffaf
}


# ═══════════════════════════════════════════════

class PersonelTableModel(QAbstractTableModel):

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

        if role == Qt.ForegroundRole:
            if col_key == "Durum":
                durum = str(row.get("Durum", ""))
                colors = {
                    "Aktif": QColor("#4ade80"),
                    "Pasif": QColor("#f87171"),
                    "İzinli": QColor("#facc15"),
                }
                return colors.get(durum, QColor("#8b8fa3"))
            # Diğer kolonlar QSS ile yönetilir (selection-color çalışsın)
            return None

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

class PersonelListesiPage(QWidget):

    izin_requested = Signal(dict)  # personel_data

    def __init__(self, db=None, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background-color: transparent;")
        self._db = db
        self._all_data = []
        self._active_filter = "Tümü"
        self._filter_btns = {}
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        main = QVBoxLayout(self)
        main.setContentsMargins(20, 12, 20, 12)
        main.setSpacing(12)

        # ── 1. FILTER PANEL (tek satır) ──
        filter_frame = QFrame()
        filter_frame.setStyleSheet(STYLES["filter_panel"])
        fp = QHBoxLayout(filter_frame)
        fp.setContentsMargins(12, 8, 12, 8)
        fp.setSpacing(8)

        for text in ["Aktif", "Pasif", "İzinli", "Tümü"]:
            btn = QPushButton(text)
            btn.setCheckable(True)
            btn.setStyleSheet(STYLES["filter_btn_all"] if text == "Tümü" else STYLES["filter_btn"])
            btn.setFixedHeight(28)
            if text == "Tümü":
                btn.setChecked(True)
            fp.addWidget(btn)
            self._filter_btns[text] = btn

        sep = QFrame()
        sep.setFixedWidth(1)
        sep.setFixedHeight(20)
        sep.setStyleSheet("background-color: rgba(255,255,255,0.08);")
        fp.addWidget(sep)

        self.cmb_gorev_yeri = QComboBox()
        self.cmb_gorev_yeri.addItem("Tüm Birimler")
        self.cmb_gorev_yeri.setFixedWidth(150)
        self.cmb_gorev_yeri.setStyleSheet(STYLES["combo"])
        fp.addWidget(self.cmb_gorev_yeri)

        self.cmb_hizmet = QComboBox()
        self.cmb_hizmet.addItem("Tüm Sınıflar")
        self.cmb_hizmet.setFixedWidth(130)
        self.cmb_hizmet.setStyleSheet(STYLES["combo"])
        fp.addWidget(self.cmb_hizmet)

        sep2 = QFrame()
        sep2.setFixedWidth(1)
        sep2.setFixedHeight(20)
        sep2.setStyleSheet("background-color: rgba(255,255,255,0.08);")
        fp.addWidget(sep2)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Ara...")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.setStyleSheet(STYLES["search"])
        self.search_input.setFixedWidth(200)
        fp.addWidget(self.search_input)

        fp.addStretch()

        self.btn_yenile = QPushButton("⟳")
        self.btn_yenile.setStyleSheet(STYLES["refresh_btn"])
        self.btn_yenile.setFixedSize(60, 28)
        self.btn_yenile.setToolTip("Yenile")
        self.btn_yenile.setCursor(QCursor(Qt.PointingHandCursor))
        fp.addWidget(self.btn_yenile)

        self.btn_yeni = QPushButton("＋ Yeni")
        self.btn_yeni.setStyleSheet(STYLES["action_btn"])
        self.btn_yeni.setFixedHeight(28)
        self.btn_yeni.setCursor(QCursor(Qt.PointingHandCursor))
        fp.addWidget(self.btn_yeni)

        sep3 = QFrame()
        sep3.setFixedWidth(1)
        sep3.setFixedHeight(20)
        sep3.setStyleSheet("background-color: rgba(255,255,255,0.08);")
        fp.addWidget(sep3)

        self.btn_kapat = QPushButton("✕")
        self.btn_kapat.setToolTip("Pencereyi Kapat")
        self.btn_kapat.setFixedSize(60, 28)
        self.btn_kapat.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_kapat.setStyleSheet("""
            QPushButton {
                background-color: rgba(239, 68, 68, 0.15);
                color: #f87171; border: 1px solid rgba(239, 68, 68, 0.25);
                border-radius: 6px; font-size: 14px; font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(239, 68, 68, 0.35);
                color: #ffffff;
            }
        """)
        fp.addWidget(self.btn_kapat)

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
        self.table.setShowGrid(False)
        self.table.setStyleSheet(STYLES["table"])
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)

        # Orantılı kolon genişlikleri
        header = self.table.horizontalHeader()
        header.setStretchLastSection(False)
        # Stretch ratios: TC(2) Ad(3) Sınıf(2) Ünvan(2) Görev(2) Tel(2) Eposta(3) Durum(1)
        stretch_cols = [2, 3, 2, 2, 2, 2, 3, 1]
        for i, s in enumerate(stretch_cols):
            header.setSectionResizeMode(i, QHeaderView.Stretch)
        # ResizeToContents only for Durum (last)
        header.setSectionResizeMode(len(COLUMNS) - 1, QHeaderView.ResizeToContents)

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
        self.progress.setStyleSheet("""
            QProgressBar {
                background-color: rgba(255,255,255,0.05);
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 4px; color: #8b8fa3; font-size: 11px;
            }
            QProgressBar::chunk {
                background-color: rgba(29, 117, 254, 0.6);
                border-radius: 3px;
            }
        """)
        footer.addWidget(self.progress)

        self.btn_excel = QPushButton("📥 Excel'e Aktar")
        self.btn_excel.setStyleSheet(STYLES["excel_btn"])
        self.btn_excel.setFixedHeight(28)
        self.btn_excel.setCursor(QCursor(Qt.PointingHandCursor))
        footer.addWidget(self.btn_excel)

        main.addLayout(footer)

    def _connect_signals(self):
        for text, btn in self._filter_btns.items():
            btn.clicked.connect(lambda checked, t=text: self._on_filter_click(t))
        self.search_input.textChanged.connect(self._on_search)
        self.cmb_gorev_yeri.currentTextChanged.connect(lambda: self._apply_filters())
        self.cmb_hizmet.currentTextChanged.connect(lambda: self._apply_filters())
        self.btn_yenile.clicked.connect(self.load_data)
        self.table.doubleClicked.connect(self._on_row_double_click)

    # ═══════════════════════════════════════════

    def load_data(self):
        if not self._db:
            logger.warning("Personel listesi: DB bağlantısı yok")
            return
        try:
            from database.repository_registry import RepositoryRegistry
            registry = RepositoryRegistry(self._db)
            repo = registry.get("Personel")
            self._all_data = repo.get_all()
            logger.info(f"Personel yüklendi: {len(self._all_data)} kayıt")
            self._populate_combos()
            self._apply_filters()
        except Exception as e:
            logger.error(f"Personel yükleme hatası: {e}")

    def _populate_combos(self):
        """Combobox'ları Sabitler tablosundan doldurur."""
        try:
            from database.repository_registry import RepositoryRegistry
            registry = RepositoryRegistry(self._db)
            sabitler = registry.get("Sabitler")
            all_sabit = sabitler.get_all()

            gorev_yerleri = sorted([
                str(r.get("MenuEleman", "")).strip()
                for r in all_sabit
                if r.get("Kod") == "Gorev_Yeri" and r.get("MenuEleman", "").strip()
            ])
            self.cmb_gorev_yeri.clear()
            self.cmb_gorev_yeri.addItem("Tüm Birimler")
            self.cmb_gorev_yeri.addItems(gorev_yerleri)

            siniflar = sorted([
                str(r.get("MenuEleman", "")).strip()
                for r in all_sabit
                if r.get("Kod") == "Hizmet_Sinifi" and r.get("MenuEleman", "").strip()
            ])
            self.cmb_hizmet.clear()
            self.cmb_hizmet.addItem("Tüm Sınıflar")
            self.cmb_hizmet.addItems(siniflar)
        except Exception as e:
            logger.error(f"Sabitler yükleme hatası: {e}")

    def _on_filter_click(self, filter_text):
        self._active_filter = filter_text
        for text, btn in self._filter_btns.items():
            btn.setChecked(text == filter_text)
        self._apply_filters()

    def _on_search(self, text):
        self._proxy.setFilterFixedString(text)
        self._update_count()

    def _apply_filters(self):
        filtered = self._all_data

        if self._active_filter == "İzinli":
            # Izin_Giris tablosundan bu ay izinli personelleri bul
            izinli_tcler = self._get_izinli_personeller()
            filtered = [
                r for r in filtered
                if str(r.get("KimlikNo", "")).strip() in izinli_tcler
            ]
        elif self._active_filter != "Tümü":
            filtered = [
                r for r in filtered
                if str(r.get("Durum", "")).strip() == self._active_filter
            ]

        birim = self.cmb_gorev_yeri.currentText()
        if birim and birim != "Tüm Birimler":
            filtered = [
                r for r in filtered
                if str(r.get("GorevYeri", "")).strip() == birim
            ]

        sinif = self.cmb_hizmet.currentText()
        if sinif and sinif != "Tüm Sınıflar":
            filtered = [
                r for r in filtered
                if str(r.get("HizmetSinifi", "")).strip() == sinif
            ]

        self._model.set_data(filtered)
        self._update_count()

    def _parse_date(self, val):
        """TEXT tarih değerini yyyy-MM-dd formatına çevirir. Birden fazla format destekler."""
        val = str(val).strip()
        if not val:
            return ""
        from datetime import datetime
        for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y", "%Y/%m/%d", "%d-%m-%Y"):
            try:
                return datetime.strptime(val, fmt).strftime("%Y-%m-%d")
            except ValueError:
                continue
        return val  # parse edilemezse olduğu gibi döndür

    def _get_izinli_personeller(self):
        """Izin_Giris tablosundan bu ay+yıl içinde izinli personel TC'lerini döndürür."""
        if not self._db:
            return set()
        try:
            from datetime import date
            bugun = date.today()
            ay_bas = date(bugun.year, bugun.month, 1).isoformat()
            if bugun.month == 12:
                ay_son = date(bugun.year + 1, 1, 1).isoformat()
            else:
                ay_son = date(bugun.year, bugun.month + 1, 1).isoformat()

            logger.info(f"İzinli sorgu aralığı: {ay_bas} — {ay_son}")

            from database.repository_registry import RepositoryRegistry
            registry = RepositoryRegistry(self._db)
            repo = registry.get("Izin_Giris")
            all_izin = repo.get_all()

            # Bu ay ile çakışan izinler:
            # BaslamaTarihi < ay_son AND BitisTarihi >= ay_bas
            izinli = set()
            for r in all_izin:
                baslama = self._parse_date(r.get("BaslamaTarihi", ""))
                bitis = self._parse_date(r.get("BitisTarihi", ""))
                tc = str(r.get("Personelid", "")).strip()
                if not baslama or not tc:
                    continue
                if not bitis:
                    bitis = baslama
                if baslama < ay_son and bitis >= ay_bas:
                    izinli.add(tc)

            logger.info(f"Bu ay izinli personel: {len(izinli)} kişi")
            return izinli
        except Exception as e:
            logger.error(f"İzinli personel sorgusu hatası: {e}")
            return set()

    def _update_count(self):
        visible = self._proxy.rowCount()
        total = len(self._all_data)
        self.lbl_info.setText(f"{visible} / {total} kayıt gösteriliyor")

    def _on_row_double_click(self, index):
        source_idx = self._proxy.mapToSource(index)
        row_data = self._model.get_row(source_idx.row())
        if row_data:
            kimlik = row_data.get("KimlikNo", "")
            ad = row_data.get("AdSoyad", "")
            logger.info(f"Personel seçildi: {kimlik} — {ad}")

    def get_selected(self):
        indexes = self.table.selectionModel().selectedRows()
        if indexes:
            source_idx = self._proxy.mapToSource(indexes[0])
            return self._model.get_row(source_idx.row())
        return None

    # ═══════════════════════════════════════════
    #  SAĞ TIKLAMA MENÜSÜ
    # ═══════════════════════════════════════════

    def _show_context_menu(self, pos):
        index = self.table.indexAt(pos)
        if not index.isValid():
            return

        source_idx = self._proxy.mapToSource(index)
        row_data = self._model.get_row(source_idx.row())
        if not row_data:
            return

        ad = row_data.get("AdSoyad", "")
        tc = row_data.get("KimlikNo", "")
        durum = str(row_data.get("Durum", "")).strip()

        menu = QMenu(self)
        menu.setStyleSheet(STYLES["context_menu"])

        # Detay aç
        act_detay = menu.addAction("📋 Detay Görüntüle")
        act_detay.triggered.connect(lambda: self.table.doubleClicked.emit(index))

        menu.addSeparator()

        # İzin Girişi
        act_izin = menu.addAction("🏖️ İzin Girişi")
        act_izin.triggered.connect(lambda: self._izin_girisi(row_data))

        menu.addSeparator()

        # Durum değiştirme
        if durum != "Aktif":
            act_aktif = menu.addAction("✅ Aktif Yap")
            act_aktif.triggered.connect(lambda: self._change_durum(tc, ad, "Aktif"))

        if durum != "Pasif":
            act_pasif = menu.addAction("⛔ Pasif Yap")
            act_pasif.triggered.connect(lambda: self._change_durum(tc, ad, "Pasif"))

        if durum != "İzinli":
            act_izinli = menu.addAction("⏸️ İzinli Yap")
            act_izinli.triggered.connect(lambda: self._change_durum(tc, ad, "İzinli"))

        menu.exec(self.table.viewport().mapToGlobal(pos))

    def _change_durum(self, tc, ad, yeni_durum):
        """Personel durumunu değiştir."""
        cevap = QMessageBox.question(
            self, "Durum Değiştir",
            f"{ad} personelinin durumu \"{yeni_durum}\" olarak değiştirilsin mi?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if cevap != QMessageBox.Yes:
            return

        try:
            from database.repository_registry import RepositoryRegistry
            registry = RepositoryRegistry(self._db)
            repo = registry.get("Personel")
            repo.update(tc, {"Durum": yeni_durum})
            logger.info(f"Durum değiştirildi: {tc} → {yeni_durum}")
            self.load_data()
        except Exception as e:
            logger.error(f"Durum değiştirme hatası: {e}")
            QMessageBox.critical(self, "Hata", f"Durum değiştirilemedi:\n{e}")

    def _izin_girisi(self, row_data):
        """İzin girişi sinyali gönder."""
        self.izin_requested.emit(row_data)
