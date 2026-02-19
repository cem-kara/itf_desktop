# -*- coding: utf-8 -*-
"""
Arıza Ekle Paneli (Gömülebilir Widget)
────────────────────────────────────────
- Cihaz listesinden çağrılır.
- Google Drive'a dosya yükleme desteği içerir.
- Tutarlı bir UI/UX sunar.
"""
import os
from datetime import datetime

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QComboBox,
    QPushButton, QProgressBar, QTextEdit, QMessageBox,
    QFileDialog
)

from core.logger import logger
from ui.theme_manager import ThemeManager
from ui.styles import DarkTheme
from ui.styles.icons import IconRenderer

S = ThemeManager.get_all_component_styles()

ARIZA_TIPLERI = [
    "Donanımsal Arıza", "Yazılımsal Arıza", "Kullanıcı Hatası",
    "Ağ / Bağlantı Sorunu", "Parça Değişimi", "Periyodik Bakım Talebi", "Diğer"
]
ONCELIK_DURUMLARI = ["Düşük", "Normal", "Yüksek", "Acil (Kritik)"]

# ─── Thread: Dosya Yükleme ────────────────────────────────────

class DosyaYukleyici(QThread):
    yuklendi = Signal(list)  # [link1, link2, ...]
    hata_olustu = Signal(str)

    def __init__(self, dosya_yollari: list, cihaz_id: str, ariza_id: str, parent=None):
        super().__init__(parent)
        self._yollar = dosya_yollari
        self._cihaz_id = cihaz_id
        self._ariza_id = ariza_id

    def run(self):
        db = None
        try:
            from core.di import get_cloud_adapter, get_registry
            from database.sqlite_manager import SQLiteManager
            from database.google.utils import resolve_storage_target

            cloud = get_cloud_adapter()
            
            db = SQLiteManager()
            registry = get_registry(db)
            all_sabit = registry.get("Sabitler").get_all()
            target = resolve_storage_target(all_sabit, "Cihaz_Ariza")

            parent_id = None
            if cloud.is_online:
                root_id = cloud.get_folder_id("Cihazlar") or target.get("drive_folder_id")
                cihaz_folder_id = cloud.find_or_create_folder(self._cihaz_id, root_id)
                ariza_folder_id = cloud.find_or_create_folder(self._ariza_id, cihaz_folder_id)
                parent_id = ariza_folder_id

            links = []
            for i, yol in enumerate(self._yollar):
                dosya_adi = f"{self._ariza_id}_ek_{i+1}{os.path.splitext(yol)[1]}"
                link = cloud.upload_file(
                    yol, 
                    parent_folder_id=parent_id, 
                    custom_name=dosya_adi,
                    offline_folder_name=target.get("offline_folder_name")
                )
                if link:
                    links.append(str(link))
            self.yuklendi.emit(links)
        except Exception as e:
            logger.error(f"Drive yükleme hatası: {e}")
            self.hata_olustu.emit(f"Dosya yüklenemedi: {e}")
        finally:
            if db: db.close()

# ─── Thread: Veritabanı Kaydı ─────────────────────────────────

class KayitIslemi(QThread):
    islem_tamam = Signal()
    hata_olustu = Signal(str)

    def __init__(self, veri: dict, parent=None):
        super().__init__(parent)
        self._veri = veri

    def run(self):
        from database.sqlite_manager import SQLiteManager
        db = None
        try:
            db = SQLiteManager()
            from core.di import get_registry
            repo = get_registry(db).get("Cihaz_Ariza")
            repo.insert(self._veri)
            self.islem_tamam.emit()
        except Exception as e:
            logger.error(f"Arıza kayıt hatası: {e}")
            self.hata_olustu.emit(str(e))
        finally:
            if db: db.close()

# ═══════════════════════════════════════════════
#  GÖMÜLEBİLİR PANEL
# ═══════════════════════════════════════════════

class ArizaEklePanel(QWidget):
    kapanma_istegi        = Signal()
    kayit_basarili_sinyali = Signal()

    def __init__(self, db=None, parent=None):
        super().__init__(parent)
        self._db = db
        self.setMinimumWidth(400)
        self.inputs = {}
        self._secilen_dosyalar = []
        self._setup_ui()

    def _setup_ui(self):
        main = QVBoxLayout(self)
        main.setContentsMargins(15, 15, 15, 15)
        main.setSpacing(12)

        lbl_baslik = QLabel("Arıza Bildirimi")
        lbl_baslik.setStyleSheet(S["header_name"])
        main.addWidget(lbl_baslik)

        form = QVBoxLayout(); form.setSpacing(10)
        self.inputs["Arizaid"] = QLineEdit(); self.inputs["Arizaid"].setVisible(False)
        form.addWidget(self.inputs["Arizaid"])

        self._add_lbl_input(form, "İlgili Cihaz:", "Cihazid", read_only=True)

        self._add_lbl_input(form, "Bildiren:", "Bildiren")
        self._add_lbl_input(form, "Konu / Başlık:", "Baslik", placeholder="Kısaca sorun nedir?")

        h_row = QHBoxLayout()
        self._add_lbl_combo(h_row, "Tip:", "ArizaTipi", ARIZA_TIPLERI)
        self._add_lbl_combo(h_row, "Öncelik:", "Oncelik", ONCELIK_DURUMLARI)
        form.addLayout(h_row)

        lbl_acik = QLabel("Açıklama:"); lbl_acik.setStyleSheet(S["label"])
        self.inputs["ArizaAcikla"] = QTextEdit(); self.inputs["ArizaAcikla"].setStyleSheet(S["input"]); self.inputs["ArizaAcikla"].setMinimumHeight(80)
        form.addWidget(lbl_acik); form.addWidget(self.inputs["ArizaAcikla"])

        # Dosya Ekleme
        lbl_dosya = QLabel("Görsel / Tutanak Ekleri:"); lbl_dosya.setStyleSheet(S["label"])
        form.addWidget(lbl_dosya)
        h_dosya = QHBoxLayout()
        self.btn_dosya_sec = QPushButton("Dosya Sec"); self.btn_dosya_sec.setStyleSheet(S["file_btn"]); self.btn_dosya_sec.clicked.connect(self._dosya_sec)
        IconRenderer.set_button_icon(self.btn_dosya_sec, "upload", color=DarkTheme.TEXT_PRIMARY, size=14)
        self.lbl_dosya_durum = QLabel("Dosya secilmedi"); self.lbl_dosya_durum.setStyleSheet(f"color: {DarkTheme.TEXT_MUTED}; font-style: italic; margin-left:10px;")
        h_dosya.addWidget(self.btn_dosya_sec); h_dosya.addWidget(self.lbl_dosya_durum, 1)
        form.addLayout(h_dosya)

        main.addLayout(form)

        self.progress = QProgressBar(); self.progress.setFixedHeight(5); self.progress.setTextVisible(False); self.progress.setStyleSheet(S.get("progress", "")); self.progress.setVisible(False)
        main.addWidget(self.progress)

        h_btn = QHBoxLayout()
        btn_vazgec = QPushButton("Vazgeç"); btn_vazgec.setStyleSheet(S["cancel_btn"]); btn_vazgec.clicked.connect(self.kapanma_istegi.emit)
        self.btn_kaydet = QPushButton("Kaydet"); self.btn_kaydet.setStyleSheet(S["save_btn"]); self.btn_kaydet.clicked.connect(self._kaydet_baslat)
        h_btn.addWidget(btn_vazgec); h_btn.addWidget(self.btn_kaydet)
        main.addLayout(h_btn)
        main.addStretch()

    def _add_lbl_input(self, layout, text: str, key: str, read_only=False, placeholder=""):
        lbl = QLabel(text); lbl.setStyleSheet(S["label"])
        w = QLineEdit(); w.setStyleSheet(S["input"]); w.setReadOnly(read_only); w.setPlaceholderText(placeholder)
        self.inputs[key] = w
        layout.addWidget(lbl); layout.addWidget(w)

    def _add_lbl_combo(self, layout, text: str, key: str, items: list):
        col = QVBoxLayout(); col.setContentsMargins(0, 0, 0, 0); col.setSpacing(2)
        lbl = QLabel(text); lbl.setStyleSheet(S["label"])
        cb = QComboBox(); cb.addItems(items); cb.setStyleSheet(S["combo"])
        self.inputs[key] = cb
        col.addWidget(lbl); col.addWidget(cb)
        layout.addLayout(col)

    def formu_sifirla(self, cihaz_id: str):
        self.inputs["Cihazid"].setText(cihaz_id)
        self.inputs["Arizaid"].setText(f"ARZ-{datetime.now().strftime('%Y%m%d-%H%M%S')}")
        self.inputs["Baslik"].clear()
        self.inputs["ArizaAcikla"].clear()
        self.inputs["Bildiren"].clear()
        self.inputs["ArizaTipi"].setCurrentIndex(0)
        self.inputs["Oncelik"].setCurrentIndex(0)
        self._secilen_dosyalar = []
        self.lbl_dosya_durum.setText("Dosya secilmedi"); self.lbl_dosya_durum.setStyleSheet(f"color: {DarkTheme.TEXT_MUTED}; font-style: italic; margin-left:10px;")
        self.btn_kaydet.setEnabled(True); self.btn_kaydet.setText("Kaydet")
        self.progress.setVisible(False)

    def _dosya_sec(self):
        yollar, _ = QFileDialog.getOpenFileNames(self, "Dosya Seç", "", "Resim/PDF (*.jpg *.png *.pdf)")
        if yollar:
            self._secilen_dosyalar = yollar
            self.lbl_dosya_durum.setText(f"{len(yollar)} dosya seçildi.")
            self.lbl_dosya_durum.setStyleSheet(f"color: {DarkTheme.STATUS_SUCCESS}; font-weight: bold; margin-left:10px;")

    def _kaydet_baslat(self):
        if not self.inputs["Baslik"].text().strip():
            QMessageBox.warning(self, "Eksik Alan", "Lütfen 'Konu' alanını doldurun.")
            return

        self.btn_kaydet.setEnabled(False); self.btn_kaydet.setText("Kaydediliyor...")
        self.progress.setVisible(True); self.progress.setRange(0, 0)

        if self._secilen_dosyalar:
            self.uploader = DosyaYukleyici(
                self._secilen_dosyalar,
                self.inputs["Cihazid"].text(),
                self.inputs["Arizaid"].text(),
                self
            )
            self.uploader.yuklendi.connect(self._kaydet_devam)
            self.uploader.hata_olustu.connect(self._on_hatali)
            self.uploader.start()
        else:
            self._kaydet_devam([])

    def _kaydet_devam(self, dosya_linkleri: list):
        veri = {
            "Arizaid": self.inputs["Arizaid"].text(),
            "Cihazid": self.inputs["Cihazid"].text(),
            "BaslangicTarihi": datetime.now().strftime("%Y-%m-%d"),
            "Saat": datetime.now().strftime("%H:%M"),
            "Bildiren": self.inputs["Bildiren"].text().strip(),
            "ArizaTipi": self.inputs["ArizaTipi"].currentText(),
            "Oncelik": self.inputs["Oncelik"].currentText(),
            "Baslik": self.inputs["Baslik"].text().strip(),
            "ArizaAcikla": self.inputs["ArizaAcikla"].toPlainText(),
            "Durum": "Açık",
            "Rapor": ";".join(dosya_linkleri) if dosya_linkleri else "",
        }
        self._saver = KayitIslemi(veri, self)
        self._saver.islem_tamam.connect(self._on_basarili)
        self._saver.hata_olustu.connect(self._on_hatali)
        self._saver.start()

    def _on_basarili(self):
        self.progress.setRange(0, 100); self.progress.setValue(100)
        logger.info(f"Arıza kaydedildi: {self.inputs['Arizaid'].text()}")
        QMessageBox.information(self, "Başarılı", "Arıza kaydı oluşturuldu.")
        self.kayit_basarili_sinyali.emit()
        self.kapanma_istegi.emit()

    def _on_hatali(self, mesaj: str):
        self.progress.setVisible(False)
        self.btn_kaydet.setEnabled(True); self.btn_kaydet.setText("Kaydet")
        QMessageBox.critical(self, "Hata", mesaj)
