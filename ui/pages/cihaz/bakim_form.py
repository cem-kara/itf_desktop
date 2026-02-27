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
from datetime import datetime, timedelta
from collections import defaultdict
from dateutil.relativedelta import relativedelta

from PySide6.QtCore import Qt, QDate, QAbstractTableModel, QModelIndex, Signal, QThread, QUrl
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame,
    QTableView, QSplitter, QHeaderView, QTabWidget,
    QGroupBox, QGridLayout,
    QLabel, QLineEdit, QComboBox, QDateEdit, QTextEdit,
    QPushButton, QMenu, QMessageBox, QSizePolicy, QScrollArea,
    QFileDialog, QProgressBar, QStackedWidget, QListWidgetItem,
)
from PySide6.QtGui import QColor, QDesktopServices, QPainter, QBrush

from core.date_utils import to_ui_date
from core.logger import logger
from database.repository_registry import RepositoryRegistry
from database.sqlite_manager import SQLiteManager
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
    "Planlandi":   _C["accent"],
    "Planlandı":   _C["accent"],
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
        self._db_path = getattr(db, "db_path", None)
        self.tip = islem_tipi  # "INSERT" veya "UPDATE"
        self.veri = veri

    def run(self):
        local_db = None
        try:
            # QThread içinde yeni DB bağlantısı oluştur (thread-safe)
            local_db = SQLiteManager(db_path=self._db_path, check_same_thread=False)
            repo = RepositoryRegistry(local_db).get("Periyodik_Bakim")
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
        finally:
            if local_db:
                local_db.close()


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
                 kullanici_adi: Optional[str] = None, action_guard=None, parent=None):
        super().__init__(parent)
        self._db                             = db
        self._cihaz_id                       = cihaz_id
        self._kullanici_adi                  = kullanici_adi
        self._action_guard                   = action_guard
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
        self._update_perf_tab_label()

    def _on_tab_changed(self, idx: int):
        """Performans tabına geçince verileri yenile."""
        if idx == 1:
            self._refresh_perf_tab()

    def _update_perf_tab_label(self):
        if hasattr(self, "_tabs"):
            label = "Bakım Geçmişi" if self._cihaz_id else "Bakım Performansı"
            self._tabs.setTabText(1, label)

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

        # ── Sekmeli Ana Alan ────────────────────────────
        self._tabs = QTabWidget()
        self._tabs.setStyleSheet(S.get("tab", ""))
        self._tabs.currentChanged.connect(self._on_tab_changed)

        # Tab 0 — Bakım Listesi
        list_tab = QWidget()
        lt_layout = QVBoxLayout(list_tab)
        lt_layout.setContentsMargins(0, 0, 0, 0)
        lt_layout.setSpacing(0)
        self._h_splitter = QSplitter(Qt.Horizontal)
        self._h_splitter.setStyleSheet(S.get("splitter", ""))
        self._h_splitter.addWidget(self._build_left_panel())
        self._h_splitter.addWidget(self._build_right_panel())
        self._h_splitter.setHandleWidth(0)
        self._h_splitter.setChildrenCollapsible(False)
        for i in range(2):
            self._h_splitter.handle(i).setEnabled(False)
        self._h_splitter.setSizes([710, 350])
        lt_layout.addWidget(self._h_splitter)
        self._tabs.addTab(list_tab, "Bakım Listesi")

        # Tab 1 — Bakım Performansı
        self._perf_tab = self._build_perf_tab()
        self._tabs.addTab(self._perf_tab, "Bakım Performansı")

        root.addWidget(self._tabs, 1)

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
            ("planlandi",    "PLANLANDI",         "0",  _C["accent"]),
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
            defaults = [("toplam","0"),("planlandi","0"),("yapildi","0"),
                        ("gecikmis","0"),("son_bakim","—")]
            for k, v in defaults:
                self._kpi_labels[k].setText(v)
            return

        toplam   = len(rows)
        planlandi   = sum(1 for r in rows if r.get("Durum","") in ("Planlandi","Planlandı"))
        yapildi  = sum(1 for r in rows if r.get("Durum","") in ("Yapildi","Yapıldı"))
        gecikmis = sum(1 for r in rows if r.get("Durum","") in ("Gecikmis","Gecikmiş"))
        tarihler = [r.get("BakimTarihi","") for r in rows if r.get("BakimTarihi")]
        son = to_ui_date(max(tarihler), "") if tarihler else "—"

        self._kpi_labels["toplam"].setText(str(toplam))
        self._kpi_labels["planlandi"].setText(str(planlandi))
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
        for lbl, val in [("Tüm Durumlar", None), ("Planlandı","Planlandı"),
                          ("Yapıldı","Yapıldı"), ("Gecikmiş","Gecikmiş")]:
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

    # (Orta gizli form paneli kaldırıldı — form artık sağ panelde QStackedWidget içinde açılır)

    # ── Sağ Panel (Detay Başlığı + Buton Bar) ──────────
    def _build_right_panel(self) -> QWidget:
        surface = getattr(DarkTheme, "SURFACE", "#13161d")
        panel_bg = getattr(DarkTheme, "PANEL",   "#191d26")
        border   = getattr(DarkTheme, "BORDER",  "#242938")
        text_pr  = getattr(DarkTheme, "TEXT_PRIMARY",   "#eef0f5")
        text_sec = getattr(DarkTheme, "TEXT_SECONDARY", "#c8cdd8")

        # Dış kapsayıcı
        outer = QWidget()
        outer.setStyleSheet(
            f"background:{surface};"
            f"border-left:1px solid {border};"
        )
        outer_layout = QVBoxLayout(outer)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        # ── QStackedWidget: sayfa 0 = detay, sayfa 1 = form ──
        self._right_stack = QStackedWidget()
        outer_layout.addWidget(self._right_stack, 1)

        # ════════════════════════════════════
        #  SAYFA 0 — Detay + Execution Form
        # ════════════════════════════════════
        detail_page = QWidget()
        detail_page.setStyleSheet(f"background:{surface};")
        detail_layout = QVBoxLayout(detail_page)
        detail_layout.setContentsMargins(0, 0, 0, 0)
        detail_layout.setSpacing(0)

        # ── Detay Bilgi Kartı ───────────────────────────────
        self._det_header = QWidget()
        self._det_header.setStyleSheet(
            f"background:{panel_bg};"
            f"border-bottom:1px solid {border};"
        )
        dh_layout = QVBoxLayout(self._det_header)
        dh_layout.setContentsMargins(14, 12, 14, 12)
        dh_layout.setSpacing(10)

        # Üst satır: Cihaz adı + Durum etiketi
        top_row = QHBoxLayout()
        top_row.setSpacing(8)
        self.lbl_det_title = QLabel("— Bir kayıt seçin —")
        self.lbl_det_title.setStyleSheet(
            f"font-size:13px;font-weight:700;color:{text_pr};"
        )
        self.lbl_det_title.setWordWrap(True)
        top_row.addWidget(self.lbl_det_title, 1)

        self.lbl_det_durum = QLabel("")
        self.lbl_det_durum.setStyleSheet(
            f"font-size:10px;font-weight:700;color:{_C['muted']};"
            f"padding:2px 8px;border-radius:10px;"
            f"background:{_C['border']};"
        )
        self.lbl_det_durum.setAlignment(Qt.AlignCenter)
        top_row.addWidget(self.lbl_det_durum)
        dh_layout.addLayout(top_row)

        # Plan No (tek satır, ince)
        self.lbl_det_planid = QLabel("")
        self.lbl_det_planid.setStyleSheet(
            f"font-size:10px;color:{_C['muted']};letter-spacing:0.04em;"
        )
        dh_layout.addWidget(self.lbl_det_planid)

        # Ayırıcı çizgi
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background:{border};")
        dh_layout.addWidget(sep)

        # Grid: Tarih + Periyot + Sıra / Tip + Teknisyen
        grid_row1 = QHBoxLayout()
        grid_row1.setSpacing(0)
        self.fw_tarih     = self._field_lbl("Planlanan Tarih", "—")
        self.fw_periyot   = self._field_lbl("Periyot", "—")
        self.fw_sira      = self._field_lbl("Bakım Sırası", "—")
        for w in [self.fw_tarih, self.fw_periyot, self.fw_sira]:
            grid_row1.addWidget(w, 1)
        dh_layout.addLayout(grid_row1)

        grid_row2 = QHBoxLayout()
        grid_row2.setSpacing(0)
        self.fw_tip       = self._field_lbl("Tip", "—")
        self.fw_teknisyen = self._field_lbl("Teknisyen", "—")
        self.fw_bakim_tar = self._field_lbl("Yapılan Tarih", "—")
        for w in [self.fw_tip, self.fw_teknisyen, self.fw_bakim_tar]:
            grid_row2.addWidget(w, 1)
        dh_layout.addLayout(grid_row2)

        # Not / Açıklama
        self.lbl_det_aciklama = QLabel("")
        self.lbl_det_aciklama.setWordWrap(True)
        self.lbl_det_aciklama.setVisible(False)
        self.lbl_det_aciklama.setStyleSheet(
            f"font-size:11px;color:{_C['muted']};"
            f"padding:6px 8px;background:{_C['surface']};"
            f"border-radius:4px;border:1px solid {_C['border']};"
        )
        dh_layout.addWidget(self.lbl_det_aciklama)

        detail_layout.addWidget(self._det_header)

        # ── Aksiyon Çubuğu ─────────────────────────────────
        btn_bar = QWidget()
        btn_bar.setStyleSheet(
            f"background:{surface};"
            f"border-bottom:1px solid {border};"
        )
        bb_layout = QHBoxLayout(btn_bar)
        bb_layout.setContentsMargins(10, 6, 10, 6)
        bb_layout.setSpacing(8)
        bb_layout.addStretch()

        self.btn_kayit_ekle = QPushButton("Bakım Bilgisi Gir")
        self.btn_kayit_ekle.setStyleSheet(S.get("btn_secondary", S.get("btn_primary", "")))
        self.btn_kayit_ekle.setEnabled(False)
        self.btn_kayit_ekle.clicked.connect(self._open_bakim_form_execution_from_btn)
        if self._action_guard:
            self._action_guard.disable_if_unauthorized(self.btn_kayit_ekle, "cihaz.write")
        bb_layout.addWidget(self.btn_kayit_ekle)

        detail_layout.addWidget(btn_bar)

        # ── Execution Form Alanı (detay header'ın altı) ────
        # index 0: boş placeholder
        # index 1: bakım bilgi giriş formu (sadece editable paneller)
        self._exec_content_stack = QStackedWidget()
        self._exec_content_stack.setStyleSheet(f"background:{surface};")

        placeholder = QWidget()
        placeholder.setStyleSheet(f"background:{surface};")
        ph_layout = QVBoxLayout(placeholder)
        ph_layout.addStretch()
        ph_lbl = QLabel('Kayıt seçip "Bakım Bilgisi Gir" butonuna tıklayın\nveya çift tıklayın.')
        ph_lbl.setAlignment(Qt.AlignCenter)
        ph_lbl.setStyleSheet(f"font-size:11px;color:{_C['muted']};")
        ph_layout.addWidget(ph_lbl)
        ph_layout.addStretch()
        self._exec_content_stack.addWidget(placeholder)   # index 0

        self._exec_form_scroll = QScrollArea()
        self._exec_form_scroll.setWidgetResizable(True)
        self._exec_form_scroll.setStyleSheet(
            S.get("scroll", f"background:{surface};border:none;")
        )
        self._exec_form_inner = QWidget()
        self._exec_form_inner.setStyleSheet(f"background:{surface};")
        self._exec_form_layout = QVBoxLayout(self._exec_form_inner)
        self._exec_form_layout.setContentsMargins(10, 10, 10, 10)
        self._exec_form_layout.setSpacing(0)
        self._exec_form_layout.addStretch()
        self._exec_form_scroll.setWidget(self._exec_form_inner)
        self._exec_content_stack.addWidget(self._exec_form_scroll)   # index 1

        detail_layout.addWidget(self._exec_content_stack, 1)

        self._right_stack.addWidget(detail_page)   # index 0

        # ════════════════════════════════════
        #  SAYFA 1 — Form Görünümü
        # ════════════════════════════════════
        form_page = QWidget()
        form_page.setStyleSheet(f"background:{surface};")
        form_page_layout = QVBoxLayout(form_page)
        form_page_layout.setContentsMargins(0, 0, 0, 0)
        form_page_layout.setSpacing(0)

        # Üst başlık + kapat butonu
        form_hdr = QWidget()
        form_hdr.setFixedHeight(34)
        form_hdr.setStyleSheet(
            f"background:{panel_bg};border-bottom:1px solid {border};"
        )
        form_hdr_l = QHBoxLayout(form_hdr)
        form_hdr_l.setContentsMargins(12, 0, 6, 0)
        form_hdr_l.setSpacing(0)

        self._form_hdr_title = QLabel("Bakım Formu")
        self._form_hdr_title.setStyleSheet(
            f"font-size:11px;font-weight:600;color:{text_sec};"
        )
        form_hdr_l.addWidget(self._form_hdr_title)
        form_hdr_l.addStretch()

        btn_kapat = QPushButton("✕")
        btn_kapat.setFixedSize(22, 22)
        btn_kapat.setStyleSheet(
            f"QPushButton{{background:transparent;border:none;"
            f"color:{text_sec};font-size:12px;border-radius:4px;}}"
            f"QPushButton:hover{{background:{border};color:{text_pr};}}"
        )
        btn_kapat.clicked.connect(self._close_form)
        form_hdr_l.addWidget(btn_kapat)
        form_page_layout.addWidget(form_hdr)

        # Form içeriğinin yerleşeceği scroll alanı
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
        form_page_layout.addWidget(scroll, 1)

        self._right_stack.addWidget(form_page)     # index 1

        # ════════════════════════════════════
        #  SAYFA 2 — Toplu Plan Paneli
        # ════════════════════════════════════
        bulk_page = QWidget()
        bulk_page.setStyleSheet(f"background:{surface};")
        bulk_layout = QVBoxLayout(bulk_page)
        bulk_layout.setContentsMargins(0, 0, 0, 0)
        bulk_layout.setSpacing(0)

        bulk_hdr = QWidget()
        bulk_hdr.setFixedHeight(34)
        bulk_hdr.setStyleSheet(
            f"background:{panel_bg};border-bottom:1px solid {border};"
        )
        bulk_hdr_l = QHBoxLayout(bulk_hdr)
        bulk_hdr_l.setContentsMargins(12, 0, 6, 0)
        bulk_hdr_l.setSpacing(0)

        bulk_title = QLabel("Toplu Bakım Planı")
        bulk_title.setStyleSheet(
            f"font-size:11px;font-weight:600;color:{text_sec};"
        )
        bulk_hdr_l.addWidget(bulk_title)
        bulk_hdr_l.addStretch()

        bulk_close = QPushButton("✕")
        bulk_close.setFixedSize(22, 22)
        bulk_close.setStyleSheet(
            f"QPushButton{{background:transparent;border:none;"
            f"color:{text_sec};font-size:12px;border-radius:4px;}}"
            f"QPushButton:hover{{background:{border};color:{text_pr};}}"
        )
        bulk_close.clicked.connect(self._close_bulk_panel)
        bulk_hdr_l.addWidget(bulk_close)
        bulk_layout.addWidget(bulk_hdr)

        bulk_scroll = QScrollArea()
        bulk_scroll.setWidgetResizable(True)
        bulk_scroll.setStyleSheet(S.get("scroll", f"background:{surface};border:none;"))

        self._bulk_inner = QWidget()
        self._bulk_inner.setStyleSheet(f"background:{surface};")
        self._bulk_layout = QVBoxLayout(self._bulk_inner)
        self._bulk_layout.setContentsMargins(10, 10, 10, 10)
        self._bulk_layout.setSpacing(0)

        self._bulk_panel = TopluBakimPlanPanel(
            db=self._db,
            on_success=self._on_toplu_plan_success,
            on_close=self._close_bulk_panel,
            parent=self,
        )
        self._bulk_layout.addWidget(self._bulk_panel)
        self._bulk_layout.addStretch()

        bulk_scroll.setWidget(self._bulk_inner)
        bulk_layout.addWidget(bulk_scroll, 1)

        self._right_stack.addWidget(bulk_page)     # index 2

        return outer

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
        
        if not self._db:
            self.cmb_marka_filter.blockSignals(False)
            return
        
        try:
            # Sabitler tablosundan Kod="Marka" olan kayıtları çek
            repo = RepositoryRegistry(self._db).get("Sabitler")
            sabitler = repo.get_all() or []
            markalar = sorted([
                str(s.get("MenuEleman", "")).strip()
                for s in sabitler
                if str(s.get("Kod", "")).strip() == "Marka" 
                and str(s.get("MenuEleman", "")).strip()
            ])
            
            for m in markalar:
                if m and m != "None":
                    self.cmb_marka_filter.addItem(m, m)
        except Exception as e:
            logger.error(f"Marka filtresi yüklenemedi: {e}")
        
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
            if sel_marka and self._db:
                # Cihazlar tablosundan seçili markaya ait cihaz ID'lerini bul
                try:
                    repo = RepositoryRegistry(self._db).get("Cihazlar")
                    cihazlar = repo.get_all() or []
                    marka_cihaz_ids = {
                        str(c.get("Cihazid","")) 
                        for c in cihazlar 
                        if str(c.get("Marka","")) == sel_marka
                    }
                    filtered = [r for r in filtered
                                if str(r.get("Cihazid","")) in marka_cihaz_ids]
                except Exception as e:
                    logger.error(f"Marka filtrelemesi yapılamadı: {e}")

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
        planid  = row.get("Planid","")

        # Başlık: cihaz adı
        self.lbl_det_title.setText(cihaz or "—")

        # Plan No (ince alt yazı)
        self.lbl_det_planid.setText(f"Plan No: {planid}" if planid else "")

        # Durum etiketi (pill)
        durum   = row.get("Durum","")
        dur_c   = _DURUM_COLOR.get(durum, _C["muted"])
        if durum:
            self.lbl_det_durum.setText(f"● {durum}")
            self.lbl_det_durum.setStyleSheet(
                f"font-size:10px;font-weight:700;color:{dur_c};"
                f"padding:2px 8px;border-radius:10px;"
                f"background:{dur_c}22;"
            )
        else:
            self.lbl_det_durum.setText("")

        # Grid alanları
        self._set_field(self.fw_tarih,     to_ui_date(row.get("PlanlananTarih",""), "—"))
        self._set_field(self.fw_periyot,   periyot or "—")
        self._set_field(self.fw_sira,      row.get("BakimSirasi","") or "—")
        self._set_field(self.fw_tip,       row.get("BakimTipi","") or "—")
        self._set_field(self.fw_teknisyen, row.get("Teknisyen","") or "—")
        self._set_field(self.fw_bakim_tar, to_ui_date(row.get("BakimTarihi",""), "—"))

        # Not / Açıklama — sadece varsa göster
        aciklama = (row.get("YapilanIslemler","") or row.get("Aciklama","") or "")
        aciklama = aciklama.strip() if aciklama not in ("-", "") else ""
        if aciklama:
            if len(aciklama) > 200:
                aciklama = aciklama[:200] + "…"
            self.lbl_det_aciklama.setText(aciklama)
            self.lbl_det_aciklama.setVisible(True)
        else:
            self.lbl_det_aciklama.setVisible(False)

    # ══════════════════════════════════════════════════════
    #  Form Açma / Kapama
    # ══════════════════════════════════════════════════════
    def _clear_form_container(self):
        """Her iki form alanını da temizle."""
        # Exec form alanı
        while self._exec_form_layout.count() > 1:
            item = self._exec_form_layout.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)
        # Plan creation form alanı
        while self._form_layout.count() > 1:
            item = self._form_layout.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)
        if self._active_form is not None:
            self._active_form.setParent(None)
            self._active_form = None

    def _open_bakim_form(self):
        """PLAN_CREATION: sağ stack'i tam form sayfasına geçir."""
        if self._action_guard and not self._action_guard.check_and_warn(
            self, "cihaz.write", "Bakim Formu Acma"
        ):
            return
        self._clear_form_container()
        form = _BakimGirisForm(
            self._db,
            self._cihaz_id,
            kullanici_adi=self._kullanici_adi,
            mode=FormMode.PLAN_CREATION,
            action_guard=self._action_guard,
            parent=self
        )
        form.saved.connect(self._on_bakim_saved)
        self._active_form = form
        self._form_layout.insertWidget(0, form)
        self._form_hdr_title.setText("Yeni Bakım Planı")
        self._right_stack.setCurrentIndex(1)

    def _open_bakim_form_execution_from_btn(self):
        """Butona basınca mevcut seçili satır için bilgi giriş formunu aç."""
        if self._selected_row:
            self._open_bakim_form_execution_with_row(self._selected_row)

    def _open_bakim_form_execution(self, index):
        """Çift tıkla bakım bilgisi giriş formunu aç (EXECUTION_INFO modu)."""
        if not self._selected_row:
            return
        self._open_bakim_form_execution_with_row(self._selected_row)

    def _open_bakim_form_execution_with_row(self, row: Dict):
        """EXECUTION_INFO formunu detay header'ın altına açar."""
        if self._action_guard and not self._action_guard.check_and_warn(
            self, "cihaz.write", "Bakim Kaydi Giris"
        ):
            return
        self._clear_form_container()
        form = _BakimGirisForm(
            self._db,
            self._cihaz_id,
            kullanici_adi=self._kullanici_adi,
            mode=FormMode.EXECUTION_INFO,
            plan_data=row,
            action_guard=self._action_guard,
            parent=self
        )
        form.saved.connect(self._on_bakim_saved)
        self._active_form = form
        self._exec_form_layout.insertWidget(0, form)
        self._exec_content_stack.setCurrentIndex(1)
        # Detay sayfasında kal (right_stack index 0)
        self._right_stack.setCurrentIndex(0)

    def _close_form(self):
        self._clear_form_container()
        self._exec_content_stack.setCurrentIndex(0)
        self._right_stack.setCurrentIndex(0)

    def _close_bulk_panel(self):
        self._right_stack.setCurrentIndex(0)

    def _on_toplu_plan_success(self, toplam_plan: int):
        self._load_data()
        QMessageBox.information(
            self,
            "Başarılı",
            f"Toplu bakım planlaması {toplam_plan} plan olacak şekilde oluşturuldu."
        )

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
    #  Bakım Performansı Tab
    # ══════════════════════════════════════════════════════
    def _build_perf_tab(self) -> QWidget:
        """Performans tabının iskeletini oluşturur (içerik _refresh_perf_tab ile dolar)."""
        surface = _C["surface"]
        outer = QScrollArea()
        outer.setWidgetResizable(True)
        outer.setStyleSheet(S.get("scroll", f"background:{surface};border:none;"))
        self._perf_inner = QWidget()
        self._perf_inner.setStyleSheet(f"background:{surface};")
        self._perf_layout = QVBoxLayout(self._perf_inner)
        self._perf_layout.setContentsMargins(16, 16, 16, 16)
        self._perf_layout.setSpacing(20)
        self._perf_layout.addStretch()
        outer.setWidget(self._perf_inner)
        return outer

    def _section_title(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet(
            f"font-size:11px;font-weight:700;letter-spacing:0.08em;"
            f"color:{_C['muted']};"
            f"padding-bottom:4px;"
            f"border-bottom:1px solid {_C['border']};"
        )
        return lbl

    def _refresh_perf_tab(self):
        """_all_rows verisini kullanarak performans tabını yeniden çizer."""
        while self._perf_layout.count():
            item = self._perf_layout.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)

        rows = self._all_rows
        if not rows:
            empty = QLabel("Gösterilecek bakım verisi yok.")
            empty.setAlignment(Qt.AlignCenter)
            empty.setStyleSheet(
                f"color:{_C['muted']};font-size:13px;padding:40px;"
            )
            self._perf_layout.addWidget(empty)
            self._perf_layout.addStretch()
            return

        if self._cihaz_id:
            # ── Tek cihaz: Bakım Geçmişi görünümü ─────────
            self._perf_layout.addWidget(
                self._section_title(f"{self._cihaz_id}  —  AYLIK BAKIM TRENDİ")
            )
            self._perf_layout.addWidget(self._build_trend_chart(rows))

            self._perf_layout.addWidget(self._section_title("DURUM DAĞILIMI"))
            self._perf_layout.addWidget(self._build_single_cihaz_stats(rows))

            self._perf_layout.addWidget(
                self._section_title("GECİKMİŞ BAKIMLAR")
            )
            self._perf_layout.addWidget(self._build_delayed_list(rows))
        else:
            # ── Genel: Marka bazlı performans görünümü ─────
            # Cihazlar tablosundan cihazid → marka eşlemesini yükle
            cihaz_marka_map, tum_markalar = self._load_cihaz_marka_map()

            self._perf_layout.addWidget(
                self._section_title("MARKA BAZLI BAKIM PERFORMANSI")
            )
            marka_data, plansiz_markalar = self._compute_marka_stats(
                rows, cihaz_marka_map, tum_markalar
            )
            self._perf_layout.addWidget(self._build_marka_grid(marka_data))

            if plansiz_markalar:
                self._perf_layout.addWidget(
                    self._section_title("BAKIM PLANI BULUNMAYAN MARKALAR")
                )
                self._perf_layout.addWidget(
                    self._build_no_plan_card(plansiz_markalar)
                )

            self._perf_layout.addWidget(self._section_title("AYLIK BAKIM TRENDİ"))
            self._perf_layout.addWidget(self._build_trend_chart(rows))

            self._perf_layout.addWidget(self._section_title("GECİKMİŞ BAKIMLAR"))
            self._perf_layout.addWidget(self._build_delayed_list(rows))

        self._perf_layout.addStretch()

    def _build_single_cihaz_stats(self, rows: List[Dict]) -> QWidget:
        """Tek cihaz için durum dağılımı özet kartları."""
        planlandi  = sum(1 for r in rows if r.get("Durum","") in ("Planlandi","Planlandı"))
        yapildi    = sum(1 for r in rows if r.get("Durum","") in ("Yapildi","Yapıldı"))
        gecikmis   = sum(1 for r in rows if r.get("Durum","") in ("Gecikmis","Gecikmiş"))

        # Tamamlanma oranı
        toplam = len(rows)
        oran = f"%{round(yapildi / toplam * 100)}" if toplam else "—"

        # Ortalama gecikme (gecikmiş olanların planlanan tarihinden bugüne)
        gecikme_list = []
        now = datetime.now()
        for r in rows:
            if r.get("Durum","") in ("Gecikmis","Gecikmiş"):
                t = r.get("PlanlananTarih","")
                if t and len(t) >= 10:
                    try:
                        dt = datetime.strptime(t[:10], "%Y-%m-%d")
                        gecikme_list.append((now - dt).days)
                    except ValueError:
                        pass
        ort_gecikme = f"{round(sum(gecikme_list)/len(gecikme_list))} gün" if gecikme_list else "—"

        container = QWidget()
        container.setStyleSheet("background:transparent;")
        hl = QHBoxLayout(container)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setSpacing(8)

        items = [
            ("Toplam",          str(toplam),    _C["accent"]),
            ("Planlandı",       str(planlandi), _C["accent"]),
            ("Yapıldı",         str(yapildi),   _C["green"]),
            ("Gecikmiş",        str(gecikmis),  _C["red"]),
            ("Tamamlanma",      oran,           _C["green"]),
            ("Ort. Gecikme",    ort_gecikme,    _C["amber"]),
        ]
        for title, value, color in items:
            card = QWidget()
            card.setStyleSheet(
                f"background:{_C['panel']};border:1px solid {_C['border']};border-radius:6px;"
            )
            cl = QVBoxLayout(card)
            cl.setContentsMargins(10, 8, 10, 8)
            cl.setSpacing(2)
            t = QLabel(title.upper())
            t.setStyleSheet(
                f"font-size:9px;font-weight:600;letter-spacing:0.06em;"
                f"color:{_C['muted']};background:transparent;"
            )
            v = QLabel(value)
            v.setStyleSheet(
                f"font-size:16px;font-weight:700;color:{color};background:transparent;"
            )
            cl.addWidget(t)
            cl.addWidget(v)
            hl.addWidget(card, 1)

        return container

    def _load_cihaz_marka_map(self):
        """
        Cihazlar tablosundan cihazid → marka eşlemesini döndürür.
        Returns:
            cihaz_marka_map : Dict[str, str]   {cihazid: marka}
            tum_markalar    : Dict[str, set]   {marka: {cihazid, ...}}
        """
        cihaz_marka_map: Dict[str, str] = {}
        tum_markalar: Dict[str, set]    = defaultdict(set)
        if not self._db:
            return cihaz_marka_map, tum_markalar
        try:
            repo = RepositoryRegistry(self._db).get("Cihazlar")
            for c in (repo.get_all() or []):
                cid   = str(c.get("Cihazid","") or "").strip()
                marka = str(c.get("Marka","")   or "").strip()
                if cid and marka:
                    cihaz_marka_map[cid] = marka
                    tum_markalar[marka].add(cid)
        except Exception as e:
            logger.error(f"Cihazlar tablosu yüklenemedi: {e}")
        return cihaz_marka_map, tum_markalar

    def _compute_marka_stats(
        self,
        rows: List[Dict],
        cihaz_marka_map: Dict[str, str],
        tum_markalar: Dict[str, set],
    ):
        """
        Bakım satırlarını marka bazında gruplar.
        Yalnızca Cihazlar tablosunda bulunan cihazlar dahil edilir.
        Returns:
            marka_data      : List[Dict]  — planlı markalar, toplama göre sıralı
            plansiz_markalar: List[Dict]  — hiç bakım planı olmayan markalar
        """
        stats: Dict[str, Dict] = {}
        now = datetime.now()

        for r in rows:
            cid = str(r.get("Cihazid","") or "").strip()
            # Cihazlar tablosunda olmayan cihazları atla
            if cid not in cihaz_marka_map:
                continue
            marka = cihaz_marka_map[cid]
            if marka not in stats:
                stats[marka] = {
                    "marka":     marka,
                    "cihazlar":  set(),
                    "toplam":    0, "yapildi": 0, "gecikmis": 0, "planlandi": 0,
                    "ay_trend":  defaultdict(int),
                }
            s = stats[marka]
            s["cihazlar"].add(cid)
            s["toplam"] += 1

            durum = r.get("Durum","")
            if durum in ("Yapildi","Yapıldı"):
                s["yapildi"] += 1
            elif durum in ("Gecikmis","Gecikmiş"):
                s["gecikmis"] += 1
            elif durum in ("Planlandi","Planlandı"):
                s["planlandi"] += 1

            t = r.get("PlanlananTarih","")
            if t and len(t) >= 7:
                try:
                    dt = datetime.strptime(t[:7], "%Y-%m")
                    months_ago = (now.year - dt.year) * 12 + (now.month - dt.month)
                    if 0 <= months_ago <= 11:
                        s["ay_trend"][11 - months_ago] += 1
                except ValueError:
                    pass

        marka_data = []
        for s in stats.values():
            trend = [s["ay_trend"].get(i, 0) for i in range(12)]
            oran  = round(s["yapildi"] / s["toplam"] * 100) if s["toplam"] else 0
            marka_data.append({
                **s,
                "cihaz_sayi": len(s["cihazlar"]),
                "trend":      trend,
                "oran":       oran,
            })
        marka_data.sort(key=lambda x: x["toplam"], reverse=True)

        # Plansız markalar: Cihazlar tablosunda var ama hiç bakım satırı yok
        planlanan_markalar = set(stats.keys())
        plansiz_markalar = []
        for marka, cihaz_ids in tum_markalar.items():
            if marka not in planlanan_markalar:
                plansiz_markalar.append({
                    "marka":      marka,
                    "cihaz_sayi": len(cihaz_ids),
                    "cihazlar":   sorted(cihaz_ids),
                })
        plansiz_markalar.sort(key=lambda x: x["marka"])

        return marka_data, plansiz_markalar

    def _build_marka_grid(self, marka_data: List[Dict]) -> QWidget:
        """Bakım planı olan markalar için kart grid."""
        if not marka_data:
            lbl = QLabel("Eşleşen marka verisi bulunamadı.")
            lbl.setStyleSheet(f"color:{_C['muted']};font-size:12px;padding:12px;")
            return lbl

        container = QWidget()
        container.setStyleSheet("background:transparent;")
        grid = QGridLayout(container)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(10)

        max_toplam = max((d["toplam"] for d in marka_data), default=1)
        cols = 3

        for idx, d in enumerate(marka_data):
            row_i, col_i = divmod(idx, cols)

            card = QWidget()
            card.setStyleSheet(
                f"QWidget{{background:{_C['panel']};border:1px solid {_C['border']};"
                f"border-radius:8px;}}"
            )
            cl = QVBoxLayout(card)
            cl.setContentsMargins(14, 12, 14, 12)
            cl.setSpacing(8)

            # ── Başlık satırı ──────────────────────────────
            hdr = QHBoxLayout()
            lbl_marka = QLabel(d["marka"])
            lbl_marka.setStyleSheet(
                f"font-size:13px;font-weight:700;color:{_C['text']};background:transparent;"
            )
            hdr.addWidget(lbl_marka)
            hdr.addStretch()

            # Cihaz sayısı küçük etiket
            lbl_cihaz_sayi = QLabel(f"{d['cihaz_sayi']} cihaz")
            lbl_cihaz_sayi.setStyleSheet(
                f"font-size:10px;color:{_C['muted']};"
                f"background:{_C['border']};border-radius:4px;padding:1px 6px;"
            )
            hdr.addWidget(lbl_cihaz_sayi)

            # Tamamlanma oranı pill
            oran_color = _C["green"] if d["oran"] >= 80 else (_C["amber"] if d["oran"] >= 50 else _C["red"])
            badge_oran = QLabel(f"%{d['oran']}")
            badge_oran.setStyleSheet(
                f"font-size:10px;font-weight:600;color:{oran_color};"
                f"background:{oran_color}22;border-radius:4px;padding:1px 6px;"
            )
            hdr.addWidget(badge_oran)

            if d["gecikmis"] > 0:
                badge_gec = QLabel(f"{d['gecikmis']} gecikmiş")
                badge_gec.setStyleSheet(
                    f"font-size:10px;font-weight:600;color:{_C['red']};"
                    f"background:{_C['red']}22;border-radius:4px;padding:1px 6px;"
                )
                hdr.addWidget(badge_gec)
            cl.addLayout(hdr)

            # ── Bar satırları ──────────────────────────────
            for lbl_txt, val, color in [
                ("Toplam",    d["toplam"],    _C["accent"]),
                ("Yapıldı",   d["yapildi"],   _C["green"]),
                ("Planlandı", d["planlandi"], _C["accent"]),
                ("Gecikmiş",  d["gecikmis"],  _C["red"]),
            ]:
                bar_pct = int((val / max_toplam) * 100) if max_toplam else 0
                cl.addWidget(self._bar_row(lbl_txt, val, bar_pct, color))

            # ── Sparkline ──────────────────────────────────
            spark = _BakimSparkline(d["trend"], parent=card)
            spark.setFixedHeight(32)
            cl.addWidget(spark)

            grid.addWidget(card, row_i, col_i)

        # Boş hücreler
        remainder = len(marka_data) % cols
        if remainder:
            for c in range(remainder, cols):
                ph = QWidget()
                ph.setStyleSheet("background:transparent;")
                grid.addWidget(ph, len(marka_data) // cols, c)

        return container

    def _build_no_plan_card(self, plansiz_markalar: List[Dict]) -> QWidget:
        """Bakım planı olmayan markalar için uyarı kartı."""
        card = QWidget()
        card.setStyleSheet(
            f"background:{_C['panel']};"
            f"border:1px solid {_C['amber']}44;"
            f"border-left:3px solid {_C['amber']};"
            f"border-radius:8px;"
        )
        cl = QVBoxLayout(card)
        cl.setContentsMargins(16, 12, 16, 12)
        cl.setSpacing(10)

        # Başlık
        hdr = QHBoxLayout()
        lbl_title = QLabel("Bakım Planlanmamış Markalar")
        lbl_title.setStyleSheet(
            f"font-size:12px;font-weight:700;color:{_C['amber']};background:transparent;"
        )
        hdr.addWidget(lbl_title)
        hdr.addStretch()
        lbl_sayi = QLabel(f"{len(plansiz_markalar)} marka")
        lbl_sayi.setStyleSheet(
            f"font-size:11px;font-weight:600;color:{_C['amber']};"
            f"background:{_C['amber']}22;border-radius:4px;padding:2px 8px;"
        )
        hdr.addWidget(lbl_sayi)
        cl.addLayout(hdr)

        # Marka satırları — yatay akış (wrap)
        wrap = QWidget()
        wrap.setStyleSheet("background:transparent;")
        wrap_l = QHBoxLayout(wrap)
        wrap_l.setContentsMargins(0, 0, 0, 0)
        wrap_l.setSpacing(8)

        for d in plansiz_markalar:
            chip = QWidget()
            chip.setStyleSheet(
                f"background:{_C['surface']};border:1px solid {_C['border']};"
                f"border-radius:6px;"
            )
            chip_l = QVBoxLayout(chip)
            chip_l.setContentsMargins(10, 6, 10, 6)
            chip_l.setSpacing(2)

            lbl_m = QLabel(d["marka"])
            lbl_m.setStyleSheet(
                f"font-size:12px;font-weight:600;color:{_C['text']};background:transparent;"
            )
            chip_l.addWidget(lbl_m)

            lbl_c = QLabel(f"{d['cihaz_sayi']} cihaz")
            lbl_c.setStyleSheet(
                f"font-size:10px;color:{_C['muted']};background:transparent;"
            )
            chip_l.addWidget(lbl_c)
            wrap_l.addWidget(chip)

        wrap_l.addStretch()
        cl.addWidget(wrap)

        return card

    def _bar_row(self, label: str, value: int, pct: int, fill_color: str) -> QWidget:
        w = QWidget()
        w.setStyleSheet("background:transparent;")
        hl = QHBoxLayout(w)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setSpacing(6)

        lbl = QLabel(label)
        lbl.setFixedWidth(56)
        lbl.setStyleSheet(f"font-size:10px;color:{_C['muted']};background:transparent;")
        hl.addWidget(lbl)

        bar_bg = QWidget()
        bar_bg.setFixedHeight(6)
        bar_bg.setStyleSheet(f"background:{_C['border']};border-radius:3px;")
        bar_bg.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        bar_fill = QWidget(bar_bg)
        bar_fill.setFixedHeight(6)
        bar_fill.setStyleSheet(f"background:{fill_color};border-radius:3px;")
        bar_fill.setFixedWidth(max(4, int(pct * 1.5)))
        hl.addWidget(bar_bg)

        cnt = QLabel(str(value))
        cnt.setFixedWidth(24)
        cnt.setAlignment(Qt.AlignRight)
        cnt.setStyleSheet(
            f"font-size:10px;font-weight:600;color:{fill_color};background:transparent;"
        )
        hl.addWidget(cnt)
        return w

    def _build_trend_chart(self, rows: List[Dict]) -> QWidget:
        """12 aylık bakım trend çubuğu."""
        now = datetime.now()
        ay_sayim: Dict[int, int] = {}
        ay_etiket: Dict[int, str] = {}
        ay_isimleri = ["Oca","Şub","Mar","Nis","May","Haz","Tem","Ağu","Eyl","Eki","Kas","Ara"]

        for i in range(12):
            ay_idx = (now.month - 1 - i) % 12
            yil    = now.year if now.month - 1 - i >= 0 else now.year - 1
            konum  = 11 - i
            ay_sayim[konum] = 0
            ay_etiket[konum] = ay_isimleri[ay_idx]

        for r in rows:
            t = r.get("PlanlananTarih","")
            if t and len(t) >= 7:
                try:
                    dt = datetime.strptime(t[:7], "%Y-%m")
                    months_ago = (now.year - dt.year) * 12 + (now.month - dt.month)
                    if 0 <= months_ago <= 11:
                        ay_sayim[11 - months_ago] += 1
                except ValueError:
                    pass

        degerler  = [ay_sayim[i] for i in range(12)]
        etiketler = [ay_etiket[i] for i in range(12)]
        max_val   = max(degerler) if any(degerler) else 1

        container = QWidget()
        container.setStyleSheet(
            f"background:{_C['panel']};border:1px solid {_C['border']};border-radius:8px;"
        )
        cl = QVBoxLayout(container)
        cl.setContentsMargins(16, 14, 16, 14)
        cl.setSpacing(6)

        bar_row_l = QHBoxLayout()
        bar_row_l.setSpacing(4)
        for val, et in zip(degerler, etiketler):
            col = QVBoxLayout()
            col.setSpacing(2)
            col.setAlignment(Qt.AlignBottom)

            val_lbl = QLabel(str(val) if val else "")
            val_lbl.setAlignment(Qt.AlignHCenter)
            val_lbl.setStyleSheet(f"font-size:9px;color:{_C['muted']};background:transparent;")
            col.addWidget(val_lbl)

            bar_color = _C["red"] if val > max_val * 0.7 else \
                        _C["amber"] if val > max_val * 0.4 else _C["accent"]
            bar_h = max(4, int((val / max_val) * 60)) if max_val else 4

            bar = QWidget()
            bar.setFixedSize(16, bar_h)
            bar.setStyleSheet(f"background:{bar_color};border-radius:3px 3px 0 0;")
            col.addWidget(bar, 0, Qt.AlignHCenter)
            bar_row_l.addLayout(col)

        cl.addLayout(bar_row_l)

        lbl_row = QHBoxLayout()
        lbl_row.setSpacing(4)
        for et in etiketler:
            lbl = QLabel(et)
            lbl.setAlignment(Qt.AlignHCenter)
            lbl.setStyleSheet(f"font-size:9px;color:{_C['muted']};background:transparent;")
            lbl_row.addWidget(lbl)
        cl.addLayout(lbl_row)

        return container

    def _build_delayed_list(self, rows: List[Dict]) -> QWidget:
        """Gecikmiş bakımlar listesi."""
        gecikmisler = sorted(
            [r for r in rows if r.get("Durum","") in ("Gecikmis","Gecikmiş")],
            key=lambda r: r.get("PlanlananTarih","")
        )

        container = QWidget()
        container.setStyleSheet("background:transparent;")
        cl = QVBoxLayout(container)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.setSpacing(6)

        if not gecikmisler:
            lbl = QLabel("Gecikmiş bakım bulunmuyor.")
            lbl.setStyleSheet(f"color:{_C['muted']};font-size:12px;padding:12px;")
            cl.addWidget(lbl)
            return container

        now = datetime.now()
        for r in gecikmisler[:15]:
            row_w = QWidget()
            row_w.setStyleSheet(
                f"background:{_C['panel']};border:1px solid {_C['border']};"
                f"border-left:3px solid {_C['red']};border-radius:6px;"
            )
            rl = QHBoxLayout(row_w)
            rl.setContentsMargins(12, 8, 12, 8)
            rl.setSpacing(12)

            chip = QLabel(str(r.get("Cihazid","")) or "—")
            chip.setStyleSheet(
                f"font-size:11px;font-weight:600;color:{_C['accent']};"
                f"background:{_C['accent']}22;border-radius:4px;padding:2px 8px;"
            )
            chip.setFixedWidth(90)
            rl.addWidget(chip)

            plan_no = QLabel(str(r.get("Planid",""))[:20])
            plan_no.setStyleSheet(f"font-size:11px;color:{_C['muted']};background:transparent;")
            plan_no.setFixedWidth(120)
            rl.addWidget(plan_no)

            periyot = QLabel(str(r.get("BakimPeriyodu","")) or "—")
            periyot.setStyleSheet(f"font-size:12px;color:{_C['text']};background:transparent;")
            periyot.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
            rl.addWidget(periyot)

            tarih_str = r.get("PlanlananTarih","")
            gecikme_lbl = QLabel(to_ui_date(tarih_str, "—"))
            try:
                dt = datetime.strptime(tarih_str[:10], "%Y-%m-%d")
                gun = (now - dt).days
                gecikme_lbl.setText(f"{to_ui_date(tarih_str,'—')}  ({gun}g)")
            except (ValueError, TypeError):
                pass
            gecikme_lbl.setStyleSheet(
                f"font-size:11px;font-weight:600;color:{_C['red']};background:transparent;"
            )
            rl.addWidget(gecikme_lbl)

            cl.addWidget(row_w)

        return container

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
        """Toplu bakım plan panelini sağ tarafta açar."""
        if hasattr(self, "_right_stack"):
            if hasattr(self, "_bulk_panel"):
                self._bulk_panel._load_cihazlar()
            self._right_stack.setCurrentIndex(2)


# ─────────────────────────────────────────────────────────────
#  Toplu Bakım Planlama Dialog'u
# ─────────────────────────────────────────────────────────────
class TopluBakimPlanPanel(QWidget):
    """Birden fazla cihaz için toplu bakım planlaması (sağ panel içinde)."""

    def __init__(self, db=None, on_success=None, on_close=None, parent=None):
        super().__init__(parent)
        self._db = db
        self.toplam_plan = 0
        self._all_cihazlar = []
        self._on_success = on_success
        self._on_close = on_close
        self._setup_ui()

    def _setup_ui(self):
        """Panel UI'ı oluştur."""
        from PySide6.QtWidgets import QListWidget, QListWidgetItem

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        # Başlık
        title = QLabel("Toplu Bakım Planı Oluştur")
        title.setStyleSheet(
            f"font-size:14px;font-weight:bold;color:{_C['accent']};"
        )
        layout.addWidget(title)

        # Marka filtresi
        lbl_marka = QLabel("Marka Filtresi:")
        lbl_marka.setStyleSheet(f"font-weight:600;color:{_C['text']};")
        layout.addWidget(lbl_marka)

        self.cmb_marka_filter = QComboBox()
        self.cmb_marka_filter.setStyleSheet(S["combo"])
        self.cmb_marka_filter.setMinimumHeight(32)
        self.cmb_marka_filter.currentIndexChanged.connect(self._refresh_cihaz_list)
        layout.addWidget(self.cmb_marka_filter)

        # Cihaz Seçimi
        lbl_cihaz = QLabel("Cihazlar Seçin:")
        lbl_cihaz.setStyleSheet(f"font-weight:600;color:{_C['text']};")
        layout.addWidget(lbl_cihaz)

        # Cihaz listesi
        self.list_cihazlar = QListWidget()
        self.list_cihazlar.setStyleSheet(S.get("list", ""))
        self.list_cihazlar.setMaximumHeight(200)

        self.list_cihazlar.setSelectionMode(QListWidget.MultiSelection)
        layout.addWidget(self.list_cihazlar)

        # Hızlı seçim butonları
        select_row = QHBoxLayout()
        btn_tumunu_sec = QPushButton("Tümünü Seç")
        btn_tumunu_sec.setStyleSheet(S.get("btn_secondary", ""))
        btn_tumunu_sec.clicked.connect(self._select_all_visible)
        select_row.addWidget(btn_tumunu_sec)

        btn_temizle = QPushButton("Seçimi Temizle")
        btn_temizle.setStyleSheet(S.get("btn_secondary", ""))
        btn_temizle.clicked.connect(self._clear_selection)
        select_row.addWidget(btn_temizle)

        select_row.addStretch()
        layout.addLayout(select_row)

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
        btn_iptal.clicked.connect(self._on_close or (lambda: None))
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
        btn_oluştur.clicked.connect(self._olustur_planlar)
        btn_layout.addWidget(btn_oluştur)

        layout.addLayout(btn_layout)

        self._load_cihazlar()

    def _load_cihazlar(self):
        """Tüm cihazları yükle ve marka filtresini hazırla."""
        self._all_cihazlar = []
        self.cmb_marka_filter.clear()
        self.cmb_marka_filter.addItem("Tüm Markalar", None)
        try:
            repo = RepositoryRegistry(self._db).get("Cihazlar")
            self._all_cihazlar = repo.get_all() or []
        except Exception as e:
            logger.error(f"Cihaz listesi yüklenemedi: {e}")
            self._all_cihazlar = []

        markalar = sorted({c.get("Marka", "").strip() for c in self._all_cihazlar if c.get("Marka")})
        for marka in markalar:
            self.cmb_marka_filter.addItem(marka, marka)

        self._refresh_cihaz_list()

    def _refresh_cihaz_list(self):
        """Marka filtresine göre cihaz listesini yeniler."""
        self.list_cihazlar.clear()
        secili_marka = self.cmb_marka_filter.currentData()
        for cihaz in self._all_cihazlar:
            c_id = cihaz.get("Cihazid", "")
            c_marka = (cihaz.get("Marka") or "").strip()
            if not c_id:
                continue
            if secili_marka and c_marka != secili_marka:
                continue
            item = QListWidgetItem(f"{c_id} - {c_marka}")
            item.setData(Qt.UserRole, c_id)
            item.setCheckState(Qt.Unchecked)
            self.list_cihazlar.addItem(item)

    def _select_all_visible(self):
        for i in range(self.list_cihazlar.count()):
            self.list_cihazlar.item(i).setCheckState(Qt.Checked)

    def _clear_selection(self):
        for i in range(self.list_cihazlar.count()):
            self.list_cihazlar.item(i).setCheckState(Qt.Unchecked)

    def _olustur_planlar(self):
        """Seçilen cihazlar için bakım planlarını oluştur."""
        secili_cihazlar = [
            self.list_cihazlar.item(i).data(Qt.UserRole)
            for i in range(self.list_cihazlar.count())
            if self.list_cihazlar.item(i).checkState() == Qt.Checked
        ]

        if not secili_cihazlar:
            QMessageBox.warning(self, "Uyarı", "Lütfen en az bir cihaz seçin.")
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
                    "Durum":           "Planlandı",
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
            if self._on_success:
                self._on_success(self.toplam_plan)
            if self._on_close:
                self._on_close()
        except Exception as e:
            logger.error(f"Toplu planlama başarısız: {e}")
            QMessageBox.critical(self, "Hata", f"Planlama başarısız: {e}")


# ─────────────────────────────────────────────────────────────
#  Sparkline Widget — 12 aylık mini çubuk grafiği
# ─────────────────────────────────────────────────────────────
class _BakimSparkline(QWidget):
    """12 değerden oluşan mini çubuk grafiği (bakım trend)."""

    def __init__(self, values: List[int], parent=None):
        super().__init__(parent)
        self._values = values or [0] * 12
        self.setMinimumHeight(28)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()
        n = len(self._values)
        if n == 0:
            return

        max_v = max(self._values) if any(self._values) else 1
        bar_w = max(2, (w - (n - 1) * 2) // n)
        gap   = 2

        for i, v in enumerate(self._values):
            bar_h = max(3, int((v / max_v) * (h - 4))) if max_v else 3
            x = i * (bar_w + gap)
            y = h - bar_h

            if v > max_v * 0.7:
                color = QColor(_C["red"])
            elif v > max_v * 0.4:
                color = QColor(_C["amber"])
            else:
                color = QColor(_C["accent"])

            color.setAlpha(180)
            painter.fillRect(x, y, bar_w, bar_h, QBrush(color))

        painter.end()


class _BakimGirisForm(QWidget):
    saved = Signal()

    def __init__(self, db=None, cihaz_id: Optional[str] = None, 
                 kullanici_adi: Optional[str] = None, 
                 mode: str = FormMode.PLAN_CREATION,
                 plan_data: Optional[Dict] = None,
                 action_guard=None,
                 parent=None):
        super().__init__(parent)
        self._db              = db
        self._cihaz_id        = cihaz_id
        self._kullanici_adi   = kullanici_adi
        self._mode            = mode
        self._plan_data       = plan_data or {}
        self._action_guard    = action_guard
        self._secilen_dosya   = None
        self._mevcut_link     = None
        self._drive_folder_id = None
        self._selected_cihaz_id = None  # Form'dan seçilen cihaz ID'si
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
        self._panel_plan = self._create_panel("Bakım Planı Seçimi")
        
        # Cihaz Seçimi
        self.cmb_cihaz_sec = QComboBox()
        self.cmb_cihaz_sec.setStyleSheet(S["combo"])
        self.cmb_cihaz_sec.setMinimumHeight(40)
        self.cmb_cihaz_sec.setEditable(True)
        self.cmb_cihaz_sec.lineEdit().setPlaceholderText("Cihaz ara veya seç...")
        self._load_cihaz_list()
        self._panel_plan.add_field("Cihaz", self.cmb_cihaz_sec)
        
        self.cmb_periyot_plan = QComboBox()
        self.cmb_periyot_plan.setStyleSheet(S["combo"])
        self.cmb_periyot_plan.addItems([
            "Tek Seferlik",
            "3 Ay (Otomatik 4 Plan)",
            "6 Ay (Otomatik 2 Plan)", 
            "1 Yıl (Tek Plan)"
        ])
        self.cmb_periyot_plan.setMinimumHeight(40)
        self.cmb_periyot_plan.currentIndexChanged.connect(self._periyot_plan_degisti)
        self._panel_plan.add_field("Plan Türü", self.cmb_periyot_plan)
        
        root.addWidget(self._panel_plan)

        # ═══════════════════════════════════════════════════════
        #  2. BAKIM TARIH & TİP BİLGİLERİ
        # ═══════════════════════════════════════════════════════
        self._panel_tarih = self._create_panel("Bakım Bilgileri")
        
        # Planlanan Tarih
        self.dt_plan = QDateEdit(QDate.currentDate())
        self.dt_plan.setCalendarPopup(True)
        self.dt_plan.setDisplayFormat("ddd, d MMMM yyyy")
        self.dt_plan.setStyleSheet(S["date"])
        self.dt_plan.setMinimumHeight(36)
        self._panel_tarih.add_field("Planlanan Tarih", self.dt_plan)
        
        # Bakım Tipi
        self.txt_tip = QLineEdit()
        self.txt_tip.setStyleSheet(S["input"])
        self.txt_tip.setPlaceholderText("Periyodik, Rutin, Acil, İyileştirme")
        self.txt_tip.setMinimumHeight(36)
        self._panel_tarih.add_field("Bakım Tipi", self.txt_tip)
        
        # Bakım Periyodu
        self.txt_periyot = QLineEdit()
        self.txt_periyot.setStyleSheet(S["input"])
        self.txt_periyot.setPlaceholderText("3 Ay, 6 Ay, 1 Yıl")
        self.txt_periyot.setReadOnly(True)
        self.txt_periyot.setMinimumHeight(36)
        self._panel_tarih.add_field("Bakım Periyodu", self.txt_periyot)
        
        # Bakım Sırası
        self.txt_sira = QLineEdit()
        self.txt_sira.setStyleSheet(S["input"])
        self.txt_sira.setReadOnly(True)
        self.txt_sira.setMinimumHeight(36)
        self._panel_tarih.add_field("Bakım Sırası", self.txt_sira)
        
        # Bakım Açıklaması
        self.txt_bakim = QLineEdit()
        self.txt_bakim.setStyleSheet(S["input"])
        self.txt_bakim.setPlaceholderText("Bakım hakkında kısa açıklama (isteğe bağlı)")
        self.txt_bakim.setMinimumHeight(36)
        self._panel_tarih.add_full_width_field("Bakım Açıklaması", self.txt_bakim)
        
        root.addWidget(self._panel_tarih)

        # ═══════════════════════════════════════════════════════
        #  3. İŞLEM DETAYLARI (Yapılan İşlemler, Durumu)
        # ═══════════════════════════════════════════════════════
        self._panel_islem = self._create_panel("🔨 İşlem Detayları")
        
        # Durum
        self.cmb_durum = QComboBox()
        self.cmb_durum.setStyleSheet(S["combo"])
        self.cmb_durum.addItems(["Planlandı", "Yapıldı", "Gecikmiş"])
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
        if self._action_guard:
            self._action_guard.disable_if_unauthorized(btn_kaydet, "cihaz.write")
        btns.addWidget(btn_kaydet)
        
        root.addWidget(btn_container)
        root.addStretch()

    def _create_panel(self, title: str) -> FormPanel:
        """Panel oluşturur."""
        return FormPanel(title)

    def _load_cihaz_list(self):
        """Cihaz listesini veritabanından yükler."""
        if not self._db:
            logger.warning("Veritabanı bağlantısı yok, cihaz listesi yüklenemedi.")
            self.cmb_cihaz_sec.addItem("⚠️ Veritabanı bağlantısı yok", None)
            return
        try:
            repo = RepositoryRegistry(self._db).get("Cihazlar")
            cihazlar = repo.get_all() or []
            
            self.cmb_cihaz_sec.clear()
            self.cmb_cihaz_sec.addItem("-- Cihaz Seçiniz --", None)
            
            if not cihazlar:
                logger.warning("Veritabanında cihaz bulunamadı.")
                self.cmb_cihaz_sec.addItem("⚠️ Cihaz bulunamadı", None)
                return
            
            for cihaz in cihazlar:
                cihaz_id = cihaz.get("Cihazid", "")
                marka = cihaz.get("Marka", "")
                
                if cihaz_id:
                    label = f"{cihaz_id} - {marka}"
                    self.cmb_cihaz_sec.addItem(label, cihaz_id)
            
            # Eğer dışarıdan cihaz_id geliyorsa bunu seç
            if self._cihaz_id:
                for i in range(self.cmb_cihaz_sec.count()):
                    if self.cmb_cihaz_sec.itemData(i) == self._cihaz_id:
                        self.cmb_cihaz_sec.setCurrentIndex(i)
                        break
            
            logger.info(f"Cihaz listesi yüklendi: {len(cihazlar)} cihaz")
        except Exception as e:
            logger.error(f"Cihaz listesi yüklenemedi: {e}")
            self.cmb_cihaz_sec.addItem(f"❌ Hata: {str(e)[:50]}", None)

    def _set_mode_ui(self):
        """Forma göre alanları etkinleştir/devre dışı bırak."""
        if self._mode == FormMode.PLAN_CREATION:
            # Plan oluşturma modu — cihaz/plan seçimi görünür, işlem panelleri gizli
            self._panel_plan.setVisible(True)
            self._panel_tarih.setVisible(True)
            self.cmb_cihaz_sec.setEnabled(True)
            self.cmb_periyot_plan.setEnabled(True)
            self.dt_plan.setEnabled(True)
            self.txt_tip.setEnabled(True)
            self.txt_bakim.setEnabled(True)
            self._panel_islem.setVisible(False)
            self._panel_teknis.setVisible(False)

        elif self._mode == FormMode.EXECUTION_INFO:
            # Bilgi giriş modu — plan bilgileri zaten header'da gösteriliyor,
            # burada sadece editable paneller görünür
            self._panel_plan.setVisible(False)
            self._panel_tarih.setVisible(False)
            self._panel_islem.setVisible(True)
            self._panel_teknis.setVisible(True)
            # Editable alanlar aktif
            self.cmb_durum.setEnabled(True)
            self.dt_bakim.setEnabled(True)
            self.txt_islemler.setEnabled(True)
            self.txt_aciklama.setEnabled(True)
            self.txt_teknisyen.setEnabled(True)
            # Plan verilerini doldur (hesaplanan alanlar için hâlâ gerekli)
            self._load_plan_data()

    def _load_plan_data(self):
        """Seçilen plan verilerini forma doldurur."""
        if not self._plan_data:
            return
        
        # Cihaz combo'sunu plan verisindeki cihaza ayarla
        cihaz_id = self._plan_data.get("Cihazid", "")
        if cihaz_id:
            for i in range(self.cmb_cihaz_sec.count()):
                if self.cmb_cihaz_sec.itemData(i) == cihaz_id:
                    self.cmb_cihaz_sec.setCurrentIndex(i)
                    break
        
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
        if self._action_guard and not self._action_guard.check_and_warn(
            self, "cihaz.write", "Bakim Kaydetme"
        ):
            return
        if not self._db:
            QMessageBox.warning(self, "Uyarı", "Veritabanı bağlantısı yok.")
            return
        
        # Cihaz seçimi kontrolü - PLAN_CREATION modunda combo'dan, EXECUTION_INFO'da plan_data'dan
        cihaz_id = None
        if self._mode == FormMode.PLAN_CREATION:
            cihaz_id = self.cmb_cihaz_sec.currentData()
            if not cihaz_id:
                QMessageBox.warning(self, "Uyarı", "Lütfen bir cihaz seçiniz.")
                return
        else:
            # Önce plan_data'dan al, yoksa constructor parametresine bak
            cihaz_id = self._plan_data.get("Cihazid") or self._cihaz_id
            if not cihaz_id:
                QMessageBox.warning(self, "Uyarı", "Cihaz bilgisi bulunamadı.")
                return
        
        # Seçilen cihaz_id'yi geçici olarak sakla
        self._selected_cihaz_id = cihaz_id

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
            s_durum = durum if i == 0 else "Planlandı"
            s_dosya = dosya_link if i == 0 else "-"
            s_yapilan = yapilan if i == 0 else "-"
            s_aciklama = aciklama if i == 0 else "-"
            s_teknisyen = teknisyen if i == 0 else "-"
            s_bakim_tarihi = bakim_tarihi if i == 0 else ""

            planid = f"{self._selected_cihaz_id}-BK-{base_id + i}"

            kayit = {
                "Planid":          planid,
                "Cihazid":         self._selected_cihaz_id,
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
