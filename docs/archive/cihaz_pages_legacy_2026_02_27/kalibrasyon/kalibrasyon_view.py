# -*- coding: utf-8 -*-
"""
Kalibrasyon Sayfası - View Layer
=================================
UI layout, KPI bar, filtre paneli, tablo, detay + form paneli.
"""
from typing import Optional, Dict, Any, List
from PySide6.QtCore import Qt, Signal, QModelIndex, QDate
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame,
    QTableView, QSplitter,
    QLabel, QLineEdit, QComboBox, QPushButton,
    QScrollArea, QGroupBox, QDateEdit, QTextEdit
)

from ui.styles.components import STYLES as S
from ui.styles import DarkTheme
from ui.pages.cihaz.components import (
    RecordTableModel, KalibrasyonTableDelegate, KalibrasyonKPIBar, KalibrasyonFilterPanel
)


class KalibrasyonView(QWidget):
    """Kalibrasyon listesi ve yönetimi sayfası"""
    
    on_kalibrasyon_selected = Signal(str)
    on_add_record_clicked = Signal()
    on_update_record_clicked = Signal(str)
    on_filter_changed = Signal()
    on_tab_changed = Signal(int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
    
    def _setup_ui(self):
        """Ana layout"""
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        
        self.kpi_bar = KalibrasyonKPIBar()
        root.addWidget(self.kpi_bar)
        
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background:{getattr(DarkTheme, 'BORDER', '#242938')};")
        root.addWidget(sep)
        
        self._h_splitter = QSplitter(Qt.Horizontal)
        self._h_splitter.setStyleSheet(S.get("splitter", ""))
        
        self._h_splitter.addWidget(self._build_left_panel())
        self._h_splitter.addWidget(self._build_right_panel())
        
        self._h_splitter.setHandleWidth(5)
        self._h_splitter.setChildrenCollapsible(False)
        self._h_splitter.setSizes([800, 400])
        
        root.addWidget(self._h_splitter, 1)
    
    def _build_left_panel(self) -> QWidget:
        """Sol: Filtreler + Tablo"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        
        self.filter_panel = KalibrasyonFilterPanel()
        self.filter_panel.filter_changed.connect(lambda s, f: self.on_filter_changed.emit())
        layout.addWidget(self.filter_panel)
        
        self.table = QTableView()
        self.table.setSelectionBehavior(QTableView.SelectRows)
        self.table.setSelectionMode(QTableView.SingleSelection)
        self.table.horizontalHeader().setStretchLastSection(False)
        self.table.verticalHeader().setVisible(False)
        self.table.clicked.connect(self._on_table_clicked)
        layout.addWidget(self.table, 1)
        
        return panel
    
    def _build_right_panel(self) -> QWidget:
        """Sağ: Detay + Form"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        
        self.detail_label = QLabel("Kalibrasyon Kaydı Seçin")
        self.detail_label.setStyleSheet("font-weight:bold; font-size:12px; color:#999;")
        layout.addWidget(self.detail_label)
        
        self.detail_area = QScrollArea()
        self.detail_area.setWidgetResizable(True)
        self.detail_widget = QWidget()
        self.detail_layout = QVBoxLayout(self.detail_widget)
        self.detail_area.setWidget(self.detail_widget)
        layout.addWidget(self.detail_area, 1)
        
        # Form
        self.form_group = QGroupBox("Kalibrasyon Sonucu Giriş")
        self.form_group.setVisible(False)
        fg_layout = QVBoxLayout(self.form_group)
        fg_layout.setSpacing(6)
        
        fg_layout.addWidget(QLabel("Kalibrasyon Tarihi:"))
        self.form_date = QDateEdit()
        self.form_date.setCalendarPopup(True)
        self.form_date.setDate(QDate.currentDate())
        fg_layout.addWidget(self.form_date)
        
        fg_layout.addWidget(QLabel("Sonuç:"))
        self.form_sonuc = QComboBox()
        self.form_sonuc.addItems(["Geçti", "İnceleme", "Başarısız"])
        fg_layout.addWidget(self.form_sonuc)
        
        fg_layout.addWidget(QLabel("Açıklama:"))
        self.form_aciklama = QTextEdit()
        self.form_aciklama.setMaximumHeight(80)
        fg_layout.addWidget(self.form_aciklama)
        
        layout.addWidget(self.form_group)
        
        btn_layout = QHBoxLayout()
        
        self.btn_add = QPushButton("Kayıt Ekle")
        self.btn_add.clicked.connect(self.on_add_record_clicked)
        btn_layout.addWidget(self.btn_add)
        
        self.btn_update = QPushButton("Sonucu Kaydet")
        self.btn_update.clicked.connect(lambda: self.on_update_record_clicked.emit(
            self.selected_kalibrasyon_id or ""
        ))
        btn_layout.addWidget(self.btn_update)
        
        layout.addLayout(btn_layout)
        
        return panel
    
    def _on_table_clicked(self, index: QModelIndex):
        pass
    
    @property
    def selected_kalibrasyon_id(self) -> Optional[str]:
        return None
    
    def get_filter_values(self) -> Dict[str, str]:
        search, filters = self.filter_panel.get_filters()
        return {
            "search": search,
            "durum": filters.get("durum", "Tümü"),
            "tip": filters.get("tip", "Tümü"),
        }
    
    def set_kpi_values(self, toplam: int, gecen_yil: int, sonraki: str, gecmis: int, hassas: int):
        self.kpi_bar.update_value("toplam", toplam)
        self.kpi_bar.update_value("bu_yil", gecen_yil)
        self.kpi_bar.update_value("sonraki", sonraki)
        self.kpi_bar.update_value("overdue", gecmis)
        self.kpi_bar.update_value("hassas", hassas)
    
    def set_table_data(self, rows: List[Dict[str, Any]]):
        pass
    
    def show_detail(self, kalibrasyon: Dict[str, Any]):
        kalibid = kalibrasyon.get("Kalibid", "?")
        self.detail_label.setText(f"Kalibrasyon #{kalibid}")
        
        detail_text = f"""
        <b>Cihaz:</b> {kalibrasyon.get('Cihazid', '?')}<br>
        <b>Tip:</b> {kalibrasyon.get('KalibrasyonTipi', '?')}<br>
        <b>Tarih:</b> {kalibrasyon.get('KalibrasyonTarihi', '—')}<br>
        <b>Sonraki:</b> {kalibrasyon.get('SonraksıTarih', '—')}<br>
        <b>Sonuç:</b> {kalibrasyon.get('Durum', '?')}<br>
        <b>Açıklama:</b> {kalibrasyon.get('Aciklama', '—')}
        """
        
        for i in reversed(range(self.detail_layout.count())):
            self.detail_layout.itemAt(i).widget().setParent(None)
        
        detail_lbl = QLabel(detail_text)
        detail_lbl.setWordWrap(True)
        self.detail_layout.addWidget(detail_lbl)
        self.detail_layout.addStretch()
        
        self.form_group.setVisible(kalibrasyon.get("Durum") != "Geçti")
    
    def get_form_data(self) -> Dict[str, Any]:
        return {
            "tarih": self.form_date.date().toString("yyyy-MM-dd"),
            "sonuc": self.form_sonuc.currentText(),
            "aciklama": self.form_aciklama.toPlainText(),
        }
    
    def clear_form(self):
        self.form_date.setDate(QDate.currentDate())
        self.form_sonuc.setCurrentIndex(0)
        self.form_aciklama.clear()
