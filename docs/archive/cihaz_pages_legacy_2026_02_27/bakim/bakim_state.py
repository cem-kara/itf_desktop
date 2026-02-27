# -*- coding: utf-8 -*-
"""
Bakım Sayfası - State Layer
===========================
Bakım listesi sayfasının durumunu manage eden dataclass'lar.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime


@dataclass
class BakimState:
    """Bakım listesi ve planlama sayfasının durumu"""
    
    # Veriler
    all_bakim: List[Dict[str, Any]] = field(default_factory=list)
    filtered_bakim: List[Dict[str, Any]] = field(default_factory=list)
    
    # Seçim
    selected_bakim_id: Optional[str] = None
    selected_bakim: Optional[Dict[str, Any]] = None
    
    # Filtreler
    filter_durum: str = "Tümü"
    filter_tip: str = "Tümü"
    filter_search: str = ""
    
    # KPI Metrikleri (hesaplanmış)
    kpi_toplam: int = 0
    kpi_planlanmis: int = 0
    kpi_yapildi: int = 0
    kpi_gecikmiş: int = 0
    kpi_son_bakim: str = "—"  # Son bakım tarihi
    
    # UI State
    active_form_mode: Optional[str] = None  # "plan_create", "exec_info"
    tab_index: int = 0
    is_loading: bool = False
    error_message: Optional[str] = None
    
    # Form alanları
    form_planid: Optional[str] = None
    form_cihazid: Optional[str] = None
    form_bakim_tarihi: Optional[str] = None
    form_bakim_tipi: str = ""
    form_teknisyen: str = ""
    form_aciklama: str = ""
    
    def apply_filters(self) -> List[Dict[str, Any]]:
        """Tüm verilere filtreleri uygula"""
        result = self.all_bakim
        
        # Durum filtresi
        if self.filter_durum != "Tümü":
            result = [r for r in result if r.get("Durum") == self.filter_durum]
        
        # Tip filtresi
        if self.filter_tip != "Tümü":
            result = [r for r in result if r.get("BakimTipi") == self.filter_tip]
        
        # Metin arama
        if self.filter_search:
            search_lower = self.filter_search.lower()
            result = [
                r for r in result
                if search_lower in str(r.get("Cihazid", "")).lower()
                or search_lower in str(r.get("BakimTipi", "")).lower()
            ]
        
        return result
    
    def calculate_kpis(self):
        """KPI metriklerini hesapla"""
        self.kpi_toplam = len(self.all_bakim)
        self.kpi_planlanmis = len([r for r in self.all_bakim if r.get("Durum") == "Planlandı"])
        self.kpi_yapildi = len([r for r in self.all_bakim if r.get("Durum") == "Yapıldı"])
        self.kpi_gecikmiş = len([
            r for r in self.all_bakim
            if r.get("Durum") == "Gecikmiş" or (
                r.get("Durum") == "Planlandı" 
                and r.get("PlanlananTarih", "") < datetime.now().isoformat()
            )
        ])
        
        # Son bakım tarihi
        yapildi_list = [r for r in self.all_bakim if r.get("Durum") == "Yapıldı"]
        if yapildi_list:
            son = max(yapildi_list, key=lambda r: r.get("BakimTarihi", ""))
            self.kpi_son_bakim = son.get("BakimTarihi", "—")
        else:
            self.kpi_son_bakim = "—"
    
    def select_bakim(self, bakim_id: Optional[str]):
        """Bakım kaydı seç"""
        self.selected_bakim_id = bakim_id
        if bakim_id:
            self.selected_bakim = next(
                (r for r in self.all_bakim if r.get("Planid") == bakim_id),
                None
            )
        else:
            self.selected_bakim = None
    
    def clear_form(self):
        """Form alanlarını temizle"""
        self.form_planid = None
        self.form_cihazid = None
        self.form_bakim_tarihi = None
        self.form_bakim_tipi = ""
        self.form_teknisyen = ""
        self.form_aciklama = ""
