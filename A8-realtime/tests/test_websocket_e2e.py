"""WebSocket e2e — Starlette `TestClient` 의 _sync_ websocket 헬퍼 사용.

`TestClient.websocket_connect(path)` 가 컨텍스트 매니저로 _가짜_ WS 클라이언트 제공.
async pytest 에서 sync TestClient 를 쓰는 건 OK — TestClient 는 내부적으로 anyio 로 앱 호출.
"""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient
from realtime.main import create_app
from realtime.settings import get_settings

pytestmark = pytest.mark.integration


@pytest.fixture
def app_no_pubsub(redis_url: str):
    """단일 인스턴스 모드 (use_pubsub=False) 로 테스트 — Redis 없이 manager 만 검증."""
    os.environ["A8_REDIS_URL"] = redis_url
    os.environ["A8_USE_PUBSUB"] = "false"
    get_settings.cache_clear()
    app = create_app()
    with TestClient(app) as client:
        yield client


@pytest.fixture
def app_with_pubsub(redis_url: str):
    """다중 인스턴스 모드 (use_pubsub=True) 로 테스트."""
    os.environ["A8_REDIS_URL"] = redis_url
    os.environ["A8_USE_PUBSUB"] = "true"
    get_settings.cache_clear()
    app = create_app()
    with TestClient(app) as client:
        yield client


def test_healthz(app_no_pubsub: TestClient) -> None:
    r = app_no_pubsub.get("/healthz")
    assert r.status_code == 200


def test_chat_join_and_message(app_no_pubsub: TestClient) -> None:
    """alice 가 join → bob 가 join → alice 가 메시지 → 둘 다 받기."""
    with app_no_pubsub.websocket_connect("/ws/chat/room1?user=alice") as alice:
        # alice 의 join 메시지 수신 (자기 자신도 broadcast 대상)
        join_msg = alice.receive_json()
        assert join_msg == {"type": "join", "user": "alice", "room": "room1"}

        with app_no_pubsub.websocket_connect("/ws/chat/room1?user=bob") as bob:
            # alice 와 bob 둘 다 bob 의 join 받음
            assert alice.receive_json() == {"type": "join", "user": "bob", "room": "room1"}
            assert bob.receive_json() == {"type": "join", "user": "bob", "room": "room1"}

            alice.send_json({"text": "hi"})
            msg_a = alice.receive_json()
            msg_b = bob.receive_json()
            assert msg_a == msg_b == {"type": "msg", "user": "alice", "text": "hi"}


def test_room_isolation(app_no_pubsub: TestClient) -> None:
    """다른 room 끼리는 메시지 안 보임."""
    with (
        app_no_pubsub.websocket_connect("/ws/chat/A?user=u1") as u1,
        app_no_pubsub.websocket_connect("/ws/chat/B?user=u2") as u2,
    ):
        u1.receive_json()  # join
        u2.receive_json()  # join

        u1.send_json({"text": "in-A"})
        assert u1.receive_json()["text"] == "in-A"
        # u2 는 _아무것도_ 받으면 안 됨 — 짧게 확인 (timeout)
        # TestClient WebSocket 은 receive_json 이 blocking 이라 직접 검증 어렵 →
        # u2.send_json 후 자기 메시지가 _바로_ 오는지로 isolation 확인
        u2.send_json({"text": "in-B"})
        assert u2.receive_json()["text"] == "in-B"


def test_broadcast_http_endpoint(app_no_pubsub: TestClient) -> None:
    """HTTP 로 메시지 보내기 — bot/cron 시나리오."""
    with app_no_pubsub.websocket_connect("/ws/chat/news?user=reader") as reader:
        reader.receive_json()  # join

        r = app_no_pubsub.post(
            "/chat/news/broadcast", json={"text": "breaking", "user": "bot"}
        )
        assert r.status_code == 200
        assert r.json()["receivers"] == 1
        assert reader.receive_json() == {"type": "msg", "user": "bot", "text": "breaking"}


def test_room_size(app_no_pubsub: TestClient) -> None:
    with (
        app_no_pubsub.websocket_connect("/ws/chat/big?user=u1"),
        app_no_pubsub.websocket_connect("/ws/chat/big?user=u2"),
    ):
        # join 메시지를 _빼지 않고도_ 사이즈 조회는 가능 (broadcast 결과와 별개)
        size = app_no_pubsub.get("/rooms/big/size").json()
        assert size["local_size"] == 2


def test_chat_with_pubsub_single_instance(app_with_pubsub: TestClient) -> None:
    """use_pubsub=True 라도 _단일 인스턴스_ 안에서 정상 동작 확인.
    (다중 인스턴스 시뮬은 test_pubsub.py 에서 broker 직접 검증)"""
    with app_with_pubsub.websocket_connect("/ws/chat/p1?user=alice") as alice:
        assert alice.receive_json()["type"] == "join"
        alice.send_json({"text": "hello"})
        msg = alice.receive_json()
        assert msg["text"] == "hello"
