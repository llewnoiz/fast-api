"""헬스/레디 라우터 — `/healthz` (liveness) + `/readyz` (readiness).

분리 이유:
    - `/healthz`: _프로세스 살아있음_ 만 (Docker HEALTHCHECK / K8s liveness probe)
    - `/readyz`: DB / Redis 응답 가능 검사 (K8s readiness probe — 트래픽 라우팅 결정)
    - 둘 다 _envelope 미적용_ — 외부 인프라가 _단순 200 OK_ 만 봄
    - `include_in_schema=False` — OpenAPI 문서엔 노출 X (운영 metadata)
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from redis.asyncio import Redis
from sqlalchemy import text

router = APIRouter(tags=["meta"], include_in_schema=False)


@router.get("/healthz")
async def healthz() -> dict[str, str]:
    """Liveness probe — _프로세스 살아있음_ 만 검사."""
    return {"status": "ok"}


@router.get("/readyz")
async def readyz(request: Request) -> dict[str, str]:
    """Readiness probe — DB / Redis 가 _응답 가능_ 한지.

    _하나라도 실패_ 하면 503 → 트래픽 라우팅 _제외_. 대용량 부하 시 _circuit breaker_ 효과.
    """
    sm = request.app.state.sessionmaker
    redis: Redis = request.app.state.redis

    try:
        async with sm() as session:
            await session.execute(text("SELECT 1"))
        ping_result = redis.ping()
        if hasattr(ping_result, "__await__"):
            await ping_result
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=503, detail=f"not ready: {e!r}") from e

    return {"status": "ready"}
