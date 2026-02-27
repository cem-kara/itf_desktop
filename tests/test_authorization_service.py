from core.auth.authorization_service import AuthorizationService


class FakeDb:
    def __init__(self, permissions):
        self._permissions = permissions

    def get_permissions_for_user(self, user_id):
        return self._permissions


def test_has_permission_true():
    db = FakeDb(["personel.read", "admin.panel"])
    authz = AuthorizationService(db)
    assert authz.has_permission(1, "admin.panel") is True


def test_has_permission_false():
    db = FakeDb(["personel.read"])
    authz = AuthorizationService(db)
    assert authz.has_permission(1, "admin.panel") is False
