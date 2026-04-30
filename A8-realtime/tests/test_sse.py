"""SSE 엔드포인트 — `text/event-stream` 응답 검증.

학습 의도: `/notify/{user}` POST 엔드포인트는 _완전한 동기 코드_ 라 검증 가능.
실제 SSE _스트림 내용_ 검증은 TestClient 한계 (cross-thread asyncio.Queue + 무한 스트림)
때문에 _httpx 비동기_ 또는 _진짜 서버_ 가 필요. 본 테스트는 _큐 동작_ 만 검증.
"""

from __future__ import annotations

import asyncio
import os

import pytest
from fastapi.testclient import TestClient
from realtime.main import create_app
from realtime.settings import get_settings

pytestmark = pytest.mark.integration


@pytest.fixture
def client(redis_url: str):
    os.environ["A8_REDIS_URL"] = redis_url
    os.environ["A8_USE_PUBSUB"] = "false"
    get_settings.cache_clear()
    app = create_app()
    with TestClient(app) as c:
        yield c


def test_notify_404_when_user_not_subscribed(client: TestClient) -> None:
    """SSE 큐 등록 안 된 사용자에 notify → 404."""
    r = client.post("/notify/ghost", json={"text": "hi"})
    assert r.status_code == 404


def test_notify_after_subscription_returns_queued(client: TestClient) -> None:
    """SSE 큐를 _직접_ 만든 후 /notify 가 큐에 push 성공."""
    queues = client.app.state.sse_queues
    queues["bob"] = asyncio.Queue()

    r = client.post("/notify/bob", json={"text": "hi", "event": "alert"})
    assert r.status_code == 200
    assert r.json() == {"status": "queued"}

    # 큐에 들어갔는지 확인 (put_nowait + qsize 는 cross-thread 에서도 안전)
    assert queues["bob"].qsize() == 1


def test_notify_multiple_messages(client: TestClient) -> None:
    queues = client.app.state.sse_queues
    queues["alice"] = asyncio.Queue()

    for i in range(5):
        r = client.post("/notify/alice", json={"text": f"msg-{i}"})
        assert r.status_code == 200

    assert queues["alice"].qsize() == 5
