from core.auth.auth_service import AuthService

from core.auth.password_hasher import PasswordHasher
from core.auth.session_context import SessionContext


class FakeUser:
    def __init__(self, user_id, username, password_hash, is_active=True, must_change=False):
        self.id = user_id
        self.username = username
        self.password_hash = password_hash
        self.is_active = is_active
        self.must_change_password = must_change


class FakeDb:
    def __init__(self, user=None, failures=0):
        self._user = user
        self._failures = failures
        self.audit_calls = []
        self.updated_password = None
        self.updated_must_change = None

    def get_recent_auth_failures(self, username, window_minutes):
        return self._failures

    def record_auth_audit(self, username, success, reason=""):
        self.audit_calls.append((username, success, reason))

    def get_user_by_username(self, username):
        return self._user

    def update_user_password(self, user_id, password_hash):
        self.updated_password = (user_id, password_hash)

    def update_user_must_change_password(self, user_id, must_change):
        self.updated_must_change = (user_id, must_change)


def test_authenticate_success_sets_session():
    hasher = PasswordHasher()
    password_hash = hasher.hash("pass1234")
    user = FakeUser(1, "alice", password_hash, is_active=True, must_change=True)
    db = FakeDb(user=user, failures=0)
    session = SessionContext()
    service = AuthService(db, hasher, session)

    session_user = service.authenticate("alice", "pass1234")

    assert session_user is not None
    assert session_user.user_id == 1
    assert session_user.must_change_password is True
    assert session.get_user() is not None
    assert db.audit_calls[-1] == ("alice", True, "ok")


def test_authenticate_rejects_bad_password():
    hasher = PasswordHasher()
    password_hash = hasher.hash("pass1234")
    user = FakeUser(1, "alice", password_hash, is_active=True)
    db = FakeDb(user=user, failures=0)
    session = SessionContext()
    service = AuthService(db, hasher, session)

    session_user = service.authenticate("alice", "wrong")

    assert session_user is None
    assert session.get_user() is None
    assert db.audit_calls[-1] == ("alice", False, "bad_password")


def test_authenticate_rejects_inactive_user():
    hasher = PasswordHasher()
    password_hash = hasher.hash("pass1234")
    user = FakeUser(1, "alice", password_hash, is_active=False)
    db = FakeDb(user=user, failures=0)
    session = SessionContext()
    service = AuthService(db, hasher, session)

    session_user = service.authenticate("alice", "pass1234")

    assert session_user is None
    assert db.audit_calls[-1] == ("alice", False, "inactive")


def test_authenticate_lockout_records_audit():
    hasher = PasswordHasher()
    user = FakeUser(1, "alice", hasher.hash("pass1234"), is_active=True)
    db = FakeDb(user=user, failures=5)
    session = SessionContext()
    service = AuthService(db, hasher, session)

    session_user = service.authenticate("alice", "pass1234")

    assert session_user is None
    assert db.audit_calls[-1] == ("alice", False, "lockout")


