# ui/pages/fhsz/dis_alan_merkez_page.py
# -*- coding: utf-8 -*-
"""
Dış Alan Radyasyon Yönetim Merkezi

Sekmeler:
  1. Excel Import          — Birimlerden gelen şablonları içe aktar
  2. Puantaj Raporu        — Kişi/birim bazlı dönem raporu
  3. Katsayı Protokolleri  — AnaBilimDali/Birim katsayı yönetimi
  4. Birim Kurulum         — Sihirbaz: operasyonel veri gir, sistem kurar
"""
from PySide6.QtWidgets import QWidget, QVBoxLayout, QTabWidget, QFrame, QHBoxLayout, QLabel, QPushButton
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

        # Üst başlık barı
        header = QFrame()
        header.setStyleSheet("background: transparent;")
        header_lay = QHBoxLayout(header)
        header_lay.setContentsMargins(16, 10, 16, 0)
        header_lay.setSpacing(0)

        lbl_title = QLabel("Radyoloji Birimi Dışı Radyasyon Görevlisi FHSZ Yönetim Merkezi")
        lbl_title.setStyleSheet("font-size:18px; font-weight:bold; color:#1D75FE;")
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        btn_close = QPushButton("✕")
        btn_close.setFixedSize(28, 28)
        btn_close.setStyleSheet("border:none; font-size:18px; color:#aaa; background:transparent;")
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.setToolTip("Kapat")
        btn_close.clicked.connect(self._on_close)

        header_lay.addStretch()
        header_lay.addWidget(lbl_title)
        header_lay.addStretch()
        header_lay.addWidget(btn_close)

        root.addWidget(header)

        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(S.get("tab_widget", ""))
        self.tabs.setDocumentMode(True)

        # ── Sekme 1: Excel Import ─────────────────────────────
        try:
            from ui.pages.fhsz.dis_alan_import_page import DisAlanImportPage
            self.tabs.addTab(DisAlanImportPage(db=self._db), "📥  Tutanak Yükleme")
        except Exception as e:
            logger.error(f"DisAlanImportPage yüklenemedi: {e}")
            self.tabs.addTab(_HataWidget(str(e)), "📥  Tutanak Yükleme")

        # ── Sekme 2: Puantaj Raporu ───────────────────────────
        try:
            from ui.pages.fhsz.puantaj_rapor_page import DisAlanPuantajRaporPage
            self.tabs.addTab(DisAlanPuantajRaporPage(db=self._db), "📊  Puantaj Raporu")
        except Exception as e:
            logger.error(f"DisAlanPuantajRaporPage yüklenemedi: {e}")
            self.tabs.addTab(_HataWidget(str(e)), "📊  Puantaj Raporu")

        # ── Sekme 3: Katsayı Protokolleri ────────────────────
        try:
            from ui.pages.fhsz.dis_alan_katsayi_page import DisAlanKatsayiPage
            self.tabs.addTab(DisAlanKatsayiPage(db=self._db), "⚙  Katsayı Protokolleri")
        except Exception as e:
            logger.error(f"DisAlanKatsayiPage yüklenemedi: {e}")
            self.tabs.addTab(_HataWidget(str(e)), "⚙  Katsayı Protokolleri")

        # ── Sekme 4: Birim Kurulum Sihirbazı ─────────────────
        try:
            from ui.pages.fhsz.dis_alan_kurulum_page import DisAlanKurulumPage
            self.tabs.addTab(DisAlanKurulumPage(db=self._db), "⚙  Birim Kurulum")
        except Exception as e:
            logger.error(f"DisAlanKurulumPage yüklenemedi: {e}")
            self.tabs.addTab(_HataWidget(str(e)), "⚙  Birim Kurulum")

        root.addWidget(self.tabs)
        self.setLayout(root)
    def _on_close(self):
        self.close()
    def showEvent(self, event):
        """Sayfa gösterildiğinde aktif sekmenin verilerini yenile."""
        super().showEvent(event)
        try:
            widget = self.tabs.currentWidget()
            if hasattr(widget, "_load_data"):
                widget._load_data()  # type: ignore[attr-defined]
            elif hasattr(widget, "load_data"):
                widget.load_data()  # type: ignore[attr-defined]
        except Exception as e:
            logger.warning(f"DisAlanMerkezPage.showEvent yenileme: {e}")


# ─────────────────────────────────────────────────────────────
#  Hata widget — sekme yüklenemediğinde gösterilir
# ─────────────────────────────────────────────────────────────

class _HataWidget(QWidget):
    def __init__(self, mesaj: str, parent=None):
        super().__init__(parent)
        from PySide6.QtWidgets import QLabel
        lay = QVBoxLayout(self)
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl = QLabel(f"⚠  Sayfa yüklenemedi:\n{mesaj}")
        lbl.setStyleSheet("color:#EF9A9A; font-size:12px; padding:20px;")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setWordWrap(True)
        lay.addWidget(lbl)
