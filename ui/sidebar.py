import json
import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QSizePolicy
)
from PySide6.QtCore import Signal, Qt
from core.config import AppConfig


class Sidebar(QWidget):
    """
    Sol menü paneli.
    ayarlar.json → menu_yapilandirma'dan dinamik menü oluşturur.
    """

    menu_clicked = Signal(str, str)   # (grup_adi, baslik) → sayfa geçişi

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setFixedWidth(220)

        self._buttons = {}       # {baslik: QPushButton}
        self._active_btn = None

        self._build_ui()

    # ────────────────────────────────────────

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── Uygulama başlığı ──
        title = QLabel(AppConfig.APP_NAME)
        title.setObjectName("app_title")
        layout.addWidget(title)

        version = QLabel(f"v{AppConfig.VERSION}")
        version.setObjectName("app_version")
        layout.addWidget(version)

        # ── Ayırıcı ──
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("color: #334155; margin: 0px 12px;")
        layout.addWidget(line)

        # ── Menü alanı (scrollable) ──
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        menu_widget = QWidget()
        menu_widget.setStyleSheet("background: transparent;")
        self._menu_layout = QVBoxLayout(menu_widget)
        self._menu_layout.setContentsMargins(0, 4, 0, 4)
        self._menu_layout.setSpacing(0)

        self._load_menu()

        self._menu_layout.addStretch()
        scroll.setWidget(menu_widget)
        layout.addWidget(scroll, 1)

        # ── Alt kısım: Sync butonu ──
        self.sync_btn = QPushButton("⟳  Senkronize Et")
        self.sync_btn.setObjectName("sync_btn")
        layout.addWidget(self.sync_btn)

        # ── Bağlantı durumu ──
        self.status_label = QLabel("● Hazır")
        self.status_label.setObjectName("app_version")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("color: #22c55e; padding: 4px 0 8px 0;")
        layout.addWidget(self.status_label)

    # ────────────────────────────────────────

    def _load_menu(self):
        """ayarlar.json'dan menü yapısını okur."""
        config_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "ayarlar.json"
        )

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            menu_config = data.get("menu_yapilandirma", {})
        except Exception:
            menu_config = {}

        for group_name, items in menu_config.items():
            # Grup başlığı
            header = QLabel(group_name)
            header.setProperty("class", "group_header")
            self._menu_layout.addWidget(header)

            # Menü öğeleri
            for item in items:
                baslik = item.get("baslik", "?")
                btn = QPushButton(baslik)
                btn.setProperty("class", "menu_btn")
                btn.setCheckable(True)
                btn.setCursor(Qt.PointingHandCursor)
                btn.clicked.connect(
                    lambda checked, g=group_name, b=baslik:
                        self._on_menu_click(g, b)
                )

                self._menu_layout.addWidget(btn)
                self._buttons[baslik] = btn

    # ────────────────────────────────────────

    def _on_menu_click(self, group, baslik):
        # Eski aktif butonu deaktif et
        if self._active_btn:
            self._active_btn.setChecked(False)

        # Yeni aktif buton
        btn = self._buttons.get(baslik)
        if btn:
            btn.setChecked(True)
            self._active_btn = btn

        self.menu_clicked.emit(group, baslik)

    # ────────────────────────────────────────

    def set_active(self, baslik):
        """Dışarıdan aktif menüyü set et."""
        self._on_menu_click("", baslik)

    def set_sync_status(self, text, color="#22c55e"):
        """Sync durumunu güncelle."""
        self.status_label.setText(text)
        self.status_label.setStyleSheet(
            f"color: {color}; padding: 4px 0 8px 0;"
        )

    def set_sync_enabled(self, enabled):
        """Sync butonunu aktif/pasif yap."""
        self.sync_btn.setEnabled(enabled)
        self.sync_btn.setText(
            "⟳  Senkronize Et" if enabled else "⏳ Senkronize ediliyor..."
        )
