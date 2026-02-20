import os
from ui.styles.icons import Icons, IconColors
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import QSize, Qt
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
        img_path = os.path.join(base_ui_dir, "styles/icons", "maintenance.png")

        if os.path.exists(img_path):
            pixmap = QPixmap(img_path)
            icon.setPixmap(pixmap.scaled(300, 300, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            icon.setStyleSheet("background: transparent;")
        else:
            icon.setPixmap(Icons.pixmap("wrench", size=48, color="#5f6380"))
            icon.setStyleSheet("background: transparent;")

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
        img_path = os.path.join(base_ui_dir, "styles/icons", "main.png")

        if os.path.exists(img_path):
            pixmap = QPixmap(img_path)
            icon.setPixmap(pixmap.scaled(800, 800, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            icon.setStyleSheet("background: transparent;")
        else:
            icon.setPixmap(Icons.pixmap("hospital", size=48, color="#4f7ef8"))
            icon.setStyleSheet("font-size: 56px; background: transparent;")

        layout.addWidget(icon)

        hint = QLabel("Başlamak için sol menüden bir modül seçin")
        hint.setStyleSheet(
            "font-size: 13px; color: #5a5d6e; padding-top: 24px; background: transparent;"
        )
        hint.setAlignment(Qt.AlignCenter)
        layout.addWidget(hint)
