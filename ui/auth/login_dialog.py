from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QFrame,
)
from ui.dialogs.mesaj_kutusu import MesajKutusu
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QPixmap


class LoginDialog(QDialog):
    """Modern giriş dialog'u - SQLite thread-safety ile"""

    def __init__(self, auth_service, parent=None) -> None:
        super().__init__(parent)
        self._auth = auth_service

        self.setWindowTitle("REPYS Giriş")
        self.resize(400, 450)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self._setup_ui()

    def _setup_ui(self) -> None:
        """UI bileşenlerini oluştur"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Ana frame
        self.frame = QFrame()
        self.frame.setStyleSheet(
            "QFrame { background-color: #1a2030; border-radius: 15px; border: 1px solid #3e3e42; }"
        )
        #self.frame.setProperty("bg-role", "panel")  # Tema için rol tanımla
        card_layout = QVBoxLayout(self.frame)
        card_layout.setContentsMargins(40, 40, 40, 40)
        card_layout.setSpacing(20)

        # Başlık
        title_layout = QHBoxLayout()
        title_layout.setSpacing(15)
        title_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Logo
        logo_label = QLabel()
        logo_pixmap = QPixmap("ui/styles/icons/Logo.ico").scaledToWidth(50, Qt.TransformationMode.SmoothTransformation)
        logo_label.setPixmap(logo_pixmap)
        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Başlık metni
        lbl_title = QLabel("REPYS GİRİŞ")
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_title.setFont(QFont("Arial", 60, QFont.Weight.Bold))
        lbl_title.setProperty("color-role", "accent")
        lbl_title.setStyleSheet("border: none;")
        
        title_layout.addWidget(logo_label)
        title_layout.addWidget(lbl_title)
        card_layout.addLayout(title_layout)

        # Kullanıcı adı alanı
        self._username = QLineEdit()
        self._username.setPlaceholderText("Kullanıcı Adı")
        self._username.setFixedHeight(45)
        self._username.setProperty("bg-role", "page")
        self._username.setProperty("color-role", "primary")
        self._username.setProperty("style-role", "form")
        self._username.setText("admin")  # Otomatik doldur
        card_layout.addWidget(self._username)

        # Şifre alanı
        self._password = QLineEdit()
        self._password.setPlaceholderText("Şifre")
        self._password.setEchoMode(QLineEdit.EchoMode.Password)
        self._password.setFixedHeight(45)
        self._password.setProperty("bg-role", "page")
        self._password.setProperty("color-role", "primary")
        self._password.setProperty("style-role", "form")
        self._password.setText("admin123")  # Otomatik doldur
        card_layout.addWidget(self._password)

        # Giriş butonu
        self._button_login = QPushButton("GİRİŞ")
        self._button_login.setFixedHeight(50)
        self._button_login.setCursor(Qt.CursorShape.PointingHandCursor)
        self._button_login.setProperty("style-role", "action")
        self._button_login.clicked.connect(self._on_accept)
        card_layout.addWidget(self._button_login)

        # Kapat butonu
        btn_cancel = QPushButton("İptal")
        btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancel.setProperty("color-role", "muted")
        btn_cancel.setProperty("bg-role", "panel")
        btn_cancel.clicked.connect(self.reject)
        card_layout.addWidget(btn_cancel)

        layout.addWidget(self.frame)

    def keyPressEvent(self, event) -> None:
        """Enter giriş yapar, Escape dialog kapatmaz."""
        key = event.key()
        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self._on_accept()
        elif key == Qt.Key.Key_Escape:
            pass  # Escape ile kapanmasın
        else:
            super().keyPressEvent(event)

    def _on_accept(self) -> None:
        """Giriş butonuna basıldığında çalışır"""
        if not self._button_login.isEnabled():
            return

        username = self._username.text().strip()
        password = self._password.text()

        if not username:
            MesajKutusu.uyari(self, "Kullanıcı adı zorunludur.")
            self._username.setFocus()
            return

        if not password:
            MesajKutusu.uyari(self, "Şifre zorunludur.")
            self._password.setFocus()
            return

        # Butonu devre dışı bırak
        self._button_login.setText("Checking...")
        self._button_login.setEnabled(False)
        self._username.setEnabled(False)
        self._password.setEnabled(False)

        # Sync authentication (ana thread'de veritabanı bağlantısını kullan)
        try:
            user = self._auth.authenticate(username, password)
            if user:
                self.accept()
            else:
                MesajKutusu.hata(self, "Kullanıcı adı veya şifre hatalı.")
                self._reset_ui()
        except Exception as e:
            MesajKutusu.hata(self, f"Giriş sırasında hata oluştu: {str(e)}")
            self._reset_ui()

    def _reset_ui(self) -> None:
        """UI alanlarını sıfırla"""
        self._button_login.setText("GİRİŞ")
        self._button_login.setEnabled(True)
        self._username.setEnabled(True)
        self._password.setEnabled(True)
        self._password.clear()
        self._username.setFocus()

