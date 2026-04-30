"""FastAPI 앱 — A12 통합 데모.

엔드포인트:
    GET  /healthz                헬스체크
    GET  /work/{n}               n 만큼 가짜 일 (trace span 생성)
    POST /boom                   강제 에러 (Sentry / 로그 ERROR 캡처 데모)
    GET  /slo/burn               현재 burn rate (가상)
    GET  /admin/dashboard.json   Grafana RED 대시보드 JSON
    GET  /admin/alerts.yaml      Prometheus 알림 규칙 dict
"""

from __future__ import annotations

import time
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import structlog
from fastapi import FastAPI, HTTPException, Request

from obsdeep.alerting import slo_burn_rate_alerts, to_rules_yaml
from obsdeep.dashboards import red_dashboard
from obsdeep.sentry_setup import setup_sentry
from obsdeep.settings import get_settings
from obsdeep.slo import Slo, compute_burn_rate, remaining_budget
from obsdeep.structured_logging import (
    bind_request_context,
    clear_request_context,
    setup_logging,
)
from obsdeep.tracing import get_tracer, instrument_fastapi, setup_tracing


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    setup_logging(level=settings.log_level, environment=settings.environment)
    setup_sentry(
        dsn=settings.sentry_dsn,
        environment=settings.environment,
        traces_sample_rate=settings.sentry_traces_sample_rate,
        profiles_sample_rate=settings.sentry_profiles_sample_rate,
    )
    setup_tracing(service_name=settings.service_name, environment=settings.environment)
    instrument_fastapi(app)
    # 학습용 가상 SLO 카운터 (실제는 Prometheus 메트릭)
    app.state.slo_total = 0
    app.state.slo_errors = 0
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="A12 — 관측가능성 운영급", lifespan=lifespan)
    log = structlog.get_logger()

    @app.middleware("http")
    async def correlation_id_middleware(request: Request, call_next: Any) -> Any:
        request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
        bind_request_context(request_id=request_id)
        start = time.monotonic()
        try:
            response = await call_next(request)
        finally:
            elapsed_ms = int((time.monotonic() - start) * 1000)
            log.info(
                "request_complete",
                method=request.method,
                path=request.url.path,
                elapsed_ms=elapsed_ms,
            )
            clear_request_context()
        response.headers["x-request-id"] = request_id
        return response

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/work/{n}")
    async def work(n: int, request: Request) -> dict[str, Any]:
        """가짜 일 — 자식 span 생성으로 분산 trace 시연."""
        tracer = get_tracer(__name__)
        with tracer.start_as_current_span("compute") as span:
            span.set_attribute("work.n", n)
            result = sum(range(n))
            span.set_attribute("work.result", result)
        request.app.state.slo_total += 1
        return {"n": n, "sum": result}

    @app.post("/boom")
    async def boom(request: Request) -> None:
        """강제 에러 — Sentry / 구조화 로그 ERROR 레벨 캡처 데모."""
        request.app.state.slo_total += 1
        request.app.state.slo_errors += 1
        log.error("boom", reason="manual trigger")
        raise HTTPException(status_code=500, detail="boom — observability demo")

    @app.get("/slo/burn")
    async def slo_burn(request: Request) -> dict[str, float | int]:
        slo = Slo(target=0.999, window_minutes=43200)
        burn = compute_burn_rate(
            errors=request.app.state.slo_errors,
            total=max(request.app.state.slo_total, 1),
            slo=slo,
        )
        budget = remaining_budget(
            errors=request.app.state.slo_errors,
            total=max(request.app.state.slo_total, 1),
            slo=slo,
        )
        return {
            "errors": request.app.state.slo_errors,
            "total": request.app.state.slo_total,
            "burn_rate": burn,
            "remaining_budget": budget,
        }

    @app.get("/admin/dashboard.json")
    async def dashboard() -> dict[str, Any]:
        settings = get_settings()
        return red_dashboard(service=settings.service_name).to_json()

    @app.get("/admin/alerts.yaml")
    async def alerts() -> dict[str, Any]:
        settings = get_settings()
        rules = slo_burn_rate_alerts(service=settings.service_name)
        return to_rules_yaml(f"{settings.service_name}.slo", rules)

    return app


app = create_app()
