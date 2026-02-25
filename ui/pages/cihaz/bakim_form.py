# -*- coding: utf-8 -*-
"""
Periyodik Bakım Formu
======================
  • Üstte KPI şeridi (Toplam / Planlı / Yapıldı / Gecikmiş / Son Bakım)
  • Sol: filtreler (Durum + Cihaz + Arama) + renk kodlu tablo
  • Sağ: her zaman görünür detay başlığı → buton bar → form container
  • Form toggle yerine kaydırılabilir alanda açılır/kapanır
  • Periyodik bakım planlama (3 ay, 6 ay, 1 yıl otomatik plan oluşturma)
  • Google Drive dosya yükleme desteği
"""
import os
import time
from typing import List, Dict, Any, Optional
from datetime import datetime
from dateutil.relativedelta import relativedelta

from PySide6.QtCore import Qt, QDate, QAbstractTableModel, QModelIndex, Signal, QThread, QUrl
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame,
    QTableView, QSplitter, QHeaderView,
    QGroupBox, QGridLayout,
    QLabel, QLineEdit, QComboBox, QDateEdit, QTextEdit,
    QPushButton, QMenu, QMessageBox, QSizePolicy, QScrollArea,
    QFileDialog, QProgressBar,
)
from PySide6.QtGui import QColor, QDesktopServices

from core.date_utils import to_ui_date
from core.logger import logger
from database.repository_registry import RepositoryRegistry
from database.google.drive import GoogleDriveService
from ui.styles import DarkTheme
from ui.styles.components import STYLES as S
from ui.styles.icons import IconRenderer


# ─────────────────────────────────────────────────────────────
#  Renk sabitleri
# ─────────────────────────────────────────────────────────────
_C = {
    "red":    getattr(DarkTheme, "DANGER",       "#f75f5f"),
    "amber":  getattr(DarkTheme, "WARNING",      "#f5a623"),
    "green":  getattr(DarkTheme, "SUCCESS",      "#3ecf8e"),
    "accent": getattr(DarkTheme, "ACCENT",       "#4f8ef7"),
    "muted":  getattr(DarkTheme, "TEXT_MUTED",   "#5a6278"),
    "surface":getattr(DarkTheme, "SURFACE",      "#13161d"),
    "panel":  getattr(DarkTheme, "PANEL",        "#191d26"),
    "border": getattr(DarkTheme, "BORDER",       "#242938"),
    "text":   getattr(DarkTheme, "TEXT_PRIMARY", "#eef0f5"),
}

_DURUM_COLOR = {
    "Planli":   _C["accent"],
    "Planlı":   _C["accent"],
    "Yapildi":  _C["green"],
    "Yapıldı":  _C["green"],
    "Gecikmis": _C["red"],
    "Gecikmiş": _C["red"],
}


# ─────────────────────────────────────────────────────────────
#  Form Modları
# ─────────────────────────────────────────────────────────────
class FormMode:
    """Form işletim modları."""
    PLAN_CREATION = "plan_creation"      # Yeni bakım planı oluşturma
    EXECUTION_INFO = "execution_info"    # Yapılan bakım bilgisi giriş


# ─────────────────────────────────────────────────────────────
#  Yardımcı Fonksiyonlar
# ─────────────────────────────────────────────────────────────
def ay_ekle(kaynak_tarih: datetime, ay_sayisi: int) -> datetime:
    """Bir tarihe belirtilen ay sayısını ekler."""
    return kaynak_tarih + relativedelta(months=ay_sayisi)


# ─────────────────────────────────────────────────────────────
#  Thread Sınıfları
# ─────────────────────────────────────────────────────────────
class IslemKaydedici(QThread):
    """Bakım kaydı ekleme/güncelleme işlemlerini thread'de yapar."""
    islem_tamam = Signal()
    hata_olustu = Signal(str)

    def __init__(self, db, islem_tipi: str, veri: Any):
        super().__init__()
        self.db = db
        self.tip = islem_tipi  # "INSERT" veya "UPDATE"
        self.veri = veri

    def run(self):
        try:
            repo = RepositoryRegistry(self.db).get("Periyodik_Bakim")
            if self.tip == "INSERT":
                # veri: List[Dict] - birden fazla kayıt
                for kayit in self.veri:
                    repo.insert(kayit)
            elif self.tip == "UPDATE":
                # veri: Dict - tek kayıt güncelleme
                repo.update(self.veri)
            self.islem_tamam.emit()
        except Exception as e:
            logger.error(f"Bakım kaydı işlemi başarısız: {e}")
            self.hata_olustu.emit(str(e))


class DosyaYukleyici(QThread):
    """Google Drive'a dosya yükleme işlemini thread'de yapar."""
    yuklendi = Signal(str)  # webViewLink
    
    def __init__(self, yerel_yol: str, folder_id: Optional[str] = None):
        super().__init__()
        self.yol = yerel_yol
        self.folder_id = folder_id

    def run(self):
        try:
            drive = GoogleDriveService()
            link = drive.upload_file(self.yol, self.folder_id)
            self.yuklendi.emit(link if link else "-")
        except Exception as e:
            logger.error(f"Dosya yükleme hatası: {e}")
            self.yuklendi.emit("-")


# ─────────────────────────────────────────────────────────────
#  Tablo kolonları
# ─────────────────────────────────────────────────────────────
BAKIM_COLUMNS = [
    ("Planid",         "Plan No",      90),
    ("Cihazid",        "Cihaz",        110),
    ("PlanlananTarih", "Plan Tarihi",  100),
    ("BakimTarihi",    "Bakım Tarihi", 100),
    ("BakimPeriyodu",  "Periyot",      110),
    ("BakimTipi",      "Tip",          110),
    ("Teknisyen",      "Teknisyen",    130),
    ("Durum",          "Durum",        100),
]


# ─────────────────────────────────────────────────────────────
#  Form Bileşenleri
# ─────────────────────────────────────────────────────────────
class FormPanel(QGroupBox):
    """Bakım formu için panel widget (arıza_kayıt tarzında)."""
    
    def __init__(self, title: str, parent=None):
        super().__init__(title, parent)
        self.setStyleSheet(S["group"])
        self.layout_main = QGridLayout(self)
        self.layout_main.setContentsMargins(12, 12, 12, 12)
        self.layout_main.setHorizontalSpacing(16)
        self.layout_main.setVerticalSpacing(8)
        self.row_counter = 0
    
    def add_field(self, label_text: str, widget: QWidget, colspan: int = 1):
        """Etiket + widget satırı ekle."""
        lbl = QLabel(label_text)
        lbl.setStyleSheet(S.get("label", "font-weight:600;"))
        self.layout_main.addWidget(lbl, self.row_counter, 0)
        self.layout_main.addWidget(widget, self.row_counter, 1, 1, colspan)
        self.row_counter += 1
    
    def add_row_fields(self, fields: List[tuple]):
        """Aynı satırda birden fazla alan ekle. 
        fields: [(label, widget, colspan), ...]
        """
        col = 0
        for label_text, widget, colspan in fields:
            lbl = QLabel(label_text)
            lbl.setStyleSheet(S.get("label", "font-weight:600;"))
            self.layout_main.addWidget(lbl, self.row_counter, col)
            col += 1
            self.layout_main.addWidget(widget, self.row_counter, col, 1, colspan)
            col += colspan
        self.row_counter += 1
    
    def add_full_width_field(self, label_text: str, widget: QWidget):
        """Tam genişlikte alan ekle."""
        self.add_field(label_text, widget, colspan=3)


# ─────────────────────────────────────────────────────────────
#  Tablo Modeli
# ─────────────────────────────────────────────────────────────


# ─────────────────────────────────────────────────────────────
#  Model
# ─────────────────────────────────────────────────────────────
class BakimTableModel(QAbstractTableModel):
    def __init__(self, rows: Optional[List[Dict[str, Any]]] = None, parent=None):
        super().__init__(parent)
        self._rows    = rows or []
        self._keys    = [c[0] for c in BAKIM_COLUMNS]
        self._headers = [c[1] for c in BAKIM_COLUMNS]

    def rowCount(self, parent=QModelIndex()):    return len(self._rows)
    def columnCount(self, parent=QModelIndex()): return len(BAKIM_COLUMNS)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        row = self._rows[index.row()]
        key = self._keys[index.column()]

        if role == Qt.DisplayRole:
            val = row.get(key, "")
            if key in ("PlanlananTarih", "BakimTarihi"):
                return to_ui_date(val, "")
            return str(val) if val else ""

        if role == Qt.TextAlignmentRole:
            if key in ("PlanlananTarih", "BakimTarihi", "Durum"):
                return Qt.AlignCenter
            return Qt.AlignVCenter | Qt.AlignLeft

        if role == Qt.ForegroundRole and key == "Durum":
            c = _DURUM_COLOR.get(row.get("Durum", ""))
            return QColor(c) if c else None

        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self._headers[section]
        return None

    def set_rows(self, rows: List[Dict[str, Any]]):
        self.beginResetModel()
        self._rows = rows or []
        self.endResetModel()

    def get_row(self, row_idx: int) -> Optional[Dict[str, Any]]:
        if 0 <= row_idx < len(self._rows):
            return self._rows[row_idx]
        return None


# ─────────────────────────────────────────────────────────────
#  Ana Form
# ─────────────────────────────────────────────────────────────
class BakimKayitForm(QWidget):
    """Periyodik Bakım listesi, detay paneli ve kayıt formu."""

    def __init__(self, db=None, cihaz_id: Optional[str] = None, 
                 kullanici_adi: Optional[str] = None, parent=None):
        super().__init__(parent)
        self._db                             = db
        self._cihaz_id                       = cihaz_id
        self._kullanici_adi                  = kullanici_adi
        self._all_rows: List[Dict]           = []
        self._rows: List[Dict]               = []
        self._selected_row: Optional[Dict]   = None
        self._active_form: Optional[QWidget] = None

        self._setup_ui()
        self._load_data()

    # ══════════════════════════════════════════════════════
    #  Dışarıdan erişim
    # ══════════════════════════════════════════════════════
    def set_cihaz_id(self, cihaz_id: Optional[str]):
        self._cihaz_id = cihaz_id
        self.cmb_cihaz_filter.setVisible(not bool(cihaz_id))
        self._load_data()

    # ══════════════════════════════════════════════════════
    #  UI İnşaası
    # ══════════════════════════════════════════════════════
    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_kpi_bar())

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background:{_C['border']};")
        root.addWidget(sep)

        self._h_splitter = QSplitter(Qt.Horizontal)
        self._h_splitter.setStyleSheet(S.get("splitter", ""))
        self._h_splitter.addWidget(self._build_left_panel())
        self._h_splitter.addWidget(self._build_form_panel())   # orta: gizli form
        self._h_splitter.addWidget(self._build_right_panel())
        self._h_splitter.setHandleWidth(0)          # handle görünmez
        self._h_splitter.setChildrenCollapsible(False)
        for i in range(3):
            self._h_splitter.handle(i).setEnabled(False)   # sürükleme kapalı
        self._h_splitter.setSizes([710, 0, 350])
        root.addWidget(self._h_splitter, 1)

    # ── KPI Şeridi ──────────────────────────────────────
    def _build_kpi_bar(self) -> QWidget:
        bar = QWidget()
        bar.setFixedHeight(68)
        bar.setStyleSheet(f"background:{_C['surface']};")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(1)

        self._kpi_labels: Dict[str, QLabel] = {}
        cards = [
            ("toplam",    "TOPLAM BAKIM",  "0",  _C["accent"]),
            ("planli",    "PLANLİ",         "0",  _C["accent"]),
            ("yapildi",   "YAPILDI",        "0",  _C["green"]),
            ("gecikmis",  "GECİKMİŞ",       "0",  _C["red"]),
            ("son_bakim", "SON BAKIM",       "—",  _C["muted"]),
        ]
        for key, title, default, color in cards:
            layout.addWidget(self._make_kpi_card(key, title, default, color), 1)
        return bar

    def _make_kpi_card(self, key: str, title: str, default: str, color: str) -> QWidget:
        card = QWidget()
        card.setStyleSheet(
            f"QWidget{{background:{_C['panel']};border-radius:6px;margin:0 2px;}}"
            f"QWidget:hover{{background:{_C['border']};}}"
        )
        vl = QVBoxLayout(card)
        vl.setContentsMargins(10, 6, 10, 6)
        vl.setSpacing(2)
        lbl_t = QLabel(title)
        lbl_t.setStyleSheet(
            f"font-size:9px;font-weight:600;letter-spacing:0.06em;"
            f"color:{_C['muted']};background:transparent;"
        )
        lbl_v = QLabel(default)
        lbl_v.setStyleSheet(
            f"font-size:18px;font-weight:700;color:{color};background:transparent;"
        )
        vl.addWidget(lbl_t)
        vl.addWidget(lbl_v)
        self._kpi_labels[key] = lbl_v
        return card

    def _update_kpi(self):
        rows = self._all_rows
        if not rows:
            defaults = [("toplam","0"),("planli","0"),("yapildi","0"),
                        ("gecikmis","0"),("son_bakim","—")]
            for k, v in defaults:
                self._kpi_labels[k].setText(v)
            return

        toplam   = len(rows)
        planli   = sum(1 for r in rows if r.get("Durum","") in ("Planli","Planlı"))
        yapildi  = sum(1 for r in rows if r.get("Durum","") in ("Yapildi","Yapıldı"))
        gecikmis = sum(1 for r in rows if r.get("Durum","") in ("Gecikmis","Gecikmiş"))
        tarihler = [r.get("BakimTarihi","") for r in rows if r.get("BakimTarihi")]
        son = to_ui_date(max(tarihler), "") if tarihler else "—"

        self._kpi_labels["toplam"].setText(str(toplam))
        self._kpi_labels["planli"].setText(str(planli))
        self._kpi_labels["yapildi"].setText(str(yapildi))
        self._kpi_labels["gecikmis"].setText(str(gecikmis))
        self._kpi_labels["son_bakim"].setText(son)

    # ── Sol Panel ───────────────────────────────────────
    def _build_left_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Filtre satırı
        filter_bar = QWidget()
        filter_bar.setStyleSheet(
            f"background:{_C['surface']};"
            f"border-bottom:1px solid {_C['border']};"
        )
        fb_l = QHBoxLayout(filter_bar)
        fb_l.setContentsMargins(10, 6, 10, 6)
        fb_l.setSpacing(8)

        self.txt_filter = QLineEdit()
        self.txt_filter.setPlaceholderText("🔍  Plan No, Cihaz, Teknisyen…")
        self.txt_filter.setStyleSheet(S["input"])
        self.txt_filter.setMaximumWidth(230)
        self.txt_filter.textChanged.connect(self._apply_filters)
        fb_l.addWidget(self.txt_filter)

        self.cmb_durum_filter = QComboBox()
        self.cmb_durum_filter.setStyleSheet(S["combo"])
        self.cmb_durum_filter.setFixedWidth(155)
        for lbl, val in [("Tüm Durumlar", None), ("Planli","Planli"),
                          ("Yapildi","Yapildi"), ("Gecikmis","Gecikmis")]:
            self.cmb_durum_filter.addItem(lbl, val)
        self.cmb_durum_filter.currentIndexChanged.connect(self._apply_filters)
        fb_l.addWidget(self.cmb_durum_filter)

        self.cmb_cihaz_filter = QComboBox()
        self.cmb_cihaz_filter.setStyleSheet(S["combo"])
        self.cmb_cihaz_filter.setFixedWidth(150)
        self.cmb_cihaz_filter.addItem("Tüm Cihazlar", None)
        self.cmb_cihaz_filter.currentIndexChanged.connect(self._apply_filters)
        self.cmb_cihaz_filter.setVisible(not bool(self._cihaz_id))
        fb_l.addWidget(self.cmb_cihaz_filter)

        self.cmb_marka_filter = QComboBox()
        self.cmb_marka_filter.setStyleSheet(S["combo"])
        self.cmb_marka_filter.setFixedWidth(130)
        self.cmb_marka_filter.addItem("Tüm Markalar", None)
        self.cmb_marka_filter.currentIndexChanged.connect(self._apply_filters)
        self.cmb_marka_filter.setVisible(not bool(self._cihaz_id))
        fb_l.addWidget(self.cmb_marka_filter)

        fb_l.addStretch()

        self.btn_yeni = QPushButton("+ Yeni Bakım")
        self.btn_yeni.setStyleSheet(S.get("btn_primary", ""))
        self.btn_yeni.clicked.connect(self._open_bakim_form)
        fb_l.addWidget(self.btn_yeni)

        self.btn_toplu = QPushButton("⚡ Toplu Plan")
        self.btn_toplu.setStyleSheet(S.get("btn_primary", ""))
        self.btn_toplu.clicked.connect(self._open_toplu_plan_dialog)
        fb_l.addWidget(self.btn_toplu)

        layout.addWidget(filter_bar)

        # Tablo
        self._model = BakimTableModel()
        self.table = QTableView()
        self.table.setModel(self._model)
        self.table.setSelectionBehavior(QTableView.SelectRows)
        self.table.setSelectionMode(QTableView.SingleSelection)
        self.table.setStyleSheet(S["table"])
        self.table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        for i, (_, _, w) in enumerate(BAKIM_COLUMNS):
            self.table.setColumnWidth(i, w)
        hdr = self.table.horizontalHeader()
        hdr.setStretchLastSection(False)
        hdr.setSectionResizeMode(QHeaderView.Stretch)
        self.table.selectionModel().currentChanged.connect(self._on_row_selected)
        self.table.doubleClicked.connect(self._open_bakim_form_execution)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)
        layout.addWidget(self.table, 1)

        self.lbl_count = QLabel("0 kayıt")
        self.lbl_count.setStyleSheet(
            f"font-size:11px;color:{_C['muted']};padding:4px 10px;"
            f"background:{_C['surface']};border-top:1px solid {_C['border']};"
        )
        layout.addWidget(self.lbl_count)
        
        # Progress bar
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        self.progress.setFixedHeight(4)
        self.progress.setStyleSheet(
            f"background: transparent; border: none; "
            f"QProgressBar::chunk {{ background: {_C['accent']}; }}"
        )
        layout.addWidget(self.progress)
        
        return panel

    # ── Form Panel (Orta - Gizli) ──────────────────────
    def _build_form_panel(self) -> QWidget:
        """
        Tablo ile detay paneli arasında açılan form alanı.
        Başlangıçta gizlidir; _open_bakim_form ile gösterilir.
        """
        surface = getattr(DarkTheme, "SURFACE", "#13161d")
        panel_bg = getattr(DarkTheme, "PANEL",   "#191d26")
        border   = getattr(DarkTheme, "BORDER",  "#242938")
        text_pr  = getattr(DarkTheme, "TEXT_PRIMARY",   "#eef0f5")
        text_sec = getattr(DarkTheme, "TEXT_SECONDARY", "#c8cdd8")

        self._form_panel = QWidget()
        self._form_panel.setVisible(False)
        self._form_panel.setStyleSheet(
            f"background:{surface};"
            f"border-left:1px solid {border};"
            f"border-right:1px solid {border};"
        )
        layout = QVBoxLayout(self._form_panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Kapatma butonu — sağ üstte tek X
        hdr = QWidget()
        hdr.setFixedHeight(30)
        hdr.setStyleSheet(f"background:{surface};border-bottom:1px solid {border};")
        hdr_l = QHBoxLayout(hdr)
        hdr_l.setContentsMargins(0, 0, 6, 0)
        hdr_l.setSpacing(0)
        hdr_l.addStretch()

        btn_kapat = QPushButton("✕")
        btn_kapat.setFixedSize(22, 22)
        btn_kapat.setStyleSheet(
            f"QPushButton{{background:transparent;border:none;"
            f"color:{text_sec};font-size:12px;border-radius:4px;}}"
            f"QPushButton:hover{{background:{border};color:{text_pr};}}"
        )
        btn_kapat.clicked.connect(self._close_form)
        hdr_l.addWidget(btn_kapat)
        layout.addWidget(hdr)

        # Scroll alanı — form widget'ı buraya eklenir
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(S.get("scroll", f"background:{surface};border:none;"))

        self._form_inner = QWidget()
        self._form_inner.setStyleSheet(f"background:{surface};")
        self._form_layout = QVBoxLayout(self._form_inner)
        self._form_layout.setContentsMargins(10, 10, 10, 10)
        self._form_layout.setSpacing(0)
        self._form_layout.addStretch()
        scroll.setWidget(self._form_inner)
        layout.addWidget(scroll, 1)

        return self._form_panel

    # ── Sağ Panel (Detay Başlığı + Buton Bar) ──────────
    def _build_right_panel(self) -> QWidget:
        surface = getattr(DarkTheme, "SURFACE", "#13161d")
        panel_bg = getattr(DarkTheme, "PANEL",   "#191d26")
        border   = getattr(DarkTheme, "BORDER",  "#242938")
        text_pr  = getattr(DarkTheme, "TEXT_PRIMARY",   "#eef0f5")
        text_sec = getattr(DarkTheme, "TEXT_SECONDARY", "#c8cdd8")

        panel = QWidget()
        panel.setStyleSheet(
            f"background:{surface};"
            f"border-left:1px solid {border};"
        )
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # -- Detay Başlığı --
        self._det_header = QWidget()
        self._det_header.setStyleSheet(
            f"background:{panel_bg};"
            f"border-bottom:1px solid {border};"
        )
        dh_layout = QVBoxLayout(self._det_header)
        dh_layout.setContentsMargins(14, 10, 14, 10)
        dh_layout.setSpacing(6)

        self.lbl_det_title = QLabel("— Bir kayıt seçin —")
        self.lbl_det_title.setStyleSheet(
            f"font-size:13px;font-weight:600;color:{text_pr};"
        )
        self.lbl_det_title.setWordWrap(True)
        dh_layout.addWidget(self.lbl_det_title)

        # Meta satırı (Plan · Yapılan · Durum)
        meta_row = QHBoxLayout()
        meta_row.setSpacing(10)
        self.lbl_det_plan   = self._meta_lbl("—")
        self.lbl_det_bakim  = self._meta_lbl("—")
        self.lbl_det_durum  = self._meta_lbl("—")
        for w in [self.lbl_det_plan, self.lbl_det_bakim, self.lbl_det_durum]:
            meta_row.addWidget(w)
        meta_row.addStretch()
        dh_layout.addLayout(meta_row)

        # Alan satırı (Teknisyen + Tip + Periyot)
        fields_row = QHBoxLayout()
        fields_row.setSpacing(16)
        self.fw_teknisyen = self._field_lbl("Teknisyen", "—")
        self.fw_tip       = self._field_lbl("Tip", "—")
        self.fw_periyot   = self._field_lbl("Periyot", "—")
        for w in [self.fw_teknisyen, self.fw_tip, self.fw_periyot]:
            fields_row.addWidget(w)
        fields_row.addStretch()
        dh_layout.addLayout(fields_row)

        # Açıklama
        self.lbl_det_aciklama = QLabel("")
        self.lbl_det_aciklama.setWordWrap(True)
        self.lbl_det_aciklama.setStyleSheet(
            f"font-size:11px;color:{_C['muted']};padding-top:2px;"
        )
        dh_layout.addWidget(self.lbl_det_aciklama)

        layout.addWidget(self._det_header)

        # -- Buton bar --
        btn_bar = QWidget()
        btn_bar.setStyleSheet(
            f"background:{surface};"
            f"border-bottom:1px solid {border};"
        )
        bb_layout = QHBoxLayout(btn_bar)
        bb_layout.setContentsMargins(10, 6, 10, 6)
        bb_layout.setSpacing(8)

        lbl_bakim_title = QLabel("Bakım Kaydı")
        lbl_bakim_title.setStyleSheet(
            f"font-size:11px;font-weight:600;color:{text_sec};"
        )
        bb_layout.addWidget(lbl_bakim_title)
        bb_layout.addStretch()

        self.btn_kayit_ekle = QPushButton("+ Kayıt Ekle")
        self.btn_kayit_ekle.setStyleSheet(S.get("btn_secondary", S.get("btn_primary", "")))
        self.btn_kayit_ekle.setEnabled(False)
        self.btn_kayit_ekle.clicked.connect(self._open_bakim_form)
        bb_layout.addWidget(self.btn_kayit_ekle)

        layout.addWidget(btn_bar)
        layout.addStretch()
        
        return panel

    # ── Yardımcı widget üreticileri ─────────────────────
    def _meta_lbl(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet(
            f"font-size:11px;color:{_C['muted']};background:{_C['panel']};"
        )
        return lbl

    def _field_lbl(self, title: str, value: str) -> QWidget:
        w = QWidget()
        w.setStyleSheet(f"background:{_C['panel']};")
        vl = QVBoxLayout(w)
        vl.setContentsMargins(0, 0, 0, 0)
        vl.setSpacing(1)
        t = QLabel(title.upper())
        t.setStyleSheet(
            f"font-size:9px;letter-spacing:0.06em;color:{_C['muted']};font-weight:600;"
        )
        v = QLabel(value)
        v.setObjectName("val")
        v.setStyleSheet(f"font-size:12px;color:{_C['text']};")
        v.setWordWrap(True)
        vl.addWidget(t)
        vl.addWidget(v)
        return w

    @staticmethod
    def _set_field(widget: QWidget, value: str):
        lbl = widget.findChild(QLabel, "val")
        if lbl:
            lbl.setText(value or "—")

    # ══════════════════════════════════════════════════════
    #  Veri yükleme & filtreleme
    # ══════════════════════════════════════════════════════
    def _load_data(self):
        if not self._db:
            self._all_rows = []
            self._rows = []
            self._model.set_rows([])
            self.lbl_count.setText("0 kayıt")
            self._update_kpi()
            return
        try:
            repo = RepositoryRegistry(self._db).get("Periyodik_Bakim")
            rows = repo.get_all()
            if self._cihaz_id:
                rows = [r for r in rows
                        if str(r.get("Cihazid","")) == str(self._cihaz_id)]
            rows.sort(key=lambda r: (r.get("PlanlananTarih") or ""), reverse=True)
            self._all_rows = rows
            self._refresh_cihaz_filter()
            self._update_kpi()
            self._apply_filters()
            if rows:
                self.table.selectRow(0)
        except Exception as e:
            logger.error(f"Bakım kayıtları yüklenemedi: {e}")
            self._all_rows = []
            self._model.set_rows([])
            self.lbl_count.setText("0 kayıt")

    def _refresh_cihaz_filter(self):
        self.cmb_cihaz_filter.blockSignals(True)
        self.cmb_cihaz_filter.clear()
        self.cmb_cihaz_filter.addItem("Tüm Cihazlar", None)
        cihazlar = sorted({
            str(r.get("Cihazid","")) for r in self._all_rows if r.get("Cihazid")
        })
        for c in cihazlar:
            self.cmb_cihaz_filter.addItem(c, c)
        self.cmb_cihaz_filter.blockSignals(False)
        self._refresh_marka_filter()

    def _refresh_marka_filter(self):
        """Marka filtresi seçeneklerini güncelle."""
        self.cmb_marka_filter.blockSignals(True)
        self.cmb_marka_filter.clear()
        self.cmb_marka_filter.addItem("Tüm Markalar", None)
        markalar = sorted({
            str(r.get("Marka","")) for r in self._all_rows if r.get("Marka")
        })
        for m in markalar:
            if m and m != "None":
                self.cmb_marka_filter.addItem(m, m)
        self.cmb_marka_filter.blockSignals(False)

    def _apply_filters(self):
        filtered = list(self._all_rows)

        sel_durum = self.cmb_durum_filter.currentData()
        if sel_durum:
            filtered = [r for r in filtered if r.get("Durum","") == sel_durum]

        if not self._cihaz_id:
            sel_cihaz = self.cmb_cihaz_filter.currentData()
            if sel_cihaz:
                filtered = [r for r in filtered
                            if str(r.get("Cihazid","")) == sel_cihaz]

            sel_marka = self.cmb_marka_filter.currentData()
            if sel_marka:
                filtered = [r for r in filtered
                            if str(r.get("Marka","")) == sel_marka]

        txt = self.txt_filter.text().strip().lower()
        if txt:
            filtered = [
                r for r in filtered
                if txt in str(r.get("Planid","")).lower()
                or txt in str(r.get("Cihazid","")).lower()
                or txt in str(r.get("Teknisyen","")).lower()
                or txt in str(r.get("BakimPeriyodu","")).lower()
            ]

        self._rows = filtered
        self._model.set_rows(filtered)
        self.lbl_count.setText(f"{len(filtered)} kayıt")

    # ══════════════════════════════════════════════════════
    #  Satır seçimi → Detay paneli
    # ══════════════════════════════════════════════════════
    def _on_row_selected(self, current, _previous):
        if not current.isValid():
            return
        row = self._model.get_row(current.row())
        if not row:
            return
        self._selected_row = row
        self._update_detail(row)
        self.btn_kayit_ekle.setEnabled(True)

    def _update_detail(self, row: Dict):
        cihaz   = row.get("Cihazid","")
        periyot = row.get("BakimPeriyodu","")
        self.lbl_det_title.setText(f"{cihaz}  —  {periyot}")

        self.lbl_det_plan.setText(
            f"📅 Plan: {to_ui_date(row.get('PlanlananTarih',''), '')}"
        )
        self.lbl_det_bakim.setText(
            f"🔧 Yapılan: {to_ui_date(row.get('BakimTarihi',''), '')}"
        )

        durum = row.get("Durum","")
        dur_c = _DURUM_COLOR.get(durum, _C["muted"])
        self.lbl_det_durum.setText(f"● {durum}" if durum else "—")
        self.lbl_det_durum.setStyleSheet(
            f"font-size:11px;font-weight:700;color:{dur_c};"
            f"background:{_C['panel']};"
        )

        self._set_field(self.fw_teknisyen, row.get("Teknisyen",""))
        self._set_field(self.fw_tip,       row.get("BakimTipi",""))
        self._set_field(self.fw_periyot,   row.get("BakimPeriyodu",""))

        aciklama = (row.get("YapilanIslemler","") or
                    row.get("Aciklama","") or "")
        if len(aciklama) > 200:
            aciklama = aciklama[:200] + "…"
        self.lbl_det_aciklama.setText(aciklama)

    # ══════════════════════════════════════════════════════
    #  Form Açma / Kapama
    # ══════════════════════════════════════════════════════
    def _clear_form_container(self):
        while self._form_layout.count() > 1:
            item = self._form_layout.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)
        if self._active_form is not None:
            self._active_form.setParent(None)
            self._active_form = None

    def _open_bakim_form(self):
        self._clear_form_container()
        form = _BakimGirisForm(
            self._db, 
            self._cihaz_id, 
            kullanici_adi=self._kullanici_adi,
            mode=FormMode.PLAN_CREATION,
            parent=self
        )
        form.saved.connect(self._on_bakim_saved)
        self._active_form = form
        self._form_layout.insertWidget(0, form)
        self._form_panel.setVisible(True)
        self._h_splitter.setSizes([470, 360, 350])

    def _open_bakim_form_execution(self, index):
        """Seçilen plan için bilgi giriş formunu aç (EXECUTION_INFO modu)."""
        if not self._selected_row:
            return
        self._clear_form_container()
        form = _BakimGirisForm(
            self._db,
            self._cihaz_id,
            kullanici_adi=self._kullanici_adi,
            mode=FormMode.EXECUTION_INFO,
            plan_data=self._selected_row,
            parent=self
        )
        form.saved.connect(self._on_bakim_saved)
        self._active_form = form
        self._form_layout.insertWidget(0, form)
        self._form_panel.setVisible(True)
        self._h_splitter.setSizes([470, 360, 350])

    def _close_form(self):
        self._clear_form_container()
        self._form_panel.setVisible(False)
        self._h_splitter.setSizes([710, 0, 350])

    # ══════════════════════════════════════════════════════
    #  Geri çağrılar
    # ══════════════════════════════════════════════════════
    def _on_bakim_saved(self):
        self._close_form()
        self.progress.setVisible(True)
        self.progress.setRange(0, 0)
        self._load_data()
        self.progress.setVisible(False)

    # ══════════════════════════════════════════════════════
    #  Sağ tık menüsü
    # ══════════════════════════════════════════════════════
    def _show_context_menu(self, pos):
        index = self.table.indexAt(pos)
        if not index.isValid():
            return
        menu = QMenu(self)
        act = menu.addAction("Yeni Bakım Kaydı Ekle")
        if menu.exec(self.table.mapToGlobal(pos)) == act:
            self._open_bakim_form()

    def _open_toplu_plan_dialog(self):
        """Toplu cihaz bakım planlaması dialogunu açar."""
        dialog = TopluBakimPlanDialog(self._db, parent=self)
        if dialog.exec():
            # Planlama başarılı olursa verileri yenile
            self._load_data()
            QMessageBox.information(
                self,
                "Başarılı",
                f"Toplu bakım planlaması {dialog.toplam_plan} plan olacak şekilde oluşturuldu."
            )


# ─────────────────────────────────────────────────────────────
#  Toplu Bakım Planlama Dialog'u
# ─────────────────────────────────────────────────────────────
class TopluBakimPlanDialog(QWidget):
    """Birden fazla cihaz için toplu bakım planlaması."""

    def __init__(self, db=None, parent=None):
        super().__init__(parent)
        self._db = db
        self.toplam_plan = 0
        self._setup_ui()
        self.exec()

    def _setup_ui(self):
        """Dialog UI'ı oluştur."""
        from PySide6.QtWidgets import QDialog, QListWidget, QListWidgetItem, QCheckBox
        
        dialog = QDialog(self.parent())
        dialog.setWindowTitle("⚡ Toplu Bakım Planlaması")
        dialog.setMinimumWidth(500)
        dialog.setMinimumHeight(450)
        
        layout = QVBoxLayout(dialog)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        # Başlık
        title = QLabel("Toplu Bakım Planı Oluştur")
        title.setStyleSheet(
            f"font-size:14px;font-weight:bold;color:{_C['accent']};"
        )
        layout.addWidget(title)

        # Cihaz Seçimi
        lbl_cihaz = QLabel("Cihazlar Seçin:")
        lbl_cihaz.setStyleSheet(f"font-weight:600;color:{_C['text']};")
        layout.addWidget(lbl_cihaz)

        # Cihaz listesi
        self.list_cihazlar = QListWidget()
        self.list_cihazlar.setStyleSheet(S.get("list", ""))
        self.list_cihazlar.setMaximumHeight(200)
        
        try:
            repo = RepositoryRegistry(self._db).get("cihaz")
            tum_cihazlar = repo.get_all() or []
            for cihaz in tum_cihazlar:
                c_id = cihaz.get("CihazID", "")
                c_ad = cihaz.get("CihazAd", "")
                c_marka = cihaz.get("Marka", "")
                if c_id:
                    item = QListWidgetItem(f"{c_id} - {c_ad} ({c_marka})")
                    item.setData(Qt.UserRole, c_id)
                    item.setCheckState(Qt.Unchecked)
                    self.list_cihazlar.addItem(item)
        except Exception as e:
            logger.error(f"Cihaz listesi yüklenemedi: {e}")
        
        self.list_cihazlar.setSelectionMode(QListWidget.MultiSelection)
        layout.addWidget(self.list_cihazlar)

        # Plan Tipi Seçimi
        lbl_plan = QLabel("Bakım Planı Türü:")
        lbl_plan.setStyleSheet(f"font-weight:600;color:{_C['text']};")
        layout.addWidget(lbl_plan)

        self.cmb_plan_tipi = QComboBox()
        self.cmb_plan_tipi.setStyleSheet(S["combo"])
        self.cmb_plan_tipi.setMinimumHeight(36)
        self.cmb_plan_tipi.addItems([
            "📌 Tek Seferlik",
            "🔄 3 Ay (4 Plan)",
            "⏱️  6 Ay (2 Plan)",
            "📆 1 Yıl (1 Plan)"
        ])
        layout.addWidget(self.cmb_plan_tipi)

        # Tarih Seçimi
        lbl_tarih = QLabel("Başlangıç Tarihi:")
        lbl_tarih.setStyleSheet(f"font-weight:600;color:{_C['text']};")
        layout.addWidget(lbl_tarih)

        self.dt_baslangic = QDateEdit(QDate.currentDate())
        self.dt_baslangic.setCalendarPopup(True)
        self.dt_baslangic.setDisplayFormat("dddd, d MMMM yyyy")
        self.dt_baslangic.setStyleSheet(S["date"])
        self.dt_baslangic.setMinimumHeight(36)
        layout.addWidget(self.dt_baslangic)

        # Açıklama
        lbl_acik = QLabel("Bakım Açıklaması (isteğe bağlı):")
        lbl_acik.setStyleSheet(f"font-weight:600;color:{_C['text']};")
        layout.addWidget(lbl_acik)

        self.txt_aciklama = QLineEdit()
        self.txt_aciklama.setStyleSheet(S["input"])
        self.txt_aciklama.setPlaceholderText("Periyodik rutin bakım, ...")
        self.txt_aciklama.setMinimumHeight(36)
        layout.addWidget(self.txt_aciklama)

        layout.addStretch()

        # Butonlar
        btn_layout = QHBoxLayout()
        btn_iptal = QPushButton("❌ İptal")
        btn_iptal.setMinimumHeight(38)
        btn_iptal.setStyleSheet(
            f"QPushButton{{background:{_C['panel']};border:1px solid {_C['border']};"
            f"border-radius:6px;color:{_C['text']};font-weight:bold;}}"
        )
        btn_iptal.clicked.connect(dialog.reject)
        btn_layout.addWidget(btn_iptal)

        btn_layout.addStretch()

        btn_oluştur = QPushButton("✅ Planları Oluştur")
        btn_oluştur.setMinimumHeight(38)
        btn_oluştur.setMinimumWidth(120)
        btn_oluştur.setStyleSheet(
            f"QPushButton{{background:{_C['green']};border:none;"
            f"border-radius:6px;color:white;font-weight:bold;font-size:12px;}}"
            f"QPushButton:hover{{background:#2e7d32;}}"
        )
        btn_oluştur.clicked.connect(lambda: self._olustur_planlar(dialog))
        btn_layout.addWidget(btn_oluştur)

        layout.addLayout(btn_layout)

        dialog.setLayout(layout)
        self.dialog = dialog

    def exec(self):
        """Dialog'u göster."""
        return self.dialog.exec()

    def _olustur_planlar(self, dialog):
        """Seçilen cihazlar için bakım planlarını oluştur."""
        secili_cihazlar = [
            self.list_cihazlar.item(i).data(Qt.UserRole)
            for i in range(self.list_cihazlar.count())
            if self.list_cihazlar.item(i).checkState() == Qt.Checked
        ]

        if not secili_cihazlar:
            QMessageBox.warning(dialog, "Uyarı", "Lütfen en az bir cihaz seçin.")
            return

        plan_tipi = self.cmb_plan_tipi.currentText()
        baslangic_tarih = self.dt_baslangic.date().toPython()
        aciklama = self.txt_aciklama.text().strip() or "Periyodik Bakım"

        # Plan parametreleri
        tekrar = 1
        ay_artis = 0
        if "3 Ay" in plan_tipi:
            tekrar, ay_artis = 4, 3
        elif "6 Ay" in plan_tipi:
            tekrar, ay_artis = 2, 6
        elif "1 Yıl" in plan_tipi:
            tekrar, ay_artis = 1, 12

        base_id = int(time.time())
        kayitlar = []
        
        for cihaz_id in secili_cihazlar:
            for i in range(tekrar):
                yeni_tarih = ay_ekle(baslangic_tarih, i * ay_artis)
                tarih_str = yeni_tarih.strftime("%Y-%m-%d")

                kayit = {
                    "Planid":          f"{cihaz_id}-BK-{base_id + i}",
                    "Cihazid":         cihaz_id,
                    "BakimPeriyodu":   plan_tipi.split("(")[0].strip(),
                    "BakimSirasi":     f"{i+1}. Bakım",
                    "PlanlananTarih":  tarih_str,
                    "Bakim":           aciklama,
                    "Durum":           "Planli",
                    "BakimTarihi":     "",
                    "BakimTipi":       "Periyodik",
                    "YapilanIslemler": "-",
                    "Aciklama":        aciklama,
                    "Teknisyen":       "-",
                    "Rapor":           "-",
                }
                kayitlar.append(kayit)

        # Veritabanına kaydet
        try:
            repo = RepositoryRegistry(self._db).get("Periyodik_Bakim")
            for kayit in kayitlar:
                repo.insert(kayit)
            self.toplam_plan = len(kayitlar)
            dialog.accept()
        except Exception as e:
            logger.error(f"Toplu planlama başarısız: {e}")
            QMessageBox.critical(dialog, "Hata", f"Planlama başarısız: {e}")



class _BakimGirisForm(QWidget):
    saved = Signal()

    def __init__(self, db=None, cihaz_id: Optional[str] = None, 
                 kullanici_adi: Optional[str] = None, 
                 mode: str = FormMode.PLAN_CREATION,
                 plan_data: Optional[Dict] = None,
                 parent=None):
        super().__init__(parent)
        self._db              = db
        self._cihaz_id        = cihaz_id
        self._kullanici_adi   = kullanici_adi
        self._mode            = mode
        self._plan_data       = plan_data or {}
        self._secilen_dosya   = None
        self._mevcut_link     = None
        self._drive_folder_id = None
        self._setup_ui()
        
        # Moda göre alanları etkinleştir/devre dışı bırak
        self._set_mode_ui()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(12)

        # ═══════════════════════════════════════════════════════
        #  1. BAKIM PLANI SEÇİMİ
        # ═══════════════════════════════════════════════════════
        panel_plan = self._create_panel("📅 Bakım Planı Seçimi")
        
        self.cmb_periyot_plan = QComboBox()
        self.cmb_periyot_plan.setStyleSheet(S["combo"])
        self.cmb_periyot_plan.addItems([
            "📌 Tek Seferlik",
            "🔄 3 Ay (Otomatik 4 Plan)",
            "⏱️  6 Ay (Otomatik 2 Plan)", 
            "📆 1 Yıl (Tek Plan)"
        ])
        self.cmb_periyot_plan.setMinimumHeight(40)
        self.cmb_periyot_plan.currentIndexChanged.connect(self._periyot_plan_degisti)
        panel_plan.add_field("Plan Türü", self.cmb_periyot_plan)
        
        root.addWidget(panel_plan)

        # ═══════════════════════════════════════════════════════
        #  2. BAKIM TARIH & TİP BİLGİLERİ
        # ═══════════════════════════════════════════════════════
        panel_tarih = self._create_panel("📋 Bakım Bilgileri")
        
        # Planlanan Tarih
        self.dt_plan = QDateEdit(QDate.currentDate())
        self.dt_plan.setCalendarPopup(True)
        self.dt_plan.setDisplayFormat("ddd, d MMMM yyyy")
        self.dt_plan.setStyleSheet(S["date"])
        self.dt_plan.setMinimumHeight(36)
        panel_tarih.add_field("📅 Planlanan Tarih", self.dt_plan)
        
        # Bakım Tipi
        self.txt_tip = QLineEdit()
        self.txt_tip.setStyleSheet(S["input"])
        self.txt_tip.setPlaceholderText("Örn: Periyodik, Rutin, Acil, İyileştirme")
        self.txt_tip.setMinimumHeight(36)
        panel_tarih.add_field("🔧 Bakım Tipi", self.txt_tip)
        
        # Bakım Periyodu
        self.txt_periyot = QLineEdit()
        self.txt_periyot.setStyleSheet(S["input"])
        self.txt_periyot.setPlaceholderText("3 Ay, 6 Ay, 1 Yıl")
        self.txt_periyot.setReadOnly(True)
        self.txt_periyot.setMinimumHeight(36)
        panel_tarih.add_field("⏰ Bakım Periyodu", self.txt_periyot)
        
        # Bakım Sırası
        self.txt_sira = QLineEdit()
        self.txt_sira.setStyleSheet(S["input"])
        self.txt_sira.setReadOnly(True)
        self.txt_sira.setMinimumHeight(36)
        panel_tarih.add_field("🔢 Bakım Sırası", self.txt_sira)
        
        # Bakım Açıklaması
        self.txt_bakim = QLineEdit()
        self.txt_bakim.setStyleSheet(S["input"])
        self.txt_bakim.setPlaceholderText("Bakım hakkında kısa açıklama (isteğe bağlı)")
        self.txt_bakim.setMinimumHeight(36)
        panel_tarih.add_full_width_field("💬 Bakım Açıklaması", self.txt_bakim)
        
        root.addWidget(panel_tarih)

        # ═══════════════════════════════════════════════════════
        #  3. İŞLEM DETAYLARI (Yapılan İşlemler, Durumu)
        # ═══════════════════════════════════════════════════════
        self._panel_islem = self._create_panel("🔨 İşlem Detayları")
        
        # Durum
        self.cmb_durum = QComboBox()
        self.cmb_durum.setStyleSheet(S["combo"])
        self.cmb_durum.addItems(["Planli", "Yapildi", "Gecikmis"])
        self.cmb_durum.setMinimumHeight(36)
        self.cmb_durum.currentTextChanged.connect(self._durum_kontrol)
        self._panel_islem.add_field("✓ Bakım Durumu", self.cmb_durum)
        
        # Bakım Tarihi
        self.dt_bakim = QDateEdit(QDate.currentDate())
        self.dt_bakim.setCalendarPopup(True)
        self.dt_bakim.setDisplayFormat("ddd, d MMMM yyyy")
        self.dt_bakim.setStyleSheet(S["date"])
        self.dt_bakim.setMinimumHeight(36)
        self._panel_islem.add_field("✔️ Bakım Yapılan Tarih", self.dt_bakim)
        
        # Yapılan İşlemler
        self.txt_islemler = QTextEdit()
        self.txt_islemler.setStyleSheet(S["input_text"])
        self.txt_islemler.setFixedHeight(80)
        self.txt_islemler.setPlaceholderText("✓ İşlem 1: ...\n✓ İşlem 2: ...\n✓ Ölçüm: ...")
        self._panel_islem.add_full_width_field("🛠️  Yapılan İşlemler ve Ölçümler", self.txt_islemler)
        
        # Açıklama / Notlar
        self.txt_aciklama = QTextEdit()
        self.txt_aciklama.setStyleSheet(S["input_text"])
        self.txt_aciklama.setFixedHeight(70)
        self.txt_aciklama.setPlaceholderText("Ek notlar, sorunlar, öneriler...")
        self._panel_islem.add_full_width_field("📝 Not / Açıklamalar", self.txt_aciklama)
        
        root.addWidget(self._panel_islem)

        # ═══════════════════════════════════════════════════════
        #  4. TEKNİSYEN & RAPOR BİLGİLERİ
        # ═══════════════════════════════════════════════════════
        self._panel_teknis = self._create_panel("👤 Sorumlular & Belgeler")
        
        # Teknisyen
        self.txt_teknisyen = QLineEdit()
        self.txt_teknisyen.setStyleSheet(S["input"])
        self.txt_teknisyen.setPlaceholderText("Teknisyen adı ve soyadı")
        self.txt_teknisyen.setMinimumHeight(36)
        if self._kullanici_adi:
            self.txt_teknisyen.setText(str(self._kullanici_adi))
        self._panel_teknis.add_field("👨‍🔧 Teknisyen Adı", self.txt_teknisyen)
        
        # Rapor / Dosya Yükleme
        file_container = QWidget()
        file_layout = QHBoxLayout(file_container)
        file_layout.setContentsMargins(0, 0, 0, 0)
        file_layout.setSpacing(8)
        
        self.lbl_dosya = QLabel("📋 Rapor Yok")
        self.lbl_dosya.setStyleSheet(
            f"color:{_C['muted']};font-style:italic;padding:8px 12px;"
            f"background:{_C['panel']};border-radius:4px;border:1px dashed {_C['border']};"
        )
        file_layout.addWidget(self.lbl_dosya, 1)
        
        self.btn_dosya_ac = QPushButton("📥 Aç")
        self.btn_dosya_ac.setVisible(False)
        self.btn_dosya_ac.setFixedSize(70, 36)
        self.btn_dosya_ac.setStyleSheet(
            f"QPushButton{{background:{_C['accent']};border-radius:4px;"
            f"color:white;font-weight:bold;}}"
            f"QPushButton:hover{{background:{_C['accent']}dd;}}"
        )
        self.btn_dosya_ac.clicked.connect(self._dosyayi_ac)
        file_layout.addWidget(self.btn_dosya_ac)
        
        btn_dosya_sec = QPushButton("📤 Seç & Yükle")
        btn_dosya_sec.setFixedSize(110, 36)
        btn_dosya_sec.setStyleSheet(
            f"QPushButton{{background:{_C['panel']};border:1px solid {_C['accent']};"
            f"border-radius:4px;color:{_C['text']};font-weight:bold;}}"
            f"QPushButton:hover{{background:{_C['border']};}}"
        )
        btn_dosya_sec.clicked.connect(self._dosya_sec)
        file_layout.addWidget(btn_dosya_sec)
        
        self._panel_teknis.add_field("📄 Bakım Raporu", file_container)
        root.addWidget(self._panel_teknis)

        # ═══════════════════════════════════════════════════════
        #  Progress Bar
        # ═══════════════════════════════════════════════════════
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        self.progress.setFixedHeight(4)
        self.progress.setStyleSheet(
            f"background: transparent; border: none; "
            f"QProgressBar::chunk {{ background: {_C['accent']}; }}"
        )
        root.addWidget(self.progress)

        # ═══════════════════════════════════════════════════════
        #  Butonlar (Alt)
        # ═══════════════════════════════════════════════════════
        btn_container = QWidget()
        btn_container.setStyleSheet(
            f"background:{_C['surface']};border-top:1px solid {_C['border']};"
            f"border-radius:0px;padding:12px;"
        )
        btns = QHBoxLayout(btn_container)
        btns.setContentsMargins(8, 8, 8, 8)
        btns.setSpacing(8)
        
        btn_temizle = QPushButton("🗑️  Temizle")
        btn_temizle.setMinimumHeight(38)
        btn_temizle.setMinimumWidth(100)
        btn_temizle.setStyleSheet(
            f"QPushButton{{background:{_C['panel']};border:1px solid {_C['border']};"
            f"border-radius:6px;color:{_C['text']};font-weight:bold;font-size:12px;}}"
            f"QPushButton:hover{{background:{_C['border']};}}"
            f"QPushButton:pressed{{background:{_C['muted']};}}"
        )
        btn_temizle.clicked.connect(self._clear)
        btns.addWidget(btn_temizle)
        
        btns.addStretch()
        
        btn_kaydet = QPushButton("💾 Bakımı Kaydet")
        btn_kaydet.setMinimumHeight(38)
        btn_kaydet.setMinimumWidth(140)
        btn_kaydet.setStyleSheet(
            f"QPushButton{{background:{_C['green']};border:none;"
            f"border-radius:6px;color:white;font-weight:bold;font-size:12px;}}"
            f"QPushButton:hover{{background:#2e7d32;}}"
            f"QPushButton:pressed{{background:#1b5e20;}}"
        )
        try:
            IconRenderer.set_button_icon(
                btn_kaydet, "save", color="white", size=14
            )
        except Exception:
            pass
        btn_kaydet.clicked.connect(self._save)
        btns.addWidget(btn_kaydet)
        
        root.addWidget(btn_container)
        root.addStretch()

    def _create_panel(self, title: str) -> FormPanel:
        """Panel oluşturur."""
        return FormPanel(title)

    def _set_mode_ui(self):
        """Forma göre alanları etkinleştir/devre dışı bırak."""
        if self._mode == FormMode.PLAN_CREATION:
            # PLAN OLUŞTURMA MODU
            # Sadece planlama alanları görünür
            self.cmb_periyot_plan.setEnabled(True)
            self.dt_plan.setEnabled(True)
            self.txt_tip.setEnabled(True)
            self.txt_bakim.setEnabled(True)
            
            # İşlem detayları ve sorumlular panellerini gizle
            self._panel_islem.setVisible(False)
            self._panel_teknis.setVisible(False)
            
        elif self._mode == FormMode.EXECUTION_INFO:
            # BİLGİ GİRİŞ MODU (Seçilen plan için)
            # Plan bilgileri salt okunur
            self.cmb_periyot_plan.setEnabled(False)
            self.txt_periyot.setEnabled(False)
            self.txt_sira.setEnabled(False)
            self.dt_plan.setEnabled(False)
            self.txt_bakim.setEnabled(False)
            self.txt_tip.setEnabled(False)
            # Yapılan bilgisi aktif
            self.cmb_durum.setEnabled(True)
            self.dt_bakim.setEnabled(True)
            self.txt_islemler.setEnabled(True)
            self.txt_aciklama.setEnabled(True)
            self.txt_teknisyen.setEnabled(True)
            
            # İşlem detayları ve sorumlular panellerini göster
            self._panel_islem.setVisible(True)
            self._panel_teknis.setVisible(True)
            
            # Plan verilerini doldur
            self._load_plan_data()

    def _load_plan_data(self):
        """Seçilen plan verilerini forma doldurur."""
        if not self._plan_data:
            return
        # Periyot bilgileri
        self.txt_periyot.setText(self._plan_data.get("BakimPeriyodu", ""))
        self.txt_sira.setText(self._plan_data.get("BakimSirasi", ""))
        dt_str = self._plan_data.get("PlanlananTarih", "")
        if dt_str:
            self.dt_plan.setDate(QDate.fromString(dt_str, "yyyy-MM-dd"))
        self.txt_tip.setText(self._plan_data.get("BakimTipi", ""))
        # Mevcut değerler varsa doldur
        self.txt_teknisyen.setText(self._plan_data.get("Teknisyen", 
                                                        self._kullanici_adi or ""))
        self.txt_aciklama.setPlainText(self._plan_data.get("Aciklama", ""))
        # Rapor linki
        rapor = self._plan_data.get("Rapor", "")
        if rapor and "http" in rapor:
            self._mevcut_link = rapor
            self.lbl_dosya.setText("📥 Mevcut Rapor")
            self.btn_dosya_ac.setVisible(True)

    def _periyot_plan_degisti(self):
        """Periyodik plan seçimi değiştiğinde periyot alanını otomatik doldurur."""
        secim = self.cmb_periyot_plan.currentText()
        if "3 Ay" in secim:
            self.txt_periyot.setText("3 Ay")
            self.txt_sira.setText("1. Bakım")
        elif "6 Ay" in secim:
            self.txt_periyot.setText("6 Ay")
            self.txt_sira.setText("1. Bakım")
        elif "1 Yıl" in secim:
            self.txt_periyot.setText("1 Yıl")
            self.txt_sira.setText("1. Bakım")
        else:  # Tek Seferlik
            self.txt_periyot.setText("Tek Seferlik")
            self.txt_sira.setText("1. Bakım")

    def _durum_kontrol(self):
        """Durum değiştiğinde gerekli alanları kontrol eder."""
        durum = self.cmb_durum.currentText()
        if durum == "Yapildi":
            self.lbl_dosya.setText("✨ Rapor Yükleyiniz (Yapıldı Durumu)")
            self.lbl_dosya.setStyleSheet(
                f"color:white;font-weight:bold;font-style:italic;padding:8px 12px;"
                f"background:{_C['amber']};border-radius:4px;border:1px solid {_C['amber']};"
            )
            self.txt_aciklama.setPlaceholderText("⚠️  Yapıldı durumunda açıklama mutlaka giriniz!")
            self.txt_aciklama.setStyleSheet(
                S["input_text"] + f"QTextEdit{{border:2px solid {_C['amber']};}}"
            )
        else:
            if not self._mevcut_link:
                self.lbl_dosya.setText("📋 Rapor Gerekmiyor")
                self.lbl_dosya.setStyleSheet(
                    f"color:{_C['muted']};font-style:italic;padding:8px 12px;"
                    f"background:{_C['panel']};border-radius:4px;border:1px dashed {_C['border']};"
                )
            self.txt_aciklama.setPlaceholderText("Ek notlar, sorunlar, öneriler...")
            self.txt_aciklama.setStyleSheet(S["input_text"])

    def _dosya_sec(self):
        """Dosya seçme dialogunu açar."""
        yol, _ = QFileDialog.getOpenFileName(
            self, 
            "Bakım Raporu Seç", 
            "", 
            "Belgeler (*.pdf *.doc *.docx);;Resimler (*.jpg *.png *.jpeg);;Tüm Dosyalar (*.*)"
        )
        if yol:
            self._secilen_dosya = yol
            dosya_adi = os.path.basename(yol)
            dosya_boyut = os.path.getsize(yol) / 1024  # KB cinsinden
            self.lbl_dosya.setText(f"✅ {dosya_adi} ({dosya_boyut:.0f} KB)")
            self.lbl_dosya.setStyleSheet(
                f"color:white;font-weight:bold;padding:8px 12px;"
                f"background:{_C['green']};border-radius:4px;border:1px solid {_C['green']};"
            )

    def _dosyayi_ac(self):
        """Mevcut rapor linkini açar."""
        if self._mevcut_link:
            QDesktopServices.openUrl(QUrl(self._mevcut_link))

    def _save(self):
        if not self._db:
            QMessageBox.warning(self, "Uyarı", "Veritabanı bağlantısı yok.")
            return
        if not self._cihaz_id:
            QMessageBox.warning(self, "Uyarı", "Cihaz seçili değil.")
            return

        # Progress başlat
        self.progress.setVisible(True)
        self.progress.setRange(0, 0)  # Indeterminate

        # Dosya varsa önce yükle
        if self._secilen_dosya:
            self.uploader = DosyaYukleyici(self._secilen_dosya, self._drive_folder_id)
            self.uploader.yuklendi.connect(self._dosya_yuklendi)
            self.uploader.start()
        else:
            # Dosya yoksa direkt kaydet
            self._kaydet_devam("-")

    def _dosya_yuklendi(self, link: str):
        """Dosya yükleme bitince kayıt işlemine devam eder."""
        self._kaydet_devam(link)

    def _kaydet_devam(self, dosya_link: str):
        """Bakım kayıtlarını oluşturur ve veritabanına kaydeder."""
        # Mevcut link varsa onu kullan
        if dosya_link == "-" and self._mevcut_link:
            dosya_link = self._mevcut_link

        # Form verilerini al
        periyot_secim = self.cmb_periyot_plan.currentText()
        periyot = self.txt_periyot.text().strip()
        tarih = self.dt_plan.date().toPython()
        durum = self.cmb_durum.currentText().strip()
        yapilan = self.txt_islemler.toPlainText().strip()
        aciklama = self.txt_aciklama.toPlainText().strip()
        teknisyen = self.txt_teknisyen.text().strip()
        bakim_tarihi = self.dt_bakim.date().toString("yyyy-MM-dd") if durum == "Yapildi" else ""
        bakim = self.txt_bakim.text().strip()
        tip = self.txt_tip.text().strip() or "Periyodik"

        # Periyodik plan sayısını ve ay artışını belirle
        tekrar = 1
        ay_artis = 0
        if "3 Ay" in periyot_secim:
            tekrar, ay_artis = 4, 3
        elif "6 Ay" in periyot_secim:
            tekrar, ay_artis = 2, 6
        elif "1 Yıl" in periyot_secim:
            tekrar, ay_artis = 1, 12
        # Tek Seferlik ise tekrar=1, ay_artis=0

        # Benzersiz ID için timestamp kullan
        base_id = int(time.time())
        kayitlar = []

        for i in range(tekrar):
            yeni_tarih = ay_ekle(tarih, i * ay_artis)
            tarih_str = yeni_tarih.strftime("%Y-%m-%d")

            # İlk kayıt için form değerlerini kullan, diğerleri için varsayılan
            s_durum = durum if i == 0 else "Planli"
            s_dosya = dosya_link if i == 0 else "-"
            s_yapilan = yapilan if i == 0 else "-"
            s_aciklama = aciklama if i == 0 else "-"
            s_teknisyen = teknisyen if i == 0 else "-"
            s_bakim_tarihi = bakim_tarihi if i == 0 else ""

            planid = f"{self._cihaz_id}-BK-{base_id + i}"

            kayit = {
                "Planid":          planid,
                "Cihazid":         self._cihaz_id,
                "BakimPeriyodu":   periyot,
                "BakimSirasi":     f"{i+1}. Bakım",
                "PlanlananTarih":  tarih_str,
                "Bakim":           bakim,
                "Durum":           s_durum,
                "BakimTarihi":     s_bakim_tarihi,
                "BakimTipi":       tip,
                "YapilanIslemler": s_yapilan,
                "Aciklama":        s_aciklama,
                "Teknisyen":       s_teknisyen,
                "Rapor":           s_dosya,
            }
            kayitlar.append(kayit)

        # Thread'de kaydet
        self.saver = IslemKaydedici(self._db, "INSERT", kayitlar)
        self.saver.islem_tamam.connect(self._kayit_basarili)
        self.saver.hata_olustu.connect(self._kayit_hatasi)
        self.saver.start()

    def _kayit_basarili(self):
        """Kayıt başarılı olduğunda çağrılır."""
        self.progress.setVisible(False)
        QMessageBox.information(
            self, 
            "Başarılı", 
            "Bakım kaydı/planı başarıyla oluşturuldu."
        )
        self._clear()
        self.saved.emit()

    def _kayit_hatasi(self, hata_mesaji: str):
        """Kayıt hatası olduğunda çağrılır."""
        self.progress.setVisible(False)
        QMessageBox.critical(
            self, 
            "Hata", 
            f"Kayıt başarısız: {hata_mesaji}"
        )

    def _clear(self):
        for w in [self.txt_periyot, self.txt_sira, self.txt_bakim,
                  self.txt_tip, self.txt_teknisyen]:
            w.clear()
        for w in [self.txt_islemler, self.txt_aciklama]:
            w.clear()
        
        # Kullanıcı adını tekrar doldur
        if self._kullanici_adi:
            self.txt_teknisyen.setText(str(self._kullanici_adi))
            
        self.dt_plan.setDate(QDate.currentDate())
        self.dt_bakim.setDate(QDate.currentDate())
        self.cmb_durum.setCurrentIndex(0)
        self.cmb_periyot_plan.setCurrentIndex(0)
        self._secilen_dosya = None
        self._mevcut_link = None
        self.lbl_dosya.setText("📋 Rapor Yok")
        self.lbl_dosya.setStyleSheet(
            f"color:{_C['muted']};font-style:italic;padding:8px 12px;"
            f"background:{_C['panel']};border-radius:4px;border:1px dashed {_C['border']};"
        )
        self.btn_dosya_ac.setVisible(False)
        self.txt_aciklama.setStyleSheet(S["input_text"])

    def closeEvent(self, event):
        """Widget kapatılırken thread'leri güvenli şekilde durdurur."""
        if hasattr(self, 'saver') and self.saver.isRunning():
            self.saver.quit()
            self.saver.wait(500)
        if hasattr(self, 'uploader') and self.uploader.isRunning():
            self.uploader.quit()
            self.uploader.wait(500)
        event.accept()
