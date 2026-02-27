# -*- coding: utf-8 -*-
"""
Kalibrasyon Sayfası - State Layer
==================================
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime


@dataclass
class KalibrasyonState:
    """Kalibrasyon kaydı sayfasının durumu"""
    
    all_kalibrasyon: List[Dict[str, Any]] = field(default_factory=list)
    filtered_kalibrasyon: List[Dict[str, Any]] = field(default_factory=list)
    
    selected_kalibrasyon_id: Optional[str] = None
    selected_kalibrasyon: Optional[Dict[str, Any]] = None
    
    filter_durum: str = "Tümü"
    filter_tip: str = "Tümü"
    filter_search: str = ""
    
    # KPI Metrikleri
    kpi_toplam: int = 0
    kpi_gecen_yil: int = 0
    kpi_sonraki_tarih: str = "—"
    kpi_gecmis_tarih: int = 0
    kpi_hassas: int = 0
    
    active_form_mode: Optional[str] = None
    tab_index: int = 0
    is_loading: bool = False
    error_message: Optional[str] = None
    
    form_kalibid: Optional[str] = None
    form_cihazid: Optional[str] = None
    form_tarih: Optional[str] = None
    form_tip: str = ""
    form_sonuc: str = ""
    form_aciklama: str = ""
    
    def apply_filters(self) -> List[Dict[str, Any]]:
        """Tüm verilere filtreleri uygula"""
        result = self.all_kalibrasyon
        
        if self.filter_durum != "Tümü":
            result = [r for r in result if r.get("Durum") == self.filter_durum]
        
        if self.filter_tip != "Tümü":
            result = [r for r in result if r.get("KalibrasyonTipi") == self.filter_tip]
        
        if self.filter_search:
            search_lower = self.filter_search.lower()
            result = [
                r for r in result
                if search_lower in str(r.get("Cihazid", "")).lower()
                or search_lower in str(r.get("KalibrasyonTipi", "")).lower()
            ]
        
        return result
    
    def calculate_kpis(self):
        """KPI metriklerini hesapla"""
        self.kpi_toplam = len(self.all_kalibrasyon)
        
        # Bu yıl geçen
        this_year = datetime.now().year
        self.kpi_gecen_yil = len([
            r for r in self.all_kalibrasyon
            if r.get("Durum") == "Geçti" and r.get("KalibrasyonTarihi", "")[:4] == str(this_year)
        ])
        
        # Geçmiş tarih (süresi geçmiş)
        today = datetime.now().date()
        self.kpi_gecmis_tarih = len([
            r for r in self.all_kalibrasyon
            if r.get("SonraksıTarih") and r.get("SonraksıTarih") < str(today)
        ])
        
        # Hassas aletler
        self.kpi_hassas = len([r for r in self.all_kalibrasyon if r.get("KalibrasyonTipi") == "Hassas"])
        
        # Sonraki tarih
        sonraki = [r for r in self.all_kalibrasyon if r.get("SonraksıTarih")]
        if sonraki:
            self.kpi_sonraki_tarih = min([r.get("SonraksıTarih", "") for r in sonraki])
        else:
            self.kpi_sonraki_tarih = "—"
    
    def select_kalibrasyon(self, kalibrasyon_id: Optional[str]):
        """Kalibrasyon kaydı seç"""
        self.selected_kalibrasyon_id = kalibrasyon_id
        if kalibrasyon_id:
            self.selected_kalibrasyon = next(
                (r for r in self.all_kalibrasyon if r.get("Kalibid") == kalibrasyon_id),
                None
            )
        else:
            self.selected_kalibrasyon = None
    
    def clear_form(self):
        """Form alanlarını temizle"""
        self.form_kalibid = None
        self.form_cihazid = None
        self.form_tarih = None
        self.form_tip = ""
        self.form_sonuc = ""
        self.form_aciklama = ""
