# -*- coding: utf-8 -*-
"""
Personel 360° Merkez Ekranı
---------------------------
Tek bir personel için tüm süreçlerin yönetildiği ana konteyner.
Yapı:
1. Header: Sabit kişi kartı (Ad, Birim, Durum)
2. Nav: Modül geçiş şeridi (Genel, İzin, Sağlık...)
3. Content: Seçili modülün yüklendiği alan (Lazy load)
4. Right Panel: Kritik bildirimler ve hızlı aksiyonlar
"""
import os
from PySide6.QtWidgets import ( # noqa
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QStackedWidget, QScrollArea, QSizePolicy, QLayout,
    QMessageBox
)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QIcon, QColor, QCursor, QPixmap

from ui.theme_manager import ThemeManager
from core.personel_ozet_servisi import personel_ozet_getir
from core.logger import logger
from ui.components.personel_overview_panel import PersonelOverviewPanel
from ui.components.personel_izin_panel import PersonelIzinPanel
from ui.components.personel_saglik_panel import PersonelSaglikPanel
from ui.components.hizli_izin_giris import HizliIzinGirisDialog
from ui.components.hizli_saglik_giris import HizliSaglikGirisDialog

# Stil tanımları
S = ThemeManager.get_all_component_styles()

class PersonelMerkezPage(QWidget):
    # Sayfa kapatma sinyali
    kapat_istegi = Signal()

    def __init__(self, db, personel_id, parent=None):
        super().__init__(parent)
        self.db = db
        self.personel_id = str(personel_id)
        self.ozet_data = {}
        
        self._initial_load_complete = False
        # Modül cache (açılan sayfaları tekrar oluşturmamak için)
        self.modules = {}
        # İşlem formu referansları
        self._current_form = None
        
        self._setup_ui()
        self._load_data()

    def _setup_ui(self):
        """Ana iskelet kurulumu."""
        self.setStyleSheet(S["page"])
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. HEADER (Sabit Üst Kart)
        self.header_frame = QFrame()
        self.header_frame.setFixedHeight(90)
        self.header_frame.setStyleSheet("background-color: #1e202c; border-bottom: 1px solid #2d303e;")
        header_layout = QHBoxLayout(self.header_frame)
        header_layout.setContentsMargins(24, 12, 24, 12)
        
        # Avatar / İsim Alanı
        self.lbl_avatar = QLabel("👤")
        self.lbl_avatar.setFixedSize(50, 50)
        self.lbl_avatar.setStyleSheet("background: #2d303e; border-radius: 25px; font-size: 24px; qproperty-alignment: AlignCenter;")
        header_layout.addWidget(self.lbl_avatar)
        
        info_layout = QVBoxLayout()
        info_layout.setSpacing(4)
        self.lbl_ad = QLabel("Yükleniyor...")
        self.lbl_ad.setStyleSheet("font-size: 18px; font-weight: bold; color: white;")
        self.lbl_detay = QLabel("...")
        self.lbl_detay.setStyleSheet("color: #8b8fa3; font-size: 13px;")
        info_layout.addWidget(self.lbl_ad)
        info_layout.addWidget(self.lbl_detay)
        header_layout.addLayout(info_layout)
        
        header_layout.addStretch()
        
        # Kapat Butonu
        btn_kapat = QPushButton("✕")
        btn_kapat.setFixedSize(32, 32)
        btn_kapat.setCursor(QCursor(Qt.PointingHandCursor))
        btn_kapat.setStyleSheet("background: transparent; color: #8b8fa3; font-size: 16px; border: none;")
        btn_kapat.clicked.connect(self.kapat_istegi.emit)
        header_layout.addWidget(btn_kapat)
        
        main_layout.addWidget(self.header_frame)

        # 2. BODY (Nav+Content | Sağ Stacked Panel)
        body_layout = QHBoxLayout()
        body_layout.setSpacing(0)
        
        # 2.1 SOL/ORTA: Navigasyon + İçerik
        left_container = QWidget()
        left_layout = QVBoxLayout(left_container)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)
        
        # Navigasyon Şeridi
        self.nav_frame = QFrame()
        self.nav_frame.setFixedHeight(45)
        self.nav_frame.setStyleSheet("background-color: #1a1c28; border-bottom: 1px solid #2d303e;")
        self.nav_layout = QHBoxLayout(self.nav_frame)
        self.nav_layout.setContentsMargins(10, 0, 10, 0)
        self.nav_layout.setSpacing(20)
        
        # Nav Butonları
        self._add_nav_btn("Genel Bakış", "GENEL", True)
        self._add_nav_btn("İzinler", "IZIN")
        self._add_nav_btn("Sağlık Takip", "SAGLIK")
        self._add_nav_btn("İşten Ayrılış", "AYRILIS")
        
        self.nav_layout.addStretch()

        # Geri Butonu
        btn_geri = QPushButton("← Listeye Dön")
        btn_geri.setCursor(QCursor(Qt.PointingHandCursor))
        btn_geri.setStyleSheet(S["back_btn"])
        btn_geri.clicked.connect(self.kapat_istegi.emit)
        self.nav_layout.addWidget(btn_geri)

        left_layout.addWidget(self.nav_frame)
        
        # İçerik Alanı (Stacked)
        self.content_stack = QStackedWidget()
        left_layout.addWidget(self.content_stack)
        
        body_layout.addWidget(left_container, 1) # Esnek genişlik
        
        # 2.2 SAĞ: Stacked Panel (Durum Özeti | İşlem Formu)
        self.right_panel_stack = QStackedWidget()
        self.right_panel_stack.setFixedWidth(380)
        
        # Sayfa 0: Durum Özeti + Hızlı İşlemler
        overview_page = QFrame()
        overview_page.setStyleSheet("background-color: #1a1c28; border-left: 1px solid #2d303e;")
        overview_layout = QVBoxLayout(overview_page)
        overview_layout.setContentsMargins(16, 20, 16, 20)
        overview_layout.setSpacing(15)
        
        # Başlık
        lbl_sag_baslik = QLabel("DURUM ÖZETİ")
        lbl_sag_baslik.setStyleSheet("color: #6bd3ff; font-weight: bold; font-size: 12px; letter-spacing: 1px;")
        overview_layout.addWidget(lbl_sag_baslik)
        
        # Kritik Uyarılar Listesi
        self.alert_container = QVBoxLayout()
        overview_layout.addLayout(self.alert_container)
        
        # Hızlı Aksiyonlar
        overview_layout.addSpacing(20)
        lbl_aksiyon = QLabel("HIZLI İŞLEMLER")
        lbl_aksiyon.setStyleSheet("color: #6bd3ff; font-weight: bold; font-size: 12px; letter-spacing: 1px;")
        overview_layout.addWidget(lbl_aksiyon)
        
        self._add_action_btn(overview_layout, "➕ İzin Ekle", lambda: self._show_islem_panel("IZIN"))
        self._add_action_btn(overview_layout, "🩺 Muayene Ekle", lambda: self._show_islem_panel("SAGLIK"))
        
        overview_layout.addStretch()
        
        self.right_panel_stack.addWidget(overview_page)  # Page 0
        
        # Sayfa 1: İşlem Formu (dinamik olarak yüklenir)
        form_page = QFrame()
        form_page.setStyleSheet("background-color: #1a1c28; border-left: 1px solid #2d303e;")
        self.form_layout = QVBoxLayout(form_page)
        self.form_layout.setContentsMargins(10, 10, 10, 10)
        self.form_layout.setSpacing(10)
        
        # Kapat butonunu form sayfasına ekle
        header_h = QHBoxLayout()
        self.lbl_form_title = QLabel("İşlem")
        self.lbl_form_title.setStyleSheet("color: #6bd3ff; font-weight: bold; font-size: 12px;")
        header_h.addWidget(self.lbl_form_title)
        header_h.addStretch()
        
        btn_form_kapat = QPushButton("✕")
        btn_form_kapat.setFixedSize(28, 28)
        btn_form_kapat.setCursor(QCursor(Qt.PointingHandCursor))
        btn_form_kapat.setStyleSheet("background: transparent; color: #8b8fa3; border: none;")
        btn_form_kapat.clicked.connect(lambda: self.right_panel_stack.setCurrentIndex(0))
        header_h.addWidget(btn_form_kapat)
        
        self.form_layout.addLayout(header_h)
        self.form_layout.addSpacing(10)
        
        self.right_panel_stack.addWidget(form_page)  # Page 1
        
        body_layout.addWidget(self.right_panel_stack)
        main_layout.addLayout(body_layout)

    def _add_nav_btn(self, text, code, active=False):
        btn = QPushButton(text)
        btn.setCursor(QCursor(Qt.PointingHandCursor))
        # Alt çizgi efekti için stil
        base_style = """
            QPushButton {
                background: transparent; border: none; 
                color: #8b8fa3; font-weight: bold; font-size: 13px;
                border-bottom: 3px solid transparent;
                padding: 10px;
            }
            QPushButton:hover { color: #e0e2ea; }
        """
        active_style = """
            QPushButton {
                background: transparent; border: none; 
                color: #3b82f6; font-weight: bold; font-size: 13px;
                border-bottom: 3px solid #3b82f6;
                padding: 10px;
            }
        """
        btn.setStyleSheet(active_style if active else base_style)
        btn.clicked.connect(lambda: self._switch_tab(code, btn))
        self.nav_layout.addWidget(btn)
        
        # Butonu sakla ki stilini değiştirebilelim
        if not hasattr(self, "nav_btns"):
            self.nav_btns = {}
        self.nav_btns[code] = btn

    def _add_action_btn(self, layout, text, callback):
        btn = QPushButton(text)
        btn.setCursor(QCursor(Qt.PointingHandCursor))
        btn.setStyleSheet("""
            QPushButton {
                background-color: #2d303e; color: #e0e2ea; border: 1px solid #3f4252;
                border-radius: 6px; padding: 8px; text-align: left;
            }
            QPushButton:hover { background-color: #363949; border-color: #555; }
        """)
        btn.clicked.connect(callback)
        layout.addWidget(btn)

    def _show_islem_panel(self, panel_type):
        """Sağ panelinde işlem formunu göster."""
        if not self.ozet_data.get("personel"):
            QMessageBox.warning(self, "Hata", "Personel verisi yüklenemedi.")
            return
        
        # Önceki form temizle
        while self.form_layout.count() > 2:  # Header ve spacing hariç
            item = self.form_layout.takeAt(2)
            if item.widget():
                item.widget().deleteLater()
        
        # Panel tipine göre uygun form yükle
        try:
            if panel_type == "IZIN":
                self.lbl_form_title.setText("➕ İzin Giriş")
                # HızlıIzinGirisDialog'unu widget'a embed et
                form = HizliIzinGirisDialog(self.db, self.ozet_data["personel"], parent=self)
                form.izin_kaydedildi.connect(self._on_form_saved)
                form.cancelled.connect(lambda: self.right_panel_stack.setCurrentIndex(0))
                self.form_layout.addWidget(form, 1)
                self._current_form = form
            
            elif panel_type == "SAGLIK":
                self.lbl_form_title.setText("🩺 Muayene Giriş")
                # HızlıSaglikGirisDialog'unu widget'a embed et
                form = HizliSaglikGirisDialog(self.db, self.ozet_data["personel"], parent=self)
                form.saglik_kaydedildi.connect(self._on_form_saved)
                form.cancelled.connect(lambda: self.right_panel_stack.setCurrentIndex(0))
                self.form_layout.addWidget(form, 1)
                self._current_form = form
        
        except Exception as e:
            logger.error(f"Form yükleme hatası ({panel_type}): {e}")
            QMessageBox.critical(self, "Hata", f"Form yüklenemedi: {e}")
            return
        
        # Sayfa 1'e geç (İşlem Formu)
        self.right_panel_stack.setCurrentIndex(1)
    
    def _on_form_saved(self):
        """Form'da veri kaydedildiğinde çağrılır."""
        self._load_data()
        # Sayfa 0'a geri dön (Durum Özeti)
        self.right_panel_stack.setCurrentIndex(0)

    def _load_data(self):
        """Verileri servisten çek ve UI güncelle."""
        try:
            self.ozet_data = personel_ozet_getir(self.db, self.personel_id)
            p = self.ozet_data.get("personel")
            
            if p:
                ad = f"{p.get('AdSoyad', 'İsimsiz')}"
                unvan = p.get("Unvan", "") or ""
                birim = p.get("GorevYeri", "") or ""
                tc = p.get("KimlikNo", "")
                
                self.lbl_ad.setText(ad)
                self.lbl_detay.setText(f"{unvan} • {birim} • {tc}")

                # Avatar / Resim Yükleme
                resim_path = str(p.get("Resim", "")).strip()
                if resim_path and os.path.exists(resim_path):
                    pixmap = QPixmap(resim_path)
                    if not pixmap.isNull():
                        self.lbl_avatar.setPixmap(pixmap.scaled(50, 50, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                        self.lbl_avatar.setText("")
                else:
                    self.lbl_avatar.setText("👤")
                    self.lbl_avatar.setPixmap(QPixmap())
            
            # Sağ panel uyarıları
            # Önce temizle
            while self.alert_container.count():
                item = self.alert_container.takeAt(0)
                if item.widget(): item.widget().deleteLater()
            
            kritikler = self.ozet_data.get("kritikler", [])
            if not kritikler:
                lbl = QLabel("Kritik durum yok.")
                lbl.setStyleSheet("color: #666; font-style: italic;")
                self.alert_container.addWidget(lbl)
            else:
                for msg in kritikler:
                    lbl = QLabel(f"⚠️ {msg}")
                    lbl.setStyleSheet("color: #f59e0b; background: rgba(245, 158, 11, 0.1); padding: 8px; border-radius: 4px;")
                    lbl.setWordWrap(True)
                    self.alert_container.addWidget(lbl)
                    
            # Eğer ilk yükleme değilse, mevcut modülü yenile.
            # İlk yüklemede ise varsayılan sekmeyi aç.
            if self._initial_load_complete:
                current_module = self.content_stack.currentWidget()
                if current_module and hasattr(current_module, "load_data"):
                    current_module.load_data()
            else:
                self._switch_tab("GENEL")
                self._initial_load_complete = True

        except Exception as e:
            logger.error(f"Personel merkez veri yükleme hatası: {e}")

    def _switch_tab(self, code, sender_btn=None):
        # 1. Navigasyon stilini güncelle
        for key, btn in self.nav_btns.items():
            is_active = (key == code)
            # Stil stringlerini tekrar tanımlamak yerine basit replace yapabiliriz veya yukarıdaki sabitleri kullanabiliriz
            # Basitlik için rengi değiştiriyoruz
            color = "#3b82f6" if is_active else "#8b8fa3"
            border = f"3px solid {color}" if is_active else "3px solid transparent"
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: transparent; border: none; 
                    color: {color}; font-weight: bold; font-size: 13px;
                    border-bottom: {border}; padding: 0 10px;
                }}
                QPushButton:hover {{ color: #e0e2ea; }}
            """)

        # 2. İçeriği Yükle (Lazy Load)
        if code not in self.modules:
            widget = self._create_module_widget(code)
            self.modules[code] = widget
            self.content_stack.addWidget(widget)
        
        self.content_stack.setCurrentWidget(self.modules[code])

    def _create_module_widget(self, code):
        """İstenen modülü oluşturur."""
        if code == "GENEL":
            # DB bağlantısını panele geçiriyoruz
            return PersonelOverviewPanel(self.ozet_data, self.db)
            
        widget = None
        try:
            if code == "IZIN":
                widget = PersonelIzinPanel(self.db, self.personel_id)
                # Eğer sayfa destekliyorsa sadece bu personeli filtrele
            
            elif code == "SAGLIK":
                widget = PersonelSaglikPanel(self.db, self.personel_id)
            
            elif code == "AYRILIS":
                from ui.pages.personel.isten_ayrilik import IstenAyrilikPage
                # İşten ayrılık sayfası genelde personel_data ister
                p_data = self.ozet_data.get("personel", {})
                widget = IstenAyrilikPage(self.db, personel_data=p_data)

        except Exception as e:
            logger.error(f"Modül yükleme hatası ({code}): {e}")
            lbl = QLabel(f"Modül yüklenemedi: {code}\n{e}")
            lbl.setStyleSheet("color: #ef4444;")
            lbl.setAlignment(Qt.AlignCenter)
            return lbl

        if widget:
            # Gömülü mod desteği varsa aktif et (başlıkları gizle vb.)
            if hasattr(widget, "set_embedded_mode"):
                widget.set_embedded_mode(True)
            return widget
        
        return QLabel(f"Modül Bulunamadı: {code}")