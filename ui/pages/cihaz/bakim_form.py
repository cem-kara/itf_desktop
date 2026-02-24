# -*- coding: utf-8 -*-
"""
Periyodik Bakım Formu
======================
  • Üstte KPI şeridi (Toplam / Planlı / Yapıldı / Gecikmiş / Son Bakım)
  • Sol: filtreler (Durum + Cihaz + Arama) + renk kodlu tablo
  • Sağ: her zaman görünür detay başlığı → buton bar → form container
  • Form toggle yerine kaydırılabilir alanda açılır/kapanır
"""
from typing import List, Dict, Any, Optional
from datetime import datetime

from PySide6.QtCore import Qt, QDate, QAbstractTableModel, QModelIndex, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame,
    QTableView, QSplitter, QHeaderView,
    QGroupBox, QGridLayout,
    QLabel, QLineEdit, QComboBox, QDateEdit, QTextEdit,
    QPushButton, QMenu, QMessageBox, QSizePolicy, QScrollArea,
)
from PySide6.QtGui import QColor

from core.date_utils import to_ui_date
from core.logger import logger
from database.repository_registry import RepositoryRegistry
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

    def __init__(self, db=None, cihaz_id: Optional[str] = None, parent=None):
        super().__init__(parent)
        self._db                             = db
        self._cihaz_id                       = cihaz_id
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

        h_splitter = QSplitter(Qt.Horizontal)
        h_splitter.setStyleSheet(S.get("splitter", ""))
        h_splitter.addWidget(self._build_left_panel())
        h_splitter.addWidget(self._build_right_panel())
        h_splitter.setStretchFactor(0, 3)
        h_splitter.setStretchFactor(1, 2)
        h_splitter.setSizes([680, 380])
        root.addWidget(h_splitter, 1)

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

        fb_l.addStretch()

        self.btn_yeni = QPushButton("+ Yeni Bakım")
        self.btn_yeni.setStyleSheet(S.get("btn_primary", ""))
        self.btn_yeni.clicked.connect(self._open_bakim_form)
        fb_l.addWidget(self.btn_yeni)
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
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)
        layout.addWidget(self.table, 1)

        self.lbl_count = QLabel("0 kayıt")
        self.lbl_count.setStyleSheet(
            f"font-size:11px;color:{_C['muted']};padding:4px 10px;"
            f"background:{_C['surface']};border-top:1px solid {_C['border']};"
        )
        layout.addWidget(self.lbl_count)
        return panel

    # ── Sağ Panel ───────────────────────────────────────
    def _build_right_panel(self) -> QWidget:
        panel = QWidget()
        panel.setStyleSheet(
            f"background:{_C['surface']};"
            f"border-left:1px solid {_C['border']};"
        )
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Detay başlığı — her zaman görünür
        det_header = QWidget()
        det_header.setStyleSheet(
            f"background:{_C['panel']};border-bottom:1px solid {_C['border']};"
        )
        dh_l = QVBoxLayout(det_header)
        dh_l.setContentsMargins(14, 10, 14, 10)
        dh_l.setSpacing(6)

        self.lbl_det_title = QLabel("— Bir kayıt seçin —")
        self.lbl_det_title.setStyleSheet(
            f"font-size:13px;font-weight:600;color:{_C['text']};"
        )
        self.lbl_det_title.setWordWrap(True)
        dh_l.addWidget(self.lbl_det_title)

        meta_row = QHBoxLayout()
        meta_row.setSpacing(10)
        self.lbl_det_plan   = self._meta_lbl("—")
        self.lbl_det_bakim  = self._meta_lbl("—")
        self.lbl_det_durum  = self._meta_lbl("—")
        for w in [self.lbl_det_plan, self.lbl_det_bakim, self.lbl_det_durum]:
            meta_row.addWidget(w)
        meta_row.addStretch()
        dh_l.addLayout(meta_row)

        fields_row = QHBoxLayout()
        fields_row.setSpacing(16)
        self.fw_teknisyen = self._field_lbl("Teknisyen", "—")
        self.fw_tip       = self._field_lbl("Tip", "—")
        self.fw_periyot   = self._field_lbl("Periyot", "—")
        for w in [self.fw_teknisyen, self.fw_tip, self.fw_periyot]:
            fields_row.addWidget(w)
        dh_l.addLayout(fields_row)

        self.lbl_det_aciklama = QLabel("")
        self.lbl_det_aciklama.setWordWrap(True)
        self.lbl_det_aciklama.setStyleSheet(
            f"font-size:11px;color:{_C['muted']};padding-top:2px;"
        )
        dh_l.addWidget(self.lbl_det_aciklama)
        layout.addWidget(det_header)

        # Buton bar
        btn_bar = QWidget()
        btn_bar.setStyleSheet(
            f"background:{_C['surface']};"
            f"border-bottom:1px solid {_C['border']};"
        )
        bb_l = QHBoxLayout(btn_bar)
        bb_l.setContentsMargins(10, 6, 10, 6)
        bb_l.setSpacing(8)
        lbl_sec = QLabel("Bakım Kaydı")
        lbl_sec.setStyleSheet(f"font-size:11px;font-weight:600;color:{_C['text']};")
        bb_l.addWidget(lbl_sec)
        bb_l.addStretch()
        self.btn_kayit_ekle = QPushButton("+ Kayıt Ekle")
        self.btn_kayit_ekle.setStyleSheet(
            S.get("btn_secondary", S.get("btn_primary", ""))
        )
        self.btn_kayit_ekle.setEnabled(False)
        self.btn_kayit_ekle.clicked.connect(self._open_bakim_form)
        bb_l.addWidget(self.btn_kayit_ekle)
        layout.addWidget(btn_bar)

        # Form container (VSplitter içinde)
        self._v_splitter = QSplitter(Qt.Vertical)
        self._v_splitter.setStyleSheet(S.get("splitter", ""))

        placeholder = QWidget()
        placeholder.setStyleSheet(f"background:{_C['surface']};")
        self._v_splitter.addWidget(placeholder)

        self.form_container = QScrollArea()
        self.form_container.setWidgetResizable(True)
        self.form_container.setStyleSheet(S.get("scroll", ""))
        self.form_container.setVisible(False)
        self._form_inner = QWidget()
        self._form_layout = QVBoxLayout(self._form_inner)
        self._form_layout.setContentsMargins(8, 8, 8, 8)
        self._form_layout.setSpacing(0)
        self._form_layout.addStretch()
        self.form_container.setWidget(self._form_inner)
        self._v_splitter.addWidget(self.form_container)

        self._v_splitter.setStretchFactor(0, 1)
        self._v_splitter.setStretchFactor(1, 0)
        self._v_splitter.setSizes([400, 0])
        layout.addWidget(self._v_splitter, 1)
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
        while self._form_layout.count() > 0:
            item = self._form_layout.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)
        if self._active_form is not None:
            self._active_form.setParent(None)
            self._active_form = None
        self._form_layout.addStretch()

    def _open_bakim_form(self):
        self._clear_form_container()
        form = _BakimGirisForm(self._db, self._cihaz_id, parent=self)
        form.saved.connect(self._on_bakim_saved)
        self._active_form = form
        self._form_layout.insertWidget(0, form)
        self.form_container.setVisible(True)
        self._v_splitter.setSizes([200, 320])

    def _close_form(self):
        self._clear_form_container()
        self.form_container.setVisible(False)
        self._v_splitter.setSizes([400, 0])

    # ══════════════════════════════════════════════════════
    #  Geri çağrılar
    # ══════════════════════════════════════════════════════
    def _on_bakim_saved(self):
        self._close_form()
        self._load_data()
        QMessageBox.information(self, "Başarı", "Bakım kaydı başarıyla eklendi.")

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


# ─────────────────────────────────────────────────────────────
#  Bakım Giriş Formu  (sağ panelde form_container içinde açılır)
# ─────────────────────────────────────────────────────────────
class _BakimGirisForm(QWidget):
    saved = Signal()

    def __init__(self, db=None, cihaz_id: Optional[str] = None, parent=None):
        super().__init__(parent)
        self._db       = db
        self._cihaz_id = cihaz_id
        self._setup_ui()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(8)

        grp = QGroupBox("Yeni Bakım Kaydı")
        grp.setStyleSheet(S["group"])
        grid = QGridLayout(grp)
        grid.setContentsMargins(12, 12, 12, 12)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(8)

        self.txt_periyot = QLineEdit()
        self.txt_periyot.setStyleSheet(S["input"])
        self._r(grid, 0, "Bakım Periyodu", self.txt_periyot)

        self.txt_sira = QLineEdit()
        self.txt_sira.setStyleSheet(S["input"])
        self._r(grid, 1, "Bakım Sırası", self.txt_sira)

        self.dt_plan = QDateEdit(QDate.currentDate())
        self.dt_plan.setCalendarPopup(True)
        self.dt_plan.setDisplayFormat("dd.MM.yyyy")
        self.dt_plan.setStyleSheet(S["date"])
        self._r(grid, 2, "Planlanan Tarih", self.dt_plan)

        self.txt_bakim = QLineEdit()
        self.txt_bakim.setStyleSheet(S["input"])
        self._r(grid, 3, "Bakım", self.txt_bakim)

        self.cmb_durum = QComboBox()
        self.cmb_durum.setStyleSheet(S["combo"])
        self.cmb_durum.addItems(["Planli", "Yapildi", "Gecikmis"])
        self._r(grid, 4, "Durum", self.cmb_durum)

        self.dt_bakim = QDateEdit(QDate.currentDate())
        self.dt_bakim.setCalendarPopup(True)
        self.dt_bakim.setDisplayFormat("dd.MM.yyyy")
        self.dt_bakim.setStyleSheet(S["date"])
        self._r(grid, 5, "Bakım Tarihi", self.dt_bakim)

        self.txt_tip = QLineEdit()
        self.txt_tip.setStyleSheet(S["input"])
        self._r(grid, 6, "Bakım Tipi", self.txt_tip)

        self.txt_islemler = QTextEdit()
        self.txt_islemler.setStyleSheet(S["input_text"])
        self.txt_islemler.setFixedHeight(70)
        self._r(grid, 7, "Yapılan İşlemler", self.txt_islemler)

        self.txt_aciklama = QTextEdit()
        self.txt_aciklama.setStyleSheet(S["input_text"])
        self.txt_aciklama.setFixedHeight(60)
        self._r(grid, 8, "Açıklama", self.txt_aciklama)

        self.txt_teknisyen = QLineEdit()
        self.txt_teknisyen.setStyleSheet(S["input"])
        self._r(grid, 9, "Teknisyen", self.txt_teknisyen)

        self.txt_rapor = QTextEdit()
        self.txt_rapor.setStyleSheet(S["input_text"])
        self.txt_rapor.setFixedHeight(60)
        self._r(grid, 10, "Rapor", self.txt_rapor)

        root.addWidget(grp)

        btns = QHBoxLayout()
        btns.addStretch()
        btn_temizle = QPushButton("Temizle")
        btn_temizle.setStyleSheet(S["btn_refresh"])
        btn_temizle.clicked.connect(self._clear)
        btns.addWidget(btn_temizle)
        btn_kaydet = QPushButton("Kaydet")
        btn_kaydet.setStyleSheet(S.get("action_btn", S.get("btn_primary","")))
        try:
            IconRenderer.set_button_icon(
                btn_kaydet, "save", color=DarkTheme.BTN_PRIMARY_TEXT, size=14
            )
        except Exception:
            pass
        btn_kaydet.clicked.connect(self._save)
        btns.addWidget(btn_kaydet)
        root.addLayout(btns)

    def _r(self, grid, row, label, widget):
        lbl = QLabel(label)
        lbl.setStyleSheet(S["label"])
        grid.addWidget(lbl, row, 0)
        grid.addWidget(widget, row, 1)

    def _save(self):
        if not self._db:
            QMessageBox.warning(self, "Uyarı", "Veritabanı bağlantısı yok.")
            return
        if not self._cihaz_id:
            QMessageBox.warning(self, "Uyarı", "Cihaz seçili değil.")
            return
        planid = f"{self._cihaz_id}-BK-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        data = {
            "Planid":          planid,
            "Cihazid":         self._cihaz_id,
            "BakimPeriyodu":   self.txt_periyot.text().strip(),
            "BakimSirasi":     self.txt_sira.text().strip(),
            "PlanlananTarih":  self.dt_plan.date().toString("yyyy-MM-dd"),
            "Bakim":           self.txt_bakim.text().strip(),
            "Durum":           self.cmb_durum.currentText().strip(),
            "BakimTarihi":     self.dt_bakim.date().toString("yyyy-MM-dd"),
            "BakimTipi":       self.txt_tip.text().strip(),
            "YapilanIslemler": self.txt_islemler.toPlainText().strip(),
            "Aciklama":        self.txt_aciklama.toPlainText().strip(),
            "Teknisyen":       self.txt_teknisyen.text().strip(),
            "Rapor":           self.txt_rapor.toPlainText().strip(),
        }
        try:
            RepositoryRegistry(self._db).get("Periyodik_Bakim").insert(data)
            self.saved.emit()
            self._clear()
        except Exception as e:
            logger.error(f"Bakım kaydı kaydedilemedi: {e}")
            QMessageBox.critical(self, "Hata", f"Kayıt başarısız: {e}")

    def _clear(self):
        for w in [self.txt_periyot, self.txt_sira, self.txt_bakim,
                  self.txt_tip, self.txt_teknisyen]:
            w.clear()
        for w in [self.txt_islemler, self.txt_aciklama, self.txt_rapor]:
            w.clear()
        self.dt_plan.setDate(QDate.currentDate())
        self.dt_bakim.setDate(QDate.currentDate())
        self.cmb_durum.setCurrentIndex(0)
