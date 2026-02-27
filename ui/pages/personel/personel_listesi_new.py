# -*- coding: utf-8 -*-
"""
Personel Listesi — Refactored View
===================================
Temiz MVP pattern: View katmanı sadece UI'dan sorumlu.
Model, Filtre, Avatar Service modüllere taşınmıştır.
"""
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QTableView, QPushButton, QProgressBar, QMessageBox, QHeaderView
)
from PySide6.QtGui import QFont

from core.logger import logger
from database.repository_registry import RepositoryRegistry
from ui.styles import DarkTheme
from ui.styles.components import STYLES

from .models.personel_list_model import PersonelTableModel, COLUMNS, COL_IDX
from .services.personel_avatar_service import (
    PersonelAvatarService, LazyLoadingManager, AvatarDownloaderWorker
)
from .components.personel_filter_panel import PersonelFilterPanel

C = DarkTheme


# ─────────────────────────────────────────────────────────────────────────────
# Personel Listesi Sayfası
# ─────────────────────────────────────────────────────────────────────────────

class PersonelListesiPage(QWidget):
    """
    Personel listesi sayfası (refactored).
    
    Signals:
        detay_requested(dict): Detay görüntüleme istendi
        izin_requested(dict): İzin yönetimi istendi
        yeni_requested(): Yeni personel istendi
    
    Architecture:
        - View: Bu sınıf (UI layout + event handling)
        - Model: PersonelTableModel (data + role'lar)
        - Service: PersonelAvatarService (avatar + cache)
        - Filter: PersonelFilterPanel (arama + combo'lar)
    """

    detay_requested = Signal(dict)
    izin_requested = Signal(dict)
    yeni_requested = Signal()

    def __init__(self, db=None, action_guard=None, parent=None):
        super().__init__(parent)
        self.setStyleSheet(STYLES["page"])
        
        # Bağımlılıklar
        self._db = db
        self._action_guard = action_guard
        
        # Model ve Service'ler
        self._model = PersonelTableModel()
        self._avatar_service = PersonelAvatarService()
        self._lazy_loader = LazyLoadingManager(page_size=100)
        self._avatar_workers = []
        
        # Filtre state
        self._visible_rows = []
        
        # UI
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        """UI bileşenleri oluştur."""
        main = QVBoxLayout(self)
        main.setContentsMargins(0, 0, 0, 0)
        main.setSpacing(0)

        # ── Toolbar ─────────────────────────────────────────────────────────
        toolbar = QFrame()
        toolbar.setFixedHeight(48)
        toolbar.setStyleSheet(f"background-color: {C.BG_SECONDARY}; border-bottom: 1px solid {C.BORDER_PRIMARY};")
        toolbar_lay = QHBoxLayout(toolbar)
        toolbar_lay.setContentsMargins(16, 0, 16, 0)
        toolbar_lay.setSpacing(8)

        title = QLabel("Personel Listesi")
        title.setStyleSheet(f"font-size: 13px; font-weight: 600; color: {C.TEXT_PRIMARY};")
        toolbar_lay.addWidget(title)
        toolbar_lay.addStretch()

        self.btn_yenile = QPushButton("🔄 Yenile")
        self.btn_yenile.setFixedHeight(36)
        self.btn_yenile.setStyleSheet(f"""
            QPushButton {{
                background-color: {C.ACCENT_PRIMARY};
                color: white;
                border: none;
                border-radius: 4px;
                font-weight: 600;
                padding: 0 12px;
            }}
        """)
        toolbar_lay.addWidget(self.btn_yenile)

        self.btn_yeni = QPushButton("➕ Yeni Personel")
        self.btn_yeni.setFixedHeight(36)
        self.btn_yeni.setStyleSheet(f"""
            QPushButton {{
                background-color: #27ae60;
                color: white;
                border: none;
                border-radius: 4px;
                font-weight: 600;
                padding: 0 12px;
            }}
        """)
        toolbar_lay.addWidget(self.btn_yeni)

        main.addWidget(toolbar)

        # ── Filtre Paneli ───────────────────────────────────────────────────
        self.filter_panel = PersonelFilterPanel()
        main.addWidget(self.filter_panel)

        # ── Tablo ───────────────────────────────────────────────────────────
        self.table = QTableView()
        self.table.setModel(self._model)
        self.table.setSelectionBehavior(QTableView.SelectRows)
        self.table.setSelectionMode(QTableView.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.setColumnCount(len(COLUMNS))
        
        header = self.table.horizontalHeader()
        header.setStretchLastSection(False)
        for i, (key, title, width) in enumerate(COLUMNS):
            self.table.setColumnWidth(i, width)
        
        self.table.setStyleSheet(f"""
            QTableView {{
                background-color: {C.BG_PRIMARY};
                alternate-background-color: {C.BG_TERTIARY};
                gridline-color: {C.BORDER_PRIMARY};
                color: {C.TEXT_PRIMARY};
            }}
        """)
        
        main.addWidget(self.table, 1)

        # ── Footer ──────────────────────────────────────────────────────────
        footer = QFrame()
        footer.setFixedHeight(50)
        footer.setStyleSheet(f"background-color: {C.BG_SECONDARY}; border-top: 1px solid {C.BORDER_PRIMARY};")
        footer_lay = QHBoxLayout(footer)
        footer_lay.setContentsMargins(16, 0, 16, 0)

        info = QLabel("")
        info.setStyleSheet(f"color: {C.TEXT_SECONDARY}; font-size: 11px;")
        footer_lay.addWidget(info)
        self._footer_info = info

        footer_lay.addStretch()

        self.progress = QProgressBar()
        self.progress.setFixedWidth(200)
        self.progress.setMaximum(0)
        self.progress.setVisible(False)
        footer_lay.addWidget(self.progress)

        self.btn_load_more = QPushButton("Daha Fazla Yükle")
        self.btn_load_more.setFixedHeight(36)
        self.btn_load_more.setVisible(False)
        footer_lay.addWidget(self.btn_load_more)

        main.addWidget(footer)

    def _connect_signals(self):
        """Sinyal bağlantıları."""
        self.btn_yenile.clicked.connect(self.load_data)
        self.btn_yeni.clicked.connect(self.yeni_requested.emit)
        self.btn_load_more.clicked.connect(self._load_more_data)
        self.table.doubleClicked.connect(self._on_double_click)
        self.filter_panel.filter_changed.connect(self._on_filter_changed)

    # ────────────────────────────────────────────────────────────────────────
    # Data Loading
    # ────────────────────────────────────────────────────────────────────────

    def load_data(self):
        """İlk sayfayı yükle."""
        if not self._db:
            logger.warning("DB yok")
            return
        
        try:
            self._lazy_loader.reset()
            registry = RepositoryRegistry(self._db)
            personel_repo = registry.get("Personel")
            
            page_data, total_count = personel_repo.get_paginated_with_bakiye(
                page=1, page_size=self._lazy_loader.page_size
            )
            
            self._lazy_loader.load_page(page_data, total_count)
            self._model.set_data(self._lazy_loader.all_data)
            self._populate_combos(registry)
            self._start_avatar_downloads()
            self._apply_filters()
            self._update_footer()
            
        except Exception as e:
            logger.error(f"Veri yükleme hatası: {e}")
            QMessageBox.critical(self, "Hata", f"Personel yükleme başarısız: {e}")

    def _load_more_data(self):
        """Sonraki sayfayı yükle."""
        if not self._db or self._lazy_loader.is_loading:
            return
        
        try:
            self._lazy_loader.is_loading = True
            self.btn_load_more.setEnabled(False)
            self.progress.setVisible(True)
            
            registry = RepositoryRegistry(self._db)
            personel_repo = registry.get("Personel")
            
            page_data, _ = personel_repo.get_paginated_with_bakiye(
                page=self._lazy_loader.current_page + 1,
                page_size=self._lazy_loader.page_size
            )
            
            has_more = self._lazy_loader.load_page(page_data, self._lazy_loader.total_count)
            self._model.set_data(self._lazy_loader.all_data)
            self._start_avatar_downloads()
            self._apply_filters()
            self._update_footer()
            
            if not has_more:
                self.btn_load_more.setVisible(False)
                
        except Exception as e:
            logger.error(f"More load hatası: {e}")
        finally:
            self._lazy_loader.is_loading = False
            self.btn_load_more.setEnabled(True)
            self.progress.setVisible(False)

    def _populate_combos(self, registry):
        """Combo filtre değerlerini doldur."""
        try:
            personel_repo = registry.get("Personel")
            birims = personel_repo.get_distinct_values("Birim")
            unvans = personel_repo.get_distinct_values("Unvan")
            
            self.filter_panel.add_combo_filter("Birim", birims)
            self.filter_panel.add_combo_filter("Unvan", unvans)
        except Exception as e:
            logger.warning(f"Combo doldurma hatası: {e}")

    # ────────────────────────────────────────────────────────────────────────
    # Filtering & Search
    # ────────────────────────────────────────────────────────────────────────

    def _on_filter_changed(self, durum: str, combos: dict, search_text: str):
        """Filtre değişti."""
        self._apply_filters()

    def _apply_filters(self):
        """Tüm filtreleri uygula."""
        durum = self.filter_panel.get_active_filter()
        search_text = self.filter_panel.get_search_text()
        
        # Durum filtresi uygula
        visible = self._model.filter_by_durum(durum)
        
        # Arama uygula
        if search_text:
            search_visible = self._model.search(search_text)
            visible = [r for r in visible if r in search_visible]
        
        # Combo filtreleri uygula
        for key in ["Birim", "Unvan"]:
            combo_value = self.filter_panel.get_combo_filter(key)
            if combo_value != "Tüm":
                combo_visible = self._model.filter_by_combo(key, combo_value)
                visible = [r for r in visible if r in combo_visible]
        
        self._visible_rows = visible
        self._update_table_display()

    def _update_table_display(self):
        """Tablo görünümünü güncelle."""
        # Not: Tüm satırları gösteriyor (daha sofistike proxy model gerekebilir)
        self._update_footer()

    def _update_footer(self):
        """Footer bilgisini güncelle."""
        total = len(self._lazy_loader.all_data)
        visible = len(self._visible_rows)
        text = f"{visible} / {total} personel"
        if self._lazy_loader.has_more:
            text += f" ({self._lazy_loader.total_count} toplam)"
        self._footer_info.setText(text)
        self.btn_load_more.setVisible(self._lazy_loader.has_more)

    # ────────────────────────────────────────────────────────────────────────
    # Avatar Management
    # ────────────────────────────────────────────────────────────────────────

    def _start_avatar_downloads(self):
        """Avatar indirme işçilerini başlat."""
        for row_data in self._lazy_loader.all_data:
            tc = row_data.get("TCKN")
            url = row_data.get("PhotoURL")
            
            if not tc or not url:
                continue
            
            # Cache'te var mı kontrol et
            if self._avatar_service.get_avatar(tc):
                continue
            
            # Worker oluştur ve bağla
            worker = AvatarDownloaderWorker(url, tc, self)
            worker.avatar_ready.connect(self._on_avatar_ready)
            worker.start()
            self._avatar_workers.append(worker)

    def _on_avatar_ready(self, tc: str, pixmap):
        """Avatar indirildi."""
        self._avatar_service.cache_avatar(tc, pixmap)
        self._model.set_avatar(tc, pixmap)

    # ────────────────────────────────────────────────────────────────────────
    # Events
    # ────────────────────────────────────────────────────────────────────────

    def _on_double_click(self, index):
        """Tablo satırına çift tıklandı."""
        row = index.row()
        row_data = self._model.get_row_data(row)
        if row_data:
            self.detay_requested.emit(row_data)
