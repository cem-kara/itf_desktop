# -*- coding: utf-8 -*-
import sys
from PySide6.QtCore import Qt, QDate, QRegularExpression
from PySide6.QtGui import QRegularExpressionValidator
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QScrollArea, QTabWidget, QProgressBar, QFrame,
    QComboBox, QLineEdit, QDateEdit, QApplication, 
    QGroupBox, QGridLayout, QDialog, QFormLayout
)

# =============================================================================
# DIALOG: İŞTEN AYRILIŞ EKRANI (SAF UI)
# =============================================================================
class AyrilisIslemleriDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("İşten Ayrılış İşlemleri")
        self.resize(400, 250)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        lbl_info = QLabel("Personelinin işten çıkış işlemleri başlatılacak.")
        lbl_info.setWordWrap(True)
        layout.addWidget(lbl_info)
        
        gb = QGroupBox("Ayrılış Detayları")
        form = QFormLayout(gb)
        
        self.dt_tarih = QDateEdit(QDate.currentDate())
        self.dt_tarih.setCalendarPopup(True)
        self.dt_tarih.setDisplayFormat("dd.MM.yyyy")
        
        self.cmb_neden = QComboBox()
        self.cmb_neden.setEditable(True)
        self.cmb_neden.addItems(["Emekli", "Vefat", "İstifa", "Tayin"])
        
        form.addRow("Ayrılış Tarihi:", self.dt_tarih)
        form.addRow("Ayrılma Nedeni:", self.cmb_neden)
        layout.addWidget(gb)
        
        lbl_uyari = QLabel("⚠️ DİKKAT: Bu işlem personeli PASİF durumuna getirecek ve dosyaları arşivleyecektir.")
        lbl_uyari.setWordWrap(True)
        layout.addWidget(lbl_uyari)
        
        h_btn = QHBoxLayout()
        self.btn_onayla = QPushButton("Onayla ve Bitir")
        self.btn_iptal = QPushButton("İptal")
        
        h_btn.addWidget(self.btn_iptal)
        h_btn.addWidget(self.btn_onayla)
        layout.addLayout(h_btn)
        
        self.prog = QProgressBar()
        self.prog.setVisible(False)
        layout.addWidget(self.prog)

# =============================================================================
# ANA FORM - SAF UI
# =============================================================================
class PersonelDetayPenceresi(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Personel Detay Paneli")
        self.resize(1400, 900)
        self.ui = {}
        self._setup_ui()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)
        
        # ÜST BAR
        header = QHBoxLayout()
        self.lbl_ad = QLabel("👤 Personel Adı Soyadı")
        
        self.btn_edit = QPushButton("✏️ Düzenle")
        self.btn_edit.setMinimumHeight(40)
        
        self.btn_save = QPushButton("💾 Kaydet")
        self.btn_save.setMinimumHeight(40)
        
        self.btn_cancel = QPushButton("❌ İptal")
        self.btn_cancel.setMinimumHeight(40)
        
        header.addWidget(self.lbl_ad)
        header.addStretch()
        header.addWidget(self.btn_edit)
        header.addWidget(self.btn_save)
        header.addWidget(self.btn_cancel)
        main_layout.addLayout(header)

        # TAB YAPI
        self.tabs = QTabWidget()
        
        # TAB 1: BİLGİLER
        self.tab_bilgi = QWidget()
        self._setup_bilgi_tab(self.tab_bilgi)
        self.tabs.addTab(self.tab_bilgi, "📋 Personel Bilgileri")
        
        # TAB 2: İZİNLER
        self.tab_izin = QWidget()
        self._setup_izin_tab(self.tab_izin)
        self.tabs.addTab(self.tab_izin, "🏖️ İzin Bilgileri")
        
        main_layout.addWidget(self.tabs)
        
        self.prog = QProgressBar()
        self.prog.setVisible(False)
        main_layout.addWidget(self.prog)

    def _setup_bilgi_tab(self, parent):
        layout = QVBoxLayout(parent)
        layout.setContentsMargins(0, 0, 0, 0)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        
        content_widget = QWidget()
        content_layout = QHBoxLayout(content_widget)
        content_layout.setSpacing(25)

        # SOL SÜTUN
        left_column = QWidget()
        left_layout = QVBoxLayout(left_column)
        left_layout.setSpacing(20)

        # Fotoğraf
        photo_grp = QGroupBox("Fotoğraf")
        photo_lay = QVBoxLayout(photo_grp)
        photo_lay.setAlignment(Qt.AlignCenter)
        self.lbl_img = QLabel("Fotoğraf")
        self.lbl_img.setFixedSize(180, 220)
        self.lbl_img.setAlignment(Qt.AlignCenter)
        self.btn_img = QPushButton("📷 Fotoğraf Değiştir")
        self.btn_img.setMinimumHeight(40)
        photo_lay.addWidget(self.lbl_img)
        photo_lay.addWidget(self.btn_img)
        left_layout.addWidget(photo_grp)

        # Kimlik
        id_grp = QGroupBox("Kimlik Bilgileri")
        id_lay = QVBoxLayout(id_grp)
        row_id_1 = QHBoxLayout()
        self.ui['tc'] = QLineEdit()
        self.ui['ad'] = QLineEdit()
        self._add_v_field(row_id_1, "TC Kimlik No", self.ui['tc'])
        self._add_v_field(row_id_1, "Ad Soyad", self.ui['ad'])
        id_lay.addLayout(row_id_1)
        
        row_id_2 = QHBoxLayout()
        self.ui['dyeri'] = QComboBox()
        self.ui['dtar'] = QDateEdit()
        self.ui['dtar'].setCalendarPopup(True)
        self._add_v_field(row_id_2, "Doğum Yeri", self.ui['dyeri'])
        self._add_v_field(row_id_2, "Doğum Tarihi", self.ui['dtar'])
        id_lay.addLayout(row_id_2)
        left_layout.addWidget(id_grp)

        # İletişim
        contact_grp = QGroupBox("İletişim Bilgileri")
        contact_lay = QVBoxLayout(contact_grp)
        row_contact = QHBoxLayout()
        self.ui['tel'] = QLineEdit()
        self.ui['mail'] = QLineEdit()
        self._add_v_field(row_contact, "Cep Telefonu", self.ui['tel'])
        self._add_v_field(row_contact, "E-Posta Adresi", self.ui['mail'])
        contact_lay.addLayout(row_contact)
        left_layout.addWidget(contact_grp)
        left_layout.addStretch()

        # SAĞ SÜTUN
        right_column = QWidget()
        right_layout = QVBoxLayout(right_column)

        # Kurumsal
        corp_grp = QGroupBox("Kadro ve Kurumsal Bilgiler")
        corp_lay = QVBoxLayout(corp_grp)
        row_corp_1 = QHBoxLayout()
        self.ui['sinif'] = QComboBox()
        self.ui['unvan'] = QComboBox()
        self._add_v_field(row_corp_1, "Hizmet Sınıfı", self.ui['sinif'])
        self._add_v_field(row_corp_1, "Kadro Ünvanı", self.ui['unvan'])
        corp_lay.addLayout(row_corp_1)
        
        row_corp_2 = QHBoxLayout()
        self.ui['gorev'] = QComboBox()
        self.ui['sicil'] = QLineEdit()
        self._add_v_field(row_corp_2, "Görev Yeri", self.ui['gorev'])
        self._add_v_field(row_corp_2, "Kurum Sicil No", self.ui['sicil'])
        corp_lay.addLayout(row_corp_2)
        
        self.ui['baslama'] = QDateEdit()
        self.ui['baslama'].setCalendarPopup(True)
        self._add_v_field(corp_lay, "Memuriyete Başlama Tarihi", self.ui['baslama'])
        
        self.btn_ayrilis = QPushButton("⚠️ İşten Çıkış Yap")
        self.btn_ayrilis.setMinimumHeight(45)
        corp_lay.addWidget(self.btn_ayrilis)
        right_layout.addWidget(corp_grp)

        # Eğitim
        edu_grp = QGroupBox("Eğitim Bilgileri")
        edu_main_lay = QHBoxLayout(edu_grp)
        
        # Okul 1
        edu_1_lay = QVBoxLayout()
        self.ui['okul1'] = QComboBox()
        self.ui['bolum1'] = QComboBox()
        self.ui['dip1'] = QLineEdit()
        self.btn_up1 = QPushButton("📤")
        self._add_v_field(edu_1_lay, "Okul Adı", self.ui['okul1'])
        self._add_v_field(edu_1_lay, "Bölüm/Fakülte", self.ui['bolum1'])
        edu_1_lay.addWidget(self.ui['dip1'])
        edu_1_lay.addWidget(self.btn_up1)
        
        # Okul 2
        edu_2_lay = QVBoxLayout()
        self.ui['okul2'] = QComboBox()
        self.ui['bolum2'] = QComboBox()
        self.ui['dip2'] = QLineEdit()
        self.btn_up2 = QPushButton("📤")
        self._add_v_field(edu_2_lay, "Okul Adı", self.ui['okul2'])
        self._add_v_field(edu_2_lay, "Bölüm/Fakülte", self.ui['bolum2'])
        edu_2_lay.addWidget(self.ui['dip2'])
        edu_2_lay.addWidget(self.btn_up2)
        
        edu_main_lay.addLayout(edu_1_lay)
        sep = QFrame(); sep.setFrameShape(QFrame.VLine); edu_main_lay.addWidget(sep)
        edu_main_lay.addLayout(edu_2_lay)
        
        right_layout.addWidget(edu_grp)
        right_layout.addStretch()

        content_layout.addWidget(left_column, stretch=1)
        content_layout.addWidget(right_column, stretch=1)
        scroll.setWidget(content_widget)
        layout.addWidget(scroll)

    def _setup_izin_tab(self, parent):
        layout = QGridLayout(parent)
        
        grp_yillik = QGroupBox("📅 Yıllık İzin Durumu")
        g_yillik = QGridLayout(grp_yillik)
        self.lbl_y_devir = self._add_stat(g_yillik, 0, "Devir Eden İzin:")
        self.lbl_y_hak = self._add_stat(g_yillik, 1, "Bu Yıl Hak Edilen:")
        self.lbl_y_toplam = self._add_stat(g_yillik, 3, "TOPLAM İZİN HAKKI:")
        self.lbl_y_kullanilan = self._add_stat(g_yillik, 4, "Kullanılan Yıllık İzin:")
        self.lbl_y_kalan = self._add_stat(g_yillik, 6, "KALAN YILLIK İZİN:")

        grp_diger = QGroupBox("☢️ Şua ve Diğer İzinler")
        g_diger = QGridLayout(grp_diger)
        self.lbl_s_hak = self._add_stat(g_diger, 0, "Hak Edilen Şua İzin:")
        self.lbl_s_kul = self._add_stat(g_diger, 1, "Kullanılan Şua İzinleri:")
        self.lbl_s_kalan = self._add_stat(g_diger, 3, "KALAN ŞUA İZNİ:")
        self.lbl_diger = self._add_stat(g_diger, 7, "Toplam Rapor/Mazeret:")

        layout.addWidget(grp_yillik, 0, 0)
        layout.addWidget(grp_diger, 0, 1)

    def _add_stat(self, grid, row, text):
        grid.addWidget(QLabel(text), row, 0)
        val = QLabel("0")
        val.setAlignment(Qt.AlignRight)
        grid.addWidget(val, row, 1)
        return val

    def _add_v_field(self, layout, text, widget):
        container = QWidget()
        lay = QVBoxLayout(container)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(QLabel(text))
        lay.addWidget(widget)
        layout.addWidget(container)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = PersonelDetayPenceresi()
    win.show()
    sys.exit(app.exec())