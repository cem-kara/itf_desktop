# -*- coding: utf-8 -*-
from core.hata_yonetici import exc_logla
import sys
import os
import logging
from datetime import datetime

# PySide6
from PySide6.QtCore import Qt, QDate, QThread, Signal
from PySide6.QtGui import QFont, QColor
from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                               QLabel, QLineEdit, QComboBox, QDateEdit, QPushButton, 
                               QScrollArea, QFrame, QFileDialog, QGridLayout, 
                               QProgressBar, QTextEdit, QCompleter, QGroupBox, QMessageBox, QSizePolicy)

from ui.theme_manager import ThemeManager
from ui.styles import DarkTheme
from ui.styles.icons import IconRenderer

# LOGLAMA
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ArizaEkle")

# YOL AYARLARI
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)
if root_dir not in sys.path:
    sys.path.append(root_dir)

# Merkezi stil
S = ThemeManager.get_all_component_styles()

# SABİT LİSTELER
ARIZA_TIPLERI = [
    "Donanımsal Arıza", "Yazılımsal Arıza", "Kullanıcı Hatası",
    "Ağ / Bağlantı Sorunu", "Parça Değişimi", "Periyodik Bakım Talebi", "Diğer"
]
ONCELIK_DURUMLARI = ["Düşük", "Normal", "Yüksek", "Acil (Kritik)"]

# =============================================================================
# 1. THREAD SINIFLARI
# =============================================================================
class BaslangicYukleyici(QThread):
    veri_hazir = Signal(str, list) # yeni_id, cihaz_listesi
    
    def __init__(self):
        super().__init__()

    def run(self):
        from database.sqlite_manager import SQLiteManager
        db = None
        try:
            yeni_id = f"ARZ-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
            
            cihaz_listesi = []
            try:
                db = SQLiteManager()
                from core.di import get_registry
                registry = get_registry(db)
                repo = registry.get("Cihazlar")
                all_cihaz = repo.get_all()
                for c in all_cihaz:
                    # Format: ID | Marka Model
                    cihaz_listesi.append(f"{c.get('Cihazid')} | {c.get('Marka')} {c.get('Model')}")
            except Exception as e:
                logger.error(f"Cihaz listesi yükleme hatası: {e}")
            
            self.veri_hazir.emit(yeni_id, cihaz_listesi)
        except Exception as e:
            logger.error(f"Başlangıç yükleme hatası: {e}")
            self.veri_hazir.emit("HATA", [])
        finally:
            if db: db.close()

class KayitIslemi(QThread):
    islem_tamam = Signal()
    hata_olustu = Signal(str)

    def __init__(self, veri_sozlugu, dosya_yollari):
        super().__init__()
        self.veri = veri_sozlugu
        self.dosyalar = dosya_yollari

    def run(self):
        from database.sqlite_manager import SQLiteManager
        db = None
        try:
            # Dosya yollarını birleştirip kaydet (basit çözüm)
            if self.dosyalar:
                self.veri["Rapor"] = ";".join(self.dosyalar)
            else:
                self.veri["Rapor"] = ""
                
            db = SQLiteManager()
            from core.di import get_registry
            registry = get_registry(db)
            repo = registry.get("Cihaz_Ariza")
            repo.insert(self.veri)
            self.islem_tamam.emit()
        except Exception as e:
            exc_logla("ArizaKayit.VeriYukleyici", e)
            self.hata_olustu.emit(str(e))
        finally:
            if db: db.close()

# =============================================================================
# 2. ANA PENCERE: ARIZA EKLE
# =============================================================================
class ArizaKayitPenceresi(QWidget):
    def __init__(self, db=None):
        super().__init__()
        self._db = db
        self.setWindowTitle("Yeni Arıza Kaydı")
        self.resize(1000, 700)
        
        self.inputs = {}
        self.secilen_dosyalar = []
        
        self.setup_ui()
        
               
        self.baslangic_yukle()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # --- HEADER ---
        header_layout = QHBoxLayout()
        lbl_baslik = QLabel("Arıza Bildirim Formu")
        lbl_baslik.setFont(QFont("Segoe UI", 16, QFont.Bold))
        lbl_baslik.setStyleSheet(S["header_name"])
        
        self.progress = QProgressBar()
        self.progress.setFixedSize(150, 10)
        self.progress.setTextVisible(False)
        self.progress.setStyleSheet(S["progress"])
        
        header_layout.addWidget(lbl_baslik)
        header_layout.addStretch()
        header_layout.addWidget(self.progress)
        main_layout.addLayout(header_layout)

        # --- CONTENT (2 KOLONLU YAPI) ---
        content_widget = QWidget()
        content_layout = QHBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(20)
        
        # ================= SOL KOLON =================
        sol_layout = QVBoxLayout()
        sol_layout.setAlignment(Qt.AlignTop)
        
        # GRUP 1: Bildirim Bilgileri
        grp_genel = QGroupBox("Bildirim Bilgileri")
        grp_genel.setStyleSheet(S["group"])
        v_genel = QVBoxLayout(grp_genel)
        v_genel.setSpacing(15)
        
        # 1. Arıza ID
        self.create_input_vbox(v_genel, "Arıza ID (Otomatik):", "ArizaID", "text")
        self.inputs["ArizaID"].setReadOnly(True)
        
        # 2. İlgili Cihaz (YERİ DEĞİŞTİRİLDİ - ARTIK 2. SIRADA)
        self.create_input_vbox(v_genel, "İlgili Cihaz (ID veya Marka Ara):", "CihazID", "combo")
        self.inputs["CihazID"].setEditable(True) 
        self.inputs["CihazID"].setInsertPolicy(QComboBox.NoInsert) # Yeni veri eklenmesin
        
        # Gelismis arama ayari (MatchContains)
        completer = self.inputs["CihazID"].completer()
        completer.setCompletionMode(QCompleter.PopupCompletion)
        completer.setFilterMode(Qt.MatchContains) # İçinde geçen kelimeyi bulur (Samsung gibi)

        # 3. Tarih
        self.create_input_vbox(v_genel, "Tarih / Saat:", "Tarih", "date")
        
        # 4. Bildiren Personel
        self.create_input_vbox(v_genel, "Bildiren Personel:", "Bildiren", "text")
        
        sol_layout.addWidget(grp_genel)
        
        # GRUP 2: Dosyalar
        grp_dosya = QGroupBox("Dosya Ekleri")
        grp_dosya.setStyleSheet(S["group"])
        v_dosya = QVBoxLayout(grp_dosya)
        v_dosya.setSpacing(10)
        
        self.lbl_dosya_durum = QLabel("Dosya seçilmedi")
        self.lbl_dosya_durum.setStyleSheet(f"color: {DarkTheme.TEXT_MUTED}; font-style: italic;")
        self.lbl_dosya_durum.setAlignment(Qt.AlignCenter)
        
        self.btn_dosya = QPushButton("Gorsel / Tutanak Ekle")
        self.btn_dosya.setStyleSheet(S["file_btn"])
        IconRenderer.set_button_icon(self.btn_dosya, "upload", color=DarkTheme.TEXT_PRIMARY, size=14)
        self.btn_dosya.clicked.connect(self.dosya_sec)
        
        v_dosya.addWidget(self.lbl_dosya_durum)
        v_dosya.addWidget(self.btn_dosya)
        
        sol_layout.addWidget(grp_dosya)
        sol_layout.addStretch()
        
        content_layout.addLayout(sol_layout, 1) # %33 Genişlik

        # ================= SAĞ KOLON =================
        sag_layout = QVBoxLayout()
        sag_layout.setAlignment(Qt.AlignTop)
        
        grp_detay = QGroupBox("Arıza Detayları")
        grp_detay.setStyleSheet(S["group"])
        frm_detay = QVBoxLayout(grp_detay)
        frm_detay.setSpacing(15)
        
        # Konu
        self.create_input_vbox(frm_detay, "Konu / Başlık:", "Konu")
        
        # Tip ve Öncelik (Yanyana)
        h_tip = QHBoxLayout()
        self.create_input_vbox_layout(h_tip, "Arıza Tipi:", "ArizaTipi", "combo")
        self.inputs["ArizaTipi"].addItems(ARIZA_TIPLERI)
        
        self.create_input_vbox_layout(h_tip, "Öncelik Durumu:", "Oncelik", "combo")
        self.inputs["Oncelik"].addItems(ONCELIK_DURUMLARI)
        frm_detay.addLayout(h_tip)
        
        # Açıklama
        lbl_aciklama = QLabel("Detaylı Açıklama:")
        lbl_aciklama.setStyleSheet(S["label"])
        
        self.txt_aciklama = QTextEdit()
        self.txt_aciklama.setPlaceholderText("Arızanın oluş şekli, belirtileri vb...")
        self.txt_aciklama.setStyleSheet(S["input"])
        
        # Yukseklik azaltildi (daha kompakt)
        self.txt_aciklama.setMinimumHeight(120) 
        self.inputs["Aciklama"] = self.txt_aciklama
        
        frm_detay.addWidget(lbl_aciklama)
        frm_detay.addWidget(self.txt_aciklama)
        frm_detay.addStretch() # Altta boşluk kalsın, yukarı sıkışmasın
        
        sag_layout.addWidget(grp_detay)
        content_layout.addLayout(sag_layout, 2) # %66 Genişlik
        
        main_layout.addWidget(content_widget)

        # --- FOOTER ---
        footer = QHBoxLayout()
        self.btn_iptal = QPushButton("Iptal")
        self.btn_iptal.setFixedSize(100, 36)
        self.btn_iptal.setStyleSheet(S["cancel_btn"])
        IconRenderer.set_button_icon(self.btn_iptal, "x", color=DarkTheme.TEXT_PRIMARY, size=14)
        self.btn_iptal.clicked.connect(self.close)
        
        self.btn_kaydet = QPushButton("Kaydi Olustur")
        self.btn_kaydet.setFixedSize(200, 36)
        self.btn_kaydet.setStyleSheet(S["save_btn"])
        IconRenderer.set_button_icon(self.btn_kaydet, "alert_triangle", color=DarkTheme.TEXT_PRIMARY, size=14)
        self.btn_kaydet.clicked.connect(self.kaydet_baslat)
        
        footer.addWidget(self.btn_iptal)
        footer.addStretch()
        footer.addWidget(self.btn_kaydet)
        main_layout.addLayout(footer)

    # --- UI YARDIMCILARI ---
    def create_input_vbox(self, layout, label_text, key, tip="text"):
        """Dikey yerleşim için Label + Input oluşturur."""
        lbl = QLabel(label_text)
        lbl.setStyleSheet(S["label"])
        widget = self._create_widget(tip)
        self.inputs[key] = widget
        layout.addWidget(lbl)
        layout.addWidget(widget)

    def create_input_vbox_layout(self, parent_layout, label_text, key, tip="text"):
        """Yatay layout içine dikey grup ekler (Label + Input)"""
        container = QVBoxLayout()
        container.setSpacing(4)
        container.setContentsMargins(0,0,0,0)
        lbl = QLabel(label_text)
        lbl.setStyleSheet(S["label"])
        widget = self._create_widget(tip)
        self.inputs[key] = widget
        container.addWidget(lbl)
        container.addWidget(widget)
        parent_layout.addLayout(container)

    def _create_widget(self, tip):
        widget = None
        if tip == "text": widget = QLineEdit()
        elif tip == "combo": widget = QComboBox()
        elif tip == "date": 
            widget = QDateEdit()
            widget.setCalendarPopup(True)
            widget.setDisplayFormat("dd.MM.yyyy")
            widget.setDate(QDate.currentDate())
            ThemeManager.setup_calendar_popup(widget)
        
        if widget:
            widget.setStyleSheet(S["input"] if tip != "combo" else S["combo"])
            widget.setMinimumHeight(35)
        return widget

    # --- MANTIK ---
    def baslangic_yukle(self):
        self.progress.setVisible(True)
        self.progress.setRange(0, 0)
        self.loader = BaslangicYukleyici()
        self.loader.veri_hazir.connect(self.veriler_yuklendi)
        self.loader.start()

    def veriler_yuklendi(self, yeni_id, cihaz_listesi):
        self.progress.setRange(0, 100); self.progress.setValue(100)
        self.inputs["ArizaID"].setText(yeni_id)
        self.inputs["CihazID"].clear()
        self.inputs["CihazID"].addItem("")
        self.inputs["CihazID"].addItems(cihaz_listesi)

    def dosya_sec(self):
        yol, _ = QFileDialog.getOpenFileName(self, "Dosya Seç", "", "Resim/PDF (*.jpg *.png *.pdf)")
        if yol:
            self.secilen_dosyalar = [yol]
            dosya_adi = os.path.basename(yol)
            self.lbl_dosya_durum.setText(dosya_adi)
            self.lbl_dosya_durum.setStyleSheet(f"color: {DarkTheme.STATUS_SUCCESS}; font-weight: bold;")

    def kaydet_baslat(self):
        cihaz_secim = self.inputs["CihazID"].currentText()
        cihaz_id = cihaz_secim.split("|")[0].strip() if "|" in cihaz_secim else cihaz_secim.strip()
        konu = self.inputs["Konu"].text().strip()
        
        if not cihaz_id or not konu:
            QMessageBox.warning(self, "Eksik", "Lütfen Cihaz ve Konu alanlarını doldurun.")
            return

        self.btn_kaydet.setEnabled(False); self.btn_kaydet.setText("Kaydediliyor...")
        self.progress.setRange(0, 0); QApplication.setOverrideCursor(Qt.WaitCursor)

        veri = {
            "Arizaid": self.inputs["ArizaID"].text(),
            "Cihazid": cihaz_id,
            "BaslangicTarihi": self.inputs["Tarih"].date().toString("yyyy-MM-dd"),
            "Saat": datetime.now().strftime("%H:%M"),
            "Bildiren": self.inputs["Bildiren"].text(),
            "ArizaTipi": self.inputs["ArizaTipi"].currentText(),
            "Oncelik": self.inputs["Oncelik"].currentText(),
            "Baslik": konu,
            "ArizaAcikla": self.inputs["Aciklama"].toPlainText(),
            "Durum": "Açık"
        }

        self.saver = KayitIslemi(veri, self.secilen_dosyalar)
        self.saver.islem_tamam.connect(self.kayit_basarili)
        self.saver.hata_olustu.connect(self.kayit_hatali)
        self.saver.start()

    def kayit_basarili(self):
        QApplication.restoreOverrideCursor()
        self.progress.setRange(0, 100); self.progress.setValue(100)
        QMessageBox.information(self, "Başarılı", "Arıza kaydı oluşturuldu.")
        self.close()

    def kayit_hatali(self, hata):
        QApplication.restoreOverrideCursor()
        self.progress.setRange(0, 100); self.progress.setValue(0)
        self.btn_kaydet.setEnabled(True); self.btn_kaydet.setText("Kaydi Olustur")
        QMessageBox.critical(self, "Hata", f"Kayıt Hatası: {hata}")

    def closeEvent(self, event):
        if hasattr(self, 'loader') and self.loader.isRunning(): self.loader.quit(); self.loader.wait(500)
        if hasattr(self, 'saver') and self.saver.isRunning(): self.saver.quit(); self.saver.wait(500)
        event.accept()
