from __future__ import annotations

from typing import Iterable


class PermissionRepository:
    def __init__(self, sqlite_manager) -> None:
        self._db = sqlite_manager

    def get_all_permissions(self) -> Iterable[str]:
        raise NotImplementedError

    def create_permission(self, key: str, description: str = "") -> int:
        raise NotImplementedError

    def create_role(self, name: str) -> int:
        raise NotImplementedError

    def assign_permission_to_role(self, role_id: int, permission_id: int) -> None:
        raise NotImplementedError
