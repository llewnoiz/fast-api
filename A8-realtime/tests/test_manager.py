"""ConnectionManager 단위 테스트 — 실제 WebSocket 없이 _Fake_ 로 검증."""

from __future__ import annotations

import pytest
from realtime.manager import ConnectionManager

from tests.conftest import FakeWebSocket


async def test_connect_accepts_and_tracks() -> None:
    mgr = ConnectionManager()
    ws = FakeWebSocket()
    await mgr.connect("room1", ws)  # type: ignore[arg-type]
    assert ws.accepted is True
    assert mgr.room_size("room1") == 1


async def test_broadcast_to_all() -> None:
    mgr = ConnectionManager()
    ws_a, ws_b = FakeWebSocket(), FakeWebSocket()
    await mgr.connect("room1", ws_a)  # type: ignore[arg-type]
    await mgr.connect("room1", ws_b)  # type: ignore[arg-type]

    sent = await mgr.broadcast("room1", {"hello": "world"})
    assert sent == 2
    assert ws_a.sent == [{"hello": "world"}]
    assert ws_b.sent == [{"hello": "world"}]


async def test_disconnect_removes_from_room() -> None:
    mgr = ConnectionManager()
    ws = FakeWebSocket()
    await mgr.connect("room1", ws)  # type: ignore[arg-type]
    await mgr.disconnect("room1", ws)  # type: ignore[arg-type]
    assert mgr.room_size("room1") == 0


async def test_broadcast_isolates_rooms() -> None:
    mgr = ConnectionManager()
    a = FakeWebSocket()
    b = FakeWebSocket()
    await mgr.connect("roomA", a)  # type: ignore[arg-type]
    await mgr.connect("roomB", b)  # type: ignore[arg-type]

    await mgr.broadcast("roomA", {"to": "A"})
    assert a.sent == [{"to": "A"}]
    assert b.sent == []


async def test_dead_connection_pruned() -> None:
    """send_json 실패 시 _자동 정리_."""
    mgr = ConnectionManager()
    alive = FakeWebSocket()
    dead = FakeWebSocket(raise_on_send=True)
    await mgr.connect("room1", alive)  # type: ignore[arg-type]
    await mgr.connect("room1", dead)  # type: ignore[arg-type]

    sent = await mgr.broadcast("room1", {"x": 1})
    assert sent == 1
    assert mgr.room_size("room1") == 1


@pytest.mark.parametrize("connections", [10, 50])
async def test_broadcast_many_connections(connections: int) -> None:
    mgr = ConnectionManager()
    sockets = [FakeWebSocket() for _ in range(connections)]
    for ws in sockets:
        await mgr.connect("big", ws)  # type: ignore[arg-type]
    sent = await mgr.broadcast("big", {"n": connections})
    assert sent == connections
    assert all(ws.sent == [{"n": connections}] for ws in sockets)
