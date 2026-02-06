# -*- coding: utf-8 -*-
import sys
from PySide6.QtCore import Qt, QDate
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QScrollArea, QProgressBar, QFrame, QComboBox, QLineEdit, 
    QDateEdit, QApplication, QGroupBox, QBoxLayout
)

class PersonelEklePenceresi(QWidget):
    def __init__(self): 
        super().__init__()
        self.setWindowTitle("Yeni Personel Ekle")
        self.setMinimumSize(1200, 800)
        self.resize(1400, 900)
        self.ui = {} 

        self._setup_ui()

    def _setup_ui(self):
        """Form Elemanlarının Yerleşimi (Saf UI)"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)

        # Scroll Area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        
        content_widget = QWidget()
        content_layout = QHBoxLayout(content_widget)
        content_layout.setSpacing(25)
        content_layout.setContentsMargins(10, 10, 10, 10)

        # --- SOL SÜTUN ---
        left_column = QWidget()
        left_layout = QVBoxLayout(left_column)
        left_layout.setSpacing(20)

        # Fotoğraf Bölümü
        photo_grp = QGroupBox("Fotoğraf")
        photo_lay = QVBoxLayout(photo_grp)
        photo_lay.setAlignment(Qt.AlignCenter)
        self.lbl_resim_onizleme = QLabel("Fotoğraf\nYüklenmedi")
        self.lbl_resim_onizleme.setFixedSize(180, 220)
        self.lbl_resim_onizleme.setAlignment(Qt.AlignCenter)
        btn_resim = QPushButton("📷 Fotoğraf Seç")
        btn_resim.setMinimumHeight(40)
        photo_lay.addWidget(self.lbl_resim_onizleme)
        photo_lay.addWidget(btn_resim)
        left_layout.addWidget(photo_grp)

        # Kimlik Bilgileri
        id_grp = QGroupBox("Kimlik Bilgileri")
        id_lay = QVBoxLayout(id_grp)
        row_id_1 = QHBoxLayout()
        self.ui['tc'] = QLineEdit()
        self.ui['ad_soyad'] = QLineEdit()
        self._add_v_field(row_id_1, "TC Kimlik No (*)", self.ui['tc'])
        self._add_v_field(row_id_1, "Ad Soyad (*)", self.ui['ad_soyad'])
        id_lay.addLayout(row_id_1)
        
        row_id_2 = QHBoxLayout()
        self.ui['dogum_yeri'] = QComboBox()
        self.ui['dogum_tarihi'] = QDateEdit()
        self.ui['dogum_tarihi'].setCalendarPopup(True)
        self._add_v_field(row_id_2, "Doğum Yeri", self.ui['dogum_yeri'])
        self._add_v_field(row_id_2, "Doğum Tarihi", self.ui['dogum_tarihi'])
        id_lay.addLayout(row_id_2)
        left_layout.addWidget(id_grp)

        # İletişim Bilgileri
        contact_grp = QGroupBox("İletişim Bilgileri")
        contact_lay = QVBoxLayout(contact_grp)
        row_contact = QHBoxLayout()
        self.ui['cep_tel'] = QLineEdit()
        self.ui['eposta'] = QLineEdit()
        self._add_v_field(row_contact, "Cep Telefonu", self.ui['cep_tel'])
        self._add_v_field(row_contact, "E-Posta Adresi", self.ui['eposta'])
        contact_lay.addLayout(row_contact)
        left_layout.addWidget(contact_grp)
        left_layout.addStretch()

        # --- SAĞ SÜTUN ---
        right_column = QWidget()
        right_layout = QVBoxLayout(right_column)
        right_layout.setSpacing(20)

        # Kurumsal Bilgiler
        corp_grp = QGroupBox("Kadro ve Kurumsal Bilgiler")
        corp_lay = QVBoxLayout(corp_grp)
        row_corp_1 = QHBoxLayout()
        self.ui['hizmet_sinifi'] = QComboBox()
        self.ui['kadro_unvani'] = QComboBox()
        self._add_v_field(row_corp_1, "Hizmet Sınıfı (*)", self.ui['hizmet_sinifi'])
        self._add_v_field(row_corp_1, "Kadro Ünvanı (*)", self.ui['kadro_unvani'])
        corp_lay.addLayout(row_corp_1)
        
        row_corp_2 = QHBoxLayout()
        self.ui['gorev_yeri'] = QComboBox()
        self.ui['sicil_no'] = QLineEdit()
        self._add_v_field(row_corp_2, "Görev Yeri", self.ui['gorev_yeri'])
        self._add_v_field(row_corp_2, "Kurum Sicil No", self.ui['sicil_no'])
        corp_lay.addLayout(row_corp_2)
        
        self.ui['baslama_tarihi'] = QDateEdit()
        self.ui['baslama_tarihi'].setCalendarPopup(True)
        self._add_v_field(corp_lay, "Memuriyete Başlama Tarihi", self.ui['baslama_tarihi'])
        right_layout.addWidget(corp_grp)

        # Eğitim Bilgileri
        edu_grp = QGroupBox("Eğitim Bilgileri")
        edu_main_lay = QHBoxLayout(edu_grp)
        
        # Okul 1 ve Okul 2
        for i in ["1", "2"]:
            v_lay = QVBoxLayout()
            self.ui[f'okul{i}'] = QComboBox(editable=True)
            self.ui[f'fakulte{i}'] = QComboBox(editable=True)
            self.ui[f'mezun_tarihi{i}'] = QLineEdit()
            self.ui[f'diploma_no{i}'] = QLineEdit()
            btn_dip = QPushButton(f"📄 Diploma {i} Seç")
            self._add_v_field(v_lay, "Okul Adı", self.ui[f'okul{i}'])
            self._add_v_field(v_lay, "Bölüm/Fakülte", self.ui[f'fakulte{i}'])
            self._add_v_field(v_lay, "Mezuniyet Tarihi", self.ui[f'mezun_tarihi{i}'])
            self._add_v_field(v_lay, "Diploma No", self.ui[f'diploma_no{i}'])
            v_lay.addWidget(btn_dip)
            edu_main_lay.addLayout(v_lay)
            if i == "1":
                sep = QFrame(); sep.setFrameShape(QFrame.VLine); edu_main_lay.addWidget(sep)

        right_layout.addWidget(edu_grp)
        right_layout.addStretch()

        content_layout.addWidget(left_column, stretch=1)
        content_layout.addWidget(right_column, stretch=1)
        scroll.setWidget(content_widget)
        main_layout.addWidget(scroll)

        # Footer
        footer = QHBoxLayout()
        self.progress = QProgressBar(); self.progress.setVisible(False)
        btn_iptal = QPushButton("❌ İPTAL"); btn_iptal.setFixedSize(150, 50)
        self.btn_kaydet = QPushButton("✅ PERSONELİ KAYDET"); self.btn_kaydet.setFixedSize(250, 50)
        footer.addWidget(self.progress); footer.addStretch()
        footer.addWidget(btn_iptal); footer.addWidget(self.btn_kaydet)
        main_layout.addLayout(footer)

    def _add_v_field(self, parent_layout, label_text, widget):
        """Hata düzeltildi: QBoxLayout import edildi."""
        container = QWidget()
        lay = QVBoxLayout(container)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(5)
        lay.addWidget(QLabel(label_text))
        lay.addWidget(widget)
        if isinstance(parent_layout, QBoxLayout):
            parent_layout.addWidget(container)
        else:
            parent_layout.addLayout(lay)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = PersonelEklePenceresi()
    win.show()
    sys.exit(app.exec())