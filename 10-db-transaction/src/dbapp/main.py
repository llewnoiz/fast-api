"""FastAPI 앱 — Engine 은 lifespan 에서 _하나_, UoW 는 요청마다 _하나_."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncEngine

from dbapp.database import make_engine, make_sessionmaker
from dbapp.settings import get_settings
from dbapp.uow import UnitOfWork

# ============================================================================
# lifespan 에 engine / sessionmaker 보관 — app.state 통해 의존성에서 접근
# ============================================================================


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    engine: AsyncEngine = make_engine(settings.database_url, echo=settings.sql_echo)
    app.state.engine = engine
    app.state.sessionmaker = make_sessionmaker(engine)
    try:
        yield
    finally:
        await engine.dispose()


# ============================================================================
# 의존성 — UoW 인스턴스 주입 (요청 단위)
# ============================================================================


async def get_uow(request: Request) -> AsyncIterator[UnitOfWork]:
    """`Request` 매개변수는 FastAPI 가 _자동 주입_. 거기서 app.state 접근."""
    sessionmaker = request.app.state.sessionmaker
    async with UnitOfWork(sessionmaker) as uow:
        yield uow
        # with 끝 = commit (예외 시 rollback)


# ============================================================================
# 스키마
# ============================================================================


class UserIn(BaseModel):
    username: str = Field(min_length=1, max_length=50)
    full_name: str = Field(min_length=1, max_length=100)


class OrderIn(BaseModel):
    item: str = Field(min_length=1, max_length=100)
    quantity: int = Field(gt=0, le=1000)


class UserOut(BaseModel):
    id: int
    username: str
    full_name: str


class OrderOut(BaseModel):
    id: int
    item: str
    quantity: int


class UserWithOrdersOut(UserOut):
    orders: list[OrderOut]


# ============================================================================
# FastAPI 앱
# ============================================================================


def create_app() -> FastAPI:
    app = FastAPI(title="db-transaction", version="0.1.0", lifespan=lifespan)

    @app.post("/users", response_model=UserOut, status_code=201)
    async def create_user(payload: UserIn, uow: Annotated[UnitOfWork, Depends(get_uow)]) -> UserOut:
        u = await uow.users.add(username=payload.username, full_name=payload.full_name)
        return UserOut(id=u.id, username=u.username, full_name=u.full_name)

    @app.get("/users", response_model=list[UserWithOrdersOut])
    async def list_users(
        uow: Annotated[UnitOfWork, Depends(get_uow)],
    ) -> list[UserWithOrdersOut]:
        users = await uow.users.list_with_orders()
        return [
            UserWithOrdersOut(
                id=u.id,
                username=u.username,
                full_name=u.full_name,
                orders=[OrderOut(id=o.id, item=o.item, quantity=o.quantity) for o in u.orders],
            )
            for u in users
        ]

    @app.post("/users/{user_id}/orders", response_model=OrderOut, status_code=201)
    async def create_order(
        user_id: int,
        payload: OrderIn,
        uow: Annotated[UnitOfWork, Depends(get_uow)],
    ) -> OrderOut:
        user = await uow.users.get(user_id)
        if user is None:
            raise HTTPException(status_code=404, detail="user not found")
        o = await uow.orders.add(user_id=user_id, item=payload.item, quantity=payload.quantity)
        return OrderOut(id=o.id, item=o.item, quantity=o.quantity)

    return app


app = create_app()
