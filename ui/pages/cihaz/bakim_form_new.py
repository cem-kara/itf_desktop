# -*- coding: utf-8 -*-
"""Bakım Formu — Refactored List/Detail View."""
from typing import List, Dict, Optional
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableView, QLineEdit, QComboBox,
    QPushButton, QLabel, QFrame, QSplitter, QTabWidget, QStackedWidget,
    QScrollArea, QMessageBox, QHeaderView, QProgressBar, QListWidget,
    QListWidgetItem, QDateEdit, QSizePolicy
)
from PySide6.QtCore import Qt, QDate, Signal
from core.logger import logger
from core.date_utils import to_ui_date
from database.repository_registry import RepositoryRegistry
from ui.styles.components import STYLES as S
from ui.styles.colors import DarkTheme
from ui.pages.cihaz.models.bakim_model import BakimTableModel, BAKIM_COLUMNS
from ui.pages.cihaz.services.bakim_workers import IslemKaydedici, DosyaYukleyici
from ui.pages.cihaz.services.bakim_utils import ay_ekle
from ui.pages.cihaz.components.bakim_widgets import FormPanel, create_field_label, set_field_value
from ui.pages.cihaz.forms.bakim_form_execution import _BakimGirisForm


# ════════════════════════════════════════════════════════════════════
#  RENKLERİ YÖNETİM
# ════════════════════════════════════════════════════════════════════
def _get_colors():
    """DarkTheme renklerini al."""
    return {
        "surface": getattr(DarkTheme, "SURFACE", "#13161d"),
        "panel": getattr(DarkTheme, "PANEL", "#191d26"),
        "border": getattr(DarkTheme, "BORDER", "#242938"),
        "accent": getattr(DarkTheme, "ACCENT", "#4f8ef7"),
        "green": getattr(DarkTheme, "STATUS_SUCCESS", "#3ecf8e"),
        "red": getattr(DarkTheme, "STATUS_ERROR", "#f75f5f"),
        "amber": getattr(DarkTheme, "STATUS_WARNING", "#ffa500"),
        "muted": getattr(DarkTheme, "TEXT_MUTED", "#5a6278"),
        "text": getattr(DarkTheme, "TEXT_PRIMARY", "#eef0f5"),
    }


# ════════════════════════════════════════════════════════════════════
#  ANA FORM SINIFI
# ════════════════════════════════════════════════════════════════════
class BakimKayitForm(QWidget):
    """Periyodik Bakım — Liste, Detay ve Kayıt Formu."""
    
    form_saved = Signal()

    def __init__(self, db=None, cihaz_id: Optional[str] = None, 
                 kullanici_adi: Optional[str] = None, action_guard=None, parent=None):
        super().__init__(parent)
        self._db = db
        self._cihaz_id = cihaz_id
        self._kullanici_adi = kullanici_adi or "Sistem"
        self._action_guard = action_guard
        
        self._colors = _get_colors()
        self._all_rows: List[Dict] = []
        self._rows: List[Dict] = []
        self._selected_row: Optional[Dict] = None
        
        self._setup_ui()
        self._load_data()

    # ══════════════════════════════════════════════════════
    #  UI KURULUMU
    # ══════════════════════════════════════════════════════
    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # KPI Şeridi
        root.addWidget(self._build_kpi_bar())

        # Ayırıcı çizgi
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background:{self._colors['border']};")
        root.addWidget(sep)

        # Sekmeli Ana Alan
        self._tabs = QTabWidget()
        self._tabs.setStyleSheet(S.get("tab", ""))
        self._tabs.currentChanged.connect(self._on_tab_changed)

        # Tab 0 — Bakım Listesi
        list_tab = self._build_list_tab()
        self._tabs.addTab(list_tab, "Bakım Listesi")

        # Tab 1 — Bakım Performansı
        self._perf_tab = QWidget()
        self._perf_tab.setStyleSheet(f"background:{self._colors['surface']};")
        self._tabs.addTab(self._perf_tab, "Bakım Performansı")

        root.addWidget(self._tabs, 1)

    def _build_kpi_bar(self) -> QWidget:
        """KPI bar — 5 metrik kartı."""
        bar = QWidget()
        bar.setFixedHeight(68)
        bar.setStyleSheet(f"background:{self._colors['surface']};")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(1)

        self._kpi_labels: Dict[str, QLabel] = {}
        cards = [
            ("toplam", "TOPLAM BAKIM", "0", self._colors["accent"]),
            ("planlandi", "PLANLANMIŞ", "0", self._colors["accent"]),
            ("yapildi", "YAPILDI", "0", self._colors["green"]),
            ("gecikmis", "GECİKMİŞ", "0", self._colors["red"]),
            ("son_bakim", "SON BAKIM", "—", self._colors["muted"]),
        ]
        for key, title, default, color in cards:
            layout.addWidget(self._make_kpi_card(key, title, default, color), 1)
        return bar

    def _make_kpi_card(self, key: str, title: str, default: str, color: str) -> QWidget:
        """Tekil KPI kartı."""
        card = QWidget()
        card.setStyleSheet(
            f"QWidget{{background:{self._colors['panel']};border-radius:6px;margin:0 2px;}}"
            f"QWidget:hover{{background:{self._colors['border']};}}"
        )
        vl = QVBoxLayout(card)
        vl.setContentsMargins(10, 6, 10, 6)
        vl.setSpacing(2)
        
        lbl_t = QLabel(title)
        lbl_t.setStyleSheet(
            f"font-size:9px;font-weight:600;letter-spacing:0.06em;color:{self._colors['muted']};background:transparent;"
        )
        lbl_v = QLabel(default)
        lbl_v.setStyleSheet(f"font-size:18px;font-weight:700;color:{color};background:transparent;")
        vl.addWidget(lbl_t)
        vl.addWidget(lbl_v)
        self._kpi_labels[key] = lbl_v
        return card

    def _update_kpi(self):
        """KPI metriklerini güncelle."""
        rows = self._all_rows
        if not rows:
            for k, v in [("toplam","0"),("planlandi","0"),("yapildi","0"),("gecikmis","0"),("son_bakim","—")]:
                self._kpi_labels[k].setText(v)
            return

        toplam = len(rows)
        planlandi = sum(1 for r in rows if r.get("Durum","") in ("Planlandi","Planlandı"))
        yapildi = sum(1 for r in rows if r.get("Durum","") in ("Yapildi","Yapıldı"))
        gecikmis = sum(1 for r in rows if r.get("Durum","") in ("Gecikmis","Gecikmiş"))
        tarihler = [r.get("BakimTarihi","") for r in rows if r.get("BakimTarihi")]
        son = to_ui_date(max(tarihler), "") if tarihler else "—"

        self._kpi_labels["toplam"].setText(str(toplam))
        self._kpi_labels["planlandi"].setText(str(planlandi))
        self._kpi_labels["yapildi"].setText(str(yapildi))
        self._kpi_labels["gecikmis"].setText(str(gecikmis))
        self._kpi_labels["son_bakim"].setText(son)

    def _build_list_tab(self) -> QWidget:
        """Liste Tab'ı — Sol Panel (Filtre + Tablo) + Sağ Panel (Detay)."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Horizontal Splitter
        splitter = QSplitter(Qt.Horizontal)
        splitter.setStyleSheet(S.get("splitter", ""))
        splitter.setHandleWidth(1)
        splitter.setChildrenCollapsible(False)

        splitter.addWidget(self._build_left_panel())
        splitter.addWidget(self._build_right_panel())
        splitter.setSizes([710, 350])

        layout.addWidget(splitter, 1)
        return tab

    def _build_left_panel(self) -> QWidget:
        """Sol Panel — Filtreler + Tablo."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Filtre Bar
        filter_bar = QWidget()
        filter_bar.setStyleSheet(
            f"background:{self._colors['surface']};border-bottom:1px solid {self._colors['border']};"
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
        layout.addWidget(self.table, 1)

        # Kayıt sayısı
        self.lbl_count = QLabel("0 kayıt")
        self.lbl_count.setStyleSheet(
            f"font-size:11px;color:{self._colors['muted']};padding:4px 10px;"
            f"background:{self._colors['surface']};border-top:1px solid {self._colors['border']};"
        )
        layout.addWidget(self.lbl_count)

        return panel

    def _build_right_panel(self) -> QWidget:
        """Sağ Panel — Detay + Execution Form."""
        outer = QWidget()
        outer.setStyleSheet(f"background:{self._colors['surface']};border-left:1px solid {self._colors['border']};")
        outer_layout = QVBoxLayout(outer)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        self._right_stack = QStackedWidget()
        outer_layout.addWidget(self._right_stack, 1)

        # ─ SAYFA 0 — Detay ─
        detail_page = self._build_detail_page()
        self._right_stack.addWidget(detail_page)

        # ─ SAYFA 1 — Execution Form ─
        form_page = self._build_form_page()
        self._right_stack.addWidget(form_page)

        # Show detail page by default
        self._right_stack.setCurrentIndex(0)
        return outer

    def _build_detail_page(self) -> QWidget:
        """Detay Sayfası."""
        page = QWidget()
        page.setStyleSheet(f"background:{self._colors['surface']};")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Detay Header
        self._det_header = QWidget()
        self._det_header.setStyleSheet(f"background:{self._colors['panel']};border-bottom:1px solid {self._colors['border']};")
        dh_layout = QVBoxLayout(self._det_header)
        dh_layout.setContentsMargins(14, 12, 14, 12)
        dh_layout.setSpacing(10)

        # Başlık + Durum
        top_row = QHBoxLayout()
        top_row.setSpacing(8)
        self.lbl_det_title = QLabel("— Bir kayıt seçin —")
        self.lbl_det_title.setStyleSheet(f"font-size:13px;font-weight:700;color:{self._colors['text']};")
        self.lbl_det_title.setWordWrap(True)
        top_row.addWidget(self.lbl_det_title, 1)

        self.lbl_det_durum = QLabel("")
        self.lbl_det_durum.setStyleSheet(
            f"font-size:10px;font-weight:700;color:{self._colors['muted']};padding:2px 8px;border-radius:10px;background:{self._colors['border']};"
        )
        self.lbl_det_durum.setAlignment(Qt.AlignCenter)
        top_row.addWidget(self.lbl_det_durum)
        dh_layout.addLayout(top_row)

        # Plan No
        self.lbl_det_planid = QLabel("")
        self.lbl_det_planid.setStyleSheet(f"font-size:10px;color:{self._colors['muted']};letter-spacing:0.04em;")
        dh_layout.addWidget(self.lbl_det_planid)

        # Ayırıcı
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background:{self._colors['border']};")
        dh_layout.addWidget(sep)

        # Grid: Tarih, Periyot, Sıra
        grid_row1 = QHBoxLayout()
        grid_row1.setSpacing(0)
        self.fw_tarih = create_field_label("Planlanan Tarih", "—")
        self.fw_periyot = create_field_label("Periyot", "—")
        self.fw_sira = create_field_label("Bakım Sırası", "—")
        for w in [self.fw_tarih, self.fw_periyot, self.fw_sira]:
            grid_row1.addWidget(w, 1)
        dh_layout.addLayout(grid_row1)

        # Grid: Tip, Teknisyen, Tarih
        grid_row2 = QHBoxLayout()
        grid_row2.setSpacing(0)
        self.fw_tip = create_field_label("Tip", "—")
        self.fw_teknisyen = create_field_label("Teknisyen", "—")
        self.fw_bakim_tar = create_field_label("Yapılan Tarih", "—")
        for w in [self.fw_tip, self.fw_teknisyen, self.fw_bakim_tar]:
            grid_row2.addWidget(w, 1)
        dh_layout.addLayout(grid_row2)

        layout.addWidget(self._det_header)

        # Aksiyon Çubuğu
        btn_bar = QWidget()
        btn_bar.setStyleSheet(f"background:{self._colors['surface']};border-bottom:1px solid {self._colors['border']};")
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
        layout.addWidget(btn_bar)

        # Execution Form Placeholder
        self._exec_content_stack = QStackedWidget()
        self._exec_content_stack.setStyleSheet(f"background:{self._colors['surface']};")

        # Boş placeholder
        placeholder = QWidget()
        placeholder.setStyleSheet(f"background:{self._colors['surface']};")
        ph_layout = QVBoxLayout(placeholder)
        ph_layout.addStretch()
        ph_lbl = QLabel('Kayıt seçip "Bakım Bilgisi Gir" butonuna tıklayın veya çift tıklayın.')
        ph_lbl.setAlignment(Qt.AlignCenter)
        ph_lbl.setStyleSheet(f"font-size:11px;color:{self._colors['muted']};")
        ph_layout.addWidget(ph_lbl)
        ph_layout.addStretch()
        self._exec_content_stack.addWidget(placeholder)

        # Execution form alanı
        self._exec_form_scroll = QScrollArea()
        self._exec_form_scroll.setWidgetResizable(True)
        self._exec_form_scroll.setStyleSheet(S.get("scroll", f"background:{self._colors['surface']};border:none;"))
        self._exec_form_inner = QWidget()
        self._exec_form_inner.setStyleSheet(f"background:{self._colors['surface']};")
        self._exec_form_layout = QVBoxLayout(self._exec_form_inner)
        self._exec_form_layout.setContentsMargins(10, 10, 10, 10)
        self._exec_form_layout.setSpacing(0)
        self._exec_form_layout.addStretch()
        self._exec_form_scroll.setWidget(self._exec_form_inner)
        self._exec_content_stack.addWidget(self._exec_form_scroll)

        layout.addWidget(self._exec_content_stack, 1)
        return page

    def _build_form_page(self) -> QWidget:
        """Form Sayfası."""
        page = QWidget()
        page.setStyleSheet(f"background:{self._colors['surface']};")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Form header
        form_hdr = QWidget()
        form_hdr.setFixedHeight(34)
        form_hdr.setStyleSheet(f"background:{self._colors['panel']};border-bottom:1px solid {self._colors['border']};")
        form_hdr_l = QHBoxLayout(form_hdr)
        form_hdr_l.setContentsMargins(12, 0, 6, 0)

        self._form_hdr_title = QLabel("Bakım Planı Formu")
        self._form_hdr_title.setStyleSheet(f"font-size:11px;font-weight:600;color:{self._colors['muted']};")
        form_hdr_l.addWidget(self._form_hdr_title)
        form_hdr_l.addStretch()

        btn_kapat = QPushButton("✕")
        btn_kapat.setFixedSize(22, 22)
        btn_kapat.setStyleSheet(
            f"QPushButton{{background:transparent;border:none;color:{self._colors['muted']};font-size:12px;border-radius:4px;}}"
            f"QPushButton:hover{{background:{self._colors['border']};color:{self._colors['text']};}}"
        )
        btn_kapat.clicked.connect(self._close_form)
        form_hdr_l.addWidget(btn_kapat)
        layout.addWidget(form_hdr)

        # Form content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(S.get("scroll", f"background:{self._colors['surface']};border:none;"))
        self._form_inner = QWidget()
        self._form_inner.setStyleSheet(f"background:{self._colors['surface']};")
        self._form_layout = QVBoxLayout(self._form_inner)
        self._form_layout.setContentsMargins(10, 10, 10, 10)
        self._form_layout.setSpacing(0)
        self._form_layout.addStretch()
        scroll.setWidget(self._form_inner)
        layout.addWidget(scroll, 1)

        return page

    # ══════════════════════════════════════════════════════
    #  VERİ YÜKLEME & FİLTRELEME
    # ══════════════════════════════════════════════════════
    def _load_data(self):
        """Verileri yükle."""
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
                rows = [r for r in rows if str(r.get("Cihazid","")) == str(self._cihaz_id)]
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
        """Cihaz filtresi seçeneklerini güncelle."""
        self.cmb_cihaz_filter.blockSignals(True)
        self.cmb_cihaz_filter.clear()
        self.cmb_cihaz_filter.addItem("Tüm Cihazlar", None)
        cihazlar = sorted({str(r.get("Cihazid","")) for r in self._all_rows if r.get("Cihazid")})
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
            repo = RepositoryRegistry(self._db).get("Sabitler")
            sabitler = repo.get_all() or []
            markalar = sorted([
                str(s.get("MenuEleman","")).strip()
                for s in sabitler
                if str(s.get("Kod","")).strip() == "Marka" and str(s.get("MenuEleman","")).strip()
            ])
            for m in markalar:
                if m and m != "None":
                    self.cmb_marka_filter.addItem(m, m)
        except Exception as e:
            logger.error(f"Marka filtresi yüklenemedi: {e}")
        
        self.cmb_marka_filter.blockSignals(False)

    def _apply_filters(self):
        """Filtreleri uygula."""
        filtered = list(self._all_rows)

        sel_durum = self.cmb_durum_filter.currentData()
        if sel_durum:
            filtered = [r for r in filtered if r.get("Durum","") == sel_durum]

        if not self._cihaz_id:
            sel_cihaz = self.cmb_cihaz_filter.currentData()
            if sel_cihaz:
                filtered = [r for r in filtered if str(r.get("Cihazid","")) == sel_cihaz]

            sel_marka = self.cmb_marka_filter.currentData()
            if sel_marka and self._db:
                try:
                    repo = RepositoryRegistry(self._db).get("Cihazlar")
                    cihazlar = repo.get_all() or []
                    marka_cihaz_ids = {str(c.get("Cihazid","")) for c in cihazlar if str(c.get("Marka","")) == sel_marka}
                    filtered = [r for r in filtered if str(r.get("Cihazid","")) in marka_cihaz_ids]
                except Exception as e:
                    logger.error(f"Marka filtrelemesi yapılamadı: {e}")

        txt = self.txt_filter.text().strip().lower()
        if txt:
            filtered = [r for r in filtered
                       if txt in str(r.get("Planid","")).lower()
                       or txt in str(r.get("Cihazid","")).lower()
                       or txt in str(r.get("Teknisyen","")).lower()
                       or txt in str(r.get("BakimPeriyodu","")).lower()]

        self._rows = filtered
        self._model.set_rows(filtered)
        self.lbl_count.setText(f"{len(filtered)} kayıt")

    # ══════════════════════════════════════════════════════
    #  SATIR SEÇİMİ → DETAY
    # ══════════════════════════════════════════════════════
    def _on_row_selected(self, current, _previous):
        """Satır seçildiğinde detayı göster."""
        if not current.isValid():
            return
        row = self._model.get_row(current.row())
        if not row:
            return
        self._selected_row = row
        self._update_detail(row)
        self.btn_kayit_ekle.setEnabled(True)
        self._right_stack.setCurrentIndex(0)

    def _update_detail(self, row: Dict):
        """Detay panelini güncelle."""
        cihaz = row.get("Cihazid","")
        planid = row.get("Planid","")
        durum = row.get("Durum","")

        self.lbl_det_title.setText(cihaz or "—")
        self.lbl_det_planid.setText(f"Plan No: {planid}" if planid else "")

        # Durum etiketi
        from ui.pages.cihaz.models.bakim_model import DURUM_COLOR
        dur_c = DURUM_COLOR.get(durum, self._colors["muted"])
        if durum:
            self.lbl_det_durum.setText(f"● {durum}")
            self.lbl_det_durum.setStyleSheet(
                f"font-size:10px;font-weight:700;color:{dur_c};padding:2px 8px;border-radius:10px;background:{dur_c}22;"
            )
        else:
            self.lbl_det_durum.setText("")

        # Alanları doldur
        set_field_value(self.fw_tarih, to_ui_date(row.get("PlanlananTarih",""), "—"))
        set_field_value(self.fw_periyot, row.get("BakimPeriyodu","") or "—")
        set_field_value(self.fw_sira, row.get("BakimSirasi","") or "—")
        set_field_value(self.fw_tip, row.get("BakimTipi","") or "—")
        set_field_value(self.fw_teknisyen, row.get("Teknisyen","") or "—")
        set_field_value(self.fw_bakim_tar, to_ui_date(row.get("BakimTarihi",""), "—"))

    # ══════════════════════════════════════════════════════
    #  FORM AÇMA / KAPAMA
    # ══════════════════════════════════════════════════════
    def _open_bakim_form(self):
        """Yeni bakım formu aç (PLAN_CREATION modu)."""
        # Clear form first
        while self._form_layout.count() > 1:
            item = self._form_layout.takeAt(0)
            if w := item.widget():
                w.setParent(None)

        from ui.pages.cihaz.bakim_form_execution import FormMode
        form = _BakimGirisForm(
            db=self._db,
            cihaz_id=self._cihaz_id,
            kullanici_adi=self._kullanici_adi,
            mode=FormMode.PLAN_CREATION,
            action_guard=self._action_guard,
            parent=self,
        )
        form.saved.connect(self._on_form_saved)
        self._form_layout.insertWidget(0, form)
        self._right_stack.setCurrentIndex(1)
        self._form_hdr_title.setText("Bakım Planı Oluştur")

    def _open_bakim_form_execution(self, index):
        """Seçilen satıra execution formu aç."""
        row = self._model.get_row(index.row())
        if row:
            self._open_bakim_form_execution_mode(row)

    def _open_bakim_form_execution_from_btn(self):
        """Butondan execution formu aç."""
        if self._selected_row:
            self._open_bakim_form_execution_mode(self._selected_row)

    def _open_bakim_form_execution_mode(self, row: Dict):
        """EXECUTION_INFO modunda formu aç."""
        # Clear form first
        while self._form_layout.count() > 1:
            item = self._form_layout.takeAt(0)
            if w := item.widget():
                w.setParent(None)

        from ui.pages.cihaz.forms.bakim_form_execution import FormMode
        form = _BakimGirisForm(
            db=self._db,
            cihaz_id=self._cihaz_id,
            kullanici_adi=self._kullanici_adi,
            mode=FormMode.EXECUTION_INFO,
            plan_data=row,
            action_guard=self._action_guard,
            parent=self,
        )
        form.saved.connect(self._on_form_saved)
        self._form_layout.insertWidget(0, form)
        self._right_stack.setCurrentIndex(1)
        self._form_hdr_title.setText(f"Bakım Bilgisi — {row.get('Planid','')}")

    def _close_form(self):
        """Formu kapat."""
        self._right_stack.setCurrentIndex(0)

    def _open_toplu_plan_dialog(self):
        """Toplu plan dialogunu aç."""
        from ui.pages.cihaz.forms.bakim_form_bulk import TopluBakimPlanDlg
        dlg = TopluBakimPlanDlg(db=self._db, parent=self)
        if dlg.exec():
            self._load_data()

    def _on_form_saved(self):
        """Form kaydedilince."""
        self._close_form()
        self._load_data()
        self.form_saved.emit()

    def _on_tab_changed(self, idx: int):
        """Tab değiştiğinde."""
        if idx == 1:
            # Performans tab yükle (TODO: implement)
            pass

    # ══════════════════════════════════════════════════════
    #  PUBLIK METOTLAR
    # ══════════════════════════════════════════════════════
    def set_cihaz_id(self, cihaz_id: Optional[str]):
        """Cihaz ID'sini ayarla."""
        self._cihaz_id = cihaz_id
        self.cmb_cihaz_filter.setVisible(not bool(cihaz_id))
        self._load_data()
