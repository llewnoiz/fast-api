"""OpenTelemetry 분산 trace 설정.

12 단계와의 차이:
    - 12 단계: ConsoleSpanExporter (학습용)
    - A12: OTLP exporter 패턴 (Jaeger / Tempo / Datadog 등 매니지드 backend 로 전송)

OTLP 가 _벤더 무관_ 표준 — Jaeger / Tempo / Honeycomb / Datadog / NewRelic 모두 수신.

운영 backend 비교:

| 옵션 | 특징 |
|---|---|
| **Jaeger** | 오픈소스, 자체 호스팅, UI 단순 |
| **Tempo** | Grafana 패밀리, 저비용 (object storage 만 사용) |
| **Honeycomb** | 매니지드, _고차원_ 분석 (event-based) |
| **Datadog APM** | 매니지드, _에러 + APM_ 통합 |
| **NewRelic** | 매니지드, AI 인사이트 |

본 모듈: 학습용 ConsoleSpanExporter + OTLP exporter 패턴.

비교:
    Java: opentelemetry-java SDK + auto-instrumentation agent (가장 강력)
    Node: @opentelemetry/sdk-node + auto-instrumentation
    Go: go.opentelemetry.io/otel
"""

from __future__ import annotations

from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    ConsoleSpanExporter,
    SpanExporter,
)


def setup_tracing(
    *,
    service_name: str,
    environment: str = "dev",
    exporter: SpanExporter | None = None,
) -> TracerProvider:
    """TracerProvider 초기화 + FastAPI 자동 계측.

    `exporter` None 이면 ConsoleSpanExporter (학습용). 운영은 OTLP:
        ```python
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        exporter = OTLPSpanExporter(endpoint="http://otel-collector:4317", insecure=True)
        ```
    """
    resource = Resource.create(
        {
            "service.name": service_name,
            "deployment.environment": environment,
        }
    )
    provider = TracerProvider(resource=resource)
    span_exporter: SpanExporter = exporter or ConsoleSpanExporter()
    provider.add_span_processor(BatchSpanProcessor(span_exporter))
    trace.set_tracer_provider(provider)
    return provider


def instrument_fastapi(app: object) -> None:
    """FastAPI 자동 계측 — 모든 라우트가 _trace span_ 생성."""
    FastAPIInstrumentor.instrument_app(app)  # type: ignore[arg-type]


def get_tracer(name: str) -> trace.Tracer:
    """수동 span 생성용. 라이브러리 / 모듈 단위로 _고유 tracer_."""
    return trace.get_tracer(name)
