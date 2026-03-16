from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional


@dataclass(frozen=True)
class DbUser:
    id: int
    username: str
    password_hash: str
    is_active: bool
    must_change_password: bool


class AuthRepository:
    def __init__(self, sqlite_manager) -> None:
        self._db = sqlite_manager

    def prune_auth_audit(self, retention_days: int) -> int:
        """AuthAudit tablosunda belirtilen günden eski kayıtları siler."""
        return self._db.prune_auth_audit(retention_days)

    def get_user_by_username(self, username: str) -> Optional[DbUser]:
        user = self._db.get_user_by_username(username)
        if not user:
            return None
        return DbUser(
            id=user.id,
            username=user.username,
            password_hash=user.password_hash,
            is_active=user.is_active,
            must_change_password=user.must_change_password,
        )

    def get_permissions_for_user(self, user_id: int) -> Iterable[str]:
        return self._db.get_permissions_for_user(user_id)

    def create_user(
        self,
        username: str,
        password_hash: str,
        is_active: bool = True,
        must_change_password: bool = False,
    ) -> int:
        return self._db.create_user(
            username=username,
            password_hash=password_hash,
            is_active=is_active,
            must_change_password=must_change_password,
        )

    def assign_role(self, user_id: int, role_id: int) -> None:
        self._db.assign_role(user_id=user_id, role_id=role_id)

    def get_all_users(self):
        """Tüm kullanıcıları getir"""
        return self._db.get_all_users()

    def get_user_by_id(self, user_id: int) -> Optional[DbUser]:
        """ID'ye göre kullanıcı getir"""
        return self._db.get_user_by_id(user_id)

    def get_user_roles(self, user_id: int):
        """Kullanıcının rollerini getir"""
        roles = self._db.get_user_roles(user_id)
        # Dict'leri dataclass'a çevir
        from dataclasses import dataclass
        
        @dataclass
        class Role:
            id: int
            name: str
        
        return [Role(id=r["id"], name=r["name"]) for r in roles]

    def get_roles(self):
        return self._db.get_roles()

    def set_user_roles(self, user_id: int, role_ids: list[int]) -> None:
        self._db.set_user_roles(user_id=user_id, role_ids=role_ids)

    def update_user_password(self, user_id: int, password_hash: str) -> None:
        """Kullanıcı şifresini güncelle"""
        self._db.update_user_password(user_id, password_hash)

    def update_user_status(self, user_id: int, is_active: bool) -> None:
        """Kullanıcı aktiflik durumunu güncelle"""
        self._db.update_user_status(user_id, is_active)

    def delete_user(self, user_id: int) -> None:
        """Kullanıcıyı sil"""
        self._db.delete_user(user_id)

    def get_auth_audit_logs(
        self,
        limit: int = 200,
        username_filter: str | None = None,
        success_filter: int | None = None,
    ):
        return self._db.get_auth_audit_logs(
            limit=limit,
            username_filter=username_filter,
            success_filter=success_filter,
        )
    def record_auth_audit(self, username: str, success: bool, reason: str = "") -> None:
        self._db.record_auth_audit(username, success, reason)

    def get_recent_auth_failures(self, username: str, window_minutes: int) -> int:
        return self._db.get_recent_auth_failures(username, window_minutes)

    def update_user_must_change_password(self, user_id: int, must_change: bool) -> None:
        self._db.update_user_must_change_password(user_id, must_change)

