"""비밀번호 해싱 + JWT 발급/검증.

비교:
    Spring Security:  BCryptPasswordEncoder + JwtEncoder/JwtDecoder
    NestJS Passport:  bcrypt + @nestjs/jwt (JwtService)

bcrypt 규칙:
    - 단방향 해시 — _복호화 불가_, 검증은 평문을 같은 알고리즘으로 다시 해싱해 비교
    - salt 자동 포함 — 같은 비번도 매번 다른 해시
    - **72바이트 길이 제한** — 그 이상은 잘림 (긴 패스프레이즈는 argon2 권장)
    - bcrypt 4.1 부터 passlib 와 호환 깨짐 → 본 프로젝트는 4.0.x 핀

JWT (HS256 = 대칭 키):
    - secret 만 알면 _누구나_ 발급/검증 가능 → 단일 시스템 / 마이크로서비스간 신뢰 도메인
    - 비대칭(RS256) 은 발급자만 private key, 검증자는 public key — 외부 검증자 분리에 유리
    - claims: sub(누구), exp(만료), iat(발급), roles(우리 추가)
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import jwt as pyjwt
from passlib.context import CryptContext

from authapp.settings import Settings, get_settings

# ============================================================================
# 비밀번호 해싱
# ============================================================================


_pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    return _pwd_ctx.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return _pwd_ctx.verify(plain, hashed)


# ============================================================================
# JWT
# ============================================================================


def create_access_token(*, subject: str, roles: list[str]) -> str:
    """`sub`, `roles`, `exp`, `iat` 클레임 포함."""
    settings = get_settings()
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": subject,
        "roles": roles,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=settings.jwt_expire_minutes)).timestamp()),
    }
    return pyjwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str, settings: Settings | None = None) -> dict[str, Any]:
    """검증 + 디코드. 만료/서명/포맷 실패 시 jwt 의 PyJWTError 계열 예외."""
    settings = settings or get_settings()
    return pyjwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
