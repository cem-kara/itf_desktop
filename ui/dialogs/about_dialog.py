# -*- coding: utf-8 -*-
"""
HakkindaDialog — Uygulama bilgileri ve lisans bildirimleri.

LGPL v3 uyumluluğu için zorunlu attribution içerir.
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QScrollArea, QWidget
)
from PySide6.QtCore import Qt

from core.config import AppConfig
from ui.styles.colors import DarkTheme as C


class HakkindaDialog(QDialog):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Hakkında")
        self.setFixedSize(520, 580)
        self.setWindowFlags(
            Qt.WindowType.Dialog |
            Qt.WindowType.WindowCloseButtonHint
        )
        self._build_ui()
        self._apply_style()

    # ── UI ─────────────────────────────────────────────────────

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_header())

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(20)

        layout.addWidget(self._build_app_info())
        layout.addWidget(self._divider())
        layout.addWidget(self._build_license_section())
        layout.addWidget(self._divider())
        layout.addWidget(self._build_icon_section())
        layout.addWidget(self._divider())
        layout.addWidget(self._build_contact_section())
        layout.addStretch()

        scroll.setWidget(content)
        root.addWidget(scroll, 1)
        root.addWidget(self._build_footer())

    def _build_header(self) -> QWidget:
        frame = QFrame()
        frame.setObjectName("about_header")
        frame.setFixedHeight(100)

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(32, 20, 32, 20)
        layout.setSpacing(4)

        name_lbl = QLabel(AppConfig.APP_NAME)
        name_lbl.setObjectName("about_app_name")

        ver_lbl = QLabel(f"Sürüm {AppConfig.VERSION}")
        ver_lbl.setObjectName("about_version")

        layout.addWidget(name_lbl)
        layout.addWidget(ver_lbl)
        return frame

    def _build_app_info(self) -> QWidget:
        frame = QFrame()
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self._info_row(layout, "Geliştirici",  "REPYS Geliştirme Ekibi")
        self._info_row(layout, "Platform",     "Windows 10/11 (64-bit)")
        self._info_row(layout, "Veritabanı",   "SQLite 3  —  Yerel depolama")
        self._info_row(layout, "Bulut Sync",   "Google Sheets / Drive API")
        return frame

    def _build_license_section(self) -> QWidget:
        frame = QFrame()
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        title = QLabel("Açık Kaynak Bileşenler")
        title.setObjectName("about_section_title")
        layout.addWidget(title)

        layout.addWidget(self._license_card(
            name    = "PySide6",
            license = "GNU Lesser General Public License v3 (LGPL v3)",
            url     = "https://www.qt.io/licensing",
            note    = (
                "Bu uygulama PySide6 kütüphanesini dinamik olarak bağlar. "
                "Kullanıcılar, PySide6 kütüphanesini LGPL v3 koşulları "
                "çerçevesinde değiştirme hakkına sahiptir."
            )
        ))

        layout.addWidget(self._license_card(
            name    = "Google API Python Client",
            license = "Apache License 2.0",
            url     = "https://github.com/googleapis/google-api-python-client",
        ))

        layout.addWidget(self._license_card(
            name    = "SQLite",
            license = "Public Domain — Kısıtlama yok",
            url     = "https://www.sqlite.org",
        ))

        return frame

    def _build_contact_section(self) -> QWidget:
        frame = QFrame()
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        title = QLabel("Geliştirici İletişim")
        title.setObjectName("about_section_title")
        layout.addWidget(title)

        card = QFrame()
        card.setObjectName("about_card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(14, 12, 14, 12)
        card_layout.setSpacing(6)

        desc = QLabel("Destek, geri bildirim veya lisans sorularınız için:")
        desc.setObjectName("about_card_note")
        card_layout.addWidget(desc)

        mail = QLabel('<a href="mailto:destek@repys.com">destek@repys.com</a>')
        mail.setOpenExternalLinks(True)
        mail.setObjectName("about_card_link")
        mail.setTextFormat(Qt.TextFormat.RichText)
        card_layout.addWidget(mail)

        layout.addWidget(card)
        return frame

    def _build_icon_section(self) -> QWidget:
        frame = QFrame()
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        title = QLabel("İkon Kaynakları")
        title.setObjectName("about_section_title")
        layout.addWidget(title)

        layout.addWidget(self._license_card(
            name    = "Lucide Icons / Tabler Icons",
            license = "MIT License",
            url     = "https://lucide.dev  |  https://tabler.io/icons",
            note    = (
                "Uygulamada kullanılan SVG ikonlar Lucide Icons ve "
                "Tabler Icons projelerinden esinlenerek hazırlanmıştır."
            )
        ))
        return frame

    def _build_footer(self) -> QWidget:
        frame = QFrame()
        frame.setObjectName("about_footer")
        frame.setFixedHeight(60)

        layout = QHBoxLayout(frame)
        layout.setContentsMargins(32, 0, 32, 0)

        copy_lbl = QLabel("© 2024–2026  REPYS Geliştirme Ekibi")
        copy_lbl.setObjectName("about_copy")
        layout.addWidget(copy_lbl, 1)

        btn = QPushButton("Kapat")
        btn.setFixedWidth(100)
        btn.setProperty("style-role", "secondary")
        btn.clicked.connect(self.accept)
        layout.addWidget(btn)
        return frame

    # ── Yardımcılar ────────────────────────────────────────────

    def _license_card(self, name: str, license: str,
                      url: str = "", note: str = "") -> QFrame:
        card = QFrame()
        card.setObjectName("about_card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(4)

        name_lbl = QLabel(name)
        name_lbl.setObjectName("about_card_name")
        layout.addWidget(name_lbl)

        lic_lbl = QLabel(license)
        lic_lbl.setObjectName("about_card_license")
        layout.addWidget(lic_lbl)

        if url:
            link = QLabel(f'<a href="{url}">{url}</a>')
            link.setOpenExternalLinks(True)
            link.setObjectName("about_card_link")
            layout.addWidget(link)

        if note:
            note_lbl = QLabel(note)
            note_lbl.setWordWrap(True)
            note_lbl.setObjectName("about_card_note")
            layout.addWidget(note_lbl)

        return card

    def _info_row(self, layout: QVBoxLayout, key: str, value: str):
        row_widget = QWidget()
        row = QHBoxLayout(row_widget)
        row.setContentsMargins(0, 0, 0, 0)

        k = QLabel(key)
        k.setObjectName("about_key")
        k.setFixedWidth(120)

        v = QLabel(value)
        v.setObjectName("about_value")

        row.addWidget(k)
        row.addWidget(v, 1)
        layout.addWidget(row_widget)

    def _divider(self) -> QFrame:
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setObjectName("about_divider")
        return line

    # ── Stil ───────────────────────────────────────────────────

    def _apply_style(self):
        self.setStyleSheet("""
            QDialog {{
                background-color: {};
            }}
            QScrollArea, QScrollArea > QWidget > QWidget {{
                background-color: {};
            }}

            QFrame#about_header {{
                background-color: {};
                border-bottom: 1px solid {};
            }}
            QLabel#about_app_name {{
                font-size: 15px;
                font-weight: 600;
                color: {};
            }}
            QLabel#about_version {{
                font-size: 12px;
                color: {};
            }}

            QLabel#about_section_title {{
                font-size: 11px;
                font-weight: 700;
                color: {};
                letter-spacing: 1px;
            }}

            QLabel#about_key {{
                font-size: 12px;
                color: {};
            }}
            QLabel#about_value {{
                font-size: 12px;
                color: {};
            }}

            QFrame#about_card {{
                background-color: {};
                border: 1px solid {};
                border-radius: 6px;
            }}
            QLabel#about_card_name {{
                font-size: 13px;
                font-weight: 600;
                color: {};
            }}
            QLabel#about_card_license {{
                font-size: 11px;
                color: {};
            }}
            QLabel#about_card_link {{
                font-size: 11px;
                color: {};
            }}
            QLabel#about_card_note {{
                font-size: 11px;
                color: {};
                margin-top: 4px;
            }}

            QFrame#about_divider {{
                border: none;
                border-top: 1px solid {};
            }}

            QFrame#about_footer {{
                background-color: {};
                border-top: 1px solid {};
            }}
            QLabel#about_copy {{
                font-size: 11px;
                color: {};
            }}
        """.format(
            C.BG_PRIMARY, C.BG_PRIMARY,
            C.BG_SECONDARY, C.BORDER_PRIMARY,
            C.TEXT_PRIMARY, C.TEXT_MUTED,
            C.ACCENT, C.TEXT_MUTED,
            C.TEXT_PRIMARY, C.BG_SECONDARY,
            C.BORDER_PRIMARY, C.TEXT_PRIMARY,
            C.STATUS_SUCCESS, C.ACCENT,
            C.TEXT_MUTED, C.BORDER_PRIMARY,
            C.BG_SECONDARY, C.BORDER_PRIMARY,
            C.TEXT_DISABLED
        ))
