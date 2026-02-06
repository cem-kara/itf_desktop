import json
import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame
)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QCursor
from core.config import AppConfig

MENU_ICONS = {
    "Personel Listesi":  "👥",
    "Personel Ekle":     "➕",
    "İzin Takip":        "📅",
    "FHSZ Yönetim":     "📊",
    "Personel Verileri": "📈",
    "Cihaz Listesi":     "🔬",
    "Cihaz Ekle":        "🆕",
    "Ariza Kaydi":       "⚠️",
    "Ariza Listesi":     "🔧",
    "Periyodik Bakim":   "🛠️",
    "Kalibrasyon Takip": "📐",
    "RKE Listesi":       "🛡️",
    "Muayene Girişi":    "🔍",
    "RKE Raporlama":     "📋",
    "Yıl Sonu İzin":    "📆",
    "Ayarlar":           "⚙️",
}

GROUP_ICONS = {
    "PERSONEL":            "👤",
    "CİHAZ":              "🔬",
    "RKE":                "🛡️",
    "YÖNETİCİ İŞLEMLERİ": "⚙️",
}

# ─── W11 Dark Glass Renkler ───
C = {
    "bg":           "#1a1a2e",
    "bg_glass":     "rgba(30, 32, 44, 0.85)",
    "header_bg":    "rgba(255, 255, 255, 0.05)",
    "header_hover": "rgba(255, 255, 255, 0.10)",
    "header_text":  "#c8cad0",
    "item_text":    "#8b8fa3",
    "item_hover":   "rgba(255, 255, 255, 0.07)",
    "item_hover_t": "#e0e2ea",
    "active_bg":    "rgba(29, 117, 254, 0.35)",
    "active_border":"#1d75fe",
    "active_text":  "#ffffff",
    "sep":          "rgba(255, 255, 255, 0.06)",
    "title":        "#e8eaef",
    "ver":          "#5a5d6e",
    "accent":       "#1d75fe",
    "accent_light": "#6bd3ff",
    "sync_bg":      "rgba(29, 117, 254, 0.25)",
    "sync_hover":   "rgba(29, 117, 254, 0.40)",
    "sync_border":  "#1d75fe",
    "sync_dis":     "rgba(255, 255, 255, 0.05)",
}


class AccordionGroup(QWidget):

    def __init__(self, group_name, icon, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background-color: transparent;")
        self.group_name = group_name
        self._expanded = False
        self._buttons = []
        self._icon = icon

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.header = QPushButton(f"  {icon}  {group_name}  ➕")
        self.header.setFixedHeight(38)
        self.header.setCursor(QCursor(Qt.PointingHandCursor))
        self.header.setStyleSheet(f"""
            QPushButton {{
                background-color: {C['header_bg']};
                color: {C['header_text']};
                border: none;
                border-bottom: 1px solid {C['sep']};
                text-align: left;
                padding-left: 12px;
                font-size: 12px;
                font-weight: bold;
                letter-spacing: 0.5px;
            }}
            QPushButton:hover {{
                background-color: {C['header_hover']};
            }}
        """)
        self.header.clicked.connect(self._toggle)
        layout.addWidget(self.header)

        self.content = QWidget()
        self.content.setStyleSheet("background-color: transparent;")
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(0, 4, 0, 4)
        self.content_layout.setSpacing(2)
        layout.addWidget(self.content)
        self.content.setVisible(False)

    def add_item(self, baslik, callback):
        icon = MENU_ICONS.get(baslik, "•")
        btn = QPushButton(f"  {icon}   {baslik}")
        btn.setFixedHeight(34)
        btn.setCursor(QCursor(Qt.PointingHandCursor))
        btn.setCheckable(True)
        btn._baslik = baslik
        btn.setStyleSheet(self._item_css(False))
        btn.clicked.connect(lambda: callback(self.group_name, baslik))
        self.content_layout.addWidget(btn)
        self._buttons.append(btn)
        return btn

    def _toggle(self):
        self._expanded = not self._expanded
        self.content.setVisible(self._expanded)
        arrow = "➖" if self._expanded else "➕"
        self.header.setText(f"  {self._icon}  {self.group_name}  {arrow}")

    def _item_css(self, active):
        if active:
            return f"""
                QPushButton {{
                    background-color: {C['active_bg']};
                    color: {C['active_text']};
                    border: none;
                    border-left: 3px solid {C['active_border']};
                    border-radius: 0px 6px 6px 0px;
                    text-align: left;
                    padding-left: 14px; margin: 0 8px 0 0;
                    font-size: 13px; font-weight: 600;
                }}
            """
        return f"""
            QPushButton {{
                background-color: transparent;
                color: {C['item_text']};
                border: none;
                border-left: 3px solid transparent;
                border-radius: 0px 6px 6px 0px;
                text-align: left;
                padding-left: 14px; margin: 0 8px 0 0;
                font-size: 13px;
            }}
            QPushButton:hover {{
                background-color: {C['item_hover']};
                color: {C['item_hover_t']};
                border-left: 3px solid rgba(29, 117, 254, 0.4);
            }}
        """

    def set_active(self, baslik):
        for btn in self._buttons:
            is_active = (btn._baslik == baslik)
            btn.setChecked(is_active)
            btn.setStyleSheet(self._item_css(is_active))


class Sidebar(QWidget):

    menu_clicked = Signal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(240)
        self.setAutoFillBackground(True)
        self.setStyleSheet(f"background-color: {C['bg']};")

        self._groups = {}
        self._all_buttons = {}
        self._active_baslik = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Başlık
        hdr = QWidget()
        hdr.setStyleSheet(f"background-color: transparent;")
        hl = QVBoxLayout(hdr)
        hl.setContentsMargins(16, 16, 16, 6)
        hl.setSpacing(2)

        t = QLabel(f"🏥  {AppConfig.APP_NAME}")
        t.setStyleSheet(f"""
            color: {C['title']}; font-size: 15px; font-weight: bold;
            background: transparent;
        """)
        hl.addWidget(t)

        v = QLabel(f"v{AppConfig.VERSION}")
        v.setStyleSheet(f"color: {C['ver']}; font-size: 11px; background: transparent;")
        hl.addWidget(v)
        layout.addWidget(hdr)

        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background-color: {C['sep']};")
        layout.addWidget(sep)

        # Scroll menü
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
                background-color: rgba(255,255,255,0.15); border-radius: 2px; min-height: 30px;
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

        # Alt kısım
        bot = QWidget()
        bot.setStyleSheet("background-color: transparent;")
        bl = QVBoxLayout(bot)
        bl.setContentsMargins(12, 4, 12, 10)
        bl.setSpacing(6)

        self.sync_btn = QPushButton("⟳  Senkronize Et")
        self.sync_btn.setFixedHeight(36)
        self.sync_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self.sync_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {C['sync_bg']};
                color: {C['accent_light']};
                border: 1px solid {C['sync_border']};
                border-radius: 8px;
                font-size: 13px; font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {C['sync_hover']};
                color: #ffffff;
            }}
            QPushButton:disabled {{
                background-color: {C['sync_dis']};
                color: #5a5d6e;
                border: 1px solid rgba(255,255,255,0.05);
            }}
        """)
        bl.addWidget(self.sync_btn)

        self.status_label = QLabel("● Hazır")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("color: #22c55e; font-size: 11px; background: transparent;")
        bl.addWidget(self.status_label)
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
        except Exception:
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
        self.status_label.setStyleSheet(f"color: {color}; font-size: 11px; background: transparent;")

    def set_sync_enabled(self, enabled):
        self.sync_btn.setEnabled(enabled)
        self.sync_btn.setText("⟳  Senkronize Et" if enabled else "⏳ Senkronize ediliyor...")
