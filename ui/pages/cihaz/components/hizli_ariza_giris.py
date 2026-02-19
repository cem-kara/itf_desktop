# -*- coding: utf-8 -*-
"""
HizliArizaGiris — Cihaz 360° Merkez için Hızlı Arıza Bildirimi Widget'ı
──────────────────────────────────────────────────────────────────────────
Personel modülündeki HizliIzinGirisDialog deseninde:
• cihaz_merkez.py'nin sağ paneline gömülü çalışır (popup yok)
• Minimal alanlar: Başlık, Bildiren, Tip, Öncelik, Açıklama
• Kayıt başarılı → ariza_kaydedildi sinyali, panel kapanır
• ArizaEklePanel'in thread mimarisini (DosyaYukleyici, KayitIslemi) yeniden kullanır
"""
from datetime import datetime

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QComboBox, QTextEdit, QPushButton,
    QProgressBar, QMessageBox, QFrame,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QCursor

from core.logger import logger
from ui.theme_manager import ThemeManager
from ui.styles import DarkTheme

C      = DarkTheme
STYLES = ThemeManager.get_all_component_styles()

ARIZA_TIPLERI = [
    "Donanımsal Arıza", "Yazılımsal Arıza", "Kullanıcı Hatası",
    "Ağ / Bağlantı Sorunu", "Parça Değişimi",
    "Periyodik Bakım Talebi", "Diğer",
]
ONCELIK_DURUMLARI = ["Düşük", "Normal", "Yüksek", "Acil (Kritik)"]


class HizliArizaGiris(QWidget):
    """
    Sağ panelde cihaz başına hızlı arıza bildirimi.
    """

    ariza_kaydedildi = Signal()   # başarılı kayıt
    iptal_edildi     = Signal()   # vazgeç

    def __init__(self, db, cihaz_id: str, parent=None):
        super().__init__(parent)
        self._db       = db
        self._cihaz_id = cihaz_id
        self._inputs   = {}
        self._setup_ui()

    # ─── UI ────────────────────────────────────────────────

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 8, 0, 8)
        root.setSpacing(8)

        # Başlık satırı
        hdr = QHBoxLayout()
        lbl = QLabel("ARIZA BİLDİRİMİ")
        lbl.setStyleSheet(STYLES["section_label"])
        hdr.addWidget(lbl)
        hdr.addStretch()
        root.addLayout(hdr)

        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background:{C.BORDER_PRIMARY};")
        root.addWidget(sep)

        form = QVBoxLayout()
        form.setSpacing(7)

        # Cihaz ID (read-only)
        self._add_field(form, "Cihaz ID", "Cihazid", read_only=True,
                        value=self._cihaz_id)

        # Gizli arıza ID
        self._inputs["Arizaid"] = QLineEdit(self._new_id())
        self._inputs["Arizaid"].setVisible(False)

        # Bildiren
        self._add_field(form, "Bildiren", "Bildiren")

        # Başlık
        self._add_field(form, "Konu / Başlık", "Baslik",
                        placeholder="Sorun kısaca nedir?")

        # Tip + Öncelik yan yana
        row = QHBoxLayout()
        row.setSpacing(8)
        self._add_combo_col(row, "Tip", "ArizaTipi", ARIZA_TIPLERI)
        self._add_combo_col(row, "Öncelik", "Oncelik", ONCELIK_DURUMLARI)
        form.addLayout(row)

        # Açıklama
        lbl_a = QLabel("Açıklama")
        lbl_a.setStyleSheet(STYLES["label"])
        form.addWidget(lbl_a)
        ta = QTextEdit()
        ta.setStyleSheet(STYLES["input"])
        ta.setFixedHeight(70)
        self._inputs["ArizaAcikla"] = ta
        form.addWidget(ta)

        root.addLayout(form)

        # Progress (gizli)
        self.progress = QProgressBar()
        self.progress.setFixedHeight(4)
        self.progress.setTextVisible(False)
        self.progress.setVisible(False)
        self.progress.setStyleSheet(STYLES.get("progress", ""))
        root.addWidget(self.progress)

        # Butonlar
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        btn_vazgec = QPushButton("Vazgeç")
        btn_vazgec.setStyleSheet(STYLES["cancel_btn"])
        btn_vazgec.setCursor(QCursor(Qt.PointingHandCursor))
        btn_vazgec.clicked.connect(self.iptal_edildi.emit)

        self.btn_kaydet = QPushButton("Kaydet")
        self.btn_kaydet.setStyleSheet(STYLES["save_btn"])
        self.btn_kaydet.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_kaydet.clicked.connect(self._kaydet)

        btn_row.addWidget(btn_vazgec)
        btn_row.addWidget(self.btn_kaydet)
        root.addLayout(btn_row)

    def _add_field(self, layout, label: str, key: str,
                   read_only=False, placeholder="", value=""):
        lbl = QLabel(label)
        lbl.setStyleSheet(STYLES["label"])
        inp = QLineEdit(value)
        inp.setStyleSheet(STYLES["input"])
        inp.setReadOnly(read_only)
        inp.setPlaceholderText(placeholder)
        self._inputs[key] = inp
        layout.addWidget(lbl)
        layout.addWidget(inp)

    def _add_combo_col(self, layout, label: str, key: str, items: list):
        col = QVBoxLayout()
        col.setSpacing(3)
        lbl = QLabel(label)
        lbl.setStyleSheet(STYLES["label"])
        cb = QComboBox()
        cb.addItems(items)
        cb.setStyleSheet(STYLES["combo"])
        self._inputs[key] = cb
        col.addWidget(lbl)
        col.addWidget(cb)
        layout.addLayout(col)

    # ─── İşlemler ──────────────────────────────────────────

    def yenile(self, cihaz_id: str):
        """Cihaz değişince formu sıfırla."""
        self._cihaz_id = cihaz_id
        self._inputs["Cihazid"].setText(cihaz_id)
        self._inputs["Arizaid"].setText(self._new_id())
        self._inputs["Bildiren"].clear()
        self._inputs["Baslik"].clear()
        self._inputs["ArizaAcikla"].clear()
        self._inputs["ArizaTipi"].setCurrentIndex(0)
        self._inputs["Oncelik"].setCurrentIndex(0)
        self.btn_kaydet.setEnabled(True)
        self.btn_kaydet.setText("Kaydet")
        self.progress.setVisible(False)

    def _kaydet(self):
        baslik = self._inputs["Baslik"].text().strip()
        if not baslik:
            QMessageBox.warning(self, "Eksik Alan", "'Konu / Başlık' alanı boş bırakılamaz.")
            return

        self.btn_kaydet.setEnabled(False)
        self.btn_kaydet.setText("Kaydediliyor…")
        self.progress.setVisible(True)
        self.progress.setRange(0, 0)

        veri = {
            "Arizaid":         self._inputs["Arizaid"].text(),
            "Cihazid":         self._cihaz_id,
            "BaslangicTarihi": datetime.now().strftime("%Y-%m-%d"),
            "Saat":            datetime.now().strftime("%H:%M"),
            "Bildiren":        self._inputs["Bildiren"].text().strip(),
            "ArizaTipi":       self._inputs["ArizaTipi"].currentText(),
            "Oncelik":         self._inputs["Oncelik"].currentText(),
            "Baslik":          baslik,
            "ArizaAcikla":     self._inputs["ArizaAcikla"].toPlainText(),
            "Durum":           "Açık",
            "Rapor":           "",
        }
        self._kayit_thread(veri)

    def _kayit_thread(self, veri: dict):
        from ui.pages.cihaz.ariza_ekle import KayitIslemi
        self._saver = KayitIslemi(veri, self)
        self._saver.islem_tamam.connect(self._on_basarili)
        self._saver.hata_olustu.connect(self._on_hatali)
        self._saver.start()

    def _on_basarili(self):
        self.progress.setRange(0, 100)
        self.progress.setValue(100)
        logger.info(f"Hızlı arıza kaydedildi: {self._inputs['Arizaid'].text()}")
        QMessageBox.information(self, "Başarılı", "Arıza bildirimi oluşturuldu.")
        self.ariza_kaydedildi.emit()

    def _on_hatali(self, mesaj: str):
        self.progress.setVisible(False)
        self.btn_kaydet.setEnabled(True)
        self.btn_kaydet.setText("Kaydet")
        QMessageBox.critical(self, "Hata", mesaj)

    @staticmethod
    def _new_id() -> str:
        return f"ARZ-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
