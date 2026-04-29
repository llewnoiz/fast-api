"""t07 — FastAPI: sync vs async 라우트 부하 비교.

가짜 _느린 외부 API 호출_ (`asyncio.sleep` / `time.sleep` 200ms) 을 _50번 동시_ 요청.
동시 요청은 httpx.AsyncClient + ASGITransport 로 _인메모리_ 에서 (도커 X).

기대 결과:
    sync 라우트   ≈  10초 가까이      ← 워커가 한 번에 1개씩 (사실상 직렬)
    async 라우트  ≈  200ms 근처       ← 동시에 50개 모두 await

이게 FastAPI 가 _async 라우트를 권장하는 이유_.

실무 가이드:
    - I/O 의존 라우트 → 무조건 async + async 라이브러리 (httpx / asyncpg / redis.asyncio)
    - CPU 의존 라우트 → sync 로 두거나 async + run_in_executor
    - sync 라우트는 FastAPI 가 _스레드 풀_ 에서 실행 (안 막히지만 _스레드_ 한정)
"""

from __future__ import annotations

import asyncio
import time

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient


def build_app() -> FastAPI:
    """비교용 _미니 앱_ — 같은 의미 작업을 sync/async 두 라우트로."""
    app = FastAPI()

    @app.get("/sync")
    def sync_route() -> dict[str, str]:
        # ❌ async 가 _아닌_ 라우트 — FastAPI 가 스레드 풀에서 실행.
        # 그래도 진짜 sync I/O 는 스레드 _점유_ → 동시성 한계 (워커 스레드 수)
        time.sleep(0.2)
        return {"mode": "sync"}

    @app.get("/async")
    async def async_route() -> dict[str, str]:
        # ✅ async — 진짜 동시성. 50개도 한꺼번에 await
        await asyncio.sleep(0.2)
        return {"mode": "async"}

    return app


async def burst(client: AsyncClient, path: str, n: int) -> tuple[float, int]:
    """n 개 요청 _동시_ 발사 → 총 걸린 시간 + 성공 카운트."""
    t0 = time.perf_counter()
    responses = await asyncio.gather(*(client.get(path) for _ in range(n)))
    elapsed_ms = (time.perf_counter() - t0) * 1000
    return elapsed_ms, sum(1 for r in responses if r.status_code == 200)


async def main(concurrency: int = 50) -> None:
    app = build_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        print(f"=== 동시 요청 {concurrency}개 — 각각 200ms 작업 ===")

        elapsed, ok = await burst(client, "/sync", concurrency)
        print(f"  /sync   : {elapsed:6.0f}ms   ({ok}/{concurrency} OK)")

        elapsed, ok = await burst(client, "/async", concurrency)
        print(f"  /async  : {elapsed:6.0f}ms   ({ok}/{concurrency} OK)")

        print("\n해석:")
        print("  /sync   = FastAPI 가 sync 라우트를 _스레드 풀_ 에서 실행 (기본 워커 한정).")
        print("  /async  = 한 스레드의 이벤트 루프가 50개 await 를 동시에. 200ms 근처.")


if __name__ == "__main__":
    asyncio.run(main())
