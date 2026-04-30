"""구조화 로그 (JSON) — Loki / ELK / CloudWatch 친화.

핵심:
    - **JSON 한 줄 = 한 이벤트**: Loki / ELK 가 _자동 파싱_
    - **컨텍스트 (correlation-id, user_id, request_id)** 자동 주입
    - **레벨**: DEBUG / INFO / WARNING / ERROR / CRITICAL
    - **민감정보 redact**: token / password / authorization 헤더는 _절대_ 로그에 X

Loki vs ELK:
    Loki: _라벨_ 기반 인덱싱 (가벼움, 비용 ↓). 로그 _내용_ 은 압축 보관, 검색 시 grep.
    ELK: _전문 인덱싱_ (강력, 비용 ↑). 모든 필드 검색 가능.
    선택: 로그 _많이_ 검색하면 ELK, 라벨로 대시보드/알람만이면 Loki.

비교:
    Spring Boot Logback + Logstash encoder
    Node Pino / Winston JSON formatter
    Go zap / zerolog
"""

from __future__ import annotations

import logging
import sys
from typing import Any

import structlog

# 민감정보 redact 화이트리스트
SENSITIVE_KEYS = {"password", "token", "authorization", "cookie", "api_key", "secret"}


def _redact_sensitive(_logger: object, _name: str, event_dict: dict[str, Any]) -> dict[str, Any]:
    """이벤트 dict 에서 민감 키 _마스킹_. structlog processor 형식."""
    for key in list(event_dict.keys()):
        lower = key.lower()
        if any(s in lower for s in SENSITIVE_KEYS):
            event_dict[key] = "***REDACTED***"
    return event_dict


def setup_logging(*, level: str = "INFO", environment: str = "dev") -> None:
    """structlog 설정 — dev 모드 (콘솔 컬러) vs prod 모드 (JSON 한 줄).

    Loki / ELK 는 stdout 의 _JSON 한 줄_ 을 그대로 수집 (Promtail / Filebeat).
    """
    timestamper = structlog.processors.TimeStamper(fmt="iso", utc=True)
    shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        timestamper,
        _redact_sensitive,
    ]

    if environment == "dev":
        renderer: Any = structlog.dev.ConsoleRenderer()
    else:
        renderer = structlog.processors.JSONRenderer()

    structlog.configure(
        processors=[*shared_processors, renderer],
        wrapper_class=structlog.make_filtering_bound_logger(_level_to_int(level)),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True,
    )


def _level_to_int(level: str) -> int:
    return getattr(logging, level.upper(), logging.INFO)


def bind_request_context(*, request_id: str, user_id: str | None = None) -> None:
    """미들웨어에서 호출. contextvars 에 _요청 단위_ 컨텍스트 저장."""
    structlog.contextvars.bind_contextvars(request_id=request_id)
    if user_id is not None:
        structlog.contextvars.bind_contextvars(user_id=user_id)


def clear_request_context() -> None:
    structlog.contextvars.clear_contextvars()
