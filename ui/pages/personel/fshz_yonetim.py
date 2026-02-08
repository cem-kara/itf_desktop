# -*- coding: utf-8 -*-
import sys
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QTabWidget, QLabel
from PySide6.QtGui import QFont

# Sayfa sınıfları (İskelet korunması için boş tanımlanmıştır, gerçek projede import edilir)
# Proje içi importlar - Mevcut dosya yapınıza göre ayarlandı
from ui.pages.personel.fhsz_yonetim import FHSZYonetimPage
from ui.pages.personel.puantaj_rapor import PuantajRaporPage # PuantajRaporPage yerine projedeki dosya ismi
from database.repository_registry import RepositoryRegistry

class FIILYonetimPaneli(QWidget):
    def __init__(self, db=None):
        super().__init__()
        self._db = db
        # Veritabanı bağlantısını alt sayfalara aktarmak için registry hazırlıyoruz
        self.registry = RepositoryRegistry(self._db) if self._db else None
        
        self.setWindowTitle("FHSZ (Şua) Yönetim Paneli")
        self.resize(1400, 900) # İçerik geniş olduğu için biraz büyütüldü
        
        # W11 Dark Glass Stilini Ana Panele Uyguluyoruz
        self.setStyleSheet("""
            QWidget { background-color: #0f111a; color: #e0e2ea; }
            QTabWidget::pane { border: 1px solid rgba(255,255,255,0.1); background: rgba(30, 32, 44, 0.5); border-radius: 8px; }
            QTabBar::tab {
                background: rgba(41, 43, 65, 0.8);
                border: 1px solid rgba(255,255,255,0.05);
                padding: 10px 25px;
                margin-right: 5px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                color: #8b8fa3;
            }
            QTabBar::tab:selected {
                background: #1d75fe;
                color: white;
                font-weight: bold;
            }
        """)
        
        self.setup_ui()

    def setup_ui(self):
        """Form Elemanlarının Yerleşimi ve Gerçek Sayfa Çağrıları"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)
        
        # Üst Başlık Alanı
        header_layout = QVBoxLayout()
        lbl_baslik = QLabel("FHSZ (Şua) Hakediş ve Raporlama Sistemi")
        lbl_baslik.setFont(QFont("Segoe UI", 20, QFont.Bold))
        lbl_baslik.setStyleSheet("color: #60cdff; background: transparent;")
        
        lbl_alt_baslik = QLabel("Fiili Hizmet Süresi Zammı Hesaplama, Takip ve Puantaj Yönetimi")
        lbl_alt_baslik.setStyleSheet("color: #8b8fa3; background: transparent; font-size: 13px;")
        
        header_layout.addWidget(lbl_baslik)
        header_layout.addWidget(lbl_alt_baslik)
        main_layout.addLayout(header_layout)
        
        # Tab Widget
        self.tabs = QTabWidget()
        
        # --- 1. SEKME: HESAPLAMA SAYFASI (fshz_yonetim.py) ---
        # Sayfaya db nesnesini gönderiyoruz ki kendi içindeki verileri çekebilsin
        self.tab_hesapla = FHSZYonetimPage(db=self._db)
        self.tabs.addTab(self.tab_hesapla, "📝 Hesaplama ve Veri Girişi")
        
        # --- 2. SEKME: RAPORLAMA/PUANTAJ SAYFASI (fshz_puantaj.py) ---
        self.tab_rapor = PuantajRaporPage(db=self._db)
        self.tabs.addTab(self.tab_rapor, "📊 Puantaj Kayıtları ve Raporlar")
        
        main_layout.addWidget(self.tabs)

        # Alt Bilgi Çubuğu
        footer = QLabel("© 2024 İTF Personel Otomasyonu | FHSZ Modülü")
        #footer.setAlignment(Qt.AlignCenter)
        footer.setStyleSheet("color: #45485e; font-size: 11px; margin-top: 5px;")
        main_layout.addWidget(footer)

if __name__ == "__main__":
    # Tek başına çalıştırmak isterseniz
    app = QApplication(sys.argv)
    # Not: Gerçek kullanımda main.py'deki db nesnesini buraya geçmelisiniz
    win = FIILYonetimPaneli(db=None) 
    win.show()
    sys.exit(app.exec())