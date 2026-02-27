# -*- coding: utf-8 -*-
"""
Arıza Sayfası - View Layer
===========================
UI layout, KPI bar, filtre paneli, tablo, detay paneli.
Hiçbir business logic yok - sadece layout ve signal wiring.
"""
from typing import Optional, Dict, Any, List
from pathlib import Path

from PySide6.QtCore import Qt, Signal, QModelIndex
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame,
    QTableView, QSplitter, QHeaderView, QTabWidget,
    QLabel, QLineEdit, QComboBox, QPushButton,
    QMenu, QMessageBox, QSizePolicy, QScrollArea, QGridLayout,
    QGroupBox, QTextEdit
)
from PySide6.QtGui import QColor, QCursor

from core.date_utils import to_ui_date
from core.logger import logger
from core.paths import DATA_DIR
from ui.styles.components import STYLES as S
from ui.styles import DarkTheme

# Renk sabitleri
_C = {
    "red":    getattr(DarkTheme, "DANGER",  "#f75f5f"),
    "amber":  getattr(DarkTheme, "WARNING", "#f5a623"),
    "green":  getattr(DarkTheme, "SUCCESS", "#3ecf8e"),
    "accent": getattr(DarkTheme, "ACCENT",  "#4f8ef7"),
    "muted":  getattr(DarkTheme, "TEXT_MUTED", "#5a6278"),
}

_DURUM_COLOR = {
    "Açık": _C["red"], "Acik": _C["red"],
    "Devam Ediyor": _C["amber"],
    "Kapalı": _C["green"], "Kapali": _C["green"],
}

_DURUM_BG_COLOR = {
    "Açık": "rgba(247, 95, 95, 0.20)", "Acik": "rgba(247, 95, 95, 0.20)",
    "Devam Ediyor": "rgba(245, 166, 35, 0.20)",
    "Kapalı": "rgba(62, 207, 142, 0.20)", "Kapali": "rgba(62, 207, 142, 0.20)",
}

_ONCELIK_COLOR = {
    "Kritik": _C["red"], "Yüksek": _C["amber"],
    "Orta": _C["accent"], "Düşük": _C["muted"],
}

_ONCELIK_BG_COLOR = {
    "Kritik": "rgba(247, 95, 95, 0.20)", "Yüksek": "rgba(245, 166, 35, 0.20)",
    "Orta": "rgba(79, 142, 247, 0.20)", "Düşük": "rgba(90, 98, 120, 0.15)",
}

# Tablo kolonları
ARIZA_COLUMNS = [
    ("Arizaid", "Arıza No", 90),
    ("Cihazid", "Cihaz", 110),
    ("BaslangicTarihi", "Tarih", 100),
    ("ArizaTipi", "Tip", 120),
    ("Oncelik", "Öncelik", 90),
    ("Baslik", "Başlık", 220),
    ("Durum", "Durum", 110),
]


class ArizaView(QWidget):
    """Arıza listesi sayfası Ana View"""
    
    # Signals
    on_ariza_selected = Signal(str)  # ariza_id
    on_add_clicked = Signal()
    on_edit_clicked = Signal(str)  # ariza_id
    on_delete_clicked = Signal(str)  # ariza_id
    on_filter_changed = Signal()
    on_tab_changed = Signal(int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
    
    def _setup_ui(self):
        """Ana layout inşa et"""
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        
        # KPI Şeridi
        root.addWidget(self._build_kpi_bar())
        
        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background:{getattr(DarkTheme, 'BORDER', '#242938')};")
        root.addWidget(sep)
        
        # Tab widget
        self._tabs = QTabWidget()
        self._tabs.setStyleSheet(S.get("tab", ""))
        self._tabs.currentChanged.connect(lambda idx: self.on_tab_changed.emit(idx))
        
        # Tab 1: Arıza Listesi
        list_tab = QWidget()
        lt_layout = QVBoxLayout(list_tab)
        lt_layout.setContentsMargins(0, 0, 0, 0)
        lt_layout.setSpacing(0)
        
        self._h_splitter = QSplitter(Qt.Horizontal)
        self._h_splitter.setStyleSheet(S.get("splitter", ""))
        self._h_splitter.addWidget(self._build_left_panel())
        self._h_splitter.addWidget(self._build_form_panel())
        self._h_splitter.addWidget(self._build_right_panel())
        self._h_splitter.setHandleWidth(0)
        self._h_splitter.setChildrenCollapsible(False)
        self._h_splitter.setSizes([710, 0, 350])
        
        lt_layout.addWidget(self._h_splitter)
        self._tabs.addTab(list_tab, "Arıza Listesi")
        
        # Tab 2: Cihaz Performansı
        perf_tab = QWidget()
        perf_layout = QVBoxLayout(perf_tab)
        perf_layout.addWidget(QLabel("Cihaz Performansı (TODO)"))
        self._tabs.addTab(perf_tab, "Cihaz Performansı")
        
        root.addWidget(self._tabs, 1)
    
    def _build_kpi_bar(self) -> QWidget:
        """KPI metrik şeridi"""
        bar = QWidget()
        bar.setFixedHeight(68)
        bar.setStyleSheet(f"background:{getattr(DarkTheme, 'SURFACE', '#13161d')};")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(1)
        
        self._kpi = {}
        cards = [
            ("toplam", "TOPLAM ARIZA", "0", _C["accent"]),
            ("acik", "AÇIK / KRİTİK", "0 / 0", _C["red"]),
            ("ort_sure", "ORT. ÇÖZÜM", "— gün", _C["amber"]),
            ("kapali_ay", "BU AY KAPANDI", "0", _C["green"]),
            ("yinelenen", "YİNELENEN ARIZA", "0", _C["red"]),
        ]
        
        for key, title, default, color in cards:
            card = self._make_kpi_card(key, title, default, color)
            layout.addWidget(card, 1)
        
        return bar
    
    def _make_kpi_card(self, key: str, title: str, default: str, color: str) -> QWidget:
        """Tek KPI kartı"""
        card = QWidget()
        card.setStyleSheet(
            f"QWidget{{background:{getattr(DarkTheme, 'PANEL', '#191d26')};"
            f"border-radius:6px; margin:0 2px;}}"
        )
        vl = QVBoxLayout(card)
        vl.setContentsMargins(10, 6, 10, 6)
        vl.setSpacing(2)
        
        lbl_title = QLabel(title)
        lbl_title.setStyleSheet(
            f"font-size:9px; font-weight:600; letter-spacing:0.06em; color:{color};"
        )
        
        lbl_value = QLabel(default)
        lbl_value.setStyleSheet(f"font-size:16px; font-weight:bold; color:{color};")
        
        vl.addWidget(lbl_title)
        vl.addWidget(lbl_value)
        
        self._kpi[key] = lbl_value
        return card
    
    def _build_left_panel(self) -> QWidget:
        """Sol panel: Filtreler + Tablo"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        
        # Filtreler
        filter_group = QGroupBox("Filtreler")
        fg_layout = QVBoxLayout(filter_group)
        
        # Arama
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Başlık veya No ara...")
        self.search_input.textChanged.connect(self.on_filter_changed)
        fg_layout.addWidget(QLabel("Arama:"))
        fg_layout.addWidget(self.search_input)
        
        # Durum
        self.durum_combo = QComboBox()
        self.durum_combo.addItems(["Tümü", "Açık", "Kapalı", "Devam Ediyor"])
        self.durum_combo.currentTextChanged.connect(self.on_filter_changed)
        fg_layout.addWidget(QLabel("Durum:"))
        fg_layout.addWidget(self.durum_combo)
        
        # Öncelik
        self.oncelik_combo = QComboBox()
        self.oncelik_combo.addItems(["Tümü", "Kritik", "Yüksek", "Orta", "Düşük"])
        self.oncelik_combo.currentTextChanged.connect(self.on_filter_changed)
        fg_layout.addWidget(QLabel("Öncelik:"))
        fg_layout.addWidget(self.oncelik_combo)
        
        layout.addWidget(filter_group)
        
        # Tablo
        self.table = QTableView()
        self.table.setSelectionBehavior(QTableView.SelectRows)
        self.table.setSelectionMode(QTableView.SingleSelection)
        self.table.horizontalHeader().setStretchLastSection(False)
        self.table.verticalHeader().setVisible(False)
        self.table.clicked.connect(self._on_table_clicked)
        layout.addWidget(self.table, 1)
        
        return panel
    
    def _build_form_panel(self) -> QWidget:
        """Orta panel: Form (gizli, toggle edilir)"""
        self.form_panel = QWidget()
        self.form_layout = QVBoxLayout(self.form_panel)
        self.form_layout.setContentsMargins(8, 8, 8, 8)
        self.form_layout.addWidget(QLabel("Form (TODO)"))
        return self.form_panel
    
    def _build_right_panel(self) -> QWidget:
        """Sağ panel: Detay ve işlemler"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        
        # Detay göstergesi
        self.detail_label = QLabel("Arıza Seçin")
        self.detail_label.setStyleSheet("font-weight:bold; color:#999;")
        layout.addWidget(self.detail_label)
        
        # Detay area
        self.detail_area = QScrollArea()
        self.detail_area.setWidgetResizable(True)
        self.detail_widget = QWidget()
        self.detail_layout = QVBoxLayout(self.detail_widget)
        self.detail_area.setWidget(self.detail_widget)
        layout.addWidget(self.detail_area, 1)
        
        # Butonlar
        btn_layout = QHBoxLayout()
        
        self.btn_add = QPushButton("Ekle")
        self.btn_add.clicked.connect(self.on_add_clicked)
        btn_layout.addWidget(self.btn_add)
        
        self.btn_edit = QPushButton("Düzenle")
        self.btn_edit.clicked.connect(lambda: self.on_edit_clicked.emit(self.selected_ariza_id or ""))
        btn_layout.addWidget(self.btn_edit)
        
        self.btn_delete = QPushButton("Sil")
        self.btn_delete.clicked.connect(lambda: self.on_delete_clicked.emit(self.selected_ariza_id or ""))
        btn_layout.addWidget(self.btn_delete)
        
        layout.addLayout(btn_layout)
        
        return panel
    
    def _on_table_clicked(self, index: QModelIndex):
        """Tablo satırı tıklandı"""
        # Model'den ariza_id al (TBD: presenter'dan gelecek)
        pass
    
    # ──────────────────────────────────────────────────────
    # Dışarıdan erişim metodları (Presenter → View)
    # ──────────────────────────────────────────────────────
    
    @property
    def selected_ariza_id(self) -> Optional[str]:
        """Seçili arıza ID'si"""
        # TODO: Model'den al
        return None
    
    def set_kpi_values(self, toplam: int, acik: int, kritik: int, 
                      ort_sure: float, kapali_ay: int, yinelenen: int):
        """KPI değerlerini güncelle"""
        self._kpi["toplam"].setText(str(toplam))
        self._kpi["acik"].setText(f"{acik} / {kritik}")
        self._kpi["ort_sure"].setText(f"{ort_sure:.1f} gün" if ort_sure > 0 else "— gün")
        self._kpi["kapali_ay"].setText(str(kapali_ay))
        self._kpi["yinelenen"].setText(str(yinelenen))
    
    def set_table_data(self, rows: List[Dict[str, Any]]):
        """Tablo verisi (Presenter → View)"""
        # TODO: Model setleme
        pass
    
    def show_detail(self, ariza: Dict[str, Any]):
        """Sağ panelde detay göster"""
        self.detail_label.setText(f"Arıza #{ariza.get('Arizaid', '?')}")
        
        # Detay bilgisini göster
        detail_text = f"""
        <b>Başlık:</b> {ariza.get('Baslik', '?')}<br>
        <b>Cihaz:</b> {ariza.get('Cihazid', '?')}<br>
        <b>Tarih:</b> {ariza.get('BaslangicTarihi', '?')}<br>
        <b>Öncelik:</b> {ariza.get('Oncelik', '?')}<br>
        <b>Durum:</b> {ariza.get('Durum', '?')}<br>
        <b>Açıklama:</b> {ariza.get('Aciklama', '?')}
        """
        
        for i in reversed(range(self.detail_layout.count())): 
            self.detail_layout.itemAt(i).widget().setParent(None)
        
        detail_lbl = QLabel(detail_text)
        detail_lbl.setWordWrap(True)
        self.detail_layout.addWidget(detail_lbl)
        self.detail_layout.addStretch()
    
    def get_filter_values(self) -> Dict[str, str]:
        """Aktif filtre değerlerini döndür"""
        return {
            "search": self.search_input.text(),
            "durum": self.durum_combo.currentText(),
            "oncelik": self.oncelik_combo.currentText(),
        }
