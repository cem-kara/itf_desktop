# -*- coding: utf-8 -*-
"""
Bildirim Paneli
main_window içinde page_title ile stack arasına yerleşir.
Uygulama açılışında ve her sync sonrasında BildirimWorker tetiklenir.
Oturum boyunca kapatılabilir (dismiss), bir sonraki sync'te yeniden açılır.
"""
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton,
    QFrame, QSizePolicy
)
from PySide6.QtCore import Qt, Signal, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QCursor

from core.logger import logger


# ── Renk sabitleri ───────────────────────────────────────────────────────────
_KRITIK_BG     = "rgba(248, 81, 73, 0.10)"
_KRITIK_BORDER = "#f85149"
_KRITIK_TEXT   = "#ff7b72"
_KRITIK_CHIP   = "rgba(248, 81, 73, 0.18)"
_KRITIK_CHIP_H = "rgba(248, 81, 73, 0.32)"

_UYARI_BG     = "rgba(210, 153, 34, 0.10)"
_UYARI_BORDER = "#d29922"
_UYARI_TEXT   = "#e3b341"
_UYARI_CHIP   = "rgba(210, 153, 34, 0.18)"
_UYARI_CHIP_H = "rgba(210, 153, 34, 0.32)"

_PANEL_BG = "#0d1117"


class _BildirimChip(QPushButton):
    """Tek bir bildirimi temsil eden tıklanabilir etiket."""

    def __init__(self, bildirim: dict, mod: str, parent=None):
        """
        bildirim: {"kategori": str, "mesaj": str, "grup": str, "sayfa": str, "sayi": int}
        mod: "kritik" | "uyari"
        """
        super().__init__(parent)
        self._bildirim = bildirim
        sayi     = bildirim["sayi"]
        kategori = bildirim["kategori"]

        chip_bg, chip_h, text_c = (
            (_KRITIK_CHIP, _KRITIK_CHIP_H, _KRITIK_TEXT)
            if mod == "kritik"
            else (_UYARI_CHIP, _UYARI_CHIP_H, _UYARI_TEXT)
        )

        self.setText(f"  {kategori}  {sayi}  ")
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setToolTip(bildirim["mesaj"])
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {chip_bg};
                color: {text_c};
                border: 1px solid {text_c};
                border-radius: 10px;
                font-size: 12px;
                font-weight: 600;
                padding: 3px 10px;
            }}
            QPushButton:hover {{
                background-color: {chip_h};
            }}
        """)


class BildirimPaneli(QWidget):
    """
    Collapsible bildirim şeridi.

    Sinyaller:
        sayfa_ac(grup: str, sayfa: str) — chip tıklandığında ilgili sayfayı açar
    """
    sayfa_ac = Signal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._dismissed = False   # oturum boyunca kapatıldı mı
        self._son_veri  = None    # son gelen bildirim verisi
        self._setup_ui()
        self.hide()

    # ── UI kurulum ───────────────────────────────────────────────────────────

    def _setup_ui(self):
        self.setObjectName("bildirimPaneli")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setMaximumHeight(0)  # başlangıçta gizli (animasyon için)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(12, 6, 12, 6)
        outer.setSpacing(4)

        # Kritik satırı
        self._kritik_frame = self._satir_olustur("kritik")
        outer.addWidget(self._kritik_frame)

        # Uyarı satırı
        self._uyari_frame = self._satir_olustur("uyari")
        outer.addWidget(self._uyari_frame)

        self.setStyleSheet(f"""
            QWidget#bildirimPaneli {{
                background-color: {_PANEL_BG};
                border-bottom: 1px solid rgba(255,255,255,0.06);
            }}
        """)

    def _satir_olustur(self, mod: str) -> QFrame:
        border = _KRITIK_BORDER if mod == "kritik" else _UYARI_BORDER
        bg     = _KRITIK_BG     if mod == "kritik" else _UYARI_BG
        icon   = "●" if mod == "kritik" else "●"
        label  = "KRİTİK" if mod == "kritik" else "UYARI"

        frame = QFrame()
        frame.setVisible(False)
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: {bg};
                border: 1px solid {border};
                border-radius: 6px;
            }}
        """)

        row = QHBoxLayout(frame)
        row.setContentsMargins(10, 4, 10, 4)
        row.setSpacing(8)

        # İkon + etiket
        lbl_icon = QLabel(f"{icon} {label}")
        lbl_icon.setStyleSheet(f"""
            color: {border};
            font-size: 11px;
            font-weight: 700;
            background: transparent;
            border: none;
            min-width: 64px;
        """)
        row.addWidget(lbl_icon)

        # Chip alanı (scroll olmadan, flex-wrap gibi yatay)
        chip_widget = QWidget()
        chip_widget.setStyleSheet("background: transparent; border: none;")
        chip_layout = QHBoxLayout(chip_widget)
        chip_layout.setContentsMargins(0, 0, 0, 0)
        chip_layout.setSpacing(6)
        chip_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        row.addWidget(chip_widget, 1)

        # Kapat butonu
        if mod == "kritik":
            self._kapat_btn = self._kapat_btn_olustur()
            row.addWidget(self._kapat_btn)

        # Referansları sakla
        if mod == "kritik":
            self._kritik_chip_layout = chip_layout
        else:
            self._uyari_chip_layout = chip_layout

        return frame

    def _kapat_btn_olustur(self) -> QPushButton:
        btn = QPushButton("✕")
        btn.setFixedSize(22, 22)
        btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn.setToolTip("Bu oturum için kapat")
        btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #5a5d6e;
                border: none;
                font-size: 13px;
                border-radius: 4px;
            }
            QPushButton:hover {
                color: #c9d1d9;
                background: rgba(255,255,255,0.08);
            }
        """)
        btn.clicked.connect(self._dismiss)
        return btn

    # ── Veri güncelleme ──────────────────────────────────────────────────────

    def guncelle(self, veri: dict):
        """
        BildirimWorker'dan gelen veriyle paneli günceller.
        Kapatılmış (dismissed) olsa bile veriyi saklar — yeni kritik
        geldiğinde paneli yeniden açar.
        """
        kritik_liste = veri.get("kritik", [])
        uyari_liste  = veri.get("uyari",  [])

        self._son_veri = veri

        # Yeni kritik bildirim varsa dismiss sıfırla
        if kritik_liste:
            self._dismissed = False

        if self._dismissed:
            return

        toplam = len(kritik_liste) + len(uyari_liste)
        if toplam == 0:
            self._animasyonlu_kapat()
            return

        self._chipları_doldur(self._kritik_chip_layout, kritik_liste, "kritik")
        self._chipları_doldur(self._uyari_chip_layout,  uyari_liste,  "uyari")

        self._kritik_frame.setVisible(bool(kritik_liste))
        self._uyari_frame.setVisible(bool(uyari_liste))

        self._animasyonlu_ac()

    def _chipları_doldur(self, layout: QHBoxLayout, liste: list, mod: str):
        """Mevcut chipleri temizle ve yenilerini ekle."""
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for bildirim in liste:
            chip = _BildirimChip(bildirim, mod)
            chip.clicked.connect(
                lambda _, b=bildirim: self.sayfa_ac.emit(b["grup"], b["sayfa"])
            )
            layout.addWidget(chip)

        layout.addStretch()

    # ── Animasyon ────────────────────────────────────────────────────────────

    def _animasyonlu_ac(self):
        if self.isVisible() and self.maximumHeight() > 0:
            return
        self.show()
        anim = QPropertyAnimation(self, b"maximumHeight", self)
        anim.setDuration(200)
        anim.setStartValue(0)
        anim.setEndValue(120)
        anim.setEasingCurve(QEasingCurve.OutCubic)
        anim.start(QPropertyAnimation.DeleteWhenStopped)

    def _animasyonlu_kapat(self):
        if not self.isVisible():
            return
        anim = QPropertyAnimation(self, b"maximumHeight", self)
        anim.setDuration(180)
        anim.setStartValue(self.height())
        anim.setEndValue(0)
        anim.setEasingCurve(QEasingCurve.InCubic)
        anim.finished.connect(self.hide)
        anim.start(QPropertyAnimation.DeleteWhenStopped)

    def _dismiss(self):
        """Oturum boyunca paneli kapat."""
        self._dismissed = True
        self._animasyonlu_kapat()
        logger.info("Bildirim paneli oturum için kapatıldı")
