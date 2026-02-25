from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .password_hasher import PasswordHasher
from .session_context import SessionContext


@dataclass(frozen=True)
class SessionUser:
    user_id: int
    username: str
    is_active: bool


class AuthService:
    def __init__(self, db, hasher: PasswordHasher, session: SessionContext) -> None:
        self._db = db
        self._hasher = hasher
        self._session = session

    def authenticate(self, username: str, password: str) -> Optional[SessionUser]:
        user = self._db.get_user_by_username(username)
        if not user:
            return None
        if not user.is_active:
            return None
        if not self._hasher.verify(password, user.password_hash):
            return None
        session_user = SessionUser(user.id, user.username, user.is_active)
        self._session.set_user(session_user)
        return session_user

    def logout(self) -> None:
        self._session.clear()
