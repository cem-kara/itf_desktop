# -*- coding: utf-8 -*-
"""
Bakım Sayfası - View Layer
==========================
UI layout, KPI bar, filtre paneli, tablo, detay + form paneli.
Hiçbir business logic yok.
"""
from typing import Optional, Dict, Any, List
from PySide6.QtCore import Qt, Signal, QModelIndex, QDate
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame,
    QTableView, QSplitter, QHeaderView,
    QLabel, QLineEdit, QComboBox, QPushButton,
    QScrollArea, QGridLayout, QGroupBox, QDateEdit, QTextEdit
)
from PySide6.QtGui import QColor

from core.date_utils import to_ui_date
from ui.styles.components import STYLES as S
from ui.styles import DarkTheme
from ui.pages.cihaz.components import (
    RecordTableModel, BakimTableDelegate, BakimKPIBar, BakimFilterPanel
)


class BakimView(QWidget):
    """Bakım listesi ve planlama sayfası"""
    
    # Signals
    on_bakim_selected = Signal(str)  # bakim_id
    on_add_plan_clicked = Signal()
    on_record_execution_clicked = Signal(str)  # bakim_id
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
        self.kpi_bar = BakimKPIBar()
        root.addWidget(self.kpi_bar)
        
        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background:{getattr(DarkTheme, 'BORDER', '#242938')};")
        root.addWidget(sep)
        
        # Ana splitter (sol: filtreler + tablo, sağ: detay)
        self._h_splitter = QSplitter(Qt.Horizontal)
        self._h_splitter.setStyleSheet(S.get("splitter", ""))
        
        # Sol: Filtreler + Tablo
        self._h_splitter.addWidget(self._build_left_panel())
        
        # Sağ: Detay + Form
        self._h_splitter.addWidget(self._build_right_panel())
        
        self._h_splitter.setHandleWidth(5)
        self._h_splitter.setChildrenCollapsible(False)
        self._h_splitter.setSizes([800, 400])
        
        root.addWidget(self._h_splitter, 1)
    
    def _build_left_panel(self) -> QWidget:
        """Sol panel: Filtreler + Tablo"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        
        # Filtre paneli (reusable component)
        self.filter_panel = BakimFilterPanel()
        self.filter_panel.filter_changed.connect(
            lambda search, filters: self.on_filter_changed.emit()
        )
        layout.addWidget(self.filter_panel)
        
        # Tablo
        self.table = QTableView()
        self.table.setSelectionBehavior(QTableView.SelectRows)
        self.table.setSelectionMode(QTableView.SingleSelection)
        self.table.horizontalHeader().setStretchLastSection(False)
        self.table.verticalHeader().setVisible(False)
        self.table.clicked.connect(self._on_table_clicked)
        layout.addWidget(self.table, 1)
        
        return panel
    
    def _build_right_panel(self) -> QWidget:
        """Sağ panel: Detay + Form"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        
        # Detay başlığı
        self.detail_label = QLabel("Bakım Kaydı Seçin")
        self.detail_label.setStyleSheet("font-weight:bold; font-size:12px; color:#999;")
        layout.addWidget(self.detail_label)
        
        # Detay scroll area
        self.detail_area = QScrollArea()
        self.detail_area.setWidgetResizable(True)
        self.detail_widget = QWidget()
        self.detail_layout = QVBoxLayout(self.detail_widget)
        self.detail_area.setWidget(self.detail_widget)
        layout.addWidget(self.detail_area, 1)
        
        # Form paneli (gizli, toggle edilir)
        self.form_group = QGroupBox("Bakım Bilgisi Giriş")
        self.form_group.setVisible(False)
        fg_layout = QVBoxLayout(self.form_group)
        fg_layout.setSpacing(6)
        
        # Form alanları
        fg_layout.addWidget(QLabel("Bakım Tarihi:"))
        self.form_date = QDateEdit()
        self.form_date.setCalendarPopup(True)
        self.form_date.setDate(QDate.currentDate())
        fg_layout.addWidget(self.form_date)
        
        fg_layout.addWidget(QLabel("Bakım Tipi:"))
        self.form_tip = QComboBox()
        self.form_tip.addItems(["Rutin", "Acil", "Preventif", "Aydınlatma"])
        fg_layout.addWidget(self.form_tip)
        
        fg_layout.addWidget(QLabel("Teknisyen:"))
        self.form_teknisyen = QLineEdit()
        fg_layout.addWidget(self.form_teknisyen)
        
        fg_layout.addWidget(QLabel("Açıklama:"))
        self.form_aciklama = QTextEdit()
        self.form_aciklama.setMaximumHeight(80)
        fg_layout.addWidget(self.form_aciklama)
        
        layout.addWidget(self.form_group)
        
        # Buton bar
        btn_layout = QHBoxLayout()
        
        self.btn_add_plan = QPushButton("Plan Ekle")
        self.btn_add_plan.clicked.connect(self.on_add_plan_clicked)
        btn_layout.addWidget(self.btn_add_plan)
        
        self.btn_record = QPushButton("Yaptıkları Kaydet")
        self.btn_record.clicked.connect(lambda: self.on_record_execution_clicked.emit(
            self.selected_bakim_id or ""
        ))
        btn_layout.addWidget(self.btn_record)
        
        layout.addLayout(btn_layout)
        
        return panel
    
    def _on_table_clicked(self, index: QModelIndex):
        """Tablo satırı tıklandı"""
        # View: presenter'dan bakim_id'yi al
        pass
    
    # ──────────────────────────────────────────────────────
    # Dışarıdan erişim (Presenter → View)
    # ──────────────────────────────────────────────────────
    
    @property
    def selected_bakim_id(self) -> Optional[str]:
        """Seçili bakım kaydı ID'si"""
        # TODO: Model'den al
        return None
    
    def get_filter_values(self) -> Dict[str, str]:
        """Aktif filtre değerlerini döndür"""
        search, filters = self.filter_panel.get_filters()
        return {
            "search": search,
            "durum": filters.get("durum", "Tümü"),
            "tip": filters.get("tip", "Tümü"),
        }
    
    def set_kpi_values(self, toplam: int, planlanmis: int, yapildi: int, gecikmiş: int, son_bakim: str):
        """KPI değerlerini güncelle"""
        self.kpi_bar.update_value("toplam", toplam)
        self.kpi_bar.update_value("ayda", yapildi)
        # ort_aralık hesaplanacak
        self.kpi_bar.update_value("overdue", gecikmiş)
        self.kpi_bar.update_value("sonraki", son_bakim)
    
    def set_table_data(self, rows: List[Dict[str, Any]]):
        """Tablo verisi (presenter tarafından ayarlanacak)"""
        # TODO: Model'ı güncelle
        pass
    
    def show_detail(self, bakim: Dict[str, Any]):
        """Sağ panelde detay göster"""
        plan_id = bakim.get("Planid", "?")
        self.detail_label.setText(f"Bakım Plan #{plan_id}")
        
        # Detail bilgisi
        detail_text = f"""
        <b>Cihaz:</b> {bakim.get('Cihazid', '?')}<br>
        <b>Plan Tarihi:</b> {bakim.get('PlanlananTarih', '?')}<br>
        <b>Bakım Tarihi:</b> {bakim.get('BakimTarihi', '—')}<br>
        <b>Bakım Tipi:</b> {bakim.get('BakimTipi', '?')}<br>
        <b>Periyot:</b> {bakim.get('BakimPeriyodu', '?')}<br>
        <b>Teknisyen:</b> {bakim.get('Teknisyen', '—')}<br>
        <b>Durum:</b> {bakim.get('Durum', '?')}
        """
        
        # Detail layout'ı temizle
        for i in reversed(range(self.detail_layout.count())):
            self.detail_layout.itemAt(i).widget().setParent(None)
        
        detail_lbl = QLabel(detail_text)
        detail_lbl.setWordWrap(True)
        self.detail_layout.addWidget(detail_lbl)
        self.detail_layout.addStretch()
        
        # Form göster
        self.form_group.setVisible(bakim.get("Durum") == "Planlandı")
    
    def show_form(self, mode: str):
        """Form göster"""
        self.form_group.setVisible(True)
    
    def hide_form(self):
        """Form gizle"""
        self.form_group.setVisible(False)
    
    def get_form_data(self) -> Dict[str, Any]:
        """Form verisi al"""
        return {
            "bakim_tarihi": self.form_date.date().toString("yyyy-MM-dd"),
            "bakim_tipi": self.form_tip.currentText(),
            "teknisyen": self.form_teknisyen.text(),
            "aciklama": self.form_aciklama.toPlainText(),
        }
    
    def clear_form(self):
        """Form alanlarını temizle"""
        self.form_date.setDate(QDate.currentDate())
        self.form_tip.setCurrentIndex(0)
        self.form_teknisyen.clear()
        self.form_aciklama.clear()
