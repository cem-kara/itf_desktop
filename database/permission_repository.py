from __future__ import annotations

from typing import Iterable


class PermissionRepository:
    def __init__(self, sqlite_manager) -> None:
        self._db = sqlite_manager

    def get_all_permissions(self) -> Iterable[str]:
        cur = self._db.conn.cursor()
        cur.execute("SELECT PermissionKey FROM Permissions")
        return [row["PermissionKey"] for row in cur.fetchall()]

    def get_permissions(self):
        return self._db.get_permissions()

    def create_permission(self, key: str, description: str = "") -> int:
        return self._db.create_permission(key=key, description=description)

    def create_role(self, name: str) -> int:
        return self._db.create_role(name=name)

    def update_role(self, role_id: int, name: str) -> None:
        self._db.update_role(role_id=role_id, name=name)

    def delete_role(self, role_id: int) -> None:
        self._db.delete_role(role_id=role_id)

    def get_roles_with_permission_count(self):
        return self._db.get_roles_with_permission_count()

    def get_role_user_count(self, role_id: int) -> int:
        return self._db.get_role_user_count(role_id)

    def assign_permission_to_role(self, role_id: int, permission_id: int) -> None:
        self._db.assign_permission_to_role(role_id=role_id, permission_id=permission_id)

    def get_role_permissions(self, role_id: int) -> set[int]:
        return self._db.get_role_permissions(role_id)

    def set_role_permissions(self, role_id: int, permission_ids: list[int]) -> None:
        self._db.set_role_permissions(role_id=role_id, permission_ids=permission_ids)
