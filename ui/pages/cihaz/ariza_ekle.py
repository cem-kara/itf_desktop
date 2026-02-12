# -*- coding: utf-8 -*-
"""
Arıza Ekle Paneli  (Gömülebilir Widget)
────────────────────────────────────────
ArizaListesiPage içinde splitter'a gömülür.
  • formu_sifirla(cihaz_id)  → dışarıdan cihaz seçimi aktarır
  • kapanma_istegi           → Vazgeç / kayıt sonrası üst widget'ı bilgilendirir
  • kayit_basarili_sinyali   → listeyi yenile
"""
from datetime import datetime

from PySide6.QtCore import QDate, QThread, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QComboBox, QDateEdit,
    QPushButton, QProgressBar, QTextEdit, QMessageBox
)

from core.logger import logger
from ui.theme_manager import ThemeManager


S = ThemeManager.get_all_component_styles()

ARIZA_TIPLERI     = [
    "Donanımsal Arıza", "Yazılımsal Arıza", "Kullanıcı Hatası",
    "Ağ Sorunu", "Parça Değişimi", "Diğer"
]
ONCELIK_DURUMLARI = ["Düşük", "Normal", "Yüksek", "Acil (Kritik)"]


# ─── Thread: yeni Arıza ID üret ───────────────────────────────

class BaslangicYukleyici(QThread):
    veri_hazir = Signal(str)

    def __init__(self, db, parent=None):
        super().__init__(parent)
        self._db = db

    def run(self):
        try:
            yeni_id = f"ARZ-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
            self.veri_hazir.emit(yeni_id)
        except Exception as e:
            logger.error(f"ID üretme hatası: {e}")
            self.veri_hazir.emit("HATA")


# ─── Thread: Cihaz_Ariza tablosuna yaz ────────────────────────

class KayitIslemi(QThread):
    islem_tamam = Signal()
    hata_olustu = Signal(str)

    def __init__(self, veri: dict, parent=None):
        super().__init__(parent)
        self._veri = veri

    def run(self):
        # Her thread kendi bağlantısını açar — SQLite check_same_thread hatası önlenir
        from database.sqlite_manager import SQLiteManager
        db = None
        try:
            db = SQLiteManager()
            from database.repository_registry import RepositoryRegistry
            registry = RepositoryRegistry(db)
            repo     = registry.get("Cihaz_Ariza")
            repo.insert(self._veri)
            self.islem_tamam.emit()
        except Exception as e:
            logger.error(f"Arıza kayıt hatası: {e}")
            self.hata_olustu.emit(str(e))
        finally:
            if db:
                db.close()


# ═══════════════════════════════════════════════
#  GÖMÜLEBİLİR PANEL
# ═══════════════════════════════════════════════

class ArizaEklePanel(QWidget):
    """
    Kullanım::

        panel = ArizaEklePanel(db=db, kullanici_adi="Ahmet")
        panel.kapanma_istegi.connect(lambda: ...)
        panel.kayit_basarili_sinyali.connect(liste_sayfasi.load_data)
        panel.formu_sifirla("CIH-001")
    """
    kapanma_istegi        = Signal()
    kayit_basarili_sinyali = Signal()

    def __init__(self, db=None, parent=None):
        super().__init__(parent)
        self._db           = db

        self.setMinimumWidth(350)
        self.inputs = {}

        self._setup_ui()
        self._baslangic_yukle()

    # ─── UI ───────────────────────────────────────────────────

    def _setup_ui(self):
        main = QVBoxLayout(self)
        main.setContentsMargins(10, 10, 10, 10)
        main.setSpacing(10)

        # Başlık
        lbl_baslik = QLabel("Arıza Bildirimi")
        lbl_baslik.setFont(QFont("Segoe UI", 12, QFont.Bold))
        lbl_baslik.setStyleSheet(
            "color:#e57373; border-bottom:2px solid #444; padding-bottom:5px;"
        )
        main.addWidget(lbl_baslik)

        # Form
        form = QVBoxLayout()
        form.setSpacing(10)

        # Gizli: Arizaid
        self.inputs["Arizaid"] = QLineEdit()
        self.inputs["Arizaid"].setVisible(False)
        form.addWidget(self.inputs["Arizaid"])

        # Cihaz (salt okunur, dışarıdan formu_sifirla ile set edilir)
        self._add_lbl_input(form, "İlgili Cihaz:", "Cihazid")
        self.inputs["Cihazid"].setReadOnly(True)
        self.inputs["Cihazid"].setStyleSheet(
            "background:#333; color:#4dabf7; font-weight:bold; border:1px solid #555;"
        )

        # Bildiren
        self._add_lbl_input(form, "Bildiren:", "Bildiren")

        # Konu / Başlık
        self._add_lbl_input(form, "Konu:", "Baslik")
        self.inputs["Baslik"].setPlaceholderText("Kısaca sorun nedir?")

        # Tip + Öncelik
        h_row = QHBoxLayout()
        self._add_lbl_combo(h_row, "Tip:",      "ArizaTipi", ARIZA_TIPLERI)
        self._add_lbl_combo(h_row, "Öncelik:", "Oncelik",   ONCELIK_DURUMLARI)
        form.addLayout(h_row)

        # Tarih (gizli, otomatik bugün)
        self.inputs["BaslangicTarihi"] = QDateEdit(QDate.currentDate())
        self.inputs["BaslangicTarihi"].setVisible(False)
        form.addWidget(self.inputs["BaslangicTarihi"])

        # Açıklama
        lbl_acik = QLabel("Açıklama:")
        lbl_acik.setStyleSheet(S["label"])
        self.inputs["ArizaAcikla"] = QTextEdit()
        self.inputs["ArizaAcikla"].setStyleSheet(S["input"])
        self.inputs["ArizaAcikla"].setFixedHeight(80)
        form.addWidget(lbl_acik)
        form.addWidget(self.inputs["ArizaAcikla"])

        main.addLayout(form)

        # Progress
        self.progress = QProgressBar()
        self.progress.setFixedHeight(5)
        self.progress.setTextVisible(False)
        self.progress.setStyleSheet(S.get("progress", ""))
        main.addWidget(self.progress)

        # Butonlar
        h_btn = QHBoxLayout()
        btn_vazgec = QPushButton("Vazgeç")
        btn_vazgec.setStyleSheet(S["cancel_btn"])
        btn_vazgec.clicked.connect(self.formu_kapat)

        self.btn_kaydet = QPushButton("Kaydet")
        self.btn_kaydet.setStyleSheet(S["save_btn"])
        self.btn_kaydet.clicked.connect(self._kaydet_baslat)

        h_btn.addWidget(btn_vazgec)
        h_btn.addWidget(self.btn_kaydet)
        main.addLayout(h_btn)

        main.addStretch()

    # ─── Yardımcılar ──────────────────────────────────────────

    def _add_lbl_input(self, layout, text: str, key: str):
        lbl = QLabel(text)
        lbl.setStyleSheet("color:#aaa; font-size:11px;")
        w = QLineEdit()
        w.setStyleSheet(S["input"])
        self.inputs[key] = w
        layout.addWidget(lbl)
        layout.addWidget(w)

    def _add_lbl_combo(self, layout, text: str, key: str, items: list):
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
        layout.addLayout(col)

    # ─── Public API ───────────────────────────────────────────

    def formu_sifirla(self, cihaz_id: str):
        """Formu temizler ve cihaz ID'sini ayarlar. Dışarıdan çağrılır."""
        self.inputs["Cihazid"].setText(cihaz_id)
        self.inputs["Baslik"].clear()
        self.inputs["ArizaAcikla"].clear()
        self.inputs["ArizaTipi"].setCurrentIndex(0)
        self.inputs["Oncelik"].setCurrentIndex(0)
        self.btn_kaydet.setEnabled(True)
        self.btn_kaydet.setText("Kaydet")
        self._baslangic_yukle()

    def formu_kapat(self):
        """Vazgeç butonuna basılınca parent'a sinyal gönderir."""
        self.kapanma_istegi.emit()

    # ─── Mantık ───────────────────────────────────────────────

    def _baslangic_yukle(self):
        self.progress.setRange(0, 0)
        self._loader = BaslangicYukleyici(self._db, self)
        self._loader.veri_hazir.connect(self._on_id_hazir)
        self._loader.start()

    def _on_id_hazir(self, yeni_id: str):
        self.inputs["Arizaid"].setText(yeni_id)
        self.progress.setRange(0, 100)
        self.progress.setValue(0)

    def _kaydet_baslat(self):
        if not self.inputs["Baslik"].text().strip():
            QMessageBox.warning(self, "Eksik Alan", "Konu giriniz.")
            return

        self.btn_kaydet.setEnabled(False)
        self.btn_kaydet.setText("Kaydediliyor...")
        self.progress.setRange(0, 0)

        veri = {
            "Arizaid":         self.inputs["Arizaid"].text(),
            "Cihazid":         self.inputs["Cihazid"].text().split("|")[0].strip(),
            "BaslangicTarihi": self.inputs["BaslangicTarihi"].date().toString("yyyy-MM-dd"),
            "Saat":            datetime.now().strftime("%H:%M"),
            "Bildiren":        self.inputs["Bildiren"].text().strip(),
            "ArizaTipi":       self.inputs["ArizaTipi"].currentText(),
            "Oncelik":         self.inputs["Oncelik"].currentText(),
            "Baslik":          self.inputs["Baslik"].text().strip(),
            "ArizaAcikla":     self.inputs["ArizaAcikla"].toPlainText(),
            "Durum":           "Açık",
            "Rapor":           "",
        }

        self._saver = KayitIslemi(veri, self)
        self._saver.islem_tamam.connect(self._on_basarili)
        self._saver.hata_olustu.connect(self._on_hatali)
        self._saver.start()

    def _on_basarili(self):
        self.progress.setRange(0, 100)
        self.progress.setValue(100)
        logger.info(f"Arıza kaydedildi: {self.inputs['Arizaid'].text()}")
        QMessageBox.information(self, "Başarılı", "Kayıt eklendi.")
        self.kayit_basarili_sinyali.emit()
        self.kapanma_istegi.emit()

    def _on_hatali(self, mesaj: str):
        self.progress.setRange(0, 100)
        self.btn_kaydet.setEnabled(True)
        self.btn_kaydet.setText("Kaydet")
        QMessageBox.critical(self, "Hata", mesaj)
