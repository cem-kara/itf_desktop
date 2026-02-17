import json
import os

from PySide6.QtCore import Qt, QSize, Signal
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from core.config import AppConfig
from core.paths import BASE_DIR
from ui.styles.colors import Colors, DarkTheme
from ui.styles.icons import GROUP_ICON_MAP, MENU_ICON_MAP, IconColors, Icons


class SidebarTheme:
    BG = DarkTheme.BG_PRIMARY
    HEADER_BG = "rgba(255, 255, 255, 0.05)"
    HEADER_HOVER = "rgba(255, 255, 255, 0.10)"
    HEADER_TEXT = DarkTheme.TEXT_PRIMARY
    ITEM_TEXT = DarkTheme.TEXT_MUTED
    ITEM_HOVER = "rgba(255, 255, 255, 0.07)"
    ITEM_HOVER_T = DarkTheme.TEXT_PRIMARY
    ACTIVE_BG = "rgba(29, 117, 254, 0.35)"
    ACTIVE_BORDER = DarkTheme.INPUT_BORDER_FOCUS
    ACTIVE_TEXT = DarkTheme.TEXT_PRIMARY
    SEPARATOR = DarkTheme.BORDER_PRIMARY
    TITLE = DarkTheme.TEXT_PRIMARY
    VERSION = DarkTheme.TEXT_DISABLED
    SYNC_BG = DarkTheme.BTN_PRIMARY_BG
    SYNC_HOVER = DarkTheme.BTN_PRIMARY_HOVER
    SYNC_BORDER = DarkTheme.INPUT_BORDER_FOCUS
    SYNC_DISABLED = "rgba(255, 255, 255, 0.05)"
    SYNC_TEXT = DarkTheme.BTN_PRIMARY_TEXT
    STATUS_READY = DarkTheme.STATUS_SUCCESS
    STATUS_WARN = DarkTheme.STATUS_WARNING
    STATUS_ERROR = DarkTheme.STATUS_ERROR
    NOTIFY_BG = "rgba(255, 193, 7, 0.15)"
    NOTIFY_HOVER = "rgba(255, 193, 7, 0.25)"
    NOTIFY_TEXT = Colors.YELLOW_400
    NOTIFY_BORDER = "rgba(255, 193, 7, 0.4)"


class AccordionGroup(QWidget):
    def __init__(self, group_name: str, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background-color: transparent;")
        self.group_name = group_name
        self._expanded = False
        self._buttons = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.header = QPushButton(f"  {group_name}")
        self.header.setFixedHeight(36)
        self.header.setCursor(QCursor(Qt.PointingHandCursor))
        self.header.setStyleSheet(
            f"""
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
            """
        )

        self._chevron_closed = Icons.get("chevron_right", size=15, color=IconColors.MUTED)
        self._chevron_open = Icons.get("chevron_down", size=15, color=IconColors.GROUP_HEADER)
        self.header.setIcon(self._chevron_closed)
        self.header.setIconSize(QSize(15, 15))

        group_icon_key = GROUP_ICON_MAP.get(group_name)
        if group_icon_key:
            self.header.setIcon(Icons.get(group_icon_key, size=16, color=IconColors.GROUP_HEADER))
            self.header.setIconSize(QSize(16, 16))

        self.header.clicked.connect(self._toggle)
        layout.addWidget(self.header)

        self.content = QWidget()
        self.content.setStyleSheet("background-color: transparent;")
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(0, 4, 0, 4)
        self.content_layout.setSpacing(2)
        self.content.setVisible(False)
        layout.addWidget(self.content)

    def add_item(self, baslik: str, callback) -> QPushButton:
        btn = QPushButton(f"   {baslik}")
        btn.setCursor(QCursor(Qt.PointingHandCursor))
        btn.setCheckable(True)
        btn._baslik = baslik
        btn.setStyleSheet(self._item_css(False))

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
        if self._expanded:
            self.header.setIcon(self._chevron_open)
        else:
            self.header.setIcon(self._chevron_closed)
        self.header.setIconSize(QSize(15, 15))

    def _item_css(self, active: bool) -> str:
        if active:
            return (
                f"""
                QPushButton {{
                    background-color: {SidebarTheme.ACTIVE_BG};
                    color: {SidebarTheme.ACTIVE_TEXT};
                    border: none;
                    border-left: 3px solid {SidebarTheme.ACTIVE_BORDER};
                    border-radius: 0px 6px 6px 0px;
                    text-align: left;
                    padding-left: 14px;
                    margin: 0 8px 0 0;
                    font-size: 13px;
                    font-weight: 600;
                }}
                """
            )

        return (
            f"""
            QPushButton {{
                background-color: transparent;
                color: {SidebarTheme.ITEM_TEXT};
                border: none;
                border-left: 3px solid transparent;
                border-radius: 0px 6px 6px 0px;
                text-align: left;
                padding-left: 14px;
                margin: 0 8px 0 0;
                font-size: 13px;
            }}
            QPushButton:hover {{
                background-color: {SidebarTheme.ITEM_HOVER};
                color: {SidebarTheme.ITEM_HOVER_T};
                border-left: 3px solid {SidebarTheme.SYNC_BORDER};
            }}
            """
        )

    def set_active(self, baslik: str | None):
        for btn in self._buttons:
            is_active = btn._baslik == baslik
            btn.setChecked(is_active)
            btn.setStyleSheet(self._item_css(is_active))

            icon_key = MENU_ICON_MAP.get(btn._baslik)
            if icon_key:
                color = IconColors.MENU_ACTIVE if is_active else IconColors.MENU_ITEM
                btn.setIcon(Icons.get(icon_key, size=14, color=color))


class Sidebar(QWidget):
    menu_clicked = Signal(str, str)
    dashboard_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(240)
        self.setAutoFillBackground(True)
        self.setStyleSheet(f"background-color: {SidebarTheme.BG};")

        self._groups = {}
        self._all_buttons = {}
        self._active_baslik = None

        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QWidget()
        header.setStyleSheet("background-color: transparent;")
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(16, 16, 16, 6)
        header_layout.setSpacing(2)

        title_row = QWidget()
        title_row.setStyleSheet("background: transparent;")
        title_layout = QHBoxLayout(title_row)
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(8)

        logo_lbl = QLabel()
        logo_lbl.setPixmap(Icons.pixmap("hospital", size=22, color=SidebarTheme.SYNC_TEXT))
        logo_lbl.setFixedSize(22, 22)
        title_layout.addWidget(logo_lbl)

        title_lbl = QLabel(AppConfig.APP_NAME)
        title_lbl.setWordWrap(True)
        title_lbl.setStyleSheet(
            f"color: {SidebarTheme.TITLE}; font-size: 15px; font-weight: bold; background: transparent;"
        )
        title_layout.addWidget(title_lbl)
        title_layout.addStretch()

        header_layout.addWidget(title_row)

        ver_lbl = QLabel(f"v{AppConfig.VERSION}")
        ver_lbl.setStyleSheet(
            f"color: {SidebarTheme.VERSION}; font-size: 11px; background: transparent;"
        )
        header_layout.addWidget(ver_lbl)

        layout.addWidget(header)

        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background-color: {SidebarTheme.SEPARATOR};")
        layout.addWidget(sep)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet(
            f"""
            QScrollArea {{ border: none; background-color: transparent; }}
            QWidget {{ background-color: transparent; }}
            QScrollBar:vertical {{ background-color: transparent; width: 4px; }}
            QScrollBar::handle:vertical {{
                background-color: {SidebarTheme.SEPARATOR};
                border-radius: 2px;
                min-height: 30px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
            """
        )

        menu_widget = QWidget()
        menu_widget.setStyleSheet("background-color: transparent;")
        self._menu_layout = QVBoxLayout(menu_widget)
        self._menu_layout.setContentsMargins(0, 6, 0, 6)
        self._menu_layout.setSpacing(0)

        self._load_menu()
        self._menu_layout.addStretch()

        scroll.setWidget(menu_widget)
        layout.addWidget(scroll, 1)

        bottom = QWidget()
        bottom.setStyleSheet("background-color: transparent;")
        bottom_layout = QVBoxLayout(bottom)
        bottom_layout.setContentsMargins(12, 4, 12, 10)
        bottom_layout.setSpacing(6)

        self.notifications_btn = QPushButton("Bildirimler")
        self.notifications_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self.notifications_btn.setIcon(Icons.get("bell_dot", size=16, color=IconColors.NOTIFICATION))
        self.notifications_btn.setIconSize(QSize(16, 16))
        self.notifications_btn.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {SidebarTheme.NOTIFY_BG};
                color: {SidebarTheme.NOTIFY_TEXT};
                border: 1px solid {SidebarTheme.NOTIFY_BORDER};
                border-radius: 8px;
                font-size: 13px;
                font-weight: 600;
                padding: 6px 12px;
                text-align: left;
            }}
            QPushButton:hover {{
                background-color: {SidebarTheme.NOTIFY_HOVER};
                color: {SidebarTheme.NOTIFY_TEXT};
            }}
            """
        )
        self.notifications_btn.clicked.connect(self.dashboard_clicked.emit)
        bottom_layout.addWidget(self.notifications_btn)

        self.sync_btn = QPushButton("Senkronize Et")
        self.sync_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self.sync_btn.setIcon(Icons.get("sync", size=15, color=IconColors.SYNC))
        self.sync_btn.setIconSize(QSize(15, 15))
        self.sync_btn.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {SidebarTheme.SYNC_BG};
                color: {SidebarTheme.SYNC_TEXT};
                border: 1px solid {SidebarTheme.SYNC_BORDER};
                border-radius: 8px;
                font-size: 13px;
                font-weight: 600;
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
            """
        )
        bottom_layout.addWidget(self.sync_btn)

        status_row = QWidget()
        status_row.setStyleSheet("background: transparent;")
        status_layout = QHBoxLayout(status_row)
        status_layout.setContentsMargins(4, 0, 0, 0)
        status_layout.setSpacing(6)

        self._status_icon_lbl = QLabel()
        self._status_icon_lbl.setPixmap(Icons.pixmap("check_circle", size=12, color=SidebarTheme.STATUS_READY))
        self._status_icon_lbl.setFixedSize(12, 12)

        self.status_label = QLabel("Hazir")
        self.status_label.setStyleSheet(
            f"color: {SidebarTheme.STATUS_READY}; font-size: 11px; background: transparent;"
        )

        status_layout.addWidget(self._status_icon_lbl)
        status_layout.addWidget(self.status_label)
        status_layout.addStretch()

        bottom_layout.addWidget(status_row)
        layout.addWidget(bottom)

    def _load_menu(self):
        cfg_path = os.path.join(BASE_DIR, "ayarlar.json")
        try:
            with open(cfg_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            menu_cfg = data.get("menu_yapilandirma", {})
        except Exception:
            menu_cfg = {}

        for group_name, items in menu_cfg.items():
            group = AccordionGroup(group_name)
            for item in items:
                baslik = item.get("baslik", "?")
                btn = group.add_item(baslik, self._on_click)
                self._all_buttons[baslik] = (group, btn)
            self._groups[group_name] = group
            self._menu_layout.addWidget(group)

    def _on_click(self, group: str, baslik: str):
        if self._active_baslik and self._active_baslik in self._all_buttons:
            old_group, _ = self._all_buttons[self._active_baslik]
            old_group.set_active(None)

        if baslik in self._all_buttons:
            grp, _ = self._all_buttons[baslik]
            grp.set_active(baslik)

        self._active_baslik = baslik
        self.menu_clicked.emit(group, baslik)

    def set_active(self, baslik: str):
        if self._active_baslik and self._active_baslik in self._all_buttons:
            old_group, _ = self._all_buttons[self._active_baslik]
            old_group.set_active(None)

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

        if color == SidebarTheme.STATUS_READY:
            icon_name = "check_circle"
        elif color == SidebarTheme.STATUS_ERROR:
            icon_name = "alert_triangle"
        else:
            icon_name = "info"

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
