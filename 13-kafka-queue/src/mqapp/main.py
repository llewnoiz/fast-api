"""FastAPI 앱 — Kafka publish + arq enqueue + BackgroundTasks 비교.

라우트:
    POST /events             Kafka 로 publish (직접)
    POST /jobs/email         arq 에 enqueue (백그라운드)
    POST /bg/touch           FastAPI BackgroundTasks (가장 단순, fire-and-forget)
    GET  /jobs/{job_id}      arq 작업 결과 조회

13 단계의 _세 가지 비동기 작업 메커니즘_ 비교:
    BackgroundTasks  — 같은 프로세스, fire-and-forget. 짧고 신뢰성 낮음 OK.
    arq              — Redis 기반 워커. 재시도/타임아웃/모니터링.
    Kafka            — 다중 컨슈머, 영속성, 이벤트 스트리밍.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated, Any

import structlog
from arq import create_pool
from arq.connections import RedisSettings
from fastapi import BackgroundTasks, Depends, FastAPI, Request

from mqapp.kafka_producer import KafkaPublisher, make_producer
from mqapp.settings import get_settings

log = structlog.get_logger()


# ============================================================================
# lifespan — Kafka producer + arq Redis pool _하나_
# ============================================================================


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()

    # Kafka producer (선택) — 로컬에서 Kafka 안 떠있어도 앱은 시작되도록 try
    try:
        producer = await make_producer(settings.kafka_bootstrap)
        app.state.kafka = KafkaPublisher(producer, settings.kafka_topic)
        app.state.kafka_producer = producer
    except Exception as e:  # noqa: BLE001 — 학습용 — Kafka 없어도 부팅
        log.warning("kafka.unavailable", error=repr(e))
        app.state.kafka = None
        app.state.kafka_producer = None

    # arq Redis pool — retry 0 으로 빠른 실패 (Redis 없을 때 lifespan 안 막힘)
    try:
        rs = RedisSettings.from_dsn(settings.redis_url)
        rs.conn_retries = 0
        app.state.arq = await create_pool(rs)
    except Exception as e:  # noqa: BLE001
        log.warning("arq.unavailable", error=repr(e))
        app.state.arq = None

    try:
        yield
    finally:
        if app.state.kafka_producer:
            await app.state.kafka_producer.stop()
        if app.state.arq:
            await app.state.arq.close()


# ============================================================================
# 의존성
# ============================================================================


def get_kafka(request: Request) -> KafkaPublisher | None:
    return request.app.state.kafka


def get_arq(request: Request) -> Any | None:
    """arq 의 ArqRedis pool 타입은 stub 없어서 Any."""
    return request.app.state.arq


# ============================================================================
# FastAPI 앱
# ============================================================================


def create_app() -> FastAPI:
    app = FastAPI(title="kafka-queue", version="0.1.0", lifespan=lifespan)

    # ---------- BackgroundTasks (가장 단순) ----------
    _touch_count = {"n": 0}

    async def _touch() -> None:
        _touch_count["n"] += 1
        log.info("bg.touch.done", n=_touch_count["n"])

    @app.post("/bg/touch", status_code=202)
    async def bg_touch(bg: BackgroundTasks) -> dict[str, str]:
        """응답 _후_ 같은 프로세스에서 실행. 재시도/모니터링 X."""
        bg.add_task(_touch)
        return {"status": "scheduled"}

    @app.get("/bg/count")
    async def bg_count() -> dict[str, int]:
        return _touch_count

    # ---------- Kafka ----------
    @app.post("/events", status_code=202)
    async def publish_event(
        payload: dict,
        kafka: Annotated[KafkaPublisher | None, Depends(get_kafka)],
    ) -> dict[str, str]:
        if kafka is None:
            return {"status": "skipped", "reason": "kafka unavailable"}
        await kafka.publish(key=str(payload.get("id", "0")), value=payload)
        return {"status": "published"}

    # ---------- arq ----------
    @app.post("/jobs/email", status_code=202)
    async def enqueue_email(
        payload: dict,
        arq: Annotated[Any | None, Depends(get_arq)],
    ) -> dict[str, str | None]:
        if arq is None:
            return {"status": "skipped", "job_id": None}
        job = await arq.enqueue_job("send_email", payload["to"], payload["subject"])
        return {"status": "queued", "job_id": job.job_id if job else None}

    return app


app = create_app()
