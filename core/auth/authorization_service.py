# core/auth/authorization_service.py
# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Iterable


class AuthorizationService:
    def __init__(self, repo_or_db) -> None:
        """
        repo_or_db: AuthRepository ornegi (tercihli) veya SQLiteManager (geriye donuk).
        """
        # AuthRepository mi yoksa SQLiteManager mi?
        if hasattr(repo_or_db, "get_permissions_for_user"):
            self._repo = repo_or_db
        else:
            # SQLiteManager geldi — AuthRepository sarmala
            from database.auth_repository import AuthRepository

            self._repo = AuthRepository(repo_or_db)

    def has_permission(self, user_id: int, permission_key: str) -> bool:
        return permission_key in self.get_permissions_for_user(user_id)

    def get_permissions_for_user(self, user_id: int) -> set[str]:
        perms: Iterable[str] = self._repo.get_permissions_for_user(user_id)
        return set(perms)
