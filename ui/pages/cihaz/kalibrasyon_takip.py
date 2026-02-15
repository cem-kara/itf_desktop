# -*- coding: utf-8 -*-
import time
import datetime
import os
from dateutil.relativedelta import relativedelta

from PySide6.QtCore import Qt, QDate, QThread, Signal, QUrl
from PySide6.QtGui import QColor, QDesktopServices, QCursor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QLineEdit, QSpinBox,
    QComboBox, QDateEdit, QTextEdit, QFileDialog, QProgressBar, QGroupBox,
    QCompleter, QAbstractItemView, QMessageBox
)

from core.logger import logger
from core.hata_yonetici import exc_logla
from ui.theme_manager import ThemeManager

S = ThemeManager.get_all_component_styles()

# ═══════════════════════════════════════════════
#  THREAD SINIFLARI
# ═══════════════════════════════════════════════

class KalibrasyonVeriYukleyici(QThread):
    veri_hazir = Signal(list, dict, list, list)
    hata_olustu = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

    def run(self):
        from database.sqlite_manager import SQLiteManager
        db = None
        try:
            db = SQLiteManager()
            from database.repository_registry import RepositoryRegistry
            registry = RepositoryRegistry(db)

            cihaz_combo = []
            cihaz_dict = {}
            for c in registry.get("Cihazlar").get_all():
                c_id = str(c.get("Cihazid", "")).strip()
                if not c_id: continue
                cihaz_combo.append(f"{c_id} | {c.get('Marka', '')} {c.get('Model', '')}".strip())
                cihaz_dict[c_id] = f"{c.get('Marka', '')} {c.get('Model', '')}".strip()

            sabitler_repo = registry.get("Sabitler")
            all_sabit = sabitler_repo.get_all()
            firmalar = [s.get("MenuEleman") for s in all_sabit if s.get("Kod") == "firmalar"]

            kalibrasyonlar = registry.get("Kalibrasyon").get_all()
            kalibrasyonlar.sort(key=lambda x: x.get("YapilanTarih", ""), reverse=True)

            self.veri_hazir.emit(sorted(cihaz_combo), cihaz_dict, sorted(firmalar), kalibrasyonlar)
        except Exception as e:
            logger.error(f"Kalibrasyon veri yükleme hatası: {e}")
            self.hata_olustu.emit(str(e))
        finally:
            if db: db.close()

class KalibrasyonKaydedici(QThread):
    islem_tamam = Signal()
    hata_olustu = Signal(str)

    def __init__(self, veri, mod="yeni", kayit_id=None, parent=None):
        super().__init__(parent)
        self._veri     = veri
        self._mod      = mod
        self._kayit_id = kayit_id

    def run(self):
        from database.sqlite_manager import SQLiteManager
        db = None
        try:
            db = SQLiteManager()
            from database.repository_registry import RepositoryRegistry
            repo = RepositoryRegistry(db).get("Kalibrasyon")

            if self._mod == "yeni":
                for satir in self._veri:
                    repo.insert(satir)
            elif self._mod == "guncelle":
                repo.update(self._kayit_id, self._veri)

            self.islem_tamam.emit()
        except Exception as e:
            exc_logla("KalibrasyonKaydedici.run", e)
            self.hata_olustu.emit(str(e))
        finally:
            if db: db.close()

class DosyaYukleyici(QThread):
    yuklendi = Signal(str)
    def __init__(self, yerel_yol: str, parent=None):
        super().__init__(parent)
        self._yol = yerel_yol

    def run(self):
        try:
            from database.google import GoogleDriveService
            link = GoogleDriveService().upload_file(self._yol)
            self.yuklendi.emit(link if link else "-")
        except Exception as e:
            logger.warning(f"Drive yükleme başarısız (devam ediliyor): {e}")
            self.yuklendi.emit("-")

# ═══════════════════════════════════════════════
#  ANA SAYFA
# ═══════════════════════════════════════════════

class KalibrasyonTakipPage(QWidget):

    def __init__(self, db=None, parent=None):
        super().__init__(parent)
        self.setStyleSheet(S["page"])
        self._db = db

        self.inputs = {}
        self.cihaz_sozlugu = {}
        self.tum_kalibrasyonlar = []
        
        self.secilen_dosya = None
        self.mevcut_link = "-"
        self.duzenleme_modu = False
        self.duzenlenen_id = None

        self._setup_ui()
        self.load_data()

    def _setup_ui(self):
        main = QHBoxLayout(self)
        main.setContentsMargins(15, 15, 15, 15)
        main.setSpacing(20)

        sol = QWidget(); sol.setFixedWidth(430)
        sol_l = QVBoxLayout(sol); sol_l.setContentsMargins(0,0,0,0); sol_l.setSpacing(12)

        card_cihaz = QGroupBox("Cihaz ve Firma")
        card_cihaz.setStyleSheet(S["group"] + f"QGroupBox {{ color: {ThemeManager.get_color('BLUE_500')}; }}")
        card_cihaz_layout = QVBoxLayout(card_cihaz)
        card_cihaz_layout.setContentsMargins(15, 22, 15, 15); card_cihaz_layout.setSpacing(10)

        self.inputs["Cihazid"] = QComboBox(); self.inputs["Cihazid"].setEditable(True)
        self.inputs["Cihazid"].setInsertPolicy(QComboBox.NoInsert)
        self.inputs["Cihazid"].setPlaceholderText("ID veya Marka ile ara...")
        self.inputs["Cihazid"].setStyleSheet(S["combo"])
        comp = self.inputs["Cihazid"].completer(); comp.setCompletionMode(QCompleter.PopupCompletion); comp.setFilterMode(Qt.MatchContains)
        lbl_cihaz = QLabel("Cihaz Seçimi:"); lbl_cihaz.setStyleSheet(S["label"])
        card_cihaz_layout.addWidget(lbl_cihaz); card_cihaz_layout.addWidget(self.inputs["Cihazid"])

        self.inputs["Firma"] = QComboBox(); self.inputs["Firma"].setEditable(True); self.inputs["Firma"].setStyleSheet(S["combo"])
        lbl_firma = QLabel("Firma / Kurum:"); lbl_firma.setStyleSheet(S["label"])
        card_cihaz_layout.addWidget(lbl_firma); card_cihaz_layout.addWidget(self.inputs["Firma"])
        sol_l.addWidget(card_cihaz)

        card_surec = QGroupBox("Sertifika ve Süreç")
        card_surec.setStyleSheet(S["group"] + f"QGroupBox {{ color: {ThemeManager.get_color('GREEN_500')}; }}")
        card_surec_layout = QVBoxLayout(card_surec)
        card_surec_layout.setContentsMargins(15, 22, 15, 15); card_surec_layout.setSpacing(10)

        self.inputs["SertifikaNo"] = QLineEdit(); self.inputs["SertifikaNo"].setStyleSheet(S["input"])
        lbl_sertifika = QLabel("Sertifika No:"); lbl_sertifika.setStyleSheet(S["label"])
        card_surec_layout.addWidget(lbl_sertifika); card_surec_layout.addWidget(self.inputs["SertifikaNo"])

        h_tarih = QHBoxLayout()
        self.inputs["YapilanTarih"] = QDateEdit(QDate.currentDate()); self.inputs["YapilanTarih"].setCalendarPopup(True); self.inputs["YapilanTarih"].setDisplayFormat("yyyy-MM-dd"); self.inputs["YapilanTarih"].setStyleSheet(S["date"]); ThemeManager.setup_calendar_popup(self.inputs["YapilanTarih"]); self.inputs["YapilanTarih"].dateChanged.connect(self._tarih_hesapla)
        v_islem_tarihi = QVBoxLayout(); v_islem_tarihi.setSpacing(3)
        lbl_islem_tarihi = QLabel("İşlem Tarihi:"); lbl_islem_tarihi.setStyleSheet(S["label"])
        v_islem_tarihi.addWidget(lbl_islem_tarihi); v_islem_tarihi.addWidget(self.inputs["YapilanTarih"])
        h_tarih.addLayout(v_islem_tarihi)

        self.inputs["GecerlilikSuresi"] = QComboBox(); self.inputs["GecerlilikSuresi"].addItems(["1 Yıl", "6 Ay", "2 Yıl", "3 Yıl", "Tek Seferlik"]); self.inputs["GecerlilikSuresi"].setStyleSheet(S["combo"]); self.inputs["GecerlilikSuresi"].currentTextChanged.connect(self._tarih_hesapla)
        v_gecerlilik = QVBoxLayout(); v_gecerlilik.setSpacing(3)
        lbl_gecerlilik = QLabel("Geçerlilik:"); lbl_gecerlilik.setStyleSheet(S["label"])
        v_gecerlilik.addWidget(lbl_gecerlilik); v_gecerlilik.addWidget(self.inputs["GecerlilikSuresi"])
        h_tarih.addLayout(v_gecerlilik)

        self.inputs["DonemSayisi"] = QSpinBox(); self.inputs["DonemSayisi"].setRange(1, 10); self.inputs["DonemSayisi"].setValue(1); self.inputs["DonemSayisi"].setStyleSheet(S["input"])
        v_donem = QVBoxLayout(); v_donem.setSpacing(3)
        lbl_donem = QLabel("Dönem Sayısı:"); lbl_donem.setStyleSheet(S["label"])
        v_donem.addWidget(lbl_donem); v_donem.addWidget(self.inputs["DonemSayisi"])
        h_tarih.addLayout(v_donem)
        card_surec_layout.addLayout(h_tarih)

        self.inputs["BitisTarihi"] = QDateEdit(); self.inputs["BitisTarihi"].setReadOnly(True); self.inputs["BitisTarihi"].setDisplayFormat("yyyy-MM-dd"); self.inputs["BitisTarihi"].setStyleSheet(S["date"])
        lbl_bitis = QLabel("Bitiş Tarihi (Hesaplanan):"); lbl_bitis.setStyleSheet(S["label"])
        card_surec_layout.addWidget(lbl_bitis); card_surec_layout.addWidget(self.inputs["BitisTarihi"])
        sol_l.addWidget(card_surec)

        card_sonuc = QGroupBox("Durum ve Belge")
        card_sonuc.setStyleSheet(S["group"] + f"QGroupBox {{ color: {ThemeManager.get_color('ORANGE_500')}; }}")
        card_sonuc_layout = QVBoxLayout(card_sonuc)
        card_sonuc_layout.setContentsMargins(15, 22, 15, 15); card_sonuc_layout.setSpacing(10)

        self.inputs["Durum"] = QComboBox(); self.inputs["Durum"].addItems(["Planlandı", "Tamamlandı", "İptal"]); self.inputs["Durum"].setCurrentText("Planlandı"); self.inputs["Durum"].setStyleSheet(S["combo"])
        lbl_durum = QLabel("Durum:"); lbl_durum.setStyleSheet(S["label"])
        card_sonuc_layout.addWidget(lbl_durum); card_sonuc_layout.addWidget(self.inputs["Durum"])

        dosya_widget = QWidget()
        h_dosya = QHBoxLayout(dosya_widget); h_dosya.setContentsMargins(0,0,0,0)
        self.lbl_dosya = QLabel("Dosya Seçilmedi"); self.lbl_dosya.setStyleSheet("color: #888; font-style: italic;")
        btn_dosya_sec = QPushButton("📂 Seç"); btn_dosya_sec.setStyleSheet(S["file_btn"]); btn_dosya_sec.setCursor(QCursor(Qt.PointingHandCursor)); btn_dosya_sec.clicked.connect(self._dosya_sec)
        h_dosya.addWidget(self.lbl_dosya, 1); h_dosya.addWidget(btn_dosya_sec)
        lbl_sertifika_rapor = QLabel("Sertifika / Rapor Dosyası:"); lbl_sertifika_rapor.setStyleSheet(S["label"])
        card_sonuc_layout.addWidget(lbl_sertifika_rapor); card_sonuc_layout.addWidget(dosya_widget)

        self.inputs["Aciklama"] = QTextEdit(); self.inputs["Aciklama"].setPlaceholderText("Varsa notlar..."); self.inputs["Aciklama"].setStyleSheet(S["input"]); self.inputs["Aciklama"].setFixedHeight(60)
        lbl_aciklama = QLabel("Açıklama:"); lbl_aciklama.setStyleSheet(S["label"])
        card_sonuc_layout.addWidget(lbl_aciklama); card_sonuc_layout.addWidget(self.inputs["Aciklama"])
        sol_l.addWidget(card_sonuc)

        self.btn_temizle = QPushButton("Yeni Kayıt / Temizle"); self.btn_temizle.setStyleSheet(S["cancel_btn"]); self.btn_temizle.setCursor(QCursor(Qt.PointingHandCursor)); self.btn_temizle.clicked.connect(self.formu_temizle)
        sol_l.addWidget(self.btn_temizle)
        self.btn_kaydet = QPushButton("💾 KAYDET"); self.btn_kaydet.setMinimumHeight(48); self.btn_kaydet.setStyleSheet(S["save_btn"]); self.btn_kaydet.setCursor(QCursor(Qt.PointingHandCursor)); self.btn_kaydet.clicked.connect(self._kaydet_baslat)
        sol_l.addWidget(self.btn_kaydet)
        sol_l.addStretch()
        main.addWidget(sol)

        sag = QVBoxLayout()
        h_header = QHBoxLayout()
        self.txt_ara = QLineEdit()
        self.txt_ara.setPlaceholderText("🔍 Listede Ara...")
        self.txt_ara.setStyleSheet(S["search"])
        self.txt_ara.textChanged.connect(self._tabloyu_filtrele)

        btn_yenile = QPushButton("⟳ Yenile")
        btn_yenile.setFixedSize(100, 36)
        btn_yenile.setStyleSheet(S["refresh_btn"])
        btn_yenile.setCursor(QCursor(Qt.PointingHandCursor))
        btn_yenile.clicked.connect(self.load_data)

        self.btn_kapat = QPushButton("✕ Kapat")
        self.btn_kapat.setFixedSize(100, 36)
        self.btn_kapat.setStyleSheet(S["close_btn"])
        self.btn_kapat.setCursor(QCursor(Qt.PointingHandCursor))
        h_header.addWidget(self.txt_ara)
        h_header.addWidget(btn_yenile)
        h_header.addWidget(self.btn_kapat)
        sag.addLayout(h_header)

        self.tablo = QTableWidget()
        self.tablo.setColumnCount(6)
        self.tablo.setHorizontalHeaderLabels(["ID", "Cihaz", "Firma", "Bitiş Tarihi", "Durum", "Belge"])
        hdr = self.tablo.horizontalHeader()
        hdr.setSectionResizeMode(QHeaderView.Stretch)
        hdr.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(5, QHeaderView.ResizeToContents)

        self.tablo.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tablo.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tablo.verticalHeader().setVisible(False)
        self.tablo.setAlternatingRowColors(True)
        self.tablo.setStyleSheet(S["table"])
        self.tablo.cellClicked.connect(self._satir_secildi)
        sag.addWidget(self.tablo, 1)

        self.progress = QProgressBar()
        self.progress.setVisible(False)
        self.progress.setFixedHeight(4)
        self.progress.setTextVisible(False)
        self.progress.setStyleSheet(S.get("progress", ""))
        sag.addWidget(self.progress)
        main.addLayout(sag)

    def load_data(self):
        self.progress.setVisible(True); self.progress.setRange(0, 0)
        self._loader = KalibrasyonVeriYukleyici(self)
        self._loader.veri_hazir.connect(self._veriler_geldi)
        self._loader.hata_olustu.connect(self._hata_goster)
        self._loader.start()

    def _veriler_geldi(self, cihaz_combo, cihaz_dict, firmalar, kalibrasyon_listesi):
        self.progress.setVisible(False)
        self.cihaz_sozlugu = cihaz_dict
        self.tum_kalibrasyonlar = kalibrasyon_listesi
        
        mevcut_cihaz = self.inputs["Cihazid"].currentText()
        self.inputs["Cihazid"].blockSignals(True); self.inputs["Cihazid"].clear(); self.inputs["Cihazid"].addItems([""] + cihaz_combo); self.inputs["Cihazid"].setCurrentText(mevcut_cihaz); self.inputs["Cihazid"].blockSignals(False)
        
        self.inputs["Firma"].clear(); self.inputs["Firma"].addItems([""] + firmalar)
        self._tabloyu_guncelle()

    def _tabloyu_guncelle(self):
        self.tablo.setRowCount(0)
        for row in self.tum_kalibrasyonlar:
            r = self.tablo.rowCount(); self.tablo.insertRow(r)
            c_id = str(row.get("Cihazid", "")); c_ad = self.cihaz_sozlugu.get(c_id, c_id)
            bitis = str(row.get("BitisTarihi", "")); dosya = str(row.get("Sertifika", ""))
            self.tablo.setItem(r, 0, QTableWidgetItem(str(row.get("Kalid", ""))))
            self.tablo.setItem(r, 1, QTableWidgetItem(c_ad))
            self.tablo.setItem(r, 2, QTableWidgetItem(str(row.get("Firma", ""))))
            item_tarih = QTableWidgetItem(bitis)
            try:
                kalan = (datetime.datetime.strptime(bitis, "%Y-%m-%d").date() - datetime.date.today()).days
                if kalan < 0: item_tarih.setForeground(QColor(ThemeManager.get_color("RED_500")))
                elif kalan < 30: item_tarih.setForeground(QColor(ThemeManager.get_color("ORANGE_500")))
                else: item_tarih.setForeground(QColor(ThemeManager.get_color("GREEN_500")))
            except: pass
            self.tablo.setItem(r, 3, item_tarih)
            self.tablo.setItem(r, 4, QTableWidgetItem(str(row.get("Durum", ""))))
            item_link = QTableWidgetItem("📄 Belge" if "http" in dosya else "-")
            if "http" in dosya:
                item_link.setForeground(QColor(ThemeManager.get_color("BLUE_500"))); item_link.setToolTip(dosya)
            self.tablo.setItem(r, 5, item_link)
            self.tablo.item(r, 0).setData(Qt.UserRole, row)

    def _satir_secildi(self, row, col):
        item = self.tablo.item(row, 0); veri = item.data(Qt.UserRole) if item else None
        if not veri: return
        if col == 5 and "http" in str(veri.get("Sertifika", "")): QDesktopServices.openUrl(QUrl(veri.get("Sertifika"))); return

        self.duzenleme_modu = True; self.duzenlenen_id = str(veri.get("Kalid", "")); self.mevcut_link = str(veri.get("Sertifika", "-"))
        self.btn_kaydet.setText("GÜNCELLE"); self.btn_kaydet.setStyleSheet(S["edit_btn"])

        c_id = str(veri.get("Cihazid", ""))
        for i in range(self.inputs["Cihazid"].count()):
            if self.inputs["Cihazid"].itemText(i).startswith(c_id): self.inputs["Cihazid"].setCurrentIndex(i); break
        
        self.inputs["Firma"].setCurrentText(str(veri.get("Firma", "")))
        self.inputs["SertifikaNo"].setText(str(veri.get("SertifikaNo", "")))
        try:
            self.inputs["YapilanTarih"].setDate(QDate.fromString(str(veri.get("YapilanTarih", "")), "yyyy-MM-dd"))
            self.inputs["BitisTarihi"].setDate(QDate.fromString(str(veri.get("BitisTarihi", "")), "yyyy-MM-dd"))
        except: pass
        self.inputs["GecerlilikSuresi"].setCurrentText(str(veri.get("GecerlilikSuresi", "")))
        self.inputs["Durum"].setCurrentText(str(veri.get("Durum", "")))
        self.inputs["Aciklama"].setText(str(veri.get("Aciklama", "")))
        self.lbl_dosya.setText("Mevcut Dosya Kayıtlı" if "http" in self.mevcut_link else "Dosya Yok")
        self.lbl_dosya.setStyleSheet("color:#42a5f5; font-weight:bold;" if "http" in self.mevcut_link else "color: #888; font-style: italic;")

    def formu_temizle(self):
        self.duzenleme_modu = False; self.duzenlenen_id = None; self.mevcut_link = "-"
        self.btn_kaydet.setText("💾 KAYDET"); self.btn_kaydet.setStyleSheet(S["save_btn"])
        self.inputs["SertifikaNo"].clear(); self.inputs["Aciklama"].clear(); self.inputs["DonemSayisi"].setValue(1)
        self.inputs["Cihazid"].setCurrentIndex(0); self.inputs["Durum"].setCurrentText("Tamamlandı"); 
        self.secilen_dosya = None; self.lbl_dosya.setText("Dosya Seçilmedi"); self.lbl_dosya.setStyleSheet("color: #888; font-style: italic;")

    def _kaydet_baslat(self):
        cihaz_text = self.inputs["Cihazid"].currentText()
        if not cihaz_text: QMessageBox.warning(self, "Hata", "Lütfen bir cihaz seçiniz."); return
        cihaz_id = cihaz_text.split('|')[0].strip()
        self.btn_kaydet.setText("İşleniyor..."); self.btn_kaydet.setEnabled(False); self.progress.setVisible(True); self.progress.setRange(0, 0)
        if self.secilen_dosya:
            self.uploader = DosyaYukleyici(self.secilen_dosya, self); self.uploader.yuklendi.connect(lambda l: self._kaydet_devam(l, cihaz_id)); self.uploader.start()
        else:
            self._kaydet_devam(self.mevcut_link if self.duzenleme_modu else "-", cihaz_id)

    def _kaydet_devam(self, link, cihaz_id):
        try:
            if self.duzenleme_modu:
                yeni_satir = {
                    "Kalid": self.duzenlenen_id, "Cihazid": cihaz_id, "Firma": self.inputs["Firma"].currentText(),
                    "SertifikaNo": self.inputs["SertifikaNo"].text(), "YapilanTarih": self.inputs["YapilanTarih"].date().toString("yyyy-MM-dd"),
                    "GecerlilikSuresi": self.inputs["GecerlilikSuresi"].currentText(), "BitisTarihi": self.inputs["BitisTarihi"].date().toString("yyyy-MM-dd"),
                    "Durum": self.inputs["Durum"].currentText(), "Sertifika": link, "Aciklama": self.inputs["Aciklama"].toPlainText()
                }
                self.saver = KalibrasyonKaydedici(yeni_satir, mod="guncelle", kayit_id=self.duzenlenen_id, parent=self)
            else:
                donem_sayisi = self.inputs["DonemSayisi"].value()
                gecerlilik = self.inputs["GecerlilikSuresi"].currentText()
                
                ay_adim = 0
                if "6 Ay" in gecerlilik: ay_adim = 6
                elif "1 Yıl" in gecerlilik: ay_adim = 12
                elif "2 Yıl" in gecerlilik: ay_adim = 24
                elif "3 Yıl" in gecerlilik: ay_adim = 36
                
                if ay_adim == 0: donem_sayisi = 1

                satirlar = []
                base_id = int(time.time())
                baslangic_tarihi = self.inputs["YapilanTarih"].date().toPython()

                for i in range(donem_sayisi):
                    yeni_baslangic = baslangic_tarihi + relativedelta(months=i * ay_adim)
                    yeni_bitis = yeni_baslangic + relativedelta(months=ay_adim) if ay_adim > 0 else baslangic_tarihi
                    ilk_kayit = (i == 0)
                    
                    yeni_satir = {
                        "Kalid": f"KAL-{base_id + i}", "Cihazid": cihaz_id, "Firma": self.inputs["Firma"].currentText() if ilk_kayit else "",
                        "SertifikaNo": self.inputs["SertifikaNo"].text() if ilk_kayit else "", "YapilanTarih": yeni_baslangic.strftime("%Y-%m-%d"),
                        "GecerlilikSuresi": gecerlilik, "BitisTarihi": yeni_bitis.strftime("%Y-%m-%d"),
                        "Durum": self.inputs["Durum"].currentText() if ilk_kayit else "Planlandı",
                        "Sertifika": link if ilk_kayit else "", "Aciklama": self.inputs["Aciklama"].toPlainText() if ilk_kayit else "Otomatik planlandı."
                    }
                    satirlar.append(yeni_satir)
                
                self.saver = KalibrasyonKaydedici(satirlar, mod="yeni", parent=self)

            self.saver.islem_tamam.connect(self._islem_bitti); self.saver.hata_olustu.connect(self._hata_goster); self.saver.start()
        except Exception as e:
            exc_logla("KalibrasyonTakip._kaydet_devam", e)
            self._hata_goster(str(e))

    def _islem_bitti(self):
        self.progress.setVisible(False); self.btn_kaydet.setEnabled(True)
        msg = "Kalibrasyon güncellendi." if self.duzenleme_modu else "Kalibrasyon kaydedildi."
        QMessageBox.information(self, "Başarılı", msg); self.formu_temizle(); self.load_data()

    def _hata_goster(self, msg):
        self.progress.setVisible(False)
        self.btn_kaydet.setEnabled(True)
        self.btn_kaydet.setText("GÜNCELLE" if self.duzenleme_modu else "💾 KAYDET")
        logger.error(f"[KalibrasyonTakipPage] {msg}")
        QMessageBox.critical(self, "Hata", msg)

    def _tabloyu_filtrele(self, text):
        text = text.lower()
        for i in range(self.tablo.rowCount()):
            match = any(text in self.tablo.item(i, j).text().lower() for j in range(self.tablo.columnCount()) if self.tablo.item(i, j))
            self.tablo.setRowHidden(i, not match)

    def _dosya_sec(self):
        yol, _ = QFileDialog.getOpenFileName(self, "Belge Seç", "", "PDF ve Resim (*.pdf *.jpg *.png)")
        if yol: self.secilen_dosya = yol; self.lbl_dosya.setText(os.path.basename(yol)); self.lbl_dosya.setStyleSheet("color:#4caf50; font-weight:bold;")

    def _tarih_hesapla(self):
        try:
            baslangic = self.inputs["YapilanTarih"].date().toPython(); secim = self.inputs["GecerlilikSuresi"].currentText()
            bitis = baslangic
            if "6 Ay" in secim: bitis += relativedelta(months=6)
            elif "1 Yıl" in secim: bitis += relativedelta(years=1)
            elif "2 Yıl" in secim: bitis += relativedelta(years=2)
            elif "3 Yıl" in secim: bitis += relativedelta(years=3)
            self.inputs["BitisTarihi"].setDate(QDate(bitis.year, bitis.month, bitis.day))
        except: pass

    def closeEvent(self, event):
        for worker_name in ("_loader", "_saver", "uploader"):
            if hasattr(self, worker_name):
                worker = getattr(self, worker_name)
                if worker and worker.isRunning(): worker.quit(); worker.wait(500)
        event.accept()
