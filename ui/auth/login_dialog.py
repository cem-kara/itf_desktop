from __future__ import annotations

from PySide6.QtWidgets import QDialog, QDialogButtonBox, QFormLayout, QLineEdit, QMessageBox, QVBoxLayout


class LoginDialog(QDialog):
    def __init__(self, auth_service, parent=None) -> None:
        super().__init__(parent)
        self._auth = auth_service

        self.setWindowTitle("Login")

        self._username = QLineEdit()
        self._password = QLineEdit()
        self._password.setEchoMode(QLineEdit.Password)

        form = QFormLayout()
        form.addRow("Username", self._username)
        form.addRow("Password", self._password)

        self._buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self._buttons.accepted.connect(self._on_accept)
        self._buttons.rejected.connect(self.reject)

        layout = QVBoxLayout()
        layout.addLayout(form)
        layout.addWidget(self._buttons)
        self.setLayout(layout)

    def _on_accept(self) -> None:
        username = self._username.text().strip()
        password = self._password.text()
        if not username:
            QMessageBox.warning(self, "Login", "Username is required.")
            self._username.setFocus()
            return
        if not password:
            QMessageBox.warning(self, "Login", "Password is required.")
            self._password.setFocus()
            return
        user = self._auth.authenticate(username, password)
        if user:
            self.accept()
            return
        QMessageBox.warning(self, "Login Failed", "Invalid username or password.")
