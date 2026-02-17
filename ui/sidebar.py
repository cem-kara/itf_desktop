# ui/sidebar.py — Icons entegrasyon örneği
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Bu dosya, sidebar.py'ye Icons kütüphanesini nasıl
# entegre edeceğinizi gösterir.
# Değişiklikler: emoji → SVG ikon
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

import json
import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame
)
from PySide6.QtCore import Signal, Qt, QSize
from PySide6.QtGui import QCursor
from core.config import AppConfig
from ui.styles.colors import DarkTheme, Colors
# ── YENİ IMPORT ──────────────────────────────────────────────
from ui.styles.icons import Icons, IconColors, MENU_ICON_MAP, GROUP_ICON_MAP


# ── SidebarTheme (değişmedi) ──────────────────────────────────
class SidebarTheme:
    BG            = DarkTheme.BG_PRIMARY
    HEADER_BG     = "rgba(255, 255, 255, 0.05)"
    HEADER_HOVER  = "rgba(255, 255, 255, 0.10)"
    HEADER_TEXT   = DarkTheme.TEXT_PRIMARY
    ITEM_TEXT     = DarkTheme.TEXT_MUTED
    ITEM_HOVER    = "rgba(255, 255, 255, 0.07)"
    ITEM_HOVER_T  = DarkTheme.TEXT_PRIMARY
    ACTIVE_BG     = "rgba(29, 117, 254, 0.35)"
    ACTIVE_BORDER = DarkTheme.INPUT_BORDER_FOCUS
    ACTIVE_TEXT   = DarkTheme.TEXT_PRIMARY
    SEPARATOR     = DarkTheme.BORDER_PRIMARY
    TITLE         = DarkTheme.TEXT_PRIMARY
    VERSION       = DarkTheme.TEXT_DISABLED
    SYNC_BG       = DarkTheme.BTN_PRIMARY_BG
    SYNC_HOVER    = DarkTheme.BTN_PRIMARY_HOVER
    SYNC_BORDER   = DarkTheme.INPUT_BORDER_FOCUS
    SYNC_DISABLED = "rgba(255, 255, 255, 0.05)"
    SYNC_TEXT     = DarkTheme.BTN_PRIMARY_TEXT
    STATUS_READY  = DarkTheme.STATUS_SUCCESS
    STATUS_WARN   = DarkTheme.STATUS_WARNING
    STATUS_ERROR  = DarkTheme.STATUS_ERROR
    NOTIFY_BG     = "rgba(255, 193, 7, 0.15)"
    NOTIFY_HOVER  = "rgba(255, 193, 7, 0.25)"
    NOTIFY_TEXT   = Colors.YELLOW_400
    NOTIFY_BORDER = "rgba(255, 193, 7, 0.4)"


# ── AccordionGroup ─────────────────────────────────────────────
class AccordionGroup(QWidget):

    def __init__(self, group_name: str, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background-color: transparent;")
        self.group_name = group_name
        self._expanded  = False
        self._buttons   = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── Grup başlık butonu (SVG ikon) ──────────────────────
        self.header = QPushButton(f"  {group_name}")
        self.header.setFixedHeight(36)
        self.header.setCursor(QCursor(Qt.PointingHandCursor))
        self.header.setStyleSheet(f"""
            QPushButton {{
                background-color: {SidebarTheme.HEADER_BG};
                color: {SidebarTheme.HEADER_TEXT};
                border: none;
                border-bottom: 1px solid {SidebarTheme.SEPARATOR};
                text-align: left;
                padding-left: 12px;
                font-size: 12px;
                font-weight: bold;
                letter-spacing: 0.5px;
            }}
            QPushButton:hover {{
                background-color: {SidebarTheme.HEADER_HOVER};
            }}
        """)

        # Grup ikonunu SVG'den al
        icon_key = GROUP_ICON_MAP.get(group_name)
        if icon_key:
            self.header.setIcon(Icons.get(icon_key, size=20, color=IconColors.GROUP_HEADER))
            self.header.setIconSize(QSize(15, 15))

        self.header.clicked.connect(self._toggle)
        layout.addWidget(self.header)

        # Chevron ikonu (açma/kapama göstergesi) ──────────────
        self._chevron_closed = Icons.get("chevron_right", size=15, color=IconColors.MUTED)
        self._chevron_open   = Icons.get("chevron_down",  size=15, color=IconColors.GROUP_HEADER)

        self.content = QWidget()
        self.content.setStyleSheet("background-color: transparent;")
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(0, 4, 0, 4)
        self.content_layout.setSpacing(2)
        layout.addWidget(self.content)
        self.content.setVisible(False)

    def add_item(self, baslik: str, callback) -> QPushButton:
        btn = QPushButton(f"   {baslik}")
        btn.setCursor(QCursor(Qt.PointingHandCursor))
        btn.setCheckable(True)
        btn._baslik = baslik
        btn.setStyleSheet(self._item_css(False))

        # Menü ikonunu SVG'den al
        icon_key = MENU_ICON_MAP.get(baslik)
        if icon_key:
            btn.setIcon(Icons.get(icon_key, size=14, color=IconColors.MENU_ITEM))
            btn.setIconSize(QSize(14, 14))

        btn.clicked.connect(lambda: callback(self.group_name, baslik))
        self.content_layout.addWidget(btn)
        self._buttons.append(btn)
        return btn

    def _toggle(self):
        self._expanded = not self._expanded
        self.content.setVisible(self._expanded)
        # Chevron yönünü güncelle
        self.header.setIcon(
            self._chevron_open if self._expanded else self._chevron_closed
        )

    def _item_css(self, active: bool) -> str:
        if active:
            return f"""
                QPushButton {{
                    background-color: {SidebarTheme.ACTIVE_BG};
                    color: {SidebarTheme.ACTIVE_TEXT};
                    border: none;
                    border-left: 3px solid {SidebarTheme.ACTIVE_BORDER};
                    border-radius: 0px 6px 6px 0px;
                    text-align: left;
                    padding-left: 14px; margin: 0 8px 0 0;
                    font-size: 13px; font-weight: 600;
                }}
            """
        return f"""
            QPushButton {{
                background-color: transparent;
                color: {SidebarTheme.ITEM_TEXT};
                border: none;
                border-left: 3px solid transparent;
                border-radius: 0px 6px 6px 0px;
                text-align: left;
                padding-left: 14px; margin: 0 8px 0 0;
                font-size: 13px;
            }}
            QPushButton:hover {{
                background-color: {SidebarTheme.ITEM_HOVER};
                color: {SidebarTheme.ITEM_HOVER_T};
                border-left: 3px solid {SidebarTheme.SYNC_BORDER};
            }}
        """

    def set_active(self, baslik: str | None):
        for btn in self._buttons:
            is_active = (btn._baslik == baslik)
            btn.setChecked(is_active)
            btn.setStyleSheet(self._item_css(is_active))

            # Aktif iken ikon rengini parlat
            icon_key = MENU_ICON_MAP.get(btn._baslik)
            if icon_key:
                color = IconColors.MENU_ACTIVE if is_active else IconColors.MENU_ITEM
                btn.setIcon(Icons.get(icon_key, size=14, color=color))


# ── Sidebar ────────────────────────────────────────────────────
class Sidebar(QWidget):

    menu_clicked      = Signal(str, str)
    dashboard_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(240)
        self.setAutoFillBackground(True)
        self.setStyleSheet(f"background-color: {SidebarTheme.BG};")

        self._groups       = {}
        self._all_buttons  = {}
        self._active_baslik = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── Başlık ────────────────────────────────────────────
        hdr = QWidget()
        hdr.setStyleSheet("background-color: transparent;")
        hl = QVBoxLayout(hdr)
        hl.setContentsMargins(16, 16, 16, 6)
        hl.setSpacing(2)

        t = QLabel(f"  {AppConfig.APP_NAME}")
        t.setWordWrap(True)
        t.setStyleSheet(f"""
            color: {SidebarTheme.TITLE}; font-size: 15px; font-weight: bold;
            background: transparent;
        """)
        # Logo ikonu
        from PySide6.QtWidgets import QHBoxLayout
        title_row = QWidget()
        title_row.setStyleSheet("background: transparent;")
        tr = QHBoxLayout(title_row)
        tr.setContentsMargins(0, 0, 0, 0)
        tr.setSpacing(8)
        logo_lbl = QLabel()
        logo_lbl.setPixmap(Icons.pixmap("hospital", size=22, color=SidebarTheme.SYNC_TEXT))
        logo_lbl.setFixedSize(22, 22)
        tr.addWidget(logo_lbl)
        tr.addWidget(t)
        tr.addStretch()
        hl.addWidget(title_row)

        v = QLabel(f"v{AppConfig.VERSION}")
        v.setStyleSheet(f"color: {SidebarTheme.VERSION}; font-size: 11px; background: transparent;")
        hl.addWidget(v)
        layout.addWidget(hdr)

        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background-color: {SidebarTheme.SEPARATOR};")
        layout.addWidget(sep)

        # ── Scroll menü ───────────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet(f"""
            QScrollArea {{ border: none; background-color: transparent; }}
            QWidget {{ background-color: transparent; }}
            QScrollBar:vertical {{
                background-color: transparent; width: 4px;
            }}
            QScrollBar::handle:vertical {{
                background-color: {SidebarTheme.SEPARATOR}; border-radius: 2px; min-height: 30px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
        """)

        menu_w = QWidget()
        menu_w.setStyleSheet("background-color: transparent;")
        self._ml = QVBoxLayout(menu_w)
        self._ml.setContentsMargins(0, 6, 0, 6)
        self._ml.setSpacing(0)

        self._load_menu()
        self._ml.addStretch()
        scroll.setWidget(menu_w)
        layout.addWidget(scroll, 1)

        # ── Alt kısım ─────────────────────────────────────────
        bot = QWidget()
        bot.setStyleSheet("background-color: transparent;")
        bl = QVBoxLayout(bot)
        bl.setContentsMargins(12, 4, 12, 10)
        bl.setSpacing(6)

        # Bildirimler butonu — bell ikonu
        self.notifications_btn = QPushButton("Bildirimler")
        self.notifications_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self.notifications_btn.setIcon(
            Icons.get("bell_dot", size=16, color=IconColors.NOTIFICATION)
        )
        self.notifications_btn.setIconSize(QSize(16, 16))
        self.notifications_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {SidebarTheme.NOTIFY_BG};
                color: {SidebarTheme.NOTIFY_TEXT};
                border: 1px solid {SidebarTheme.NOTIFY_BORDER};
                border-radius: 8px;
                font-size: 13px; font-weight: 600;
                padding: 6px 12px;
                text-align: left;
            }}
            QPushButton:hover {{
                background-color: {SidebarTheme.NOTIFY_HOVER};
                color: {SidebarTheme.NOTIFY_TEXT};
            }}
        """)
        self.notifications_btn.clicked.connect(self.dashboard_clicked.emit)
        bl.addWidget(self.notifications_btn)

        # Sync butonu — sync ikonu
        self.sync_btn = QPushButton("Senkronize Et")
        self.sync_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self.sync_btn.setIcon(Icons.get("sync", size=15, color=IconColors.SYNC))
        self.sync_btn.setIconSize(QSize(15, 15))
        self.sync_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {SidebarTheme.SYNC_BG};
                color: {SidebarTheme.SYNC_TEXT};
                border: 1px solid {SidebarTheme.SYNC_BORDER};
                border-radius: 8px;
                font-size: 13px; font-weight: 600;
                padding: 6px 12px;
                text-align: left;
            }}
            QPushButton:hover {{
                background-color: {SidebarTheme.SYNC_HOVER};
                color: #ffffff;
            }}
            QPushButton:disabled {{
                background-color: {SidebarTheme.SYNC_DISABLED};
                color: {SidebarTheme.VERSION};
                border: 1px solid {SidebarTheme.SEPARATOR};
            }}
        """)
        bl.addWidget(self.sync_btn)

        # Durum etiketi — check_circle ikonu
        status_row = QWidget()
        status_row.setStyleSheet("background: transparent;")
        from PySide6.QtWidgets import QHBoxLayout
        sr = QHBoxLayout(status_row)
        sr.setContentsMargins(4, 0, 0, 0)
        sr.setSpacing(6)
        self._status_icon_lbl = QLabel()
        self._status_icon_lbl.setPixmap(Icons.pixmap("check_circle", size=12, color=SidebarTheme.STATUS_READY))
        self._status_icon_lbl.setFixedSize(12, 12)
        self.status_label = QLabel("Hazır")
        self.status_label.setStyleSheet(f"color: {SidebarTheme.STATUS_READY}; font-size: 11px; background: transparent;")
        sr.addWidget(self._status_icon_lbl)
        sr.addWidget(self.status_label)
        sr.addStretch()
        bl.addWidget(status_row)

        layout.addWidget(bot)

    def _load_menu(self):
        cfg_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "ayarlar.json"
        )
        try:
            with open(cfg_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            menu_cfg = data.get("menu_yapilandirma", {})
        except Exception as e:
            from core.logger import logger
            logger.error(f"ayarlar.json yüklenemedi: {e}")
            menu_cfg = {}

        for gname, items in menu_cfg.items():
            grp = AccordionGroup(gname)       # emoji yok artık
            for item in items:
                baslik = item.get("baslik", "?")
                btn = grp.add_item(baslik, self._on_click)
                self._all_buttons[baslik] = (grp, btn)
            self._groups[gname] = grp
            self._ml.addWidget(grp)

    def _on_click(self, group: str, baslik: str):
        if self._active_baslik and self._active_baslik in self._all_buttons:
            old_grp, _ = self._all_buttons[self._active_baslik]
            old_grp.set_active(None)
        if baslik in self._all_buttons:
            grp, _ = self._all_buttons[baslik]
            grp.set_active(baslik)
        self._active_baslik = baslik
        self.menu_clicked.emit(group, baslik)

    def set_active(self, baslik: str):
        if self._active_baslik and self._active_baslik in self._all_buttons:
            old_grp, _ = self._all_buttons[self._active_baslik]
            old_grp.set_active(None)
        if baslik and baslik in self._all_buttons:
            grp, _ = self._all_buttons[baslik]
            grp.set_active(baslik)
            self._active_baslik = baslik
        else:
            self._active_baslik = None

    def set_sync_status(self, text: str, color: str = SidebarTheme.STATUS_READY):
        self.status_label.setText(text)
        self.status_label.setStyleSheet(
            f"color: {color}; font-size: 11px; background: transparent;"
        )
        # İkonu da renge göre güncelle
        icon_name = "check_circle" if color == SidebarTheme.STATUS_READY else \
                    "alert_triangle" if color == SidebarTheme.STATUS_ERROR else "info"
        self._status_icon_lbl.setPixmap(Icons.pixmap(icon_name, size=12, color=color))

    def set_sync_enabled(self, enabled: bool):
        self.sync_btn.setEnabled(enabled)
        if enabled:
            self.sync_btn.setText("  Yenile / Senkronize Et")
            self.sync_btn.setIcon(Icons.get("sync", size=15, color=IconColors.SYNC))
        else:
            self.sync_btn.setText("  Senkronize ediliyor...")
            self.sync_btn.setIcon(Icons.get("refresh", size=15, color=IconColors.MUTED))
        self.sync_btn.setIconSize(QSize(15, 15))
