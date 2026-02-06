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

class IzinGirisPenceresi(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Personel İzin Takip ve Giriş")
        self.resize(1350, 850)
        self.ui = {}
        self._setup_ui()

    def _setup_ui(self):
        main_layout = QHBoxLayout(self)
        
        # --- SOL TARAF (Giriş ve Bakiye) ---
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)

        # 1. GİRİŞ KUTUSU
        grp_giris = QGroupBox("İzin Giriş / Düzenleme")
        form_layout = QGridLayout(grp_giris)
        form_layout.setSpacing(10)

        self.txt_id = QLineEdit()
        self.txt_id.setVisible(False)

        self.ui['sinif'] = QComboBox()
        self._add_field(form_layout, 0, "Hizmet Sınıfı:", self.ui['sinif'])
        
        self.ui['personel'] = QComboBox()
        self.ui['personel'].setEditable(True)
        self._add_field(form_layout, 1, "Personel:", self.ui['personel'])

        self.ui['izin_tipi'] = QComboBox()
        self._add_field(form_layout, 2, "İzin Tipi:", self.ui['izin_tipi'])

        h_tarih = QHBoxLayout()
        self.ui['baslama'] = QDateEdit(QDate.currentDate())
        self.ui['baslama'].setCalendarPopup(True)
        self.ui['baslama'].setDisplayFormat("dd.MM.yyyy")
        self.ui['gun'] = QSpinBox()
        self.ui['gun'].setRange(1, 365)
        h_tarih.addWidget(self.ui['baslama'])
        h_tarih.addWidget(QLabel(" Gün:"))
        h_tarih.addWidget(self.ui['gun'])
        
        form_layout.addWidget(QLabel("Başlama / Süre:"), 3, 0)
        form_layout.addLayout(h_tarih, 3, 1)

        self.ui['bitis'] = QDateEdit()
        self.ui['bitis'].setReadOnly(True)
        self.ui['bitis'].setDisplayFormat("dd.MM.yyyy")
        self.ui['bitis'].setButtonSymbols(QAbstractSpinBox.NoButtons)
        self._add_field(form_layout, 4, "Bitiş (İşe Başlama):", self.ui['bitis'])

        h_btn = QHBoxLayout()
        self.btn_temizle = QPushButton("Yeni Kayıt")
        self.btn_kaydet = QPushButton("KAYDET")
        h_btn.addWidget(self.btn_temizle)
        h_btn.addWidget(self.btn_kaydet)
        form_layout.addLayout(h_btn, 5, 0, 1, 2)

        left_layout.addWidget(grp_giris)

        # 2. BAKİYE PANOSU
        grp_bilgi = QGroupBox("Personel İzin Durumu")
        bilgi_grid = QGridLayout(grp_bilgi)
        bilgi_grid.setVerticalSpacing(5)
        
        bilgi_grid.addWidget(QLabel("<b>YILLIK İZİN</b>"), 0, 0, 1, 2, Qt.AlignCenter)
        self.lbl_yillik_devir = self._add_stat(bilgi_grid, 1, "Devir:")
        self.lbl_yillik_hak = self._add_stat(bilgi_grid, 2, "Hakediş:")
        bilgi_grid.addWidget(self._hl(), 3, 0, 1, 2)
        self.lbl_yillik_kul = self._add_stat(bilgi_grid, 4, "Kullanılan:")
        self.lbl_yillik_kal = self._add_stat(bilgi_grid, 5, "KALAN:")
        
        bilgi_grid.addWidget(self._hl(), 6, 0, 1, 2)
        bilgi_grid.addWidget(QLabel("<b>ŞUA İZNİ</b>"), 7, 0, 1, 2, Qt.AlignCenter)
        self.lbl_sua_hak = self._add_stat(bilgi_grid, 8, "Hakediş:")
        self.lbl_sua_kul = self._add_stat(bilgi_grid, 9, "Kullanılan:")
        self.lbl_sua_kal = self._add_stat(bilgi_grid, 10, "KALAN:")
        
        bilgi_grid.addWidget(self._hl(), 11, 0, 1, 2)
        self.lbl_diger_top = self._add_stat(bilgi_grid, 12, "Rapor/Mazeret:")

        left_layout.addWidget(grp_bilgi)
        left_layout.addStretch()

        # --- SAĞ TARAF (LİSTE) ---
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)

        grp_genel = QGroupBox("Tüm Personel İzin Listesi")
        v_genel = QVBoxLayout(grp_genel)

        h_fil = QHBoxLayout()
        self.cmb_yil = QComboBox()
        self.cmb_yil.addItems(["Tümü"])
        self.cmb_ay = QComboBox()
        self.cmb_ay.addItems(["Tümü"])
        
        h_fil.addWidget(QLabel("Yıl:"))
        h_fil.addWidget(self.cmb_yil)
        h_fil.addWidget(QLabel("Ay:"))
        h_fil.addWidget(self.cmb_ay)
        h_fil.addStretch()
        v_genel.addLayout(h_fil)

        self.table_genel = QTableWidget()
        self.table_genel.setColumnCount(7)
        self.table_genel.setHorizontalHeaderLabels(["TC", "Ad Soyad", "İzin Tipi", "Başlama", "Gün", "Bitiş", "Durum"])
        self.table_genel.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table_genel.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_genel.setEditTriggers(QAbstractItemView.NoEditTriggers)
        
        v_genel.addWidget(self.table_genel)
        right_layout.addWidget(grp_genel)

        # Splitter
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)
        main_layout.addWidget(splitter)
        
        self.progress = QProgressBar(self)
        self.progress.setVisible(False)
        self.progress.setFixedHeight(3)

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
    win = IzinGirisPenceresi()
    win.show()
    sys.exit(app.exec())