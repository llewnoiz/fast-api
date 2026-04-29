"""pytest 공용 fixture.

httpx.AsyncClient + ASGITransport — 진짜 서버 안 띄우고 인메모리에서 호출.
Spring `MockMvc`, NestJS `INestApplication.getHttpServer()` 자리.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest_asyncio
from app.main import create_app
from httpx import ASGITransport, AsyncClient


@pytest_asyncio.fixture
async def client() -> AsyncIterator[AsyncClient]:
    """ASGITransport 로 _진짜 네트워크 없이_ 앱을 호출.

    yield 앞: 셋업, 뒤: 정리. with 문과 같은 모델.
    """
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
