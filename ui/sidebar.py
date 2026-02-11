import json
import os

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from core.config import AppConfig
from ui.theme_manager import ThemeManager

MENU_ICONS = {
    "Personel Listesi": "👥",
    "Personel Ekle": "➕",
    "İzin Takip": "📅",
    "FHSZ Yönetim": "📊",
    "Puantaj Rapor": "📋",
    "Personel Verileri": "📈",
    "Cihaz Listesi": "🔬",
    "Cihaz Ekle": "🆕",
    "Arıza Kayıt": "⚠️",
    "Arıza Listesi": "🔧",
    "Periyodik Bakım": "🛠️",
    "Kalibrasyon Takip": "📐",
    "RKE Listesi": "🛡️",
    "Muayene Girişi": "🔍",
    "RKE Raporlama": "📋",
    "Yıl Sonu İzin": "📆",
    "Ayarlar": "⚙️",
}

GROUP_ICONS = {
    "PERSONEL": "👤",
    "CİHAZ": "🔬",
    "RKE": "🛡️",
    "YÖNETİCİ İŞLEMLERİ": "⚙️",
}


class AccordionGroup(QWidget):
    def __init__(self, group_name, icon, parent=None):
        super().__init__(parent)
        self.group_name = group_name
        self._expanded = False
        self._buttons = []
        self._icon = icon

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.header = QPushButton(f"  {icon}  {group_name}  [+]")
        self.header.setObjectName("sidebar_group_header")
        self.header.setFixedHeight(38)
        self.header.setCursor(QCursor(Qt.PointingHandCursor))
        self.header.clicked.connect(self._toggle)
        layout.addWidget(self.header)

        self.content = QWidget()
        self.content.setObjectName("sidebar_group_content")
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(0, 4, 0, 4)
        self.content_layout.setSpacing(2)
        layout.addWidget(self.content)
        self.content.setVisible(False)

    def add_item(self, baslik, callback):
        icon = MENU_ICONS.get(baslik, "•")

        btn = QPushButton(f"  {icon}   {baslik}")
        btn.setObjectName("sidebar_menu_item")
        btn.setFixedHeight(34)
        btn.setCursor(QCursor(Qt.PointingHandCursor))
        btn.setCheckable(True)
        btn._baslik = baslik
        btn.clicked.connect(lambda: callback(self.group_name, baslik))
        ThemeManager.set_variant(btn, "default")
        self.content_layout.addWidget(btn)
        self._buttons.append(btn)
        return btn

    def _toggle(self):
        self._expanded = not self._expanded
        self.content.setVisible(self._expanded)
        arrow = "[-]" if self._expanded else "[+]"
        self.header.setText(f"  {self._icon}  {self.group_name}  {arrow}")

    def set_active(self, baslik):
        for btn in self._buttons:
            is_active = btn._baslik == baslik
            btn.setChecked(is_active)
            ThemeManager.set_variant(btn, "active" if is_active else "default")


class Sidebar(QWidget):
    menu_clicked = Signal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setFixedWidth(240)
        self.setAutoFillBackground(True)

        self._groups = {}
        self._all_buttons = {}
        self._active_baslik = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        hdr = QWidget()
        hl = QVBoxLayout(hdr)
        hl.setContentsMargins(16, 16, 16, 6)
        hl.setSpacing(2)

        t = QLabel(f"🏥  {AppConfig.APP_NAME}")
        t.setObjectName("sidebar_title")
        hl.addWidget(t)

        v = QLabel(f"v{AppConfig.VERSION}")
        v.setObjectName("sidebar_version")
        hl.addWidget(v)
        layout.addWidget(hdr)

        sep = QFrame()
        sep.setObjectName("sidebar_separator")
        sep.setFixedHeight(1)
        layout.addWidget(sep)

        scroll = QScrollArea()
        scroll.setObjectName("sidebar_scroll")
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        menu_w = QWidget()
        self._ml = QVBoxLayout(menu_w)
        self._ml.setContentsMargins(0, 6, 0, 6)
        self._ml.setSpacing(0)

        self._load_menu()
        self._ml.addStretch()

        scroll.setWidget(menu_w)
        layout.addWidget(scroll, 1)

        bot = QWidget()
        bl = QVBoxLayout(bot)
        bl.setContentsMargins(12, 4, 12, 10)
        bl.setSpacing(6)

        self.sync_btn = QPushButton("⟳  Senkronize Et")
        self.sync_btn.setObjectName("sidebar_sync_btn")
        self.sync_btn.setFixedHeight(36)
        self.sync_btn.setCursor(QCursor(Qt.PointingHandCursor))
        bl.addWidget(self.sync_btn)

        self.status_label = QLabel("● Hazır")
        self.status_label.setObjectName("sidebar_status_label")
        self.status_label.setAlignment(Qt.AlignCenter)
        ThemeManager.set_variant(self.status_label, "ok")
        bl.addWidget(self.status_label)
        layout.addWidget(bot)

    def _load_menu(self):
        cfg_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "ayarlar.json",
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
            icon = GROUP_ICONS.get(gname, "📁")
            grp = AccordionGroup(gname, icon)

            for item in items:
                baslik = item.get("baslik", "?")
                btn = grp.add_item(baslik, self._on_click)
                self._all_buttons[baslik] = (grp, btn)

            self._groups[gname] = grp
            self._ml.addWidget(grp)

    def _on_click(self, group, baslik):
        if self._active_baslik and self._active_baslik in self._all_buttons:
            old_grp, _ = self._all_buttons[self._active_baslik]
            old_grp.set_active(None)
        if baslik in self._all_buttons:
            grp, _ = self._all_buttons[baslik]
            grp.set_active(baslik)
        self._active_baslik = baslik
        self.menu_clicked.emit(group, baslik)

    def set_active(self, baslik):
        self._on_click("", baslik)

    def set_sync_status(self, text, color="#22c55e"):
        self.status_label.setText(text)
        variant = "ok"
        if color == "#f59e0b":
            variant = "warn"
        elif color == "#ef4444":
            variant = "error"
        ThemeManager.set_variant(self.status_label, variant)

    def set_sync_enabled(self, enabled):
        self.sync_btn.setEnabled(enabled)
        self.sync_btn.setText("⟳  Senkronize Et" if enabled else "⏳ Senkronize ediliyor...")
