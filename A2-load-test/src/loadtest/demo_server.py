"""sync vs async 비교용 미니 서버.

06 단계 t07_fastapi_loadcompare 의 build_app() 을 _독립 실행_ 가능하게 wrap.
locust 가 부하를 줄 _진짜 uvicorn 서버_ 가 필요해서.

실행:
    uv run uvicorn loadtest.demo_server:app --host 127.0.0.1 --port 8000
또는:
    make demo-server
"""

from __future__ import annotations

import asyncio
import time

from fastapi import FastAPI

app = FastAPI(title="sync-vs-async demo (A2)")


@app.get("/sync")
def sync_route() -> dict[str, str]:
    """❌ sync — FastAPI 가 _스레드 풀_ 에서 실행. 동시성 한계."""
    time.sleep(0.2)   # 가짜 외부 I/O
    return {"mode": "sync"}


@app.get("/async")
async def async_route() -> dict[str, str]:
    """✅ async — 이벤트 루프가 _진짜_ 동시 처리."""
    await asyncio.sleep(0.2)
    return {"mode": "async"}
