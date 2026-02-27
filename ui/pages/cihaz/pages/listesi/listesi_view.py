# -*- coding: utf-8 -*-
"""Cihaz Listesi - View (UI Layout & Signals)"""

from PySide6.QtCore import Qt, Signal, QTimer, QSize, QSortFilterProxyModel
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QProgressBar, QPushButton, QHeaderView, QTableView,
    QComboBox, QLineEdit
)
from PySide6.QtGui import QCursor

from core.logger import logger
from ui.pages.cihaz.components.cihaz_list_delegate import CihazDelegate
from ui.pages.cihaz.models.cihaz_list_model import COLUMNS, COL_IDX
from ui.styles import DarkTheme
from ui.styles.components import ComponentStyles, STYLES
from ui.styles.icons import IconRenderer
from .listesi_presenter import CihazListesiPresenter

C = DarkTheme


class CihazListesiView(QWidget):
    """Cihaz Listesi View - Layout ve signal'lar"""
    
    detay_requested = Signal(dict)
    edit_requested = Signal(dict)
    periodic_maintenance_requested = Signal(dict)
    add_requested = Signal()
    refresh_requested = Signal()
    
    def __init__(self, presenter: CihazListesiPresenter = None, action_guard=None, parent=None):
        super().__init__(parent)
        self.setStyleSheet(STYLES["page"])
        self.presenter = presenter
        self._action_guard = action_guard
        self._hover_row = -1
        
        # Arama debounce
        self._search_timer = QTimer()
        self._search_timer.setInterval(300)
        self._search_timer.setSingleShot(True)
        self._search_timer.timeout.connect(self._execute_search)
        
        # UI bileşenleri
        self._filter_btns = {}
        
        self._setup_ui()
        self._connect_signals()
        self._initialize_presenter()
    
    def _setup_ui(self):
        main = QVBoxLayout(self)
        main.setContentsMargins(0, 0, 0, 0)
        main.setSpacing(0)
        main.addWidget(self._build_toolbar())
        main.addWidget(self._build_subtoolbar())
        main.addWidget(self._build_table(), 1)
        main.addWidget(self._build_footer())
    
    def _build_toolbar(self) -> QFrame:
        frame = QFrame()
        frame.setFixedHeight(48)
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: {C.BG_SECONDARY};
                border-bottom: 1px solid {C.BORDER_PRIMARY};
            }}
        """)
        lay = QHBoxLayout(frame)
        lay.setContentsMargins(16, 0, 16, 0)
        lay.setSpacing(8)
        
        title = QLabel("Cihaz Listesi")
        title.setStyleSheet(f"font-size:13px; font-weight:600; color:{C.TEXT_PRIMARY}; background:transparent;")
        lay.addWidget(title)
        
        lay.addWidget(self._sep())
        
        # Durum butonları
        for status in ("Aktif", "Bakımda", "Arızalı", "Tümü"):
            btn = QPushButton(status)
            btn.setCheckable(True)
            btn.setCursor(QCursor(Qt.PointingHandCursor))
            btn.setFixedHeight(28)
            btn.setMinimumWidth(90)
            
            bg = ComponentStyles.get_status_color(status)
            text_color = ComponentStyles.get_status_text_color(status)
            r, g, b, a = bg
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: rgba({r}, {g}, {b}, {a});
                    color: {text_color};
                    border: 1px solid rgba({r}, {g}, {b}, {min(a + 80, 255)});
                    border-radius: 4px;
                    padding: 4px 12px;
                    font-size: 11px;
                    font-weight: 500;
                }}
                QPushButton:checked {{
                    background: rgba({r}, {g}, {b}, {min(a + 60, 255)});
                    border: 1px solid {text_color};
                    font-weight: 600;
                }}
            """)
            
            if status == "Tümü":
                btn.setChecked(True)
            
            self._filter_btns[status] = btn
            lay.addWidget(btn)
        
        lay.addWidget(self._sep())
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Cihaz, marka, model, seri ara…")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.setFixedWidth(220)
        self.search_input.setStyleSheet(STYLES["search"])
        lay.addWidget(self.search_input)
        
        lay.addStretch()
        
        self.btn_yenile = QPushButton()
        self.btn_yenile.setToolTip("Yenile")
        self.btn_yenile.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_yenile.setFixedSize(32, 28)
        self.btn_yenile.setStyleSheet(STYLES["refresh_btn"])
        IconRenderer.set_button_icon(self.btn_yenile, "refresh", color=C.TEXT_SECONDARY, size=16)
        lay.addWidget(self.btn_yenile)
        
        self.btn_yeni = QPushButton(" Yeni Cihaz")
        self.btn_yeni.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_yeni.setStyleSheet(STYLES["action_btn"])
        IconRenderer.set_button_icon(self.btn_yeni, "plus", color=C.BTN_PRIMARY_TEXT, size=16)
        self.btn_yeni.setIconSize(QSize(16, 16))
        
        if self._action_guard:
            self._action_guard.disable_if_unauthorized(self.btn_yeni, "cihaz.write")
        
        lay.addWidget(self.btn_yeni)
        
        return frame
    
    def _build_subtoolbar(self) -> QFrame:
        frame = QFrame()
        frame.setFixedHeight(36)
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: {C.BG_PRIMARY};
                border-bottom: 1px solid {C.BORDER_PRIMARY};
            }}
        """)
        lay = QHBoxLayout(frame)
        lay.setContentsMargins(16, 0, 16, 0)
        lay.setSpacing(8)
        
        lbl = QLabel("FİLTRE:")
        lbl.setStyleSheet(f"font-size:11px; color:{C.TEXT_DISABLED}; background:transparent;")
        lay.addWidget(lbl)
        
        lbl_abd = QLabel("Birim:")
        lbl_abd.setStyleSheet(f"font-size:11px; color:{C.TEXT_DISABLED}; background:transparent;")
        lay.addWidget(lbl_abd)
        
        self.cmb_unit = QComboBox()
        self.cmb_unit.setFixedWidth(160)
        self.cmb_unit.setStyleSheet(STYLES["combo"])
        lay.addWidget(self.cmb_unit)
        
        lbl_kaynak = QLabel("Kaynak:")
        lbl_kaynak.setStyleSheet(f"font-size:11px; color:{C.TEXT_DISABLED}; background:transparent;")
        lay.addWidget(lbl_kaynak)
        
        self.cmb_source = QComboBox()
        self.cmb_source.setFixedWidth(160)
        self.cmb_source.setStyleSheet(STYLES["combo"])
        lay.addWidget(self.cmb_source)
        
        lay.addStretch()
        
        return frame
    
    def _build_table(self) -> QTableView:
        self._proxy = QSortFilterProxyModel()
        self._proxy.setSourceModel(self.presenter.get_model())
        self._proxy.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self._proxy.setFilterKeyColumn(-1)
        
        self.table = QTableView()
        self.table.setModel(self._proxy)
        self.table.setStyleSheet(STYLES["table"])
        self.table.setAlternatingRowColors(False)
        self.table.setSelectionBehavior(QTableView.SelectRows)
        self.table.setSelectionMode(QTableView.SingleSelection)
        self.table.setSortingEnabled(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setMouseTracking(True)
        self.table.verticalHeader().setDefaultSectionSize(46)
        
        self._delegate = CihazDelegate(self.table)
        self.table.setItemDelegate(self._delegate)
        
        hdr = self.table.horizontalHeader()
        for i, (_, _, w) in enumerate(COLUMNS):
            hdr.setSectionResizeMode(i, QHeaderView.Fixed)
            self.table.setColumnWidth(i, w)
        hdr.setSectionResizeMode(COL_IDX["_marka_model"], QHeaderView.Stretch)
        hdr.setSectionResizeMode(COL_IDX["Birim"], QHeaderView.Stretch)
        
        return self.table
    
    def _build_footer(self) -> QFrame:
        frame = QFrame()
        frame.setFixedHeight(40)
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: {C.BG_SECONDARY};
                border-top: 1px solid {C.BORDER_PRIMARY};
            }}
        """)
        lay = QHBoxLayout(frame)
        lay.setContentsMargins(16, 0, 16, 0)
        lay.setSpacing(16)
        
        self.lbl_info = QLabel("0 kayıt")
        self.lbl_info.setStyleSheet(STYLES["footer_label"])
        lay.addWidget(self.lbl_info)
        
        lay.addStretch()
        
        self.progress = QProgressBar()
        self.progress.setFixedSize(140, 4)
        self.progress.setVisible(False)
        self.progress.setTextVisible(False)
        self.progress.setStyleSheet(STYLES["progress"])
        lay.addWidget(self.progress)
        
        self.btn_load_more = QPushButton("Daha Fazla Yükle")
        self.btn_load_more.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_load_more.setFixedHeight(28)
        self.btn_load_more.setStyleSheet(STYLES["action_btn"])
        self.btn_load_more.setVisible(False)
        lay.addWidget(self.btn_load_more)
        
        return frame
    
    def _connect_signals(self):
        # Filter buttons
        for status, btn in self._filter_btns.items():
            btn.clicked.connect(lambda _, s=status: self._on_status_filter(s))
        
        # Search
        self.search_input.textChanged.connect(self._on_search_typed)
        
        # Combos
        self.cmb_unit.currentTextChanged.connect(lambda u: self.presenter.apply_unit_filter(u))
        self.cmb_source.currentTextChanged.connect(lambda s: self.presenter.apply_source_filter(s))
        
        # Buttons
        self.btn_yenile.clicked.connect(self.refresh_requested.emit)
        self.btn_yeni.clicked.connect(self.add_requested.emit)
        self.btn_load_more.clicked.connect(self._on_load_more)
        
        # Table
        self.table.doubleClicked.connect(self._on_row_double_click)
        self.table.mouseMoveEvent = self._on_table_mouse_move
        self.table.mousePressEvent = self._on_table_mouse_press
        self.table.leaveEvent = self._on_table_leave
    
    def _initialize_presenter(self):
        """Presenter initialize et ve UI'ya veri doldur"""
        if not self.presenter:
            return
        
        state, model = self.presenter.initialize()
        
        # Combos'ı doldur
        units, sources = self.presenter.get_combo_items()
        
        self.cmb_unit.blockSignals(True)
        self.cmb_unit.addItems(units)
        self.cmb_unit.blockSignals(False)
        
        self.cmb_source.blockSignals(True)
        self.cmb_source.addItems(sources)
        self.cmb_source.blockSignals(False)
        
        self._update_display_count()
    
    def _on_status_filter(self, status: str):
        """Durum filtresini uygula"""
        for s, btn in self._filter_btns.items():
            btn.setChecked(s == status)
        self.presenter.apply_status_filter(status)
        self._update_display_count()
    
    def _on_search_typed(self, text: str):
        """Arama metni yazıldı - debounce yap"""
        self._search_timer.stop()
        self._search_timer.start()
    
    def _execute_search(self):
        """Ara"""
        text = self.search_input.text()
        self.presenter.apply_search(text)
        self._update_display_count()
    
    def _on_load_more(self):
        """Daha fazla yükle"""
        self.progress.setVisible(True)
        self.btn_load_more.setEnabled(False)
        
        success = self.presenter.load_more()
        if success:
            self._update_display_count()
            state = self.presenter.get_state()
            loaded = len(state.all_data)
            self.btn_load_more.setText(f"Daha Fazla Yükle ({loaded}/{state.total_count})")
        else:
            # Daha veri yok
            self.btn_load_more.setVisible(False)
        
        self.progress.setVisible(False)
        self.btn_load_more.setEnabled(True)
    
    def _on_row_double_click(self, idx):
        """Satır double-click"""
        if idx.isValid():
            src = self._proxy.mapToSource(idx)
            row_data = self.presenter.get_row_at(src.row())
            if row_data:
                self.detay_requested.emit(row_data)
    
    def _on_table_mouse_move(self, event):
        """Table mouse move"""
        idx = self.table.indexAt(event.pos())
        row = idx.row() if idx.isValid() else -1
        self._hover_row = row
        self._delegate.set_hover_row(row)
        self.table.viewport().update()
        QTableView.mouseMoveEvent(self.table, event)
    
    def _on_table_mouse_press(self, event):
        """Table mouse press"""
        idx = self.table.indexAt(event.pos())
        if idx.isValid():
            src = self._proxy.mapToSource(idx)
            row_data = self.presenter.get_row_at(src.row())
            if row_data and COLUMNS[idx.column()][0] == "_actions":
                cell_rect = self.table.visualRect(idx)
                local_pos = event.pos() - cell_rect.topLeft()
                action = self._delegate.get_action_at(idx.row(), local_pos)
                if action == "detay":
                    self.detay_requested.emit(row_data)
                    event.accept()
                    return
                if action == "edit":
                    self.edit_requested.emit(row_data)
                    event.accept()
                    return
                if action == "bakim":
                    self.periodic_maintenance_requested.emit(row_data)
                    event.accept()
                    return
        QTableView.mousePressEvent(self.table, event)
    
    def _on_table_leave(self, event):
        """Table leave"""
        self._hover_row = -1
        self._delegate.set_hover_row(-1)
        self.table.viewport().update()
        QTableView.leaveEvent(self.table, event)
    
    def _update_display_count(self):
        """Ekranda gözüken kayıt sayısını güncelle"""
        state = self.presenter.get_state()
        self.lbl_info.setText(f"{state.total_display} kayıt")
        
        # Load more butonu
        loaded = len(state.all_data)
        has_more = loaded < state.total_count
        self.btn_load_more.setVisible(has_more)
        if has_more:
            self.btn_load_more.setText(f"Daha Fazla Yükle ({loaded}/{state.total_count})")
    
    @staticmethod
    def _sep():
        f = QFrame()
        f.setFixedSize(1, 22)
        f.setStyleSheet(f"background:{C.BORDER_PRIMARY};")
        return f
