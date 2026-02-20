# -*- coding: utf-8 -*-
"""
İzin Takip, FHSZ Yönetim, Puantaj Rapor — Birleştirilmiş Merkez
──────────────────────────────────────────────────────────────
Üç sayfayı tek pencerenin üç sekmesi olarak yönetir.
PersonelMerkez yapısı aynen kullanılır.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QStackedWidget
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QCursor

from ui.styles import DarkTheme
from ui.styles.components import ComponentStyles, STYLES
from ui.styles.icons import IconRenderer
from core.logger import logger

C = DarkTheme

# Sekme tanımları
TABS = [
    ("IZIN",    "İzin Takip"),
    ("FHSZ",    "FHSZ Yönetim"),
    ("PUANTAJ", "Puantaj Rapor"),
]


class IzinFHSZPuantajMerkezPage(QWidget):
    """İzin Takip, FHSZ Yönetim, Puantaj Rapor birleştirilmiş sayfası"""
    
    kapat_istegi = Signal()

    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db           = db
        self._modules     = {}       # code → widget (lazy cache)
        self._nav_btns    = {}       # code → QPushButton
        self._active_tab  = "IZIN"
        
        # main_window.py uyumluluğu için
        self.btn_kapat = None

        self._setup_ui()
        self._load_data()

    # ═══════════════════════════════════════════════════
    #  UI KURULUM
    # ═══════════════════════════════════════════════════

    def _setup_ui(self):
        self.setStyleSheet(STYLES["page"])
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._build_header())

        self.content_stack = QStackedWidget()
        root.addWidget(self.content_stack, 1)

    def _build_header(self) -> QFrame:
        """Header (52px) + sekme nav (36px)."""
        outer = QFrame()
        outer.setStyleSheet(f"""
            QFrame {{
                background-color: {C.BG_SECONDARY};
                border-bottom: 1px solid {C.BORDER_PRIMARY};
            }}
        """)
        lay = QVBoxLayout(outer)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # ── Üst şerit ──
        top = QWidget()
        top.setFixedHeight(52)
        top_lay = QHBoxLayout(top)
        top_lay.setContentsMargins(16, 0, 16, 0)
        top_lay.setSpacing(10)

        # Başlık
        lbl_title = QLabel("İzin & FHSZ & Puantaj")
        lbl_title.setStyleSheet(
            f"font-size:16px; font-weight:600; color:{C.TEXT_PRIMARY}; "
            "background:transparent;"
        )
        top_lay.addWidget(lbl_title)

        top_lay.addStretch()

        # Kapat
        btn_kapat = QPushButton("Kapat")
        btn_kapat.setCursor(QCursor(Qt.PointingHandCursor))
        btn_kapat.setToolTip("Kapat")
        btn_kapat.setStyleSheet(STYLES["close_btn"])
        btn_kapat.clicked.connect(self.kapat_istegi.emit)
        IconRenderer.set_button_icon(btn_kapat, "x", color=C.TEXT_PRIMARY, size=14)
        top_lay.addWidget(btn_kapat)

        lay.addWidget(top)

        # ── Sekme nav ──
        nav = QWidget()
        nav.setFixedHeight(36)
        nav.setStyleSheet(f"background:transparent; border-top:1px solid {C.BORDER_SECONDARY};")
        nav_lay = QHBoxLayout(nav)
        nav_lay.setContentsMargins(16, 0, 16, 0)
        nav_lay.setSpacing(0)

        for code, label in TABS:
            btn = QPushButton(label)
            btn.setCursor(QCursor(Qt.PointingHandCursor))
            btn.setStyleSheet(self._tab_btn_qss(active=False))
            btn.clicked.connect(lambda _, c=code: self._switch_tab(c))
            nav_lay.addWidget(btn)
            self._nav_btns[code] = btn

        nav_lay.addStretch()
        lay.addWidget(nav)
        return outer

    def _sep(self) -> QFrame:
        """Dikey ayırıcı"""
        sep = QFrame()
        sep.setFrameShape(QFrame.VLine)
        sep.setLineWidth(1)
        sep.setStyleSheet(f"color:{C.BORDER_PRIMARY};")
        sep.setMaximumWidth(1)
        return sep

    def _tab_btn_qss(self, active=False) -> str:
        """Sekme butonu stili"""
        if active:
            return (
                f"QPushButton{{"
                f"background:transparent; border:none;"
                f"border-bottom:2px solid {C.INPUT_BORDER_FOCUS};"
                f"color:{C.BTN_PRIMARY_TEXT};"
                f"font-size:12px; font-weight:600; padding:0 14px;"
                f"}}"
            )
        return (
            f"QPushButton{{"
            f"background:transparent; border:none;"
            f"border-bottom:2px solid transparent;"
            f"color:{C.TEXT_MUTED};"
            f"font-size:12px; padding:0 14px;"
            f"}}"
            f"QPushButton:hover{{color:{C.TEXT_SECONDARY};}}"
        )

    # ═══════════════════════════════════════════════════
    #  VERİ YÜKLEME
    # ═══════════════════════════════════════════════════

    def _load_data(self):
        try:
            # Sekmeleri başlat
            self._switch_tab("IZIN")
        except Exception as e:
            logger.error(f"İzin/FHSZ/Puantaj merkez veri hatası: {e}")

    # ═══════════════════════════════════════════════════
    #  SEKME YÖNETİMİ
    # ═══════════════════════════════════════════════════

    def _switch_tab(self, code: str):
        """Sekmeyi değiştir"""
        if code not in [t[0] for t in TABS]:
            logger.warning(f"Bilinmeyen sekme: {code}")
            return

        # UI güncelle
        self._active_tab = code
        for c, btn in self._nav_btns.items():
            btn.setStyleSheet(self._tab_btn_qss(active=(c == code)))

        # Widget lazy-load
        if code not in self._modules:
            try:
                # İçeri al (lazy import)
                if code == "IZIN":
                    from ui.pages.personel.izin_takip import IzinTakipPage
                    widget = IzinTakipPage(db=self.db)
                elif code == "FHSZ":
                    from ui.pages.personel.fhsz_yonetim import FHSZYonetimPage
                    widget = FHSZYonetimPage(db=self.db)
                elif code == "PUANTAJ":
                    from ui.pages.personel.puantaj_rapor import PuantajRaporPage
                    widget = PuantajRaporPage(db=self.db)
                else:
                    widget = QWidget()

                self._modules[code] = widget
                self.content_stack.addWidget(widget)
            except Exception as e:
                import traceback
                logger.error(f"Sekme {code} yüklemesi başarısız: {e}\n{traceback.format_exc()}")
                widget = QWidget()
                self._modules[code] = widget
                self.content_stack.addWidget(widget)

        # Widget'i göster
        w = self._modules[code]
        self.content_stack.setCurrentWidget(w)

        # load_data() çağır (varsa)
        if hasattr(w, "load_data"):
            try:
                w.load_data()
            except Exception as e:
                import traceback
                logger.error(f"Sekme {code} load_data hatası: {e}\n{traceback.format_exc()}")

    def btn_kapat_clicked(self):
        """Uyum için (main_window.py geleneksel adlandırması)"""
        self.kapat_istegi.emit()
