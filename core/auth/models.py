from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SessionUser:
    user_id: int
    username: str
    is_active: bool
    must_change_password: bool
