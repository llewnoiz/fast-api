"""FastAPI 앱 + DI 와이어링.

여기가 헥사고날의 _Composition Root_ ── 모든 어댑터/도메인을 _연결하는 한 곳_.
다른 코드는 _이 와이어링을 모름_ — Protocol 인터페이스만 봄.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from tenderdomain.adapters.api.router import make_router
from tenderdomain.adapters.inmemory import (
    CollectingNotifier,
    InMemoryOrderRepository,
    InMemoryUnitOfWork,
    InMemoryUserRepository,
)
from tenderdomain.application.cancel_order import CancelOrderUseCase
from tenderdomain.application.get_order import GetOrderUseCase
from tenderdomain.application.place_order import PlaceOrderUseCase


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # 어댑터 인스턴스 — 운영은 SQLAlchemy / Kafka.
    user_repo = InMemoryUserRepository()
    user_repo.add(1)
    user_repo.add(2)
    user_repo.add(3)
    order_repo = InMemoryOrderRepository()
    notifier = CollectingNotifier()

    # UoW 는 Repository 를 _공유_ (학습용 단순화). 운영은 _요청 단위_ 새 UoW.
    uow = InMemoryUnitOfWork(orders=order_repo, users=user_repo)

    # use case 인스턴스 ── 학습 단순화로 앱 전체 공유.
    # 운영은 _요청 단위_ DI (FastAPI Depends).
    app.state.place_order_uc = PlaceOrderUseCase(uow=uow, notifier=notifier)
    app.state.cancel_order_uc = CancelOrderUseCase(uow=uow, notifier=notifier)
    app.state.get_order_uc = GetOrderUseCase(uow=uow)
    app.state.notifier = notifier  # 검증용 노출
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="A11 — DDD / 헥사고날", lifespan=lifespan)

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(make_router())
    return app


app = create_app()
