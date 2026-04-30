"""인증 _순수 함수_ — bcrypt 해시 + JWT encode/decode.

FastAPI 의존성 (`get_current_user`, `require_role`) 은 `app.deps.auth` 로 분리
(관심사 분리: pure 함수 vs FastAPI 의존성 트리).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import jwt as pyjwt
from passlib.context import CryptContext

from app.core.settings import Settings

_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    return _pwd.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return _pwd.verify(plain, hashed)


def create_token(*, subject: str, role: str, settings: Settings) -> str:
    """JWT 발급. `subject` 는 보통 username 또는 user_id."""
    now = datetime.now(UTC)
    payload = {
        "sub": subject,
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=settings.jwt_expire_min)).timestamp()),
    }
    return pyjwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str, *, settings: Settings) -> dict[str, Any]:
    """검증 + 디코드. PyJWTError raise 시 호출자가 AuthError 로 변환."""
    return pyjwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
