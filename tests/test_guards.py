import os

from PySide6.QtWidgets import QApplication, QPushButton

from core.auth.authorization_service import AuthorizationService
from core.auth.session_context import SessionContext
from core.auth.models import SessionUser
from ui.guards.action_guard import ActionGuard
from ui.guards.page_guard import PageGuard


def _get_app():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


class FakeDb:
    def __init__(self, permissions):
        self._permissions = permissions

    def get_permissions_for_user(self, user_id):
        return self._permissions


def test_page_guard_denies_without_user():
    db = FakeDb(["personel.read"])
    authz = AuthorizationService(db)
    session = SessionContext()
    guard = PageGuard(authz, session)

    assert guard.can_open("personel.read") is False


def test_page_guard_allows_with_permission():
    db = FakeDb(["admin.panel"])
    authz = AuthorizationService(db)
    session = SessionContext()
    session.set_user(SessionUser(1, "admin", True, False))
    guard = PageGuard(authz, session)

    assert guard.can_open("admin.panel") is True


def test_action_guard_disable_if_unauthorized():
    _get_app()
    db = FakeDb(["personel.read"])
    authz = AuthorizationService(db)
    session = SessionContext()
    session.set_user(SessionUser(1, "viewer", True, False))
    guard = ActionGuard(authz, session)

    btn = QPushButton("Test")
    guard.disable_if_unauthorized(btn, "personel.write")

    assert btn.isEnabled() is False
