"""structlog 설정 — 04 / 12 단계에서 추출."""

from __future__ import annotations

import logging

import structlog


def configure_logging(*, env: str = "dev", log_level: str = "INFO") -> None:
    """앱 시작 시 한 번 호출.

    env="dev"  → 컬러풀 콘솔
    env=other  → JSON 한 줄 (운영 권장)
    """
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
