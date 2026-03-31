# -*- coding: utf-8 -*-
"""
Tutanaklı Çalışma Giriş Ekranı — Dış Alan RKS Kayıt Modülü
"""
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QFrame, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QLineEdit, QDateEdit, QSplitter, QSpinBox
)
from PySide6.QtCore import Qt, QDate

from core.hesaplamalar import tr_upper
from core.auth.session_context import SessionContext
from ui.styles.components import STYLES as S
from ui.styles.icons import IconRenderer

# RKS Katsayıları — değer: kayıt anında snapshot alınır, servis bağımsız çalışır
KATSAYI_TABLOSU = {
    "Anjio (Koroner/Vasküler)":     0.35,
    "Ameliyathane (C-Kollu Skopi)": 0.15,
    "ERCP (Gastroenteroloji)":      0.50,
    "ESWL (Taş Kırma)":            0.75,
    "Üroloji (Skopi Destekli)":    0.20,
    "Diğer (Manuel Giriş)":        1.00,
}


class TutanakliGirisPage(QWidget):
    def __init__(self, db=None, parent=None):
        super().__init__(parent)
        self.setStyleSheet(S["page"])
        self._db = db
        self._selected_personel_id = None
        self._selected_personel_ad = None
        self._all_personel = []

        self._setup_ui()
        self._connect_signals()

    # ─────────────────────────────────────────────────────
    #  UI Kurulum
    # ─────────────────────────────────────────────────────

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 15, 20, 15)

        # Üst Bar
        top_bar = QFrame()
        top_bar.setStyleSheet(S["filter_panel"])
        top_bar.setMaximumHeight(54)
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(12, 6, 12, 6)
        top_layout.setSpacing(12)

        lbl_title = QLabel("Tutanaklı Radyasyon Çalışma Girişi (RKS Denetimli)")
        lbl_title.setStyleSheet(
            "font-size: 15px; font-weight: bold; color: #1D75FE; letter-spacing: 0.5px;"
        )
        top_layout.addWidget(lbl_title)
        top_layout.addStretch()

        lbl_donem = QLabel("Dönem:")
        lbl_donem.setProperty("color-role", "primary")
        top_layout.addWidget(lbl_donem)

        self.cmb_ay = QComboBox()
        self.cmb_ay.addItems([
            "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
            "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"
        ])
        self.cmb_ay.setCurrentIndex(datetime.now().month - 1)
        self.cmb_ay.setFixedWidth(90)
        top_layout.addWidget(self.cmb_ay)

        self.cmb_yil = QComboBox()
        self.cmb_yil.addItems([
            str(y) for y in range(datetime.now().year - 2, datetime.now().year + 3)
        ])
        self.cmb_yil.setCurrentText(str(datetime.now().year))
        self.cmb_yil.setFixedWidth(70)
        top_layout.addWidget(self.cmb_yil)

        main_layout.addWidget(top_bar)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Sol Panel: Personel Listesi
        left_panel = QFrame()
        left_panel.setStyleSheet(S["filter_panel"])
        left_layout = QVBoxLayout(left_panel)

        lbl_kapsam = QLabel("Kapsamdaki Personel (Hemşire / Doktor)")
        lbl_kapsam.setStyleSheet(
            "font-size: 13px; font-weight: bold; color: #1D75FE; margin-bottom: 4px;"
        )
        left_layout.addWidget(lbl_kapsam)

        self.txt_ara = QLineEdit()
        self.txt_ara.setPlaceholderText("İsim veya TC ile ara...")
        self.txt_ara.setStyleSheet(S["input"])
        left_layout.addWidget(self.txt_ara)

        self.list_personel = QTableWidget()
        self.list_personel.setColumnCount(2)
        self.list_personel.setHorizontalHeaderLabels(["TC Kimlik", "Ad Soyad"])
        self.list_personel.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.list_personel.verticalHeader().setVisible(False)
        self.list_personel.setStyleSheet(S["table"])
        self.list_personel.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        left_layout.addWidget(self.list_personel)

        # Sağ Panel: Form
        right_panel = QFrame()
        right_panel.setStyleSheet(S["filter_panel"])
        right_panel.setMaximumWidth(420)
        right_panel.setMinimumWidth(340)
        right_panel_layout = QHBoxLayout(right_panel)
        right_panel_layout.setContentsMargins(0, 0, 0, 0)
        right_panel_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        form_container = QFrame()
        form_container.setProperty("bg-role", "panel")
        self.form_layout = QVBoxLayout(form_container)
        self.form_layout.setSpacing(12)

        self.lbl_secili = QLabel("Lütfen personel seçiniz.")
        self.lbl_secili.setProperty("color-role", "primary")
        self.form_layout.addWidget(self.lbl_secili)

        # İşlem Alanı
        self.cmb_islem = QComboBox()
        self.cmb_islem.addItems(list(KATSAYI_TABLOSU.keys()))
        self._add_form_item("Çalışılan Alan / İşlem Tipi:", self.cmb_islem)

        # Vaka Sayısı
        self.inp_vaka = QSpinBox()
        self.inp_vaka.setRange(0, 1000)
        self.inp_vaka.setFixedHeight(35)
        self._add_form_item("Toplam Vaka / İşlem Sayısı:", self.inp_vaka)

        # Hesaplanan Saat (salt okunur)
        self.inp_saat = QLineEdit()
        self.inp_saat.setReadOnly(True)
        self.inp_saat.setStyleSheet(
            "background-color: rgba(255,255,255,0.05); color: #66bb6a; font-weight: bold;"
        )
        self._add_form_item("Hesaplanan Fiili Süre (Saat):", self.inp_saat)

        # Tutanak Bilgileri
        self.inp_tutanak_no = QLineEdit()
        self.inp_tutanak_no.setPlaceholderText("Tutanak No")
        self._add_form_item("Tutanak Kayıt No:", self.inp_tutanak_no)

        self.inp_tutanak_tar = QDateEdit()
        self.inp_tutanak_tar.setCalendarPopup(True)
        self.inp_tutanak_tar.setDate(QDate.currentDate())
        self._add_form_item("Tutanak Tarihi:", self.inp_tutanak_tar)

        self.form_layout.addStretch()

        # Kaydet butonu
        self.btn_ekle = QPushButton("TUTANAĞI ONAYLA VE KAYDET")
        self.btn_ekle.setStyleSheet(S["save_btn"])
        self.btn_ekle.setMinimumHeight(45)
        self.btn_ekle.setMaximumWidth(320)
        IconRenderer.set_button_icon(self.btn_ekle, "save", color="#FFFFFF")
        self.form_layout.addWidget(self.btn_ekle)

        # Dönem özeti butonu
        self.btn_ozet = QPushButton("DÖNEM ÖZETİ HESAPLA")
        self.btn_ozet.setStyleSheet(S.get("secondary_btn", S["save_btn"]))
        self.btn_ozet.setMinimumHeight(38)
        self.btn_ozet.setMaximumWidth(320)
        self.form_layout.addWidget(self.btn_ozet)

        right_panel_layout.addWidget(form_container)

        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 4)
        splitter.setStretchFactor(1, 6)
        main_layout.addWidget(splitter)

    def _add_form_item(self, label_text: str, widget):
        row = QVBoxLayout()
        lbl = QLabel(label_text)
        lbl.setProperty("color-role", "primary")
        row.addWidget(lbl)
        widget.setStyleSheet(S["input"])
        row.addWidget(widget)
        self.form_layout.addLayout(row)

    # ─────────────────────────────────────────────────────
    #  Sinyaller
    # ─────────────────────────────────────────────────────

    def _connect_signals(self):
        self.list_personel.itemClicked.connect(self._personel_secildi)
        self.cmb_islem.currentIndexChanged.connect(self._hesapla)
        self.inp_vaka.valueChanged.connect(self._hesapla)
        self.btn_ekle.clicked.connect(self._kaydet)
        self.btn_ozet.clicked.connect(self._donem_ozeti_hesapla)
        self.txt_ara.textChanged.connect(self._filtrele)

    # ─────────────────────────────────────────────────────
    #  İş Mantığı
    # ─────────────────────────────────────────────────────

    def _hesapla(self):
        """Vaka × katsayı anlık hesap."""
        islem = self.cmb_islem.currentText()
        vaka = self.inp_vaka.value()
        katsayi = KATSAYI_TABLOSU.get(islem, 0)
        self.inp_saat.setText(f"{vaka * katsayi:.2f}")

    def _personel_secildi(self, item):
        row = item.row()
        tc_item = self.list_personel.item(row, 0)
        ad_item = self.list_personel.item(row, 1)

        if tc_item and ad_item:
            self._selected_personel_id = tc_item.text()
            self._selected_personel_ad = ad_item.text()
            self.lbl_secili.setText(f"Seçili: {ad_item.text()}")
            self.lbl_secili.setProperty("color-role", "primary")
        else:
            self._selected_personel_id = None
            self._selected_personel_ad = None
            self.lbl_secili.setText("Lütfen personel seçiniz.")
            self.lbl_secili.setProperty("color-role", "primary")

    def _kaydet(self):
        """Formu doğrular ve DB'ye yazar."""
        if not self._selected_personel_id:
            QMessageBox.warning(self, "Eksik Bilgi", "Lütfen personel seçin.")
            return
        if self.inp_vaka.value() == 0:
            QMessageBox.warning(self, "Eksik Bilgi", "Vaka sayısı 0 olamaz.")
            return
        if not self.inp_tutanak_no.text().strip():
            QMessageBox.warning(self, "Eksik Bilgi", "Tutanak numarası boş olamaz.")
            return

        if not self._db:
            QMessageBox.critical(self, "Hata", "Veritabanı bağlantısı kurulamadı.")
            return

        from core.di import get_dis_alan_service
        svc = get_dis_alan_service(self._db)

        islem = self.cmb_islem.currentText()
        ay = self.cmb_ay.currentIndex() + 1
        yil = int(self.cmb_yil.currentText())

        # Oturumu açık kullanıcıyı al (yoksa "RKS")
        try:
            kaydeden = SessionContext().current_user or "RKS"
        except Exception:
            kaydeden = "RKS"

        veri = {
            "PersonelKimlik":    self._selected_personel_id,
            "PersonelAd":        self._selected_personel_ad,
            "DonemAy":           ay,
            "DonemYil":          yil,
            "IslemTipi":         islem,
            "Katsayi":           KATSAYI_TABLOSU.get(islem, 0),
            "VakaSayisi":        self.inp_vaka.value(),
            "HesaplananSaat":    float(self.inp_saat.text()),
            "TutanakNo":         self.inp_tutanak_no.text().strip(),
            "TutanakTarihi":     self.inp_tutanak_tar.date().toString("yyyy-MM-dd"),
            "KaydedenKullanici": kaydeden,
        }

        basari = svc.calisma_kaydet(veri)

        if basari:
            QMessageBox.information(
                self,
                "Kaydedildi",
                f"{self._selected_personel_ad} için\n"
                f"{self.inp_saat.text()} saatlik çalışma kaydedildi.",
            )
            self._formu_temizle()
        else:
            QMessageBox.warning(
                self,
                "Kayıt Hatası",
                "Bu tutanak numarası bu dönem için zaten kayıtlı.\n"
                "Lütfen tutanak numarasını kontrol edin.",
            )

    def _donem_ozeti_hesapla(self):
        """Seçili personelin mevcut dönemi için özet hesaplar ve gösterir."""
        if not self._selected_personel_id:
            QMessageBox.warning(self, "Eksik Bilgi", "Önce personel seçin.")
            return
        if not self._db:
            return

        from core.di import get_dis_alan_service
        svc = get_dis_alan_service(self._db)

        ay = self.cmb_ay.currentIndex() + 1
        yil = int(self.cmb_yil.currentText())

        ozet = svc.ozet_hesapla_ve_kaydet(
            personel_kimlik=self._selected_personel_id,
            personel_ad=self._selected_personel_ad,
            donem_ay=ay,
            donem_yil=yil,
        )

        if ozet:
            QMessageBox.information(
                self,
                "Dönem Özeti",
                f"Personel : {ozet['PersonelAd']}\n"
                f"Dönem    : {ay}/{yil}\n"
                f"Toplam   : {ozet['ToplamSaat']:.2f} saat\n"
                f"İzin Hakkı: {ozet['IzinGunHakki']:.1f} gün\n\n"
                f"{ozet.get('Notlar', '')}",
            )
        else:
            QMessageBox.warning(
                self,
                "Hesaplanamadı",
                "Bu dönem onaylanmış olabilir veya kayıt bulunamadı.",
            )

    def _formu_temizle(self):
        self.inp_vaka.setValue(0)
        self.inp_tutanak_no.clear()
        self.inp_saat.clear()

    # ─────────────────────────────────────────────────────
    #  Veri Yükleme
    # ─────────────────────────────────────────────────────

    def load_data(self):
        """Sayfa açılışında veya dönem değişiminde çağrılır."""
        if not self._db:
            return
        from core.di import get_dis_alan_service
        svc = get_dis_alan_service(self._db)
        self._all_personel = svc.get_dis_alan_personeli().veri or []
        self._listeyi_doldur(self._all_personel)

    def _listeyi_doldur(self, data: list[dict]):
        self.list_personel.setRowCount(0)
        self.list_personel.setRowCount(len(data))
        for i, p in enumerate(data):
            self.list_personel.setItem(
                i, 0, QTableWidgetItem(str(p.get("KimlikNo", "")))
            )
            self.list_personel.setItem(
                i, 1, QTableWidgetItem(str(p.get("AdSoyad", "")))
            )

    def _filtrele(self, text: str):
        search = tr_upper(text)
        filtered = [
            p for p in self._all_personel
            if search in tr_upper(str(p.get("AdSoyad", "")))
            or search in str(p.get("KimlikNo", ""))
        ]
        self._listeyi_doldur(filtered)

    def showEvent(self, event):
        """Sayfa her gösterildiğinde personel listesini tazeler."""
        super().showEvent(event)
        self.load_data()
