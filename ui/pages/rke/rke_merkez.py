# -*- coding: utf-8 -*-
"""
rke_merkez.py — Merkezi RKE Yönetim Sayfası

Envanter, Muayene ve Rapor sekmelerini tek pencerede birleştirir.
Cihaz modülündeki cihaz_merkez.py tasarım prensibini takip eder:
  - Lazy-loaded sekmeler (ilk açılışta oluşturulur)
  - QStackedWidget tabanlı sekme geçişi
  - Sekmeler arası veri aktarımı (Envanter → Muayene seçimi)
"""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QStackedWidget,
)
from PySide6.QtGui import QCursor

from core.di import get_rke_service
from core.logger import logger
from core.hata_yonetici import hata_goster
from ui.styles.colors import DarkTheme as C
from ui.styles.icons import IconRenderer, IconColors

# ── Sekme tanımları ─────────────────────────────────────────────
_TABS = [
    ("ENVANTER",  "box",         "Envanter"),
    ("MUAYENE",   "clipboard",   "Muayene"),
    ("RAPOR",     "bar_chart",   "Rapor"),
]


class RKEMerkezPage(QWidget):
    """
    RKE modülü merkezi sayfası.

    Kullanım (main_window.py veya ayarlar.json menü bağlantısı):
        page = RKEMerkezPage(db=self._db, action_guard=self._action_guard)
    """

    def __init__(self, db=None, action_guard=None, parent=None):
        super().__init__(parent)
        self._db           = db
        self._action_guard = action_guard
        self._modules: dict[str, QWidget] = {}   # code → widget (lazy)
        self._nav_btns: dict[str, QPushButton] = {}
        self._active_tab   = ""

        self._setup_ui()
        # İlk sekmeyi göster
        self._switch_tab("ENVANTER")

    # ═══════════════════════════════════════════════════════════
    #  UI KURULUM
    # ═══════════════════════════════════════════════════════════

    def _setup_ui(self):
        self.setProperty("bg-role", "page")
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._build_header())

        self._stack = QStackedWidget()
        root.addWidget(self._stack, 1)

    def _build_header(self) -> QFrame:
        outer = QFrame()
        outer.setStyleSheet(
            f"QFrame{{background:{C.BG_SECONDARY};"
            f"border-bottom:1px solid {C.BORDER_PRIMARY};}}"
        )
        outer.setFixedHeight(44)
        lay = QHBoxLayout(outer)
        lay.setContentsMargins(16, 0, 16, 0)
        lay.setSpacing(0)

        # Başlık ikonu + yazı
        ico = QLabel()
        IconRenderer.set_label_icon(ico, "shield", color=C.ACCENT, size=18)
        lay.addWidget(ico)

        lbl = QLabel("  RKE Yönetimi")
        lbl.setStyleSheet(
            f"font-size:14px; font-weight:700; color:{C.TEXT_PRIMARY};"
            f"background:transparent;"
        )
        lay.addWidget(lbl)

        # Ayırıcı
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setProperty("color-role", "primary")
        sep.setFixedHeight(22)
        lay.addSpacing(16)
        lay.addWidget(sep)
        lay.addSpacing(4)

        # Sekme butonları
        for code, icon_key, label in _TABS:
            btn = QPushButton(f"  {label}")
            btn.setFixedHeight(44)
            btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            btn.setFlat(True)
            IconRenderer.set_button_icon(
                btn, icon_key,
                color=C.TEXT_SECONDARY, size=14,
            )
            btn.setStyleSheet(self._tab_qss(active=False))
            btn.clicked.connect(lambda _, c=code: self._switch_tab(c))
            self._nav_btns[code] = btn
            lay.addWidget(btn)

        lay.addStretch()

        # Yenile butonu
        btn_yenile = QPushButton()
        btn_yenile.setFixedSize(32, 32)
        btn_yenile.setToolTip("Sayfayı Yenile")
        btn_yenile.setProperty("style-role", "secondary")
        btn_yenile.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        IconRenderer.set_button_icon(btn_yenile, "refresh", color=C.TEXT_SECONDARY, size=15)
        btn_yenile.clicked.connect(self._yenile)
        lay.addWidget(btn_yenile)

        return outer

    # ═══════════════════════════════════════════════════════════
    #  SEKME YÖNETİMİ
    # ═══════════════════════════════════════════════════════════

    def _switch_tab(self, code: str):
        if code == self._active_tab:
            return
        self._active_tab = code

        # Buton stillerini güncelle
        for c, btn in self._nav_btns.items():
            btn.setStyleSheet(self._tab_qss(active=(c == code)))
            IconRenderer.set_button_icon(
                btn,
                next(icon for cd, icon, _ in _TABS if cd == c),
                color=C.ACCENT if c == code else C.TEXT_SECONDARY,
                size=14,
            )

        # Lazy-load: ilk geçişte modülü oluştur
        if code not in self._modules:
            widget = self._create_module(code)
            self._modules[code] = widget
            self._stack.addWidget(widget)

        self._stack.setCurrentWidget(self._modules[code])

    def _create_module(self, code: str) -> QWidget:
        try:
            if code == "ENVANTER":
                from ui.pages.rke.rke_yonetim import RKEYonetimPenceresi
                w = RKEYonetimPenceresi(
                    db=self._db,
                    action_guard=self._action_guard,
                )
                # Çift tıklama → Muayene sekmesine ekipmanla geç
                if hasattr(w, "ekipman_secildi_signal"):
                    w.ekipman_secildi_signal.connect(self._muayeneye_gec)
                return w

            elif code == "MUAYENE":
                from ui.pages.rke.rke_muayene import RKEMuayenePage
                from core.auth.session_context import SessionContext
                try:
                    session = SessionContext()
                    kullanici = session.get_user()
                    kullanici_adi = kullanici.username if kullanici else None
                except Exception:
                    kullanici_adi = None
                w = RKEMuayenePage(
                    db=self._db,
                    action_guard=self._action_guard,
                    kullanici_adi=kullanici_adi,
                )
                return w

            elif code == "RAPOR":
                from ui.pages.rke.rke_rapor import RKERaporPenceresi
                w = RKERaporPenceresi(
                    db=self._db,
                    action_guard=self._action_guard,
                )
                return w

            else:
                raise ValueError(f"Bilinmeyen sekme: {code}")

        except Exception as e:
            logger.error(f"RKE modül yükleme hatası ({code}): {e}")
            err = QLabel(f"Modül yüklenemedi: {code}\n{e}")
            err.setAlignment(Qt.AlignmentFlag.AlignCenter)
            err.setProperty("color-role", "primary")
            return err

    def _muayeneye_gec(self, ekipman_no: str = ""):
        """
        Envanter sekmesinden çift tıklandığında muayene sekmesine geç
        ve ekipmanı otomatik seç.
        """
        self._switch_tab("MUAYENE")
        if ekipman_no:
            w = self._modules.get("MUAYENE")
            if w and hasattr(w, "cmb_rke"):
                idx = w.cmb_rke.findText(ekipman_no, Qt.MatchFlag.MatchContains)
                if idx >= 0:
                    w.cmb_rke.setCurrentIndex(idx)

    def _yenile(self):
        """Aktif sekmeyi yenile."""
        w = self._modules.get(self._active_tab)
        if w and hasattr(w, "load_data"):
            w.load_data()
        elif w and hasattr(w, "verileri_yukle"):
            w.verileri_yukle()

    # ═══════════════════════════════════════════════════════════
    #  main_window.py arayüzü
    # ═══════════════════════════════════════════════════════════

    def load_data(self):
        """main_window.py'den çağrılan standart arayüz."""
        self._yenile()

    # ═══════════════════════════════════════════════════════════
    #  STİL
    # ═══════════════════════════════════════════════════════════

    @staticmethod
    def _tab_qss(active: bool) -> str:
        if active:
            return (
                f"QPushButton{{"
                f"background:transparent; border:none;"
                f"border-bottom:2px solid {C.ACCENT};"
                f"color:{C.TEXT_PRIMARY};"
                f"font-size:13px; font-weight:700; padding:0 14px;"
                f"}}"
            )
        return (
            f"QPushButton{{"
            f"background:transparent; border:none;"
            f"border-bottom:2px solid transparent;"
            f"color:{C.TEXT_SECONDARY};"
            f"font-size:13px; font-weight:600; padding:0 14px;"
            f"}}"
            f"QPushButton:hover{{color:{C.TEXT_PRIMARY};}}"
        )
