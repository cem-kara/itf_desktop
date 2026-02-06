# -*- coding: utf-8 -*-
import sys
from PySide6.QtCore import Qt, QDate
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QTableWidget, QTableWidgetItem, QHeaderView, QComboBox, 
    QDateEdit, QSpinBox, QFrame, QAbstractItemView,
    QGroupBox, QSplitter, QLineEdit, QAbstractSpinBox, 
    QProgressBar, QGridLayout, QApplication
)

class IzinTakipPenceresi(QWidget):
    def __init__(self, personel_data=None):
        super().__init__()
        # Yerleşimi ve boyutları koru
        self.setWindowTitle("İzin Takip Paneli")
        self.resize(1100, 650)
        self.ui = {}

        self._setup_ui()

    def _setup_ui(self):
        """Form Elemanlarının Yerleşimi (Saf UI)"""
        main_layout = QHBoxLayout(self)
        
        # --- SOL TARAF (Giriş ve Bakiye) ---
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)

        # 1. GİRİŞ KUTUSU
        grp_giris = QGroupBox("Yeni İzin Girişi")
        form_layout = QGridLayout(grp_giris)
        form_layout.setSpacing(10)

        self.ui['izin_tipi'] = QComboBox()
        self._add_field(form_layout, 0, "İzin Tipi:", self.ui['izin_tipi'])

        h_tarih = QHBoxLayout()
        self.ui['baslama'] = QDateEdit(QDate.currentDate())
        self.ui['baslama'].setCalendarPopup(True)
        self.ui['baslama'].setDisplayFormat("dd.MM.yyyy")
        
        self.ui['gun'] = QSpinBox()
        self.ui['gun'].setRange(1, 365)
        self.ui['gun'].setValue(1)
        
        h_tarih.addWidget(self.ui['baslama'])
        h_tarih.addWidget(QLabel(" Gün:"))
        h_tarih.addWidget(self.ui['gun'])
        
        form_layout.addWidget(QLabel("Başlama / Süre:"), 1, 0)
        form_layout.addLayout(h_tarih, 1, 1)

        self.ui['bitis'] = QDateEdit()
        self.ui['bitis'].setReadOnly(True)
        self.ui['bitis'].setDisplayFormat("dd.MM.yyyy")
        self.ui['bitis'].setButtonSymbols(QAbstractSpinBox.NoButtons)
        self._add_field(form_layout, 2, "Bitiş (İşe Başlama):", self.ui['bitis'])

        self.btn_kaydet = QPushButton("KAYDET")
        self.btn_kaydet.setFixedHeight(35)
        form_layout.addWidget(self.btn_kaydet, 3, 0, 1, 2)

        left_layout.addWidget(grp_giris)

        # 2. BAKİYE PANOSU
        grp_bilgi = QGroupBox("İzin Bakiyesi")
        bilgi_grid = QGridLayout(grp_bilgi)
        bilgi_grid.setVerticalSpacing(5)
        
        # Yıllık Bölümü
        bilgi_grid.addWidget(QLabel("<b>YILLIK İZİN</b>"), 0, 0, 1, 2, Qt.AlignCenter)
        self.lbl_yillik_devir = self._add_stat(bilgi_grid, 1, "Devir:")
        self.lbl_yillik_hak = self._add_stat(bilgi_grid, 2, "Hakediş:")
        bilgi_grid.addWidget(self._hl(), 3, 0, 1, 2)
        self.lbl_yillik_kul = self._add_stat(bilgi_grid, 4, "Kullanılan:")
        self.lbl_yillik_kal = self._add_stat(bilgi_grid, 5, "KALAN:")
        
        # Şua Bölümü
        bilgi_grid.addWidget(self._hl(), 6, 0, 1, 2)
        bilgi_grid.addWidget(QLabel("<b>ŞUA İZNİ</b>"), 7, 0, 1, 2, Qt.AlignCenter)
        self.lbl_sua_hak = self._add_stat(bilgi_grid, 8, "Hakediş:")
        self.lbl_sua_kul = self._add_stat(bilgi_grid, 9, "Kullanılan:")
        self.lbl_sua_kal = self._add_stat(bilgi_grid, 10, "KALAN:")
        
        # Diğer
        bilgi_grid.addWidget(self._hl(), 11, 0, 1, 2)
        self.lbl_diger_top = self._add_stat(bilgi_grid, 12, "Rapor/Mazeret:")

        left_layout.addWidget(grp_bilgi)
        left_layout.addStretch()

        # --- SAĞ TARAF (GEÇMİŞ) ---
        right_widget = QGroupBox("İzin Geçmişi")
        right_layout = QVBoxLayout(right_widget)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["Id", "İzin Tipi", "Başlama", "Bitiş", "Gün", "Durum"])
        self.table.setColumnHidden(0, True) 
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        
        right_layout.addWidget(self.table)

        # Splitter (1:2 oranını koru)
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        main_layout.addWidget(splitter)
        
        self.progress = QProgressBar(self)
        self.progress.setVisible(False)
        self.progress.setFixedHeight(3)

    # --- UI YARDIMCILARI ---
    def _add_field(self, layout, row, text, widget):
        layout.addWidget(QLabel(text), row, 0)
        layout.addWidget(widget, row, 1)

    def _add_stat(self, grid, row, text):
        lbl_t = QLabel(text)
        lbl_v = QLabel("-")
        lbl_v.setAlignment(Qt.AlignRight)
        grid.addWidget(lbl_t, row, 0)
        grid.addWidget(lbl_v, row, 1)
        return lbl_v

    def _hl(self):
        f = QFrame()
        f.setFrameShape(QFrame.HLine)
        f.setFrameShadow(QFrame.Sunken)
        return f

if __name__ == "__main__":
    app = QApplication(sys.argv)
    # Varsayılan test verisi
    win = IzinTakipPenceresi()
    win.show()
    sys.exit(app.exec())