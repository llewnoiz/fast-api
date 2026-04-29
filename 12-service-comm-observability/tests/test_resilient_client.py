"""ResilientClient 재시도 + 회로 차단기 검증 — httpx MockTransport 사용."""

from __future__ import annotations

import httpx
import pytest
from obsapp.http_client import ResilientClient, make_breaker_factory


class TestRetry:
    async def test_success_first_try(self) -> None:
        async def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"ok": True})

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            rc = ResilientClient(client, make_breaker_factory(threshold=10, recovery_s=10), retry_attempts=3)
            assert await rc.get_json("https://api.test/x") == {"ok": True}

    async def test_retries_on_5xx_then_success(self) -> None:
        calls = {"n": 0}

        async def handler(request: httpx.Request) -> httpx.Response:
            calls["n"] += 1
            # 처음 2번은 500, 3번째 200
            return httpx.Response(500 if calls["n"] < 3 else 200, json={"attempt": calls["n"]})

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            rc = ResilientClient(client, make_breaker_factory(threshold=10, recovery_s=10), retry_attempts=5)
            result = await rc.get_json("https://api.test/x")
            assert result["attempt"] == 3
            assert calls["n"] == 3

    async def test_does_not_retry_4xx(self) -> None:
        calls = {"n": 0}

        async def handler(request: httpx.Request) -> httpx.Response:
            calls["n"] += 1
            return httpx.Response(404, json={"error": "not found"})

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            rc = ResilientClient(client, make_breaker_factory(threshold=10, recovery_s=10), retry_attempts=5)
            with pytest.raises(httpx.HTTPStatusError) as exc:
                await rc.get_json("https://api.test/x")
            assert exc.value.response.status_code == 404
            assert calls["n"] == 1   # 한 번만, 재시도 X


class TestCircuitBreaker:
    async def test_opens_after_threshold_failures(self) -> None:
        calls = {"n": 0}

        async def handler(request: httpx.Request) -> httpx.Response:
            calls["n"] += 1
            return httpx.Response(500)

        # threshold=2 — 2번 연속 실패하면 OPEN
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            rc = ResilientClient(
                client,
                make_breaker_factory(threshold=2, recovery_s=60),
                retry_attempts=1,    # 재시도 안 함 → 한 호출 = 한 실패
            )

            # 첫 호출 — 500
            with pytest.raises(httpx.HTTPStatusError):
                await rc.get_json("https://flaky.test/x")
            # 두 번째 — 또 500, 임계치 도달 → 회로 OPEN
            with pytest.raises(httpx.HTTPStatusError):
                await rc.get_json("https://flaky.test/x")

            calls_before_breaker = calls["n"]

            # 세 번째 — 회로 OPEN, _upstream 호출 안 함_, breaker 예외 발생
            with pytest.raises(Exception) as exc:  # noqa: PT011 — breaker 예외 클래스 비공개
                await rc.get_json("https://flaky.test/x")
            assert "open" in str(exc.value).lower() or "breaker" in str(type(exc.value)).lower()

            # 호출 카운터 변동 _없어야_ (빠른 실패)
            assert calls["n"] == calls_before_breaker
