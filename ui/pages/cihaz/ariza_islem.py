# -*- coding: utf-8 -*-
import os
import logging
from datetime import datetime

from PySide6.QtCore import Qt, QDate, QThread, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                               QLabel, QLineEdit, QComboBox, QDateEdit, QPushButton, 
                               QMessageBox, QFrame, QProgressBar, QTextEdit, QFileDialog)

from ui.theme_manager import ThemeManager

# --- LOGLAMA ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ArizaIslem")

# Merkezi stil
S = ThemeManager.get_all_component_styles()

# =============================================================================
# 1. THREAD SINIFLARI
# =============================================================================
class VeriYukleyici(QThread):
    veri_hazir = Signal(dict, list, list, list) # ariza_bilgisi, gecmis_islemler, islem_turleri, durum_secenekleri
    hata_olustu = Signal(str)

    def __init__(self, ariza_id):
        super().__init__()
        self.ariza_id = str(ariza_id).strip()

    def run(self):
        from database.sqlite_manager import SQLiteManager
        from database.repository_registry import RepositoryRegistry
        db = None
        try:
            db = SQLiteManager()
            registry = RepositoryRegistry(db)
            
            repo_ariza = registry.get("Cihaz_Ariza")
            ariza_bilgisi = repo_ariza.get_by_id(self.ariza_id) or {}
            
            cursor = db.execute(
                "SELECT * FROM Ariza_Islem WHERE Arizaid = ? ORDER BY Islemid DESC", 
                (self.ariza_id,)
            )
            gecmis_islemler = [dict(r) for r in cursor.fetchall()]
            
            # Sabitleri yükle
            sabitler_repo = registry.get("Sabitler")
            all_sabit = sabitler_repo.get_all()
            islem_turleri = [s.get("MenuEleman") for s in all_sabit if s.get("Kod") == "Ariza_Islem_Turu"]
            durum_secenekleri = [s.get("MenuEleman") for s in all_sabit if s.get("Kod") == "Ariza_Durum"]

            self.veri_hazir.emit(ariza_bilgisi, gecmis_islemler, islem_turleri, durum_secenekleri)
        except Exception as e:
            self.hata_olustu.emit(str(e))
        finally:
            if db: db.close()

class IslemKaydedici(QThread):
    islem_tamam = Signal()
    hata_olustu = Signal(str)

    def __init__(self, islem_verisi):
        super().__init__()
        self.islem_verisi = islem_verisi

    def run(self):
        from database.sqlite_manager import SQLiteManager
        from database.repository_registry import RepositoryRegistry
        db = None
        try:
            db = SQLiteManager()
            registry = RepositoryRegistry(db)
                
            # İşlem Kaydı Ekle (Ariza_Islem)
            repo_islem = registry.get("Ariza_Islem")
            repo_islem.insert(self.islem_verisi)
            
            # Arıza Durumunu Güncelle (Cihaz_Ariza)
            yeni_durum = self.islem_verisi.get("YeniDurum")
            ariza_id = self.islem_verisi.get("Arizaid")
            
            if yeni_durum and ariza_id:
                repo_ariza = registry.get("Cihaz_Ariza")
                repo_ariza.update(ariza_id, {"Durum": yeni_durum})
            
            self.islem_tamam.emit()
        except Exception as e:
            self.hata_olustu.emit(str(e))
        finally:
            if db: db.close()

class DosyaYukleyici(QThread):
    yuklendi = Signal(str)
    hata_olustu = Signal(str)

    def __init__(self, dosya_yolu: str, cihaz_id: str, ariza_id: str, parent=None):
        super().__init__(parent)
        self._yol = dosya_yolu
        self._cihaz_id = cihaz_id
        self._ariza_id = ariza_id

    def run(self):
        try:
            from database.google import GoogleDriveService
            drive = GoogleDriveService()
            cihaz_folder_id = drive.find_or_create_folder(self._cihaz_id, drive.get_folder_id("Cihazlar"))
            ariza_folder_id = drive.find_or_create_folder(self._ariza_id, cihaz_folder_id)

            islem_id = f"islem_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            dosya_adi = f"{islem_id}{os.path.splitext(self._yol)[1]}"
            
            link = drive.upload_file(self._yol, parent_folder_id=ariza_folder_id, custom_name=dosya_adi)
            if link:
                self.yuklendi.emit(link)
            else:
                self.hata_olustu.emit("Dosya yüklenemedi, ancak işlem kaydedildi.")
        except Exception as e:
            logger.error(f"Drive yükleme hatası (ariza_islem): {e}")
            self.hata_olustu.emit(f"Dosya yüklenemedi: {e}")

# =============================================================================
# 3. ANA PENCERE: KOMPAKT ARIZA İŞLEM
# =============================================================================
class ArizaIslemPenceresi(QWidget):
    kapanma_istegi = Signal()

    def __init__(self, ariza_id=None, ana_pencere=None):
        super().__init__()
        self.ariza_id = str(ariza_id).strip() if ariza_id else None
        self.ana_pencere = ana_pencere
        
        self.setWindowTitle(f"Arıza Takip Kartı | {self.ariza_id}")
        
        self.inputs = {}
        self.ariza_data = {} 
        self.secilen_rapor_yolu = None
        self.ariza_kapali_mi = False # Durum kontrolü için bayrak
        
        self.setup_ui()
        if self.ariza_id:
            self.verileri_yukle()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # Başlık
        self.lbl_baslik = QLabel(f"Arıza No: {self.ariza_id if self.ariza_id else '---'}")
        self.lbl_baslik.setFont(QFont("Segoe UI", 12, QFont.Bold))
        self.lbl_baslik.setStyleSheet(
            "color:#e57373; border-bottom:2px solid #444; padding-bottom:5px;"
        )
        main_layout.addWidget(self.lbl_baslik)

        # Form
        form = QVBoxLayout()
        form.setSpacing(10)

        # Cihaz No & Tarih (Yan yana)
        h_info = QHBoxLayout()
        self._add_lbl_input(h_info, "Cihaz No:", "CihazID", read_only=True)
        self.inputs["CihazID"].setStyleSheet(
            "background:#333; color:#4dabf7; font-weight:bold; border:1px solid #555;"
        )
        self._add_lbl_input(h_info, "Tarih:", "Tarih", read_only=True)
        self.inputs["Tarih"].setStyleSheet(
            "background:#333; color:#aaa; border:1px solid #444;"
        )
        form.addLayout(h_info)

        # Arıza Açıklaması
        lbl_acik = QLabel("Arıza Detayı:")
        lbl_acik.setStyleSheet("color:#aaa; font-size:11px;")
        self.inputs["Aciklama"] = QTextEdit()
        self.inputs["Aciklama"].setReadOnly(True)
        self.inputs["Aciklama"].setStyleSheet(
            "background:#333; color:#ddd; border:1px solid #444;"
        )
        self.inputs["Aciklama"].setMaximumHeight(60)
        form.addWidget(lbl_acik)
        form.addWidget(self.inputs["Aciklama"])

        # Ayraç
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        line.setStyleSheet("background-color: #444;")
        form.addWidget(line)

        # Müdahale Başlık
        self.lbl_mudahale = QLabel("Müdahale Girişi")
        self.lbl_mudahale.setStyleSheet("color:#4CAF50; font-weight:bold; font-size:12px;")
        form.addWidget(self.lbl_mudahale)

        # İşlem Tarih / Saat
        h_zaman = QHBoxLayout()
        self._add_lbl_date(h_zaman, "Tarih:", "IslemTarih")
        self._add_lbl_input(h_zaman, "Saat:", "IslemSaat")
        self.inputs["IslemSaat"].setText(datetime.now().strftime("%H:%M"))
        form.addLayout(h_zaman)

        # Yapan / Tür
        h_personel = QHBoxLayout()
        self._add_lbl_input(h_personel, "Yapan:", "IslemYapan")
        self._add_lbl_combo(h_personel, "Tür:", "IslemTuru", [])
        form.addLayout(h_personel)

        # Yapılan İşlem
        lbl_yapilan = QLabel("Yapılan İşlem:")
        lbl_yapilan.setStyleSheet("color:#aaa; font-size:11px;")
        self.inputs["YapilanIslem"] = QTextEdit()
        self.inputs["YapilanIslem"].setStyleSheet(S["input"])
        self.inputs["YapilanIslem"].setMinimumHeight(80)
        form.addWidget(lbl_yapilan)
        form.addWidget(self.inputs["YapilanIslem"])

        # Durum
        self._add_lbl_combo(form, "Yeni Durum:", "YeniDurum", [])

        # Rapor Dosyası
        lbl_rapor = QLabel("Rapor (Opsiyonel):")
        lbl_rapor.setStyleSheet("color:#aaa; font-size:11px;")
        form.addWidget(lbl_rapor)
        
        h_rapor = QHBoxLayout()
        self.txt_rapor_yolu = QLineEdit()
        self.txt_rapor_yolu.setReadOnly(True)
        self.txt_rapor_yolu.setPlaceholderText("Dosya seçilmedi")
        self.txt_rapor_yolu.setStyleSheet(S["input"])
        
        self.btn_rapor_sec = QPushButton("Seç")
        self.btn_rapor_sec.setFixedSize(50, 30)
        self.btn_rapor_sec.setStyleSheet(S["file_btn"])
        self.btn_rapor_sec.clicked.connect(self.rapor_dosyasi_sec)
        
        h_rapor.addWidget(self.txt_rapor_yolu)
        h_rapor.addWidget(self.btn_rapor_sec)
        form.addLayout(h_rapor)

        main_layout.addLayout(form)

        # Progress
        self.progress = QProgressBar()
        self.progress.setFixedHeight(5)
        self.progress.setTextVisible(False)
        self.progress.setStyleSheet(S.get("progress", ""))
        main_layout.addWidget(self.progress)

        # Butonlar
        h_btn = QHBoxLayout()
        self.btn_kapat = QPushButton("Vazgeç")
        self.btn_kapat.setStyleSheet(S["cancel_btn"])
        self.btn_kapat.clicked.connect(self.kapanma_istegi.emit)
        
        self.btn_kaydet = QPushButton("Kaydet")
        self.btn_kaydet.setStyleSheet(S["save_btn"])
        self.btn_kaydet.clicked.connect(self.kaydet_baslat)
        
        h_btn.addWidget(self.btn_kapat)
        h_btn.addWidget(self.btn_kaydet)
        main_layout.addLayout(h_btn)

        main_layout.addStretch()

    # ─── Yardımcılar ──────────────────────────────────────────

    def _add_lbl_input(self, layout, text, key, read_only=False):
        col = QVBoxLayout()
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(2)
        lbl = QLabel(text)
        lbl.setStyleSheet("color:#aaa; font-size:11px;")
        w = QLineEdit()
        w.setStyleSheet(S["input"])
        if read_only:
            w.setReadOnly(True)
        self.inputs[key] = w
        col.addWidget(lbl)
        col.addWidget(w)
        layout.addLayout(col, 1)

    def _add_lbl_combo(self, layout, text, key, items):
        col = QVBoxLayout()
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(2)
        lbl = QLabel(text)
        lbl.setStyleSheet("color:#aaa; font-size:11px;")
        cb = QComboBox()
        cb.addItems(items)
        cb.setStyleSheet(S["combo"])
        self.inputs[key] = cb
        col.addWidget(lbl)
        col.addWidget(cb)
        layout.addLayout(col, 1)

    def _add_lbl_date(self, layout, text, key):
        col = QVBoxLayout()
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(2)
        lbl = QLabel(text)
        lbl.setStyleSheet("color:#aaa; font-size:11px;")
        de = QDateEdit()
        de.setCalendarPopup(True)
        de.setDisplayFormat("dd.MM.yyyy")
        de.setDate(QDate.currentDate())
        de.setStyleSheet(S["date"])

        # Takvim popup düzeltmesi
        cal = de.calendarWidget()
        cal.setMinimumWidth(350)
        cal.setMinimumHeight(250)
        cal.setStyleSheet("""
            QCalendarWidget {
                background-color: #1e202c;
                color: #e0e2ea;
            }
            QCalendarWidget QToolButton {
                background-color: #1e202c;
                color: #e0e2ea;
                border: none; padding: 6px 10px;
                font-size: 13px; font-weight: bold;
            }
            QCalendarWidget QToolButton:hover {
                background-color: rgba(29, 117, 254, 0.3);
                border-radius: 4px;
            }
            QCalendarWidget QMenu {
                background-color: #1e202c; color: #e0e2ea;
            }
            QCalendarWidget QSpinBox {
                background-color: #1e202c; color: #e0e2ea;
                border: 1px solid #292b41; font-size: 13px;
            }
            QCalendarWidget QAbstractItemView {
                background-color: #1e202c;
                color: #c8cad0;
                selection-background-color: rgba(29, 117, 254, 0.4);
                selection-color: #ffffff;
                font-size: 13px;
                outline: none;
            }
            QCalendarWidget QAbstractItemView:enabled {
                color: #c8cad0;
            }
            QCalendarWidget QAbstractItemView:disabled {
                color: #5a5d6e;
            }
            QCalendarWidget #qt_calendar_navigationbar {
                background-color: #16172b;
                border-bottom: 1px solid rgba(255,255,255,0.08);
                padding: 4px;
            }
        """)
        cal.setVerticalHeaderFormat(cal.VerticalHeaderFormat.NoVerticalHeader)

        self.inputs[key] = de
        col.addWidget(lbl)
        col.addWidget(de)
        layout.addLayout(col, 1)

    # --- MANTIK ---
    def yukle(self, ariza_id):
        self.ariza_id = str(ariza_id).strip()
        self.lbl_baslik.setText(f"Arıza No: {self.ariza_id}")
        self.verileri_yukle()

    def verileri_yukle(self):
        self.progress.setVisible(True)
        self.progress.setRange(0, 0)
        self.loader = VeriYukleyici(self.ariza_id)
        self.loader.veri_hazir.connect(self.verileri_doldur)
        self.loader.hata_olustu.connect(self.hata_goster)
        self.loader.start()

    def verileri_doldur(self, ariza_info, gecmis, islem_turleri, durum_secenekleri):
        self.progress.setRange(0, 100); self.progress.setValue(100)
        self.ariza_data = ariza_info
        
        self.inputs["IslemTuru"].clear(); self.inputs["IslemTuru"].addItems(islem_turleri)
        self.inputs["YeniDurum"].clear(); self.inputs["YeniDurum"].addItems(durum_secenekleri)
        self.secilen_rapor_yolu = None

        if not ariza_info:
            QMessageBox.critical(self, "Hata", "Arıza kaydı bulunamadı!")
            self.close()
            return

        def get_val(key_list):
            for k in key_list:
                if k in ariza_info: return str(ariza_info[k])
            return "-"

        self.inputs["CihazID"].setText(get_val(["CihazID", "Cihazid"]))
        self.inputs["Tarih"].setText(get_val(["Tarih", "BaslangicTarihi"]))
        detay = get_val(["Aciklama", "ariza_acikla", "ArizaAcikla"])
        self.inputs["Aciklama"].setText(detay)
        
        mevcut_durum = get_val(["Durum", "durum"])
        index = self.inputs["YeniDurum"].findText(mevcut_durum)
        if index >= 0: self.inputs["YeniDurum"].setCurrentIndex(index)

        # 🛑 KAPALI KONTROLÜ
        self.ariza_kapali_mi = "kapalı" in mevcut_durum.lower()
        if self.ariza_kapali_mi:
            self.form_durumunu_ayarla(kapali=True)
        else:
            self.form_durumunu_ayarla(kapali=False)

        # GEÇMİŞ
        log_text = ""
        if gecmis:
            for islem in gecmis:
                zaman = f"{islem.get('Tarih', '')} {islem.get('Saat', '')}".strip()
                yapan = islem.get("IslemYapan", "")
                tur = islem.get("IslemTuru", "")
                detay = islem.get("YapilanIslem", "")
                rapor = islem.get("Rapor", "")
                
                log_text += f"[{zaman}] {yapan} ({tur}): {detay}"
                if rapor: log_text += " [📄 Rapor Var]"
                log_text += "\n"
       

    def form_durumunu_ayarla(self, kapali):
        """Eğer arıza kapalıysa inputları kapat, sadece rapor yüklemeye izin ver."""
        durum = not kapali # Aktif mi?
        
        self.inputs["IslemTarih"].setEnabled(durum)
        self.inputs["IslemSaat"].setEnabled(durum)
        self.inputs["IslemYapan"].setEnabled(durum)
        self.inputs["IslemTuru"].setEnabled(durum)
        self.inputs["YapilanIslem"].setReadOnly(kapali)
        self.inputs["YeniDurum"].setEnabled(durum)
        
        if kapali:
            self.lbl_mudahale.setText("🔒 Arıza Kapatılmış (Sadece Rapor Eklenebilir)")
            self.lbl_mudahale.setStyleSheet("color: #e57373; font-weight: bold; font-size: 13px; margin-top: 5px;")
            self.btn_kaydet.setText("Raporu Kaydet")
            # Arkaplanları gri yapalım ki kapalı olduğu anlaşılsın
            disabled_style = "background: rgba(255,255,255,0.05); color: #666; border: 1px solid #333;"
            self.inputs["IslemYapan"].setStyleSheet(disabled_style)
            self.inputs["YapilanIslem"].setStyleSheet(disabled_style)
        else:
            self.lbl_mudahale.setText("🛠️ Müdahale ve Çözüm Girişi")
            self.lbl_mudahale.setStyleSheet("color:#4CAF50; font-weight:bold; font-size:12px;")
            self.btn_kaydet.setText("Kaydet")

    def rapor_dosyasi_sec(self):
        yol, _ = QFileDialog.getOpenFileName(self, "Rapor Dosyası Seç", "", "PDF ve Resimler (*.pdf *.jpg *.png)")
        if yol:
            self.secilen_rapor_yolu = yol
            dosya_adi = os.path.basename(yol)
            self.txt_rapor_yolu.setText(dosya_adi)
            self.txt_rapor_yolu.setStyleSheet("color: #4caf50; font-weight: bold;")

    def kaydet_baslat(self):
        if self.ariza_kapali_mi:
            if not self.secilen_rapor_yolu:
                QMessageBox.warning(self, "Uyarı", "Bu arıza kapatılmıştır. Sadece rapor dosyası yükleyebilirsiniz.")
                return
        else:
            yapan = self.inputs["IslemYapan"].text().strip()
            yapilan = self.inputs["YapilanIslem"].toPlainText().strip()
            if not yapan or not yapilan:
                QMessageBox.warning(self, "Eksik", "Lütfen 'İşlemi Yapan' ve 'Yapılan İşlem' alanlarını doldurun.")
                return

        self.btn_kaydet.setText("Kaydediliyor...")
        self.btn_kaydet.setEnabled(False)
        self.progress.setRange(0, 0)

        if self.secilen_rapor_yolu:
            cihaz_id = self.ariza_data.get("Cihazid", "BilinmeyenCihaz")
            self.uploader = DosyaYukleyici(self.secilen_rapor_yolu, cihaz_id, self.ariza_id, self)
            self.uploader.yuklendi.connect(self._kaydet_devam)
            self.uploader.hata_olustu.connect(self._on_upload_error)
            self.uploader.start()
        else:
            self._kaydet_devam("") # Rapor linki yok

    def _kaydet_devam(self, rapor_link):
        if self.ariza_kapali_mi:
            yapan = "Sistem"
            yapilan = "Arıza kapalıyken sonradan rapor eklendi."
            tur = "Rapor Ekleme"
            yeni_durum = self.inputs["YeniDurum"].currentText()
        else:
            yapan = self.inputs["IslemYapan"].text().strip()
            yapilan = self.inputs["YapilanIslem"].toPlainText().strip()
            tur = self.inputs["IslemTuru"].currentText()
            yeni_durum = self.inputs["YeniDurum"].currentText()

        islem_verisi = {
            "Arizaid": self.ariza_id,
            "IslemYapan": yapan,
            "Tarih": self.inputs["IslemTarih"].date().toString("yyyy-MM-dd"),
            "Saat": self.inputs["IslemSaat"].text(),
            "IslemTuru": tur,
            "YapilanIslem": yapilan,
            "YeniDurum": yeni_durum,
            "Rapor": rapor_link
        }
        
        self.saver = IslemKaydedici(islem_verisi)
        self.saver.islem_tamam.connect(self.kayit_basarili)
        self.saver.hata_olustu.connect(self.hata_goster)
        self.saver.start()

    def kayit_basarili(self):
        self.progress.setRange(0, 100)
        QMessageBox.information(self, "Başarılı", "Kayıt işlemi tamamlandı.")
        if self.ana_pencere and hasattr(self.ana_pencere, 'verileri_yenile'):
            self.ana_pencere.verileri_yenile()
        self.kapanma_istegi.emit()

    def _on_upload_error(self, hata_mesaji):
        QMessageBox.warning(self, "Dosya Yükleme Hatası", hata_mesaji)
        self._kaydet_devam("") # Dosya yüklenemese de işlemi kaydet

    def hata_goster(self, msg):
        self.progress.setRange(0, 100)
        QMessageBox.critical(self, "Hata", msg)
        self.btn_kaydet.setEnabled(True)
        self.btn_kaydet.setText("Kaydet")

    def closeEvent(self, event):
        if hasattr(self, 'loader') and self.loader.isRunning(): self.loader.quit(); self.loader.wait(500)
        if hasattr(self, 'saver') and self.saver.isRunning(): self.saver.quit(); self.saver.wait(500)
        if hasattr(self, 'uploader') and self.uploader.isRunning(): self.uploader.quit(); self.uploader.wait(500)
        event.accept()
