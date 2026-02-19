# -*- coding: utf-8 -*-
"""
Cihaz 360° Merkez — v3
────────────────────────
Personel modülündeki PersonelMerkezPage deseninde:
• Header (52px) + sekme nav (36px)
• QStackedWidget: her sekme kendi Component dosyasında (lazy-load)
• Sağ panel (300px): uyarılar + HizliArizaGiris inline

Sekme → Component eşleşmesi:
  GENEL       → components.cihaz_genel_panel.CihazGenelPanel
  ARIZA       → components.ariza_panel.ArizaPanel
  KALIBRASYON → components.kalibrasyon_panel.KalibrasyonPanel
  BAKIM       → components.bakim_panel.BakimPanel
"""
from datetime import date

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QStackedWidget, QScrollArea,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QCursor

from core.logger import logger
from ui.theme_manager import ThemeManager
from ui.styles import DarkTheme

from ui.pages.cihaz.components.cihaz_genel_panel import CihazGenelPanel
from ui.pages.cihaz.components.ariza_panel       import ArizaPanel
from ui.pages.cihaz.components.kalibrasyon_panel import KalibrasyonPanel
from ui.pages.cihaz.components.bakim_panel       import BakimPanel
from ui.pages.cihaz.components.hizli_ariza_giris import HizliArizaGiris

C      = DarkTheme
STYLES = ThemeManager.get_all_component_styles()

TABS = [
    ("GENEL",       "Genel Bilgi"),
    ("ARIZA",       "Arızalar"),
    ("KALIBRASYON", "Kalibrasyon"),
    ("BAKIM",       "Periyodik Bakım"),
]

TIP_SIMGE = {
    "Röntgen": "R", "MR": "M", "CT": "C", "USG": "U",
    "EKG": "E", "Monitör": "V", "Enjektör": "J",
    "Bilgisayar": "B", "Yazıcı": "Y",
}

CIHAZ_DURUM_BADGE = {
    "Aktif":         STYLES.get("header_durum_aktif",  ""),
    "Arızalı":       STYLES.get("header_durum_pasif",  ""),
    "Bakımda":       STYLES.get("header_durum_izinli", ""),
    "Pasif":         STYLES.get("section_label",       ""),
    "Kalibrasyonda": (
        f"color:#a78bfa; background:rgba(167,139,250,.15);"
        f"border:1px solid rgba(167,139,250,.3);"
        "border-radius:4px; padding:0 8px; font-size:11px; font-weight:500;"
    ),
}


class CihazMerkezPage(QWidget):

    kapat_istegi = Signal()

    def __init__(self, db, cihaz_data: dict, parent=None):
        super().__init__(parent)
        self.db        = db
        self.cihaz     = cihaz_data or {}
        self._cihaz_id = str(self.cihaz.get("Cihazid", ""))
        self._nav_btns = {}
        self._modules  = {}

        self._setup_ui()
        self._load_header()
        self._switch_tab("GENEL")

    # ═══════════════════════════════════════════════════
    #  UI
    # ═══════════════════════════════════════════════════

    def _setup_ui(self):
        self.setStyleSheet(STYLES["page"])
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._build_header())

        body     = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        self.content_stack = QStackedWidget()
        body.addWidget(self.content_stack, 1)
        body.addWidget(self._build_right_panel())

        body_w = QWidget()
        body_w.setLayout(body)
        root.addWidget(body_w, 1)

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
        tl  = QHBoxLayout(top)
        tl.setContentsMargins(16, 0, 16, 0)
        tl.setSpacing(10)

        btn_back = QPushButton("← Listeye")
        btn_back.setCursor(QCursor(Qt.PointingHandCursor))
        btn_back.setStyleSheet(STYLES["back_btn"])
        btn_back.clicked.connect(self.kapat_istegi.emit)
        tl.addWidget(btn_back)
        tl.addWidget(self._sep(20))

        self.lbl_icon = QLabel()
        self.lbl_icon.setFixedSize(34, 34)
        self.lbl_icon.setAlignment(Qt.AlignCenter)
        self.lbl_icon.setStyleSheet(
            f"background:{C.BG_TERTIARY}; border-radius:8px;"
            f"font-size:13px; font-weight:700; color:{C.TEXT_SECONDARY};"
        )
        tl.addWidget(self.lbl_icon)

        info = QVBoxLayout()
        info.setSpacing(1)
        self.lbl_ad = QLabel("Yükleniyor…")
        self.lbl_ad.setStyleSheet(
            f"font-size:14px; font-weight:600; color:{C.TEXT_PRIMARY}; background:transparent;"
        )
        self.lbl_detay = QLabel("")
        self.lbl_detay.setStyleSheet(STYLES["info_label"])
        info.addWidget(self.lbl_ad)
        info.addWidget(self.lbl_detay)
        tl.addLayout(info)

        self.lbl_durum = QLabel("")
        self.lbl_durum.setFixedHeight(22)
        tl.addWidget(self.lbl_durum)

        tl.addStretch()

        self.btn_ariza_hizli = QPushButton("+ Arıza Bildir")
        self.btn_ariza_hizli.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_ariza_hizli.setStyleSheet(STYLES["refresh_btn"])
        self.btn_ariza_hizli.clicked.connect(self._toggle_ariza_form)
        tl.addWidget(self.btn_ariza_hizli)

        btn_x = QPushButton("✕")
        btn_x.setCursor(QCursor(Qt.PointingHandCursor))
        btn_x.setToolTip("Kapat")
        btn_x.setStyleSheet(
            f"QPushButton{{background:transparent;border:none;color:{C.TEXT_MUTED};font-size:14px;}}"
            f"QPushButton:hover{{color:{C.TEXT_PRIMARY};}}"
        )
        btn_x.clicked.connect(self.kapat_istegi.emit)
        tl.addWidget(btn_x)
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
            btn.setStyleSheet(self._tab_qss(False))
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

        # Hızlı Arıza Formu (gizli)
        self.ariza_form_frame = QFrame()
        self.ariza_form_frame.setVisible(False)
        self.ariza_form_frame.setStyleSheet(
            f"background:{C.BG_TERTIARY}; border-bottom:1px solid {C.BORDER_PRIMARY};"
        )
        afl = QVBoxLayout(self.ariza_form_frame)
        afl.setContentsMargins(14, 0, 14, 8)

        self.ariza_form = HizliArizaGiris(db=self.db, cihaz_id=self._cihaz_id, parent=self)
        self.ariza_form.ariza_kaydedildi.connect(self._on_ariza_kaydedildi)
        self.ariza_form.iptal_edildi.connect(self._hide_ariza_form)
        afl.addWidget(self.ariza_form)
        lay.addWidget(self.ariza_form_frame)

        # Uyarılar + hızlı işlemler
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
        for label, cb in [
            ("Arıza Bildir",     self._toggle_ariza_form),
            ("Arızalar Sekmesi", lambda: self._switch_tab("ARIZA")),
            ("Kalibrasyon Ekle", lambda: self._switch_tab("KALIBRASYON")),
            ("Bakım Planı",      lambda: self._switch_tab("BAKIM")),
        ]:
            btn = QPushButton(label)
            btn.setCursor(QCursor(Qt.PointingHandCursor))
            btn.setStyleSheet(STYLES["action_btn"])
            btn.clicked.connect(cb)
            il.addWidget(btn)

        il.addStretch()
        scroll.setWidget(info_w)
        lay.addWidget(scroll, 1)
        return panel

    # ═══════════════════════════════════════════════════
    #  HEADER
    # ═══════════════════════════════════════════════════

    def _load_header(self):
        p     = self.cihaz
        marka = str(p.get("Marka", "") or "")
        model = str(p.get("Model", "") or "")
        cid   = str(p.get("Cihazid", ""))
        tip   = str(p.get("CihazTipi", "") or "")
        birim = str(p.get("Birim", "") or "")
        durum = str(p.get("Durum", ""))

        self.lbl_ad.setText(f"{marka} {model}".strip() or "—")
        self.lbl_detay.setText(" · ".join(filter(None, [tip, birim, f"#{cid}"])))
        self.lbl_icon.setText(TIP_SIMGE.get(tip, tip[:1].upper() if tip else "?"))
        self.lbl_durum.setText(durum)
        self.lbl_durum.setStyleSheet(CIHAZ_DURUM_BADGE.get(durum, STYLES.get("info_label", "")))
        self._fill_alerts()

    def _fill_alerts(self):
        while self.alert_container.count():
            item = self.alert_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        alerts = self._compute_alerts()
        if not alerts:
            lbl = QLabel("✓  Kritik durum yok")
            lbl.setStyleSheet(f"color:{C.STATUS_SUCCESS}; background:transparent; font-size:12px;")
            self.alert_container.addWidget(lbl)
            return

        for text, level in alerts:
            color = {"error": C.STATUS_ERROR, "warning": C.STATUS_WARNING}.get(level, C.TEXT_MUTED)
            lbl = QLabel(f"{'⚠' if level == 'error' else '○'}  {text}")
            lbl.setWordWrap(True)
            lbl.setStyleSheet(
                f"color:{color}; background:{C.BG_TERTIARY};"
                f"border:1px solid {C.BORDER_PRIMARY};"
                "border-radius:5px; padding:6px 10px; font-size:12px;"
            )
            self.alert_container.addWidget(lbl)

    def _compute_alerts(self) -> list:
        alerts = []
        bugun  = date.today()
        kal_str = str(self.cihaz.get("KalibrasyonSonTarih", "") or "")
        if kal_str:
            try:
                from core.date_utils import parse_date
                kal = parse_date(kal_str)
                if kal:
                    delta = (kal - bugun).days
                    if delta < 0:
                        alerts.append((f"Kalibrasyon {abs(delta)} gün önce sona erdi!", "error"))
                    elif delta <= 30:
                        alerts.append((f"Kalibrasyon {delta} gün içinde sona erecek.", "warning"))
            except Exception:
                pass
        durum = str(self.cihaz.get("Durum", "")).strip()
        if durum == "Arızalı":
            alerts.append(("Cihaz arızalı — bakım gerekli.", "error"))
        elif durum == "Bakımda":
            alerts.append(("Cihaz bakımda.", "warning"))
        return alerts

    # ═══════════════════════════════════════════════════
    #  SEKME
    # ═══════════════════════════════════════════════════

    def _switch_tab(self, code: str):
        for c, btn in self._nav_btns.items():
            btn.setStyleSheet(self._tab_qss(c == code))
        if code not in self._modules:
            self._modules[code] = self._create_module(code)
            self.content_stack.addWidget(self._modules[code])
        self.content_stack.setCurrentWidget(self._modules[code])

    def _create_module(self, code: str) -> QWidget:
        try:
            if code == "GENEL":
                w = CihazGenelPanel(cihaz_data=self.cihaz, db=self.db)
                w.veri_guncellendi.connect(self._on_genel_saved)
                return w
            elif code == "ARIZA":
                w = ArizaPanel(db=self.db, cihaz_id=self._cihaz_id)
                w.load_data(); return w
            elif code == "KALIBRASYON":
                w = KalibrasyonPanel(cihaz_id=self._cihaz_id, db=self.db)
                w.load_data(); return w
            elif code == "BAKIM":
                w = BakimPanel(cihaz_id=self._cihaz_id, db=self.db)
                w.load_data(); return w
            raise ValueError(code)
        except Exception as e:
            logger.error(f"Cihaz sekme yükleme ({code}): {e}")
            err = QLabel(f"Modül yüklenemedi:\n{code}\n{e}")
            err.setAlignment(Qt.AlignCenter)
            err.setStyleSheet(f"color:{C.STATUS_ERROR};")
            return err

    def _on_genel_saved(self):
        try:
            from core.di import get_registry
            for r in get_registry(self.db).get("Cihazlar").get_all():
                if str(r.get("Cihazid", "")) == self._cihaz_id:
                    self.cihaz = r; break
        except Exception:
            pass
        self._load_header()

    # ═══════════════════════════════════════════════════
    #  HIZLI ARIZA FORMU
    # ═══════════════════════════════════════════════════

    def _toggle_ariza_form(self):
        if not self.ariza_form_frame.isVisible():
            self.ariza_form.yenile(self._cihaz_id)
        self.ariza_form_frame.setVisible(not self.ariza_form_frame.isVisible())

    def _hide_ariza_form(self):
        self.ariza_form_frame.setVisible(False)

    def _on_ariza_kaydedildi(self):
        self._hide_ariza_form()
        self._fill_alerts()
        if "ARIZA" in self._modules:
            try:
                self._modules["ARIZA"].load_data()
            except Exception:
                pass

    # ═══════════════════════════════════════════════════
    #  YARDIMCILAR
    # ═══════════════════════════════════════════════════

    @staticmethod
    def _sep(h: int = 20) -> QFrame:
        s = QFrame(); s.setFixedSize(1, h)
        s.setStyleSheet(f"background:{C.BORDER_PRIMARY};")
        return s

    @staticmethod
    def _sec_lbl(text: str) -> QLabel:
        lbl = QLabel(text); lbl.setStyleSheet(STYLES["section_label"]); return lbl

    @staticmethod
    def _tab_qss(active: bool) -> str:
        if active:
            return (
                f"QPushButton{{background:transparent;border:none;"
                f"border-bottom:2px solid {C.INPUT_BORDER_FOCUS};"
                f"color:{C.BTN_PRIMARY_TEXT};font-size:12px;font-weight:600;padding:0 14px;}}"
            )
        return (
            "QPushButton{background:transparent;border:none;"
            "border-bottom:2px solid transparent;"
            f"color:{C.TEXT_MUTED};font-size:12px;padding:0 14px;}}"
            f"QPushButton:hover{{color:{C.TEXT_SECONDARY};}}"
        )
