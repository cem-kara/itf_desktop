# -*- coding: utf-8 -*-
"""
Cihaz 360° Merkez — v2 (Yeni Dosya)
─────────────────────────────────────
Cihaz listesinde "Detay" tıklandığında bu sayfa açılır.
CihazDetayPage'in yerini alır; daha zengin bir deneyim sunar.

Yapı:
• Header (52px): ← Listeye | İkon + Marka/Model + Cihaz ID | Durum badge | Arıza Bildir butonu
• Sekme nav (36px): GENEL | ARIZALAR | KALİBRASYON | PERİYODİK BAKIM
• Sağ panel (300px): Uyarılar (yaklaşan bakım/kalibrasyon) + hızlı işlemler
• Form container (sağ panelin üstüne açılır): Arıza formu inline

Modüller lazy-load, mevcut kodlar değişmeden kullanılır.
"""
import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QStackedWidget, QScrollArea, QMessageBox,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QCursor, QColor

from ui.theme_manager import ThemeManager
from ui.styles import DarkTheme
from ui.styles.icons import IconRenderer
from core.logger import logger

C      = DarkTheme
STYLES = ThemeManager.get_all_component_styles()

# Sekme tanımları
TABS = [
    ("GENEL",      "Genel Bilgi"),
    ("ARIZA",      "Arızalar"),
    ("KALIBRASYON","Kalibrasyon"),
    ("BAKIM",      "Periyodik Bakım"),
]

# Durum renkleri (cihaz bazlı)
CIHAZ_DURUM_BADGE = {
    "Aktif":         STYLES.get("header_durum_aktif",  ""),
    "Arızalı":       STYLES.get("header_durum_pasif",  ""),   # kırmızı grubu
    "Bakımda":       STYLES.get("header_durum_izinli", ""),   # sarı grubu
    "Pasif":         STYLES.get("section_label",       ""),
    "Kalibrasyonda": "color:#a78bfa; background:rgba(167,139,250,.15); border:1px solid rgba(167,139,250,.3); border-radius:4px; padding:0 8px; font-size:11px; font-weight:500;",
}

TIP_SIMGE = {
    "Röntgen": "R", "MR": "M", "CT": "C", "USG": "U",
    "EKG": "E", "Monitör": "V", "Enjektör": "J",
    "Bilgisayar": "B", "Yazıcı": "Y",
}


class CihazMerkezPage(QWidget):
    """Cihaz 360° detay hub'ı."""

    kapat_istegi = Signal()

    def __init__(self, db, cihaz_data: dict, parent=None):
        super().__init__(parent)
        self.db          = db
        self.cihaz       = cihaz_data or {}
        self._cihaz_id   = str(self.cihaz.get("Cihazid", ""))
        self._modules    = {}
        self._nav_btns   = {}
        self._active_tab = "GENEL"
        self._form_widget       = None
        self._current_form_type = None
        self._initial_load      = False

        self._setup_ui()
        self._load_header()
        self._switch_tab("GENEL")
        self._initial_load = True

    # ═══════════════════════════════════════════════════
    #  UI KURULUM
    # ═══════════════════════════════════════════════════

    def _setup_ui(self):
        self.setStyleSheet(STYLES["page"])
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._build_header())

        body_lay = QHBoxLayout()
        body_lay.setSpacing(0)
        body_lay.setContentsMargins(0, 0, 0, 0)
        self.content_stack = QStackedWidget()
        body_lay.addWidget(self.content_stack, 1)
        body_lay.addWidget(self._build_right_panel())

        body = QWidget()
        body.setLayout(body_lay)
        root.addWidget(body, 1)

    def _build_header(self) -> QFrame:
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

        # ── Üst şerit (52px) ──
        top = QWidget()
        top.setFixedHeight(52)
        tl = QHBoxLayout(top)
        tl.setContentsMargins(16, 0, 16, 0)
        tl.setSpacing(10)

        btn_back = QPushButton("← Listeye")
        btn_back.setCursor(QCursor(Qt.PointingHandCursor))
        btn_back.setStyleSheet(STYLES["back_btn"])
        btn_back.clicked.connect(self.kapat_istegi.emit)
        tl.addWidget(btn_back)
        tl.addWidget(self._sep())

        # Cihaz ikonu (tip rengi)
        self.lbl_icon = QLabel()
        self.lbl_icon.setFixedSize(34, 34)
        self.lbl_icon.setAlignment(Qt.AlignCenter)
        self.lbl_icon.setStyleSheet(
            f"background:{C.BG_TERTIARY}; border-radius:8px;"
            f"font-size:13px; font-weight:700; color:{C.TEXT_SECONDARY};"
        )
        tl.addWidget(self.lbl_icon)

        # Marka/Model + Cihaz ID
        info_lay = QVBoxLayout()
        info_lay.setSpacing(1)
        self.lbl_ad = QLabel("Yükleniyor…")
        self.lbl_ad.setStyleSheet(
            f"font-size:14px; font-weight:600; color:{C.TEXT_PRIMARY}; background:transparent;"
        )
        self.lbl_detay = QLabel("")
        self.lbl_detay.setStyleSheet(STYLES["info_label"])
        info_lay.addWidget(self.lbl_ad)
        info_lay.addWidget(self.lbl_detay)
        tl.addLayout(info_lay)

        self.lbl_durum = QLabel("")
        self.lbl_durum.setFixedHeight(22)
        tl.addWidget(self.lbl_durum)

        tl.addStretch()

        # Hızlı aksiyonlar
        self.btn_ariza = QPushButton("+ Arıza Bildir")
        self.btn_ariza.setFixedHeight(28)
        self.btn_ariza.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_ariza.setStyleSheet(STYLES["refresh_btn"])
        self.btn_ariza.clicked.connect(lambda: self._toggle_form("ARIZA"))
        tl.addWidget(self.btn_ariza)

        self.btn_bakim = QPushButton("+ Bakım Ekle")
        self.btn_bakim.setFixedHeight(28)
        self.btn_bakim.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_bakim.setStyleSheet(STYLES["refresh_btn"])
        self.btn_bakim.clicked.connect(lambda: self._switch_tab("BAKIM"))
        tl.addWidget(self.btn_bakim)

        btn_kapat = QPushButton()
        btn_kapat.setFixedSize(28, 28)
        btn_kapat.setStyleSheet("background:transparent; border:none;")
        btn_kapat.setCursor(QCursor(Qt.PointingHandCursor))
        btn_kapat.setToolTip("Kapat")
        btn_kapat.clicked.connect(self.kapat_istegi.emit)
        try:
            IconRenderer.set_button_icon(btn_kapat, "x", color=C.TEXT_MUTED, size=14)
        except Exception:
            btn_kapat.setText("✕")
        tl.addWidget(btn_kapat)
        lay.addWidget(top)

        # ── Sekme nav (36px) ──
        nav = QWidget()
        nav.setFixedHeight(36)
        nav.setStyleSheet(f"background:transparent; border-top:1px solid {C.BORDER_SECONDARY};")
        nl = QHBoxLayout(nav)
        nl.setContentsMargins(16, 0, 16, 0)
        nl.setSpacing(0)
        for code, label in TABS:
            btn = QPushButton(label)
            btn.setCursor(QCursor(Qt.PointingHandCursor))
            btn.setStyleSheet(self._tab_qss(active=False))
            btn.clicked.connect(lambda _, c=code: self._switch_tab(c))
            self._nav_btns[code] = btn
            nl.addWidget(btn)
        nl.addStretch()
        lay.addWidget(nav)
        return outer

    def _build_right_panel(self) -> QFrame:
        panel = QFrame()
        panel.setFixedWidth(300)
        panel.setStyleSheet(f"""
            QFrame {{
                background-color: {C.BG_SECONDARY};
                border-left: 1px solid {C.BORDER_PRIMARY};
            }}
        """)
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # Form container (gizli başlar)
        self.form_container = QFrame()
        self.form_container.setVisible(False)
        self.form_container.setStyleSheet(
            f"background:{C.BG_TERTIARY}; border-bottom:1px solid {C.BORDER_PRIMARY};"
        )
        self.form_outer_lay = QVBoxLayout(self.form_container)
        self.form_outer_lay.setContentsMargins(12, 10, 12, 10)
        self.form_outer_lay.setSpacing(8)

        form_hdr = QHBoxLayout()
        self.lbl_form_title = QLabel("İşlem")
        self.lbl_form_title.setStyleSheet(STYLES["section_label"])
        form_hdr.addWidget(self.lbl_form_title)
        form_hdr.addStretch()
        btn_form_kapat = QPushButton()
        btn_form_kapat.setFixedSize(20, 20)
        btn_form_kapat.setStyleSheet("background:transparent; border:none;")
        btn_form_kapat.setCursor(QCursor(Qt.PointingHandCursor))
        btn_form_kapat.clicked.connect(self._hide_form)
        try:
            IconRenderer.set_button_icon(btn_form_kapat, "x", color=C.TEXT_MUTED, size=11)
        except Exception:
            btn_form_kapat.setText("✕")
        form_hdr.addWidget(btn_form_kapat)
        self.form_outer_lay.addLayout(form_hdr)

        self.form_content_lay = QVBoxLayout()
        self.form_content_lay.setContentsMargins(0, 0, 0, 0)
        self.form_outer_lay.addLayout(self.form_content_lay)
        lay.addWidget(self.form_container)

        # Scroll: uyarılar + hızlı işlemler
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet(STYLES["scroll"])

        info_w = QWidget()
        info_w.setStyleSheet("background:transparent;")
        il = QVBoxLayout(info_w)
        il.setContentsMargins(14, 16, 14, 16)
        il.setSpacing(14)

        il.addWidget(self._sec_lbl("DURUM"))
        self.alert_container = QVBoxLayout()
        self.alert_container.setSpacing(5)
        il.addLayout(self.alert_container)

        il.addWidget(self._sec_lbl("HIZLI İŞLEMLER"))
        for label, icon, cb in [
            ("Arıza Bildir",     "alert-triangle",  lambda: self._toggle_form("ARIZA")),
            ("Kalibrasyon Ekle", "check-circle",     lambda: self._switch_tab("KALIBRASYON")),
            ("Bakım Ekle",       "tool",             lambda: self._switch_tab("BAKIM")),
            ("Durum Değiştir",   "refresh-cw",       None),
        ]:
            il.addWidget(self._action_btn(label, icon, cb))

        il.addStretch()
        scroll.setWidget(info_w)
        lay.addWidget(scroll, 1)
        return panel

    # ═══════════════════════════════════════════════════
    #  HEADER & UYARILAR
    # ═══════════════════════════════════════════════════

    def _load_header(self):
        p = self.cihaz
        marka = str(p.get("Marka", "") or "")
        model = str(p.get("Model", "") or "")
        cid   = str(p.get("Cihazid", ""))
        tip   = str(p.get("CihazTipi", "") or "")
        birim = str(p.get("Birim", "") or "")
        durum = str(p.get("Durum", ""))

        ad = f"{marka} {model}".strip() or "—"
        self.lbl_ad.setText(ad)
        self.lbl_detay.setText(" · ".join(filter(None, [tip, birim, f"#{cid}"])))

        # İkon
        harf = TIP_SIMGE.get(tip, tip[:1].upper() if tip else "?")
        self.lbl_icon.setText(harf)

        # Durum badge
        badge_qss = CIHAZ_DURUM_BADGE.get(durum, STYLES.get("info_label", ""))
        self.lbl_durum.setText(durum)
        self.lbl_durum.setStyleSheet(badge_qss)

        # Uyarıları doldur
        self._fill_alerts()

    def _fill_alerts(self):
        while self.alert_container.count():
            item = self.alert_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        alerts = self._compute_alerts()

        if not alerts:
            lbl = QLabel("✓ Kritik durum yok")
            lbl.setStyleSheet(
                f"color:{C.STATUS_SUCCESS}; background:transparent; font-size:12px;"
            )
            self.alert_container.addWidget(lbl)
            return

        for text, level in alerts:
            color = {
                "error":   C.STATUS_ERROR,
                "warning": C.STATUS_WARNING,
                "info":    C.STATUS_INFO,
            }.get(level, C.TEXT_MUTED)
            lbl = QLabel(f"{'⚠' if level=='error' else '○'}  {text}")
            lbl.setWordWrap(True)
            lbl.setStyleSheet(
                f"color:{color}; background:{C.BG_TERTIARY};"
                f"border:1px solid {C.BORDER_PRIMARY};"
                "border-radius:5px; padding:6px 10px; font-size:12px;"
            )
            self.alert_container.addWidget(lbl)

    def _compute_alerts(self) -> list[tuple[str, str]]:
        """Kalibrasyon ve bakım için uyarı listesi üretir."""
        alerts = []
        from datetime import date
        bugun = date.today()

        # Kalibrasyon son tarih
        kal_str = str(self.cihaz.get("KalibrasyonSonTarih", "") or "")
        if kal_str:
            from core.date_utils import parse_date as pd
            kal = pd(kal_str)
            if kal:
                delta = (kal - bugun).days
                if delta < 0:
                    alerts.append((f"Kalibrasyon {abs(delta)} gün önce sona erdi!", "error"))
                elif delta <= 30:
                    alerts.append((f"Kalibrasyon {delta} gün içinde sona erecek.", "warning"))

        # Cihaz durumu
        durum = str(self.cihaz.get("Durum", "")).strip()
        if durum == "Arızalı":
            alerts.append(("Cihaz arızalı — bakım gerekli.", "error"))
        elif durum == "Bakımda":
            alerts.append(("Cihaz bakımda.", "warning"))

        return alerts

    # ═══════════════════════════════════════════════════
    #  SEKME YÖNETİMİ
    # ═══════════════════════════════════════════════════

    def _switch_tab(self, code: str):
        self._active_tab = code
        for c, btn in self._nav_btns.items():
            btn.setStyleSheet(self._tab_qss(active=(c == code)))

        if code not in self._modules:
            widget = self._create_module(code)
            self._modules[code] = widget
            self.content_stack.addWidget(widget)

        self.content_stack.setCurrentWidget(self._modules[code])

    def _create_module(self, code: str) -> QWidget:
        try:
            if code == "GENEL":
                from ui.pages.cihaz.cihaz_ekle import CihazEklePage
                w = CihazEklePage(db=self.db, edit_data=self.cihaz,
                                  on_saved=self._on_genel_saved)
            elif code == "ARIZA":
                from ui.pages.cihaz.ariza_listesi import ArizaListesiPage
                w = ArizaListesiPage(db=self.db)
                if hasattr(w, "load_data"):
                    w.load_data()
            elif code == "KALIBRASYON":
                from ui.pages.cihaz.kalibrasyon_takip import KalibrasyonTakipPage
                w = KalibrasyonTakipPage(db=self.db)
                if hasattr(w, "load_data"):
                    w.load_data()
            elif code == "BAKIM":
                from ui.pages.cihaz.periyodik_bakim import PeriyodikBakimPage
                w = PeriyodikBakimPage(db=self.db)
                if hasattr(w, "load_data"):
                    w.load_data()
            else:
                raise ValueError(f"Bilinmeyen sekme: {code}")

            if hasattr(w, "set_embedded_mode"):
                w.set_embedded_mode(True)
            return w

        except Exception as e:
            logger.error(f"Cihaz modül yükleme ({code}): {e}")
            err = QLabel(f"Modül yüklenemedi: {code}\n{e}")
            err.setAlignment(Qt.AlignCenter)
            err.setStyleSheet(STYLES.get("stat_red", f"color:{C.STATUS_ERROR};"))
            return err

    def _on_genel_saved(self):
        """Genel bilgi kaydedilince header'ı güncelle."""
        self._load_header()

    # ═══════════════════════════════════════════════════
    #  FORM YÖNETİMİ (arıza inline)
    # ═══════════════════════════════════════════════════

    def _toggle_form(self, form_type: str):
        if self.form_container.isVisible() and self._current_form_type == form_type:
            self._hide_form()
            return
        self._show_form(form_type)

    def _show_form(self, form_type: str):
        # Önceki formu temizle
        while self.form_content_lay.count():
            item = self.form_content_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._form_widget = None

        try:
            if form_type == "ARIZA":
                self.lbl_form_title.setText("ARIZA BİLDİRİMİ")
                from ui.pages.cihaz.ariza_ekle import ArizaEklePanel
                form = ArizaEklePanel(db=self.db, parent=self)
                form.formu_sifirla(self._cihaz_id)
                form.kayit_basarili_sinyali.connect(self._on_form_saved)
                form.kapanma_istegi.connect(self._hide_form)
            else:
                return

            self.form_content_lay.addWidget(form)
            self._form_widget       = form
            self._current_form_type = form_type
            self.form_container.setVisible(True)

        except Exception as e:
            logger.error(f"Form yükleme ({form_type}): {e}")
            QMessageBox.critical(self, "Hata", f"Form yüklenemedi:\n{e}")

    def _hide_form(self):
        self.form_container.setVisible(False)
        while self.form_content_lay.count():
            item = self.form_content_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._form_widget       = None
        self._current_form_type = None

    def _on_form_saved(self):
        self._hide_form()
        self._fill_alerts()
        # Arıza sekmesini yenile
        if "ARIZA" in self._modules and hasattr(self._modules["ARIZA"], "load_data"):
            self._modules["ARIZA"].load_data()

    # ═══════════════════════════════════════════════════
    #  YARDIMCILAR
    # ═══════════════════════════════════════════════════

    @staticmethod
    def _sep() -> QFrame:
        s = QFrame(); s.setFixedSize(1, 20)
        s.setStyleSheet(f"background:{C.BORDER_PRIMARY};")
        return s

    @staticmethod
    def _sec_lbl(text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet(STYLES["section_label"])
        return lbl

    @staticmethod
    def _action_btn(label: str, icon: str, callback) -> QPushButton:
        btn = QPushButton(label)
        btn.setCursor(QCursor(Qt.PointingHandCursor))
        btn.setFixedHeight(34)
        btn.setStyleSheet(STYLES["action_btn"])
        try:
            IconRenderer.set_button_icon(btn, icon, color=C.TEXT_SECONDARY, size=13)
        except Exception:
            pass
        if callback:
            btn.clicked.connect(callback)
        else:
            btn.setEnabled(False)
        return btn

    @staticmethod
    def _tab_qss(active: bool) -> str:
        if active:
            return (
                f"QPushButton{{background:transparent;border:none;"
                f"border-bottom:2px solid {C.INPUT_BORDER_FOCUS};"
                f"color:{C.BTN_PRIMARY_TEXT};"
                f"font-size:12px;font-weight:600;padding:0 14px;}}"
            )
        return (
            f"QPushButton{{background:transparent;border:none;"
            f"border-bottom:2px solid transparent;"
            f"color:{C.TEXT_MUTED};font-size:12px;padding:0 14px;}}"
            f"QPushButton:hover{{color:{C.TEXT_SECONDARY};}}"
        )
