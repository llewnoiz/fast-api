"""FastAPI BackgroundTasks 검증 — 가장 가벼운 비동기 작업."""

from __future__ import annotations

import asyncio

from httpx import AsyncClient


class TestBackgroundTasks:
    async def test_bg_task_runs_after_response(self, app_client: AsyncClient) -> None:
        # 시작 카운트
        before = (await app_client.get("/bg/count")).json()["n"]

        # 트리거 — 즉시 응답 (202)
        r = await app_client.post("/bg/touch")
        assert r.status_code == 202
        assert r.json() == {"status": "scheduled"}

        # 백그라운드 task 가 _이벤트 루프 다음 tick_ 에 실행됨
        await asyncio.sleep(0.05)

        after = (await app_client.get("/bg/count")).json()["n"]
        assert after == before + 1
