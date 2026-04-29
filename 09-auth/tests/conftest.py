"""테스트 fixture — AsyncClient + 로그인 헬퍼."""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest_asyncio
from authapp.main import create_app
from httpx import ASGITransport, AsyncClient


@pytest_asyncio.fixture
async def client() -> AsyncIterator[AsyncClient]:
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


async def _login(client: AsyncClient, username: str, password: str) -> str:
    """form-data 로 토큰 받아오는 헬퍼. 테스트 가독성용."""
    r = await client.post(
        "/auth/token",
        data={"username": username, "password": password},
    )
    assert r.status_code == 200, f"login failed: {r.text}"
    return r.json()["access_token"]


@pytest_asyncio.fixture
async def alice_token(client: AsyncClient) -> str:
    return await _login(client, "alice", "alice123")


@pytest_asyncio.fixture
async def bob_token(client: AsyncClient) -> str:
    return await _login(client, "bob", "bob123")


@pytest_asyncio.fixture
async def carol_token(client: AsyncClient) -> str:
    return await _login(client, "carol", "carol123")
