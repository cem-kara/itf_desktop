"""Sprint-1 Adım-5: FastAPI başlangıç uygulaması.

Kapsam:
- Health endpoint
- Basit login
- Bearer token kontrolü
- Rol bazlı örnek endpoint

Not:
Bu dosya MVP amaçlı minimal bir iskelet sağlar.
"""

from __future__ import annotations

from datetime import datetime, timezone
from secrets import token_urlsafe
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, status
from pydantic import BaseModel, EmailStr

app = FastAPI(title="REPYS Next API", version="0.1.0")


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"


class UserContext(BaseModel):
    user_id: str
    email: str
    role: str


# MVP için geçici kullanıcı deposu
_USERS = {
    "admin@repys.local": {
        "user_id": "u-admin-001",
        "password": "admin123",
        "role": "admin",
    },
    "staff@repys.local": {
        "user_id": "u-staff-001",
        "password": "staff123",
        "role": "staff",
    },
}

# MVP için bellek içi token deposu (prod'da Redis/DB kullanılmalı)
_ACCESS_TOKENS: dict[str, UserContext] = {}


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "service": "repys-next-api",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.post("/auth/login", response_model=TokenResponse)
def login(payload: LoginRequest) -> TokenResponse:
    user = _USERS.get(payload.email)
    if not user or user["password"] != payload.password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Geçersiz kimlik bilgisi",
        )

    access_token = token_urlsafe(32)
    refresh_token = token_urlsafe(48)

    _ACCESS_TOKENS[access_token] = UserContext(
        user_id=user["user_id"],
        email=payload.email,
        role=user["role"],
    )

    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


def get_current_user(
    authorization: Annotated[str | None, Header()] = None,
) -> UserContext:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer token gerekli",
        )

    token = authorization.removeprefix("Bearer ").strip()
    user = _ACCESS_TOKENS.get(token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Geçersiz veya süresi dolmuş token",
        )

    return user


@app.get("/auth/me", response_model=UserContext)
def me(current_user: Annotated[UserContext, Depends(get_current_user)]) -> UserContext:
    return current_user


@app.get("/admin/ping")
def admin_ping(current_user: Annotated[UserContext, Depends(get_current_user)]) -> dict:
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bu işlem için admin rolü gerekli",
        )

    return {"ok": True, "message": "admin erişimi doğrulandı"}
