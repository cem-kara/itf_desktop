# ui/pages/fhsz/dis_alan_merkez_page.py
# -*- coding: utf-8 -*-
"""
Dış Alan Radyasyon Yönetim Merkezi

4 sekme:
  1. Excel Import     — Dosya yükle, oku, kaydet.
                        Alt sekme: Import Karşılaştırma
  2. Puantaj ve Onay  — Kişi bazlı özet, RKS onay, PDF çıktısı
  3. Dönem Geçmişi    — Açık / kapalı dönem takibi
  4. Ayarlar          — Katsayı Protokolleri + Birim Kurulum Sihirbazı
"""
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QLabel, QFrame, QPushButton
from PySide6.QtCore import Qt

from ui.styles.components import STYLES as S
from core.logger import logger



from PySide6.QtCore import Signal
from PySide6.QtGui import QCursor
from ui.styles import DarkTheme
from ui.styles.icons import IconRenderer

class DisAlanMerkezPage(QWidget):
    kapat_istegi = Signal()

    def __init__(self, db=None, parent=None):
        super().__init__(parent)
        self.setProperty("bg-role", "page")
        self._db = db
        self.btn_kapat = None
        self._setup_ui()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        # Modern başlık alanı (izin_fhsz_puantaj_merkez.py tarzı)
        header = QFrame()
        header.setProperty("bg-role", "panel")
        header.setFixedHeight(52)
        header_lay = QHBoxLayout(header)
        header_lay.setContentsMargins(16, 0, 16, 0)
        header_lay.setSpacing(10)
        lbl_title = QLabel("Radyoloji Harici Personel Fiili Hizmet Yönetimi")
        lbl_title.setProperty("style-role", "section-title")
        lbl_title.setProperty("color-role", "primary")
        header_lay.addWidget(lbl_title)
        header_lay.addStretch()
        # Kapat butonu
        btn_kapat = QPushButton("Kapat")
        btn_kapat.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_kapat.setToolTip("Kapat")
        btn_kapat.setProperty("style-role", "danger")
        btn_kapat.style().unpolish(btn_kapat)
        btn_kapat.style().polish(btn_kapat)
        btn_kapat.clicked.connect(self.kapat_istegi.emit)
        IconRenderer.set_button_icon(btn_kapat, "x", color="primary", size=14)
        self.btn_kapat = btn_kapat
        header_lay.addWidget(btn_kapat)
        root.addWidget(header)

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)

        # 1 — Excel Import (Import Karsilastirma alt sekme olarak icinde)
        try:
            from ui.pages.fhsz.dis_alan_import_page import DisAlanImportPage
            self.tabs.addTab(DisAlanImportPage(db=self._db), "Excel Import")
        except Exception as e:
            logger.error(f"DisAlanImportPage yuklenemedi: {e}")
            self.tabs.addTab(_HataWidget(str(e)), "Excel Import")

        # 2 — Puantaj & Onay
        try:
            from ui.pages.fhsz.dis_alan_puantaj_page import DisAlanPuantajPage
            self.tabs.addTab(DisAlanPuantajPage(db=self._db), "Puantaj & Onay")
        except Exception as e:
            logger.error(f"DisAlanPuantajPage yuklenemedi: {e}")
            self.tabs.addTab(_HataWidget(str(e)), "Puantaj & Onay")

        # 3 — Dönem Geçmişi
        try:
            from ui.pages.fhsz.dis_alan_donem_gecmisi_page import DisAlanDonemGecmisiPage
            self.tabs.addTab(DisAlanDonemGecmisiPage(db=self._db), "Dönem Geçmişi")
        except Exception as e:
            logger.error(f"DisAlanDonemGecmisiPage yuklenemedi: {e}")
            self.tabs.addTab(_HataWidget(str(e)), "Dönem Geçmişi")

        # 4 — Ayarlar (Katsayi + Kurulum)
        self.tabs.addTab(_AyarlarWidget(db=self._db), "Ayarlar")

        root.addWidget(self.tabs)
        self.setLayout(root)
        self.tabs.currentChanged.connect(self._sekme_yenile)

    def showEvent(self, event):
        super().showEvent(event)
        self._sekme_yenile(self.tabs.currentIndex())

    def _sekme_yenile(self, idx: int):
        widget = self.tabs.widget(idx)
        if not widget:
            return
        for metod in ("_load_data", "_yukle", "load_data"):
            if hasattr(widget, metod):
                try:
                    getattr(widget, metod)()
                except Exception as e:
                    logger.warning(f"Sekme yenileme ({metod}): {e}")
                return
        # Alt sekme iceriyorsa (hem 'tabs' hem de '_tabs' kontrolü)
        inner_tabs = getattr(widget, "tabs", None) or getattr(widget, "_tabs", None)
        if inner_tabs:
            inner = inner_tabs.currentWidget()
            if inner:
                for metod in ("_load_data", "_yukle", "load_data"):
                    if hasattr(inner, metod):
                        try:
                            getattr(inner, metod)()
                        except Exception as e:
                            logger.warning(f"İç sekme yenileme ({metod}): {e}")
                        return


class _AyarlarWidget(QWidget):
    def __init__(self, db=None, parent=None):
        super().__init__(parent)
        self._db = db
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)

        try:
            from ui.pages.fhsz.dis_alan_katsayi_page import DisAlanKatsayiPage
            self.tabs.addTab(DisAlanKatsayiPage(db=self._db), "Katsayı Protokolleri")
        except Exception as e:
            logger.error(f"DisAlanKatsayiPage yuklenemedi: {e}")
            self.tabs.addTab(_HataWidget(str(e)), "Katsayı Protokolleri")

        try:
            from ui.pages.fhsz.dis_alan_kurulum_page import DisAlanKurulumPage
            self.tabs.addTab(DisAlanKurulumPage(db=self._db), "Birim Kurulum")
        except Exception as e:
            logger.error(f"DisAlanKurulumPage yuklenemedi: {e}")
            self.tabs.addTab(_HataWidget(str(e)), "Birim Kurulum")

        lay.addWidget(self.tabs)


class _HataWidget(QWidget):
    def __init__(self, mesaj: str, parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl = QLabel(f"Sayfa yüklenemedi:\n{mesaj}")
        lbl.setProperty("color-role", "err")
        lbl.setProperty("style-role", "info")
        lbl.setProperty("bg-role", "panel")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setWordWrap(True)
        lay.addWidget(lbl)
