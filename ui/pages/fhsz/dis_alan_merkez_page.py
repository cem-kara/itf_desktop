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
from PySide6.QtWidgets import QWidget, QVBoxLayout, QTabWidget, QLabel
from PySide6.QtCore import Qt

from ui.styles.components import STYLES as S
from core.logger import logger


class DisAlanMerkezPage(QWidget):
    def __init__(self, db=None, parent=None):
        super().__init__(parent)
        self.setStyleSheet(S["page"])
        self._db = db
        self._setup_ui()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(S.get("tab_widget", ""))
        self.tabs.setDocumentMode(True)

        # 1 — Excel Import (Import Karsilastirma alt sekme olarak icinde)
        try:
            from ui.pages.fhsz.dis_alan_import_page import DisAlanImportPage
            self.tabs.addTab(DisAlanImportPage(db=self._db), "📥  Excel Import")
        except Exception as e:
            logger.error(f"DisAlanImportPage yuklenemedi: {e}")
            self.tabs.addTab(_HataWidget(str(e)), "📥  Excel Import")

        # 2 — Puantaj & Onay
        try:
            from ui.pages.fhsz.dis_alan_puantaj_page import DisAlanPuantajPage
            self.tabs.addTab(DisAlanPuantajPage(db=self._db), "📊  Puantaj & Onay")
        except Exception as e:
            logger.error(f"DisAlanPuantajPage yuklenemedi: {e}")
            self.tabs.addTab(_HataWidget(str(e)), "📊  Puantaj & Onay")

        # 3 — Dönem Geçmişi
        try:
            from ui.pages.fhsz.dis_alan_donem_gecmisi_page import DisAlanDonemGecmisiPage
            self.tabs.addTab(DisAlanDonemGecmisiPage(db=self._db), "📅  Dönem Geçmişi")
        except Exception as e:
            logger.error(f"DisAlanDonemGecmisiPage yuklenemedi: {e}")
            self.tabs.addTab(_HataWidget(str(e)), "📅  Dönem Geçmişi")

        # 4 — Ayarlar (Katsayi + Kurulum)
        self.tabs.addTab(_AyarlarWidget(db=self._db), "⚙  Ayarlar")

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
            self.tabs.addTab(DisAlanKatsayiPage(db=self._db), "📋  Katsayı Protokolleri")
        except Exception as e:
            logger.error(f"DisAlanKatsayiPage yuklenemedi: {e}")
            self.tabs.addTab(_HataWidget(str(e)), "📋  Katsayı Protokolleri")

        try:
            from ui.pages.fhsz.dis_alan_kurulum_page import DisAlanKurulumPage
            self.tabs.addTab(DisAlanKurulumPage(db=self._db), "🔧  Birim Kurulum")
        except Exception as e:
            logger.error(f"DisAlanKurulumPage yuklenemedi: {e}")
            self.tabs.addTab(_HataWidget(str(e)), "🔧  Birim Kurulum")

        lay.addWidget(self.tabs)


class _HataWidget(QWidget):
    def __init__(self, mesaj: str, parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl = QLabel(f"⚠  Sayfa yuklenemedi:\n{mesaj}")
        lbl.setStyleSheet("color:#EF9A9A; font-size:12px; padding:20px;")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setWordWrap(True)
        lay.addWidget(lbl)
