# -*- coding: utf-8 -*-
"""
Ariza Kayit
============
Yeni tasarım:
  • Üstte KPI şeridi (Toplam / Açık-Kritik / Ort. Çözüm / Bu Ay Kapandı / Yinelenen)
  • Sol: filtreler (Durum + Öncelik + Cihaz + Arama) + renk kodlu tablo
  • Sağ: her zaman görünür detay başlığı → butanlar → ArizaIslemPenceresi
  • Form'lar toggle yerine kaydırılabilir alanda açılır/kapanır
"""
from typing import List, Dict, Any, Optional
from pathlib import Path
from collections import defaultdict
from datetime import datetime, timedelta

from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex, Signal, QRect
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame,
    QTableView, QSplitter, QHeaderView, QTabWidget,
    QLabel, QLineEdit, QComboBox, QPushButton,
    QMenu, QMessageBox, QSizePolicy, QScrollArea, QGridLayout,
    QGroupBox, QTextEdit, QDialog,
)
from PySide6.QtGui import QColor, QCursor, QPainter, QPen, QBrush

from core.date_utils import to_ui_date
from core.logger import logger
from core.paths import DATA_DIR
from core.services.ariza_service import ArizaService
from ui.components.base_table_model import BaseTableModel
from ui.pages.cihaz.components.ariza_duzenle_form import ArizaDuzenleForm
from ui.styles.colors import C as _C
from ui.styles.components import STYLES as S
from ui.styles import DarkTheme
from ui.pages.cihaz.ariza_islem import ArizaIslemPenceresi, ArizaIslemForm


_DURUM_COLOR = {
    "Açık":           _C["red"],
    "Acik":           _C["red"],
    "Devam Ediyor":   _C["amber"],
    "Kapalı":         _C["green"],
    "Kapali":         _C["green"],
}

_DURUM_BG_COLOR = {
    "Açık":           "rgba(247, 95, 95, 0.20)",      # Düşük opacity kırmızı
    "Acik":           "rgba(247, 95, 95, 0.20)",
    "Devam Ediyor":   "rgba(245, 166, 35, 0.20)",     # Düşük opacity sarı
    "Kapalı":         "rgba(62, 207, 142, 0.20)",     # Düşük opacity yeşil
    "Kapali":         "rgba(62, 207, 142, 0.20)",
}

_ONCELIK_COLOR = {
    "Kritik":  _C["red"],
    "Yüksek":  _C["amber"],
    "Orta":    _C["accent"],
    "Düşük":   _C["muted"],
}

_ONCELIK_BG_COLOR = {
    "Kritik":  "rgba(247, 95, 95, 0.20)",          # Düşük opacity kırmızı
    "Yüksek":  "rgba(245, 166, 35, 0.20)",         # Düşük opacity sarı
    "Orta":    "rgba(79, 142, 247, 0.20)",         # Düşük opacity mavi
    "Düşük":   "rgba(90, 98, 120, 0.15)",          # Düşük opacity gri
}


# ─────────────────────────────────────────────────────────────
#  Tablo kolonları
# ─────────────────────────────────────────────────────────────
ARIZA_COLUMNS = [
    ("Arizaid",         "Arıza No",    90),
    ("Cihazid",         "Cihaz",       110),
    ("BaslangicTarihi", "Tarih",       100),
    ("ArizaTipi",       "Tip",         120),
    ("Oncelik",         "Öncelik",     90),
    ("Baslik",          "Başlık",      220),
    ("Durum",           "Durum",       110),
]


# ─────────────────────────────────────────────────────────────
#  Model
# ─────────────────────────────────────────────────────────────
class ArizaTableModel(BaseTableModel):
    DATE_KEYS = frozenset({"BaslangicTarihi"})
    def __init__(self, rows: Optional[List[Dict[str, Any]]] = None, parent=None):
        super().__init__(ARIZA_COLUMNS, rows, parent)

    def _display(self, key, row):
        val = row.get(key, "")
        if key == "BaslangicTarihi":
            return self._fmt_date(val, "")
        return str(val) if val else ""

    def _fg(self, key, row):
        if key == "Durum":
            return self._status_fg(row.get("Durum", ""))
        if key == "Oncelik":
            c = _ONCELIK_COLOR.get(row.get("Oncelik", ""))
            return QColor(c) if c else None
        return None

    def _bg(self, key, row):
        if key == "Durum":
            bg = _DURUM_BG_COLOR.get(row.get("Durum", ""))
            return QColor(bg) if bg else None
        if key == "Oncelik":
            bg = _ONCELIK_BG_COLOR.get(row.get("Oncelik", ""))
            return QColor(bg) if bg else None
        return None

    def _align(self, key):
        if key in ("BaslangicTarihi", "Oncelik", "Durum"):
            return Qt.AlignmentFlag.AlignCenter
        return Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft

    def set_rows(self, rows: List[Dict[str, Any]]):
        self.set_data(rows)

    def all_rows(self) -> List[Dict[str, Any]]:
        return self.all_data()


# ─────────────────────────────────────────────────────────────
#  Ana Form
# ─────────────────────────────────────────────────────────────
class ArizaKayitForm(QWidget):
    """Arıza listesi, detay paneli ve işlem geçmişi."""

    def __init__(self, db=None, cihaz_id: Optional[str] = None, action_guard=None, parent=None):
        super().__init__(parent)
        self._db               = db
        self._cihaz_id         = cihaz_id
        self._action_guard     = action_guard
        self._rows: List[Dict] = []
        self._all_rows: List[Dict] = []        # filtresiz tüm veriler (KPI için)
        self._selected_ariza_id: Optional[str] = None
        
        # Service layer
        if db:
            from core.di import get_cihaz_service as _gcf4
            self._cihaz_svc = _gcf4(db)
            self._svc = ArizaService(self._cihaz_svc._r)
        else:
            self._svc = None

        self._base_docs_dir = Path(DATA_DIR) / "offline_uploads" / "cihazlar" / "belgeler"
        self._base_docs_dir.mkdir(parents=True, exist_ok=True)
        self._docs_dir = (
            self._base_docs_dir / cihaz_id if cihaz_id else self._base_docs_dir
        )
        self._docs_dir.mkdir(parents=True, exist_ok=True)

        self._active_form: Optional[QWidget] = None

        self._setup_ui()
        self._load_filter_combos()
        self._load_data()
        self._update_perf_tab_label()

    # ══════════════════════════════════════════════════════
    #  Dışarıdan erişim
    # ══════════════════════════════════════════════════════
    def set_cihaz_id(self, cihaz_id: Optional[str]):
        self._cihaz_id = cihaz_id
        if cihaz_id:
            self._docs_dir = self._base_docs_dir / cihaz_id
            self._docs_dir.mkdir(parents=True, exist_ok=True)
        self._load_filter_combos()
        self._load_data()
        self._update_perf_tab_label()

    # ══════════════════════════════════════════════════════
    #  UI İnşaası
    # ══════════════════════════════════════════════════════
    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── KPI Şeridi (her iki tabda da görünür) ───────
        root.addWidget(self._build_kpi_bar())

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFixedHeight(1)
        sep.setStyleSheet(
            f"background:{getattr(DarkTheme,'BORDER','#242938')};"
        )
        root.addWidget(sep)

        # ── Sekmeli Ana Alan ────────────────────────────
        self._tabs = QTabWidget()
        self._tabs.setStyleSheet(S.get("tab", ""))
        self._tabs.currentChanged.connect(self._on_tab_changed)

        # Tab 1 — Arıza Listesi
        list_tab = QWidget()
        lt_layout = QVBoxLayout(list_tab)
        lt_layout.setContentsMargins(0, 0, 0, 0)
        lt_layout.setSpacing(0)
        self._h_splitter = QSplitter(Qt.Orientation.Horizontal)
        self._h_splitter.setStyleSheet(S.get("splitter", ""))
        self._h_splitter.addWidget(self._build_left_panel())
        self._h_splitter.addWidget(self._build_form_panel())   # orta: gizli form
        self._h_splitter.addWidget(self._build_right_panel())
        self._h_splitter.setHandleWidth(0)          # handle görünmez
        self._h_splitter.setChildrenCollapsible(False)
        for i in range(3):
            self._h_splitter.handle(i).setEnabled(False)   # sürükleme kapalı
        self._h_splitter.setSizes([710, 0, 350])
        lt_layout.addWidget(self._h_splitter)
        self._tabs.addTab(list_tab, "Arıza Listesi")

        # Tab 2 — Cihaz Performansı
        self._perf_tab = self._build_perf_tab()
        self._tabs.addTab(self._perf_tab, "Cihaz Performansı")

        root.addWidget(self._tabs, 1)

    def _on_tab_changed(self, idx: int):
        """Performans/Geçmiş tabına geçilince verileri yenile."""
        if idx == 1:
            self._refresh_perf_tab()

    def _update_perf_tab_label(self):
        """cihaz_id varsa tab adını 'Arıza Geçmişi', yoksa 'Cihaz Performansı' yap."""
        if hasattr(self, "_tabs"):
            label = "Arıza Geçmişi" if self._cihaz_id else "Cihaz Performansı"
            self._tabs.setTabText(1, label)

    # ── KPI Şeridi ──────────────────────────────────────
    def _build_kpi_bar(self) -> QWidget:
        bar = QWidget()
        bar.setFixedHeight(68)
        bar.setStyleSheet(
            f"background:{getattr(DarkTheme,'SURFACE','#13161d')};"
        )
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(1)

        self._kpi_labels: Dict[str, QLabel] = {}
        cards = [
            ("toplam",    "TOPLAM ARIZA",      "0",  _C["accent"]),
            ("acik",      "AÇIK / KRİTİK",     "0 / 0", _C["red"]),
            ("ort_sure",  "ORT. ÇÖZÜM",        "— gün", _C["amber"]),
            ("kapali_ay", "BU AY KAPANDI",      "0",  _C["green"]),
            ("yinelenen", "YİNELENEN ARIZA",   "0",  _C["red"]),
        ]
        for key, title, default, color in cards:
            card = self._make_kpi_card(key, title, default, color)
            layout.addWidget(card, 1)

        return bar

    def _make_kpi_card(self, key: str, title: str, default: str, color: str) -> QWidget:
        card = QWidget()
        card.setStyleSheet(
            f"QWidget{{background:{getattr(DarkTheme,'PANEL','#191d26')};"
            f"border-radius:6px; margin:0 2px;}}"
            f"QWidget:hover{{background:{getattr(DarkTheme,'BORDER','#242938')};}} "
        )
        vl = QVBoxLayout(card)
        vl.setContentsMargins(10, 6, 10, 6)
        vl.setSpacing(2)

        lbl_title = QLabel(title)
        lbl_title.setStyleSheet(
            f"font-size:9px; font-weight:600; letter-spacing:0.06em;"
            f"color:{_C['muted']}; background:transparent;"
        )
        val_lbl = QLabel(default)
        val_lbl.setStyleSheet(
            f"font-size:18px; font-weight:700; color:{color}; background:transparent;"
        )
        vl.addWidget(lbl_title)
        vl.addWidget(val_lbl)
        self._kpi_labels[key] = val_lbl
        return card

    def _update_kpi(self):
        """_all_rows verisiyle KPI kartlarını günceller."""
        rows = self._all_rows
        if not rows:
            for k, v in [("toplam","0"),("acik","0 / 0"),("ort_sure","— gün"),("kapali_ay","0"),("yinelenen","0")]:
                self._kpi_labels[k].setText(v)
            return

        toplam  = len(rows)
        acik    = sum(1 for r in rows if r.get("Durum","") in ("Açık","Acik"))
        kritik  = sum(1 for r in rows if r.get("Oncelik","") == "Kritik"
                      and r.get("Durum","") in ("Açık","Acik","Devam Ediyor"))

        # Ortalama çözüm süresi (kapalı arızalar, BaslangicTarihi → bugün proxy)
        sure_list = []
        for r in rows:
            if r.get("Durum","") in ("Kapalı","Kapali"):
                t = r.get("BaslangicTarihi","")
                if t and len(t) >= 10:
                    try:
                        start = datetime.strptime(t[:10], "%Y-%m-%d")
                        sure_list.append((datetime.now() - start).days)
                    except ValueError:
                        pass
        ort_sure = f"{round(sum(sure_list)/len(sure_list),1)} gün" if sure_list else "— gün"

        # Bu ay kapatılan
        now = datetime.now()
        kapali_ay = sum(
            1 for r in rows
            if r.get("Durum","") in ("Kapalı","Kapali")
            and (r.get("BaslangicTarihi","") or "")[:7] == now.strftime("%Y-%m")
        )

        # Yinelenen: aynı Cihazid'de 2+ arıza
        cihaz_cnt = defaultdict(int)
        for r in rows:
            cihaz_cnt[r.get("Cihazid","")] += 1
        yinelenen = sum(1 for c in cihaz_cnt.values() if c >= 2)

        self._kpi_labels["toplam"].setText(str(toplam))
        self._kpi_labels["acik"].setText(f"{acik} / {kritik}")
        self._kpi_labels["ort_sure"].setText(ort_sure)
        self._kpi_labels["kapali_ay"].setText(str(kapali_ay))
        self._kpi_labels["yinelenen"].setText(str(yinelenen))

    # ── Sol Panel (Filtreler + Tablo) ───────────────────
    def _build_left_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Filtre satırı
        filter_bar = QWidget()
        filter_bar.setStyleSheet(
            f"background:{getattr(DarkTheme,'SURFACE','#13161d')};"
            f"border-bottom:1px solid {getattr(DarkTheme,'BORDER','#242938')};"
        )
        fb_layout = QHBoxLayout(filter_bar)
        fb_layout.setContentsMargins(10, 6, 10, 6)
        fb_layout.setSpacing(8)

        # Arama
        self.txt_filter = QLineEdit()
        self.txt_filter.setPlaceholderText("🔍  Arıza No, Cihaz, Başlık…")
        self.txt_filter.setStyleSheet(S["input"])
        self.txt_filter.setMaximumWidth(220)
        self.txt_filter.textChanged.connect(self._apply_filters)
        fb_layout.addWidget(self.txt_filter)

        # Durum filtresi
        self.cmb_durum_filter = QComboBox()
        self.cmb_durum_filter.setStyleSheet(S["combo"])
        self.cmb_durum_filter.setFixedWidth(160)
        self.cmb_durum_filter.addItem("Tüm Durumlar", None)
        self.cmb_durum_filter.currentIndexChanged.connect(self._apply_filters)
        fb_layout.addWidget(self.cmb_durum_filter)

        # Öncelik filtresi
        self.cmb_oncelik_filter = QComboBox()
        self.cmb_oncelik_filter.setStyleSheet(S["combo"])
        self.cmb_oncelik_filter.setFixedWidth(150)
        for lbl, val in [("Tüm Öncelikler", None), ("Kritik", "Kritik"),
                          ("Yüksek", "Yüksek"), ("Orta", "Orta"), ("Düşük", "Düşük")]:
            self.cmb_oncelik_filter.addItem(lbl, val)
        self.cmb_oncelik_filter.currentIndexChanged.connect(self._apply_filters)
        fb_layout.addWidget(self.cmb_oncelik_filter)

        # Cihaz filtresi — sadece genel görünümde (cihaz_id yokken)
        self.cmb_cihaz_filter = QComboBox()
        self.cmb_cihaz_filter.setStyleSheet(S["combo"])
        self.cmb_cihaz_filter.setFixedWidth(150)
        self.cmb_cihaz_filter.addItem("Tüm Cihazlar", None)
        self.cmb_cihaz_filter.currentIndexChanged.connect(self._apply_filters)
        self.cmb_cihaz_filter.setVisible(not bool(self._cihaz_id))
        fb_layout.addWidget(self.cmb_cihaz_filter)

        fb_layout.addStretch()

        # Yeni Arıza butonu
        self.btn_yeni_ariza = QPushButton("+ Yeni Arıza")
        self.btn_yeni_ariza.setStyleSheet(S.get("btn_primary", ""))
        self.btn_yeni_ariza.clicked.connect(self._open_ariza_form)
        if self._action_guard:
            self._action_guard.disable_if_unauthorized(self.btn_yeni_ariza, "cihaz.write")
        fb_layout.addWidget(self.btn_yeni_ariza)

        layout.addWidget(filter_bar)

        # Tablo
        self._model = ArizaTableModel()
        self.table = QTableView()
        self.table.setModel(self._model)
        self.table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        self.table.setStyleSheet(S["table"])
        self.table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self._model.setup_columns(self.table)

        self.table.selectionModel().currentChanged.connect(self._on_row_selected)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)
        layout.addWidget(self.table, 1)

        # Alt sayaç
        self.lbl_count = QLabel("0 kayıt")
        self.lbl_count.setStyleSheet(
            f"font-size:11px; color:{_C['muted']};"
            f"padding:4px 10px;"
            f"background:{getattr(DarkTheme,'SURFACE','#13161d')};"
            f"border-top:1px solid {getattr(DarkTheme,'BORDER','#242938')};"
        )
        layout.addWidget(self.lbl_count)

        return panel

    # ── Sağ Panel (Detay + İşlem) ───────────────────────
    def _build_form_panel(self) -> QWidget:
        """
        Tablo ile detay paneli arasında açılan form alanı.
        Başlangıçta gizlidir; _open_ariza_form / _open_islem_form ile gösterilir.
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
        hdr.setStyleSheet("border-bottom: 1px solid {border};")
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

    def _build_right_panel(self) -> QWidget:
        panel = QWidget()
        panel.setStyleSheet(
            f"background:{getattr(DarkTheme,'SURFACE','#13161d')};"
            f"border-left:1px solid {getattr(DarkTheme,'BORDER','#242938')};"
        )
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # -- Detay Başlığı --
        self._det_header = QWidget()
        self._det_header.setStyleSheet(
            f"background:{getattr(DarkTheme,'PANEL','#191d26')};"
            f"border-bottom:1px solid {getattr(DarkTheme,'BORDER','#242938')};"
        )
        dh_layout = QVBoxLayout(self._det_header)
        dh_layout.setContentsMargins(14, 10, 14, 10)
        dh_layout.setSpacing(6)

        self.lbl_det_title = QLabel("— Bir arıza seçin —")
        self.lbl_det_title.setStyleSheet(
            "font-size:13px; font-weight:600; color:"
            + getattr(DarkTheme, "TEXT_PRIMARY", "#eef0f5") + ";"
        )
        self.lbl_det_title.setWordWrap(True)
        dh_layout.addWidget(self.lbl_det_title)

        # Meta satırı (ID · Tarih · Tip · Öncelik · Durum)
        meta_row = QHBoxLayout()
        meta_row.setSpacing(10)
        self.lbl_det_id     = self._meta_lbl("—")
        self.lbl_det_tarih  = self._meta_lbl("—")
        self.lbl_det_tip    = self._meta_lbl("—")
        self.lbl_det_onc    = self._meta_lbl("—")
        self.lbl_det_durum  = self._meta_lbl("—")
        for w in [self.lbl_det_id, self.lbl_det_tarih,
                  self.lbl_det_tip, self.lbl_det_onc, self.lbl_det_durum]:
            meta_row.addWidget(w)
        meta_row.addStretch()
        dh_layout.addLayout(meta_row)

        # Bildiren + Açıklama
        info_grid = QHBoxLayout()
        info_grid.setSpacing(20)
        self.lbl_det_bildiren = self._field_lbl("Bildiren", "—")
        self.lbl_det_saat     = self._field_lbl("Saat", "—")
        info_grid.addWidget(self.lbl_det_bildiren)
        info_grid.addWidget(self.lbl_det_saat)
        info_grid.addStretch()
        dh_layout.addLayout(info_grid)

        self.lbl_det_aciklama = QLabel("")
        self.lbl_det_aciklama.setWordWrap(True)
        self.lbl_det_aciklama.setStyleSheet(
            f"font-size:11px; color:{_C['muted']}; padding-top:2px;"
        )
        dh_layout.addWidget(self.lbl_det_aciklama)

        layout.addWidget(self._det_header)

        # -- İşlem Ekle butonu --
        btn_bar = QWidget()
        btn_bar.setStyleSheet(
            f"background:{getattr(DarkTheme,'SURFACE','#13161d')};"
            f"border-bottom:1px solid {getattr(DarkTheme,'BORDER','#242938')};"
        )
        bb_layout = QHBoxLayout(btn_bar)
        bb_layout.setContentsMargins(10, 6, 10, 6)
        bb_layout.setSpacing(8)

        lbl_islem_title = QLabel("İşlem Geçmişi")
        lbl_islem_title.setStyleSheet(
            f"font-size:11px; font-weight:600; color:{getattr(DarkTheme,'TEXT_SECONDARY','#c8cdd8')};"
        )
        bb_layout.addWidget(lbl_islem_title)
        bb_layout.addStretch()

        self.btn_islem_ekle = QPushButton("+ İşlem Ekle")
        self.btn_islem_ekle.setStyleSheet(S.get("btn_secondary", S.get("btn_primary", "")))
        self.btn_islem_ekle.setEnabled(False)
        self.btn_islem_ekle.clicked.connect(self._open_islem_form)
        if self._action_guard:
            self._action_guard.disable_if_unauthorized(self.btn_islem_ekle, "cihaz.write")
        bb_layout.addWidget(self.btn_islem_ekle)

        layout.addWidget(btn_bar)

        # -- İşlem penceresi (tam yükseklik, form artık ortada açılıyor) --
        self.islem_penceresi = ArizaIslemPenceresi(self._db)
        layout.addWidget(self.islem_penceresi, 1)
        return panel

    # ── Küçük yardımcı widget üreticileri ───────────────
    def _meta_lbl(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet(
            f"font-size:11px; color:{_C['muted']};"
            f"background:{getattr(DarkTheme,'PANEL','#191d26')};"
        )
        return lbl

    def _field_lbl(self, title: str, value: str) -> QWidget:
        w = QWidget()
        w.setProperty("bg-role", "panel")
        w.style().unpolish(w)
        w.style().polish(w)
        vl = QVBoxLayout(w)
        vl.setContentsMargins(0, 0, 0, 0)
        vl.setSpacing(1)
        t = QLabel(title.upper())
        t.setStyleSheet(
            f"font-size:9px; letter-spacing:0.06em; color:{_C['muted']}; font-weight:600;"
        )
        v = QLabel(value)
        v.setProperty("color-role", "primary")
        v.setStyleSheet("font-size: 12px;")
        v.style().unpolish(v)
        v.style().polish(v)
        vl.addWidget(t)
        vl.addWidget(v)
        w.setProperty("val_lbl", v)   # değere erişmek için
        return w

    # ══════════════════════════════════════════════════════
    #  Filtre yükleme
    # ══════════════════════════════════════════════════════
    def _load_filter_combos(self):
        """Sabitler'den durum listesi; cihaz filtresini _all_rows'dan doldurur."""
        # Durum filtresi
        self.cmb_durum_filter.blockSignals(True)
        self.cmb_durum_filter.clear()
        self.cmb_durum_filter.addItem("Tüm Durumlar", None)
        if self._db and self._svc:
            try:
                durumlar = self._svc.get_ariza_durumlari()
                for durum in durumlar:
                    self.cmb_durum_filter.addItem(durum, durum)
            except Exception as e:
                logger.error(f"Durum filtresi yüklenemedi: {e}")
        self.cmb_durum_filter.blockSignals(False)

        # Cihaz filtresi görünürlüğü
        self.cmb_cihaz_filter.setVisible(not bool(self._cihaz_id))

    def _refresh_cihaz_filter(self):
        """_all_rows'daki cihazları combobox'a doldurur."""
        self.cmb_cihaz_filter.blockSignals(True)
        self.cmb_cihaz_filter.clear()
        self.cmb_cihaz_filter.addItem("Tüm Cihazlar", None)
        cihazlar = sorted({str(r.get("Cihazid","")) for r in self._all_rows if r.get("Cihazid")})
        for c in cihazlar:
            self.cmb_cihaz_filter.addItem(c, c)
        self.cmb_cihaz_filter.blockSignals(False)

    # ══════════════════════════════════════════════════════
    #  Veri yükleme & filtreleme
    # ══════════════════════════════════════════════════════
    def _load_data(self):
        if not self._db or not self._svc:
            self._all_rows = []
            self._rows = []
            self._model.set_rows([])
            self.lbl_count.setText("0 kayıt")
            self._update_kpi()
            return
        try:
            rows = self._svc.get_ariza_listesi(self._cihaz_id)
            self._all_rows = rows
            self._refresh_cihaz_filter()
            self._update_kpi()
            self._apply_filters()
            if rows:
                self.table.selectRow(0)
        except Exception as e:
            logger.error(f"Arıza kayıtları yüklenemedi: {e}")
            self._all_rows = []
            self._model.set_rows([])
            self.lbl_count.setText("0 kayıt")

    def _apply_filters(self):
        filtered = list(self._all_rows)

        # Durum
        sel_durum = self.cmb_durum_filter.currentData()
        if sel_durum:
            filtered = [r for r in filtered if r.get("Durum","") == sel_durum]

        # Öncelik
        sel_onc = self.cmb_oncelik_filter.currentData()
        if sel_onc:
            filtered = [r for r in filtered if r.get("Oncelik","") == sel_onc]

        # Cihaz
        if not self._cihaz_id:
            sel_cihaz = self.cmb_cihaz_filter.currentData()
            if sel_cihaz:
                filtered = [r for r in filtered if str(r.get("Cihazid","")) == sel_cihaz]

        # Metin
        txt = self.txt_filter.text().strip().lower()
        if txt:
            filtered = [
                r for r in filtered
                if txt in str(r.get("Arizaid","")).lower()
                or txt in str(r.get("Cihazid","")).lower()
                or txt in str(r.get("Baslik","")).lower()
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
        ariza_id = row.get("Arizaid")
        self._selected_ariza_id = ariza_id
        self._update_detail(row)
        if ariza_id:
            self.islem_penceresi.set_ariza_id(ariza_id)
        self.btn_islem_ekle.setEnabled(bool(ariza_id))
        if self._action_guard and not self._action_guard.can_perform("cihaz.write"):
            self.btn_islem_ekle.setEnabled(False)

    def _update_detail(self, row: Dict):
        """Sağ paneldeki detay alanlarını seçili arıza ile doldurur."""
        title = f"{row.get('Cihazid','')}  —  {row.get('Baslik','')}"
        self.lbl_det_title.setText(title)

        ariza_id = row.get("Arizaid", "")
        self.lbl_det_id.setText(f"#{ariza_id[-10:] if len(ariza_id)>10 else ariza_id}")

        tarih = to_ui_date(row.get("BaslangicTarihi",""), "")
        self.lbl_det_tarih.setText(f"{tarih}")

        tip = row.get("ArizaTipi","—")
        self.lbl_det_tip.setText(f"{tip}")

        oncelik = row.get("Oncelik","")
        onc_color = _ONCELIK_COLOR.get(oncelik, _C["muted"])
        self.lbl_det_onc.setText(oncelik or "—")
        self.lbl_det_onc.setStyleSheet(
            f"font-size:11px; font-weight:700; color:{onc_color};"
            f"background:{getattr(DarkTheme,'PANEL','#191d26')};"
        )

        durum = row.get("Durum","")
        dur_color = _DURUM_COLOR.get(durum, _C["muted"])
        self.lbl_det_durum.setText(f"● {durum}" if durum else "—")
        self.lbl_det_durum.setStyleSheet(
            f"font-size:11px; font-weight:700; color:{dur_color};"
            f"background:{getattr(DarkTheme,'PANEL','#191d26')};"
        )

        # Bildiren / Saat
        bil_val = self.lbl_det_bildiren.property("val_lbl")
        if bil_val:
            bil_val.setText(row.get("Bildiren","—") or "—")
        saat_val = self.lbl_det_saat.property("val_lbl")
        if saat_val:
            saat_val.setText(row.get("Saat","—") or "—")

        aciklama = row.get("ArizaAcikla","") or row.get("Rapor","") or ""
        if len(aciklama) > 180:
            aciklama = aciklama[:180] + "…"
        self.lbl_det_aciklama.setText(aciklama)

    # ══════════════════════════════════════════════════════
    #  Form Açma / Kapama
    # ══════════════════════════════════════════════════════
    def _clear_form_container(self):
        """Form alanını temizler."""
        while self._form_layout.count() > 0:
            item = self._form_layout.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)
        if self._active_form is not None:
            self._active_form.setParent(None)
            self._active_form = None
        self._form_layout.addStretch()

    def _open_ariza_form(self):
        """Yeni Arıza formunu — tablo ile detay arasında — açar."""
        if self._action_guard and not self._action_guard.check_and_warn(
            self, "cihaz.write", "Ariza Kaydi Acma"
        ):
            return
        from ui.pages.cihaz.ariza_girisi_form import ArizaGirisForm
        self._clear_form_container()
        # Cihaz ID: önce self._cihaz_id (cihaz detay modu), yoksa seçili satırdan al
        cihaz_id = self._cihaz_id
        if not cihaz_id and self._selected_ariza_id:
            # seçili satırdan Cihazid'i bul
            for r in self._all_rows:
                if r.get("Arizaid") == self._selected_ariza_id:
                    cihaz_id = str(r.get("Cihazid", ""))
                    break
        form = ArizaGirisForm(self._db, cihaz_id=cihaz_id, action_guard=self._action_guard, parent=self)
        form.saved.connect(self._on_ariza_saved)
        self._active_form = form
        self._form_layout.insertWidget(0, form)
        self._form_panel.setVisible(True)
        self._h_splitter.setSizes([470, 360, 350])

    def _open_islem_form(self):
        """Seçili arıza için İşlem Giriş formunu açar."""
        if self._action_guard and not self._action_guard.check_and_warn(
            self, "cihaz.write", "Ariza Islem Girisi"
        ):
            return
        if not self._selected_ariza_id:
            QMessageBox.warning(self, "Uyarı", "Lütfen önce bir arıza seçin.")
            return
        self._clear_form_container()
        form = ArizaIslemForm(self._db, ariza_id=self._selected_ariza_id, action_guard=self._action_guard, parent=self)
        form.saved.connect(self._on_islem_saved)
        self._active_form = form
        self._form_layout.insertWidget(0, form)
        self._form_panel.setVisible(True)
        self._h_splitter.setSizes([470, 360, 350])

    def _close_form(self):
        """Açık formu kapatır, orta paneli daraltır."""
        self._clear_form_container()
        self._form_panel.setVisible(False)
        self._h_splitter.setSizes([710, 0, 350])

    # ══════════════════════════════════════════════════════
    #  Form kayıt geri çağrıları
    # ══════════════════════════════════════════════════════
    def _on_ariza_saved(self):
        self._close_form()
        self._load_data()
        QMessageBox.information(self, "Başarı", "Arıza başarıyla kaydedildi.")

    def _on_islem_saved(self):
        self._close_form()
        if self._selected_ariza_id:
            self.islem_penceresi.set_ariza_id(self._selected_ariza_id)
        QMessageBox.information(self, "Başarı", "İşlem başarıyla kaydedildi.")

    # ══════════════════════════════════════════════════════
    #  Sağ tık menüsü
    # ══════════════════════════════════════════════════════
    def _show_context_menu(self, pos):
        index = self.table.indexAt(pos)
        if not index.isValid():
            return
        row = self._model.get_row(index.row())
        if not row:
            return

        menu = QMenu(self)
        act_detay = menu.addAction("Detayı Görüntüle")
        act_duzenle = menu.addAction("Düzenle")
        menu.addSeparator()
        act_islem = menu.addAction("Bu Arızaya İşlem Ekle")
        act_hatali = menu.addAction("Hatalı Giriş Olarak İşaretle")
        menu.addSeparator()
        act_ariza = menu.addAction("Yeni Arıza Gir")
        
        result = menu.exec(self.table.mapToGlobal(pos))

        if result == act_detay:
            self._view_ariza_detail(row)
        elif result == act_duzenle:
            self._selected_ariza_id = row.get("Arizaid")
            self._edit_ariza(row)
        elif result == act_islem:
            self._selected_ariza_id = row.get("Arizaid")
            self._open_islem_form()
        elif result == act_hatali:
            self._mark_as_invalid(row)
        elif result == act_ariza:
            self._open_ariza_form()

    def _view_ariza_detail(self, row: Dict):
        """Arıza detaylarını bir modal dialog'unda göster."""
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Arıza Detayı — {row.get('Arizaid', '')}")
        dialog.setMinimumWidth(500)
        dialog.setMinimumHeight(400)
        dialog.setStyleSheet(S["page"])
        
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(S.get("scroll", ""))
        
        content = QWidget()
        content_lay = QVBoxLayout(content)
        content_lay.setSpacing(10)
        
        fields = [
            ("Arıza No", row.get("Arizaid", "—")),
            ("Cihaz", row.get("Cihazid", "—")),
            ("Başlık", row.get("Baslik", "—")),
            ("Arıza Tipi", row.get("ArizaTipi", "—")),
            ("Durum", row.get("Durum", "—")),
            ("Öncelik", row.get("Oncelik", "—")),
            ("Başlangıç Tarihi", to_ui_date(row.get("BaslangicTarihi", ""), "—")),
            ("Saat", row.get("Saat", "—")),
            ("Bildiren", row.get("Bildiren", "—")),
            ("Açıklama", row.get("Aciklama", "—")),
        ]
        
        for label, value in fields:
            frm = QHBoxLayout()
            frm.setSpacing(16)
            
            lbl = QLabel(label)
            lbl.setProperty("color-role", "secondary")
            lbl.setStyleSheet("font-weight: 600; min-width: 120px;")
            lbl.style().unpolish(lbl)
            lbl.style().polish(lbl)
            
            val = QLabel(str(value))
            val.setProperty("color-role", "primary")
            val.style().unpolish(val)
            val.style().polish(val)
            val.setWordWrap(True)
            
            frm.addWidget(lbl)
            frm.addWidget(val, 1)
            content_lay.addLayout(frm)
        
        content_lay.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)
        
        btn_kapat = QPushButton("Kapat")
        btn_kapat.setStyleSheet(S.get("cancel_btn", ""))
        btn_kapat.setFixedWidth(100)
        btn_kapat.clicked.connect(dialog.accept)
        
        btn_lay = QHBoxLayout()
        btn_lay.addStretch()
        btn_lay.addWidget(btn_kapat)
        layout.addLayout(btn_lay)
        
        dialog.exec()

    def _edit_ariza(self, row: Dict):
        """Seçili arızayı düzenleme formunu aç."""
        self._clear_form_container()
        
        form = ArizaDuzenleForm(self._db, ariza_data=row, parent=self)
        form.saved.connect(self._on_ariza_saved)
        self._active_form = form
        self._form_layout.insertWidget(0, form)
        self._form_panel.setVisible(True)
        self._h_splitter.setSizes([470, 360, 350])

    def _mark_as_invalid(self, row: Dict):
        """Arızayı 'Hatalı Giriş' olarak işaretle."""
        ariza_id = row.get("Arizaid")
        if not ariza_id or not self._db:
            return
        
        reply = QMessageBox.warning(
            self, 
            "Hatalı Giriş Olarak İşaretle",
            f"Arıza '{ariza_id}' hatalı giriş olarak işaretlenecek. Devam etmek istiyor musunuz?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        try:
            # Service kullanarak güncelle
            success = self._svc.guncelle(ariza_id, {"Durum": "Hatalı Giriş"}) if self._svc else False
            if success:
                logger.info(f"Arıza hatalı giriş olarak işaretlendi: {ariza_id}")
                self._load_data()
                QMessageBox.information(self, "Başarılı", f"Arıza '{ariza_id}' hatalı giriş olarak işaretlendi.")
            else:
                QMessageBox.critical(self, "Hata", "Service kullanılamıyor")
        except Exception as e:
            logger.error(f"Arıza güncellenemedi: {e}")
            QMessageBox.critical(self, "Hata", f"İşaretleme başarısız: {e}")



    def _build_perf_tab(self) -> QWidget:
        """Performans tabının iskeletini oluşturur (içerik _refresh_perf_tab ile dolar)."""
        surface = getattr(DarkTheme, "SURFACE", "#13161d")
        border  = getattr(DarkTheme, "BORDER",  "#242938")

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
            f"color:{getattr(DarkTheme,'TEXT_MUTED','#5a6278')};"
            f"padding-bottom:4px;"
            f"border-bottom:1px solid {getattr(DarkTheme,'BORDER','#242938')};"
        )
        return lbl

    def _refresh_perf_tab(self):
        """_all_rows verisini kullanarak performans/geçmiş tabını yeniden çizer."""
        while self._perf_layout.count():
            item = self._perf_layout.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)

        rows = self._all_rows
        if not rows:
            empty = QLabel("Gösterilecek arıza verisi yok.")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setStyleSheet(
                f"color:{getattr(DarkTheme,'TEXT_MUTED','#5a6278')};font-size:13px;padding:40px;"
            )
            self._perf_layout.addWidget(empty)
            self._perf_layout.addStretch()
            return

        if self._cihaz_id:
            # ── Tek Cihaz: Arıza Geçmişi görünümü ──────
            self._perf_layout.addWidget(
                self._section_title(f"{self._cihaz_id}  —  AYLIK ARIZA TRENDİ")
            )
            self._perf_layout.addWidget(self._build_trend_chart(rows))

            # Özet istatistik kartları
            self._perf_layout.addWidget(
                self._section_title("DURUM DAĞILIMI")
            )
            self._perf_layout.addWidget(self._build_single_cihaz_stats(rows))

            self._perf_layout.addWidget(
                self._section_title("TEKRARLAYAN ARIZALAR (SON 90 GÜN)")
            )
            self._perf_layout.addWidget(self._build_repeat_list(rows))
        else:
            # ── Genel: Cihaz Performansı görünümü ──────
            self._perf_layout.addWidget(
                self._section_title("CİHAZ BAZLI ARIZA DAĞILIMI — SON 12 AY")
            )
            cihaz_data = self._compute_cihaz_stats(rows)
            self._perf_layout.addWidget(self._build_cihaz_grid(cihaz_data))

            self._perf_layout.addWidget(self._section_title("AYLIK ARIZA TRENDİ"))
            self._perf_layout.addWidget(self._build_trend_chart(rows))

            self._perf_layout.addWidget(self._section_title("TEKRARLAYAN ARIZALAR (SON 90 GÜN)"))
            self._perf_layout.addWidget(self._build_repeat_list(rows))

        self._perf_layout.addStretch()

    def _build_single_cihaz_stats(self, rows: List[Dict]) -> QWidget:
        """Tek cihaz için durum dağılımı özet kartları."""
        panel_bg = getattr(DarkTheme, "PANEL",   "#191d26")
        border   = getattr(DarkTheme, "BORDER",  "#242938")
        muted    = getattr(DarkTheme, "TEXT_MUTED", "#5a6278")

        acik     = sum(1 for r in rows if r.get("Durum","") in ("Açık","Acik"))
        devam    = sum(1 for r in rows if r.get("Durum","") == "Devam Ediyor")
        kapali   = sum(1 for r in rows if r.get("Durum","") in ("Kapalı","Kapali"))
        kritik   = sum(1 for r in rows if r.get("Oncelik","") == "Kritik")

        # Ort. çözüm süresi
        sure_list = []
        now = datetime.now()
        for r in rows:
            if r.get("Durum","") in ("Kapalı","Kapali"):
                t = r.get("BaslangicTarihi","")
                if t and len(t) >= 10:
                    try:
                        dt = datetime.strptime(t[:10], "%Y-%m-%d")
                        sure_list.append((now - dt).days)
                    except ValueError:
                        pass
        ort_sure = round(sum(sure_list)/len(sure_list), 1) if sure_list else None

        container = QWidget()
        container.setStyleSheet("background:transparent;")
        hl = QHBoxLayout(container)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setSpacing(8)

        items = [
            ("Toplam",       str(len(rows)),                          _C["accent"]),
            ("Açık",         str(acik),                               _C["red"]),
            ("Devam Ediyor", str(devam),                              _C["amber"]),
            ("Kapandı",      str(kapali),                             _C["green"]),
            ("Kritik",       str(kritik),                             _C["red"]),
            ("Ort. Çözüm",   f"{ort_sure} gün" if ort_sure else "—", _C["amber"]),
        ]
        for title, value, color in items:
            card = QWidget()
            card.setStyleSheet(
                f"background:{panel_bg};border:1px solid {border};border-radius:6px;"
            )
            cl = QVBoxLayout(card)
            cl.setContentsMargins(10, 8, 10, 8)
            cl.setSpacing(2)
            t = QLabel(title.upper())
            t.setStyleSheet(
                f"font-size:9px;font-weight:600;letter-spacing:0.06em;"
                f"color:{muted};background:transparent;"
            )
            v = QLabel(value)
            v.setStyleSheet(
                f"font-size:16px;font-weight:700;color:{color};background:transparent;"
            )
            cl.addWidget(t)
            cl.addWidget(v)
            hl.addWidget(card, 1)

        return container

    # ── Veri hesaplama ──────────────────────────────────
    def _compute_cihaz_stats(self, rows: List[Dict]) -> List[Dict]:
        """Cihaz başına arıza istatistikleri ve 12 aylık trend hesaplar."""
        stats: Dict[str, Dict] = {}
        now = datetime.now()

        for r in rows:
            cid = str(r.get("Cihazid","") or "")
            if not cid:
                continue
            if cid not in stats:
                stats[cid] = {
                    "cihaz": cid,
                    "toplam": 0, "acik": 0, "kritik": 0,
                    "sure_list": [], "ay_trend": defaultdict(int),
                }
            s = stats[cid]
            s["toplam"] += 1

            durum = r.get("Durum","")
            if durum in ("Açık","Acik","Devam Ediyor"):
                s["acik"] += 1
            if r.get("Oncelik","") == "Kritik":
                s["kritik"] += 1

            t = r.get("BaslangicTarihi","")
            if t and len(t) >= 10:
                try:
                    dt = datetime.strptime(t[:10], "%Y-%m-%d")
                    # 12 aylık trend için ay indexi (0=12 ay önce, 11=bu ay)
                    months_ago = (now.year - dt.year) * 12 + (now.month - dt.month)
                    if 0 <= months_ago <= 11:
                        s["ay_trend"][11 - months_ago] += 1
                    # Ortalama çözüm süresi (yaklaşık)
                    if durum in ("Kapalı","Kapali"):
                        s["sure_list"].append((now - dt).days)
                except ValueError:
                    pass

        result = []
        for s in stats.values():
            trend = [s["ay_trend"].get(i, 0) for i in range(12)]
            ort = round(sum(s["sure_list"]) / len(s["sure_list"]), 1) if s["sure_list"] else None
            result.append({**s, "trend": trend, "ort_sure": ort})

        result.sort(key=lambda x: x["toplam"], reverse=True)
        return result

    # ── Cihaz kart grid ─────────────────────────────────
    def _build_cihaz_grid(self, cihaz_data: List[Dict]) -> QWidget:
        panel  = getattr(DarkTheme, "PANEL",        "#191d26")
        border = getattr(DarkTheme, "BORDER",       "#242938")
        text   = getattr(DarkTheme, "TEXT_PRIMARY", "#eef0f5")
        muted  = getattr(DarkTheme, "TEXT_MUTED",   "#5a6278")

        container = QWidget()
        container.setStyleSheet("background: transparent;")
        grid = QGridLayout(container)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(10)

        max_toplam = max((d["toplam"] for d in cihaz_data), default=1)
        cols = 3

        for idx, d in enumerate(cihaz_data):
            row_i, col_i = divmod(idx, cols)

            card = QWidget()
            card.setStyleSheet(
                f"QWidget{{background:{panel};border:1px solid {border};"
                f"border-radius:8px;}}"
            )
            cl = QVBoxLayout(card)
            cl.setContentsMargins(14, 12, 14, 12)
            cl.setSpacing(8)

            # Başlık
            hdr = QHBoxLayout()
            lbl_id = QLabel(d["cihaz"])
            lbl_id.setStyleSheet(
                f"font-size:13px;font-weight:700;color:{text};"
                f"background:transparent;"
            )
            hdr.addWidget(lbl_id)
            hdr.addStretch()
            if d["acik"] > 0:
                badge = QLabel(f"{d['acik']} açık")
                badge.setStyleSheet(
                    f"font-size:10px;font-weight:600;color:{_C['red']};"
                    f"background:{_C['red']}22;border-radius:4px;padding:1px 6px;"
                )
                hdr.addWidget(badge)
            cl.addLayout(hdr)

            # Bar satırları: Toplam / Kritik / Açık
            for lbl_txt, val, color in [
                ("Toplam",  d["toplam"],  _C["accent"]),
                ("Kritik",  d["kritik"],  _C["red"]),
                ("Açık",    d["acik"],    _C["amber"]),
            ]:
                bar_pct = int((val / max_toplam) * 100) if max_toplam else 0
                cl.addWidget(self._bar_row(lbl_txt, val, bar_pct, color, muted, panel))

            # Ortalama çözüm süresi
            ort = d.get("ort_sure")
            if ort is not None:
                ort_color = _C["red"] if ort > 7 else (_C["amber"] if ort > 3 else _C["green"])
                ort_lbl = QLabel(f"Ort. Çözüm:  {ort} gün")
                ort_lbl.setStyleSheet(
                    f"font-size:11px;font-weight:600;color:{ort_color};"
                    f"background:transparent;"
                )
                cl.addWidget(ort_lbl)

            # Sparkline
            spark = _SparklineWidget(d["trend"], parent=card)
            spark.setFixedHeight(32)
            cl.addWidget(spark)

            grid.addWidget(card, row_i, col_i)

        # Boş hücreleri doldur
        remainder = len(cihaz_data) % cols
        if remainder:
            for c in range(remainder, cols):
                placeholder = QWidget()
                placeholder.setStyleSheet("background:transparent;")
                grid.addWidget(placeholder, len(cihaz_data) // cols, c)

        return container

    def _bar_row(self, label, value, pct, fill_color, muted, panel) -> QWidget:
        """Tek bir yatay bar satırı oluşturur."""
        border = getattr(DarkTheme, "BORDER", "#242938")
        w = QWidget()
        w.setStyleSheet("background: transparent;")
        hl = QHBoxLayout(w)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setSpacing(6)

        lbl = QLabel(label)
        lbl.setFixedWidth(46)
        lbl.setStyleSheet("font-size: 10px; background: transparent;")
        hl.addWidget(lbl)

        bar_bg = QWidget()
        bar_bg.setFixedHeight(6)
        bar_bg.setStyleSheet(
            f"background:{border};border-radius:3px;"
        )
        bar_bg.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        bar_fill = QWidget(bar_bg)
        bar_fill.setFixedHeight(6)
        bar_fill.setStyleSheet(
            f"background:{fill_color};border-radius:3px;"
        )
        # Genişliği resizeEvent'e bırakacağız — sabit yüzde ile ayarla
        bar_fill.setFixedWidth(max(4, int(pct * 1.5)))   # ~150px max
        hl.addWidget(bar_bg)

        cnt = QLabel(str(value))
        cnt.setFixedWidth(24)
        cnt.setAlignment(Qt.AlignmentFlag.AlignRight)
        cnt.setStyleSheet("font-size: 10px; font-weight: 600; background: transparent;")
        hl.addWidget(cnt)
        return w

    # ── Aylık trend çubuğu ──────────────────────────────
    def _build_trend_chart(self, rows: List[Dict]) -> QWidget:
        panel  = getattr(DarkTheme, "PANEL",  "#191d26")
        border = getattr(DarkTheme, "BORDER", "#242938")
        muted  = getattr(DarkTheme, "TEXT_MUTED", "#5a6278")

        now = datetime.now()
        ay_sayim = defaultdict(int)
        ay_etiket = {}
        for i in range(12):
            ay_idx = (now.month - 1 - i) % 12
            yil    = now.year if now.month - 1 - i >= 0 else now.year - 1
            anahtar = f"{yil}-{ay_idx+1:02d}"
            konum   = 11 - i
            ay_sayim[konum] = 0
            ay_etiket[konum] = ["Oca","Şub","Mar","Nis","May","Haz",
                                  "Tem","Ağu","Eyl","Eki","Kas","Ara"][ay_idx]

        for r in rows:
            t = r.get("BaslangicTarihi","")
            if t and len(t) >= 7:
                try:
                    dt = datetime.strptime(t[:7], "%Y-%m")
                    months_ago = (now.year - dt.year) * 12 + (now.month - dt.month)
                    if 0 <= months_ago <= 11:
                        ay_sayim[11 - months_ago] += 1
                except ValueError:
                    pass

        degerler = [ay_sayim[i] for i in range(12)]
        etiketler = [ay_etiket[i] for i in range(12)]
        max_val = max(degerler) if any(degerler) else 1

        container = QWidget()
        container.setStyleSheet(
            f"background:{panel};border:1px solid {border};border-radius:8px;"
        )
        cl = QVBoxLayout(container)
        cl.setContentsMargins(16, 14, 16, 14)
        cl.setSpacing(6)

        # Çubuklar + değer etiketleri
        bar_row = QHBoxLayout()
        bar_row.setSpacing(4)
        for i, (val, et) in enumerate(zip(degerler, etiketler)):
            col = QVBoxLayout()
            col.setSpacing(2)
            col.setAlignment(Qt.AlignmentFlag.AlignBottom)

            val_lbl = QLabel(str(val) if val else "")
            val_lbl.setAlignment(Qt.AlignmentFlag.AlignHCenter)
            val_lbl.setStyleSheet(
                f"font-size:9px;color:{muted};background:transparent;"
            )
            col.addWidget(val_lbl)

            bar_color = _C["red"] if val > max_val * 0.7 else \
                        _C["amber"] if val > max_val * 0.4 else _C["accent"]
            bar_h = max(4, int((val / max_val) * 60)) if max_val else 4

            bar = QWidget()
            bar.setFixedSize(16, bar_h)
            bar.setStyleSheet(
                f"background:{bar_color};border-radius:3px 3px 0 0;opacity:0.8;"
            )
            col.addWidget(bar, 0, Qt.AlignmentFlag.AlignHCenter)
            bar_row.addLayout(col)

        cl.addLayout(bar_row)

        # Ay etiketleri
        lbl_row = QHBoxLayout()
        lbl_row.setSpacing(4)
        for et in etiketler:
            lbl = QLabel(et)
            lbl.setAlignment(Qt.AlignmentFlag.AlignHCenter)
            lbl.setStyleSheet(
                f"font-size:9px;color:{muted};background:transparent;"
            )
            lbl_row.addWidget(lbl)
        cl.addLayout(lbl_row)

        return container

    # ── Tekrarlayan arızalar listesi ────────────────────
    def _build_repeat_list(self, rows: List[Dict]) -> QWidget:
        panel  = getattr(DarkTheme, "PANEL",  "#191d26")
        border = getattr(DarkTheme, "BORDER", "#242938")
        text   = getattr(DarkTheme, "TEXT_PRIMARY", "#eef0f5")
        muted  = getattr(DarkTheme, "TEXT_MUTED",   "#5a6278")

        cutoff = datetime.now() - timedelta(days=90)
        recent = []
        for r in rows:
            t = r.get("BaslangicTarihi","")
            if t and len(t) >= 10:
                try:
                    if datetime.strptime(t[:10], "%Y-%m-%d") >= cutoff:
                        recent.append(r)
                except ValueError:
                    pass

        # (Cihazid, Baslik) çiftlerini say
        counter: Dict[tuple, int] = defaultdict(int)
        for r in recent:
            key = (str(r.get("Cihazid","")), str(r.get("Baslik",""))[:40])
            counter[key] += 1

        tekrarlar = sorted(
            [(k, v) for k, v in counter.items() if v >= 2],
            key=lambda x: -x[1]
        )

        container = QWidget()
        container.setStyleSheet("background:transparent;")
        cl = QVBoxLayout(container)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.setSpacing(6)

        if not tekrarlar:
            lbl = QLabel("Son 90 günde tekrarlayan arıza tespit edilmedi.")
            lbl.setStyleSheet("font-size: 12px; padding: 12px;")
            cl.addWidget(lbl)
            return container

        for (cihaz, baslik), sayi in tekrarlar[:10]:
            row_w = QWidget()
            row_w.setStyleSheet(
                f"background:{panel};border:1px solid {border};"
                f"border-radius:6px;"
            )
            rl = QHBoxLayout(row_w)
            rl.setContentsMargins(12, 8, 12, 8)
            rl.setSpacing(12)

            chip = QLabel(cihaz or "—")
            chip.setStyleSheet(
                f"font-size:11px;font-weight:600;color:{_C['accent']};"
                f"background:{_C['accent']}22;border-radius:4px;"
                f"padding:2px 8px;"
            )
            chip.setFixedWidth(80)
            rl.addWidget(chip)

            lbl_baslik = QLabel(baslik)
            lbl_baslik.setStyleSheet("font-size: 12px; background: transparent;")
            lbl_baslik.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Preferred)
            rl.addWidget(lbl_baslik)

            lbl_sayi = QLabel(f"{sayi}× tekrar")
            lbl_sayi.setStyleSheet(
                f"font-size:11px;font-weight:600;color:{_C['red']};background:transparent;"
            )
            rl.addWidget(lbl_sayi)

            cl.addWidget(row_w)

        return container


# ─────────────────────────────────────────────────────────────
#  Sparkline Widget — 12 aylık mini çubuk grafiği
# ─────────────────────────────────────────────────────────────
class _SparklineWidget(QWidget):
    """12 değerden oluşan mini çubuk grafiği."""

    def __init__(self, values: List[int], parent=None):
        super().__init__(parent)
        self._values = values or [0] * 12
        self.setMinimumHeight(28)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        n = len(self._values)
        if n == 0:
            return

        max_v = max(self._values) if any(self._values) else 1
        bar_w = max(2, (w - (n - 1) * 2) // n)
        gap   = 2

        for i, v in enumerate(self._values):
            bar_h  = max(3, int((v / max_v) * (h - 4))) if max_v else 3
            x      = i * (bar_w + gap)
            y      = h - bar_h

            if v > max_v * 0.7:
                color = QColor(_C["red"])
            elif v > max_v * 0.4:
                color = QColor(_C["amber"])
            else:
                color = QColor(_C["accent"])

            color.setAlpha(180)
            painter.fillRect(x, y, bar_w, bar_h, QBrush(color))

        painter.end()


