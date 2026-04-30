"""FastAPI 앱 — 7가지 패턴 데모 라우트.

엔드포인트:
    GET  /healthz
    GET  /stampede/{key}            stampede 방지 (lock-based) 데모
    GET  /xfetch/{key}              XFetch (PER) 데모
    POST /saga/checkout             Saga orchestration 시연
    POST /cqrs/order                CQRS — command
    GET  /cqrs/summary/{user_id}    CQRS — query
    POST /es/{account}/deposit      Event Sourcing — Deposited 이벤트
    GET  /es/{account}/balance      Event Sourcing — replay
    POST /schema/register           Schema Registry — 등록
    GET  /schema/{subject}/latest   Schema Registry — 최신
    POST /dlq/enqueue               DLQ — 메시지 enqueue (테스트용)
    POST /dlq/process               DLQ — 한 번 처리
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated, Any

from fastapi import Depends, FastAPI, HTTPException, Request
from pydantic import BaseModel
from redis.asyncio import Redis

from cachemqdeep import event_sourcing as es
from cachemqdeep import stampede
from cachemqdeep.cqrs import (
    CqrsStore,
    CreateOrderCommand,
    GetUserSummaryQuery,
    handle_create_order,
    handle_get_summary,
)
from cachemqdeep.dlq import DLQConfig, DLQProcessor
from cachemqdeep.saga import Saga
from cachemqdeep.schema_registry import SchemaRegistry
from cachemqdeep.settings import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    redis = Redis.from_url(settings.redis_url, decode_responses=False)
    app.state.redis = redis
    app.state.cqrs = CqrsStore()
    app.state.event_store = es.EventStore()
    app.state.schema_registry = SchemaRegistry()
    app.state.dlq = DLQProcessor(redis, DLQConfig(main_queue="a7:main", dlq_queue="a7:dlq"))
    try:
        yield
    finally:
        await redis.aclose()


def get_redis(request: Request) -> Redis:
    redis: Redis = request.app.state.redis
    return redis


def get_cqrs(request: Request) -> CqrsStore:
    store: CqrsStore = request.app.state.cqrs
    return store


def get_event_store(request: Request) -> es.EventStore:
    store: es.EventStore = request.app.state.event_store
    return store


def get_schema_registry(request: Request) -> SchemaRegistry:
    reg: SchemaRegistry = request.app.state.schema_registry
    return reg


def get_dlq(request: Request) -> DLQProcessor:
    dlq: DLQProcessor = request.app.state.dlq
    return dlq


RedisDep = Annotated[Redis, Depends(get_redis)]
CqrsDep = Annotated[CqrsStore, Depends(get_cqrs)]
EventStoreDep = Annotated[es.EventStore, Depends(get_event_store)]
SchemaRegDep = Annotated[SchemaRegistry, Depends(get_schema_registry)]
DLQDep = Annotated[DLQProcessor, Depends(get_dlq)]


class OrderIn(BaseModel):
    user_id: int
    item: str
    quantity: int


class SchemaIn(BaseModel):
    subject: str
    schema_def: dict[str, Any]


class MessageIn(BaseModel):
    payload: dict[str, Any]


def create_app() -> FastAPI:
    app = FastAPI(title="A7 — 캐시·MQ 심화", lifespan=lifespan)

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    # ── Stampede ─────────────────────────────────────────────
    @app.get("/stampede/{key}")
    async def stampede_demo(key: str, redis: RedisDep) -> dict[str, Any]:
        async def expensive() -> dict[str, Any]:
            await asyncio.sleep(0.05)  # 비싼 연산 흉내
            return {"computed": key}

        value = await stampede.get_or_set_with_lock(redis, key, expensive, ttl=10)
        return {"value": value}

    @app.get("/xfetch/{key}")
    async def xfetch_demo(key: str, redis: RedisDep) -> dict[str, Any]:
        async def expensive() -> dict[str, Any]:
            await asyncio.sleep(0.05)
            return {"computed": key}

        value = await stampede.get_or_set_xfetch(redis, key, expensive, ttl=10)
        return {"value": value}

    # ── Saga (시연 — 결제 / 재고 / 배송) ───────────────────────
    @app.post("/saga/checkout")
    async def saga_checkout(*, fail_at: str | None = None) -> dict[str, Any]:
        async def charge(ctx: dict[str, object]) -> object:
            if fail_at == "charge":
                raise RuntimeError("payment gateway down")
            ctx["charge_id"] = "ch_abc"
            return "charge_ok"

        async def refund(_ctx: dict[str, object]) -> None:
            pass

        async def reserve(ctx: dict[str, object]) -> object:
            if fail_at == "reserve":
                raise RuntimeError("inventory shortage")
            ctx["reservation_id"] = "rs_xyz"
            return "reserved"

        async def release(_ctx: dict[str, object]) -> None:
            pass

        async def ship(ctx: dict[str, object]) -> object:
            if fail_at == "ship":
                raise RuntimeError("carrier down")
            ctx["shipment_id"] = "sh_123"
            return "shipped"

        async def cancel_shipment(_ctx: dict[str, object]) -> None:
            pass

        saga = (
            Saga()
            .add_step("charge", charge, refund)
            .add_step("reserve", reserve, release)
            .add_step("ship", ship, cancel_shipment)
        )
        result = await saga.execute()
        return {
            "succeeded": result.succeeded,
            "completed": result.completed_steps,
            "compensated": result.compensated_steps,
            "error": result.error,
        }

    # ── CQRS ─────────────────────────────────────────────────
    @app.post("/cqrs/order")
    async def cqrs_create_order(payload: OrderIn, store: CqrsDep) -> dict[str, int]:
        order_id = await handle_create_order(
            store, CreateOrderCommand(payload.user_id, payload.item, payload.quantity)
        )
        return {"order_id": order_id}

    @app.get("/cqrs/summary/{user_id}")
    async def cqrs_summary(user_id: int, store: CqrsDep) -> dict[str, Any]:
        view = await handle_get_summary(store, GetUserSummaryQuery(user_id))
        if view is None:
            raise HTTPException(status_code=404, detail="no orders")
        return {
            "user_id": view.user_id,
            "total_orders": view.total_orders,
            "total_quantity": view.total_quantity,
            "last_item": view.last_item,
        }

    # ── Event Sourcing ───────────────────────────────────────
    @app.post("/es/{account}/open")
    async def es_open(
        account: str, opening_balance: int, store: EventStoreDep
    ) -> dict[str, int]:
        evt = es.open_account(store, account, opening_balance)
        return {"sequence": evt.sequence}

    @app.post("/es/{account}/deposit")
    async def es_deposit(account: str, amount: int, store: EventStoreDep) -> dict[str, int]:
        evt = es.deposit(store, account, amount)
        return {"sequence": evt.sequence}

    @app.post("/es/{account}/withdraw")
    async def es_withdraw(account: str, amount: int, store: EventStoreDep) -> dict[str, int]:
        try:
            evt = es.withdraw(store, account, amount)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e
        return {"sequence": evt.sequence}

    @app.get("/es/{account}/balance")
    async def es_balance(account: str, store: EventStoreDep) -> dict[str, Any]:
        events = store.load(account)
        if not events:
            raise HTTPException(status_code=404, detail="unknown account")
        agg = es.BankAccount.replay(events)
        return {
            "id": agg.id,
            "balance": agg.balance,
            "is_open": agg.is_open,
            "is_closed": agg.is_closed,
            "events": len(events),
        }

    # ── Schema Registry ──────────────────────────────────────
    @app.post("/schema/register")
    async def schema_register(payload: SchemaIn, reg: SchemaRegDep) -> dict[str, int]:
        sv = reg.register(payload.subject, payload.schema_def)
        return {"id": sv.id, "version": sv.version}

    @app.get("/schema/{subject}/latest")
    async def schema_latest(subject: str, reg: SchemaRegDep) -> dict[str, Any]:
        try:
            sv = reg.latest(subject)
        except KeyError as e:
            raise HTTPException(status_code=404, detail=str(e)) from e
        return {"id": sv.id, "version": sv.version, "schema": sv.schema}

    # ── DLQ ──────────────────────────────────────────────────
    @app.post("/dlq/enqueue")
    async def dlq_enqueue(payload: MessageIn, dlq: DLQDep) -> dict[str, str]:
        await dlq.enqueue(payload.payload)
        return {"status": "enqueued"}

    @app.post("/dlq/process")
    async def dlq_process_one(*, fail: bool = False, dlq: DLQDep) -> dict[str, str]:
        async def handler(_msg: dict[str, object]) -> None:
            if fail:
                raise RuntimeError("simulated failure")

        outcome = await dlq.process_one(handler)
        return {"outcome": outcome}

    return app


app = create_app()
