# ui/sidebar.py  ─  REPYS v3 · Medikal Dark-Blue Sidebar
import json, os
from PySide6.QtCore import Qt, QSize, Signal
from PySide6.QtGui import QCursor, QColor, QLinearGradient, QPainter
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QVBoxLayout, QWidget, QGraphicsDropShadowEffect,
)
from core.config import AppConfig
from core.paths import BASE_DIR
from ui.styles.colors import DarkTheme as T
from ui.styles.icons import GROUP_ICON_MAP, MENU_ICON_MAP, IconColors, Icons

# ── Renk sabitleri ──────────────────────────────────────────────
BG            = "#0a1520"       # sidebar zemin (topbar'dan biraz daha koyu)
BORDER        = "rgba(255,255,255,0.07)"
HEADER_BG     = "#060d1a"       # logo alanı
ITEM_TEXT     = "#6a90b4"
ITEM_HOVER_BG = "rgba(255,255,255,0.04)"
ITEM_HOVER_T  = "#c2d8ef"
ACTIVE_BG     = "rgba(0,180,216,0.12)"
ACTIVE_BORDER = "#00b4d8"
ACTIVE_TEXT   = "#22d3ee"
GROUP_LBL     = "#2e4a68"
SYNC_BG       = "#00b4d8"
SYNC_HOVER    = "#22d3ee"
SYNC_TEXT     = "#060d1a"
STATUS_READY  = T.STATUS_SUCCESS
STATUS_WARN   = T.STATUS_WARNING
STATUS_ERROR  = T.STATUS_ERROR
NOTIFY_BG     = "rgba(245,158,11,0.10)"
NOTIFY_HOVER  = "rgba(245,158,11,0.18)"
NOTIFY_TEXT   = "#f59e0b"
NOTIFY_BORDER = "rgba(245,158,11,0.25)"


class FlatSection(QWidget):
    def __init__(self, group_name: str, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background: transparent;")
        self.group_name = group_name
        self._buttons   = []

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        lbl = QLabel(group_name.upper())
        lbl.setStyleSheet(
            f"color: {GROUP_LBL}; font-size: 10px; font-weight: 700;"
            f" letter-spacing: 0.14em; background: transparent;"
            f" padding: 14px 16px 5px 16px;"
        )
        lay.addWidget(lbl)

        self.content = QWidget()
        self.content.setStyleSheet("background: transparent;")
        self._content_lay = QVBoxLayout(self.content)
        self._content_lay.setContentsMargins(8, 2, 8, 4)
        self._content_lay.setSpacing(1)
        lay.addWidget(self.content)

    def add_item(self, baslik: str, callback, icon_key: str | None = None) -> QPushButton:
        btn = QPushButton(f"  {baslik}")
        btn.setCursor(QCursor(Qt.PointingHandCursor))
        btn.setCheckable(True)
        btn.setFixedHeight(34)
        btn._baslik = baslik

        resolved = (icon_key if (icon_key and icon_key in Icons.available())
                    else MENU_ICON_MAP.get(baslik))
        btn._icon_key = resolved
        if resolved:
            try:
                btn.setIcon(Icons.get(resolved, size=14, color=ITEM_TEXT))
                btn.setIconSize(QSize(14, 14))
            except Exception:
                pass

        btn.setStyleSheet(self._item_css(False))
        btn.clicked.connect(lambda _=False: callback(self.group_name, baslik))
        self._content_lay.addWidget(btn)
        self._buttons.append(btn)
        return btn

    @staticmethod
    def _item_css(active: bool) -> str:
        if active:
            return (
                f"QPushButton {{"
                f"  background: {ACTIVE_BG};"
                f"  color: {ACTIVE_TEXT};"
                f"  border: none;"
                f"  border-left: 2px solid {ACTIVE_BORDER};"
                f"  border-radius: 0 8px 8px 0;"
                f"  text-align: left;"
                f"  padding-left: 12px;"
                f"  font-size: 13px;"
                f"  font-weight: 600;"
                f"}}"
            )
        return (
            f"QPushButton {{"
            f"  background: transparent;"
            f"  color: {ITEM_TEXT};"
            f"  border: none;"
            f"  border-left: 2px solid transparent;"
            f"  border-radius: 0 8px 8px 0;"
            f"  text-align: left;"
            f"  padding-left: 12px;"
            f"  font-size: 13px;"
            f"}}"
            f"QPushButton:hover {{"
            f"  background: {ITEM_HOVER_BG};"
            f"  color: {ITEM_HOVER_T};"
            f"  border-left-color: rgba(0,180,216,0.30);"
            f"}}"
        )

    def set_active(self, baslik: str | None):
        for btn in self._buttons:
            active = btn._baslik == baslik
            btn.setChecked(active)
            btn.setStyleSheet(self._item_css(active))
            key = getattr(btn, "_icon_key", None) or MENU_ICON_MAP.get(btn._baslik)
            if key:
                try:
                    color = ACTIVE_TEXT if active else ITEM_TEXT
                    btn.setIcon(Icons.get(key, size=14, color=color))
                except Exception:
                    pass


class Sidebar(QWidget):
    menu_clicked      = Signal(str, str)
    dashboard_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(230)
        self.setAutoFillBackground(True)
        self.setStyleSheet(f"background-color: {BG};")

        # Sağ kenar ince çizgi + gölge
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(24)
        shadow.setOffset(6, 0)
        shadow.setColor(QColor(0, 0, 0, 60))
        self.setGraphicsEffect(shadow)

        self._groups        = {}
        self._all_buttons   = {}
        self._active_baslik = None
        self._build_ui()

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # ── Logo / Header ──────────────────────────────────────
        header = QWidget()
        header.setFixedHeight(58)
        header.setStyleSheet(
            f"background: {HEADER_BG};"
            f"border-bottom: 1px solid rgba(0,180,216,0.15);"
        )
        hl = QHBoxLayout(header)
        hl.setContentsMargins(16, 0, 14, 0)
        hl.setSpacing(10)

        # İkon
        try:
            logo_lbl = QLabel()
            logo_lbl.setPixmap(Icons.pixmap("hospital", size=22, color=ACTIVE_TEXT))
            logo_lbl.setFixedSize(22, 22)
            hl.addWidget(logo_lbl)
        except Exception:
            dot = QLabel("✚")
            dot.setStyleSheet(f"color:{ACTIVE_TEXT}; font-size:18px; font-weight:900; background:transparent;")
            hl.addWidget(dot)

        # Başlık sütunu
        name_col = QVBoxLayout()
        name_col.setSpacing(1)

        name_lbl = QLabel("REPYS")
        name_lbl.setStyleSheet(
            f"color: #e2eaf4; font-size: 14px; font-weight: 800;"
            f" letter-spacing: -0.01em; background: transparent;"
        )
        ver_lbl = QLabel(f"Teknik Servis · v{AppConfig.VERSION}")
        ver_lbl.setStyleSheet(
            f"color: {GROUP_LBL}; font-size: 10px; background: transparent;"
        )
        name_col.addWidget(name_lbl)
        name_col.addWidget(ver_lbl)
        hl.addLayout(name_col)
        hl.addStretch()

        # Cyan accent dot
        accent_dot = QLabel("●")
        accent_dot.setStyleSheet(
            f"color: {ACTIVE_TEXT}; font-size: 8px; background: transparent;"
        )
        hl.addWidget(accent_dot)
        lay.addWidget(header)

        # ── Kaydırılabilir Menü ────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet(f"""
            QScrollArea {{ border: none; background: transparent; }}
            QWidget {{ background: transparent; }}
            QScrollBar:vertical {{
                background: transparent; width: 4px; margin: 0;
            }}
            QScrollBar::handle:vertical {{
                background: rgba(0,180,216,0.20);
                border-radius: 2px; min-height: 24px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: rgba(0,180,216,0.40);
            }}
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {{ height: 0; }}
        """)
        menu_w = QWidget()
        menu_w.setStyleSheet("background: transparent;")
        self._menu_layout = QVBoxLayout(menu_w)
        self._menu_layout.setContentsMargins(0, 4, 0, 8)
        self._menu_layout.setSpacing(0)
        self._load_menu()
        self._menu_layout.addStretch()
        scroll.setWidget(menu_w)
        lay.addWidget(scroll, 1)

        # ── Alt Bölüm ─────────────────────────────────────────
        bottom = QWidget()
        bottom.setStyleSheet(
            f"background: {HEADER_BG};"
            f"border-top: 1px solid rgba(0,180,216,0.12);"
        )
        bl = QVBoxLayout(bottom)
        bl.setContentsMargins(12, 10, 12, 12)
        bl.setSpacing(6)

        # Bildirim butonu
        self.notifications_btn = QPushButton("  Bildirimler")
        self.notifications_btn.setCursor(QCursor(Qt.PointingHandCursor))
        try:
            self.notifications_btn.setIcon(
                Icons.get("bell_dot", size=14, color=NOTIFY_TEXT))
            self.notifications_btn.setIconSize(QSize(14, 14))
        except Exception:
            pass
        self.notifications_btn.setStyleSheet(f"""
            QPushButton {{
                background: {NOTIFY_BG};
                color: {NOTIFY_TEXT};
                border: 1px solid {NOTIFY_BORDER};
                border-radius: 8px;
                font-size: 12px; font-weight: 600;
                padding: 7px 10px; text-align: left;
            }}
            QPushButton:hover {{
                background: {NOTIFY_HOVER};
                border-color: rgba(245,158,11,0.45);
            }}
        """)
        self.notifications_btn.clicked.connect(self.dashboard_clicked.emit)
        bl.addWidget(self.notifications_btn)

        # Senkronize Et butonu
        self.sync_btn = QPushButton("  Senkronize Et")
        self.sync_btn.setCursor(QCursor(Qt.PointingHandCursor))
        try:
            self.sync_btn.setIcon(Icons.get("sync", size=14, color=SYNC_TEXT))
            self.sync_btn.setIconSize(QSize(14, 14))
        except Exception:
            pass
        self.sync_btn.setStyleSheet(f"""
            QPushButton {{
                background: {SYNC_BG};
                color: {SYNC_TEXT};
                border: none;
                border-radius: 8px;
                font-size: 12px; font-weight: 700;
                padding: 7px 10px; text-align: left;
            }}
            QPushButton:hover {{ background: {SYNC_HOVER}; }}
            QPushButton:disabled {{
                background: rgba(0,180,216,0.15);
                color: rgba(6,13,26,0.4);
            }}
        """)
        bl.addWidget(self.sync_btn)

        # Durum satırı
        status_row = QWidget()
        status_row.setStyleSheet("background: transparent;")
        sl = QHBoxLayout(status_row)
        sl.setContentsMargins(4, 2, 0, 0)
        sl.setSpacing(6)

        self._status_dot = QLabel("●")
        self._status_dot.setStyleSheet(
            f"color: {STATUS_READY}; font-size: 8px; background: transparent;"
        )
        self._status_dot.setFixedWidth(12)

        self.status_label = QLabel("Hazır")
        self.status_label.setStyleSheet(
            f"color: {STATUS_READY}; font-size: 11px;"
            f" background: transparent; font-weight: 500;"
        )
        sl.addWidget(self._status_dot)
        sl.addWidget(self.status_label)
        sl.addStretch()
        bl.addWidget(status_row)
        lay.addWidget(bottom)

    def _load_menu(self):
        cfg_path = os.path.join(BASE_DIR, "ayarlar.json")
        try:
            with open(cfg_path, "r", encoding="utf-8-sig") as f:
                data = json.load(f)
            menu_cfg = data.get("menu_yapilandirma", {})
        except Exception:
            menu_cfg = {}

        for group_name, items in menu_cfg.items():
            section = FlatSection(group_name)
            for item in items:
                baslik   = item.get("baslik", "?")
                icon_key = item.get("icon")
                btn = section.add_item(baslik, self._on_click, icon_key=icon_key)
                self._all_buttons[baslik] = (section, btn)
            self._groups[group_name] = section
            self._menu_layout.addWidget(section)

    def _on_click(self, group: str, baslik: str):
        if self._active_baslik and self._active_baslik in self._all_buttons:
            old_sec, _ = self._all_buttons[self._active_baslik]
            old_sec.set_active(None)
        if baslik in self._all_buttons:
            sec, _ = self._all_buttons[baslik]
            sec.set_active(baslik)
        self._active_baslik = baslik
        self.menu_clicked.emit(group, baslik)

    def set_active(self, baslik: str):
        if self._active_baslik and self._active_baslik in self._all_buttons:
            old_sec, _ = self._all_buttons[self._active_baslik]
            old_sec.set_active(None)
        if baslik and baslik in self._all_buttons:
            sec, _ = self._all_buttons[baslik]
            sec.set_active(baslik)
            self._active_baslik = baslik
        else:
            self._active_baslik = None

    def set_sync_status(self, text: str, color: str = STATUS_READY):
        self.status_label.setText(text)
        self.status_label.setStyleSheet(
            f"color: {color}; font-size: 11px; background: transparent; font-weight: 500;"
        )
        self._status_dot.setStyleSheet(
            f"color: {color}; font-size: 8px; background: transparent;"
        )

    def set_sync_enabled(self, enabled: bool):
        self.sync_btn.setEnabled(enabled)
        if enabled:
            self.sync_btn.setText("  Senkronize Et")
            try:
                self.sync_btn.setIcon(Icons.get("sync", size=14, color=SYNC_TEXT))
            except Exception:
                pass
        else:
            self.sync_btn.setText("  Senkronize ediliyor...")
            try:
                self.sync_btn.setIcon(Icons.get("refresh", size=14, color="#4e6888"))
            except Exception:
                pass
