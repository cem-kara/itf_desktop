from __future__ import annotations


class PageGuard:
    def __init__(self, authorization_service, session_context) -> None:
        self._authz = authorization_service
        self._session = session_context

    def can_open(self, permission_key: str) -> bool:
        user = self._session.get_user()
        if not user:
            return False
        return self._authz.has_permission(user.user_id, permission_key)
