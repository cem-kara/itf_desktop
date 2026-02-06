import os
from datetime import datetime

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QStackedWidget, QLabel, QStatusBar
)
from PySide6.QtCore import Qt, QTimer, Slot

from core.config import AppConfig
from core.logger import logger
from core.paths import DB_PATH
from ui.sidebar import Sidebar
from ui.pages.placeholder import WelcomePage, PlaceholderPage
from database.sync_worker import SyncWorker
from database.sqlite_manager import SQLiteManager


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()

        self.setWindowTitle(f"{AppConfig.APP_NAME} v{AppConfig.VERSION}")
        self.setMinimumSize(1100, 700)
        self.resize(1280, 800)

        self._pages = {}
        self._sync_worker = None

        # Ana thread DB bağlantısı (okuma amaçlı — UI sayfaları için)
        self._db = SQLiteManager()

        self._load_theme()
        self._build_ui()
        self._build_status_bar()
        self._setup_sync()

    # ═══════════════════════════════════════════

    def _load_theme(self):
        theme_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "theme.qss"
        )
        try:
            with open(theme_path, "r", encoding="utf-8") as f:
                self.setStyleSheet(f.read())
        except FileNotFoundError:
            logger.warning("Tema dosyası bulunamadı")

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Sidebar (kendi styling'ini yönetiyor)
        self.sidebar = Sidebar()
        self.sidebar.menu_clicked.connect(self._on_menu_clicked)
        self.sidebar.sync_btn.clicked.connect(self._start_sync)
        main_layout.addWidget(self.sidebar)

        # İçerik alanı
        content = QWidget()
        content.setObjectName("content_area")
        content.setStyleSheet("background-color: #f8fafc;")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        # Sayfa başlığı
        self.page_title = QLabel("")
        self.page_title.setStyleSheet("""
            font-size: 20px; font-weight: bold;
            color: #0f172a; padding: 16px 24px 8px 24px;
            background-color: #f8fafc;
        """)
        self.page_title.setVisible(False)
        content_layout.addWidget(self.page_title)

        # Stacked Widget
        self.stack = QStackedWidget()
        content_layout.addWidget(self.stack, 1)

        main_layout.addWidget(content, 1)

        # Hoş geldin sayfası
        self._welcome = WelcomePage()
        self.stack.addWidget(self._welcome)
        self.stack.setCurrentWidget(self._welcome)

    def _build_status_bar(self):
        self.status = QStatusBar()
        self.status.setStyleSheet("""
            QStatusBar {
                background-color: #e2e8f0;
                border-top: 1px solid #cbd5e1;
                padding: 2px 8px;
            }
            QStatusBar QLabel {
                font-size: 12px; color: #475569; padding: 0 8px;
            }
        """)
        self.setStatusBar(self.status)

        self.sync_status_label = QLabel("● Hazır")
        self.sync_status_label.setStyleSheet("color: #22c55e;")
        self.status.addWidget(self.sync_status_label)

        self.last_sync_label = QLabel("")
        self.status.addWidget(self.last_sync_label, 1)

        version_label = QLabel(f"v{AppConfig.VERSION}")
        self.status.addPermanentWidget(version_label)

    # ═══════════════════════════════════════════
    #  SAYFA YÖNETİMİ
    # ═══════════════════════════════════════════

    @Slot(str, str)
    def _on_menu_clicked(self, group, baslik):
        logger.info(f"Menü seçildi: {group} → {baslik}")

        if baslik in self._pages:
            page = self._pages[baslik]
        else:
            page = self._create_page(group, baslik)
            self._pages[baslik] = page
            self.stack.addWidget(page)

        self.stack.setCurrentWidget(page)
        self.page_title.setText(baslik)
        self.page_title.setVisible(True)

    def _create_page(self, group, baslik):
        # ── Personel modülü ──
        if baslik == "Personel Listesi":
            from ui.pages.personel.personel_listesi import PersonelListesiPage
            page = PersonelListesiPage(db=self._db)
            page.load_data()
            return page

        # TODO: Diğer sayfalar burada eklenecek

        return PlaceholderPage(
            title=baslik,
            subtitle=f"{group} modülü — geliştirme aşamasında"
        )

    def register_page(self, baslik, widget):
        self._pages[baslik] = widget
        self.stack.addWidget(widget)

    # ═══════════════════════════════════════════
    #  SENKRONİZASYON
    # ═══════════════════════════════════════════

    def _setup_sync(self):
        if AppConfig.AUTO_SYNC:
            QTimer.singleShot(3000, self._start_sync)
            self._sync_timer = QTimer(self)
            self._sync_timer.timeout.connect(self._start_sync)
            self._sync_timer.start(AppConfig.SYNC_INTERVAL_MIN * 60 * 1000)

    def _start_sync(self):
        if self._sync_worker and self._sync_worker.isRunning():
            return

        self.sidebar.set_sync_enabled(False)
        self.sidebar.set_sync_status("⏳ Senkronize ediliyor...", "#f59e0b")
        self.sync_status_label.setText("⏳ Senkronize ediliyor...")
        self.sync_status_label.setStyleSheet("color: #f59e0b;")

        self._sync_worker = SyncWorker()
        self._sync_worker.finished.connect(self._on_sync_finished)
        self._sync_worker.error.connect(self._on_sync_error)
        self._sync_worker.start()

    @Slot()
    def _on_sync_finished(self):
        now = datetime.now().strftime("%H:%M:%S")
        self.sidebar.set_sync_enabled(True)
        self.sidebar.set_sync_status("● Senkronize", "#22c55e")
        self.sync_status_label.setText("● Senkronize")
        self.sync_status_label.setStyleSheet("color: #22c55e;")
        self.last_sync_label.setText(f"Son sync: {now}")

        # Açık sayfaların verisini yenile
        self._refresh_active_page()

    @Slot(str)
    def _on_sync_error(self, msg):
        now = datetime.now().strftime("%H:%M:%S")
        self.sidebar.set_sync_enabled(True)
        self.sidebar.set_sync_status("● Sync hatası", "#ef4444")
        self.sync_status_label.setText("● Sync hatası")
        self.sync_status_label.setStyleSheet("color: #ef4444;")
        self.last_sync_label.setText(f"Hata: {now}")

    # ═══════════════════════════════════════════

    def closeEvent(self, event):
        if self._sync_worker and self._sync_worker.isRunning():
            self._sync_worker.stop()
        if self._db:
            self._db.close()
        event.accept()

    def _refresh_active_page(self):
        """Aktif sayfanın verisini yeniler (sync sonrası)."""
        current = self.stack.currentWidget()
        if hasattr(current, "load_data"):
            try:
                current.load_data()
            except Exception as e:
                logger.error(f"Sayfa yenileme hatası: {e}")
