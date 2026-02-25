# -*- coding: utf-8 -*-
"""
Kalibrasyon Formu
==================
  • Üstte KPI şeridi (Toplam / Geçerli / Geçersiz / Yaklaşan Bitiş / Son Kalibrasyon)
  • Sol: filtreler (Durum + Cihaz + Arama) + renk kodlu tablo
  • Sağ: her zaman görünür detay başlığı → buton bar → form container
  • Bitiş tarihi rengi dinamik: geçmiş → kırmızı, 30 gün → turuncu, uzak → yeşil
  • Form toggle yerine kaydırılabilir alanda açılır/kapanır
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

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
class KalibrasyonTableModel(QAbstractTableModel):
    def __init__(self, rows: Optional[List[Dict[str, Any]]] = None, parent=None):
        super().__init__(parent)
        self._rows    = rows or []
        self._keys    = [c[0] for c in KAL_COLUMNS]
        self._headers = [c[1] for c in KAL_COLUMNS]

    def rowCount(self, parent=QModelIndex()):    return len(self._rows)
    def columnCount(self, parent=QModelIndex()): return len(KAL_COLUMNS)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        row = self._rows[index.row()]
        key = self._keys[index.column()]

        if role == Qt.DisplayRole:
            val = row.get(key, "")
            if key in ("YapilanTarih", "BitisTarihi"):
                return to_ui_date(val, "")
            return str(val) if val else ""

        if role == Qt.TextAlignmentRole:
            if key in ("YapilanTarih", "BitisTarihi", "Durum"):
                return Qt.AlignCenter
            return Qt.AlignVCenter | Qt.AlignLeft

        if role == Qt.ForegroundRole:
            if key == "Durum":
                c = _DURUM_COLOR.get(row.get("Durum",""))
                return QColor(c) if c else None
            # Bitiş tarihini renklendir
            if key == "BitisTarihi":
                return QColor(_bitis_rengi(row.get("BitisTarihi","")))

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


def _bitis_rengi(bitis_raw: str) -> str:
    """Bitiş tarihine göre renk döndürür."""
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
    """Kalibrasyon listesi, detay paneli ve kayıt formu."""

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
            ("toplam",   "TOPLAM",            "0",  _C["accent"]),
            ("gecerli",  "GEÇERLİ",            "0",  _C["green"]),
            ("gecersiz", "GEÇERSİZ",           "0",  _C["red"]),
            ("yaklasan", "YAKLAŞAN BİTİŞ",     "0",  _C["amber"]),
            ("son_kal",  "SON KALİBRASYON",    "—",  _C["muted"]),
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
            defaults = [("toplam","0"),("gecerli","0"),("gecersiz","0"),
                        ("yaklasan","0"),("son_kal","—")]
            for k, v in defaults:
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

        # Tablo
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
        layout.addWidget(self.table, 1)

        self.lbl_count = QLabel("0 kayıt")
        self.lbl_count.setStyleSheet(
            f"font-size:11px;color:{_C['muted']};padding:4px 10px;"
            f"background:{_C['surface']};border-top:1px solid {_C['border']};"
        )
        layout.addWidget(self.lbl_count)
        return panel

    # ── Form Panel (Orta - Gizli) ──────────────────────
    def _build_form_panel(self) -> QWidget:
        """
        Tablo ile detay paneli arasında açılan form alanı.
        Başlangıçta gizlidir; _open_kal_form ile gösterilir.
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
        self.lbl_det_yapilan = self._meta_lbl("—")
        self.lbl_det_bitis   = self._meta_lbl("—")
        self.lbl_det_durum   = self._meta_lbl("—")
        for w in [self.lbl_det_yapilan, self.lbl_det_bitis, self.lbl_det_durum]:
            meta_row.addWidget(w)
        meta_row.addStretch()
        dh_l.addLayout(meta_row)

        fields_row = QHBoxLayout()
        fields_row.setSpacing(16)
        self.fw_firma      = self._field_lbl("Firma", "—")
        self.fw_sertifika  = self._field_lbl("Sertifika No", "—")
        self.fw_gecerlilik = self._field_lbl("Geçerlilik", "—")
        for w in [self.fw_firma, self.fw_sertifika, self.fw_gecerlilik]:
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
        lbl_sec = QLabel("Kalibrasyon Kaydı")
        lbl_sec.setStyleSheet(f"font-size:11px;font-weight:600;color:{_C['text']};")
        bb_l.addWidget(lbl_sec)
        bb_l.addStretch()
        self.btn_kayit_ekle = QPushButton("+ Kayıt Ekle")
        self.btn_kayit_ekle.setStyleSheet(
            S.get("btn_secondary", S.get("btn_primary", ""))
        )
        self.btn_kayit_ekle.setEnabled(False)
        self.btn_kayit_ekle.clicked.connect(self._open_kal_form)
        bb_l.addWidget(self.btn_kayit_ekle)
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
        cihaz = row.get("Cihazid","")
        firma = row.get("Firma","")
        self.lbl_det_title.setText(f"{cihaz}  —  {firma}")

        self.lbl_det_yapilan.setText(
            f"📅 Yapılan: {to_ui_date(row.get('YapilanTarih',''), '')}"
        )

        bitis_raw = row.get("BitisTarihi","")
        bitis_str = to_ui_date(bitis_raw, "")
        bitis_c   = _bitis_rengi(bitis_raw)
        self.lbl_det_bitis.setText(f"⏱ Bitiş: {bitis_str}")
        self.lbl_det_bitis.setStyleSheet(
            f"font-size:11px;color:{bitis_c};background:{_C['panel']};"
        )

        durum = row.get("Durum","")
        dur_c = _DURUM_COLOR.get(durum, _C["muted"])
        self.lbl_det_durum.setText(f"● {durum}" if durum else "—")
        self.lbl_det_durum.setStyleSheet(
            f"font-size:11px;font-weight:700;color:{dur_c};"
            f"background:{_C['panel']};"
        )

        self._set_field(self.fw_firma,      row.get("Firma",""))
        self._set_field(self.fw_sertifika,  row.get("SertifikaNo",""))
        self._set_field(self.fw_gecerlilik, row.get("Gecerlilik",""))

        aciklama = row.get("Aciklama","") or ""
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

    def _open_kal_form(self):
        self._clear_form_container()
        form = _KalibrasyonGirisForm(self._db, self._cihaz_id, parent=self)
        form.saved.connect(self._on_kal_saved)
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


# ─────────────────────────────────────────────────────────────
#  Kalibrasyon Giriş Formu  (sağ panelde form_container içinde açılır)
# ─────────────────────────────────────────────────────────────
class _KalibrasyonGirisForm(QWidget):
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

        grp = QGroupBox("Yeni Kalibrasyon Kaydı")
        grp.setStyleSheet(S["group"])
        grid = QGridLayout(grp)
        grid.setContentsMargins(12, 12, 12, 12)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(8)

        self.txt_firma = QLineEdit()
        self.txt_firma.setStyleSheet(S["input"])
        self._r(grid, 0, "Firma", self.txt_firma)

        self.txt_sertifika = QLineEdit()
        self.txt_sertifika.setStyleSheet(S["input"])
        self._r(grid, 1, "Sertifika No", self.txt_sertifika)

        self.dt_yapilan = QDateEdit(QDate.currentDate())
        self.dt_yapilan.setCalendarPopup(True)
        self.dt_yapilan.setDisplayFormat("dd.MM.yyyy")
        self.dt_yapilan.setStyleSheet(S["date"])
        self._r(grid, 2, "Yapılan Tarih", self.dt_yapilan)

        self.txt_gecerlilik = QLineEdit()
        self.txt_gecerlilik.setStyleSheet(S["input"])
        self._r(grid, 3, "Geçerlilik", self.txt_gecerlilik)

        self.dt_bitis = QDateEdit(QDate.currentDate())
        self.dt_bitis.setCalendarPopup(True)
        self.dt_bitis.setDisplayFormat("dd.MM.yyyy")
        self.dt_bitis.setStyleSheet(S["date"])
        self._r(grid, 4, "Bitiş Tarihi", self.dt_bitis)

        self.cmb_durum = QComboBox()
        self.cmb_durum.setStyleSheet(S["combo"])
        self.cmb_durum.addItems(["Gecerli", "Gecersiz"])
        self._r(grid, 5, "Durum", self.cmb_durum)

        self.txt_dosya = QLineEdit()
        self.txt_dosya.setStyleSheet(S["input"])
        self._r(grid, 6, "Dosya", self.txt_dosya)

        self.txt_aciklama = QTextEdit()
        self.txt_aciklama.setStyleSheet(S["input_text"])
        self.txt_aciklama.setFixedHeight(80)
        self._r(grid, 7, "Açıklama", self.txt_aciklama)

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
