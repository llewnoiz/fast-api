"""헬스체크 라우터 — /healthz, /readyz.

비교:
    Spring Boot:  /actuator/health (auto)
    NestJS:       @nestjs/terminus
    Kubernetes:   liveness probe / readiness probe 가 _이 두 엔드포인트_ 를 찌름

두 가지 차이:
    /healthz   liveness   — "프로세스가 살아있는지". DB 연결 끊겨도 OK
                            응답 _못_ 하면 K8s 가 재시작
    /readyz    readiness  — "트래픽 받을 준비됐는지". DB / Redis / 외부 의존성 OK 인가
                            응답 못 하면 K8s 가 _트래픽 차단_ (재시작 X)

이 단계에선 단순 OK 만 반환. 10 단계 (DB) 부터 _진짜 의존성_ 검사 추가.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.settings import Settings, get_settings

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: str
    app: str
    version: str
    env: str


@router.get("/healthz", summary="Liveness probe")
async def healthz(settings: Annotated[Settings, Depends(get_settings)]) -> HealthResponse:
    """프로세스가 살아있다는 신호만. DB 등 외부 의존성 _검사 안 함_."""
    return HealthResponse(
        status="ok",
        app=settings.app_name,
        version=settings.version,
        env=settings.env,
    )


@router.get("/readyz", summary="Readiness probe")
async def readyz() -> dict[str, str]:
    """트래픽 받을 준비됐는지. 10 단계에서 DB/Redis ping 추가 예정."""
    # TODO(10단계): await db.ping(), await redis.ping()
    return {"status": "ready"}
