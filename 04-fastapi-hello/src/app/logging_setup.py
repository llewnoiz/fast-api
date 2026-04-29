"""structlog 설정 — 환경별로 다른 출력.

dev:  사람이 읽기 좋은 컬러 콘솔
prod: JSON 한 줄 (ELK / Datadog / Loki 친화)

12 단계 (관측가능성) 에서 OpenTelemetry / correlation-id 가 추가됨.
"""

from __future__ import annotations

import logging

import structlog


def configure_logging(*, env: str, log_level: str) -> None:
    """앱 시작 시 한 번 호출. 이후 `structlog.get_logger()` 로 어디서든 로거 획득."""
    level_num = getattr(logging, log_level.upper(), logging.INFO)
    logging.basicConfig(level=level_num, format="%(message)s")

    is_dev = env == "dev"
    processors: list = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
    ]
    if is_dev:
        processors.append(structlog.dev.ConsoleRenderer(colors=True))
    else:
        processors.append(structlog.processors.JSONRenderer())

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(level_num),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
