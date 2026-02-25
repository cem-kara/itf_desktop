from __future__ import annotations

from typing import Iterable


class AuthorizationService:
    def __init__(self, db) -> None:
        self._db = db

    def has_permission(self, user_id: int, permission_key: str) -> bool:
        perms = self.get_permissions_for_user(user_id)
        return permission_key in perms

    def get_permissions_for_user(self, user_id: int) -> set[str]:
        permissions: Iterable[str] = self._db.get_permissions_for_user(user_id)
        return set(permissions)
