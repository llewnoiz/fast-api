"""인증 _순수 함수_ — bcrypt 해시 + JWT (access / refresh) encode/decode.

FastAPI 의존성 (`get_current_user`, `require_role`) 은 `app.deps.auth` 로 분리
(관심사 분리: pure 함수 vs FastAPI 의존성 트리).

토큰 페어 패턴:
    - access token: _짧은 TTL_ (15분), 모든 API 호출에 사용
    - refresh token: _긴 TTL_ (7일), `/auth/refresh` 에만 사용 — DB / Redis 에 jti 저장 + revoke
    - rotation: refresh 사용 시 _새 access + 새 refresh_ 발급, 옛 refresh _무효화_
"""

from __future__ import annotations

import secrets
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


# ── Access token ────────────────────────────────────────────────


def create_access_token(*, subject: str, role: str, settings: Settings) -> str:
    """짧은 TTL access JWT. `subject` = username.

    `jti` (랜덤) 포함 — 같은 초 발급 시에도 토큰 _매번 다름_. 운영에서 access revoke 가
    필요해지면 Redis 에 jti 화이트리스트 (refresh 와 같은 패턴) 적용 가능.
    """
    now = datetime.now(UTC)
    payload = {
        "sub": subject,
        "role": role,
        "type": "access",
        "jti": secrets.token_urlsafe(8),
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=settings.jwt_expire_min)).timestamp()),
    }
    return pyjwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str, *, settings: Settings) -> dict[str, Any]:
    """access token 검증 + 디코드. PyJWTError raise."""
    payload = pyjwt.decode(
        token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
    )
    if payload.get("type") not in (None, "access"):  # 옛 토큰 호환 (type 없으면 access)
        raise pyjwt.InvalidTokenError("not an access token")
    return payload


# ── Refresh token ────────────────────────────────────────────────


def create_refresh_token(
    *, subject: str, settings: Settings
) -> tuple[str, str]:
    """refresh JWT 발급 + jti (token id) 반환.

    호출자가 _Redis 에 jti 저장_ 해야 함 (`refresh_store.add_jti`).
    """
    now = datetime.now(UTC)
    jti = secrets.token_urlsafe(16)
    payload = {
        "sub": subject,
        "jti": jti,
        "type": "refresh",
        "iat": int(now.timestamp()),
        "exp": int(
            (now + timedelta(days=settings.refresh_expire_days)).timestamp()
        ),
    }
    token = pyjwt.encode(
        payload, settings.refresh_secret, algorithm=settings.jwt_algorithm
    )
    return token, jti


def decode_refresh_token(token: str, *, settings: Settings) -> dict[str, Any]:
    """refresh token 검증 + 디코드. _별도_ secret 사용.

    `type=refresh` 강제 — access token 으로 refresh 시도 차단.
    """
    payload = pyjwt.decode(
        token, settings.refresh_secret, algorithms=[settings.jwt_algorithm]
    )
    if payload.get("type") != "refresh":
        raise pyjwt.InvalidTokenError("not a refresh token")
    return payload


# ── 호환 alias (옛 테스트 / 외부 코드용) ─────────────────────────
create_token = create_access_token
decode_token = decode_access_token
