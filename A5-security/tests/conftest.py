from __future__ import annotations

from collections.abc import AsyncIterator

import pytest_asyncio
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient
from secapp.main import create_app


@pytest_asyncio.fixture
async def app_client() -> AsyncIterator[AsyncClient]:
    app = create_app()
    async with LifespanManager(app), AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
