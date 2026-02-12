# -*- coding: utf-8 -*-
"""
Arıza Kayıt Sayfası  (Tam Form — Bağımsız Sayfa)
──────────────────────────────────────────────────
• 2 kolonlu yerleşim: Sol = bildiren bilgileri + dosya eki, Sağ = arıza detayları
• Cihaz seçiminde QCompleter ile "içinde geçen" (MatchContains) arama
• DB tablosu: Cihaz_Ariza
• kayit_tamamlandi sinyali → üst katmanda listeyi yenilemek için kullanılır
"""
import os
from datetime import datetime

from PySide6.QtCore import Qt, QDate, QThread, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QComboBox, QLineEdit, QDateEdit,
    QGroupBox, QMessageBox, QFileDialog, QTextEdit, QCompleter,
    QProgressBar
)
from PySide6.QtGui import QCursor, QFont

from core.logger import logger
from ui.theme_manager import ThemeManager


S = ThemeManager.get_all_component_styles()

ARIZA_TIPLERI     = [
    "Donanımsal Arıza", "Yazılımsal Arıza", "Kullanıcı Hatası",
    "Ağ / Bağlantı Sorunu", "Parça Değişimi",
    "Periyodik Bakım Talebi", "Diğer"
]
ONCELIK_DURUMLARI = ["Düşük", "Normal", "Yüksek", "Acil (Kritik)"]


# ─── Thread: ID üret + cihaz listesini yükle ──────────────────

class BaslangicYukleyici(QThread):
    veri_hazir = Signal(str, list)

    def __init__(self, parent=None):
        super().__init__(parent)

    def run(self):
        yeni_id       = f"ARZ-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        cihaz_listesi = []
        from database.sqlite_manager import SQLiteManager
        db = None
        try:
            db = SQLiteManager()
            from database.repository_registry import RepositoryRegistry
            registry = RepositoryRegistry(db)
            repo     = registry.get("Cihazlar")
            for c in repo.get_all():
                cihaz_listesi.append(
                    f"{c.get('Cihazid','')} | {c.get('Marka','')} {c.get('Model','')}".strip()
                )
        except Exception as e:
            logger.warning(f"Cihaz listesi yüklenemedi: {e}")
        finally:
            if db:
                db.close()
        self.veri_hazir.emit(yeni_id, cihaz_listesi)


# ─── Thread: Cihaz_Ariza tablosuna yaz ────────────────────────

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
#  ANA SAYFA
# ═══════════════════════════════════════════════

class ArizaKayitPage(QWidget):
    """Yeni arıza kaydı oluşturma sayfası."""
    kayit_tamamlandi = Signal()

    def __init__(self, db=None, yetki="viewer", kullanici_adi=None, parent=None):
        super().__init__(parent)
        self.setStyleSheet(S["page"])
        self._db           = db
        self.yetki         = yetki
        self.kullanici_adi = kullanici_adi

        self.inputs       = {}
        self._rapor_dosya = ""

        self._setup_ui()
        self._baslangic_yukle()

    # ─── UI ───────────────────────────────────────────────────

    def _setup_ui(self):
        main = QVBoxLayout(self)
        main.setContentsMargins(20, 16, 20, 16)
        main.setSpacing(14)

        # ── Header ──
        hdr = QHBoxLayout()
        lbl_baslik = QLabel("Arıza Bildirim Formu")
        lbl_baslik.setFont(QFont("Segoe UI", 15, QFont.Bold))
        lbl_baslik.setStyleSheet(S["header_name"])

        self.progress = QProgressBar()
        self.progress.setFixedSize(150, 6)
        self.progress.setTextVisible(False)
        self.progress.setStyleSheet(S.get("progress", ""))

        hdr.addWidget(lbl_baslik)
        hdr.addStretch()
        hdr.addWidget(self.progress)
        main.addLayout(hdr)

        # ── İçerik: Sol + Sağ kolon ──
        content = QHBoxLayout()
        content.setSpacing(20)

        # ─── Sol Kolon ─────────────────────────────────────────
        sol = QVBoxLayout()
        sol.setAlignment(Qt.AlignTop)

        grp_bildirim = QGroupBox("Bildiren Bilgileri")
        grp_bildirim.setStyleSheet(S["group"])
        v_bil = QVBoxLayout(grp_bildirim)
        v_bil.setSpacing(12)

        # Arıza ID (otomatik, sadece görüntüleme)
        self.inputs["Arizaid"] = QLineEdit()
        self.inputs["Arizaid"].setReadOnly(True)
        self.inputs["Arizaid"].setStyleSheet(
            "font-weight:bold; color:#e57373; background:#2b2b2b; border:1px solid #444;"
        )
        self.inputs["Arizaid"].setMinimumHeight(35)
        self._add_labeled(v_bil, "Arıza ID (Otomatik):", self.inputs["Arizaid"])

        # İlgili Cihaz – düzenlenebilir ComboBox + MatchContains arama
        self.inputs["Cihazid"] = QComboBox()
        self.inputs["Cihazid"].setEditable(True)
        self.inputs["Cihazid"].setInsertPolicy(QComboBox.NoInsert)
        self.inputs["Cihazid"].setStyleSheet(S["combo"])
        self.inputs["Cihazid"].setMinimumHeight(35)
        comp = self.inputs["Cihazid"].completer()
        comp.setCompletionMode(QCompleter.PopupCompletion)
        comp.setFilterMode(Qt.MatchContains)   # "Samsung" yazınca içinde geçenleri bulur
        self._add_labeled(v_bil, "İlgili Cihaz (ID veya Marka Ara):", self.inputs["Cihazid"])

        # Tarih
        self.inputs["BaslangicTarihi"] = QDateEdit(QDate.currentDate())
        self.inputs["BaslangicTarihi"].setCalendarPopup(True)
        self.inputs["BaslangicTarihi"].setDisplayFormat("dd.MM.yyyy")
        self.inputs["BaslangicTarihi"].setStyleSheet(S["date"])
        self.inputs["BaslangicTarihi"].setMinimumHeight(35)
        self._add_labeled(v_bil, "Tarih:", self.inputs["BaslangicTarihi"])

        # Bildiren
        self.inputs["Bildiren"] = QLineEdit()
        self.inputs["Bildiren"].setStyleSheet(S["input"])
        self.inputs["Bildiren"].setMinimumHeight(35)
        if self.kullanici_adi:
            self.inputs["Bildiren"].setText(str(self.kullanici_adi))
            self.inputs["Bildiren"].setReadOnly(True)
            self.inputs["Bildiren"].setStyleSheet(
                "background:#2b2b2b; color:#888; border:1px solid #444;"
            )
        self._add_labeled(v_bil, "Bildiren Personel:", self.inputs["Bildiren"])

        sol.addWidget(grp_bildirim)

        # Grup: Dosya Eki
        grp_dosya = QGroupBox("Dosya Ekleri")
        grp_dosya.setStyleSheet(S["group"])
        v_dos = QVBoxLayout(grp_dosya)
        v_dos.setSpacing(10)

        self.lbl_dosya_durum = QLabel("Dosya seçilmedi")
        self.lbl_dosya_durum.setAlignment(Qt.AlignCenter)
        self.lbl_dosya_durum.setStyleSheet("color:#888; font-style:italic;")

        self.btn_dosya = QPushButton("📎  Görsel / Tutanak Ekle")
        self.btn_dosya.setStyleSheet(S["file_btn"])
        self.btn_dosya.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_dosya.clicked.connect(self._dosya_sec)

        v_dos.addWidget(self.lbl_dosya_durum)
        v_dos.addWidget(self.btn_dosya)
        sol.addWidget(grp_dosya)
        sol.addStretch()

        content.addLayout(sol, 1)   # %33 genişlik

        # ─── Sağ Kolon ─────────────────────────────────────────
        sag = QVBoxLayout()
        sag.setAlignment(Qt.AlignTop)

        grp_detay = QGroupBox("Arıza Detayları")
        grp_detay.setStyleSheet(S["group"])
        v_det = QVBoxLayout(grp_detay)
        v_det.setSpacing(12)

        # Başlık (konu)
        self.inputs["Baslik"] = QLineEdit()
        self.inputs["Baslik"].setPlaceholderText("Arızanın kısa başlığı")
        self.inputs["Baslik"].setStyleSheet(S["input"])
        self.inputs["Baslik"].setMinimumHeight(35)
        self._add_labeled(v_det, "Konu / Başlık:", self.inputs["Baslik"])

        # Arıza Tipi + Öncelik (yan yana)
        h_tip = QHBoxLayout()
        h_tip.setSpacing(12)
        self.inputs["ArizaTipi"] = QComboBox()
        self.inputs["ArizaTipi"].addItems(ARIZA_TIPLERI)
        self.inputs["ArizaTipi"].setStyleSheet(S["combo"])
        self.inputs["ArizaTipi"].setMinimumHeight(35)

        self.inputs["Oncelik"] = QComboBox()
        self.inputs["Oncelik"].addItems(ONCELIK_DURUMLARI)
        self.inputs["Oncelik"].setStyleSheet(S["combo"])
        self.inputs["Oncelik"].setMinimumHeight(35)

        col_tip = QVBoxLayout()
        col_tip.setSpacing(4)
        col_tip.addWidget(self._lbl("Arıza Tipi:"))
        col_tip.addWidget(self.inputs["ArizaTipi"])

        col_onc = QVBoxLayout()
        col_onc.setSpacing(4)
        col_onc.addWidget(self._lbl("Öncelik Durumu:"))
        col_onc.addWidget(self.inputs["Oncelik"])

        h_tip.addLayout(col_tip)
        h_tip.addLayout(col_onc)
        v_det.addLayout(h_tip)

        # Detaylı Açıklama
        lbl_acik = QLabel("Detaylı Açıklama:")
        lbl_acik.setStyleSheet(S["label"])
        self.inputs["ArizaAcikla"] = QTextEdit()
        self.inputs["ArizaAcikla"].setPlaceholderText(
            "Arızanın oluş şekli, belirtileri, ne zaman başladığı..."
        )
        self.inputs["ArizaAcikla"].setStyleSheet(S["input"])
        self.inputs["ArizaAcikla"].setMinimumHeight(120)
        v_det.addWidget(lbl_acik)
        v_det.addWidget(self.inputs["ArizaAcikla"])
        v_det.addStretch()

        sag.addWidget(grp_detay)
        content.addLayout(sag, 2)   # %66 genişlik

        main.addLayout(content, 1)

        # ── Ayraç + Footer ──
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("background:#333; max-height:1px;")
        main.addWidget(sep)

        footer = QHBoxLayout()
        self.btn_iptal = QPushButton("İptal")
        self.btn_iptal.setFixedSize(120, 42)
        self.btn_iptal.setStyleSheet(S["cancel_btn"])
        self.btn_iptal.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_iptal.clicked.connect(self._temizle)

        self.btn_kaydet = QPushButton("⚠️  Kaydı Oluştur")
        self.btn_kaydet.setFixedSize(200, 42)
        self.btn_kaydet.setStyleSheet(S["save_btn"])
        self.btn_kaydet.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_kaydet.clicked.connect(self._kaydet_baslat)

        footer.addWidget(self.btn_iptal)
        footer.addStretch()
        footer.addWidget(self.btn_kaydet)
        main.addLayout(footer)

    # ─── Yardımcılar ──────────────────────────────────────────

    def _lbl(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet(S["label"])
        return lbl

    def _add_labeled(self, layout, text: str, widget):
        layout.addWidget(self._lbl(text))
        layout.addWidget(widget)

    # ─── Mantık ───────────────────────────────────────────────

    def _baslangic_yukle(self):
        self.progress.setRange(0, 0)
        self._loader = BaslangicYukleyici(self)
        self._loader.veri_hazir.connect(self._on_yukle_tamam)
        self._loader.start()

    def _on_yukle_tamam(self, yeni_id: str, cihaz_listesi: list):
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.inputs["Arizaid"].setText(yeni_id)
        self.inputs["Cihazid"].clear()
        self.inputs["Cihazid"].addItem("")
        self.inputs["Cihazid"].addItems(cihaz_listesi)

    def _dosya_sec(self):
        yol, _ = QFileDialog.getOpenFileName(
            self, "Dosya Seç", "",
            "Resim / PDF (*.jpg *.jpeg *.png *.pdf)"
        )
        if not yol:
            return
        self._rapor_dosya = yol
        self.lbl_dosya_durum.setText(f"✅  {os.path.basename(yol)}")
        self.lbl_dosya_durum.setStyleSheet("color:#4caf50; font-weight:bold;")

    def _kaydet_baslat(self):
        cihaz_secim = self.inputs["Cihazid"].currentText().strip()
        cihaz_id    = cihaz_secim.split("|")[0].strip() if "|" in cihaz_secim else cihaz_secim
        baslik      = self.inputs["Baslik"].text().strip()

        if not cihaz_id:
            QMessageBox.warning(self, "Eksik Alan", "Lütfen ilgili cihazı seçiniz.")
            return
        if not baslik:
            QMessageBox.warning(self, "Eksik Alan", "Konu / Başlık alanı boş bırakılamaz.")
            return

        self.btn_kaydet.setEnabled(False)
        self.btn_kaydet.setText("Kaydediliyor...")
        self.progress.setRange(0, 0)

        veri = {
            "Arizaid":         self.inputs["Arizaid"].text(),
            "Cihazid":         cihaz_id,
            "BaslangicTarihi": self.inputs["BaslangicTarihi"].date().toString("yyyy-MM-dd"),
            "Saat":            datetime.now().strftime("%H:%M"),
            "Bildiren":        self.inputs["Bildiren"].text().strip(),
            "ArizaTipi":       self.inputs["ArizaTipi"].currentText(),
            "Oncelik":         self.inputs["Oncelik"].currentText(),
            "Baslik":          baslik,
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
        QMessageBox.information(self, "Başarılı", "Arıza kaydı oluşturuldu.")
        self.kayit_tamamlandi.emit()
        self._temizle()

    def _on_hatali(self, mesaj: str):
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.btn_kaydet.setEnabled(True)
        self.btn_kaydet.setText("⚠️  Kaydı Oluştur")
        QMessageBox.critical(self, "Hata", f"Kayıt başarısız:\n{mesaj}")

    def _temizle(self):
        self.inputs["Baslik"].clear()
        self.inputs["ArizaAcikla"].clear()
        self.inputs["Cihazid"].setCurrentIndex(0)
        self.inputs["ArizaTipi"].setCurrentIndex(0)
        self.inputs["Oncelik"].setCurrentIndex(0)
        self.inputs["BaslangicTarihi"].setDate(QDate.currentDate())
        self._rapor_dosya = ""
        self.lbl_dosya_durum.setText("Dosya seçilmedi")
        self.lbl_dosya_durum.setStyleSheet("color:#888; font-style:italic;")
        self.btn_kaydet.setEnabled(True)
        self.btn_kaydet.setText("⚠️  Kaydı Oluştur")
        self._baslangic_yukle()

    def closeEvent(self, event):
        for attr in ("_loader", "_saver"):
            w = getattr(self, attr, None)
            if w and w.isRunning():
                w.quit()
                w.wait(500)
        event.accept()
