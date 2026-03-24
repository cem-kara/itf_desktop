from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QPushButton,
    QLabel, QFrame
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from ui.admin.audit_view import AuditView
from ui.admin.permissions_view import PermissionsView
from ui.admin.users_view import UsersView
from ui.admin.roles_view import RolesView
from ui.admin.log_viewer_page import LogViewerPage
from ui.admin.yil_sonu_devir_page import YilSonuDevirPage
from ui.admin.backup_page import BackupPage
from ui.styles.colors import DarkTheme
from ui.styles.icons import Icons, IconRenderer


class AdminPanel(QWidget):
    def __init__(self, db, action_guard=None, parent=None):
        super().__init__(parent)
        self._db = db
        self._action_guard = action_guard
        self._build_ui()
    
    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Header
        header = self._build_header()
        layout.addWidget(header)
        
        # Tabs
        self._tabs = QTabWidget()
        self._tabs.setStyleSheet("""
            QTabWidget::pane {{
                border: 1px solid {};
                background: {};
            }}
            QTabBar::tab {{
                background: {};
                color: {};
                padding: 8px 20px;
                border: 1px solid {};
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                margin-right: 2px;
            }}
            QTabBar::tab:selected {{
                background: {};
                color: {};
                border-bottom: 1px solid {};
            }}
            QTabBar::tab:hover {{
                background: {};
            }}
        """.format(
            DarkTheme.BORDER_PRIMARY, DarkTheme.BG_PRIMARY,
            DarkTheme.BG_SECONDARY, DarkTheme.TEXT_SECONDARY,
            DarkTheme.BORDER_PRIMARY, DarkTheme.BG_PRIMARY,
            DarkTheme.TEXT_PRIMARY, DarkTheme.BG_PRIMARY,
            DarkTheme.BG_HOVER
        ))
        
        # Kullanıcılar sekmesi
        self.users_view = UsersView(self._db, action_guard=self._action_guard)
        self._tabs.addTab(self.users_view, "Kullanıcılar")
        self._tabs.setTabIcon(0, Icons.get("user"))
        
        # Roller sekmesi
        self.roles_view = RolesView(self._db, action_guard=self._action_guard)
        self._tabs.addTab(self.roles_view, "Roller")
        self._tabs.setTabIcon(1, Icons.get("shield"))
        
        # Yetkiler sekmesi
        self.permissions_view = PermissionsView(self._db, action_guard=self._action_guard)
        self._tabs.addTab(self.permissions_view, "Yetkiler")
        self._tabs.setTabIcon(2, Icons.get("lock"))
        
        # Audit log sekmesi
        self.audit_view = AuditView(self._db, action_guard=self._action_guard)
        self._tabs.addTab(self.audit_view, "Audit Log")
        self._tabs.setTabIcon(3, Icons.get("clipboard_list"))
        
        # Log görüntüleyici sekmesi
        self.log_viewer = LogViewerPage()
        self._tabs.addTab(self.log_viewer, "Log Görüntüleyici")
        self._tabs.setTabIcon(4, Icons.get("file_text"))
        
        # Yıl sonu devir işlemleri sekmesi
        self.yil_sonu_devir = YilSonuDevirPage(self._db)
        self._tabs.addTab(self.yil_sonu_devir, "Yıl Sonu Devir")
        self._tabs.setTabIcon(5, Icons.get("calendar_year"))
        
        # Yedekleme sekmesi
        self.backup_page = BackupPage()
        self._tabs.addTab(self.backup_page, "Yedekleme")
        self._tabs.setTabIcon(6, Icons.get("database"))

        # Nöbet Ayarları sekmesi (Birimler + Vardiyalar)
        try:
            from ui.admin.nobet_ayarlar_page import NobetAyarlarPage
            self.nobet_ayarlar_page = NobetAyarlarPage(self._db)
            self._tabs.addTab(self.nobet_ayarlar_page, "Nöbet Ayarları")
            self._tabs.setTabIcon(7, Icons.get("settings"))
        except Exception as e:
            from core.logger import logger
            logger.error(f"Nöbet Ayarları sekmesi yüklenemedi: {e}")

        layout.addWidget(self._tabs)
    
    def _build_header(self):
        """Sayfa başlığı"""
        header = QFrame()
        header.setStyleSheet("""
            QFrame {{
                background: {};
                border-bottom: 2px solid {};
                padding: 8px;
            }}
        """.format(DarkTheme.BG_SECONDARY, DarkTheme.BORDER_PRIMARY))
        
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(20, 8, 20, 8)
        
        # Başlık
        title = QLabel("Admin Panel")
        font = QFont()
        font.setPointSize(16)
        font.setBold(True)
        title.setFont(font)
        title.setProperty("color-role", "primary")
        title.style().unpolish(title)
        title.style().polish(title)
        
        header_layout.addWidget(title)
        header_layout.addStretch()
        
        # Kapatma butonu
        self.btn_kapat = QPushButton("Kapat")
        IconRenderer.set_button_icon(self.btn_kapat, "x", size=14)
        self.btn_kapat.setFixedHeight(32)
        self.btn_kapat.setProperty("style-role", "secondary")
        header_layout.addWidget(self.btn_kapat)
        
        return header
    
    def _placeholder(self, name: str) -> QWidget:
        """Placeholder widget"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        label = QLabel(f"{name}")
        label.setStyleSheet("""
            QLabel {{
                color: {};
                font-size: 16px;
                padding: 40px;
            }}
        """.format(DarkTheme.TEXT_DISABLED))
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label)
        
        info = QLabel("Bu özellik yakında eklenecek...")
        info.setProperty("color-role", "disabled")
        info.setStyleSheet("font-size: 12px;")
        info.style().unpolish(info)
        info.style().polish(info)
        info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(info)
        
        return widget

