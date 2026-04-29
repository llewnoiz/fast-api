"""FastAPI 앱 — DB + Redis 의존성 주입.

핵심: `Depends` 로 _의존성을 주입_ 하면 테스트에서 `app.dependency_overrides[...]` 로
교체 가능. 이게 FastAPI 테스팅의 _마법_.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException
from psycopg import AsyncConnection
from pydantic import BaseModel, Field
from redis.asyncio import Redis

from testapp.cache import HitCounter
from testapp.repository import ItemRepository
from testapp.settings import Settings, get_settings

# ============================================================================
# 의존성 — Settings 가 _주입 가능_ 해야 테스트에서 교체 가능
# ============================================================================


async def get_db_conn(
    settings: Annotated[Settings, Depends(get_settings)],
) -> AsyncIterator[AsyncConnection]:
    conn = await AsyncConnection.connect(settings.database_url)
    try:
        yield conn
    finally:
        await conn.close()


async def get_redis(
    settings: Annotated[Settings, Depends(get_settings)],
) -> AsyncIterator[Redis]:
    client = Redis.from_url(settings.redis_url, decode_responses=True)
    try:
        yield client
    finally:
        await client.aclose()


def get_repo(
    conn: Annotated[AsyncConnection, Depends(get_db_conn)],
) -> ItemRepository:
    return ItemRepository(conn)


def get_counter(
    client: Annotated[Redis, Depends(get_redis)],
) -> HitCounter:
    return HitCounter(client)


# ============================================================================
# 스키마 (요청/응답)
# ============================================================================


class ItemIn(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    price: int = Field(ge=0)


class ItemOut(BaseModel):
    id: int
    name: str
    price: int


# ============================================================================
# lifespan — 앱 시작 시 스키마 초기화 (학습용; 실무는 Alembic)
# ============================================================================


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:  # noqa: ARG001
    settings = get_settings()
    try:
        async with await AsyncConnection.connect(settings.database_url) as conn:
            await ItemRepository(conn).init_schema()
    except Exception:  # noqa: BLE001 — 부팅 시 DB 없어도 앱 자체는 떠야 함 (테스트 친화)
        pass
    yield


# ============================================================================
# FastAPI 앱
# ============================================================================


def create_app() -> FastAPI:
    app = FastAPI(title="testing-deep", version="0.1.0", lifespan=lifespan)

    @app.post("/items", response_model=ItemOut, status_code=201)
    async def create_item(
        payload: ItemIn,
        repo: Annotated[ItemRepository, Depends(get_repo)],
        counter: Annotated[HitCounter, Depends(get_counter)],
    ) -> ItemOut:
        await counter.hit("create_item")
        item = await repo.add(payload.name, payload.price)
        return ItemOut(id=item.id, name=item.name, price=item.price)

    @app.get("/items/{item_id}", response_model=ItemOut)
    async def get_item(
        item_id: int,
        repo: Annotated[ItemRepository, Depends(get_repo)],
        counter: Annotated[HitCounter, Depends(get_counter)],
    ) -> ItemOut:
        await counter.hit("get_item")
        item = await repo.get(item_id)
        if item is None:
            raise HTTPException(status_code=404, detail="item not found")
        return ItemOut(id=item.id, name=item.name, price=item.price)

    @app.get("/stats")
    async def stats(
        repo: Annotated[ItemRepository, Depends(get_repo)],
        counter: Annotated[HitCounter, Depends(get_counter)],
    ) -> dict[str, int]:
        return {
            "total_price": await repo.total(),
            "hits_create": await counter.get("create_item"),
            "hits_get": await counter.get("get_item"),
        }

    return app


app = create_app()
