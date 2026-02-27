# -*- coding: utf-8 -*-
"""
Arıza Sayfası - Presenter Layer
================================
View ve Service arasında köprü.
Event handling, model binding, state sync.
"""
from typing import Optional, Dict, Any, List
from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex
from PySide6.QtGui import QColor

from .ariza_view import ArizaView
from .ariza_state import ArizaState
from core.logger import logger


class ArizaTableModel(QAbstractTableModel):
    """Arıza tablosu model'i"""
    
    COLUMNS = [
        ("Arizaid", "Arıza No", 90),
        ("Cihazid", "Cihaz", 110),
        ("BaslangicTarihi", "Tarih", 100),
        ("ArizaTipi", "Tip", 120),
        ("Oncelik", "Öncelik", 90),
        ("Baslik", "Başlık", 220),
        ("Durum", "Durum", 110),
    ]
    
    COLOR_DURUM = {
        "Açık": "#f75f5f", "Acik": "#f75f5f",
        "Devam Ediyor": "#f5a623",
        "Kapalı": "#3ecf8e", "Kapali": "#3ecf8e",
    }
    
    COLOR_ONCELIK = {
        "Kritik": "#f75f5f",
        "Yüksek": "#f5a623",
        "Orta": "#4f8ef7",
        "Düşük": "#5a6278",
    }
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._rows = []
        self._headers = [c[1] for c in self.COLUMNS]
        self._keys = [c[0] for c in self.COLUMNS]
    
    def rowCount(self, parent=QModelIndex()) -> int:
        return len(self._rows)
    
    def columnCount(self, parent=QModelIndex()) -> int:
        return len(self.COLUMNS)
    
    def headerData(self, section: int, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self._headers[section]
        return None
    
    def data(self, index: QModelIndex, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        
        row = self._rows[index.row()]
        key = self._keys[index.column()]
        val = row.get(key, "")
        
        if role == Qt.DisplayRole:
            if key == "BaslangicTarihi":
                # Tarih format
                from core.date_utils import to_ui_date
                return to_ui_date(val, "")
            return str(val) if val else ""
        
        if role == Qt.TextAlignmentRole:
            if key in ("BaslangicTarihi", "Oncelik", "Durum"):
                return Qt.AlignCenter
            return Qt.AlignVCenter | Qt.AlignLeft
        
        if role == Qt.ForegroundRole:
            if key == "Durum":
                color = self.COLOR_DURUM.get(row.get("Durum", ""))
                return QColor(color) if color else None
            if key == "Oncelik":
                color = self.COLOR_ONCELIK.get(row.get("Oncelik", ""))
                return QColor(color) if color else None
        
        if role == Qt.BackgroundRole:
            if key == "Durum":
                durum = row.get("Durum", "")
                bg = "rgba(247, 95, 95, 0.15)" if durum in ("Açık", "Acik") else \
                     "rgba(245, 166, 35, 0.15)" if durum == "Devam Ediyor" else \
                     "rgba(62, 207, 142, 0.15)" if durum in ("Kapalı", "Kapali") else None
                return QColor(bg) if bg else None
        
        return None
    
    def set_rows(self, rows: List[Dict[str, Any]]):
        """Tablo verisi güncelle"""
        self.beginResetModel()
        self._rows = rows
        self.endResetModel()
    
    def get_ariza_id_at_row(self, row: int) -> Optional[str]:
        """Satırdan ariza ID'si al"""
        if 0 <= row < len(self._rows):
            return self._rows[row].get("Arizaid")
        return None


class ArizaPresenter:
    """Arıza sayfası presenter"""
    
    def __init__(self, view: ArizaView, state: ArizaState, parent=None):
        self._view = view
        self._state = state
        self._table_model = ArizaTableModel()
        
        self._setup_model_binding()
        self._connect_signals()
    
    def _setup_model_binding(self):
        """Model'i view'a bağla"""
        self._view.table.setModel(self._table_model)
        
        # Kolon genişlikleri
        for i, (_, _, width) in enumerate(ArizaTableModel.COLUMNS):
            self._view.table.horizontalHeader().resizeSection(i, width)
    
    def _connect_signals(self):
        """View sinyallerini presenter metodlarına bağla"""
        self._view.on_ariza_selected.connect(self._on_ariza_selected)
        self._view.on_add_clicked.connect(self._on_add_clicked)
        self._view.on_edit_clicked.connect(self._on_edit_clicked)
        self._view.on_delete_clicked.connect(self._on_delete_clicked)
        self._view.on_filter_changed.connect(self._on_filter_changed)
        self._view.on_tab_changed.connect(self._on_tab_changed)
        
        # Tablo tıklama
        self._view.table.clicked.connect(self._on_table_row_clicked)
    
    # ──────────────────────────────────────────────────────
    # View → Presenter (Event Handlers)
    # ──────────────────────────────────────────────────────
    
    def _on_table_row_clicked(self, index: QModelIndex):
        """Tabulda satır seçildi"""
        ariza_id = self._table_model.get_ariza_id_at_row(index.row())
        if ariza_id:
            self._state.select_ariza(ariza_id)
            self._view.show_detail(self._state.selected_ariza or {})
    
    def _on_ariza_selected(self, ariza_id: str):
        """Arıza seçildi"""
        self._state.select_ariza(ariza_id)
        if self._state.selected_ariza:
            self._view.show_detail(self._state.selected_ariza)
    
    def _on_add_clicked(self):
        """Yeni arıza ekleme"""
        logger.info("Arıza ekleme dialog'u aç (TODO)")
    
    def _on_edit_clicked(self, ariza_id: str):
        """Arıza düzenleme"""
        logger.info(f"Arıza {ariza_id} düzenle (TODO)")
    
    def _on_delete_clicked(self, ariza_id: str):
        """Arıza silme"""
        logger.info(f"Arıza {ariza_id} sil (TODO)")
    
    def _on_filter_changed(self):
        """Filtre değişti"""
        filters = self._view.get_filter_values()
        self._state.filter_durum = filters["durum"]
        self._state.filter_oncelik = filters["oncelik"]
        self._state.filter_search = filters["search"]
        
        # Filtreleri uygula ve tabloyu güncelle
        self._state.filtered_arizalar = self._state.apply_filters()
        self._table_model.set_rows(self._state.filtered_arizalar)
    
    def _on_tab_changed(self, idx: int):
        """Tab değişti"""
        self._state.tab_index = idx
        if idx == 1:  # Performans tabı
            logger.info("Cihaz performansı verisi yükle (TODO)")
    
    # ──────────────────────────────────────────────────────
    # Presenter → View (State Update)
    # ──────────────────────────────────────────────────────
    
    def load_data(self, all_arizalar: List[Dict[str, Any]]):
        """Verileri state'e yükle ve view'u güncelle"""
        self._state.all_arizalar = all_arizalar
        self._state.calculate_kpis()
        
        # View'u güncelle
        self._view.set_kpi_values(
            self._state.kpi_toplam,
            self._state.kpi_acik,
            self._state.kpi_kritik,
            self._state.kpi_ort_sure,
            self._state.kpi_kapali_ay,
            self._state.kpi_yinelenen,
        )
        
        # Tabloyu güncelle (filtered = all, ilk load'da filtre yok)
        self._state.filtered_arizalar = self._state.apply_filters()
        self._table_model.set_rows(self._state.filtered_arizalar)
    
    def refresh_data(self, all_arizalar: List[Dict[str, Any]]):
        """Verileri yenile"""
        self.load_data(all_arizalar)
    
    def get_selected_ariza_id(self) -> Optional[str]:
        """Seçili arıza ID'si"""
        return self._state.selected_ariza_id
