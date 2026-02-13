import os
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from core.config import AppConfig

class PlaceholderPage(QWidget):

    def __init__(self, title="", subtitle="", parent=None):
        super().__init__(parent)
        self.setStyleSheet("background-color: transparent;")

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)

        icon = QLabel()
        icon.setAlignment(Qt.AlignCenter)

        # Resim yolunu belirle (ui/styles/maintenance.png varsayımıyla)
        base_ui_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        img_path = os.path.join(base_ui_dir, "styles", "maintenance.png")

        if os.path.exists(img_path):
            pixmap = QPixmap(img_path)
            icon.setPixmap(pixmap.scaled(128, 128, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            icon.setStyleSheet("background: transparent;")
        else:
            icon.setText("🚧")
            icon.setStyleSheet("font-size: 48px; background: transparent;")

        layout.addWidget(icon)

        lbl_title = QLabel(title or "Yapım Aşamasında")
        lbl_title.setStyleSheet(
            "font-size: 20px; font-weight: bold; color: #c8cad0; padding: 8px; background: transparent;"
        )
        lbl_title.setAlignment(Qt.AlignCenter)
        layout.addWidget(lbl_title)

        lbl_sub = QLabel(subtitle or "Bu sayfa henüz geliştirme aşamasında.")
        lbl_sub.setStyleSheet("font-size: 14px; color: #5a5d6e; background: transparent;")
        lbl_sub.setAlignment(Qt.AlignCenter)
        layout.addWidget(lbl_sub)


class WelcomePage(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background-color: transparent;")

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(12)

        icon = QLabel()
        icon.setAlignment(Qt.AlignCenter)

        base_ui_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        img_path = os.path.join(base_ui_dir, "styles", "logo.png")

        if os.path.exists(img_path):
            pixmap = QPixmap(img_path)
            icon.setPixmap(pixmap.scaled(150, 150, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            icon.setStyleSheet("background: transparent;")
        else:
            icon.setText("🏥")
            icon.setStyleSheet("font-size: 56px; background: transparent;")

        layout.addWidget(icon)

        title = QLabel(AppConfig.APP_NAME)
        title.setStyleSheet(
            "font-size: 28px; font-weight: bold; color: #e0e2ea; background: transparent;"
        )
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        subtitle = QLabel("Yönetim Sistemi")
        subtitle.setStyleSheet("font-size: 16px; color: #6bd3ff; background: transparent;")
        subtitle.setAlignment(Qt.AlignCenter)
        layout.addWidget(subtitle)

        hint = QLabel("Başlamak için sol menüden bir modül seçin")
        hint.setStyleSheet(
            "font-size: 13px; color: #5a5d6e; padding-top: 24px; background: transparent;"
        )
        hint.setAlignment(Qt.AlignCenter)
        layout.addWidget(hint)
