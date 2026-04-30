"""인증 순수 함수 테스트 — DB / FastAPI 불필요."""

from __future__ import annotations

import time

import jwt as pyjwt
import pytest

from app.core.security import create_token, decode_token, hash_password, verify_password
from app.core.settings import Settings


@pytest.fixture
def settings() -> Settings:
    return Settings(jwt_secret="test-secret-do-not-use-in-prod", jwt_expire_min=30)


def test_hash_then_verify_round_trip() -> None:
    hashed = hash_password("password123")
    assert hashed != "password123"
    assert verify_password("password123", hashed) is True
    assert verify_password("wrong", hashed) is False


def test_hash_is_random() -> None:
    """bcrypt 는 _매번 다른 salt_ → 같은 입력도 hash 다름."""
    a = hash_password("same")
    b = hash_password("same")
    assert a != b
    assert verify_password("same", a)
    assert verify_password("same", b)


def test_create_and_decode_token(settings: Settings) -> None:
    token = create_token(subject="alice", role="user", settings=settings)
    payload = decode_token(token, settings=settings)
    assert payload["sub"] == "alice"
    assert payload["role"] == "user"
    assert "exp" in payload
    assert "iat" in payload


def test_token_with_wrong_secret_raises(settings: Settings) -> None:
    token = create_token(subject="x", role="user", settings=settings)
    bad = Settings(jwt_secret="different-secret", jwt_expire_min=30)
    with pytest.raises(pyjwt.InvalidSignatureError):
        decode_token(token, settings=bad)


def test_expired_token_raises() -> None:
    """만료 0 분 → 즉시 만료."""
    s = Settings(jwt_secret="x", jwt_expire_min=0)
    token = create_token(subject="alice", role="user", settings=s)
    time.sleep(1)
    with pytest.raises(pyjwt.ExpiredSignatureError):
        decode_token(token, settings=s)
