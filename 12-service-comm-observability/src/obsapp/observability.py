"""OpenTelemetry + Prometheus 셋업.

OTel:
    - **자동 계측** — fastapi/httpx 라이브러리에 _코드 변경 없이_ tracing 부착
    - traceparent 헤더로 분산 trace 전파 (W3C 표준)
    - OTLP exporter — Tempo, Jaeger, Datadog 등 받음

Prometheus:
    - prometheus-fastapi-instrumentator 가 _자동_ 으로 /metrics 엔드포인트 + 기본 메트릭
        (요청 수, 지연시간 분포, 상태 코드별 카운트 등)

비교:
    Spring:    Micrometer (Prometheus + OTel) + Spring Cloud Sleuth
    NestJS:    @nestjs/terminus + nestjs-otel
    Go:        opentelemetry-go + prometheus-go-client
"""

from __future__ import annotations

import structlog
from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from prometheus_fastapi_instrumentator import Instrumentator

from obsapp.settings import Settings

log = structlog.get_logger()


def setup_otel(app: FastAPI, settings: Settings) -> None:
    """OTel TracerProvider 등록 + FastAPI/httpx 자동 계측."""
    if not settings.otel_enabled:
        return

    resource = Resource.create({"service.name": settings.service_name, "deployment.environment": settings.env})
    provider = TracerProvider(resource=resource)

    # exporter — 학습용 콘솔. 운영에선 OTLP HTTP/gRPC.
    if settings.otel_endpoint:
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
            OTLPSpanExporter,  # noqa: PLC0415
        )

        exporter = OTLPSpanExporter(endpoint=settings.otel_endpoint)
    else:
        exporter = ConsoleSpanExporter()  # type: ignore[assignment]

    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

    # 자동 계측 — _라이브러리 코드 변경 없이_
    FastAPIInstrumentor.instrument_app(app)
    HTTPXClientInstrumentor().instrument()

    log.info("otel.configured", endpoint=settings.otel_endpoint or "console")


def setup_prometheus(app: FastAPI) -> Instrumentator:
    """/metrics 엔드포인트 + 기본 RED 메트릭 (Rate / Errors / Duration) 자동."""
    instr = Instrumentator(should_group_status_codes=False, should_ignore_untemplated=True)
    instr.instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)
    return instr
