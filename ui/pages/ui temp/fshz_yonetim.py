# -*- coding: utf-8 -*-
import sys
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QTabWidget, QLabel
from PySide6.QtGui import QFont

# Sayfa sınıfları (İskelet korunması için boş tanımlanmıştır, gerçek projede import edilir)
class FHSZHesaplamaPenceresi(QWidget): 
    def __init__(self): super().__init__()

class PuantajRaporPenceresi(QWidget): 
    def __init__(self): super().__init__()

class FHSZYonetimPaneli(QWidget):
    def __init__(self, yetki='viewer', kullanici_adi=None):
        super().__init__()
                
        self.setWindowTitle("FHSZ (Şua) Yönetim Paneli")
        self.resize(1300, 850)
        
        self.setup_ui()

    def setup_ui(self):
        """Form Elemanlarının Yerleşimi ve Sayfa Çağrıları"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(10)
        
        # Başlık
        lbl_baslik = QLabel("FHSZ (Şua) Hakediş ve Raporlama Sistemi")
        lbl_baslik.setFont(QFont("Segoe UI", 18, QFont.Bold))
        main_layout.addWidget(lbl_baslik)
        
        # Tab Widget
        self.tabs = QTabWidget()
        
        # --- 1. SEKME: HESAPLAMA SAYFASI ---
        self.tab_hesapla = FHSZHesaplamaPenceresi(self.yetki, self.kullanici_adi)
        self.tabs.addTab(self.tab_hesapla, "📝 Hesaplama ve Veri Girişi")
        
        # --- 2. SEKME: RAPORLAMA SAYFASI ---
        self.tab_rapor = PuantajRaporPenceresi(self.yetki, self.kullanici_adi)
        self.tabs.addTab(self.tab_rapor, "📊 Raporlar ve Analiz")
        
        main_layout.addWidget(self.tabs)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = FHSZYonetimPaneli()
    win.show()
    sys.exit(app.exec())