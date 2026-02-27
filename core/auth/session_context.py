from __future__ import annotations

from typing import Optional

from .models import SessionUser


class SessionContext:
    def __init__(self) -> None:
        self._user: Optional[SessionUser] = None

    def set_user(self, user: SessionUser) -> None:
        self._user = user

    def get_user(self) -> Optional[SessionUser]:
        return self._user

    def clear(self) -> None:
        self._user = None
