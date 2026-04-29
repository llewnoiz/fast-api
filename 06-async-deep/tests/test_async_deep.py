"""06 단계 — async 핵심 동작 검증.

asyncio_mode=auto (루트 pyproject) 라 함수에 @pytest.mark.asyncio 안 붙여도
async def test_* 가 자동으로 async 테스트로 인식됨.
"""

from __future__ import annotations

import time

from asyncdeep.t02_concurrent import sequential, with_gather, with_taskgroup
from asyncdeep.t03_antipattern import all_async, all_blocking
from asyncdeep.t04_executor import fetch_via_thread
from asyncdeep.t06_async_iter import even_squares, stream_numbers
from asyncdeep.t07_fastapi_loadcompare import build_app, burst
from httpx import ASGITransport, AsyncClient


# ---------- t02 동시성 ----------
class TestConcurrent:
    async def test_gather_faster_than_sequential(self) -> None:
        seq_ms, _ = await sequential()
        gather_ms, _ = await with_gather()
        # 순차는 600ms 근처, gather 는 300ms 근처 — 절반 이하여야
        assert gather_ms < seq_ms / 1.5

    async def test_taskgroup_returns_same_results(self) -> None:
        _, gather_results = await with_gather()
        _, tg_results = await with_taskgroup()
        assert sorted(gather_results) == sorted(tg_results)


# ---------- t03 안티패턴 — sync 가 _진짜_ 더 느림을 증명 ----------
class TestAntipattern:
    async def test_blocking_is_significantly_slower(self) -> None:
        async_ms = await all_async()
        blocking_ms = await all_blocking()
        # blocking 은 _순차_ 화 → 최소 2배 이상 느려야 함
        assert blocking_ms > async_ms * 2


# ---------- t04 to_thread ----------
class TestExecutor:
    async def test_to_thread_returns_value(self) -> None:
        result = await fetch_via_thread("https://example.com")
        assert result == "https://example.com:200"


# ---------- t06 async iterator ----------
class TestAsyncIter:
    async def test_stream_yields_in_order(self) -> None:
        out = []
        async for v in stream_numbers(5):
            out.append(v)
        assert out == [0, 1, 2, 3, 4]

    async def test_even_squares_pipeline(self) -> None:
        out = []
        async for v in even_squares(stream_numbers(6)):
            out.append(v)
        assert out == [0, 4, 16]   # 0,2,4 의 제곱


# ---------- t07 FastAPI sync vs async ----------
class TestLoadCompare:
    """부하 _차이_ 증명은 `make demo M=t07_fastapi_loadcompare` 로.

    인메모리 ASGITransport 환경에선 sync 라우트도 효율적 처리되어
    실제 uvicorn 멀티 워커와 차이가 작음. 진짜 측정은 _실행_ 데모로.
    """

    async def test_both_routes_return_200(self) -> None:
        app = build_app()
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            timeout=10.0,
        ) as client:
            r1 = await client.get("/sync")
            r2 = await client.get("/async")
            assert r1.status_code == 200
            assert r2.status_code == 200
            assert r1.json() == {"mode": "sync"}
            assert r2.json() == {"mode": "async"}

    async def test_async_finishes_in_reasonable_time(self) -> None:
        """동시 20개 async 요청은 _대략 200ms 한 번_ 시간으로 처리되어야."""
        app = build_app()
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            timeout=10.0,
        ) as client:
            t0 = time.perf_counter()
            ms, ok = await burst(client, "/async", 20)
            elapsed = time.perf_counter() - t0
            assert ok == 20
            assert elapsed < 1.0      # 동시 20개가 1초 이내
            assert ms < 1000
