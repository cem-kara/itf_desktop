from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional


@dataclass(frozen=True)
class DbUser:
    id: int
    username: str
    password_hash: str
    is_active: bool


class AuthRepository:
    def __init__(self, sqlite_manager) -> None:
        self._db = sqlite_manager

    def get_user_by_username(self, username: str) -> Optional[DbUser]:
        raise NotImplementedError

    def get_permissions_for_user(self, user_id: int) -> Iterable[str]:
        raise NotImplementedError

    def create_user(self, username: str, password_hash: str, is_active: bool = True) -> int:
        raise NotImplementedError

    def assign_role(self, user_id: int, role_id: int) -> None:
        raise NotImplementedError
