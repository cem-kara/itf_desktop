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
        self.sidebar.dashboard_clicked.connect(self._open_dashboard)
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
        from ui.pages.placeholder import WelcomePage
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

    @Slot()
    def _open_dashboard(self):
        self._on_menu_clicked("YÖNETİCİ İŞLEMLERİ", "Genel Bakış")

    def _on_menu_clicked(self, group, baslik, *args):
        """
        Menüden veya dashboard'dan gelen tıklamaları yönetir.
        Dashboard'dan gelirse `args` içinde filtre dict'i bulunur.
        """
        filters = args[0] if args else {}
        logger.info(f"Menü seçildi: {group} → {baslik} (Filtreler: {filters})")

        if baslik in self._pages:
            page = self._pages[baslik]
        else:
            page = self._create_page(group, baslik)
            if isinstance(page, PlaceholderPage) or page is None:
                if page:
                    self.stack.addWidget(page)
                    self.stack.setCurrentWidget(page)
                return
            self._pages[baslik] = page
            self.stack.addWidget(page)

        self.stack.setCurrentWidget(page)
        self.page_title.setText(baslik)
        self.page_title.setVisible(True)

        if filters and hasattr(page, "apply_filters"):
            logger.info(f"'{baslik}' sayfasına filtreler uygulanıyor: {filters}")
            page.apply_filters(filters)

    def _create_page(self, group, baslik):
        if baslik == "Genel Bakış":
            from ui.pages.dashboard import DashboardPage
            page = DashboardPage(db=self._db)
            page.open_page_requested.connect(self._on_menu_clicked)
            page.btn_kapat.clicked.connect(lambda: self._close_page("Genel Bakış"))
            page.load_data()
            return page

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

        if baslik == "Saglik Takip":
            from ui.pages.personel.saglik_takip import SaglikTakipPage
            page = SaglikTakipPage(db=self._db)
            page.btn_kapat.clicked.connect(lambda: self._close_page("Saglik Takip"))
            page.load_data()
            return page

        if baslik == "Cihaz Ekle":
            from ui.pages.cihaz.cihaz_ekle import CihazEklePage
            page = CihazEklePage(
                db=self._db,
                on_saved=self._on_cihaz_saved
            )
            return page

        if baslik == "Cihaz Listesi":
            from ui.pages.cihaz.cihaz_listesi import CihazListesiPage
            page = CihazListesiPage(db=self._db)
            page.add_requested.connect(lambda: self._on_menu_clicked("Cihaz", "Cihaz Ekle"))
            page.edit_requested.connect(self._open_cihaz_detay)
            page.periodic_maintenance_requested.connect(self.open_periodic_maintenance_for_device)
            page.btn_kapat.clicked.connect(lambda: self._close_page("Cihaz Listesi"))
            page.load_data()
            return page

        if baslik == "Arıza Listesi":
            from ui.pages.cihaz.ariza_listesi import ArizaListesiPage
            page = ArizaListesiPage(db=self._db)
            page.btn_kapat.clicked.connect(lambda: self._close_page("Arıza Listesi"))
            page.load_data()
            return page

        if baslik == "Periyodik Bakım":
            from ui.pages.cihaz.periyodik_bakim import PeriyodikBakimPage
            page = PeriyodikBakimPage(db=self._db)
            page.btn_kapat.clicked.connect(lambda: self._close_page("Periyodik Bakım"))
            return page

        if baslik == "Kalibrasyon Takip":
            from ui.pages.cihaz.kalibrasyon_takip import KalibrasyonTakipPage
            page = KalibrasyonTakipPage(db=self._db)
            page.btn_kapat.clicked.connect(lambda: self._close_page("Kalibrasyon Takip"))
            return page
        
        if baslik == "RKE Envanter":
            from ui.pages.rke.rke_yonetim import RKEYonetimPage
            page = RKEYonetimPage(db=self._db)
            page.btn_kapat.clicked.connect(lambda: self._close_page("RKE Envanter"))
            page.load_data()
            return page

        if baslik == "RKE Muayene":
            from ui.pages.rke.rke_muayene import RKEMuayenePage
            page = RKEMuayenePage(db=self._db)
            page.btn_kapat.clicked.connect(lambda: self._close_page("RKE Muayene"))
            page.load_data()
            return page

        if baslik == "RKE Raporlama":
            from ui.pages.rke.rke_rapor import RKERaporPage
            page = RKERaporPage(db=self._db)
            page.btn_kapat.clicked.connect(lambda: self._close_page("RKE Raporlama"))
            page.load_data()
            return page

        if baslik == "Yıl Sonu İzin":
            from ui.pages.admin.yil_sonu_islemleri import YilSonuIslemleriPage
            page = YilSonuIslemleriPage(db=self._db)
            page.btn_kapat.clicked.connect(lambda: self._close_page("Yıl Sonu İzin"))
            page.load_data()
            return page

        if baslik == "Log Görüntüleyici":
            from ui.pages.admin.log_goruntuleme import LogGoruntuleme
            page = LogGoruntuleme(db=self._db)
            page.btn_kapat.clicked.connect(lambda: self._close_page("Log Görüntüleyici"))
            return page
        
        if baslik == "Ayarlar":
            from ui.pages.admin.yonetim_ayarlar import AyarlarPenceresi
            page = AyarlarPenceresi(db=self._db)
            page.btn_kapat.clicked.connect(lambda: self._close_page("Ayarlar"))
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
            logger.warning("Sync zaten çalışıyor, yeni sync atlanıyor")
            return
        
        logger.info("Sync başlatılıyor...")
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
        logger.info(f"Sync başarıyla tamamlandı ({now})")
        
        self.sidebar.set_sync_enabled(True)
        self.sidebar.set_sync_status("● Senkronize", "#22c55e")
        self.sync_status_label.setText("● Senkronize")
        self.sync_status_label.setStyleSheet("color: #22c55e;")
        self.last_sync_label.setText(f"Son sync: {now}")
        self._refresh_active_page()
        # Dashboard açıksa onu da yenile
        if "Genel Bakış" in self._pages:
            dashboard_page = self._pages["Genel Bakış"]
            if hasattr(dashboard_page, "load_data"):
                logger.info("Dashboard yenileniyor...")
                dashboard_page.load_data()

    @Slot(str, str)
    def _on_sync_error(self, short_msg, detail_msg):
        """
        Sync hatası geldiğinde detaylı bilgi göster
        
        Args:
            short_msg: Kısa hata mesajı (status bar için)
            detail_msg: Detaylı hata mesajı (tooltip/log için)
        """
        now = datetime.now().strftime("%H:%M:%S")
        
        logger.error(f"Sync hatası: {short_msg} - {detail_msg}")
        
        # UI güncelleme
        self.sidebar.set_sync_enabled(True)
        self.sidebar.set_sync_status(f"● {short_msg}", "#ef4444")
        
        # Status bar'da kısa mesaj
        self.sync_status_label.setText(f"● {short_msg}")
        self.sync_status_label.setStyleSheet("color: #ef4444;")
        
        # Detaylı mesajı tooltip olarak ekle
        self.sync_status_label.setToolTip(
            f"Hata Zamanı: {now}\n"
            f"Kısa Açıklama: {short_msg}\n"
            f"Detay: {detail_msg}\n\n"
            f"Daha fazla bilgi için log dosyalarını kontrol edin."
        )
        
        self.last_sync_label.setText(f"Hata: {now}")
        self.last_sync_label.setToolTip(detail_msg)
        
        # Opsiyonel: Kullanıcıya bildirim göster
        from PySide6.QtWidgets import QMessageBox
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Warning)
        msg_box.setWindowTitle("Senkronizasyon Hatası")
        msg_box.setText(short_msg)
        msg_box.setInformativeText(detail_msg)
        msg_box.setDetailedText(
            f"Hata zamanı: {now}\n\n"
            f"Çözüm önerileri:\n"
            f"1. İnternet bağlantınızı kontrol edin\n"
            f"2. Google Sheets erişim izinlerini kontrol edin\n"
            f"3. Birkaç dakika bekleyip tekrar deneyin\n"
            f"4. Sorun devam ederse log dosyalarını kontrol edin:\n"
            f"   - logs/app.log\n"
            f"   - logs/sync.log\n"
            f"   - logs/errors.log"
        )
        msg_box.setStandardButtons(QMessageBox.Ok)
        msg_box.exec()

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

    def _on_cihaz_saved(self):
        """Cihaz kaydedildikten/iptal edildikten sonra listeye dön ve yenile."""
        # Cihaz Ekle sayfasını kaldır
        if "Cihaz Ekle" in self._pages:
            old = self._pages.pop("Cihaz Ekle")
            self.stack.removeWidget(old)
            old.deleteLater()

        # Cihaz Listesi sayfasına geç, yoksa welcome'a dön
        if "Cihaz Listesi" in self._pages:
            page = self._pages["Cihaz Listesi"]
            if hasattr(page, "load_data"):
                page.load_data()
            self.stack.setCurrentWidget(page)
            self.page_title.setText("Cihaz Listesi")
            self.sidebar.set_active("Cihaz Listesi")
        else:
            self.stack.setCurrentWidget(self._welcome)
            self.page_title.setVisible(False)
            self.sidebar.set_active("")

    def _open_cihaz_duzenle(self, data):
        """Cihaz düzenleme sayfasını aç."""
        # Eğer Cihaz Ekle sayfası zaten açıksa kapat (temiz başlasın)
        if "Cihaz Ekle" in self._pages:
            old = self._pages.pop("Cihaz Ekle")
            self.stack.removeWidget(old)
            old.deleteLater()
            
        from ui.pages.cihaz.cihaz_ekle import CihazEklePage
        page = CihazEklePage(
            db=self._db,
            edit_data=data,
            on_saved=self._on_cihaz_saved
        )
        
        self._pages["Cihaz Ekle"] = page
        self.stack.addWidget(page)
        self.stack.setCurrentWidget(page)
        
        marka = data.get("Marka", "")
        model = data.get("Model", "")
        self.page_title.setText(f"Cihaz Düzenle — {marka} {model}")
        self.page_title.setVisible(True)

    def _open_cihaz_detay(self, data):
        """Cihaz detay sayfasını aç."""
        cihaz_id = data.get("Cihazid", "")
        detay_key = f"__cihaz_detay_{cihaz_id}"

        # Eğer zaten açıksa kapat
        if detay_key in self._pages:
            old = self._pages.pop(detay_key)
            self.stack.removeWidget(old)
            old.deleteLater()

        from ui.pages.cihaz.cihaz_detay import CihazDetayPage
        page = CihazDetayPage(
            db=self._db,
            data=data,
            on_saved=self._on_cihaz_saved
        )
        
        # Sinyalleri bağla
        page.back_requested.connect(lambda: self._back_to_cihaz_listesi(detay_key))

        self._pages[detay_key] = page
        self.stack.addWidget(page)
        self.stack.setCurrentWidget(page)
        
        marka = data.get("Marka", "")
        model = data.get("Model", "")
        self.page_title.setText(f"Cihaz Detay — {marka} {model}")
        self.page_title.setVisible(True)

    def _back_to_cihaz_listesi(self, detay_key):
        """Detay sayfasından cihaz listesine geri dön."""
        # Detay sayfasını kapat
        if detay_key in self._pages:
            old = self._pages.pop(detay_key)
            self.stack.removeWidget(old)
            old.deleteLater()
            
        # Listeyi aç
        self._on_menu_clicked("Cihaz", "Cihaz Listesi")

    def open_periodic_maintenance_for_device(self, device_data):
        """Cihaz listesinden periyodik bakım sayfasını açar ve cihazı seçer."""
        cihaz_id = device_data.get("Cihazid", "")
        if not cihaz_id:
            return

        # Periyodik Bakım sayfasını aç veya oluştur
        self._on_menu_clicked("Cihaz", "Periyodik Bakım")

        # Sayfa instance'ını al
        page = self._pages.get("Periyodik Bakım")
        if page and hasattr(page, 'set_cihaz'):
            # Cihazı ayarla
            page.set_cihaz(cihaz_id)
            logger.info(f"Periyodik Bakım sayfası {cihaz_id} için açıldı.")
        else:
            logger.warning("Periyodik Bakım sayfası bulunamadı veya 'set_cihaz' metodu yok.")

    def _delete_cihaz_from_detay(self, cihaz_id, page_key):
        """Detay sayfasından cihaz silme işlemi."""
        try:
            from database.repository_registry import RepositoryRegistry
            registry = RepositoryRegistry(self._db)
            repo = registry.get("Cihazlar")
            repo.delete(cihaz_id)
            
            # Sayfayı kapat ve listeye dön
            self._back_to_cihaz_listesi(page_key)
            
            # Listeyi yenile
            if "Cihaz Listesi" in self._pages:
                self._pages["Cihaz Listesi"].load_data()
                
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.information(self, "Başarılı", "Cihaz silindi.")
            
        except Exception as e:
            logger.error(f"Cihaz silme hatası: {e}")
