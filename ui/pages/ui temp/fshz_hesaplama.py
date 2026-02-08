# -*- coding: utf-8 -*-
import sys
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, 
    QTableWidgetItem, QHeaderView, QPushButton, QLabel, 
    QComboBox, QFrame, QAbstractItemView, QProgressBar, QGroupBox
)
from PySide6.QtCore import Qt

class FHSZHesaplamaPenceresi(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FHSZ (Şua) Hesaplama ve Düzenleme")
        self.resize(1250, 800)
        
        self.setup_ui()

    def setup_ui(self):
        """Form Elemanlarının Yerleşimi (Saf UI)"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)
        
        # --- 1. FİLTRE PANELİ ---
        filter_grp = QGroupBox("Dönem Seçimi")
        hl = QHBoxLayout(filter_grp)
        hl.setContentsMargins(20, 25, 20, 15)
        hl.setSpacing(15)
        
        hl.addWidget(QLabel("Yıl:"))
        self.cmb_yil = QComboBox()
        self.cmb_yil.setFixedWidth(100)
        hl.addWidget(self.cmb_yil)
        
        hl.addWidget(QLabel("Ay:"))
        self.cmb_ay = QComboBox()
        self.cmb_ay.setFixedWidth(140)
        hl.addWidget(self.cmb_ay)
        
        self.lbl_donem = QLabel("Dönem: --.--.---- - --.--.----")
        hl.addWidget(self.lbl_donem)
        hl.addStretch()
        
        self.btn_hesapla = QPushButton("⚡ LİSTELE VE HESAPLA")
        self.btn_hesapla.setMinimumHeight(40)
        hl.addWidget(self.btn_hesapla)
        main_layout.addWidget(filter_grp)

        # --- 2. VERİ TABLOSU ---
        self.cols = ["Kimlik No", "Adı Soyadı", "Birim", "Çalışma Koşulu", "Ait Yıl", "Dönem", "Aylık Gün", "Kullanılan İzin", "Fiili Çalışma (Saat)"]
        self.tablo = QTableWidget()
        self.tablo.setColumnCount(len(self.cols))
        self.tablo.setHorizontalHeaderLabels(self.cols)
        self.tablo.verticalHeader().setVisible(False)
        self.tablo.setAlternatingRowColors(True)
        self.tablo.setSelectionBehavior(QAbstractItemView.SelectRows)
        
        h = self.tablo.horizontalHeader()
        h.setSectionResizeMode(QHeaderView.Stretch)
        # Orijinal genişlik tanımlamaları korundu
        h.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        h.setSectionResizeMode(3, QHeaderView.Fixed)
        self.tablo.setColumnWidth(3, 160)
        h.setSectionResizeMode(8, QHeaderView.Fixed)
        self.tablo.setColumnWidth(8, 120)
        
        main_layout.addWidget(self.tablo)
        
        # --- 3. ALT BAR (Durum ve Aksiyonlar) ---
        fl = QHBoxLayout()
        self.lbl_durum = QLabel("Hazır")
        fl.addWidget(self.lbl_durum)
        fl.addStretch()
        
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        self.progress.setFixedWidth(200)
        fl.addWidget(self.progress)
        
        btn_kapat = QPushButton("Kapat")
        btn_kapat.setFixedSize(100, 40)
        fl.addWidget(btn_kapat)
        
        self.btn_kaydet = QPushButton("💾 KAYDET / GÜNCELLE")
        self.btn_kaydet.setFixedWidth(220)
        self.btn_kaydet.setFixedHeight(40)
        fl.addWidget(self.btn_kaydet)
        
        main_layout.addLayout(fl)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = FHSZHesaplamaPenceresi()
    win.show()
    sys.exit(app.exec())