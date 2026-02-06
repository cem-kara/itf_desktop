# -*- coding: utf-8 -*-
import sys
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
    QTableWidget, QTableWidgetItem, QHeaderView, 
    QPushButton, QLabel, QComboBox, QFrame, QAbstractItemView,
    QProgressBar, QGroupBox
)
from PySide6.QtCore import Qt

class PuantajRaporPenceresi(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Puantaj Raporlama ve Şua Takip Sistemi")
        self.resize(1280, 800)
        self.setup_ui()
        
    def setup_ui(self):
        """Form Elemanlarının Yerleşimi (Saf UI)"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # --- 1. FİLTRE PANELİ ---
        grp_filtre = QGroupBox("Rapor Filtreleri")
        filter_layout = QHBoxLayout(grp_filtre)
        filter_layout.setContentsMargins(20, 25, 20, 15) 
        filter_layout.setSpacing(20)

        # Yıl Seçimi
        vbox_yil = QVBoxLayout(); vbox_yil.setSpacing(5)
        vbox_yil.addWidget(QLabel("Rapor Yılı:"))
        self.cmb_yil = QComboBox()
        self.cmb_yil.setFixedWidth(100)
        vbox_yil.addWidget(self.cmb_yil)
        filter_layout.addLayout(vbox_yil)

        # Dönem Seçimi
        vbox_donem = QVBoxLayout(); vbox_donem.setSpacing(5)
        vbox_donem.addWidget(QLabel("Dönem / Ay:"))
        self.cmb_donem = QComboBox()
        self.cmb_donem.setFixedWidth(140)
        vbox_donem.addWidget(self.cmb_donem)
        filter_layout.addLayout(vbox_donem)

        filter_layout.addStretch()

        # Rapor Oluştur Butonu
        self.btn_getir = QPushButton(" Raporu Oluştur")
        self.btn_getir.setMinimumHeight(40)
        filter_layout.addWidget(self.btn_getir)

        main_layout.addWidget(grp_filtre)

        # --- 2. TABLO BİLGİ VE GÖVDE ---
        self.lbl_bilgi = QLabel("Veri bekleniyor...")
        self.lbl_bilgi.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        main_layout.addWidget(self.lbl_bilgi)

        self.sutunlar = ["ID", "Ad Soyad", "Yıl", "Dönem", "Top. Gün", "Top. İzin", "Yıllık Fiili Saat", "Kümülatif Saat", "Hak Edilen Şua"]
        self.tablo = QTableWidget()
        self.tablo.setColumnCount(len(self.sutunlar))
        self.tablo.setHorizontalHeaderLabels(self.sutunlar)
        self.tablo.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tablo.verticalHeader().setVisible(False)
        self.tablo.setAlternatingRowColors(True)
        self.tablo.setSelectionBehavior(QAbstractItemView.SelectRows)
        
        main_layout.addWidget(self.tablo)

        # --- 3. ALT PANEL (Aksiyonlar) ---
        bottom_layout = QHBoxLayout()
        
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        self.progress.setFixedWidth(200)
        bottom_layout.addWidget(self.progress)

        btn_kapat = QPushButton(" Çıkış")
        btn_kapat.setFixedSize(100, 45)
        bottom_layout.addWidget(btn_kapat)
        
        bottom_layout.addStretch()

        self.btn_excel = QPushButton(" Excel İndir")
        self.btn_excel.setFixedSize(140, 45)
        bottom_layout.addWidget(self.btn_excel)

        self.btn_pdf = QPushButton(" PDF İndir")
        self.btn_pdf.setFixedSize(140, 45)
        bottom_layout.addWidget(self.btn_pdf)

        main_layout.addLayout(bottom_layout)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = PuantajRaporPenceresi()
    win.show()
    sys.exit(app.exec())