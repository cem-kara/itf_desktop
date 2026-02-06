from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt


class PlaceholderPage(QWidget):
    """
    Henüz geliştirilmemiş sayfalar için placeholder.
    """

    def __init__(self, title="", subtitle="", parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)

        icon = QLabel("🚧")
        icon.setStyleSheet("font-size: 48px;")
        icon.setAlignment(Qt.AlignCenter)
        layout.addWidget(icon)

        lbl_title = QLabel(title or "Yapım Aşamasında")
        lbl_title.setStyleSheet(
            "font-size: 20px; font-weight: bold; color: #334155; padding: 8px;"
        )
        lbl_title.setAlignment(Qt.AlignCenter)
        layout.addWidget(lbl_title)

        lbl_sub = QLabel(subtitle or "Bu sayfa henüz geliştirme aşamasında.")
        lbl_sub.setStyleSheet("font-size: 14px; color: #64748b;")
        lbl_sub.setAlignment(Qt.AlignCenter)
        layout.addWidget(lbl_sub)


class WelcomePage(QWidget):
    """
    Uygulama açılış ekranı — dashboard hazırlanana kadar kullanılır.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(12)

        icon = QLabel("🏥")
        icon.setStyleSheet("font-size: 56px;")
        icon.setAlignment(Qt.AlignCenter)
        layout.addWidget(icon)

        title = QLabel("ITF Desktop")
        title.setStyleSheet(
            "font-size: 28px; font-weight: bold; color: #1e293b;"
        )
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        subtitle = QLabel("Yönetim Sistemi")
        subtitle.setStyleSheet("font-size: 16px; color: #64748b;")
        subtitle.setAlignment(Qt.AlignCenter)
        layout.addWidget(subtitle)

        hint = QLabel("Başlamak için sol menüden bir modül seçin")
        hint.setStyleSheet(
            "font-size: 13px; color: #94a3b8; padding-top: 24px;"
        )
        hint.setAlignment(Qt.AlignCenter)
        layout.addWidget(hint)
