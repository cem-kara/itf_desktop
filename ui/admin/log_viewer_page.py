"""
Log Viewer Page — Program loglarını görüntüleme sayfası

Özellikler:
- Log dosyası seçimi (app.log, sync.log, errors.log, ui_log.log)
- Log seviyesi filtreleme (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- Tarih aralığı filtreleme
- Metin araması
- Renklendirme (seviyeye göre)
- Otomatik yenileme
"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QLineEdit,
    QPushButton,
    QTableView,
    QHeaderView,
    QDateEdit,
    QSpinBox,
    QGroupBox,
    QCheckBox,
    QMessageBox,
)
from PySide6.QtCore import Qt, QTimer, QDate
from PySide6.QtGui import QColor

from core.logger import logger
from core.services.log_service import LogService
from ui.components.base_table_model import BaseTableModel
from ui.styles.colors import DarkTheme as C
from ui.styles.components import STYLES
from ui.styles.icons import Icons, IconRenderer


# Sütun tanımları
LOG_COLUMNS = [
    ("timestamp", "Zaman", 150),
    ("level", "Seviye", 80),
    ("message", "Mesaj", 600),
]

# Seviye renkleri
LEVEL_COLORS = {
    "DEBUG": "#888888",
    "INFO": "#3ecf8e",
    "WARNING": "#f7b731",
    "ERROR": "#f75f5f",
    "CRITICAL": "#d63031",
}


class LogTableModel(BaseTableModel):
    """Log kayıtları için tablo modeli"""

    def __init__(self, rows=None, parent=None):
        super().__init__(LOG_COLUMNS, rows, parent)

    def _display(self, key, row):
        val = row.get(key, "")
        return str(val) if val else ""

    def _fg(self, key, row):
        """Seviye rengini ayarla"""
        level = row.get("level", "")
        if level in LEVEL_COLORS:
            return QColor(LEVEL_COLORS[level])
        return None

    def _align(self, key):
        if key == "timestamp":
            return Qt.AlignmentFlag.AlignCenter
        if key == "level":
            return Qt.AlignmentFlag.AlignCenter
        return Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft


class LogViewerPage(QWidget):
    """Log görüntüleyici sayfası"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._service = LogService()
        self._auto_refresh_timer = QTimer(self)
        self._auto_refresh_timer.timeout.connect(self._load_logs)
        
        self._setup_ui()
        self._load_available_files()

    def _setup_ui(self):
        """UI bileşenlerini oluştur"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Başlık
        title_layout = QHBoxLayout()
        title_label = QLabel("Log Görüntüleyici")
        title_label.setProperty("color-role", "primary")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        title_label.style().unpolish(title_label)
        title_label.style().polish(title_label)
        title_icon = QLabel()
        title_icon.setPixmap(Icons.pixmap("file_text", size=24))
        title_layout.addWidget(title_icon)
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        layout.addLayout(title_layout)

        # Filtre grubu
        filter_group = QGroupBox("Filtreler")
        filter_layout = QVBoxLayout()
        filter_group.setLayout(filter_layout)

        # Üst satır: Log dosyası ve seviye
        row1 = QHBoxLayout()
        
        row1.addWidget(QLabel("Log Dosyası:"))
        self._combo_file = QComboBox()
        self._combo_file.setMinimumWidth(200)
        # setStyleSheet kaldırıldı: input_combo — global QSS kuralı geçerli
        self._combo_file.currentIndexChanged.connect(self._on_file_changed)
        row1.addWidget(self._combo_file)
        
        row1.addWidget(QLabel("Seviye:"))
        self._combo_level = QComboBox()
        # setStyleSheet kaldırıldı: input_combo — global QSS kuralı geçerli
        self._combo_level.addItem("Tümü", None)
        self._combo_level.addItem("DEBUG", "DEBUG")
        self._combo_level.addItem("INFO", "INFO")
        self._combo_level.addItem("WARNING", "WARNING")
        self._combo_level.addItem("ERROR", "ERROR")
        self._combo_level.addItem("CRITICAL", "CRITICAL")
        self._combo_level.setCurrentText("Tümü")
        row1.addWidget(self._combo_level)
        
        row1.addWidget(QLabel("Max Satır:"))
        self._spin_max_lines = QSpinBox()
        # setStyleSheet kaldırıldı: spin — global QSS kuralı geçerli
        self._spin_max_lines.setRange(100, 10000)
        self._spin_max_lines.setValue(1000)
        self._spin_max_lines.setSingleStep(100)
        row1.addWidget(self._spin_max_lines)
        
        row1.addStretch()
        filter_layout.addLayout(row1)

        # Alt satır: Tarih ve arama
        row2 = QHBoxLayout()
        
        row2.addWidget(QLabel("Başlangıç:"))
        self._date_start = QDateEdit()
        self._date_start.setCalendarPopup(True)
        self._date_start.setDate(QDate.currentDate().addDays(-7))
        self._date_start.setDisplayFormat("yyyy-MM-dd")
        row2.addWidget(self._date_start)
        
        row2.addWidget(QLabel("Bitiş:"))
        self._date_end = QDateEdit()
        self._date_end.setCalendarPopup(True)
        self._date_end.setDate(QDate.currentDate())
        self._date_end.setDisplayFormat("yyyy-MM-dd")
        row2.addWidget(self._date_end)
        
        self._check_date_filter = QCheckBox("Tarih filtresi aktif")
        row2.addWidget(self._check_date_filter)
        
        row2.addWidget(QLabel("Ara:"))
        self._txt_search = QLineEdit()
        # setStyleSheet kaldırıldı: input_field — global QSS kuralı geçerli
        self._txt_search.setPlaceholderText("Mesajda ara...")
        self._txt_search.setMinimumWidth(200)
        self._txt_search.returnPressed.connect(self._load_logs)
        row2.addWidget(self._txt_search)
        
        row2.addStretch()
        filter_layout.addLayout(row2)

        layout.addWidget(filter_group)

        # Butonlar
        btn_layout = QHBoxLayout()
        
        self._btn_load = QPushButton("Yükle")
        IconRenderer.set_button_icon(self._btn_load, "refresh", size=14)
        self._btn_load.clicked.connect(self._load_logs)
        btn_layout.addWidget(self._btn_load)
        
        self._btn_clear = QPushButton("Temizle")
        IconRenderer.set_button_icon(self._btn_clear, "trash", size=14)
        self._btn_clear.clicked.connect(self._clear_table)
        btn_layout.addWidget(self._btn_clear)
        
        self._btn_export = QPushButton("Dışa Aktar")
        IconRenderer.set_button_icon(self._btn_export, "download", size=14)
        self._btn_export.clicked.connect(self._export_logs)
        btn_layout.addWidget(self._btn_export)
        
        btn_layout.addSpacing(20)
        
        self._check_auto_refresh = QCheckBox("Otomatik Yenile (10 sn)")
        self._check_auto_refresh.stateChanged.connect(self._toggle_auto_refresh)
        btn_layout.addWidget(self._check_auto_refresh)
        
        btn_layout.addStretch()
        
        self._lbl_stats = QLabel("Hazır")
        btn_layout.addWidget(self._lbl_stats)
        
        layout.addLayout(btn_layout)

        # Tablo
        self._table = QTableView()
        self._table.setAlternatingRowColors(True)
        self._table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        self._table.setSortingEnabled(False)
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.verticalHeader().setVisible(False)
        
        self._model = LogTableModel()
        self._table.setModel(self._model)
        
        # Sütun genişlikleri
        for i, (_, _, width) in enumerate(LOG_COLUMNS):
            self._table.setColumnWidth(i, width)
        
        layout.addWidget(self._table)

    def _load_available_files(self):
        """Mevcut log dosyalarını combo'ya yükle"""
        files = self._service.get_available_log_files().veri or []
        
        self._combo_file.clear()
        for file_info in files:
            display_text = f"{file_info['name']} ({file_info['size_mb']} MB)"
            self._combo_file.addItem(display_text, file_info['path'])
        
        if files:
            self._combo_file.setCurrentIndex(0)
            self._load_logs()

    def _on_file_changed(self):
        """Dosya değiştiğinde logları yükle"""
        if self._combo_file.currentData():
            self._load_logs()

    def _load_logs(self):
        """Seçili log dosyasını oku ve tabloya yükle"""
        log_file_path = self._combo_file.currentData()
        if not log_file_path:
            self._lbl_stats.setText("Log dosyası seçilmedi")
            return

        # Filtreleri topla
        level_filter = self._combo_level.currentData()
        search_text = self._txt_search.text().strip()
        max_lines = self._spin_max_lines.value()
        
        start_date = None
        end_date = None
        if self._check_date_filter.isChecked():
            start_date = self._date_start.date().toString("yyyy-MM-dd")
            end_date = self._date_end.date().toString("yyyy-MM-dd")

        try:
            self._lbl_stats.setText("Yükleniyor...")
            
            logs = self._service.read_logs(
                log_file_path=log_file_path,
                level_filter=level_filter,
                search_text=search_text if search_text else None,
                start_date=start_date,
                end_date=end_date,
                max_lines=max_lines,
                reverse=True
            ).veri or []
            
            self._model.set_data(logs)
            
            # İstatistik
            stats_text = f"{len(logs)} kayıt yüklendi"
            if level_filter:
                stats_text += f" (Seviye: {level_filter})"
            if search_text:
                stats_text += f" (Arama: '{search_text}')"
            
            self._lbl_stats.setText(stats_text)
            logger.info(f"Log yüklendi: {len(logs)} kayıt")
            
        except Exception as e:
            self._lbl_stats.setText(f"Hata: {str(e)}")
            logger.error(f"Log yükleme hatası: {e}")
            QMessageBox.critical(self, "Hata", f"Loglar yüklenemedi:\n{str(e)}")

    def _clear_table(self):
        """Tabloyu temizle"""
        self._model.set_data([])
        self._lbl_stats.setText("Tablo temizlendi")

    def _export_logs(self):
        """Gösterilen logları dosyaya kaydet"""
        from PySide6.QtWidgets import QFileDialog
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Logları Kaydet",
            "",
            "Text Files (*.txt);;All Files (*)"
        )
        
        if not file_path:
            return
        
        try:
            rows = self._model.all_data()
            with open(file_path, 'w', encoding='utf-8') as f:
                for row in rows:
                    f.write(row.get('raw', '') + '\n')
            
            QMessageBox.information(self, "Başarılı", f"{len(rows)} log kaydedildi:\n{file_path}")
            logger.info(f"Loglar dışa aktarıldı: {file_path}")
            
        except Exception as e:
            logger.error(f"Log dışa aktarma hatası: {e}")
            QMessageBox.critical(self, "Hata", f"Loglar kaydedilemedi:\n{str(e)}")

    def _toggle_auto_refresh(self, state):
        """Otomatik yenilemeyi aç/kapat"""
        if state == Qt.CheckState.Checked:
            self._auto_refresh_timer.start(10000)  # 10 saniye
            logger.info("Otomatik log yenileme aktifleştirildi")
        else:
            self._auto_refresh_timer.stop()
            logger.info("Otomatik log yenileme kapatıldı")
