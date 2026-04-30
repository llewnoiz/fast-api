"""FastAPI 앱 — WebSocket 채팅 + SSE 알림 + Redis pub/sub 다중 인스턴스 fan-out.

엔드포인트:
    GET   /healthz                              헬스체크
    WS    /ws/chat/{room}?user=alice            WebSocket 채팅 (room 단위)
    POST  /chat/{room}/broadcast                HTTP → broker.publish (다중 인스턴스 fan-out 데모)
    GET   /sse/notifications/{user}             SSE 알림 (단방향 스트림)
    POST  /notify/{user}                        HTTP → SSE 큐로 push
    GET   /rooms/{room}/size                    room 의 _이 인스턴스_ 연결 수
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from redis.asyncio import Redis

from realtime.manager import ConnectionManager
from realtime.pubsub import RedisBroker
from realtime.settings import get_settings
from realtime.sse import make_sse_response


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    redis = Redis.from_url(settings.redis_url, decode_responses=False)
    manager = ConnectionManager()
    broker = RedisBroker(redis, manager)
    app.state.redis = redis
    app.state.manager = manager
    app.state.broker = broker
    # 사용자별 SSE 큐 — 학습 단순화. 운영은 _연결 단위_ + Redis pub/sub 으로 fan-out.
    app.state.sse_queues = {}

    if settings.use_pubsub:
        await broker.start()
    try:
        yield
    finally:
        if settings.use_pubsub:
            await broker.stop()
        await redis.aclose()


def get_manager(request: Request) -> ConnectionManager:
    manager: ConnectionManager = request.app.state.manager
    return manager


def get_broker(request: Request) -> RedisBroker:
    broker: RedisBroker = request.app.state.broker
    return broker


def get_sse_queues(request: Request) -> dict[str, asyncio.Queue[dict[str, str | int]]]:
    queues: dict[str, asyncio.Queue[dict[str, str | int]]] = request.app.state.sse_queues
    return queues


ManagerDep = Annotated[ConnectionManager, Depends(get_manager)]
BrokerDep = Annotated[RedisBroker, Depends(get_broker)]
SSEQueuesDep = Annotated[dict[str, asyncio.Queue[dict[str, str | int]]], Depends(get_sse_queues)]


class BroadcastIn(BaseModel):
    text: str
    user: str = "system"


class NotifyIn(BaseModel):
    text: str
    event: str = "notify"


def create_app() -> FastAPI:
    app = FastAPI(title="A8 — Realtime", lifespan=lifespan)

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    # ── WebSocket 채팅 ──────────────────────────────────────────────
    @app.websocket("/ws/chat/{room}")
    async def ws_chat(
        websocket: WebSocket,
        room: str,
        user: str = "anon",
    ) -> None:
        manager: ConnectionManager = websocket.app.state.manager
        broker: RedisBroker = websocket.app.state.broker
        settings = get_settings()

        await manager.connect(room, websocket)
        # 입장 알림 — pub/sub 으로 모든 인스턴스에 fan-out
        join_msg = {"type": "join", "user": user, "room": room}
        if settings.use_pubsub:
            await broker.publish(room, join_msg)
        else:
            await manager.broadcast(room, join_msg)

        try:
            while True:
                payload = await websocket.receive_json()
                # 클라이언트가 보낸 메시지를 모든 참가자에게 fan-out
                msg = {"type": "msg", "user": user, "text": payload.get("text", "")}
                if settings.use_pubsub:
                    await broker.publish(room, msg)
                else:
                    await manager.broadcast(room, msg)
        except WebSocketDisconnect:
            pass
        finally:
            await manager.disconnect(room, websocket)
            leave_msg = {"type": "leave", "user": user, "room": room}
            if settings.use_pubsub:
                await broker.publish(room, leave_msg)
            else:
                await manager.broadcast(room, leave_msg)

    @app.post("/chat/{room}/broadcast")
    async def broadcast_http(
        room: str,
        payload: BroadcastIn,
        manager: ManagerDep,
        broker: BrokerDep,
    ) -> dict[str, int]:
        """HTTP 로 메시지 보내기 — bot / cron 에서 채널로 알림 보낼 때.

        use_pubsub=True 면 모든 인스턴스에 fan-out, False 면 _이 인스턴스_ 만.
        """
        msg = {"type": "msg", "user": payload.user, "text": payload.text}
        settings = get_settings()
        if settings.use_pubsub:
            receivers = await broker.publish(room, msg)
        else:
            receivers = await manager.broadcast(room, msg)
        return {"receivers": receivers}

    @app.get("/rooms/{room}/size")
    async def room_size(room: str, manager: ManagerDep) -> dict[str, int]:
        return {"local_size": manager.room_size(room)}

    # ── SSE 알림 ────────────────────────────────────────────────────
    @app.get("/sse/notifications/{user}")
    async def sse_notifications(user: str, queues: SSEQueuesDep) -> object:
        """사용자 별 SSE 스트림. 같은 user 가 _여러 탭_ 열어도 모두 같은 큐 (학습 단순화)."""
        queue = queues.setdefault(user, asyncio.Queue())
        return make_sse_response(queue)

    @app.post("/notify/{user}")
    async def notify_user(user: str, payload: NotifyIn, queues: SSEQueuesDep) -> dict[str, str]:
        queue = queues.get(user)
        if queue is None:
            raise HTTPException(status_code=404, detail="user not subscribed")
        await queue.put({"event": payload.event, "data": payload.text})
        return {"status": "queued"}

    return app


app = create_app()
