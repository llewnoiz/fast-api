"""Rate limit — login 엔드포인트 brute-force 방지."""

from __future__ import annotations

import os

import pytest

from tests.conftest import signup_user

pytestmark = pytest.mark.integration


@pytest.fixture
async def low_limit_client(redis_url, postgres_container):
    """login limit 을 _3_ 으로 낮춘 별도 클라이언트 — 테스트 시간 단축."""
    from asgi_lifespan import LifespanManager  # noqa: PLC0415
    from httpx import ASGITransport, AsyncClient  # noqa: PLC0415
    from sqlalchemy import text  # noqa: PLC0415
    from sqlalchemy.ext.asyncio import (  # noqa: PLC0415
        async_sessionmaker,
        create_async_engine,
    )

    async_url, _ = postgres_container

    os.environ["APP_DATABASE_URL"] = async_url
    os.environ["APP_REDIS_URL"] = redis_url
    os.environ["APP_RATE_LIMIT_LOGIN_PER_MIN"] = "3"

    from app.core.settings import get_settings  # noqa: PLC0415

    get_settings.cache_clear()

    # DB clean
    eng = create_async_engine(async_url)
    sm = async_sessionmaker(eng, expire_on_commit=False)
    async with sm() as s:
        await s.execute(text("TRUNCATE users, items RESTART IDENTITY CASCADE"))
        await s.commit()
    await eng.dispose()

    # Redis clean
    from redis.asyncio import Redis  # noqa: PLC0415

    rc = Redis.from_url(redis_url, decode_responses=True)
    await rc.flushdb()
    await rc.aclose()

    # RateLimiter 가 settings_attr 런타임 조회 → reload 불필요
    from app.main import create_app  # noqa: PLC0415

    fastapi_app = create_app()
    async with (
        LifespanManager(fastapi_app),
        AsyncClient(
            transport=ASGITransport(app=fastapi_app), base_url="http://test"
        ) as ac,
    ):
        yield ac

    # cleanup — 다른 테스트가 영향 안 받게 environ 복구
    del os.environ["APP_RATE_LIMIT_LOGIN_PER_MIN"]
    get_settings.cache_clear()


async def test_login_blocked_after_limit_and_envelope_format(low_limit_client) -> None:
    """3회 시도까지 OK (틀린 비번 401), 4회째 → 429 + Retry-After + envelope."""
    await signup_user(
        low_limit_client, email="alice@example.com", username="alice"
    )

    # 잘못된 비번 3번 — 모두 401 (rate limit 통과)
    for _ in range(3):
        r = await low_limit_client.post(
            "/api/v1/auth/login",
            json={"email": "alice@example.com", "password": "wrong"},
        )
        assert r.status_code == 401

    # 4번째 → 429 + Retry-After
    r = await low_limit_client.post(
        "/api/v1/auth/login",
        json={"email": "alice@example.com", "password": "wrong"},
    )
    assert r.status_code == 429
    assert "Retry-After" in r.headers

    # envelope 형식
    body = r.json()
    assert {"code", "message", "data"} <= body.keys()
    assert "429" in body["code"]
