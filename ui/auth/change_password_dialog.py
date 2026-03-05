from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QVBoxLayout,
)


class ChangePasswordDialog(QDialog):
    def __init__(self, auth_service, session_user, parent=None) -> None:
        super().__init__(parent)
        self._auth = auth_service
        self._session_user = session_user

        self.setWindowTitle("Sifre Degistirme")
        self.setMinimumWidth(360)

        info = QLabel(
            "Ilk giris icin sifre degistirme zorunludur."
        )
        info.setWordWrap(True)

        self._new_password = QLineEdit()
        self._new_password.setEchoMode(QLineEdit.Password)

        self._confirm_password = QLineEdit()
        self._confirm_password.setEchoMode(QLineEdit.Password)

        form = QFormLayout()
        form.addRow("Yeni sifre", self._new_password)
        form.addRow("Yeni sifre tekrar", self._confirm_password)

        self._buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self._buttons.accepted.connect(self._on_accept)
        self._buttons.rejected.connect(self.reject)

        layout = QVBoxLayout()
        layout.addWidget(info)
        layout.addLayout(form)
        layout.addWidget(self._buttons)
        self.setLayout(layout)

    @staticmethod
    def _validate_password(password: str) -> list[str]:
        errors = []
        if len(password) < 8:
            errors.append("Sifre en az 8 karakter olmali")
        if not any(c.isalpha() for c in password):
            errors.append("Sifre en az bir harf icermeli")
        if not any(c.isdigit() for c in password):
            errors.append("Sifre en az bir rakam icermeli")
        return errors

    def _on_accept(self) -> None:
        new_password = self._new_password.text()
        confirm_password = self._confirm_password.text()

        if not new_password:
            QMessageBox.warning(self, "Uyari", "Yeni sifre bos olamaz.")
            self._new_password.setFocus()
            return
        if new_password != confirm_password:
            QMessageBox.warning(self, "Uyari", "Sifreler eslesmiyor.")
            self._confirm_password.setFocus()
            return

        pw_errors = self._validate_password(new_password)
        if pw_errors:
            QMessageBox.warning(self, "Uyari", "\n".join(pw_errors))
            return

        try:
            self._auth.change_password(self._session_user.user_id, new_password)
            QMessageBox.information(self, "Basarili", "Sifre guncellendi.")
            self.accept()
        except Exception as exc:  # pragma: no cover - UI error path
            QMessageBox.critical(self, "Hata", f"Sifre guncellenemedi:\n{exc}")
