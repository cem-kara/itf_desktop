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
from core.services.kalibrasyon_service import KalibrasyonService
from ui.components.base_table_model import BaseTableModel
from ui.styles.colors import C as _C
from ui.styles import DarkTheme
from ui.styles.components import STYLES as S
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
    def __init__(self, rows: Optional[List[Dict[str, Any]]] = None, parent=None):
        super().__init__(KAL_COLUMNS, rows, parent)

    def _display(self, key, row):
        val = row.get(key, "")
        if key in ("YapilanTarih", "BitisTarihi"):
            return to_ui_date(val, "")
        return str(val) if val else ""

    def _fg(self, key, row):
        if key == "Durum":
            c = _DURUM_COLOR.get(row.get("Durum", ""))
            return QColor(c) if c else None
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

    def set_rows(self, rows: List[Dict[str, Any]]):
        self.set_data(rows)


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
            from database.repository_registry import RepositoryRegistry
            self._svc = KalibrasyonService(RepositoryRegistry(db))
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
        sep.setStyleSheet(f"background:{_C['border']};")
        root.addWidget(sep)

        self._tabs = QTabWidget()
        self._tabs.setStyleSheet(S.get("tab", ""))
        self._tabs.currentChanged.connect(self._on_tab_changed)

        # Tab 0 — Kalibrasyon Listesi
        list_tab = QWidget()
        lt_layout = QVBoxLayout(list_tab)
        lt_layout.setContentsMargins(0, 0, 0, 0)
        lt_layout.setSpacing(0)
        self._h_splitter = QSplitter(Qt.Orientation.Horizontal)
        self._h_splitter.setStyleSheet(S.get("splitter", ""))
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
        bar.setStyleSheet(f"background:{_C['surface']};")
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
        card.setStyleSheet(
            f"QWidget{{background:{_C['panel']};border-radius:6px;margin:0 2px;}}"
            f"QWidget:hover{{background:{_C['border']};}}"
        )
        vl = QVBoxLayout(card)
        vl.setContentsMargins(10, 6, 10, 6)
        vl.setSpacing(2)
        t = QLabel(title)
        t.setStyleSheet(
            f"font-size:9px;font-weight:600;letter-spacing:0.06em;"
            f"color:{_C['muted']};background:transparent;"
        )
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
        filter_bar.setStyleSheet(
            f"background:{_C['surface']};border-bottom:1px solid {_C['border']};"
        )
        fb_l = QHBoxLayout(filter_bar)
        fb_l.setContentsMargins(10, 6, 10, 6)
        fb_l.setSpacing(8)

        self.txt_filter = QLineEdit()
        self.txt_filter.setPlaceholderText("🔍  Kal. No, Cihaz, Firma…")
        self.txt_filter.setStyleSheet(S["input"])
        self.txt_filter.setMaximumWidth(230)
        self.txt_filter.textChanged.connect(self._apply_filters)
        fb_l.addWidget(self.txt_filter)

        self.cmb_durum_filter = QComboBox()
        self.cmb_durum_filter.setStyleSheet(S["combo"])
        self.cmb_durum_filter.setFixedWidth(155)
        for lbl, val in [("Tüm Durumlar", None),
                          ("Geçerli","Gecerli"), ("Geçersiz","Gecersiz")]:
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

        fb_l.addStretch()
        self.btn_yeni = QPushButton("+ Yeni Kalibrasyon")
        self.btn_yeni.setStyleSheet(S.get("btn_primary", ""))
        self.btn_yeni.clicked.connect(self._open_kal_form)
        fb_l.addWidget(self.btn_yeni)
        layout.addWidget(filter_bar)

        self._model = KalibrasyonTableModel()
        self.table = QTableView()
        self.table.setModel(self._model)
        self.table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        self.table.setStyleSheet(S["table"])
        self.table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        for i, (_, _, w) in enumerate(KAL_COLUMNS):
            self.table.setColumnWidth(i, w)
        hdr = self.table.horizontalHeader()
        hdr.setStretchLastSection(False)
        hdr.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.selectionModel().currentChanged.connect(self._on_row_selected)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)
        self.table.doubleClicked.connect(self._open_kal_form)
        layout.addWidget(self.table, 1)

        self.lbl_count = QLabel("0 kayıt")
        self.lbl_count.setStyleSheet(
            f"font-size:11px;color:{_C['muted']};padding:4px 10px;"
            f"background:{_C['surface']};border-top:1px solid {_C['border']};"
        )
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
        self._right_stack.setStyleSheet(
            f"background:{surface};border-left:1px solid {border};"
        )

        # ════════════════════════════
        #  SAYFA 0 — Detay + Form
        # ════════════════════════════
        detail_page = QWidget()
        detail_page.setStyleSheet(f"background:{surface};")
        dp_l = QVBoxLayout(detail_page)
        dp_l.setContentsMargins(0, 0, 0, 0)
        dp_l.setSpacing(0)

        # ── Detay Bilgi Kartı ──────────────────────────
        self._det_header = QWidget()
        self._det_header.setStyleSheet(
            f"background:{panel_bg};border-bottom:1px solid {border};"
        )
        dh_l = QVBoxLayout(self._det_header)
        dh_l.setContentsMargins(14, 12, 14, 12)
        dh_l.setSpacing(10)

        # Üst satır: Cihaz adı + Durum pill
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
            f"padding:2px 8px;border-radius:10px;background:{_C['border']};"
        )
        self.lbl_det_durum.setAlignment(Qt.AlignmentFlag.AlignCenter)
        top_row.addWidget(self.lbl_det_durum)
        dh_l.addLayout(top_row)

        # Kal No
        self.lbl_det_kalid = QLabel("")
        self.lbl_det_kalid.setStyleSheet(
            f"font-size:10px;color:{_C['muted']};letter-spacing:0.04em;"
        )
        dh_l.addWidget(self.lbl_det_kalid)

        # Ayırıcı
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background:{border};")
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
        self.lbl_det_aciklama.setStyleSheet(
            f"font-size:11px;color:{_C['muted']};"
            f"padding:6px 8px;background:{surface};"
            f"border-radius:4px;border:1px solid {border};"
        )
        dh_l.addWidget(self.lbl_det_aciklama)
        dp_l.addWidget(self._det_header)

        # ── Buton Bar ──────────────────────────────────
        btn_bar = QWidget()
        btn_bar.setStyleSheet(
            f"background:{surface};border-bottom:1px solid {border};"
        )
        bb_l = QHBoxLayout(btn_bar)
        bb_l.setContentsMargins(10, 6, 10, 6)
        bb_l.setSpacing(8)
        bb_l.addStretch()
        self.btn_kayit_ekle = QPushButton("+ Kayıt Ekle")
        self.btn_kayit_ekle.setStyleSheet(
            S.get("btn_secondary", S.get("btn_primary", ""))
        )
        self.btn_kayit_ekle.setEnabled(False)
        self.btn_kayit_ekle.clicked.connect(self._open_kal_form)
        if self._action_guard:
            self._action_guard.disable_if_unauthorized(self.btn_kayit_ekle, "cihaz.write")
        bb_l.addWidget(self.btn_kayit_ekle)
        dp_l.addWidget(btn_bar)

        # ── Exec Form Alanı ────────────────────────────
        self._exec_content_stack = QStackedWidget()
        self._exec_content_stack.setStyleSheet(f"background:{surface};")

        # index 0: placeholder
        ph = QWidget()
        ph.setStyleSheet(f"background:{surface};")
        ph_l = QVBoxLayout(ph)
        ph_l.addStretch()
        ph_lbl = QLabel('Yeni kayıt için "+ Kayıt Ekle" veya çift tıklayın.')
        ph_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ph_lbl.setStyleSheet(f"font-size:11px;color:{_C['muted']};")
        ph_l.addWidget(ph_lbl)
        ph_l.addStretch()
        self._exec_content_stack.addWidget(ph)   # index 0

        # index 1: form scroll
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

        dp_l.addWidget(self._exec_content_stack, 1)
        self._right_stack.addWidget(detail_page)   # stack page 0

        return self._right_stack

    # ── Yardımcı widget üreticileri ───────────────────
    def _field_lbl(self, title: str, value: str) -> QWidget:
        w = QWidget()
        w.setStyleSheet(f"background:{_C['panel']};")
        vl = QVBoxLayout(w)
        vl.setContentsMargins(0, 4, 8, 4)
        vl.setSpacing(2)
        t = QLabel(title.upper())
        t.setStyleSheet(
            f"font-size:9px;letter-spacing:0.06em;color:{_C['muted']};"
            f"font-weight:600;background:transparent;"
        )
        v = QLabel(value)
        v.setObjectName("val")
        v.setStyleSheet(f"font-size:12px;color:{_C['text']};background:transparent;")
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
            rows = self._svc.get_kalibrasyon_listesi(self._cihaz_id)
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

        dur_c = _DURUM_COLOR.get(durum, _C["muted"])
        if durum:
            self.lbl_det_durum.setText(f"● {durum}")
            self.lbl_det_durum.setStyleSheet(
                f"font-size:10px;font-weight:700;color:{dur_c};"
                f"padding:2px 8px;border-radius:10px;background:{dur_c}22;"
            )
        else:
            self.lbl_det_durum.setText("")

        self._set_field(self.fw_yapilan,    to_ui_date(row.get("YapilanTarih",""), "—"))
        bitis_c   = _bitis_rengi(bitis_raw)
        bitis_lbl = self.fw_bitis.findChild(QLabel, "val")
        if bitis_lbl:
            bitis_lbl.setText(to_ui_date(bitis_raw, "—"))
            bitis_lbl.setStyleSheet(
                f"font-size:12px;font-weight:600;color:{bitis_c};background:transparent;"
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
        outer.setStyleSheet(S.get("scroll", f"background:{_C['surface']};border:none;"))
        self._perf_inner = QWidget()
        self._perf_inner.setStyleSheet(f"background:{_C['surface']};")
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
            f"color:{_C['muted']};padding-bottom:4px;"
            f"border-bottom:1px solid {_C['border']};"
        )
        return lbl

    def _refresh_perf_tab(self):
        while self._perf_layout.count():
            item = self._perf_layout.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)

        rows = self._all_rows
        if not rows:
            empty = QLabel("Gösterilecek kalibrasyon verisi yok.")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setStyleSheet(f"color:{_C['muted']};font-size:13px;padding:40px;")
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
            cl.addWidget(t); cl.addWidget(v)
            hl.addWidget(card, 1)
        return container

    def _load_cihaz_marka_map(self):
        cihaz_marka_map: Dict[str, str] = {}
        tum_markalar: Dict[str, set]    = defaultdict(set)
        if not self._db or not self._svc:
            return cihaz_marka_map, tum_markalar
        try:
            cihazlar = self._svc.get_cihaz_listesi()
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

            hdr = QHBoxLayout()
            lbl_m = QLabel(d["marka"])
            lbl_m.setStyleSheet(
                f"font-size:13px;font-weight:700;color:{_C['text']};background:transparent;"
            )
            hdr.addWidget(lbl_m)
            hdr.addStretch()
            lbl_cs = QLabel(f"{d['cihaz_sayi']} cihaz")
            lbl_cs.setStyleSheet(
                f"font-size:10px;color:{_C['muted']};"
                f"background:{_C['border']};border-radius:4px;padding:1px 6px;"
            )
            hdr.addWidget(lbl_cs)
            oran_color = (_C["green"] if d["oran"] >= 80 else
                          _C["amber"] if d["oran"] >= 50 else _C["red"])
            badge = QLabel(f"%{d['oran']} geçerli")
            badge.setStyleSheet(
                f"font-size:10px;font-weight:600;color:{oran_color};"
                f"background:{oran_color}22;border-radius:4px;padding:1px 6px;"
            )
            hdr.addWidget(badge)
            if d["yaklasan"] > 0:
                badge2 = QLabel(f"{d['yaklasan']} yaklaşan")
                badge2.setStyleSheet(
                    f"font-size:10px;font-weight:600;color:{_C['amber']};"
                    f"background:{_C['amber']}22;border-radius:4px;padding:1px 6px;"
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
        card.setStyleSheet(
            f"background:{_C['panel']};"
            f"border:1px solid {_C['amber']}44;"
            f"border-left:3px solid {_C['amber']};"
            f"border-radius:8px;"
        )
        cl = QVBoxLayout(card)
        cl.setContentsMargins(16, 12, 16, 12)
        cl.setSpacing(10)

        hdr = QHBoxLayout()
        lbl_t = QLabel("Kalibrasyonu Olmayan Markalar")
        lbl_t.setStyleSheet(
            f"font-size:12px;font-weight:700;color:{_C['amber']};background:transparent;"
        )
        hdr.addWidget(lbl_t)
        hdr.addStretch()
        lbl_s = QLabel(f"{len(kalsiz)} marka")
        lbl_s.setStyleSheet(
            f"font-size:11px;font-weight:600;color:{_C['amber']};"
            f"background:{_C['amber']}22;border-radius:4px;padding:2px 8px;"
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
            chip.setStyleSheet(
                f"background:{_C['surface']};border:1px solid {_C['border']};border-radius:6px;"
            )
            chip_l = QVBoxLayout(chip)
            chip_l.setContentsMargins(10, 6, 10, 6)
            chip_l.setSpacing(2)
            lm = QLabel(d["marka"])
            lm.setStyleSheet(
                f"font-size:12px;font-weight:600;color:{_C['text']};background:transparent;"
            )
            chip_l.addWidget(lm)
            lc = QLabel(f"{d['cihaz_sayi']} cihaz")
            lc.setStyleSheet(f"font-size:10px;color:{_C['muted']};background:transparent;")
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
        lbl.setStyleSheet(f"font-size:10px;color:{_C['muted']};background:transparent;")
        hl.addWidget(lbl)
        bar_bg = QWidget()
        bar_bg.setFixedHeight(6)
        bar_bg.setStyleSheet(f"background:{_C['border']};border-radius:3px;")
        bar_bg.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        bar_fill = QWidget(bar_bg)
        bar_fill.setFixedHeight(6)
        bar_fill.setStyleSheet(f"background:{fill_color};border-radius:3px;")
        bar_fill.setFixedWidth(max(4, int(pct * 1.5)))
        hl.addWidget(bar_bg)
        cnt = QLabel(str(value))
        cnt.setFixedWidth(24)
        cnt.setAlignment(Qt.AlignmentFlag.AlignRight)
        cnt.setStyleSheet(
            f"font-size:10px;font-weight:600;color:{fill_color};background:transparent;"
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
        container.setStyleSheet(
            f"background:{_C['panel']};border:1px solid {_C['border']};border-radius:8px;"
        )
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
            val_lbl.setStyleSheet(f"font-size:9px;color:{_C['muted']};background:transparent;")
            col.addWidget(val_lbl)
            bar_color = (_C["red"] if val > max_val * 0.7 else
                         _C["amber"] if val > max_val * 0.4 else _C["green"])
            bar_h = max(4, int((val / max_val) * 60)) if max_val else 4
            bar = QWidget()
            bar.setFixedSize(16, bar_h)
            bar.setStyleSheet(f"background:{bar_color};border-radius:3px 3px 0 0;")
            col.addWidget(bar, 0, Qt.AlignmentFlag.AlignHCenter)
            bar_row_l.addLayout(col)
        cl.addLayout(bar_row_l)

        lbl_row = QHBoxLayout()
        lbl_row.setSpacing(4)
        for et in etiketler:
            lbl = QLabel(et)
            lbl.setAlignment(Qt.AlignmentFlag.AlignHCenter)
            lbl.setStyleSheet(f"font-size:9px;color:{_C['muted']};background:transparent;")
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
            lbl.setStyleSheet(f"color:{_C['muted']};font-size:12px;padding:12px;")
            cl.addWidget(lbl)
            return container

        for bt, r in ilgili[:20]:
            bitis_raw = r.get("BitisTarihi","")
            bitis_c   = _bitis_rengi(bitis_raw)
            gecti     = bt < bugun
            kalan     = (bt - bugun).days

            row_w = QWidget()
            row_w.setStyleSheet(
                f"background:{_C['panel']};border:1px solid {_C['border']};"
                f"border-left:3px solid {bitis_c};border-radius:6px;"
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

            firma = QLabel(str(r.get("Firma","")) or "—")
            firma.setStyleSheet(f"font-size:12px;color:{_C['text']};background:transparent;")
            firma.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Preferred)
            rl.addWidget(firma)

            sert = QLabel(str(r.get("SertifikaNo","")) or "—")
            sert.setStyleSheet(f"font-size:10px;color:{_C['muted']};background:transparent;")
            sert.setFixedWidth(90)
            rl.addWidget(sert)

            zaman_str = (
                f"{to_ui_date(bitis_raw,'—')}  ({abs(kalan)}g geçti)"
                if gecti else
                f"{to_ui_date(bitis_raw,'—')}  ({kalan}g kaldı)"
            )
            zaman_lbl = QLabel(zaman_str)
            zaman_lbl.setStyleSheet(
                f"font-size:11px;font-weight:600;color:{bitis_c};background:transparent;"
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
        self._setup_ui()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 8)
        root.setSpacing(8)

        # Form başlığı + kapatma
        hdr = QWidget()
        hdr.setStyleSheet(f"background:{_C['panel']};border-radius:6px;")
        hdr_l = QHBoxLayout(hdr)
        hdr_l.setContentsMargins(12, 8, 8, 8)
        hdr_l.setSpacing(0)
        lbl_title = QLabel("Yeni Kalibrasyon Kaydı")
        lbl_title.setStyleSheet(
            f"font-size:12px;font-weight:700;color:{_C['text']};background:transparent;"
        )
        hdr_l.addWidget(lbl_title)
        hdr_l.addStretch()
        text_sec = getattr(DarkTheme, "TEXT_SECONDARY", "#c8cdd8")
        btn_kapat = QPushButton("✕")
        btn_kapat.setFixedSize(22, 22)
        btn_kapat.setStyleSheet(
            f"QPushButton{{background:transparent;border:none;"
            f"color:{text_sec};font-size:12px;border-radius:4px;}}"
            f"QPushButton:hover{{background:{_C['border']};color:{_C['text']};}}"
        )
        btn_kapat.clicked.connect(self._close_self)
        hdr_l.addWidget(btn_kapat)
        root.addWidget(hdr)

        # Form alanları
        grp = QGroupBox()
        grp.setStyleSheet(S.get("group", ""))
        grid = QGridLayout(grp)
        grid.setContentsMargins(12, 12, 12, 12)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(8)

        self.txt_firma = QLineEdit()
        self.txt_firma.setStyleSheet(S["input"])
        self.txt_firma.setPlaceholderText("Kalibrasyon firması")
        self._r(grid, 0, "Firma *", self.txt_firma)

        self.txt_sertifika = QLineEdit()
        self.txt_sertifika.setStyleSheet(S["input"])
        self.txt_sertifika.setPlaceholderText("Sertifika numarası")
        self._r(grid, 1, "Sertifika No", self.txt_sertifika)

        self.dt_yapilan = QDateEdit(QDate.currentDate())
        self.dt_yapilan.setCalendarPopup(True)
        self.dt_yapilan.setDisplayFormat("ddd, d MMMM yyyy")
        self.dt_yapilan.setStyleSheet(S["date"])
        self._r(grid, 2, "Yapılan Tarih *", self.dt_yapilan)

        self.txt_gecerlilik = QLineEdit()
        self.txt_gecerlilik.setStyleSheet(S["input"])
        self.txt_gecerlilik.setPlaceholderText("Örn: 1 Yıl, 2 Yıl")
        self._r(grid, 3, "Geçerlilik Süresi", self.txt_gecerlilik)

        self.dt_bitis = QDateEdit(QDate.currentDate())
        self.dt_bitis.setCalendarPopup(True)
        self.dt_bitis.setDisplayFormat("ddd, d MMMM yyyy")
        self.dt_bitis.setStyleSheet(S["date"])
        self._r(grid, 4, "Bitiş Tarihi *", self.dt_bitis)

        self.cmb_durum = QComboBox()
        self.cmb_durum.setStyleSheet(S["combo"])
        self.cmb_durum.addItems(["Gecerli", "Gecersiz"])
        self._r(grid, 5, "Durum", self.cmb_durum)

        self.txt_dosya = QLineEdit()
        self.txt_dosya.setStyleSheet(S["input"])
        self.txt_dosya.setPlaceholderText("Dosya yolu veya link")
        self._r(grid, 6, "Dosya / Link", self.txt_dosya)

        self.txt_aciklama = QTextEdit()
        self.txt_aciklama.setStyleSheet(S["input_text"])
        self.txt_aciklama.setFixedHeight(72)
        self.txt_aciklama.setPlaceholderText("Ek açıklama (isteğe bağlı)")
        self._r(grid, 7, "Açıklama", self.txt_aciklama)

        root.addWidget(grp)

        # Butonlar
        btns = QHBoxLayout()
        btns.addStretch()
        btn_temizle = QPushButton("Temizle")
        btn_temizle.setStyleSheet(S.get("btn_refresh", ""))
        btn_temizle.clicked.connect(self._clear)
        btns.addWidget(btn_temizle)
        btn_kaydet = QPushButton("Kaydet")
        btn_kaydet.setStyleSheet(S.get("action_btn", S.get("btn_primary", "")))
        try:
            IconRenderer.set_button_icon(
                btn_kaydet, "save", color=DarkTheme.BTN_PRIMARY_TEXT, size=14
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
        lbl.setStyleSheet(S["label"])
        grid.addWidget(lbl, row, 0)
        grid.addWidget(widget, row, 1)

    def _close_self(self):
        parent = self.parentWidget()
        while parent:
            if hasattr(parent, "_close_form"):
                parent._close_form()
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
