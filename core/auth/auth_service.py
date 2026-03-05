from __future__ import annotations

from typing import Optional

from .models import SessionUser
from .password_hasher import PasswordHasher
from .session_context import SessionContext


class AuthService:
    def __init__(self, db, hasher: PasswordHasher, session: SessionContext) -> None:
        self._db = db
        self._hasher = hasher
        self._session = session
        self._lockout_window_minutes = 10
        self._lockout_max_failures = 5

    def authenticate(self, username: str, password: str) -> Optional[SessionUser]:
        # Lockout kontrolu (son N dakika icinde fazla hatali deneme)
        try:
            failures = self._db.get_recent_auth_failures(
                username, self._lockout_window_minutes
            )
            if failures >= self._lockout_max_failures:
                self._db.record_auth_audit(username, success=False, reason="lockout")
                return None
        except Exception:
            # Lockout kontrolu hatasi login'i bloklamasin
            pass

        user = self._db.get_user_by_username(username)
        if not user:
            self._db.record_auth_audit(username, success=False, reason="user_not_found")
            return None
        if not user.is_active:
            self._db.record_auth_audit(username, success=False, reason="inactive")
            return None
        if not self._hasher.verify(password, user.password_hash):
            self._db.record_auth_audit(username, success=False, reason="bad_password")
            return None
        self._db.record_auth_audit(username, success=True, reason="ok")
        session_user = SessionUser(
            user.id,
            user.username,
            user.is_active,
            user.must_change_password,
        )
        self._session.set_user(session_user)
        return session_user

    def change_password(self, user_id: int, new_password: str) -> None:
        """Kullanici sifresini degistir ve ilk giris zorunlulugunu kaldir."""
        password_hash = self._hasher.hash(new_password)
        self._db.update_user_password(user_id, password_hash)
        self._db.update_user_must_change_password(user_id, False)
        current_user = self._session.get_user()
        if current_user and current_user.user_id == user_id:
            self._session.set_user(
                SessionUser(
                    current_user.user_id,
                    current_user.username,
                    current_user.is_active,
                    False,
                )
            )

    def logout(self) -> None:
        self._session.clear()
