import os

from PySide6.QtWidgets import QApplication, QDialog

from ui.auth.login_dialog import LoginDialog
from ui.dialogs.mesaj_kutusu import MesajKutusu


def _get_app():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


class FakeAuth:
    def __init__(self, result=None):
        self._result = result
        self.calls = []

    def authenticate(self, username, password):
        self.calls.append((username, password))
        return self._result


def test_login_dialog_accepts_on_success(monkeypatch):
    _get_app()
    monkeypatch.setattr(MesajKutusu, "hata", lambda *args, **kwargs: None)
    monkeypatch.setattr(MesajKutusu, "uyari", lambda *args, **kwargs: None)
    auth = FakeAuth(result=object())
    dialog = LoginDialog(auth_service=auth)

    dialog._username.setText("alice")
    dialog._password.setText("pass1234")

    dialog._on_accept()

    assert dialog.result() == QDialog.DialogCode.Accepted
    assert auth.calls == [("alice", "pass1234")]


def test_login_dialog_rejects_on_failure(monkeypatch):
    _get_app()
    monkeypatch.setattr(MesajKutusu, "hata", lambda *args, **kwargs: None)
    monkeypatch.setattr(MesajKutusu, "uyari", lambda *args, **kwargs: None)
    auth = FakeAuth(result=None)
    dialog = LoginDialog(auth_service=auth)

    dialog._username.setText("alice")
    dialog._password.setText("wrong")

    dialog._on_accept()

    assert dialog.result() != QDialog.DialogCode.Accepted
    assert auth.calls == [("alice", "wrong")]
