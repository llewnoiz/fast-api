"""structlog 설정 — dev=콘솔 / prod=JSON 한 줄.

운영 (`APP_ENV=prod`) 에선 JSON 출력 → Loki / ELK / CloudWatch _자동 파싱_.
"""

from __future__ import annotations

import logging
from typing import Any

import structlog


def configure_logging(*, env: str = "dev", log_level: str = "INFO") -> None:
    level_num = getattr(logging, log_level.upper(), logging.INFO)
    logging.basicConfig(level=level_num, format="%(message)s")

    is_dev = env == "dev"
    processors: list[Any] = [
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
