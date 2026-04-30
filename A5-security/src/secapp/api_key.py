"""API Key 인증 — 서버↔서버.

JWT 보다 _단순_ + _장기 유효_. 사용자 로그인 X, 자동화 / 마이크로서비스 간 인증.

규칙:
    - **저장**: 평문 X — 단방향 해시 (sha256 또는 bcrypt). 발급 시점에만 _전체 키_ 노출.
    - **회전**: 정기적 (예: 90일). 두 키 _공존_ 기간 두고 천천히 마이그레이션.
    - **prefix 노출**: `pk_live_...` 같이 prefix 만 dashboard 에 표시 (full 키는 다시 못 봄).
    - **scope**: 키마다 _권한 범위_ 제한 (Stripe API 키 패턴).

비교:
    Spring:    `@PreAuthorize("hasAuthority('SCOPE_api')")`
    NestJS:    Guard + ApiKeyStrategy
    Stripe:    `Bearer sk_live_...` (사실상 API key + scope)
"""

from __future__ import annotations

import hashlib
import secrets
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader

# 헤더 자동 추출 (Swagger Authorize 통합)
_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def generate_api_key(prefix: str = "ak") -> tuple[str, str]:
    """(전체_키, 해시) 반환.

    전체_키 — 사용자에게 _한 번만_ 보여줌. 분실 시 재발급.
    해시 — DB 에 저장.
    """
    raw = f"{prefix}_{secrets.token_urlsafe(32)}"
    h = hashlib.sha256(raw.encode()).hexdigest()
    return raw, h


def hash_key(raw: str) -> str:
    """검증 시점에 사용 — 들어온 키를 같은 방식으로 해시 후 DB 비교."""
    return hashlib.sha256(raw.encode()).hexdigest()


# ============================================================================
# 의존성 — 라우트에 `Depends(require_api_key)` 로 보호
# ============================================================================
#
# _학습용_ 인메모리 저장소. 실무는 DB.
# ============================================================================


_VALID_KEY_HASHES: set[str] = set()


def seed(raw_keys: list[str]) -> None:
    """학습/테스트 용 시드."""
    _VALID_KEY_HASHES.clear()
    for k in raw_keys:
        _VALID_KEY_HASHES.add(hash_key(k))


async def require_api_key(
    api_key: Annotated[str | None, Depends(_api_key_header)],
) -> str:
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="X-API-Key header required",
        )
    if hash_key(api_key) not in _VALID_KEY_HASHES:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid api key",
        )
    return api_key
