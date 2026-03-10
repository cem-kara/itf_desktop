# -*- coding: utf-8 -*-
"""
Bakim ve Kalibrasyon Formları
==============================
Yeni tasarım (ariza_kayit.py ile aynı desen):
  • Üstte KPI şeridi
  • Sol: filtreler + renk kodlu liste tablosu
  • Sağ: her zaman görünür detay paneli → kayıt formu kaydırılabilir alanda açılır
"""
from typing import List, Dict, Any, Optional, cast
from pathlib import Path
from datetime import datetime, timedelta

from PySide6.QtCore import Qt, QDate, QAbstractTableModel, QModelIndex, QPersistentModelIndex, Signal
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
from ui.styles.icons import IconRenderer


# ─────────────────────────────────────────────────────────────
#  Renk sabitleri
# ─────────────────────────────────────────────────────────────
_C = {
    "red":    getattr(DarkTheme, "DANGER",   "#f75f5f"),
    "amber":  getattr(DarkTheme, "WARNING",  "#f5a623"),
    "green":  getattr(DarkTheme, "SUCCESS",  "#3ecf8e"),
    "accent": getattr(DarkTheme, "ACCENT",   "#4f8ef7"),
    "muted":  getattr(DarkTheme, "TEXT_MUTED", "#5a6278"),
    "surface":getattr(DarkTheme, "SURFACE",  "#13161d"),
    "panel":  getattr(DarkTheme, "PANEL",    "#191d26"),
    "border": getattr(DarkTheme, "BORDER",   "#242938"),
    "text":   getattr(DarkTheme, "TEXT_PRIMARY", "#eef0f5"),
}

_BAKIM_DURUM_COLOR = {
    "Planli":    _C["accent"],
    "Planlı":    _C["accent"],
    "Yapildi":   _C["green"],
    "Yapıldı":   _C["green"],
    "Gecikmis":  _C["red"],
    "Gecikmiş":  _C["red"],
}

_KAL_DURUM_COLOR = {
    "Gecerli":  _C["green"],
    "Geçerli":  _C["green"],
    "Gecersiz": _C["red"],
    "Geçersiz": _C["red"],
}


# ═════════════════════════════════════════════════════════════
#  ORTAK YARDIMCI: BaseTableModel
# ═════════════════════════════════════════════════════════════
class _BaseTableModel(QAbstractTableModel):
    """Renk destekli generic tablo modeli."""

    def __init__(self, columns, color_map: Dict[str, Dict[str, str]],
                 rows=None, parent=None):
        super().__init__(parent)
        self._cols      = columns          # [(key, header, width), ...]
        self._color_map = color_map        # {key: {value: color}}
        self._keys      = [c[0] for c in columns]
        self._headers   = [c[1] for c in columns]
        self._rows: List[Dict] = rows or []

    def rowCount(self, parent: QModelIndex | QPersistentModelIndex | None = None) -> int:
        return len(self._rows)
    def columnCount(self, parent: QModelIndex | QPersistentModelIndex | None = None) -> int:
        return len(self._cols)
    
    def set_rows(self, rows: List[Dict]):
        """Update model rows and refresh display."""
        self._rows = rows
        self.layoutChanged.emit()

    def data(self, index: QModelIndex | QPersistentModelIndex, role: int = 0):
        if not index.isValid():
            return None
        row = self._rows[index.row()]
        key = self._keys[index.column()]

        if role == Qt.ItemDataRole.DisplayRole:
            val = row.get(key, "")
            if key.endswith("Tarih") or key.endswith("Tarihi"):
                return to_ui_date(val, "")
            return str(val) if val else ""

        if role == Qt.ItemDataRole.TextAlignmentRole:
            if key in ("Durum", "PlanlananTarih", "BakimTarihi",
                       "YapilanTarih", "BitisTarihi"):
                return Qt.AlignmentFlag.AlignCenter
            return Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft

        if role == Qt.ItemDataRole.ForegroundRole and key in self._color_map:
            val = row.get(key, "")
            c = self._color_map[key].get(val)
            return QColor(c) if c else None

        return None

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = 0):
        if role == Qt.ItemDataRole.DisplayRole and orientation == Qt.Orientation.Horizontal:
            return self._headers[section]
        return None

    def get_row(self, idx: int) -> Optional[Dict]:
        return self._rows[idx] if 0 <= idx < len(self._rows) else None


# ─────────────────────────────────────────────────────────────
#  ORTAK YARDIMCI: _BaseListDetailForm
#  Her iki form bu sınıftan türeyerek liste+detay+KPI yapısını
#  hazır alır; alt sınıf sadece kolon/renk/KPI/detay/form
#  parçalarını tanımlar.
# ─────────────────────────────────────────────────────────────
class _BaseListDetailForm(QWidget):

    def __init__(self, db=None, cihaz_id: Optional[str] = None, parent=None):
        super().__init__(parent)
        self._db       = db
        self._cihaz_id = cihaz_id
        self._all_rows: List[Dict] = []
        self._filtered_rows: List[Dict] = []
        self._selected_row: Optional[Dict] = None
        self._active_form: Optional[QWidget] = None

        self._model = _BaseTableModel(
            self._columns(),
            self._color_map(),
        )

        self._setup_ui()
        self._load_data()

    # ── Alt sınıfların gezmesi gereken API ──────────────
    def _columns(self)   -> List: raise NotImplementedError
    def _color_map(self) -> Dict: raise NotImplementedError
    def _kpi_definitions(self) -> List: raise NotImplementedError   # [(key,title,default,color)]
    def _compute_kpi(self, rows: List[Dict]) -> Dict[str, str]: raise NotImplementedError
    def _repo_name(self) -> str: raise NotImplementedError
    def _filter_rows(self, rows: List[Dict]) -> List[Dict]: raise NotImplementedError
    def _build_entry_form(self) -> QWidget: raise NotImplementedError
    def _update_detail(self, row: Dict): raise NotImplementedError
    def _new_btn_label(self) -> str: return "+ Yeni Kayıt"
    def _panel_title(self) -> str: return "Kayıtlar"
    def _detail_title(self) -> str: return "Detay"

    # ── UI İnşaası ──────────────────────────────────────
    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_kpi_bar())
        root.addWidget(self._make_hsep())

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self._build_left_panel())
        splitter.addWidget(self._build_right_panel())
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        splitter.setSizes([640, 380])
        root.addWidget(splitter, 1)

    def _make_hsep(self) -> QFrame:
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFixedHeight(1)
        sep.setProperty('color-role', 'border')
        return sep

    # KPI şeridi
    def _build_kpi_bar(self) -> QWidget:
        bar = QWidget()
        bar.setFixedHeight(68)
        bar.setProperty('color-role', 'surface')
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(1)
        self._kpi_labels: Dict[str, QLabel] = {}
        for key, title, default, color in self._kpi_definitions():
            layout.addWidget(self._make_kpi_card(key, title, default, color), 1)
        return bar

    def _make_kpi_card(self, key, title, default, color) -> QWidget:
        card = QWidget()
        card.setStyleSheet(
            f"QWidget{{background:{_C['panel']};border-radius:6px;padding:0 2px;}}"
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
        v.setStyleSheet(
            f"font-size:18px;font-weight:700;color:{color};background:transparent;"
        )
        vl.addWidget(t)
        vl.addWidget(v)
        self._kpi_labels[key] = v
        return card

    def _refresh_kpi(self):
        for k, v in self._compute_kpi(self._all_rows).items():
            if k in self._kpi_labels:
                self._kpi_labels[k].setText(v)

    # Sol panel
    def _build_left_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Filtre / buton satırı
        fb = QWidget()
        fb.setStyleSheet(
            f"background:{_C['surface']};"
            f"border-bottom:1px solid {_C['border']};"
        )
        fb_l = QHBoxLayout(fb)
        fb_l.setContentsMargins(10, 6, 10, 6)
        fb_l.setSpacing(8)

        self.txt_filter = QLineEdit()
        self.txt_filter.setPlaceholderText("🔍  Ara…")
        self.txt_filter.setMaximumWidth(200)
        self.txt_filter.textChanged.connect(self._apply_filters)
        fb_l.addWidget(self.txt_filter)

        self.cmb_durum_filter = QComboBox()
        self.cmb_durum_filter.setFixedWidth(160)
        for lbl, val in self._durum_filter_items():
            self.cmb_durum_filter.addItem(lbl, val)
        self.cmb_durum_filter.currentIndexChanged.connect(self._apply_filters)
        fb_l.addWidget(self.cmb_durum_filter)

        fb_l.addStretch()

        self.btn_yeni = QPushButton(self._new_btn_label())
        self.btn_yeni.setProperty("style-role", "secondary")
        self.btn_yeni.clicked.connect(self._open_entry_form)
        fb_l.addWidget(self.btn_yeni)
        layout.addWidget(fb)

        # Tablo
        self.table = QTableView()
        self.table.setModel(self._model)
        from PySide6.QtWidgets import QAbstractItemView
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        cols = self._columns()
        for i, (_, _, w) in enumerate(cols):
            self.table.setColumnWidth(i, w)
        hdr = self.table.horizontalHeader()
        hdr.setStretchLastSection(False)
        hdr.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.selectionModel().currentChanged.connect(self._on_row_selected)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)
        layout.addWidget(self.table, 1)

        # Sayaç
        self.lbl_count = QLabel("0 kayıt")
        self.lbl_count.setStyleSheet(
            f"font-size:11px;color:{_C['muted']};padding:4px 10px;"
            f"background:{_C['surface']};border-top:1px solid {_C['border']};"
        )
        layout.addWidget(self.lbl_count)
        return panel

    def _durum_filter_items(self) -> List:
        return [("Tüm Durumlar", None)]

    # Sağ panel
    def _build_right_panel(self) -> QWidget:
        panel = QWidget()
        panel.setStyleSheet(
            f"background:{_C['surface']};"
            f"border-left:1px solid {_C['border']};"
        )
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Detay başlık widget'ı (alt sınıf _build_detail_header'ı override edebilir)
        layout.addWidget(self._build_detail_header())

        # Kayıt butonu bar
        btn_bar = QWidget()
        btn_bar.setStyleSheet(
            f"background:{_C['surface']};"
            f"border-bottom:1px solid {_C['border']};"
        )
        bb_l = QHBoxLayout(btn_bar)
        bb_l.setContentsMargins(10, 6, 10, 6)
        bb_l.setSpacing(8)
        lbl = QLabel(self._detail_title())
        lbl.setStyleSheet(
            f"font-size:11px;font-weight:600;color:{_C['text'][:7]};"
        )
        bb_l.addWidget(lbl)
        bb_l.addStretch()
        self.btn_duzenle = QPushButton("Düzenle / Yeni")
        self.btn_duzenle.setProperty("style-role", "secondary")
        self.btn_duzenle.setEnabled(False)
        self.btn_duzenle.clicked.connect(self._open_entry_form)
        bb_l.addWidget(self.btn_duzenle)
        layout.addWidget(btn_bar)

        # Dikey splitter: detay alanları + form
        self._v_splitter = QSplitter(Qt.Orientation.Vertical)

        detail_scroll = QScrollArea()
        detail_scroll.setWidgetResizable(True)
        self._detail_widget = QWidget()
        self._detail_layout = QVBoxLayout(self._detail_widget)
        self._detail_layout.setContentsMargins(12, 10, 12, 10)
        self._detail_layout.setSpacing(6)
        self._detail_layout.addStretch()
        detail_scroll.setWidget(self._detail_widget)
        self._v_splitter.addWidget(detail_scroll)

        # Form container
        self.form_container = QScrollArea()
        self.form_container.setWidgetResizable(True)
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

    def _build_detail_header(self) -> QWidget:
        """Sağ panelin en üstündeki başlık widget'ı. Alt sınıflar override edebilir."""
        w = QWidget()
        w.setStyleSheet(
            f"background:{_C['panel']};border-bottom:1px solid {_C['border']};"
        )
        vl = QVBoxLayout(w)
        vl.setContentsMargins(14, 10, 14, 10)
        vl.setSpacing(4)
        self.lbl_det_title = QLabel("— Bir kayıt seçin —")
        self.lbl_det_title.setStyleSheet(
            f"font-size:13px;font-weight:600;color:{_C['text']};"
        )
        self.lbl_det_title.setWordWrap(True)
        vl.addWidget(self.lbl_det_title)

        self._meta_row = QHBoxLayout()
        self._meta_row.setSpacing(10)
        vl.addLayout(self._meta_row)
        return w

    # ── Veri ────────────────────────────────────────────
    def set_cihaz_id(self, cihaz_id: Optional[str]):
        self._cihaz_id = cihaz_id
        self._load_data()

    def _load_data(self):
        if not self._db:
            self._all_rows = []
            self._model.set_rows([])
            self.lbl_count.setText("0 kayıt")
            self._refresh_kpi()
            return
        try:
            repo = RepositoryRegistry(self._db).get(self._repo_name())
            rows = repo.get_all()
            if self._cihaz_id:
                rows = [r for r in rows if str(r.get("Cihazid","")) == str(self._cihaz_id)]
            rows.sort(key=lambda r: (r.get(self._sort_key()) or ""), reverse=True)
            self._all_rows = rows
            self._refresh_kpi()
            self._apply_filters()
            if rows:
                self.table.selectRow(0)
        except Exception as e:
            logger.error(f"{self._repo_name()} yüklenemedi: {e}")
            self._all_rows = []
            self._model.set_rows([])
            self.lbl_count.setText("0 kayıt")

    def _sort_key(self) -> str:
        return "BaslangicTarihi"

    def _apply_filters(self):
        rows = self._filter_rows(self._all_rows)

        sel_durum = self.cmb_durum_filter.currentData()
        if sel_durum:
            rows = [r for r in rows if r.get("Durum","") == sel_durum]

        txt = self.txt_filter.text().strip().lower()
        if txt:
            rows = [r for r in rows if any(
                txt in str(r.get(k,"")).lower()
                for k in self._search_keys()
            )]

        self._filtered_rows = rows
        self._model.set_rows(rows)
        self.lbl_count.setText(f"{len(rows)} kayıt")

    def _search_keys(self) -> List[str]:
        return ["Cihazid"]

    # ── Satır seçimi ────────────────────────────────────
    def _on_row_selected(self, current, _previous):
        if not current.isValid():
            return
        row = self._model.get_row(current.row())
        if row:
            self._selected_row = row
            self._update_detail(row)
            self.btn_duzenle.setEnabled(True)

    # ── Form açma/kapama ────────────────────────────────
    def _clear_form_container(self):
        while self._form_layout.count():
            item = self._form_layout.takeAt(0)
            widget = item.widget() if item else None
            if widget:
                widget.setParent(None)
        if self._active_form:
            self._active_form.setParent(None)
            self._active_form = None
        self._form_layout.addStretch()

    def _open_entry_form(self):
        self._clear_form_container()
        form: QWidget = self._build_entry_form()
        if hasattr(form, 'saved'):
            cast(Any, form).saved.connect(self._on_saved)
        self._active_form = form
        self._form_layout.insertWidget(0, form)
        self.form_container.setVisible(True)
        self._v_splitter.setSizes([250, 300])

    def _close_form(self):
        self._clear_form_container()
        self.form_container.setVisible(False)
        self._v_splitter.setSizes([400, 0])

    def _on_saved(self):
        self._close_form()
        self._load_data()

    # ── Sağ tık ─────────────────────────────────────────
    def _show_context_menu(self, pos):
        index = self.table.indexAt(pos)
        if not index.isValid():
            return
        menu = QMenu(self)
        act = menu.addAction(self._new_btn_label())
        if menu.exec(self.table.mapToGlobal(pos)) == act:
            self._open_entry_form()

    # ── Yardımcı widget üreticileri ─────────────────────
    def _meta_label(self, text: str, color: str | None = None) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet(
            f"font-size:11px;color:{color or _C['muted']};"
            f"background:{_C['panel']};"
        )
        return lbl

    def _field_widget(self, title: str, value: str = "—") -> QWidget:
        w = QWidget()
        w.setProperty('color-role', 'surface')
        vl = QVBoxLayout(w)
        vl.setContentsMargins(0, 0, 0, 0)
        vl.setSpacing(1)
        t = QLabel(title.upper())
        t.setStyleSheet(
            f"font-size:9px;letter-spacing:0.06em;color:{_C['muted']};font-weight:600;"
        )
        v = QLabel(value)
        v.setObjectName("val")
        v.setStyleSheet("font-size:12px;")
        v.setProperty('color-role', 'text')
        v.setWordWrap(True)
        vl.addWidget(t)
        vl.addWidget(v)
        return w

    @staticmethod
    def _set_field(widget: QWidget, value: str):
        lbl = widget.findChild(QLabel, "val")
        if lbl:
            lbl.setText(value or "—")


# ═════════════════════════════════════════════════════════════
#  BAKIM FORMU
# ═════════════════════════════════════════════════════════════
_BAKIM_COLS = [
    ("Planid",          "Plan No",       90),
    ("PlanlananTarih",  "Plan Tarihi",   100),
    ("BakimTarihi",     "Bakım Tarihi",  100),
    ("BakimPeriyodu",   "Periyot",       100),
    ("BakimTipi",       "Tip",           110),
    ("Teknisyen",       "Teknisyen",     120),
    ("Durum",           "Durum",         100),
]


class BakimKayitForm(_BaseListDetailForm):
    """Periyodik Bakım — liste + detay + KPI."""

    saved = Signal()

    # ── Kolon / renk ────────────────────────────────────
    def _columns(self):    return _BAKIM_COLS
    def _color_map(self):  return {"Durum": _BAKIM_DURUM_COLOR}
    def _repo_name(self):  return "Periyodik_Bakim"
    def _sort_key(self):   return "PlanlananTarih"
    def _new_btn_label(self): return "+ Yeni Bakım"
    def _panel_title(self):   return "Bakım Kayıtları"
    def _detail_title(self):  return "Bakım Detayı"

    def _durum_filter_items(self):
        return [
            ("Tüm Durumlar", None),
            ("Planli",    "Planli"),
            ("Yapildi",   "Yapildi"),
            ("Gecikmis",  "Gecikmis"),
        ]

    def _search_keys(self):
        return ["Planid", "Cihazid", "BakimPeriyodu", "Teknisyen"]

    def _filter_rows(self, rows):
        return list(rows)

    # ── KPI ─────────────────────────────────────────────
    def _kpi_definitions(self):
        return [
            ("toplam",    "TOPLAM BAKIM",     "0",  _C["accent"]),
            ("planli",    "PLANLİ",            "0",  _C["accent"]),
            ("yapildi",   "YAPILDI",           "0",  _C["green"]),
            ("gecikmis",  "GECİKMİŞ",          "0",  _C["red"]),
            ("son_bakim", "SON BAKIM",          "—",  _C["muted"]),
        ]

    def _compute_kpi(self, rows):
        if not rows:
            return dict(toplam="0", planli="0", yapildi="0", gecikmis="0", son_bakim="—")

        toplam   = len(rows)
        planli   = sum(1 for r in rows if r.get("Durum","") in ("Planli","Planlı"))
        yapildi  = sum(1 for r in rows if r.get("Durum","") in ("Yapildi","Yapıldı"))
        gecikmis = sum(1 for r in rows if r.get("Durum","") in ("Gecikmis","Gecikmiş"))

        tarihler = [r.get("BakimTarihi","") for r in rows if r.get("BakimTarihi")]
        son = to_ui_date(max(tarihler), "") if tarihler else "—"

        return dict(
            toplam=str(toplam), planli=str(planli),
            yapildi=str(yapildi), gecikmis=str(gecikmis), son_bakim=son,
        )

    # ── Detay paneli ────────────────────────────────────
    def _build_detail_header(self) -> QWidget:
        w = QWidget()
        w.setStyleSheet(
            f"background:{_C['panel']};border-bottom:1px solid {_C['border']};"
        )
        vl = QVBoxLayout(w)
        vl.setContentsMargins(14, 10, 14, 10)
        vl.setSpacing(6)

        self.lbl_det_title = QLabel("— Bir kayıt seçin —")
        self.lbl_det_title.setStyleSheet(
            f"font-size:13px;font-weight:600;color:{_C['text']};"
        )
        self.lbl_det_title.setWordWrap(True)
        vl.addWidget(self.lbl_det_title)

        meta = QHBoxLayout()
        meta.setSpacing(10)
        self.lbl_det_plan   = self._meta_label("—")
        self.lbl_det_bakim  = self._meta_label("—")
        self.lbl_det_durum  = self._meta_label("—")
        for lb in [self.lbl_det_plan, self.lbl_det_bakim, self.lbl_det_durum]:
            meta.addWidget(lb)
        meta.addStretch()
        vl.addLayout(meta)

        grid = QHBoxLayout()
        grid.setSpacing(16)
        self._fw_teknisyen = self._field_widget("Teknisyen")
        self._fw_tip       = self._field_widget("Tip")
        self._fw_periyot   = self._field_widget("Periyot")
        grid.addWidget(self._fw_teknisyen)
        grid.addWidget(self._fw_tip)
        grid.addWidget(self._fw_periyot)
        vl.addLayout(grid)

        self.lbl_det_islemler = QLabel("")
        self.lbl_det_islemler.setWordWrap(True)
        self.lbl_det_islemler.setStyleSheet(
            f"font-size:11px;color:{_C['muted']};padding-top:2px;"
        )
        vl.addWidget(self.lbl_det_islemler)
        return w

    def _update_detail(self, row: Dict):
        cihaz = row.get("Cihazid","")
        periyot = row.get("BakimPeriyodu","")
        self.lbl_det_title.setText(f"{cihaz}  —  Bakım  |  {periyot}")

        plan_t  = to_ui_date(row.get("PlanlananTarih",""), "")
        bakim_t = to_ui_date(row.get("BakimTarihi",""), "")
        self.lbl_det_plan.setText(f"📅 Plan: {plan_t}")
        self.lbl_det_bakim.setText(f"🔧 Yapılan: {bakim_t}")

        durum = row.get("Durum","")
        dur_c = _BAKIM_DURUM_COLOR.get(durum, _C["muted"])
        self.lbl_det_durum.setText(f"● {durum}" if durum else "—")
        self.lbl_det_durum.setStyleSheet(
            f"font-size:11px;font-weight:700;color:{dur_c};"
            f"background:{_C['panel']};"
        )

        self._set_field(self._fw_teknisyen, row.get("Teknisyen",""))
        self._set_field(self._fw_tip,       row.get("BakimTipi",""))
        self._set_field(self._fw_periyot,   row.get("BakimPeriyodu",""))

        islemler = row.get("YapilanIslemler","") or row.get("Aciklama","") or ""
        if len(islemler) > 200:
            islemler = islemler[:200] + "…"
        self.lbl_det_islemler.setText(islemler)

    # ── Giriş formu ─────────────────────────────────────
    def _build_entry_form(self) -> QWidget:
        return _BakimGirisForm(self._db, self._cihaz_id, parent=self)


# ─────────────────────────────────────────────────────────────
#  Bakım Giriş Formu (iç widget)
# ─────────────────────────────────────────────────────────────
class _BakimGirisForm(QWidget):
    saved = Signal()

    def __init__(self, db=None, cihaz_id=None, parent=None):
        super().__init__(parent)
        self._db = db
        self._cihaz_id = cihaz_id
        self._setup_ui()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(8)

        # Widget tanımları
        self.txt_periyot   = QLineEdit()
        self.txt_sira      = QLineEdit()
        self.txt_bakim     = QLineEdit()
        self.txt_tip       = QLineEdit()
        self.txt_teknisyen = QLineEdit()
        self.txt_islemler  = QTextEdit()
        self.txt_aciklama  = QTextEdit()
        self.txt_rapor     = QTextEdit()
        self.cmb_durum     = QComboBox()

        grp = QGroupBox("Bakım Kaydı")
        grid = QGridLayout(grp)
        grid.setContentsMargins(12, 12, 12, 12)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(8)

        self._r(grid, 0, "Bakım Periyodu", self.txt_periyot)

        self._r(grid, 1, "Bakım Sırası", self.txt_sira)

        self.dt_plan = QDateEdit(QDate.currentDate())
        self.dt_plan.setCalendarPopup(True); self.dt_plan.setDisplayFormat("dd.MM.yyyy")
        self._r(grid, 2, "Planlanan Tarih", self.dt_plan)

        self._r(grid, 3, "Bakım", self.txt_bakim)

        self.cmb_durum.addItems(["Planli", "Yapildi", "Gecikmis"])
        self._r(grid, 4, "Durum", self.cmb_durum)

        self.dt_bakim = QDateEdit(QDate.currentDate())
        self.dt_bakim.setCalendarPopup(True); self.dt_bakim.setDisplayFormat("dd.MM.yyyy")
        self._r(grid, 5, "Bakım Tarihi", self.dt_bakim)

        self._r(grid, 6, "Bakım Tipi", self.txt_tip)

        self.txt_islemler.setFixedHeight(70)
        self._r(grid, 7, "Yapılan İşlemler", self.txt_islemler)

        self.txt_aciklama.setFixedHeight(60)
        self._r(grid, 8, "Açıklama", self.txt_aciklama)

        self._r(grid, 9, "Teknisyen", self.txt_teknisyen)

        self.txt_rapor.setFixedHeight(60)
        self._r(grid, 10, "Rapor", self.txt_rapor)

        root.addWidget(grp)

        btns = QHBoxLayout()
        btns.addStretch()
        btn_temizle = QPushButton("Temizle")
        btn_temizle.setProperty("style-role", "refresh")
        btn_temizle.clicked.connect(self._clear)
        btns.addWidget(btn_temizle)

        btn_kaydet = QPushButton("Kaydet")
        btn_kaydet.setProperty("style-role", "action")
        try:
            IconRenderer.set_button_icon(btn_kaydet, "save",
                                         color=DarkTheme.BTN_PRIMARY_TEXT, size=14)
        except Exception:
            pass
        btn_kaydet.clicked.connect(self._save)
        btns.addWidget(btn_kaydet)
        root.addLayout(btns)

    def _r(self, grid, row, label, widget):
        lbl = QLabel(label)
        lbl.setProperty("style-role", "form")
        grid.addWidget(lbl, row, 0); grid.addWidget(widget, row, 1)

    def _save(self):
        if not self._db or not self._cihaz_id:
            QMessageBox.warning(self, "Uyarı", "Cihaz seçili değil.")
            return
        planid = f"{self._cihaz_id}-BK-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        data = {
            "Planid":         planid,
            "Cihazid":        self._cihaz_id,
            "BakimPeriyodu":  self.txt_periyot.text().strip(),
            "BakimSirasi":    self.txt_sira.text().strip(),
            "PlanlananTarih": self.dt_plan.date().toString("yyyy-MM-dd"),
            "Bakim":          self.txt_bakim.text().strip(),
            "Durum":          self.cmb_durum.currentText().strip(),
            "BakimTarihi":    self.dt_bakim.date().toString("yyyy-MM-dd"),
            "BakimTipi":      self.txt_tip.text().strip(),
            "YapilanIslemler":self.txt_islemler.toPlainText().strip(),
            "Aciklama":       self.txt_aciklama.toPlainText().strip(),
            "Teknisyen":      self.txt_teknisyen.text().strip(),
            "Rapor":          self.txt_rapor.toPlainText().strip(),
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


# ═════════════════════════════════════════════════════════════
#  KALİBRASYON FORMU
# ═════════════════════════════════════════════════════════════
_KAL_COLS = [
    ("Kalid",        "Kal. No",       90),
    ("Firma",        "Firma",         130),
    ("SertifikaNo",  "Sertifika",     110),
    ("YapilanTarih", "Yapılan",       100),
    ("BitisTarihi",  "Geçerlilik",    100),
    ("Durum",        "Durum",         100),
]


class KalibrasyonKayitForm(_BaseListDetailForm):
    """Kalibrasyon — liste + detay + KPI."""

    saved = Signal()

    def _columns(self):    return _KAL_COLS
    def _color_map(self):  return {"Durum": _KAL_DURUM_COLOR}
    def _repo_name(self):  return "Kalibrasyon"
    def _sort_key(self):   return "YapilanTarih"
    def _new_btn_label(self): return "+ Yeni Kalibrasyon"
    def _panel_title(self):   return "Kalibrasyon Kayıtları"
    def _detail_title(self):  return "Kalibrasyon Detayı"

    def _durum_filter_items(self):
        return [
            ("Tüm Durumlar", None),
            ("Geçerli",  "Gecerli"),
            ("Geçersiz", "Gecersiz"),
        ]

    def _search_keys(self):
        return ["Kalid", "Cihazid", "Firma", "SertifikaNo"]

    def _filter_rows(self, rows):
        return list(rows)

    # ── KPI ─────────────────────────────────────────────
    def _kpi_definitions(self):
        return [
            ("toplam",    "TOPLAM",           "0",   _C["accent"]),
            ("gecerli",   "GEÇERLİ",           "0",   _C["green"]),
            ("gecersiz",  "GEÇERSİZ",          "0",   _C["red"]),
            ("yaklasan",  "YAKLAŞAN BİTİŞ",    "0",   _C["amber"]),
            ("son_kal",   "SON KALİBRASYON",   "—",   _C["muted"]),
        ]

    def _compute_kpi(self, rows):
        if not rows:
            return dict(toplam="0", gecerli="0", gecersiz="0", yaklasan="0", son_kal="—")

        toplam   = len(rows)
        gecerli  = sum(1 for r in rows if r.get("Durum","") in ("Gecerli","Geçerli"))
        gecersiz = sum(1 for r in rows if r.get("Durum","") in ("Gecersiz","Geçersiz"))

        # 30 gün içinde biten kalibrasyonlar
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

        return dict(
            toplam=str(toplam), gecerli=str(gecerli),
            gecersiz=str(gecersiz), yaklasan=str(yaklasan), son_kal=son,
        )

    # ── Detay paneli ────────────────────────────────────
    def _build_detail_header(self) -> QWidget:
        w = QWidget()
        w.setStyleSheet(
            f"background:{_C['panel']};border-bottom:1px solid {_C['border']};"
        )
        vl = QVBoxLayout(w)
        vl.setContentsMargins(14, 10, 14, 10)
        vl.setSpacing(6)

        self.lbl_det_title = QLabel("— Bir kayıt seçin —")
        self.lbl_det_title.setStyleSheet(
            f"font-size:13px;font-weight:600;color:{_C['text']};"
        )
        self.lbl_det_title.setWordWrap(True)
        vl.addWidget(self.lbl_det_title)

        meta = QHBoxLayout()
        meta.setSpacing(10)
        self.lbl_det_yapilan = self._meta_label("—")
        self.lbl_det_bitis   = self._meta_label("—")
        self.lbl_det_durum   = self._meta_label("—")
        for lb in [self.lbl_det_yapilan, self.lbl_det_bitis, self.lbl_det_durum]:
            meta.addWidget(lb)
        meta.addStretch()
        vl.addLayout(meta)

        grid = QHBoxLayout()
        grid.setSpacing(16)
        self._fw_firma     = self._field_widget("Firma")
        self._fw_sertifika = self._field_widget("Sertifika No")
        self._fw_gecerlilik= self._field_widget("Geçerlilik")
        grid.addWidget(self._fw_firma)
        grid.addWidget(self._fw_sertifika)
        grid.addWidget(self._fw_gecerlilik)
        vl.addLayout(grid)

        self.lbl_det_aciklama = QLabel("")
        self.lbl_det_aciklama.setWordWrap(True)
        self.lbl_det_aciklama.setStyleSheet(
            f"font-size:11px;color:{_C['muted']};padding-top:2px;"
        )
        vl.addWidget(self.lbl_det_aciklama)
        return w

    def _update_detail(self, row: Dict):
        cihaz = row.get("Cihazid","")
        firma = row.get("Firma","")
        self.lbl_det_title.setText(f"{cihaz}  —  {firma}")

        self.lbl_det_yapilan.setText(
            f"📅 Yapılan: {to_ui_date(row.get('YapilanTarih',''), '')}"
        )
        bitis_str = to_ui_date(row.get("BitisTarihi",""), "")
        self.lbl_det_bitis.setText(f"⏱ Bitiş: {bitis_str}")

        # Bitiş rengi: 30 gün içindeyse amber, geçmişse kırmızı
        bitis_raw = row.get("BitisTarihi","")
        bitis_color = _C["muted"]
        if bitis_raw and len(bitis_raw) >= 10:
            try:
                bt = datetime.strptime(bitis_raw[:10], "%Y-%m-%d").date()
                bugun = datetime.now().date()
                if bt < bugun:
                    bitis_color = _C["red"]
                elif bt <= bugun + timedelta(days=30):
                    bitis_color = _C["amber"]
                else:
                    bitis_color = _C["green"]
            except ValueError:
                pass
        self.lbl_det_bitis.setStyleSheet(
            f"font-size:11px;color:{bitis_color};background:{_C['panel']};"
        )

        durum = row.get("Durum","")
        dur_c = _KAL_DURUM_COLOR.get(durum, _C["muted"])
        self.lbl_det_durum.setText(f"● {durum}" if durum else "—")
        self.lbl_det_durum.setStyleSheet(
            f"font-size:11px;font-weight:700;color:{dur_c};background:{_C['panel']};"
        )

        self._set_field(self._fw_firma,      row.get("Firma",""))
        self._set_field(self._fw_sertifika,  row.get("SertifikaNo",""))
        self._set_field(self._fw_gecerlilik, row.get("Gecerlilik",""))

        aciklama = row.get("Aciklama","") or ""
        if len(aciklama) > 200:
            aciklama = aciklama[:200] + "…"
        self.lbl_det_aciklama.setText(aciklama)

    # ── Giriş formu ─────────────────────────────────────
    def _build_entry_form(self) -> QWidget:
        return _KalibrasyonGirisForm(self._db, self._cihaz_id, parent=self)


# ─────────────────────────────────────────────────────────────
#  Kalibrasyon Giriş Formu (iç widget)
# ─────────────────────────────────────────────────────────────
class _KalibrasyonGirisForm(QWidget):
    saved = Signal()

    def __init__(self, db=None, cihaz_id=None, parent=None):
        super().__init__(parent)
        self._db = db
        self._cihaz_id = cihaz_id
        self._setup_ui()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(8)

        # Widget tanımları
        self.txt_firma      = QLineEdit()
        self.txt_sertifika  = QLineEdit()
        self.txt_gecerlilik = QLineEdit()
        self.txt_dosya      = QLineEdit()
        self.txt_aciklama   = QTextEdit()
        self.cmb_durum      = QComboBox()

        grp = QGroupBox("Kalibrasyon Kaydı")
        grid = QGridLayout(grp)
        grid.setContentsMargins(12, 12, 12, 12)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(8)

        self._r(grid, 0, "Firma", self.txt_firma)

        self._r(grid, 1, "Sertifika No", self.txt_sertifika)

        self.dt_yapilan = QDateEdit(QDate.currentDate())
        self.dt_yapilan.setCalendarPopup(True); self.dt_yapilan.setDisplayFormat("dd.MM.yyyy")
        self._r(grid, 2, "Yapılan Tarih", self.dt_yapilan)

        self._r(grid, 3, "Geçerlilik", self.txt_gecerlilik)

        self.dt_bitis = QDateEdit(QDate.currentDate())
        self.dt_bitis.setCalendarPopup(True); self.dt_bitis.setDisplayFormat("dd.MM.yyyy")
        self._r(grid, 4, "Bitiş Tarihi", self.dt_bitis)

        self.cmb_durum.addItems(["Gecerli", "Gecersiz"])
        self._r(grid, 5, "Durum", self.cmb_durum)

        self._r(grid, 6, "Dosya", self.txt_dosya)

        self.txt_aciklama.setFixedHeight(80)
        self._r(grid, 7, "Açıklama", self.txt_aciklama)

        root.addWidget(grp)

        btns = QHBoxLayout()
        btns.addStretch()
        btn_temizle = QPushButton("Temizle")
        btn_temizle.setProperty("style-role", "refresh")
        btn_temizle.clicked.connect(self._clear)
        btns.addWidget(btn_temizle)

        btn_kaydet = QPushButton("Kaydet")
        btn_kaydet.setProperty("style-role", "action")
        try:
            IconRenderer.set_button_icon(btn_kaydet, "save",
                                         color=DarkTheme.BTN_PRIMARY_TEXT, size=14)
        except Exception:
            pass
        btn_kaydet.clicked.connect(self._save)
        btns.addWidget(btn_kaydet)
        root.addLayout(btns)

    def _r(self, grid, row, label, widget):
        lbl = QLabel(label)
        lbl.setProperty("style-role", "form")
        grid.addWidget(lbl, row, 0); grid.addWidget(widget, row, 1)

    def _save(self):
        if not self._db or not self._cihaz_id:
            QMessageBox.warning(self, "Uyarı", "Cihaz seçili değil.")
            return
        kalid = f"{self._cihaz_id}-KL-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        data = {
            "Kalid":        kalid,
            "Cihazid":      self._cihaz_id,
            "Firma":        self.txt_firma.text().strip(),
            "SertifikaNo":  self.txt_sertifika.text().strip(),
            "YapilanTarih": self.dt_yapilan.date().toString("yyyy-MM-dd"),
            "Gecerlilik":   self.txt_gecerlilik.text().strip(),
            "BitisTarihi":  self.dt_bitis.date().toString("yyyy-MM-dd"),
            "Durum":        self.cmb_durum.currentText().strip(),
            "Dosya":        self.txt_dosya.text().strip(),
            "Aciklama":     self.txt_aciklama.toPlainText().strip(),
        }
        try:
            RepositoryRegistry(self._db).get("Kalibrasyon").insert(data)
            self.saved.emit()
            self._clear()
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
