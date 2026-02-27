# -*- coding: utf-8 -*-
"""
Bakım Sayfası - Presenter Layer
================================
View ve Service arasında köprü.
Event handling, model binding, state sync.
"""
from typing import Optional, Dict, Any, List
from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex
from PySide6.QtGui import QColor

from .bakim_view import BakimView
from .bakim_state import BakimState
from ui.pages.cihaz.components import RecordTableModel, BakimTableDelegate
from core.logger import logger


class BakimTableModel(RecordTableModel):
    """Bakım kaydı tablosu modeli"""
    
    COLUMNS = [
        ("Planid", "Plan No", 90),
        ("Cihazid", "Cihaz", 110),
        ("PlanlananTarih", "Plan Tarihi", 100),
        ("BakimTarihi", "Bakım Tarihi", 100),
        ("BakimPeriyodu", "Periyot", 100),
        ("BakimTipi", "Tip", 100),
        ("Teknisyen", "Teknisyen", 120),
        ("Durum", "Durum", 90),
    ]
    
    COLOR_MAPPING = {
        "Durum": {
            "Planlandı": "#4f8ef7",  # Mavi
            "Yapıldı": "#3ecf8e",    # Yeşil
            "Gecikmiş": "#f75f5f",   # Kırmızı
        }
    }
    
    def __init__(self, parent=None):
        super().__init__(parent)


class BakimPresenter:
    """Bakım sayfası presenter"""
    
    def __init__(self, view: BakimView, state: BakimState, parent=None):
        self._view = view
        self._state = state
        self._table_model = BakimTableModel()
        self._table_delegate = BakimTableDelegate()
        
        self._setup_model_binding()
        self._connect_signals()
    
    def _setup_model_binding(self):
        """Model'i view'a bağla"""
        self._view.table.setModel(self._table_model)
        self._view.table.setItemDelegate(self._table_delegate)
        
        # Kolon genişlikleri
        for i, (_, _, width) in enumerate(BakimTableModel.COLUMNS):
            self._view.table.horizontalHeader().resizeSection(i, width)
    
    def _connect_signals(self):
        """View sinyallerini presenter metodlarına bağla"""
        self._view.on_bakim_selected.connect(self._on_bakim_selected)
        self._view.on_add_plan_clicked.connect(self._on_add_plan_clicked)
        self._view.on_record_execution_clicked.connect(self._on_record_execution_clicked)
        self._view.on_filter_changed.connect(self._on_filter_changed)
        self._view.on_tab_changed.connect(self._on_tab_changed)
        
        # Tablo tıklama
        self._view.table.clicked.connect(self._on_table_row_clicked)
    
    # ──────────────────────────────────────────────────────
    # View → Presenter (Event Handlers)
    # ──────────────────────────────────────────────────────
    
    def _on_table_row_clicked(self, index: QModelIndex):
        """Tablo satırı seçildi"""
        bakim_id = self._table_model.get_column_value(index.row(), "Planid")
        if bakim_id:
            self._state.select_bakim(bakim_id)
            self._view.show_detail(self._state.selected_bakim or {})
    
    def _on_bakim_selected(self, bakim_id: str):
        """Bakım kaydı seçildi"""
        self._state.select_bakim(bakim_id)
        if self._state.selected_bakim:
            self._view.show_detail(self._state.selected_bakim)
    
    def _on_add_plan_clicked(self):
        """Yeni bakım planı ekleme dialog'u"""
        logger.info("Yeni bakım planı oluştur (TODO)")
    
    def _on_record_execution_clicked(self, bakim_id: str):
        """Bakım yaptıkları kaydet"""
        logger.info(f"Bakım {bakim_id} yaptıkları kaydet (TODO)")
    
    def _on_filter_changed(self):
        """Filtre değişti"""
        filters = self._view.get_filter_values()
        self._state.filter_durum = filters["durum"]
        self._state.filter_tip = filters["tip"]
        self._state.filter_search = filters["search"]
        
        # Filtreleri uygula ve tabloyu güncelle
        self._state.filtered_bakim = self._state.apply_filters()
        self._table_model.set_rows(self._state.filtered_bakim)
    
    def _on_tab_changed(self, idx: int):
        """Tab değişti"""
        self._state.tab_index = idx
    
    # ──────────────────────────────────────────────────────
    # Presenter → View (State Update)
    # ──────────────────────────────────────────────────────
    
    def load_data(self, all_bakim: List[Dict[str, Any]]):
        """Verileri state'e yükle ve view'u güncelle"""
        self._state.all_bakim = all_bakim
        self._state.calculate_kpis()
        
        # View'u güncelle
        self._view.set_kpi_values(
            self._state.kpi_toplam,
            self._state.kpi_planlanmis,
            self._state.kpi_yapildi,
            self._state.kpi_gecikmiş,
            self._state.kpi_son_bakim,
        )
        
        # Tabloyu güncelle
        self._state.filtered_bakim = self._state.apply_filters()
        self._table_model.set_rows(self._state.filtered_bakim)
    
    def refresh_data(self, all_bakim: List[Dict[str, Any]]):
        """Verileri yenile"""
        self.load_data(all_bakim)
    
    def get_selected_bakim_id(self) -> Optional[str]:
        """Seçili bakım kaydı ID'si"""
        return self._state.selected_bakim_id
