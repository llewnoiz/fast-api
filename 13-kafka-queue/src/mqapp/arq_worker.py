"""arq 백그라운드 작업 큐 — Redis 기반.

비교:
    Celery (Python 표준): 가장 풍부, 무거움, _sync 친화_
    arq:                  async 친화, _가벼움_, FastAPI 와 잘 맞음
    Bull (Node):          유사 패턴
    Sidekiq (Ruby):       유사 패턴

언제 BackgroundTasks 가 _아니라_ arq:
    - 작업이 _수 초 이상_
    - _재시도_ 필요 (실패 시 백오프)
    - _스케줄링_ 필요 (cron-like)
    - _분산 워커_ 필요 (여러 인스턴스)
    - 작업 _상태 추적_ 필요

실행:
    arq mqapp.arq_worker.WorkerSettings   ← 별도 프로세스
"""

from __future__ import annotations

import asyncio
from typing import Any

import structlog
from arq.connections import RedisSettings

from mqapp.settings import get_settings

log = structlog.get_logger()


# ============================================================================
# 작업 함수 — _async_ def
# ============================================================================


async def send_email(ctx: dict[str, Any], to: str, subject: str) -> str:
    """가짜 이메일 발송 — 실제론 SES/SendGrid 호출."""
    log.info("arq.send_email", to=to, subject=subject)
    await asyncio.sleep(0.1)
    return f"sent to {to}"


async def process_order(ctx: dict[str, Any], order_id: int) -> dict[str, Any]:
    """주문 처리 — DB 갱신, 외부 호출 등."""
    log.info("arq.process_order", order_id=order_id)
    await asyncio.sleep(0.2)
    return {"order_id": order_id, "status": "processed"}


# ============================================================================
# WorkerSettings — `arq mqapp.arq_worker.WorkerSettings` 로 실행
# ============================================================================


class WorkerSettings:
    """arq 워커 설정. functions / 재시도 정책 / 큐 / 동시성."""

    functions = [send_email, process_order]
    redis_settings = RedisSettings.from_dsn(get_settings().redis_url)

    # 재시도 — 실패 시 backoff
    max_tries = 3
    job_timeout = 30  # 초
    keep_result = 3600  # 결과 1시간 보관 (디버깅용)
