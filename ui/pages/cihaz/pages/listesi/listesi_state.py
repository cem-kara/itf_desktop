# -*- coding: utf-8 -*-
"""Cihaz Listesi - State Management"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class CihazListesiState:
    """Cihaz Listesi sayfası state (veri + UI durumu)"""
    
    # Veri
    all_data: list = field(default_factory=list)  # Tüm cihazlar
    filtered_data: list = field(default_factory=list)  # Filtre uygulanmış
    
    # Lazy loading
    current_page: int = 1
    page_size: int = 100
    total_count: int = 0
    is_loading: bool = False
    
    # Filtreleme
    active_filter: str = "Tümü"  # Durum filtresi
    selected_unit: str = "Tümü"  # Birim filtresi
    selected_source: str = "Tümü"  # Kaynak filtresi
    search_text: str = ""
    
    # Combo verileri
    units: list = field(default_factory=list)
    sources: list = field(default_factory=list)
    statuses: list = field(default_factory=list)
    
    # UI
    hover_row: int = -1
    total_display: int = 0
