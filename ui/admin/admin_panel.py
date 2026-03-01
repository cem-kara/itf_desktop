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
from ui.admin.settings_page import SettingsPage
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
        self._tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                border: 1px solid {DarkTheme.BORDER_PRIMARY};
                background: {DarkTheme.BG_PRIMARY};
            }}
            QTabBar::tab {{
                background: {DarkTheme.BG_SECONDARY};
                color: {DarkTheme.TEXT_SECONDARY};
                padding: 8px 20px;
                border: 1px solid {DarkTheme.BORDER_PRIMARY};
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                margin-right: 2px;
            }}
            QTabBar::tab:selected {{
                background: {DarkTheme.BG_PRIMARY};
                color: {DarkTheme.TEXT_PRIMARY};
                border-bottom: 1px solid {DarkTheme.BG_PRIMARY};
            }}
            QTabBar::tab:hover {{
                background: {DarkTheme.BG_HOVER};
            }}
        """)
        
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
        
        # Ayarlar sekmesi
        self.settings_page = SettingsPage()
        self._tabs.addTab(self.settings_page, "Ayarlar")
        self._tabs.setTabIcon(7, Icons.get("settings"))
        
        layout.addWidget(self._tabs)
    
    def _build_header(self):
        """Sayfa başlığı"""
        header = QFrame()
        header.setStyleSheet(f"""
            QFrame {{
                background: {DarkTheme.BG_SECONDARY};
                border-bottom: 2px solid {DarkTheme.BORDER_PRIMARY};
                padding: 8px;
            }}
        """)
        
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(20, 8, 20, 8)
        
        # Başlık
        title = QLabel("Admin Panel")
        font = QFont()
        font.setPointSize(16)
        font.setBold(True)
        title.setFont(font)
        title.setStyleSheet(f"color: {DarkTheme.TEXT_PRIMARY};")
        
        header_layout.addWidget(title)
        header_layout.addStretch()
        
        # Kapatma butonu
        self.btn_kapat = QPushButton("Kapat")
        IconRenderer.set_button_icon(self.btn_kapat, "x", size=14)
        self.btn_kapat.setFixedHeight(32)
        self.btn_kapat.setStyleSheet(f"""
            QPushButton {{
                background: {DarkTheme.BG_TERTIARY};
                color: {DarkTheme.TEXT_SECONDARY};
                border: 1px solid {DarkTheme.BORDER_PRIMARY};
                border-radius: 6px;
                padding: 0 16px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background: {DarkTheme.BG_HOVER};
                color: {DarkTheme.TEXT_PRIMARY};
                border-color: {DarkTheme.BORDER_STRONG};
            }}
        """)
        header_layout.addWidget(self.btn_kapat)
        
        return header
    
    def _placeholder(self, name: str) -> QWidget:
        """Placeholder widget"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        label = QLabel(f"{name}")
        label.setStyleSheet(f"""
            QLabel {{
                color: {DarkTheme.TEXT_DISABLED};
                font-size: 16px;
                padding: 40px;
            }}
        """)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label)
        
        info = QLabel("Bu özellik yakında eklenecek...")
        info.setStyleSheet(f"color: {DarkTheme.TEXT_DISABLED}; font-size: 12px;")
        info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(info)
        
        return widget

