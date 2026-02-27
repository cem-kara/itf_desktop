# -*- coding: utf-8 -*-
"""Cihaz Listesi - Service Layer (Business Logic)"""

from typing import Tuple
from core.logger import logger
from database.repository_registry import RepositoryRegistry
from .listesi_state import CihazListesiState


class CihazListesiService:
    """Cihaz listesi iş mantığı"""
    
    def __init__(self, db=None):
        self.db = db
        self.state = CihazListesiState()
    
    def load_initial_data(self) -> CihazListesiState:
        """İlk veri yükleme (lazy-loading ile sayfalama)"""
        if not self.db:
            logger.warning("CihazListesiService: DB yok")
            return self.state
        
        try:
            self.state.current_page = 1
            self.state.total_count = 0
            self.state.all_data = []
            
            registry = RepositoryRegistry(self.db)
            cihaz_repo = registry.get("Cihazlar")
            
            page_data, total = cihaz_repo.get_paginated(
                page=self.state.current_page,
                page_size=self.state.page_size
            )
            
            self.state.all_data = page_data
            self.state.total_count = total
            self.state.filtered_data = page_data.copy()
            
            # Combo'lar için veri yükle
            self._populate_filters(registry)
            
            self.state.total_display = len(self.state.filtered_data)
            
        except Exception as e:
            logger.error(f"CihazListesiService.load_initial_data: {e}")
        
        return self.state
    
    def load_more_data(self) -> bool:
        """Daha fazla veri yükle (sayfalama)"""
        if self.state.is_loading or not self.db:
            return False
        
        try:
            self.state.is_loading = True
            
            registry = RepositoryRegistry(self.db)
            cihaz_repo = registry.get("Cihazlar")
            
            self.state.current_page += 1
            page_data, _ = cihaz_repo.get_paginated(
                page=self.state.current_page,
                page_size=self.state.page_size
            )
            
            if not page_data:
                self.state.current_page -= 1
                return False
            
            self.state.all_data.extend(page_data)
            self.apply_filters()  # Filtreleri yeniden uygula
            
            return True
            
        except Exception as e:
            logger.error(f"CihazListesiService.load_more_data: {e}")
            self.state.current_page -= 1
            return False
        finally:
            self.state.is_loading = False
    
    def apply_filters(self) -> list:
        """Filtreleri uygula ve filtered_data güncelle"""
        filtered = self.state.all_data.copy()
        
        # Durum filtresi
        if self.state.active_filter != "Tümü":
            filtered = [r for r in filtered
                       if str(r.get("Durum", "")).strip() == self.state.active_filter]
        
        # Birim filtresi
        if self.state.selected_unit != "Tümü":
            filtered = [r for r in filtered
                       if str(r.get("AnaBilimDali", "")).strip() == self.state.selected_unit]
        
        # Kaynak filtresi
        if self.state.selected_source != "Tümü":
            filtered = [r for r in filtered
                       if str(r.get("Kaynak", "")).strip() == self.state.selected_source]
        
        # Arama filtresi
        if self.state.search_text:
            search_lower = self.state.search_text.lower()
            filtered = [r for r in filtered
                       if (search_lower in str(r.get("Cihazid", "")).lower() or
                           search_lower in str(r.get("Marka", "")).lower() or
                           search_lower in str(r.get("Model", "")).lower() or
                           search_lower in str(r.get("SeriNo", "")).lower())]
        
        self.state.filtered_data = filtered
        self.state.total_display = len(self.state.filtered_data)
        
        return self.state.filtered_data
    
    def set_status_filter(self, status: str):
        """Durum filtresini değiştir"""
        self.state.active_filter = status
        self.apply_filters()
    
    def set_unit_filter(self, unit: str):
        """Birim filtresini değiştir"""
        self.state.selected_unit = unit
        self.apply_filters()
    
    def set_source_filter(self, source: str):
        """Kaynak filtresini değiştir"""
        self.state.selected_source = source
        self.apply_filters()
    
    def set_search_text(self, text: str):
        """Arama metnini değiştir"""
        self.state.search_text = text
        self.apply_filters()
    
    def _populate_filters(self, registry):
        """Combo'lar için filtre verilerini yükle"""
        sabitler = []
        try:
            sabitler = registry.get("Sabitler").get_all()
        except Exception as e:
            logger.debug(f"Sabitler okunamadi: {e}")
        
        # Birimler
        abd_list = sorted({
            str(r.get("MenuEleman", "")).strip()
            for r in sabitler
            if r.get("Kod") == "AnaBilimDali" and str(r.get("MenuEleman", "")).strip()
        })
        if not abd_list:
            abd_list = sorted({
                str(r.get("AnaBilimDali", "")).strip()
                for r in self.state.all_data
                if str(r.get("AnaBilimDali", "")).strip()
            })
        self.state.units = ["Tümü"] + abd_list
        
        # Kaynaklar
        kaynak_list = sorted({
            str(r.get("MenuEleman", "")).strip()
            for r in sabitler
            if r.get("Kod") == "Kaynak" and str(r.get("MenuEleman", "")).strip()
        })
        if not kaynak_list:
            kaynak_list = sorted({
                str(r.get("Kaynak", "")).strip()
                for r in self.state.all_data
                if str(r.get("Kaynak", "")).strip()
            })
        self.state.sources = ["Tümü"] + kaynak_list
        
        # Durumlar
        self.state.statuses = ["Aktif", "Bakımda", "Arızalı", "Tümü"]
