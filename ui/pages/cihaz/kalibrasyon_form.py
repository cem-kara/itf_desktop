# -*- coding: utf-8 -*-
"""
Kalibrasyon Formu
==================
  • Üstte KPI şeridi (Toplam / Geçerli / Geçersiz / Yaklaşan Bitiş / Son Kalibrasyon)
  • Sol: filtreler (Durum + Cihaz + Arama) + renk kodlu tablo
  • Sağ: QStackedWidget — genişletilmiş detay header + form alanı (exec_content_stack)
  • Tab 2: Kalibrasyon Performansı — marka bazlı grid, trend, yaklaşan bitiş
  • Bitiş tarihi rengi dinamik: geçmiş → kırmızı, 30 gün → turuncu, uzak → yeşil
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict

from PySide6.QtCore import Qt, QDate, QAbstractTableModel, QModelIndex, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame,
    QTableView, QSplitter, QHeaderView, QTabWidget,
    QGroupBox, QGridLayout,
    QLabel, QLineEdit, QComboBox, QDateEdit, QTextEdit,
    QPushButton, QMenu, QMessageBox, QSizePolicy, QScrollArea,
    QStackedWidget,
)
from PySide6.QtGui import QColor, QPainter, QBrush

from core.date_utils import to_ui_date
from core.logger import logger
from core.di import get_cihaz_service
from core.services.kalibrasyon_service import KalibrasyonService
from ui.components.base_table_model import BaseTableModel
from ui.styles.colors import C as _C
from ui.styles import DarkTheme
from ui.styles.icons import IconRenderer


_DURUM_COLOR = {
    "Gecerli":  _C["green"],
    "Geçerli":  _C["green"],
    "Gecersiz": _C["red"],
    "Geçersiz": _C["red"],
}


# ─────────────────────────────────────────────────────────────
#  Tablo kolonları
# ─────────────────────────────────────────────────────────────
KAL_COLUMNS = [
    ("Kalid",        "Kal. No",     90),
    ("Cihazid",      "Cihaz",       110),
    ("Firma",        "Firma",       130),
    ("SertifikaNo",  "Sertifika",   110),
    ("YapilanTarih", "Yapılan",     100),
    ("BitisTarihi",  "Geçerlilik",  100),
    ("Durum",        "Durum",       100),
]


# ─────────────────────────────────────────────────────────────
#  Model
# ─────────────────────────────────────────────────────────────
class KalibrasyonTableModel(BaseTableModel):
    DATE_KEYS = frozenset({"YapilanTarih", "BitisTarihi"})
    def __init__(self, rows: Optional[List[Dict[str, Any]]] = None, parent=None):
        super().__init__(KAL_COLUMNS, rows, parent)

    def _display(self, key, row):
        val = row.get(key, "")
        if key in ("YapilanTarih", "BitisTarihi"):
            return self._fmt_date(val, "")
        return str(val) if val else ""

    def _fg(self, key, row):
        if key == "Durum":
            return self.status_fg(row.get("Durum", ""))
        if key == "BitisTarihi":
            return QColor(_bitis_rengi(row.get("BitisTarihi", "")))
        return None

    def _bg(self, key, row):
        if key == "Durum":
            durum = row.get("Durum", "")
            if durum in ("Gecerli", "Geçerli"):
                return QColor(_C["green"] + "22")
            if durum in ("Gecersiz", "Geçersiz"):
                return QColor(_C["red"] + "22")
        return None

    def _align(self, key):
        if key in ("YapilanTarih", "BitisTarihi", "Durum"):
            return Qt.AlignmentFlag.AlignCenter
        return Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft


def _bitis_rengi(bitis_raw: str) -> str:
    if not bitis_raw or len(bitis_raw) < 10:
        return _C["muted"]
    try:
        bt    = datetime.strptime(bitis_raw[:10], "%Y-%m-%d").date()
        bugun = datetime.now().date()
        if bt < bugun:
            return _C["red"]
        if bt <= bugun + timedelta(days=30):
            return _C["amber"]
        return _C["green"]
    except ValueError:
        return _C["muted"]


# ─────────────────────────────────────────────────────────────
#  Ana Form
# ─────────────────────────────────────────────────────────────
class KalibrasyonKayitForm(QWidget):

    def __init__(self, db=None, cihaz_id: Optional[str] = None, action_guard=None, parent=None):
        super().__init__(parent)
        self._db                             = db
        self._cihaz_id                       = cihaz_id
        self._action_guard                   = action_guard
        self._all_rows: List[Dict]           = []
        self._rows: List[Dict]               = []
        self._selected_row: Optional[Dict]   = None
        self._active_form: Optional[QWidget] = None
        
        # Service layer
        if db:
            self._cihaz_svc = get_cihaz_service(db)
            self._svc = KalibrasyonService(self._cihaz_svc._r)
        else:
            self._svc = None

        self._setup_ui()
        self._load_data()
        self._update_perf_tab_label()

    # ══════════════════════════════════════════════════════
    #  Dışarıdan erişim
    # ══════════════════════════════════════════════════════
    def set_cihaz_id(self, cihaz_id: Optional[str]):
        self._cihaz_id = cihaz_id
        self.cmb_cihaz_filter.setVisible(not bool(cihaz_id))
        self._load_data()
        self._update_perf_tab_label()

    def _on_tab_changed(self, idx: int):
        if idx == 1:
            self._refresh_perf_tab()

    def _update_perf_tab_label(self):
        if hasattr(self, "_tabs"):
            label = "Kalibrasyon Geçmişi" if self._cihaz_id else "Kalibrasyon Performansı"
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
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFixedHeight(1)
        sep.setProperty("bg-role", "separator")
        sep.style().unpolish(sep)
        sep.style().polish(sep)
        root.addWidget(sep)

        self._tabs = QTabWidget()
        self._tabs.currentChanged.connect(self._on_tab_changed)

        # Tab 0 — Kalibrasyon Listesi
        list_tab = QWidget()
        lt_layout = QVBoxLayout(list_tab)
        lt_layout.setContentsMargins(0, 0, 0, 0)
        lt_layout.setSpacing(0)
        self._h_splitter = QSplitter(Qt.Orientation.Horizontal)
        self._h_splitter.addWidget(self._build_left_panel())
        self._h_splitter.addWidget(self._build_right_panel())
        self._h_splitter.setHandleWidth(0)
        self._h_splitter.setChildrenCollapsible(False)
        for i in range(2):
            self._h_splitter.handle(i).setEnabled(False)
        self._h_splitter.setSizes([710, 350])
        lt_layout.addWidget(self._h_splitter)
        self._tabs.addTab(list_tab, "Kalibrasyon Listesi")

        # Tab 1 — Kalibrasyon Performansı
        self._perf_tab = self._build_perf_tab()
        self._tabs.addTab(self._perf_tab, "Kalibrasyon Performansı")

        root.addWidget(self._tabs, 1)

    # ── KPI Şeridi ────────────────────────────────────
    def _build_kpi_bar(self) -> QWidget:
        bar = QWidget()
        bar.setFixedHeight(68)
        bar.setProperty("bg-role", "panel")
        bar.style().unpolish(bar)
        bar.style().polish(bar)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(1)
        self._kpi_labels: Dict[str, QLabel] = {}
        for key, title, default, color in [
            ("toplam",   "TOPLAM",           "0",  _C["accent"]),
            ("gecerli",  "GEÇERLİ",          "0",  _C["green"]),
            ("gecersiz", "GEÇERSİZ",         "0",  _C["red"]),
            ("yaklasan", "YAKLAŞAN BİTİŞ",   "0",  _C["amber"]),
            ("son_kal",  "SON KALİBRASYON",  "—",  _C["muted"]),
        ]:
            layout.addWidget(self._make_kpi_card(key, title, default, color), 1)
        return bar

    def _make_kpi_card(self, key, title, default, color) -> QWidget:
        card = QWidget()
        card.setProperty("bg-role", "panel")
        card.setStyleSheet(
            "QWidget{{border-radius:6px;padding:0 2px;}}"
            "QWidget:hover{{background:{};}}" .format(_C['border'])
        )
        card.style().unpolish(card)
        card.style().polish(card)
        vl = QVBoxLayout(card)
        vl.setContentsMargins(10, 6, 10, 6)
        vl.setSpacing(2)
        t = QLabel(title)
        t.setProperty("color-role", "muted")
        t.setStyleSheet(
            "font-size:9px;font-weight:600;letter-spacing:0.06em;background:transparent;"
        )
        t.style().unpolish(t)
        t.style().polish(t)
        v = QLabel(default)
        v.setStyleSheet("font-size: 18px; font-weight: 700; background: transparent;")
        vl.addWidget(t); vl.addWidget(v)
        self._kpi_labels[key] = v
        return card

    def _update_kpi(self):
        rows = self._all_rows
        if not rows:
            for k, v in [("toplam","0"),("gecerli","0"),("gecersiz","0"),
                         ("yaklasan","0"),("son_kal","—")]:
                self._kpi_labels[k].setText(v)
            return
        toplam   = len(rows)
        gecerli  = sum(1 for r in rows if r.get("Durum","") in ("Gecerli","Geçerli"))
        gecersiz = sum(1 for r in rows if r.get("Durum","") in ("Gecersiz","Geçersiz"))
        bugun = datetime.now().date()
        limit = bugun + timedelta(days=30)
        yaklasan = 0
        for r in rows:
            bitis = r.get("BitisTarihi","")
            if bitis and len(bitis) >= 10:
                try:
                    bt = datetime.strptime(bitis[:10], "%Y-%m-%d").date()
                    if bugun <= bt <= limit:
                        yaklasan += 1
                except ValueError:
                    pass
        tarihler = [r.get("YapilanTarih","") for r in rows if r.get("YapilanTarih")]
        son = to_ui_date(max(tarihler), "") if tarihler else "—"
        self._kpi_labels["toplam"].setText(str(toplam))
        self._kpi_labels["gecerli"].setText(str(gecerli))
        self._kpi_labels["gecersiz"].setText(str(gecersiz))
        self._kpi_labels["yaklasan"].setText(str(yaklasan))
        self._kpi_labels["son_kal"].setText(son)

    # ── Sol Panel ─────────────────────────────────────
    def _build_left_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        filter_bar = QWidget()
        filter_bar.setProperty("bg-role", "surface")
        filter_bar.setStyleSheet(
            "border-bottom:1px solid {};" .format(_C['border'])
        )
        filter_bar.style().unpolish(filter_bar)
        filter_bar.style().polish(filter_bar)
        fb_l = QHBoxLayout(filter_bar)
        fb_l.setContentsMargins(10, 6, 10, 6)
        fb_l.setSpacing(8)

        self.txt_filter = QLineEdit()
        self.txt_filter.setPlaceholderText("Kal. No, Cihaz, Firma…")
        self.txt_filter.setProperty("bg-role", "input")
        self.txt_filter.style().unpolish(self.txt_filter)
        self.txt_filter.style().polish(self.txt_filter)
        self.txt_filter.setMaximumWidth(230)
        self.txt_filter.textChanged.connect(self._apply_filters)
        fb_l.addWidget(self.txt_filter)

        self.cmb_durum_filter = QComboBox()
        self.cmb_durum_filter.setProperty("bg-role", "input")
        self.cmb_durum_filter.style().unpolish(self.cmb_durum_filter)
        self.cmb_durum_filter.style().polish(self.cmb_durum_filter)
        self.cmb_durum_filter.setFixedWidth(155)
        for lbl, val in [("Tüm Durumlar", None),
                          ("Geçerli","Gecerli"), ("Geçersiz","Gecersiz")]:
            self.cmb_durum_filter.addItem(lbl, val)
        self.cmb_durum_filter.currentIndexChanged.connect(self._apply_filters)
        fb_l.addWidget(self.cmb_durum_filter)

        self.cmb_cihaz_filter = QComboBox()
        self.cmb_cihaz_filter.setProperty("bg-role", "input")
        self.cmb_cihaz_filter.style().unpolish(self.cmb_cihaz_filter)
        self.cmb_cihaz_filter.style().polish(self.cmb_cihaz_filter)
        self.cmb_cihaz_filter.setFixedWidth(150)
        self.cmb_cihaz_filter.addItem("Tüm Cihazlar", None)
        self.cmb_cihaz_filter.currentIndexChanged.connect(self._apply_filters)
        self.cmb_cihaz_filter.setVisible(not bool(self._cihaz_id))
        fb_l.addWidget(self.cmb_cihaz_filter)

        fb_l.addStretch()
        self.btn_yeni = QPushButton("+ Yeni Kalibrasyon")
        self.btn_yeni.clicked.connect(self._open_kal_form)
        fb_l.addWidget(self.btn_yeni)
        layout.addWidget(filter_bar)

        self._model = KalibrasyonTableModel()
        self.table = QTableView()
        self.table.setModel(self._model)
        self.table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        # tema otomatik — self.table.setStyleSheet(S["table"]) kaldırıldı
        self.table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._model.setup_columns(self.table)
        self.table.selectionModel().currentChanged.connect(self._on_row_selected)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)
        self.table.doubleClicked.connect(self._open_kal_form)
        layout.addWidget(self.table, 1)

        self.lbl_count = QLabel("0 kayıt")
        self.lbl_count.setProperty("color-role", "muted")
        self.lbl_count.setProperty("bg-role", "surface")
        self.lbl_count.setStyleSheet(
            "font-size:11px;padding:4px 10px;border-top:1px solid {};" .format(_C['border'])
        )
        self.lbl_count.style().unpolish(self.lbl_count)
        self.lbl_count.style().polish(self.lbl_count)
        layout.addWidget(self.lbl_count)
        return panel

    # ── Sağ Panel (QStackedWidget) ────────────────────
    def _build_right_panel(self) -> QWidget:
        surface  = _C["surface"]
        panel_bg = _C["panel"]
        border   = _C["border"]
        text_pr  = _C["text"]
        text_sec = getattr(DarkTheme, "TEXT_SECONDARY", "#c8cdd8")

        self._right_stack = QStackedWidget()
        self._right_stack.setProperty("bg-role", "surface")
        self._right_stack.setStyleSheet(
            "border-left:1px solid {};" .format(border)
        )
        self._right_stack.style().unpolish(self._right_stack)
        self._right_stack.style().polish(self._right_stack)

        # ════════════════════════════
        #  SAYFA 0 — Detay + Form
        # ════════════════════════════
        detail_page = QWidget()
        detail_page.setProperty("bg-role", "surface")
        detail_page.style().unpolish(detail_page)
        detail_page.style().polish(detail_page)
        dp_l = QVBoxLayout(detail_page)
        dp_l.setContentsMargins(0, 0, 0, 0)
        dp_l.setSpacing(0)

        # ── Detay Bilgi Kartı ──────────────────────────
        self._det_header = QWidget()
        self._det_header.setProperty("bg-role", "panel")
        self._det_header.setStyleSheet(
            "border-bottom:1px solid {};" .format(border)
        )
        self._det_header.style().unpolish(self._det_header)
        self._det_header.style().polish(self._det_header)
        dh_l = QVBoxLayout(self._det_header)
        dh_l.setContentsMargins(14, 12, 14, 12)
        dh_l.setSpacing(10)

        # Üst satır: Cihaz adı + Durum pill
        top_row = QHBoxLayout()
        top_row.setSpacing(8)
        self.lbl_det_title = QLabel("— Bir kayıt seçin —")
        self.lbl_det_title.setProperty("color-role", "primary")
        self.lbl_det_title.setStyleSheet(
            "font-size:13px;font-weight:700;"
        )
        self.lbl_det_title.style().unpolish(self.lbl_det_title)
        self.lbl_det_title.style().polish(self.lbl_det_title)
        self.lbl_det_title.setWordWrap(True)
        top_row.addWidget(self.lbl_det_title, 1)
        self.lbl_det_durum = QLabel("")
        self.lbl_det_durum.setProperty("color-role", "muted")
        self.lbl_det_durum.setProperty("bg-role", "separator")
        self.lbl_det_durum.setStyleSheet(
            "font-size:10px;font-weight:700;padding:2px 8px;border-radius:10px;"
        )
        self.lbl_det_durum.style().unpolish(self.lbl_det_durum)
        self.lbl_det_durum.style().polish(self.lbl_det_durum)
        self.lbl_det_durum.setAlignment(Qt.AlignmentFlag.AlignCenter)
        top_row.addWidget(self.lbl_det_durum)
        dh_l.addLayout(top_row)

        # Kal No
        self.lbl_det_kalid = QLabel("")
        self.lbl_det_kalid.setProperty("color-role", "muted")
        self.lbl_det_kalid.setStyleSheet(
            "font-size:10px;letter-spacing:0.04em;"
        )
        self.lbl_det_kalid.style().unpolish(self.lbl_det_kalid)
        self.lbl_det_kalid.style().polish(self.lbl_det_kalid)
        dh_l.addWidget(self.lbl_det_kalid)

        # Ayırıcı
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFixedHeight(1)
        sep.setProperty("bg-role", "separator")
        sep.style().unpolish(sep)
        sep.style().polish(sep)
        dh_l.addWidget(sep)

        # Grid satır 1: Yapılan / Bitiş / Geçerlilik
        row1 = QHBoxLayout(); row1.setSpacing(0)
        self.fw_yapilan    = self._field_lbl("Yapılan Tarih", "—")
        self.fw_bitis      = self._field_lbl("Bitiş Tarihi", "—")
        self.fw_gecerlilik = self._field_lbl("Geçerlilik", "—")
        for w in [self.fw_yapilan, self.fw_bitis, self.fw_gecerlilik]:
            row1.addWidget(w, 1)
        dh_l.addLayout(row1)

        # Grid satır 2: Firma / Sertifika / Dosya
        row2 = QHBoxLayout(); row2.setSpacing(0)
        self.fw_firma     = self._field_lbl("Firma", "—")
        self.fw_sertifika = self._field_lbl("Sertifika No", "—")
        self.fw_dosya     = self._field_lbl("Dosya", "—")
        for w in [self.fw_firma, self.fw_sertifika, self.fw_dosya]:
            row2.addWidget(w, 1)
        dh_l.addLayout(row2)

        # Açıklama
        self.lbl_det_aciklama = QLabel("")
        self.lbl_det_aciklama.setWordWrap(True)
        self.lbl_det_aciklama.setVisible(False)
        self.lbl_det_aciklama.setProperty("color-role", "muted")
        self.lbl_det_aciklama.setProperty("bg-role", "surface")
        self.lbl_det_aciklama.setStyleSheet(
            "font-size:11px;padding:6px 8px;border-radius:4px;border:1px solid {};" .format(border)
        )
        self.lbl_det_aciklama.style().unpolish(self.lbl_det_aciklama)
        self.lbl_det_aciklama.style().polish(self.lbl_det_aciklama)
        dh_l.addWidget(self.lbl_det_aciklama)
        dp_l.addWidget(self._det_header)

        # ── Buton Bar ──────────────────────────────────
        btn_bar = QWidget()
        btn_bar.setProperty("bg-role", "surface")
        btn_bar.setStyleSheet(
            "border-bottom:1px solid {};" .format(border)
        )
        btn_bar.style().unpolish(btn_bar)
        btn_bar.style().polish(btn_bar)
        bb_l = QHBoxLayout(btn_bar)
        bb_l.setContentsMargins(10, 6, 10, 6)
        bb_l.setSpacing(8)
        bb_l.addStretch()
        self.btn_kayit_ekle = QPushButton("+ Kayıt Ekle")
        self.btn_kayit_ekle.setStyleSheet(
            ""
        )
        self.btn_kayit_ekle.setEnabled(False)
        self.btn_kayit_ekle.clicked.connect(self._open_kal_form)
        if self._action_guard:
            self._action_guard.disable_if_unauthorized(self.btn_kayit_ekle, "cihaz.write")
        bb_l.addWidget(self.btn_kayit_ekle)
        dp_l.addWidget(btn_bar)

        # ── Exec Form Alanı ────────────────────────────
        self._exec_content_stack = QStackedWidget()
        self._exec_content_stack.setProperty("bg-role", "surface")
        self._exec_content_stack.style().unpolish(self._exec_content_stack)
        self._exec_content_stack.style().polish(self._exec_content_stack)

        # index 0: placeholder
        ph = QWidget()
        ph.setProperty("bg-role", "surface")
        ph.style().unpolish(ph)
        ph.style().polish(ph)
        ph_l = QVBoxLayout(ph)
        ph_l.addStretch()
        ph_lbl = QLabel('Yeni kayıt için "+ Kayıt Ekle" veya çift tıklayın.')
        ph_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ph_lbl.setProperty("color-role", "muted")
        ph_lbl.setStyleSheet("font-size: 11px;")
        ph_lbl.style().unpolish(ph_lbl)
        ph_lbl.style().polish(ph_lbl)
        ph_l.addWidget(ph_lbl)
        ph_l.addStretch()
        self._exec_content_stack.addWidget(ph)   # index 0

        # index 1: form scroll
        self._exec_form_scroll = QScrollArea()
        self._exec_form_scroll.setWidgetResizable(True)
        # tema otomatik — scroll
        self._exec_form_inner = QWidget()
        self._exec_form_inner.setProperty("bg-role", "surface")
        self._exec_form_inner.style().unpolish(self._exec_form_inner)
        self._exec_form_inner.style().polish(self._exec_form_inner)
        self._exec_form_layout = QVBoxLayout(self._exec_form_inner)
        self._exec_form_layout.setContentsMargins(10, 10, 10, 10)
        self._exec_form_layout.setSpacing(0)
        self._exec_form_layout.addStretch()
        self._exec_form_scroll.setWidget(self._exec_form_inner)
        self._exec_content_stack.addWidget(self._exec_form_scroll)   # index 1

        dp_l.addWidget(self._exec_content_stack, 1)
        self._right_stack.addWidget(detail_page)   # stack page 0

        return self._right_stack

    # ── Yardımcı widget üreticileri ───────────────────
    def _field_lbl(self, title: str, value: str) -> QWidget:
        w = QWidget()
        w.setProperty("bg-role", "elevated")
        w.style().unpolish(w)
        w.style().polish(w)
        vl = QVBoxLayout(w)
        vl.setContentsMargins(0, 4, 8, 4)
        vl.setSpacing(2)
        t = QLabel(title.upper())
        t.setProperty("color-role", "muted")
        t.setStyleSheet(
            "font-size:9px;letter-spacing:0.06em;font-weight:600;background:transparent;"
        )
        t.style().unpolish(t)
        t.style().polish(t)
        v = QLabel(value)
        v.setObjectName("val")
        v.setProperty("color-role", "primary")
        v.setStyleSheet("font-size: 12px;")
        v.style().unpolish(v)
        v.style().polish(v)
        v.setWordWrap(True)
        vl.addWidget(t); vl.addWidget(v)
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
        if not self._db or not self._svc:
            self._all_rows = []
            self._rows = []
            self._model.set_rows([])
            self.lbl_count.setText("0 kayıt")
            self._update_kpi()
            return
        try:
            rows = self._svc.get_kalibrasyon_listesi(self._cihaz_id).veri or []
            self._all_rows = rows
            self._refresh_cihaz_filter()
            self._update_kpi()
            self._apply_filters()
            if rows:
                self.table.selectRow(0)
        except Exception as e:
            logger.error(f"Kalibrasyon kayıtları yüklenemedi: {e}")
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
        txt = self.txt_filter.text().strip().lower()
        if txt:
            filtered = [
                r for r in filtered
                if txt in str(r.get("Kalid","")).lower()
                or txt in str(r.get("Cihazid","")).lower()
                or txt in str(r.get("Firma","")).lower()
                or txt in str(r.get("SertifikaNo","")).lower()
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
        cihaz     = row.get("Cihazid","")
        firma     = row.get("Firma","")
        kalid     = row.get("Kalid","")
        durum     = row.get("Durum","")
        bitis_raw = row.get("BitisTarihi","")

        self.lbl_det_title.setText(f"{cihaz}  —  {firma}" if firma else cihaz or "—")
        self.lbl_det_kalid.setText(f"Kal. No: {kalid}" if kalid else "")

        dur_c_map = {"Planlandi": _C["accent"], "Planlandı": _C["accent"], "Yapildi": _C["green"], "Yapıldı": _C["green"], "Gecikmis": _C["red"], "Gecikmiş": _C["red"]}
        dur_c = dur_c_map.get(durum, _C["muted"])
        if durum:
            self.lbl_det_durum.setText(durum)
            self.lbl_det_durum.setStyleSheet(
                "font-size:10px;font-weight:700;color:{};padding:2px 8px;border-radius:10px;background:{}22;" .format(dur_c, dur_c)
            )
        else:
            self.lbl_det_durum.setText("")

        self._set_field(self.fw_yapilan,    to_ui_date(row.get("YapilanTarih",""), "—"))
        bitis_c   = _bitis_rengi(bitis_raw)
        bitis_lbl = self.fw_bitis.findChild(QLabel, "val")
        if bitis_lbl:
            bitis_lbl.setText(to_ui_date(bitis_raw, "—"))
            bitis_lbl.setStyleSheet(
                "font-size:12px;font-weight:600;color:{};background:transparent;" .format(bitis_c)
            )
        self._set_field(self.fw_gecerlilik, row.get("Gecerlilik","") or "—")
        self._set_field(self.fw_firma,      row.get("Firma","") or "—")
        self._set_field(self.fw_sertifika,  row.get("SertifikaNo","") or "—")
        dosya = (row.get("Dosya","") or "").strip()
        self._set_field(self.fw_dosya, (dosya[:22] + "…") if len(dosya) > 22 else dosya or "—")

        aciklama = (row.get("Aciklama","") or "").strip()
        if aciklama:
            self.lbl_det_aciklama.setText(aciklama[:200] + ("…" if len(aciklama) > 200 else ""))
            self.lbl_det_aciklama.setVisible(True)
        else:
            self.lbl_det_aciklama.setVisible(False)

    # ══════════════════════════════════════════════════════
    #  Form Açma / Kapama
    # ══════════════════════════════════════════════════════
    def _clear_form_container(self):
        while self._exec_form_layout.count() > 1:
            item = self._exec_form_layout.takeAt(0)
            if not item:
                continue
            w = item.widget()
            if w:
                w.setParent(None)
        if self._active_form is not None:
            self._active_form.setParent(None)
            self._active_form = None

    def _open_kal_form(self, *_):
        if self._action_guard and not self._action_guard.check_and_warn(
            self, "cihaz.write", "Kalibrasyon Formu Acma"
        ):
            return
        self._clear_form_container()
        cihaz_id = self._cihaz_id
        if not cihaz_id and self._selected_row:
            cihaz_id = self._selected_row.get("Cihazid")
        form = _KalibrasyonGirisForm(self._db, cihaz_id, action_guard=self._action_guard, parent=self)
        form.saved.connect(self._on_kal_saved)
        self._active_form = form
        self._exec_form_layout.insertWidget(0, form)
        self._exec_content_stack.setCurrentIndex(1)
        self._right_stack.setCurrentIndex(0)

    def _close_form(self):
        self._clear_form_container()
        self._exec_content_stack.setCurrentIndex(0)
        self._right_stack.setCurrentIndex(0)

    # ══════════════════════════════════════════════════════
    #  Geri çağrılar
    # ══════════════════════════════════════════════════════
    def _on_kal_saved(self):
        self._close_form()
        self._load_data()
        QMessageBox.information(self, "Başarı", "Kalibrasyon kaydı başarıyla eklendi.")

    # ══════════════════════════════════════════════════════
    #  Sağ tık menüsü
    # ══════════════════════════════════════════════════════
    def _show_context_menu(self, pos):
        index = self.table.indexAt(pos)
        if not index.isValid():
            return
        menu = QMenu(self)
        act = menu.addAction("Yeni Kalibrasyon Kaydı Ekle")
        if menu.exec(self.table.mapToGlobal(pos)) == act:
            self._open_kal_form()

    # ══════════════════════════════════════════════════════
    #  Kalibrasyon Performansı Tab
    # ══════════════════════════════════════════════════════
    def _build_perf_tab(self) -> QWidget:
        outer = QScrollArea()
        outer.setWidgetResizable(True)
        # tema otomatik — scroll
        self._perf_inner = QWidget()
        self._perf_inner.setProperty("bg-role", "elevated")
        self._perf_inner.style().unpolish(self._perf_inner)
        self._perf_inner.style().polish(self._perf_inner)
        self._perf_layout = QVBoxLayout(self._perf_inner)
        self._perf_layout.setContentsMargins(16, 16, 16, 16)
        self._perf_layout.setSpacing(20)
        self._perf_layout.addStretch()
        outer.setWidget(self._perf_inner)
        return outer

    def _section_title(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setProperty("color-role", "muted")
        lbl.setStyleSheet(
            "font-size:11px;font-weight:700;letter-spacing:0.08em;"
            "padding-bottom:4px;border-bottom:1px solid {};" .format(_C['border'])
        )
        lbl.style().unpolish(lbl)
        lbl.style().polish(lbl)
        return lbl

    def _refresh_perf_tab(self):
        while self._perf_layout.count():
            item = self._perf_layout.takeAt(0)
            if not item:
                continue
            w = item.widget()
            if w:
                w.setParent(None)

        rows = self._all_rows
        if not rows:
            empty = QLabel("Gösterilecek kalibrasyon verisi yok.")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setProperty("color-role", "muted")
            empty.setStyleSheet("font-size: 13px; padding: 40px;")
            empty.style().unpolish(empty)
            empty.style().polish(empty)
            self._perf_layout.addWidget(empty)
            self._perf_layout.addStretch()
            return

        if self._cihaz_id:
            self._perf_layout.addWidget(
                self._section_title(f"{self._cihaz_id}  —  AYLIK KALİBRASYON TRENDİ")
            )
            self._perf_layout.addWidget(self._build_trend_chart(rows))
            self._perf_layout.addWidget(self._section_title("DURUM ÖZETİ"))
            self._perf_layout.addWidget(self._build_single_cihaz_stats(rows))
            self._perf_layout.addWidget(self._section_title("YAKLAŞAN & GEÇMİŞ BİTİŞ TARİHLERİ"))
            self._perf_layout.addWidget(self._build_expiry_list(rows))
        else:
            cihaz_marka_map, tum_markalar = self._load_cihaz_marka_map()
            self._perf_layout.addWidget(
                self._section_title("MARKA BAZLI KALİBRASYON PERFORMANSI")
            )
            marka_data, kalsiz_markalar = self._compute_marka_stats(
                rows, cihaz_marka_map, tum_markalar
            )
            self._perf_layout.addWidget(self._build_marka_grid(marka_data))
            if kalsiz_markalar:
                self._perf_layout.addWidget(
                    self._section_title("KALİBRASYON KAYDI BULUNMAYAN MARKALAR")
                )
                self._perf_layout.addWidget(self._build_no_kal_card(kalsiz_markalar))
            self._perf_layout.addWidget(self._section_title("AYLIK KALİBRASYON TRENDİ"))
            self._perf_layout.addWidget(self._build_trend_chart(rows))
            self._perf_layout.addWidget(self._section_title("YAKLAŞAN & GEÇMİŞ BİTİŞ TARİHLERİ"))
            self._perf_layout.addWidget(self._build_expiry_list(rows))

        self._perf_layout.addStretch()

    def _build_single_cihaz_stats(self, rows: List[Dict]) -> QWidget:
        gecerli  = sum(1 for r in rows if r.get("Durum","") in ("Gecerli","Geçerli"))
        gecersiz = sum(1 for r in rows if r.get("Durum","") in ("Gecersiz","Geçersiz"))
        toplam   = len(rows)
        bugun = datetime.now().date()
        limit = bugun + timedelta(days=30)
        yaklasan = sum(
            1 for r in rows
            if r.get("BitisTarihi","") and len(r.get("BitisTarihi","")) >= 10
            and bugun <= datetime.strptime(
                r["BitisTarihi"][:10], "%Y-%m-%d"
            ).date() <= limit
        )
        gecersiz_pct = f"%{round(gecersiz / toplam * 100)}" if toplam else "—"

        container = QWidget()
        container.setStyleSheet("background:transparent;")
        hl = QHBoxLayout(container)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setSpacing(8)
        for title, value, color in [
            ("Toplam",         str(toplam),     _C["accent"]),
            ("Geçerli",        str(gecerli),    _C["green"]),
            ("Geçersiz",       str(gecersiz),   _C["red"]),
            ("Yaklaşan Bitiş", str(yaklasan),   _C["amber"]),
            ("Geçersizlik",    gecersiz_pct,    _C["red"]),
        ]:
            card = QWidget()
            card.setProperty("bg-role", "panel")
            card.setStyleSheet(
                "border:1px solid {};border-radius:6px;" .format(_C['border'])
            )
            card.style().unpolish(card)
            card.style().polish(card)
            cl = QVBoxLayout(card)
            cl.setContentsMargins(10, 8, 10, 8)
            cl.setSpacing(2)
            t = QLabel(title.upper())
            t.setProperty("color-role", "muted")
            t.setStyleSheet(
                "font-size:9px;font-weight:600;letter-spacing:0.06em;background:transparent;"
            )
            t.style().unpolish(t)
            t.style().polish(t)
            v = QLabel(value)
            v.setStyleSheet(
                "font-size:16px;font-weight:700;color:{};background:transparent;" .format(color)
            )
            cl.addWidget(t); cl.addWidget(v)
            hl.addWidget(card, 1)
        return container

    def _load_cihaz_marka_map(self):
        cihaz_marka_map: Dict[str, str] = {}
        tum_markalar: Dict[str, set]    = defaultdict(set)
        if not self._db or not self._svc:
            return cihaz_marka_map, tum_markalar
        try:
            cihazlar = self._svc.get_cihaz_listesi().veri or []
            for c in (cihazlar or []):
                cid   = str(c.get("Cihazid","") or "").strip()
                marka = str(c.get("Marka","")   or "").strip()
                if cid and marka:
                    cihaz_marka_map[cid] = marka
                    tum_markalar[marka].add(cid)
        except Exception as e:
            logger.error(f"Cihazlar tablosu yüklenemedi: {e}")
        return cihaz_marka_map, tum_markalar

    def _compute_marka_stats(self, rows, cihaz_marka_map, tum_markalar):
        stats: Dict[str, Dict] = {}
        now   = datetime.now()
        bugun = now.date()
        limit = bugun + timedelta(days=30)

        for r in rows:
            cid = str(r.get("Cihazid","") or "").strip()
            if cid not in cihaz_marka_map:
                continue
            marka = cihaz_marka_map[cid]
            if marka not in stats:
                stats[marka] = {
                    "marka":    marka, "cihazlar": set(),
                    "toplam":   0, "gecerli": 0, "gecersiz": 0, "yaklasan": 0,
                    "ay_trend": defaultdict(int),
                }
            s = stats[marka]
            s["cihazlar"].add(cid)
            s["toplam"] += 1
            durum = r.get("Durum","")
            if durum in ("Gecerli","Geçerli"):
                s["gecerli"] += 1
            elif durum in ("Gecersiz","Geçersiz"):
                s["gecersiz"] += 1
            bitis = r.get("BitisTarihi","")
            if bitis and len(bitis) >= 10:
                try:
                    bt = datetime.strptime(bitis[:10], "%Y-%m-%d").date()
                    if bugun <= bt <= limit:
                        s["yaklasan"] += 1
                except ValueError:
                    pass
            t = r.get("YapilanTarih","")
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
            oran  = round(s["gecerli"] / s["toplam"] * 100) if s["toplam"] else 0
            marka_data.append({**s, "cihaz_sayi": len(s["cihazlar"]),
                                "trend": trend, "oran": oran})
        marka_data.sort(key=lambda x: x["toplam"], reverse=True)

        planlanan = set(stats.keys())
        kalsiz = [
            {"marka": m, "cihaz_sayi": len(ids), "cihazlar": sorted(ids)}
            for m, ids in tum_markalar.items() if m not in planlanan
        ]
        kalsiz.sort(key=lambda x: x["marka"])
        return marka_data, kalsiz

    def _build_marka_grid(self, marka_data: List[Dict]) -> QWidget:
        if not marka_data:
            lbl = QLabel("Eşleşen marka verisi bulunamadı.")
            lbl.setProperty("color-role", "muted")
            lbl.setStyleSheet("font-size: 12px; padding: 12px;")
            lbl.style().unpolish(lbl)
            lbl.style().polish(lbl)
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
            card.setProperty("bg-role", "panel")
            card.setStyleSheet(
                "border:1px solid {};border-radius:8px;" .format(_C['border'])
            )
            card.style().unpolish(card)
            card.style().polish(card)
            cl = QVBoxLayout(card)
            cl.setContentsMargins(14, 12, 14, 12)
            cl.setSpacing(8)

            hdr = QHBoxLayout()
            lbl_m = QLabel(d["marka"])
            lbl_m.setProperty("color-role", "primary")
            lbl_m.setStyleSheet(
                "font-size:13px;font-weight:700;"
            )
            lbl_m.style().unpolish(lbl_m)
            lbl_m.style().polish(lbl_m)
            hdr.addWidget(lbl_m)
            hdr.addStretch()
            lbl_cs = QLabel(f"{d['cihaz_sayi']} cihaz")
            lbl_cs.setProperty("color-role", "muted")
            lbl_cs.setProperty("bg-role", "separator")
            lbl_cs.setStyleSheet(
                "font-size:10px;border-radius:4px;padding:1px 6px;"
            )
            lbl_cs.style().unpolish(lbl_cs)
            lbl_cs.style().polish(lbl_cs)
            hdr.addWidget(lbl_cs)
            oran_color = (_C["green"] if d["oran"] >= 80 else
                          _C["amber"] if d["oran"] >= 50 else _C["red"])
            badge = QLabel(f"%{d['oran']} geçerli")
            badge.setStyleSheet(
                "font-size:10px;font-weight:600;color:{};background:{}22;border-radius:4px;padding:1px 6px;" .format(oran_color, oran_color)
            )
            hdr.addWidget(badge)
            if d["yaklasan"] > 0:
                badge2 = QLabel(f"{d['yaklasan']} yaklaşan")
                badge2.setStyleSheet(
                    "font-size:10px;font-weight:600;color:{};background:{}22;border-radius:4px;padding:1px 6px;" .format(_C['amber'], _C['amber'])
                )
                hdr.addWidget(badge2)
            cl.addLayout(hdr)

            for lbl_txt, val, color in [
                ("Toplam",   d["toplam"],   _C["accent"]),
                ("Geçerli",  d["gecerli"],  _C["green"]),
                ("Geçersiz", d["gecersiz"], _C["red"]),
            ]:
                bar_pct = int((val / max_toplam) * 100) if max_toplam else 0
                cl.addWidget(self._bar_row(lbl_txt, val, bar_pct, color))

            spark = _KalSparkline(d["trend"], parent=card)
            spark.setFixedHeight(32)
            cl.addWidget(spark)
            grid.addWidget(card, row_i, col_i)

        remainder = len(marka_data) % cols
        if remainder:
            for c in range(remainder, cols):
                ph = QWidget()
                ph.setStyleSheet("background:transparent;")
                grid.addWidget(ph, len(marka_data) // cols, c)

        return container

    def _build_no_kal_card(self, kalsiz: List[Dict]) -> QWidget:
        card = QWidget()
        card.setProperty("bg-role", "panel")
        card.setStyleSheet(
            "border:1px solid {};border-left:3px solid {};border-radius:8px;" .format(_C['amber'] + "44", _C['amber'])
        )
        card.style().unpolish(card)
        card.style().polish(card)
        cl = QVBoxLayout(card)
        cl.setContentsMargins(16, 12, 16, 12)
        cl.setSpacing(10)

        hdr = QHBoxLayout()
        lbl_t = QLabel("Kalibrasyonu Olmayan Markalar")
        lbl_t.setStyleSheet(
            "font-size:12px;font-weight:700;color:{};background:transparent;" .format(_C['amber'])
        )
        hdr.addWidget(lbl_t)
        hdr.addStretch()
        lbl_s = QLabel(f"{len(kalsiz)} marka")
        lbl_s.setStyleSheet(
            "font-size:11px;font-weight:600;color:{};background:{}22;border-radius:4px;padding:2px 8px;" .format(_C['amber'], _C['amber'])
        )
        hdr.addWidget(lbl_s)
        cl.addLayout(hdr)

        wrap = QWidget()
        wrap.setStyleSheet("background:transparent;")
        wrap_l = QHBoxLayout(wrap)
        wrap_l.setContentsMargins(0, 0, 0, 0)
        wrap_l.setSpacing(8)
        for d in kalsiz:
            chip = QWidget()
            chip.setProperty("bg-role", "surface")
            chip.setStyleSheet(
                "border:1px solid {};border-radius:6px;" .format(_C['border'])
            )
            chip.style().unpolish(chip)
            chip.style().polish(chip)
            chip_l = QVBoxLayout(chip)
            chip_l.setContentsMargins(10, 6, 10, 6)
            chip_l.setSpacing(2)
            lm = QLabel(d["marka"])
            lm.setProperty("color-role", "primary")
            lm.setStyleSheet(
                "font-size:12px;font-weight:600;"
            )
            lm.style().unpolish(lm)
            lm.style().polish(lm)
            chip_l.addWidget(lm)
            lc = QLabel(f"{d['cihaz_sayi']} cihaz")
            lc.setProperty("color-role", "muted")
            lc.setStyleSheet("font-size: 10px;")
            lc.style().unpolish(lc)
            lc.style().polish(lc)
            chip_l.addWidget(lc)
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
        lbl.setFixedWidth(58)
        lbl.setProperty("color-role", "muted")
        lbl.setStyleSheet("font-size: 10px;")
        lbl.style().unpolish(lbl)
        lbl.style().polish(lbl)
        hl.addWidget(lbl)
        bar_bg = QWidget()
        bar_bg.setFixedHeight(6)
        bar_bg.setProperty("bg-role", "separator")
        bar_bg.setStyleSheet("border-radius: 3px;")
        bar_bg.style().unpolish(bar_bg)
        bar_bg.style().polish(bar_bg)
        bar_bg.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        bar_fill = QWidget(bar_bg)
        bar_fill.setFixedHeight(6)
        bar_fill.setStyleSheet(
            "background:{};border-radius:3px;" .format(fill_color)
        )
        bar_fill.setFixedWidth(max(4, int(pct * 1.5)))
        hl.addWidget(bar_bg)
        cnt = QLabel(str(value))
        cnt.setFixedWidth(24)
        cnt.setAlignment(Qt.AlignmentFlag.AlignRight)
        cnt.setStyleSheet(
            "font-size:10px;font-weight:600;color:{};background:transparent;" .format(fill_color)
        )
        hl.addWidget(cnt)
        return w

    def _build_trend_chart(self, rows: List[Dict]) -> QWidget:
        now = datetime.now()
        ay_sayim:  Dict[int, int] = {}
        ay_etiket: Dict[int, str] = {}
        ay_isimleri = ["Oca","Şub","Mar","Nis","May","Haz","Tem","Ağu","Eyl","Eki","Kas","Ara"]
        for i in range(12):
            ay_idx = (now.month - 1 - i) % 12
            konum  = 11 - i
            ay_sayim[konum] = 0
            ay_etiket[konum] = ay_isimleri[ay_idx]
        for r in rows:
            t = r.get("YapilanTarih","")
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
        container.setProperty("bg-role", "panel")
        container.setStyleSheet(
            "border:1px solid {};border-radius:8px;" .format(_C['border'])
        )
        container.style().unpolish(container)
        container.style().polish(container)
        cl = QVBoxLayout(container)
        cl.setContentsMargins(16, 14, 16, 14)
        cl.setSpacing(6)

        bar_row_l = QHBoxLayout()
        bar_row_l.setSpacing(4)
        for val, _ in zip(degerler, etiketler):
            col = QVBoxLayout()
            col.setSpacing(2)
            col.setAlignment(Qt.AlignmentFlag.AlignBottom)
            val_lbl = QLabel(str(val) if val else "")
            val_lbl.setAlignment(Qt.AlignmentFlag.AlignHCenter)
            val_lbl.setProperty("color-role", "muted")
            val_lbl.setStyleSheet("font-size: 9px;")
            val_lbl.style().unpolish(val_lbl)
            val_lbl.style().polish(val_lbl)
            col.addWidget(val_lbl)
            bar_color = (_C["red"] if val > max_val * 0.7 else
                         _C["amber"] if val > max_val * 0.4 else _C["green"])
            bar_h = max(4, int((val / max_val) * 60)) if max_val else 4
            bar = QWidget()
            bar.setFixedSize(16, bar_h)
            bar.setStyleSheet(
                "background:{};border-radius:3px 3px 0 0;" .format(bar_color)
            )
            col.addWidget(bar, 0, Qt.AlignmentFlag.AlignHCenter)
            bar_row_l.addLayout(col)
        cl.addLayout(bar_row_l)

        lbl_row = QHBoxLayout()
        lbl_row.setSpacing(4)
        for et in etiketler:
            lbl = QLabel(et)
            lbl.setAlignment(Qt.AlignmentFlag.AlignHCenter)
            lbl.setProperty("color-role", "muted")
            lbl.setStyleSheet("font-size: 9px;")
            lbl.style().unpolish(lbl)
            lbl.style().polish(lbl)
            lbl_row.addWidget(lbl)
        cl.addLayout(lbl_row)
        return container

    def _build_expiry_list(self, rows: List[Dict]) -> QWidget:
        """Yaklaşan (90 gün) ve geçmiş bitiş tarihleri."""
        bugun = datetime.now().date()
        limit = bugun + timedelta(days=90)
        ilgili = []
        for r in rows:
            bitis = r.get("BitisTarihi","")
            if bitis and len(bitis) >= 10:
                try:
                    bt = datetime.strptime(bitis[:10], "%Y-%m-%d").date()
                    if bt <= limit:
                        ilgili.append((bt, r))
                except ValueError:
                    pass
        ilgili.sort(key=lambda x: x[0])

        container = QWidget()
        container.setStyleSheet("background:transparent;")
        cl = QVBoxLayout(container)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.setSpacing(6)

        if not ilgili:
            lbl = QLabel("Yaklaşan veya geçmiş bitiş tarihi bulunmuyor.")
            lbl.setProperty("color-role", "muted")
            lbl.setStyleSheet("font-size: 12px; padding: 12px;")
            lbl.style().unpolish(lbl)
            lbl.style().polish(lbl)
            cl.addWidget(lbl)
            return container

        for bt, r in ilgili[:20]:
            bitis_raw = r.get("BitisTarihi","")
            bitis_c   = _bitis_rengi(bitis_raw)
            gecti     = bt < bugun
            kalan     = (bt - bugun).days

            row_w = QWidget()
            row_w.setProperty("bg-role", "panel")
            row_w.setStyleSheet(
                "border:1px solid {};border-left:3px solid {};border-radius:6px;" .format(_C['border'], bitis_c)
            )
            row_w.style().unpolish(row_w)
            row_w.style().polish(row_w)
            rl = QHBoxLayout(row_w)
            rl.setContentsMargins(12, 8, 12, 8)
            rl.setSpacing(12)

            chip = QLabel(str(r.get("Cihazid","")) or "—")
            chip.setStyleSheet(
                "font-size:11px;font-weight:600;color:{};background:{}22;border-radius:4px;padding:2px 8px;" .format(_C['accent'], _C['accent'])
            )
            chip.setFixedWidth(90)
            rl.addWidget(chip)

            firma = QLabel(str(r.get("Firma","")) or "—")
            firma.setProperty("color-role", "primary")
            firma.setStyleSheet("font-size: 12px;")
            firma.style().unpolish(firma)
            firma.style().polish(firma)
            firma.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
            rl.addWidget(firma)

            sert = QLabel(str(r.get("SertifikaNo","")) or "—")
            sert.setProperty("color-role", "muted")
            sert.setStyleSheet("font-size: 10px;")
            sert.style().unpolish(sert)
            sert.style().polish(sert)
            sert.setFixedWidth(90)
            rl.addWidget(sert)

            zaman_str = (
                f"{to_ui_date(bitis_raw,'—')}  ({abs(kalan)}g geçti)"
                if gecti else
                f"{to_ui_date(bitis_raw,'—')}  ({kalan}g kaldı)"
            )
            zaman_lbl = QLabel(zaman_str)
            zaman_lbl.setStyleSheet(
                "font-size:11px;font-weight:600;color:{};background:transparent;" .format(bitis_c)
            )
            rl.addWidget(zaman_lbl)
            cl.addWidget(row_w)

        return container


# ─────────────────────────────────────────────────────────────
#  Sparkline Widget
# ─────────────────────────────────────────────────────────────
class _KalSparkline(QWidget):
    def __init__(self, values: List[int], parent=None):
        super().__init__(parent)
        self._values = values or [0] * 12
        self.setMinimumHeight(28)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h, n = self.width(), self.height(), len(self._values)
        if n == 0:
            return
        max_v = max(self._values) if any(self._values) else 1
        bar_w = max(2, (w - (n - 1) * 2) // n)
        for i, v in enumerate(self._values):
            bar_h = max(3, int((v / max_v) * (h - 4))) if max_v else 3
            x = i * (bar_w + 2)
            y = h - bar_h
            color = QColor(_C["red"] if v > max_v * 0.7 else
                           _C["amber"] if v > max_v * 0.4 else _C["green"])
            color.setAlpha(180)
            painter.fillRect(x, y, bar_w, bar_h, QBrush(color))
        painter.end()


# ─────────────────────────────────────────────────────────────
#  Kalibrasyon Giriş Formu
# ─────────────────────────────────────────────────────────────
class _KalibrasyonGirisForm(QWidget):
    saved = Signal()

    def __init__(self, db=None, cihaz_id: Optional[str] = None, action_guard=None, parent=None):
        super().__init__(parent)
        self._db       = db
        self._cihaz_id = cihaz_id
        self._action_guard = action_guard
        if db:
            from core.di import get_cihaz_service
            self._svc = KalibrasyonService(get_cihaz_service(db)._r)
        else:
            self._svc = None
        self._setup_ui()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 8)
        root.setSpacing(8)

        # Form başlığı + kapatma
        hdr = QWidget()
        hdr.setProperty("bg-role", "elevated")
        hdr.setStyleSheet("border-radius: 6px;")
        hdr.style().unpolish(hdr)
        hdr.style().polish(hdr)
        hdr_l = QHBoxLayout(hdr)
        hdr_l.setContentsMargins(12, 8, 8, 8)
        hdr_l.setSpacing(0)
        lbl_title = QLabel("Yeni Kalibrasyon Kaydı")
        lbl_title.setProperty("color-role", "primary")
        lbl_title.setStyleSheet(
            "font-size:12px;font-weight:700;"
        )
        lbl_title.style().unpolish(lbl_title)
        lbl_title.style().polish(lbl_title)
        hdr_l.addWidget(lbl_title)
        hdr_l.addStretch()
        text_sec = getattr(DarkTheme, "TEXT_SECONDARY", "#c8cdd8")
        btn_kapat = QPushButton("✕")
        btn_kapat.setFixedSize(22, 22)
        btn_kapat.setProperty("style-role", "close")
        btn_kapat.clicked.connect(self._close_self)
        hdr_l.addWidget(btn_kapat)
        root.addWidget(hdr)

        # Form alanları
        grp = QGroupBox()
        grid = QGridLayout(grp)
        grid.setContentsMargins(12, 12, 12, 12)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(8)

        self.txt_firma = QLineEdit()
        self.txt_firma.setProperty("bg-role", "input")
        self.txt_firma.style().unpolish(self.txt_firma)
        self.txt_firma.style().polish(self.txt_firma)
        self.txt_firma.setPlaceholderText("Kalibrasyon firması")
        self._r(grid, 0, "Firma *", self.txt_firma)

        self.txt_sertifika = QLineEdit()
        self.txt_sertifika.setProperty("bg-role", "input")
        self.txt_sertifika.style().unpolish(self.txt_sertifika)
        self.txt_sertifika.style().polish(self.txt_sertifika)
        self.txt_sertifika.setPlaceholderText("Sertifika numarası")
        self._r(grid, 1, "Sertifika No", self.txt_sertifika)

        self.dt_yapilan = QDateEdit(QDate.currentDate())
        self.dt_yapilan.setCalendarPopup(True)
        self.dt_yapilan.setDisplayFormat("ddd, d MMMM yyyy")
        # tema otomatik — self.dt_yapilan.setStyleSheet(S["date"]) kaldırıldı
        self._r(grid, 2, "Yapılan Tarih *", self.dt_yapilan)

        self.txt_gecerlilik = QLineEdit()
        self.txt_gecerlilik.setProperty("bg-role", "input")
        self.txt_gecerlilik.style().unpolish(self.txt_gecerlilik)
        self.txt_gecerlilik.style().polish(self.txt_gecerlilik)
        self.txt_gecerlilik.setPlaceholderText("Örn: 1 Yıl, 2 Yıl")
        self._r(grid, 3, "Geçerlilik Süresi", self.txt_gecerlilik)

        self.dt_bitis = QDateEdit(QDate.currentDate())
        self.dt_bitis.setCalendarPopup(True)
        self.dt_bitis.setDisplayFormat("ddd, d MMMM yyyy")
        # tema otomatik — self.dt_bitis.setStyleSheet(S["date"]) kaldırıldı
        self._r(grid, 4, "Bitiş Tarihi *", self.dt_bitis)

        self.cmb_durum = QComboBox()
        self.cmb_durum.setProperty("bg-role", "input")
        self.cmb_durum.style().unpolish(self.cmb_durum)
        self.cmb_durum.style().polish(self.cmb_durum)
        self.cmb_durum.addItems(["Gecerli", "Gecersiz"])
        self._r(grid, 5, "Durum", self.cmb_durum)

        self.txt_dosya = QLineEdit()
        self.txt_dosya.setProperty("bg-role", "input")
        self.txt_dosya.style().unpolish(self.txt_dosya)
        self.txt_dosya.style().polish(self.txt_dosya)
        self.txt_dosya.setPlaceholderText("Dosya yolu veya link")
        self._r(grid, 6, "Dosya / Link", self.txt_dosya)

        self.txt_aciklama = QTextEdit()
        # tema otomatik — self.txt_aciklama.setStyleSheet(S["input_text"]) kaldırıldı
        self.txt_aciklama.setFixedHeight(72)
        self.txt_aciklama.setPlaceholderText("Ek açıklama (isteğe bağlı)")
        self._r(grid, 7, "Açıklama", self.txt_aciklama)

        root.addWidget(grp)

        # Butonlar
        btns = QHBoxLayout()
        btns.addStretch()
        btn_temizle = QPushButton("Temizle")
        btn_temizle.clicked.connect(self._clear)
        btns.addWidget(btn_temizle)
        btn_kaydet = QPushButton("Kaydet")
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
        root.addLayout(btns)

    def _r(self, grid, row, label, widget):
        lbl = QLabel(label)
        lbl.setProperty("color-role", "secondary")
        lbl.style().unpolish(lbl)
        lbl.style().polish(lbl)
        grid.addWidget(lbl, row, 0)
        grid.addWidget(widget, row, 1)

    def _close_self(self):
        parent = self.parentWidget()
        while parent:
            if hasattr(parent, "_close_form") and callable(getattr(parent, "_close_form", None)):
                parent._close_form()  # type: ignore
                return
            parent = parent.parentWidget()

    def _save(self):
        if self._action_guard and not self._action_guard.check_and_warn(
            self, "cihaz.write", "Kalibrasyon Kaydetme"
        ):
            return
        if not self._db:
            QMessageBox.warning(self, "Uyarı", "Veritabanı bağlantısı yok.")
            return
        if not self._cihaz_id:
            QMessageBox.warning(self, "Uyarı", "Cihaz seçili değil.")
            return
        firma = self.txt_firma.text().strip()
        if not firma:
            QMessageBox.warning(self, "Uyarı", "Firma adı zorunludur.")
            return
        kalid = f"{self._cihaz_id}-KL-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        data = {
            "Kalid":        kalid,
            "Cihazid":      self._cihaz_id,
            "Firma":        firma,
            "SertifikaNo":  self.txt_sertifika.text().strip(),
            "YapilanTarih": self.dt_yapilan.date().toString("yyyy-MM-dd"),
            "Gecerlilik":   self.txt_gecerlilik.text().strip(),
            "BitisTarihi":  self.dt_bitis.date().toString("yyyy-MM-dd"),
            "Durum":        self.cmb_durum.currentText().strip(),
            "Dosya":        self.txt_dosya.text().strip(),
            "Aciklama":     self.txt_aciklama.toPlainText().strip(),
        }
        try:
            # Service kullanarak kaydet
            success = self._svc.kaydet(data) if self._svc else False
            if success:
                self.saved.emit()
                self._clear()
            else:
                QMessageBox.critical(self, "Hata", "Kalibrasyon kaydı başarısız")
        except Exception as e:
            logger.error(f"Kalibrasyon kaydı kaydedilemedi: {e}")
            QMessageBox.critical(self, "Hata", f"Kayıt başarısız: {e}")

    def _clear(self):
        for w in [self.txt_firma, self.txt_sertifika,
                  self.txt_gecerlilik, self.txt_dosya]:
            w.clear()
        self.txt_aciklama.clear()
        self.dt_yapilan.setDate(QDate.currentDate())
        self.dt_bitis.setDate(QDate.currentDate())
        self.cmb_durum.setCurrentIndex(0)