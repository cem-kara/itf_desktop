# ui/sidebar.py  ─  REPYS v3 · Medikal Dark-Blue Sidebar
import json, os
from PySide6.QtCore import Qt, QSize, Signal
from PySide6.QtGui import QCursor, QColor, QIcon
from PySide6.QtWidgets import (
    QHBoxLayout, QLabel, QPushButton, QScrollArea,
    QVBoxLayout, QWidget, QGraphicsDropShadowEffect,
)


class MenuButton(QPushButton):
    """Custom button with additional attributes for menu items."""
    def __init__(self, text: str = "", parent=None):
        super().__init__(text, parent)
        self._baslik: str = ""
        self._icon_key: str | None = None
from core.config import AppConfig
from core.paths import BASE_DIR
from ui.styles.colors import DarkTheme as T
from ui.permissions.page_permissions import PAGE_PERMISSIONS
from ui.styles.icons import MENU_ICON_MAP, Icons

# ── Renk sabitleri ──────────────────────────────────────────────
BG            = "#0a1520"
BORDER        = "rgba(255,255,255,0.07)"
HEADER_BG     = "#060d1a"
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

# ── Grup başlığı aksan renkleri (her grup farklı) ───────────────
_GROUP_ACCENT: dict[str, tuple[str, str]] = {
    "PERSONEL":            ("#22d3ee", "rgba(34,211,238,0.07)"),
    "CİHAZ":               ("#4080e0", "rgba(64,128,224,0.07)"),
    "RKE":                 ("#a855f7", "rgba(168,85,247,0.07)"),
    "YÖNETİCİ İŞLEMLERİ": ("#e8a030", "rgba(232,160,48,0.07)"),
    "AYARLAR":             ("#6a8ca8", "rgba(106,140,168,0.06)"),
}
_DEFAULT_ACCENT = ("#4080e0", "rgba(64,128,224,0.07)")


class CollapsibleSection(QWidget):
    """
    Tıklanabilir başlık ile açılıp kapanabilen menü grubu.
    Her grup kendine özgü aksan rengine sahiptir.
    """
    def __init__(self, group_name: str, collapsed: bool = False, parent=None):
        super().__init__(parent)
        self.setProperty("bg-role", "panel")
        self.group_name = group_name
        self._buttons: list[MenuButton] = []
        self._collapsed = collapsed

        accent, accent_bg = _GROUP_ACCENT.get(group_name, _DEFAULT_ACCENT)
        self._accent    = accent
        self._accent_bg = accent_bg

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # ── Grup başlık butonu (ikon sağda) ──────────────────────
        # QPushButton kullanıyoruz: metin sol hizalı, chevron ikon sağ
        # setLayoutDirection(RightToLeft) ile ikon sağa alınır
        self._header_btn = QPushButton()
        self._header_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._header_btn.setFixedHeight(30)
        self._header_btn.setCheckable(False)
        self._header_btn.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        self._header_btn.clicked.connect(self._toggle)
        lay.addWidget(self._header_btn)

        # ── İçerik alanı ───────────────────────────────────────
        self.content = QWidget()
        self.content.setProperty("bg-role", "panel")
        self._content_lay = QVBoxLayout(self.content)
        self._content_lay.setContentsMargins(8, 2, 8, 6)
        self._content_lay.setSpacing(1)
        lay.addWidget(self.content)

        self._apply_header_style()
        self.content.setVisible(not self._collapsed)

    def _apply_header_style(self):
        accent    = self._accent
        accent_bg = self._accent_bg
        icon_key  = "chevron_right" if self._collapsed else "chevron_down"

        # Chevron ikonunu QIcon olarak al ve butona ata
        try:
            self._header_btn.setIcon(Icons.get(icon_key, size=13, color=accent))
            self._header_btn.setIconSize(QSize(13, 13))
        except Exception:
            self._header_btn.setIcon(QIcon())

        # Metin: grup adı sol hizalı
        self._header_btn.setText(f"  {self.group_name}")

        # İkonu sağa taşı: LayoutDirection RightToLeft yapar ama metni bozar.
        # Bunun yerine padding trick: metin solda, ikon sağda için
        # setStyleSheet içinde QPushButton::menu-indicator değil,
        # subcontrol yok — ancak setLayoutDirection ile ikon sağa geçer
        # ve metni LEFT hizalamak için padding ayarlarız.
        self._header_btn.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

        self._header_btn.setStyleSheet(
            f"QPushButton {{"
            f"  background: {accent_bg};"
            f"  color: {accent};"
            "  border: none;"
            f"  border-left: 3px solid {accent};"
            "  border-radius: 0 6px 6px 0;"
            "  text-align: left;"
            "  padding: 0 8px 0 10px;"
            "  font-size: 12px;"
            "  font-weight: 800;"
            "  letter-spacing: 0.12em;"
            "  margin: 6px 8px 2px 0px;"
            f"}}"
            f"QPushButton:hover {{"
            f"  background: {accent}22;"
            f"  color: {accent};"
            f"}}"
        )

    def _toggle(self):
        self._collapsed = not self._collapsed
        self._apply_header_style()
        self.content.setVisible(not self._collapsed)
        p = self.parent()
        if p:
            p.adjustSize()

    def expand(self):
        if self._collapsed:
            self._toggle()

    def collapse(self):
        if not self._collapsed:
            self._toggle()

    @property
    def is_collapsed(self) -> bool:
        return self._collapsed

    def add_item(self, baslik: str, callback, icon_key: str | None = None) -> MenuButton:
        btn = MenuButton(f"  {baslik}")
        btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn.setCheckable(True)
        btn.setFixedHeight(34)
        btn._baslik = baslik

        resolved = (icon_key if (icon_key and icon_key in Icons.available())
                    else MENU_ICON_MAP.get(baslik))
        btn._icon_key = resolved
        if resolved:
            try:
                # Badge ikonu dene (emoji tarzı renkli); olmazsa klasik ikon
                badge = Icons.menu_badge(baslik, size=20)
                if badge:
                    btn.setIcon(badge)
                    btn.setIconSize(QSize(20, 20))
                else:
                    btn.setIcon(Icons.get(resolved, size=14, color=ITEM_TEXT))
                    btn.setIconSize(QSize(14, 14))
            except Exception:
                pass

        btn.setStyleSheet(self._item_css(False))
        btn.clicked.connect(lambda _=False: callback(self.group_name, baslik))
        self._content_lay.addWidget(btn)
        self._buttons.append(btn)
        return btn

    def _item_css(self, active: bool) -> str:
        if active:
            return (
                f"QPushButton {{"
                f"  background: {self._accent}18;"
                f"  color: {self._accent};"
                "  border: none;"
                f"  border-left: 2px solid {self._accent};"
                "  border-radius: 0 8px 8px 0;"
                "  text-align: left;"
                "  padding-left: 12px;"
                "  font-size: 13px;"
                "  font-weight: 600;"
                f"}}"
            )
        return (
            f"QPushButton {{"
            "  background: transparent;"
            f"  color: {ITEM_TEXT};"
            "  border: none;"
            "  border-left: 2px solid transparent;"
            "  border-radius: 0 8px 8px 0;"
            "  text-align: left;"
            "  padding-left: 12px;"
            "  font-size: 13px;"
            f"}}"
            f"QPushButton:hover {{"
            f"  background: {ITEM_HOVER_BG};"
            f"  color: {ITEM_HOVER_T};"
            f"  border-left-color: {self._accent}55;"
            f"}}"
        )

    def set_active(self, baslik: str | None):
        for btn in self._buttons:
            active = btn._baslik == baslik
            btn.setChecked(active)
            btn.setStyleSheet(self._item_css(active))
            # Badge ikonu varsa aktif/pasif'te değiştirme — rengi zaten içinde
            try:
                badge = Icons.menu_badge(btn._baslik, size=20)
                if badge:
                    btn.setIcon(badge)
                    btn.setIconSize(QSize(20, 20))
                else:
                    key = getattr(btn, "_icon_key", None) or MENU_ICON_MAP.get(btn._baslik)
                    if key:
                        color = self._accent if active else ITEM_TEXT
                        btn.setIcon(Icons.get(key, size=14, color=color))
            except Exception:
                pass

    def ensure_visible(self, baslik: str):
        """Aktif öğe bu gruptaysa grubu aç."""
        for btn in self._buttons:
            if btn._baslik == baslik:
                self.expand()
                return


# Geriye dönük uyumluluk
FlatSection = CollapsibleSection


class Sidebar(QWidget):
    menu_clicked      = Signal(str, str)
    dashboard_clicked = Signal()

    def __init__(self, parent=None, page_guard=None):
        super().__init__(parent)
        self.setFixedWidth(230)
        self.setAutoFillBackground(True)
        self.setStyleSheet("background-color: {};".format(BG))

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(24)
        shadow.setOffset(6, 0)
        shadow.setColor(QColor(0, 0, 0, 60))
        self.setGraphicsEffect(shadow)

        self._groups:        dict[str, CollapsibleSection] = {}
        self._all_buttons:   dict[str, tuple] = {}
        self._active_baslik: str | None = None
        self._page_guard = page_guard
        self._build_ui()

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # ── Logo / Header ──────────────────────────────────────
        header = QWidget()
        header.setFixedHeight(58)
        header.setStyleSheet(
            "background: {};border-bottom: 1px solid rgba(0,180,216,0.15);".format(HEADER_BG)
        )
        hl = QHBoxLayout(header)
        hl.setContentsMargins(16, 0, 14, 0)
        hl.setSpacing(10)

        try:
            logo_lbl = QLabel()
            logo_lbl.setPixmap(Icons.pixmap("hospital", size=22, color=ACTIVE_TEXT))
            logo_lbl.setFixedSize(22, 22)
            hl.addWidget(logo_lbl)
        except Exception:
            dot = QLabel("+")
            dot.setProperty("bg-role", "panel")
            hl.addWidget(dot)

        name_col = QVBoxLayout()
        name_col.setSpacing(1)
        name_lbl = QLabel("REPYS")
        name_lbl.setStyleSheet(
            "color: #e2eaf4; font-size: 14px; font-weight: 800; background: transparent;"
        )
        ver_lbl = QLabel(f"Versiyon · v{AppConfig.VERSION}")
        ver_lbl.setStyleSheet(
            f"color: {GROUP_LBL}; font-size: 11px; background: transparent;"
        )
        name_col.addWidget(name_lbl)
        name_col.addWidget(ver_lbl)
        hl.addLayout(name_col)
        hl.addStretch()

        accent_dot = QLabel("●")
        accent_dot.setStyleSheet(
            f"color: {ACTIVE_TEXT}; font-size: 8px; background: transparent;"
        )
        hl.addWidget(accent_dot)
        lay.addWidget(header)

        # ── Kaydırılabilir Menü ────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("""
            QScrollArea { border: none; background: transparent; }
            QWidget { background: transparent; }
            QScrollBar:vertical {
                background: transparent; width: 4px; padding: 0;
            }
            QScrollBar::handle:vertical {
                background: rgba(0,180,216,0.20);
                border-radius: 2px; min-height: 24px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(0,180,216,0.40);
            }
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical { height: 0; }
        """)
        menu_w = QWidget()
        menu_w.setProperty("bg-role", "panel")
        self._menu_layout = QVBoxLayout(menu_w)
        self._menu_layout.setContentsMargins(0, 6, 0, 8)
        self._menu_layout.setSpacing(2)
        self._load_menu()
        self._menu_layout.addStretch()
        scroll.setWidget(menu_w)
        lay.addWidget(scroll, 1)

        # ── Alt Bölüm ─────────────────────────────────────────
        bottom = QWidget()
        bottom.setStyleSheet(
            "background: {};border-top: 1px solid rgba(0,180,216,0.12);".format(HEADER_BG)
        )
        bl = QVBoxLayout(bottom)
        bl.setContentsMargins(12, 10, 12, 12)
        bl.setSpacing(6)

        self.notifications_btn = QPushButton("  Bildirimler")
        self.notifications_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        try:
            self.notifications_btn.setIcon(
                Icons.get("bell_dot", size=14, color=NOTIFY_TEXT))
            self.notifications_btn.setIconSize(QSize(14, 14))
        except Exception:
            pass
        self.notifications_btn.setStyleSheet("""
            QPushButton {{
                background: {};
                color: {};
                border: 1px solid {};
                border-radius: 8px;
                font-size: 12px; font-weight: 600;
                padding: 7px 10px; text-align: left;
            }}
            QPushButton:hover {{
                background: {};
                border-color: rgba(245,158,11,0.45);
            }}
        """.format(NOTIFY_BG, NOTIFY_TEXT, NOTIFY_BORDER, NOTIFY_HOVER))
        self.notifications_btn.clicked.connect(self.dashboard_clicked.emit)
        bl.addWidget(self.notifications_btn)

        self.sync_btn = QPushButton("  Senkronize Et")
        self.sync_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        try:
            self.sync_btn.setIcon(Icons.get("sync", size=14, color=SYNC_TEXT))
            self.sync_btn.setIconSize(QSize(14, 14))
        except Exception:
            pass
        self.sync_btn.setStyleSheet("""
            QPushButton {{
                background: {};
                color: {};
                border: none;
                border-radius: 8px;
                font-size: 12px; font-weight: 700;
                padding: 7px 10px; text-align: left;
            }}
            QPushButton:hover {{ background: {}; }}
            QPushButton:disabled {{
                background: rgba(0,180,216,0.15);
                color: rgba(6,13,26,0.4);
            }}
        """.format(SYNC_BG, SYNC_TEXT, SYNC_HOVER))
        bl.addWidget(self.sync_btn)

        status_row = QWidget()
        status_row.setProperty("bg-role", "panel")
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
            section = CollapsibleSection(group_name, collapsed=True)
            added_any = False
            for item in items:
                baslik = item.get("baslik", "?")
                perm_key = PAGE_PERMISSIONS.get(baslik)
                if self._page_guard and perm_key:
                    if not self._page_guard.can_open(perm_key):
                        continue
                icon_key = item.get("icon")
                btn = section.add_item(baslik, self._on_click, icon_key=icon_key)
                self._all_buttons[baslik] = (section, btn)
                added_any = True
            if added_any:
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
            # Grup kapalıysa otomatik aç
            sec.ensure_visible(baslik)
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
