# -*- coding: utf-8 -*-
"""
Cihaz Modülü - Shared Components Paketi
=======================================
Bakım, Kalibrasyon, Arıza, vb. sayfaların kullandığı ortak bileşenler.

Classes:
    - RecordTableModel: QAbstractTableModel base (kayıt tabloları için)
    - RecordTableDelegate: QStyledItemDelegate base (renk kodlama)
    - BakimTableDelegate, KalibrasyonTableDelegate: Özel delegate'ler
    - KPICard, KPIBar: KPI metrik widgetleri
    - BakimKPIBar, KalibrasyonKPIBar: Özel KPI barlar
    - FilterPanel: Filtre paneli
    - BakimFilterPanel, KalibrasyonFilterPanel: Özel filtre panelleri

Usage:
    from ui.pages.cihaz.components import RecordTableModel, KPIBar, FilterPanel
    
    # Bakım tablosu
    model = RecordTableModel()
    model.COLUMNS = [("id", "ID", 50), ("ad", "Ad", 100), ...]
    model.COLOR_MAPPING = {"durum": {"Açık": "#f75f5f", ...}}
"""

from .record_tables import (
    RecordTableModel,
    RecordTableDelegate,
    BakimTableDelegate,
    KalibrasyonTableDelegate,
    THEME_COLORS,
    DURATION_COLORS_3_6_12,
)
from .kpi_bar_widget import (
    KPICard,
    KPIBar,
    BakimKPIBar,
    KalibrasyonKPIBar,
    get_duration_color_name,
)
from .filter_panel_widget import (
    FilterPanel,
    BakimFilterPanel,
    KalibrasyonFilterPanel,
    BAKIM_FILTER_CONFIG,
    KALIBRASYON_FILTER_CONFIG,
    ARIZA_FILTER_CONFIG,
)
from .bakim_widgets import (
    FormPanel,
    create_field_label,
    set_field_value,
)
from .kalibrasyon_components import (
    KalibrasyonGirisForm,
    KalSparkline,
    load_cihaz_marka_map,
    compute_marka_stats,
    build_single_cihaz_stats,
    build_marka_grid,
    build_no_kal_card,
    build_trend_chart,
    build_expiry_list,
)
from .cihaz_list_delegate import CihazDelegate

__all__ = [
    # Model
    'RecordTableModel',
    # Delegates
    'RecordTableDelegate',
    'BakimTableDelegate',
    'KalibrasyonTableDelegate',
    'THEME_COLORS',
    'DURATION_COLORS_3_6_12',
    # KPI Widgets
    'KPICard',
    'KPIBar',
    'BakimKPIBar',
    'KalibrasyonKPIBar',
    'get_duration_color_name',
    # Filter Panels
    'FilterPanel',
    'BakimFilterPanel',
    'KalibrasyonFilterPanel',
    'BAKIM_FILTER_CONFIG',
    'KALIBRASYON_FILTER_CONFIG',
    'ARIZA_FILTER_CONFIG',
    # Bakım Widgets
    'FormPanel',
    'create_field_label',
    'set_field_value',
    'KalibrasyonGirisForm',
    'KalSparkline',
    'load_cihaz_marka_map',
    'compute_marka_stats',
    'build_single_cihaz_stats',
    'build_marka_grid',
    'build_no_kal_card',
    'build_trend_chart',
    'build_expiry_list',
    # Cihaz Listesi Delegate
    'CihazDelegate',
]
