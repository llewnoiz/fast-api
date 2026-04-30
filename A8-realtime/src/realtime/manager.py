"""ConnectionManager — _단일 인스턴스_ WebSocket 브로드캐스트.

핵심:
    - WebSocket 연결을 _room (채널)_ 단위로 묶어 보관
    - `broadcast(room, message)` 가 같은 room 의 _모든_ 연결에 전송
    - 연결 끊김 시 자동 정리

**한계** (의도적):
    - 한 프로세스 안에서만 동작. 인스턴스 N 개면 _서로 못 봄_.
    - 운영급은 `pubsub.RedisBroker` 와 결합 (다음 모듈) — 인스턴스 간 fan-out.

**다국 비교**:
    Spring `SimpMessagingTemplate` (STOMP) — 자동 사용자/세션 단위 라우팅
    Node `socket.io` — `io.to(room).emit(...)` 표준
    ASP.NET SignalR — `Clients.Group(name).Send(...)` 자동 그룹 관리
"""

from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import Any

from fastapi import WebSocket


class ConnectionManager:
    """동시성 안전: rooms 변경은 _lock_ 으로. broadcast 는 lock 밖에서 실행 (느린 보내기 도중 다른 가입 막지 않음).

    학습 단순화: lock 안에서 list 복사 → lock 밖에서 send. 운영급은 _per-connection 큐_ + 워커.
    """

    def __init__(self) -> None:
        self._rooms: dict[str, set[WebSocket]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def connect(self, room: str, ws: WebSocket) -> None:
        await ws.accept()
        async with self._lock:
            self._rooms[room].add(ws)

    async def disconnect(self, room: str, ws: WebSocket) -> None:
        async with self._lock:
            self._rooms[room].discard(ws)
            if not self._rooms[room]:
                self._rooms.pop(room, None)

    async def broadcast(self, room: str, message: Any) -> int:
        """room 의 모든 WebSocket 에 send_json. 끊긴 연결은 _조용히 무시_.

        반환: 성공적으로 보낸 연결 수. 테스트/디버깅 친화.
        """
        async with self._lock:
            connections = list(self._rooms.get(room, ()))

        sent = 0
        dead: list[WebSocket] = []
        for ws in connections:
            try:
                await ws.send_json(message)
                sent += 1
            except Exception:  # noqa: BLE001 — RuntimeError(disconnected) 등 다양
                dead.append(ws)
        if dead:
            async with self._lock:
                for ws in dead:
                    self._rooms.get(room, set()).discard(ws)
        return sent

    def room_size(self, room: str) -> int:
        return len(self._rooms.get(room, set()))
