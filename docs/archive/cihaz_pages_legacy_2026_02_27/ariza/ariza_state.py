# -*- coding: utf-8 -*-
"""
Arıza Sayfası - State Layer
=============================
Sayfa durumunu manage eden dataclass'lar ve state yönetimi.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime


@dataclass
class ArizaState:
    """Arıza listesi sayfasının durumu"""
    
    # Veriler
    all_arizalar: List[Dict[str, Any]] = field(default_factory=list)
    filtered_arizalar: List[Dict[str, Any]] = field(default_factory=list)
    
    # Seçim
    selected_ariza_id: Optional[str] = None
    selected_ariza: Optional[Dict[str, Any]] = None
    
    # Filtreler
    filter_durum: str = "Tümü"
    filter_oncelik: str = "Tümü"
    filter_cihaz_id: Optional[str] = None
    filter_search: str = ""
    
    # KPI Metrikleri (hesaplanmış)
    kpi_toplam: int = 0
    kpi_acik: int = 0
    kpi_kritik: int = 0
    kpi_ort_sure: float = 0.0  # gün
    kpi_kapali_ay: int = 0
    kpi_yinelenen: int = 0
    
    # UI State
    active_form: Optional[str] = None  # "ekle", "duzen", "detay", vb.
    tab_index: int = 0
    is_loading: bool = False
    error_message: Optional[str] = None
    
    def apply_filters(self) -> List[Dict[str, Any]]:
        """Tüm verilere filtreleri uygula"""
        result = self.all_arizalar
        
        # Durum filtresi
        if self.filter_durum != "Tümü":
            result = [r for r in result if r.get("Durum") == self.filter_durum]
        
        # Öncelik filtresi
        if self.filter_oncelik != "Tümü":
            result = [r for r in result if r.get("Oncelik") == self.filter_oncelik]
        
        # Cihaz filtresi
        if self.filter_cihaz_id:
            result = [r for r in result if r.get("Cihazid") == self.filter_cihaz_id]
        
        # Metin arama
        if self.filter_search:
            search_lower = self.filter_search.lower()
            result = [
                r for r in result
                if search_lower in str(r.get("Baslik", "")).lower()
                or search_lower in str(r.get("Arizaid", "")).lower()
            ]
        
        return result
    
    def calculate_kpis(self):
        """KPI metriklerini hesapla"""
        self.kpi_toplam = len(self.all_arizalar)
        
        # Açık ve kritik sayısı
        self.kpi_acik = len([r for r in self.all_arizalar if r.get("Durum") in ("Açık", "Acik")])
        self.kpi_kritik = len([r for r in self.all_arizalar if r.get("Oncelik") == "Kritik"])
        
        # Bu ay kapandı
        from datetime import datetime, timedelta
        this_month = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        self.kpi_kapali_ay = len([
            r for r in self.all_arizalar
            if r.get("Durum") in ("Kapalı", "Kapali")
            and r.get("KapalisTarihi")
            and datetime.fromisoformat(str(r.get("KapalisTarihi", ""))) >= this_month
        ])
        
        # Ortalama çözüm süresi (basit hesap)
        kapali_arizalar = [
            r for r in self.all_arizalar
            if r.get("Durum") in ("Kapalı", "Kapali")
        ]
        if kapali_arizalar:
            total_days = 0
            for ariza in kapali_arizalar:
                try:
                    baslangic = datetime.fromisoformat(str(ariza.get("BaslangicTarihi", "")))
                    kapalis = datetime.fromisoformat(str(ariza.get("KapalisTarihi", "")))
                    total_days += (kapalis - baslangic).days
                except (ValueError, TypeError):
                    pass
            self.kpi_ort_sure = total_days / len(kapali_arizalar) if kapali_arizalar else 0
        else:
            self.kpi_ort_sure = 0.0
        
        # Yinelenen (aynı cihazdan 3+ arıza)
        cihaz_counts = {}
        for r in self.all_arizalar:
            cihaz_id = r.get("Cihazid")
            cihaz_counts[cihaz_id] = cihaz_counts.get(cihaz_id, 0) + 1
        self.kpi_yinelenen = sum(1 for count in cihaz_counts.values() if count >= 3)
    
    def select_ariza(self, ariza_id: Optional[str]):
        """Arıza seç"""
        self.selected_ariza_id = ariza_id
        if ariza_id:
            self.selected_ariza = next(
                (r for r in self.all_arizalar if r.get("Arizaid") == ariza_id),
                None
            )
        else:
            self.selected_ariza = None
