# -*- coding: utf-8 -*-
"""Cihaz Listesi - Presenter (UI Binding & State Management)"""

from PySide6.QtCore import Qt, QAbstractTableModel
from core.logger import logger
from ui.pages.cihaz.models.cihaz_list_model import CihazTableModel, COLUMNS
from .listesi_service import CihazListesiService
from .listesi_state import CihazListesiState


class CihazListesiPresenter:
    """Cihaz listesi presenter - service ve model arasındaki bağlantı"""
    
    def __init__(self, service: CihazListesiService = None, db=None):
        self.service = service or CihazListesiService(db)
        self.model = CihazTableModel()
        self._state: CihazListesiState = None
    
    def initialize(self) -> tuple:
        """Presenter'ı initialize et ve state + model döndür"""
        self._state = self.service.load_initial_data()
        self._update_model_from_state()
        return self._state, self.model
    
    def refresh_data(self):
        """Veriyi yenile"""
        self._state = self.service.load_initial_data()
        self._update_model_from_state()
    
    def load_more(self) -> bool:
        """Daha fazla veri yükle"""
        success = self.service.load_more_data()
        if success:
            self._update_model_from_state()
        return success
    
    def apply_status_filter(self, status: str):
        """Durum filtresini uygula"""
        self.service.set_status_filter(status)
        self._update_model_from_state()
    
    def apply_unit_filter(self, unit: str):
        """Birim filtresini uygula"""
        self.service.set_unit_filter(unit)
        self._update_model_from_state()
    
    def apply_source_filter(self, source: str):
        """Kaynak filtresini uygula"""
        self.service.set_source_filter(source)
        self._update_model_from_state()
    
    def apply_search(self, text: str):
        """Arama filtersini uygula"""
        self.service.set_search_text(text)
        self._update_model_from_state()
    
    def get_row_at(self, row: int) -> dict:
        """Belirli satırı dict olarak döndür"""
        return self.model.get_row(row)
    
    def get_state(self) -> CihazListesiState:
        """Geçerli state'i döndür"""
        return self._state
    
    def get_model(self) -> CihazTableModel:
        """Model'i döndür"""
        return self.model
    
    def get_combo_items(self) -> tuple:
        """Combo'lar için items döndür (units, sources)"""
        return (self._state.units, self._state.sources)
    
    def _update_model_from_state(self):
        """State'deki filtered_data'yı model'e aktar"""
        self.model.set_data(self._state.filtered_data)
