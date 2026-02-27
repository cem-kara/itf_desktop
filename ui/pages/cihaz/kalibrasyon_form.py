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
from typing import List, Dict, Optional
from datetime import datetime, timedelta

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame,
    QTableView, QSplitter, QHeaderView, QTabWidget,
    QGroupBox, QGridLayout,
    QLabel, QLineEdit, QComboBox, QDateEdit,
    QPushButton, QMenu, QMessageBox, QSizePolicy, QScrollArea,
    QStackedWidget,
)
from PySide6.QtGui import QColor

from core.date_utils import to_ui_date
from core.logger import logger
from database.repository_registry import RepositoryRegistry
from ui.styles import DarkTheme
from ui.styles.components import STYLES as S
from ui.pages.cihaz.models.kalibrasyon_model import KAL_COLUMNS, KalibrasyonTableModel
from ui.pages.cihaz.components.kalibrasyon_components import (
    KalibrasyonGirisForm,
    load_cihaz_marka_map,
    compute_marka_stats,
    build_single_cihaz_stats,
    build_marka_grid,
    build_no_kal_card,
    build_trend_chart,
    build_expiry_list,
)


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
    "Gecerli":  _C["green"],
    "Geçerli":  _C["green"],
    "Gecersiz": _C["red"],
    "Geçersiz": _C["red"],
}

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
        sep.setFrameShape(QFrame.HLine)
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
        v.setStyleSheet(f"font-size:18px;font-weight:700;color:{color};background:transparent;")
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
        self.table.setSelectionBehavior(QTableView.SelectRows)
        self.table.setSelectionMode(QTableView.SingleSelection)
        self.table.setStyleSheet(S["table"])
        self.table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        for i, (_, _, w) in enumerate(KAL_COLUMNS):
            self.table.setColumnWidth(i, w)
        hdr = self.table.horizontalHeader()
        hdr.setStretchLastSection(False)
        hdr.setSectionResizeMode(QHeaderView.Stretch)
        self.table.selectionModel().currentChanged.connect(self._on_row_selected)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
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
        self.lbl_det_durum.setAlignment(Qt.AlignCenter)
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
        sep.setFrameShape(QFrame.HLine)
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
        ph_lbl.setAlignment(Qt.AlignCenter)
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
        if not self._db:
            self._all_rows = []
            self._rows = []
            self._model.set_rows([])
            self.lbl_count.setText("0 kayıt")
            self._update_kpi()
            return
        try:
            repo = RepositoryRegistry(self._db).get("Kalibrasyon")
            rows = repo.get_all()
            if self._cihaz_id:
                rows = [r for r in rows
                        if str(r.get("Cihazid","")) == str(self._cihaz_id)]
            rows.sort(key=lambda r: (r.get("YapilanTarih") or ""), reverse=True)
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
        form = KalibrasyonGirisForm(self._db, cihaz_id, action_guard=self._action_guard, parent=self)
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
            empty.setAlignment(Qt.AlignCenter)
            empty.setStyleSheet(f"color:{_C['muted']};font-size:13px;padding:40px;")
            self._perf_layout.addWidget(empty)
            self._perf_layout.addStretch()
            return

        if self._cihaz_id:
            self._perf_layout.addWidget(
                self._section_title(f"{self._cihaz_id}  —  AYLIK KALİBRASYON TRENDİ")
            )
            self._perf_layout.addWidget(build_trend_chart(rows, _C))
            self._perf_layout.addWidget(self._section_title("DURUM ÖZETİ"))
            self._perf_layout.addWidget(build_single_cihaz_stats(rows, _C))
            self._perf_layout.addWidget(self._section_title("YAKLAŞAN & GEÇMİŞ BİTİŞ TARİHLERİ"))
            self._perf_layout.addWidget(build_expiry_list(rows, _C, _bitis_rengi))
        else:
            cihaz_marka_map, tum_markalar = load_cihaz_marka_map(self._db)
            self._perf_layout.addWidget(
                self._section_title("MARKA BAZLI KALİBRASYON PERFORMANSI")
            )
            marka_data, kalsiz_markalar = compute_marka_stats(
                rows, cihaz_marka_map, tum_markalar
            )
            self._perf_layout.addWidget(build_marka_grid(marka_data, _C))
            if kalsiz_markalar:
                self._perf_layout.addWidget(
                    self._section_title("KALİBRASYON KAYDI BULUNMAYAN MARKALAR")
                )
                self._perf_layout.addWidget(build_no_kal_card(kalsiz_markalar, _C))
            self._perf_layout.addWidget(self._section_title("AYLIK KALİBRASYON TRENDİ"))
            self._perf_layout.addWidget(build_trend_chart(rows, _C))
            self._perf_layout.addWidget(self._section_title("YAKLAŞAN & GEÇMİŞ BİTİŞ TARİHLERİ"))
            self._perf_layout.addWidget(build_expiry_list(rows, _C, _bitis_rengi))

        self._perf_layout.addStretch()

