# -*- coding: utf-8 -*-
"""
Kalibrasyon Sayfası - Presenter Layer
======================================
View ve Service arasında köprü.
"""
from typing import Optional, Dict, Any, List
from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex

from .kalibrasyon_view import KalibrasyonView
from .kalibrasyon_state import KalibrasyonState
from ui.pages.cihaz.components import RecordTableModel, KalibrasyonTableDelegate
from core.logger import logger


class KalibrasyonTableModel(RecordTableModel):
    """Kalibrasyon tablosu modeli"""
    
    COLUMNS = [
        ("Kalibid", "Kalib No", 90),
        ("Cihazid", "Cihaz", 110),
        ("KalibrasyonTarihi", "Tarih", 100),
        ("KalibrasyonTipi", "Tip", 100),
        ("SonraksıTarih", "Sonraki", 100),
        ("Durum", "Durum", 90),
    ]
    
    COLOR_MAPPING = {
        "Durum": {
            "Geçti": "#3ecf8e",      # Yeşil
            "İnceleme": "#f5a623",    # Amber
            "Başarısız": "#f75f5f",   # Kırmızı
        }
    }
    
    def __init__(self, parent=None):
        super().__init__(parent)


class KalibrasyonPresenter:
    """Kalibrasyon sayfası presenter"""
    
    def __init__(self, view: KalibrasyonView, state: KalibrasyonState, parent=None):
        self._view = view
        self._state = state
        self._table_model = KalibrasyonTableModel()
        self._table_delegate = KalibrasyonTableDelegate()
        
        self._setup_model_binding()
        self._connect_signals()
    
    def _setup_model_binding(self):
        """Model'i view'a bağla"""
        self._view.table.setModel(self._table_model)
        self._view.table.setItemDelegate(self._table_delegate)
        
        for i, (_, _, width) in enumerate(KalibrasyonTableModel.COLUMNS):
            self._view.table.horizontalHeader().resizeSection(i, width)
    
    def _connect_signals(self):
        """View sinyallerini bağla"""
        self._view.on_kalibrasyon_selected.connect(self._on_kalibrasyon_selected)
        self._view.on_add_record_clicked.connect(self._on_add_record_clicked)
        self._view.on_update_record_clicked.connect(self._on_update_record_clicked)
        self._view.on_filter_changed.connect(self._on_filter_changed)
        self._view.on_tab_changed.connect(self._on_tab_changed)
        self._view.table.clicked.connect(self._on_table_row_clicked)
    
    def _on_table_row_clicked(self, index: QModelIndex):
        kalibid = self._table_model.get_column_value(index.row(), "Kalibid")
        if kalibid:
            self._state.select_kalibrasyon(kalibid)
            self._view.show_detail(self._state.selected_kalibrasyon or {})
    
    def _on_kalibrasyon_selected(self, kalibid: str):
        self._state.select_kalibrasyon(kalibid)
        if self._state.selected_kalibrasyon:
            self._view.show_detail(self._state.selected_kalibrasyon)
    
    def _on_add_record_clicked(self):
        logger.info("Yeni kalibrasyon kaydı ekle (TODO)")
    
    def _on_update_record_clicked(self, kalibid: str):
        logger.info(f"Kalibrasyon {kalibid} sonucu kaydet (TODO)")
    
    def _on_filter_changed(self):
        filters = self._view.get_filter_values()
        self._state.filter_durum = filters["durum"]
        self._state.filter_tip = filters["tip"]
        self._state.filter_search = filters["search"]
        
        self._state.filtered_kalibrasyon = self._state.apply_filters()
        self._table_model.set_rows(self._state.filtered_kalibrasyon)
    
    def _on_tab_changed(self, idx: int):
        self._state.tab_index = idx
    
    def load_data(self, all_kalibrasyon: List[Dict[str, Any]]):
        """Verileri yükle"""
        self._state.all_kalibrasyon = all_kalibrasyon
        self._state.calculate_kpis()
        
        self._view.set_kpi_values(
            self._state.kpi_toplam,
            self._state.kpi_gecen_yil,
            self._state.kpi_sonraki_tarih,
            self._state.kpi_gecmis_tarih,
            self._state.kpi_hassas,
        )
        
        self._state.filtered_kalibrasyon = self._state.apply_filters()
        self._table_model.set_rows(self._state.filtered_kalibrasyon)
    
    def refresh_data(self, all_kalibrasyon: List[Dict[str, Any]]):
        """Verileri yenile"""
        self.load_data(all_kalibrasyon)
    
    def get_selected_kalibrasyon_id(self) -> Optional[str]:
        return self._state.selected_kalibrasyon_id
