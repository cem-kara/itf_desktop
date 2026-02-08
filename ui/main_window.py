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
        self._db = SQLiteManager()

        self._load_theme()
        self._build_ui()
        self._build_status_bar()
        self._setup_sync()

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

        # Sidebar
        self.sidebar = Sidebar()
        self.sidebar.menu_clicked.connect(self._on_menu_clicked)
        self.sidebar.sync_btn.clicked.connect(self._start_sync)
        main_layout.addWidget(self.sidebar)

        # İçerik alanı
        content = QWidget()
        content.setObjectName("content_area")
        content.setStyleSheet("""
            #content_area {
                background-color: #16172b;
            }
        """)
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        # Sayfa başlığı
        self.page_title = QLabel("")
        self.page_title.setStyleSheet("""
            font-size: 20px; font-weight: bold;
            color: #e0e2ea; padding: 16px 24px 8px 24px;
            background-color: transparent;
        """)
        self.page_title.setVisible(False)
        content_layout.addWidget(self.page_title)

        # Stacked Widget
        self.stack = QStackedWidget()
        content_layout.addWidget(self.stack, 1)

        main_layout.addWidget(content, 1)

        # Hoş geldin
        self._welcome = WelcomePage()
        self.stack.addWidget(self._welcome)
        self.stack.setCurrentWidget(self._welcome)

    def _build_status_bar(self):
        self.status = QStatusBar()
        self.status.setStyleSheet("""
            QStatusBar {
                background-color: #0f1020;
                border-top: 1px solid rgba(255, 255, 255, 0.06);
                padding: 2px 8px;
            }
            QStatusBar QLabel {
                font-size: 12px; color: #5a5d6e; padding: 0 8px;
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

    # ── SAYFA YÖNETİMİ ──

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
        if baslik == "Personel Listesi":
            from ui.pages.personel.personel_listesi import PersonelListesiPage
            page = PersonelListesiPage(db=self._db)
            page.table.doubleClicked.connect(
                lambda idx: self._open_personel_detay(page, idx)
            )
            page.btn_kapat.clicked.connect(lambda: self._close_page("Personel Listesi"))
            page.btn_yeni.clicked.connect(lambda: self._on_menu_clicked("Personel", "Personel Ekle"))
            page.izin_requested.connect(lambda data: self.open_izin_giris(data))
            page.load_data()
            return page

        if baslik == "Personel Ekle":
            from ui.pages.personel.personel_ekle import PersonelEklePage
            page = PersonelEklePage(
                db=self._db,
                on_saved=self._on_personel_saved
            )
            return page

        if baslik == "İzin Takip":
            from ui.pages.personel.izin_takip import IzinTakipPage
            page = IzinTakipPage(db=self._db)
            page.btn_kapat.clicked.connect(lambda: self._close_page("İzin Takip"))
            page.load_data()
            return page

        if baslik == "FHSZ Yönetim":
            from ui.pages.personel.fhsz_yonetim import FHSZYonetimPage
            page = FHSZYonetimPage(db=self._db)
            page.btn_kapat.clicked.connect(lambda: self._close_page("FHSZ Yönetim"))
            page.load_data()
            return page

        if baslik == "Puantaj Rapor":
            from ui.pages.personel.puantaj_rapor import PuantajRaporPage
            page = PuantajRaporPage(db=self._db)
            page.btn_kapat.clicked.connect(lambda: self._close_page("Puantaj Rapor"))
            return page

        return PlaceholderPage(
            title=baslik,
            subtitle=f"{group} modülü — geliştirme aşamasında"
        )

    def _open_personel_detay(self, liste_page, index):
        """Personel listesinde çift tıklama → detay sayfası aç."""
        source_idx = liste_page._proxy.mapToSource(index)
        row_data = liste_page._model.get_row(source_idx.row())
        if not row_data:
            return

        tc = row_data.get("KimlikNo", "")
        ad = row_data.get("AdSoyad", "")
        detay_key = f"__detay_{tc}"

        # Eski detay sayfası varsa kaldır
        if detay_key in self._pages:
            old = self._pages.pop(detay_key)
            self.stack.removeWidget(old)
            old.deleteLater()

        from ui.pages.personel.personel_detay import PersonelDetayPage
        page = PersonelDetayPage(
            db=self._db,
            personel_data=row_data,
            on_back=lambda: self._back_to_personel_listesi(detay_key)
        )
        page.ayrilis_requested.connect(
            lambda data: self.open_isten_ayrilik(data, detay_key)
        )
        self._pages[detay_key] = page
        self.stack.addWidget(page)
        self.stack.setCurrentWidget(page)
        self.page_title.setText(f"Personel Detay — {ad}")

    def _back_to_personel_listesi(self, detay_key):
        """Detay sayfasından listeye geri dön."""
        if "Personel Listesi" in self._pages:
            page = self._pages["Personel Listesi"]
            page.load_data()
            self.stack.setCurrentWidget(page)
            self.page_title.setText("Personel Listesi")
            self.sidebar.set_active("Personel Listesi")

        if detay_key in self._pages:
            old = self._pages.pop(detay_key)
            self.stack.removeWidget(old)
            old.deleteLater()

    def open_isten_ayrilik(self, personel_data, from_key=None):
        """İşten ayrılık sayfasını aç."""
        tc = personel_data.get("KimlikNo", "")
        ad = personel_data.get("AdSoyad", "")
        ayrilik_key = f"__ayrilik_{tc}"

        if ayrilik_key in self._pages:
            old = self._pages.pop(ayrilik_key)
            self.stack.removeWidget(old)
            old.deleteLater()

        from ui.pages.personel.isten_ayrilik import IstenAyrilikPage
        page = IstenAyrilikPage(
            db=self._db,
            personel_data=personel_data,
            on_back=lambda: self._back_from_ayrilik(ayrilik_key, from_key)
        )
        self._pages[ayrilik_key] = page
        self.stack.addWidget(page)
        self.stack.setCurrentWidget(page)
        self.page_title.setText(f"İşten Ayrılış — {ad}")

    def _back_from_ayrilik(self, ayrilik_key, from_key=None):
        """Ayrılık sayfasından geri dön."""
        if from_key and from_key in self._pages:
            self.stack.setCurrentWidget(self._pages[from_key])
        elif "Personel Listesi" in self._pages:
            page = self._pages["Personel Listesi"]
            page.load_data()
            self.stack.setCurrentWidget(page)
            self.page_title.setText("Personel Listesi")
            self.sidebar.set_active("Personel Listesi")

        if ayrilik_key in self._pages:
            old = self._pages.pop(ayrilik_key)
            self.stack.removeWidget(old)
            old.deleteLater()

    def open_izin_giris(self, personel_data, from_key=None):
        """İzin giriş sayfasını aç."""
        tc = personel_data.get("KimlikNo", "")
        ad = personel_data.get("AdSoyad", "")
        izin_key = f"__izin_{tc}"

        if izin_key in self._pages:
            old = self._pages.pop(izin_key)
            self.stack.removeWidget(old)
            old.deleteLater()

        from ui.pages.personel.izin_giris import IzinGirisPage
        page = IzinGirisPage(
            db=self._db,
            personel_data=personel_data,
            on_back=lambda: self._back_from_izin(izin_key, from_key)
        )
        self._pages[izin_key] = page
        self.stack.addWidget(page)
        self.stack.setCurrentWidget(page)
        self.page_title.setText(f"İzin Takip — {ad}")

    def _back_from_izin(self, izin_key, from_key=None):
        """İzin sayfasından geri dön."""
        # Geldiği sayfaya geri dön
        if from_key and from_key in self._pages:
            page = self._pages[from_key]
            self.stack.setCurrentWidget(page)
            ad = from_key.replace("__detay_", "")
            self.page_title.setText(f"Personel Detay — {ad}")
        elif "Personel Listesi" in self._pages:
            page = self._pages["Personel Listesi"]
            page.load_data()
            self.stack.setCurrentWidget(page)
            self.page_title.setText("Personel Listesi")
            self.sidebar.set_active("Personel Listesi")

        if izin_key in self._pages:
            old = self._pages.pop(izin_key)
            self.stack.removeWidget(old)
            old.deleteLater()

    def register_page(self, baslik, widget):
        self._pages[baslik] = widget
        self.stack.addWidget(widget)

    def _close_page(self, baslik):
        """Sayfayı kapat ve welcome'a dön."""
        if baslik in self._pages:
            old = self._pages.pop(baslik)
            self.stack.removeWidget(old)
            old.deleteLater()
        self.stack.setCurrentWidget(self._welcome)
        self.page_title.setVisible(False)
        self.sidebar.set_active("")

    # ── SENKRONİZASYON ──

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
        self._refresh_active_page()

    @Slot(str)
    def _on_sync_error(self, msg):
        now = datetime.now().strftime("%H:%M:%S")
        self.sidebar.set_sync_enabled(True)
        self.sidebar.set_sync_status("● Sync hatası", "#ef4444")
        self.sync_status_label.setText("● Sync hatası")
        self.sync_status_label.setStyleSheet("color: #ef4444;")
        self.last_sync_label.setText(f"Hata: {now}")

    def closeEvent(self, event):
        if self._sync_worker and self._sync_worker.isRunning():
            self._sync_worker.stop()
        if self._db:
            self._db.close()
        event.accept()

    def _refresh_active_page(self):
        current = self.stack.currentWidget()
        if hasattr(current, "load_data"):
            try:
                current.load_data()
            except Exception as e:
                logger.error(f"Sayfa yenileme hatası: {e}")

    def _on_personel_saved(self):
        """Personel kaydedildikten sonra listeye dön ve yenile."""
        if "Personel Listesi" in self._pages:
            page = self._pages["Personel Listesi"]
            page.load_data()
            self.stack.setCurrentWidget(page)
            self.page_title.setText("Personel Listesi")
            self.sidebar.set_active("Personel Listesi")

        # Ekle formunu sıfırla (sonraki açılışta taze form)
        if "Personel Ekle" in self._pages:
            del self._pages["Personel Ekle"]
