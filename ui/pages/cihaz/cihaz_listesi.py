# -*- coding: utf-8 -*-
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QLineEdit, QComboBox, QFrame, QMessageBox, QMenu
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QCursor, QAction, QColor

from core.logger import logger
from ui.theme_manager import ThemeManager
from ui.styles import DarkTheme
from ui.styles.icons import IconRenderer
from ui.pages.cihaz.ariza_ekle import ArizaEklePanel

# Merkezi stil
S = ThemeManager.get_all_component_styles()

class CihazListesiPage(QWidget):
    # Sinyaller
    edit_requested = Signal(dict)  # Düzenleme için veri gönderir
    add_requested = Signal()       # Yeni ekleme isteği
    periodic_maintenance_requested = Signal(dict)

    def __init__(self, db=None, parent=None):
        super().__init__(parent)
        self.setStyleSheet(S["page"])
        self._db = db
        self._all_data = []
        
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        # Ana Layout (Yatay: Liste | Arıza Paneli)
        self.root_layout = QHBoxLayout(self)
        self.root_layout.setContentsMargins(0, 0, 0, 0)
        self.root_layout.setSpacing(0)

        # Liste Konteyneri (Sol Taraf)
        self.list_container = QWidget()
        layout = QVBoxLayout(self.list_container)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # ── FİLTRE PANELİ ──
        filter_frame = QFrame()
        filter_frame.setStyleSheet(S["filter_panel"])
        fl = QHBoxLayout(filter_frame)
        fl.setContentsMargins(15, 10, 15, 10)
        fl.setSpacing(15)

        # Cihaz Tipi Filtresi
        self.cmb_cihaz_tipi = QComboBox()
        self.cmb_cihaz_tipi.setPlaceholderText("Tüm Tipler")
        self.cmb_cihaz_tipi.setStyleSheet(S["combo"])
        self.cmb_cihaz_tipi.setFixedWidth(200)
        self.cmb_cihaz_tipi.addItem("Tüm Tipler")
        fl.addWidget(self.cmb_cihaz_tipi)

        # Kaynak Filtresi
        self.cmb_kaynak = QComboBox()
        self.cmb_kaynak.setPlaceholderText("Tüm Kaynaklar")
        self.cmb_kaynak.setStyleSheet(S["combo"])
        self.cmb_kaynak.setFixedWidth(200)
        self.cmb_kaynak.addItem("Tüm Kaynaklar")
        fl.addWidget(self.cmb_kaynak)

        # Birim Filtresi
        self.cmb_birim = QComboBox()
        self.cmb_birim.setPlaceholderText("Tüm Birimler")
        self.cmb_birim.setStyleSheet(S["combo"])
        self.cmb_birim.setFixedWidth(200)
        self.cmb_birim.addItem("Tüm Birimler")
        fl.addWidget(self.cmb_birim)

        fl.addStretch()

        # Yenile Butonu
        self.btn_refresh = QPushButton("Yenile")
        self.btn_refresh.setToolTip("Listeyi Yenile")
        self.btn_refresh.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_refresh.setStyleSheet(S["refresh_btn"])
        IconRenderer.set_button_icon(self.btn_refresh, "sync", color=DarkTheme.TEXT_PRIMARY, size=14)
        fl.addWidget(self.btn_refresh)

        # Kapat Butonu
        self.btn_kapat = QPushButton("Kapat")
        self.btn_kapat.setToolTip("Kapat")
        self.btn_kapat.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_kapat.setStyleSheet(S["close_btn"])
        IconRenderer.set_button_icon(self.btn_kapat, "x", color=DarkTheme.TEXT_PRIMARY, size=14)
        fl.addWidget(self.btn_kapat)

        layout.addWidget(filter_frame)

        # ── TABLO ──
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "Cihaz ID", "Marka", "Model", "Seri No", 
            "Birim", "Durum", "Son İşlem"
        ])
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setStyleSheet(S["table"])
        
        # Header ayarları
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents) # ID
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents) # Durum

        layout.addWidget(self.table)

        # ── ALT PANEL ──
        footer = QHBoxLayout()
        
        self.lbl_count = QLabel("Toplam: 0 cihaz")
        self.lbl_count.setStyleSheet(S["footer_label"])
        footer.addWidget(self.lbl_count)
        
        footer.addStretch()

        self.btn_new = QPushButton("YENI CIHAZ EKLE")
        self.btn_new.setStyleSheet(S["action_btn"])
        self.btn_new.setCursor(QCursor(Qt.PointingHandCursor))
        IconRenderer.set_button_icon(self.btn_new, "device_add", color=DarkTheme.TEXT_PRIMARY, size=14)
        footer.addWidget(self.btn_new)

        layout.addLayout(footer)
        
        self.root_layout.addWidget(self.list_container, 1)

        # ── SAĞ PANEL (Arıza Ekle) ──
        self.ariza_panel = ArizaEklePanel(db=self._db, parent=self)
        self.ariza_panel.setVisible(False)
        self.ariza_panel.setStyleSheet(
            f"border-left: 1px solid {DarkTheme.BORDER_PRIMARY}; background-color: {DarkTheme.BG_PRIMARY};"
        )
        self.ariza_panel.kapanma_istegi.connect(self._close_ariza_panel)
        self.ariza_panel.kayit_basarili_sinyali.connect(self._on_ariza_saved)
        self.root_layout.addWidget(self.ariza_panel, 0)

    def _connect_signals(self):
        self.cmb_cihaz_tipi.currentTextChanged.connect(self._filter_table)
        self.cmb_kaynak.currentTextChanged.connect(self._filter_table)
        self.cmb_birim.currentTextChanged.connect(self._filter_table)
        self.btn_refresh.clicked.connect(self.load_data)
        self.btn_new.clicked.connect(self.add_requested.emit)
        self.table.doubleClicked.connect(self._on_row_double_clicked)
        
        # Context Menu
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)

    def load_data(self):
        if not self._db:
            return
            
        try:
            from core.di import get_registry
            registry = get_registry(self._db)
            repo = registry.get("Cihazlar")
            self._all_data = repo.get_all()
            
            # Birim combobox doldur
            birimler, tipler, kaynaklar = set(), set(), set()
            for row in self._all_data:
                if row.get("Birim"): birimler.add(str(row.get("Birim")))
                if row.get("CihazTipi"): tipler.add(str(row.get("CihazTipi")))
                if row.get("Kaynak"): kaynaklar.add(str(row.get("Kaynak")))
            
            def populate(combo, items, default_text):
                current = combo.currentText()
                combo.blockSignals(True)
                combo.clear()
                combo.addItem(default_text)
                combo.addItems(sorted(list(items)))
                idx = combo.findText(current)
                if idx >= 0:
                    combo.setCurrentIndex(idx)
                else:
                    combo.setCurrentIndex(0)
                combo.blockSignals(False)

            populate(self.cmb_birim, birimler, "Tüm Birimler")
            populate(self.cmb_cihaz_tipi, tipler, "Tüm Tipler")
            populate(self.cmb_kaynak, kaynaklar, "Tüm Kaynaklar")

            self._filter_table()
            
        except Exception as e:
            logger.error(f"Cihaz listesi yükleme hatası: {e}")
            QMessageBox.critical(self, "Hata", f"Veri yüklenirken hata oluştu: {e}")

    def _filter_table(self):
        filter_tip = self.cmb_cihaz_tipi.currentText()
        filter_kaynak = self.cmb_kaynak.currentText()
        filter_birim = self.cmb_birim.currentText()
        
        filtered = []
        for row in self._all_data:
            # Cihaz Tipi
            if filter_tip != "Tüm Tipler" and str(row.get("CihazTipi", "")) != filter_tip:
                continue
            # Kaynak
            if filter_kaynak != "Tüm Kaynaklar" and str(row.get("Kaynak", "")) != filter_kaynak:
                continue
            # Birim filtre
            if filter_birim != "Tüm Birimler" and str(row.get("Birim", "")) != filter_birim:
                continue
                
            filtered.append(row)
            
        self._populate_table(filtered)

    def _populate_table(self, data):
        self.table.setRowCount(0)
        self.table.setRowCount(len(data))
        
        for r, row in enumerate(data):
            # ID
            self.table.setItem(r, 0, QTableWidgetItem(str(row.get("Cihazid", ""))))
            # Marka
            self.table.setItem(r, 1, QTableWidgetItem(str(row.get("Marka", ""))))
            # Model
            self.table.setItem(r, 2, QTableWidgetItem(str(row.get("Model", ""))))
            # Seri No
            self.table.setItem(r, 3, QTableWidgetItem(str(row.get("SeriNo", ""))))
            # Birim
            self.table.setItem(r, 4, QTableWidgetItem(str(row.get("Birim", ""))))
            
            # Durum (Renkli)
            durum = str(row.get("Durum", "Bilinmiyor"))
            item_durum = QTableWidgetItem(durum)
            
            # Durum rengi
            color_hex = ThemeManager.get_status_text_color(durum)
            if color_hex:
                item_durum.setForeground(QColor(color_hex))
                
            self.table.setItem(r, 5, item_durum)
            
            # Son İşlem (Placeholder)
            self.table.setItem(r, 6, QTableWidgetItem("-"))
            
            # Satır verisini sakla
            self.table.item(r, 0).setData(Qt.UserRole, row)

        self.lbl_count.setText(f"Toplam: {len(data)} cihaz")

    def _on_row_double_clicked(self, index):
        row = index.row()
        item = self.table.item(row, 0)
        if item:
            data = item.data(Qt.UserRole)
            self.edit_requested.emit(data)

    def _show_context_menu(self, position):
        menu = QMenu()
        menu.setStyleSheet(S["context_menu"])
        
        idx = self.table.indexAt(position)
        if not idx.isValid():
            return
            
        edit_action = QAction("Duzenle", self)
        edit_action.triggered.connect(lambda: self._on_row_double_clicked(idx))
        menu.addAction(edit_action)
        
        menu.addSeparator()
        
        ariza_action = QAction("Ariza Bildir", self)
        ariza_action.triggered.connect(lambda: self._open_ariza_panel(idx))
        menu.addAction(ariza_action)

        bakim_action = QAction("Periyodik Bakim Ekle", self)
        bakim_action.triggered.connect(lambda: self._request_periodic_maintenance(idx))
        menu.addAction(bakim_action)
              
        menu.exec(self.table.viewport().mapToGlobal(position))

    def _open_ariza_panel(self, index):
        row = index.row()
        item = self.table.item(row, 0)
        if item:
            data = item.data(Qt.UserRole)
            cihaz_id = str(data.get("Cihazid", ""))
            self.ariza_panel.formu_sifirla(cihaz_id)
            self.ariza_panel.setVisible(True)

    def _request_periodic_maintenance(self, index):
        row = index.row()
        item = self.table.item(row, 0)
        if item:
            data = item.data(Qt.UserRole)
            self.periodic_maintenance_requested.emit(data)

    def _close_ariza_panel(self):
        self.ariza_panel.setVisible(False)

    def _on_ariza_saved(self):
        self.ariza_panel.setVisible(False)
        self.load_data()

    def _delete_row(self, row):
        item = self.table.item(row, 0)
        if not item: return
        
        data = item.data(Qt.UserRole)
        cihaz_id = data.get("Cihazid")
        
        reply = QMessageBox.question(
            self, "Silme Onayı", 
            f"{cihaz_id} ID'li cihazı silmek istediğinize emin misiniz?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                from core.di import get_registry
                registry = get_registry(self._db)
                repo = registry.get("Cihazlar")
                repo.delete(cihaz_id)
                
                self.load_data()
                QMessageBox.information(self, "Başarılı", "Cihaz silindi.")
            except Exception as e:
                logger.error(f"Cihaz silme hatası: {e}")
                QMessageBox.critical(self, "Hata", f"Silme işlemi başarısız: {e}")


