"""structlog 설정 — dev=콘솔 / prod=JSON 한 줄 + PII redaction.

운영 (`APP_ENV != dev`) 에선 JSON 출력 → Loki / ELK / CloudWatch _자동 파싱_.
민감 키 (password / token / authorization / secret / api_key) 는 _자동_ `***REDACTED***`.
"""

from __future__ import annotations

import logging
from typing import Any

import structlog

# 키 부분 일치 매칭 — `password`, `Authorization`, `api_key_v2` 등 모두 잡힘.
SENSITIVE_KEY_PARTS = (
    "password",
    "token",
    "authorization",
    "cookie",
    "api_key",
    "apikey",
    "secret",
    "passwd",
)


def _redact_sensitive(
    _logger: object, _name: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    """structlog processor — 이벤트 dict 의 _민감 키_ 마스킹.

    GDPR / PCI DSS / 보안 표준 — 로그에 _평문 자격증명 절대 X_.
    """
    for key in list(event_dict.keys()):
        lower = key.lower()
        if any(part in lower for part in SENSITIVE_KEY_PARTS):
            event_dict[key] = "***REDACTED***"
    return event_dict


def configure_logging(*, env: str = "dev", log_level: str = "INFO") -> None:
    level_num = getattr(logging, log_level.upper(), logging.INFO)
    logging.basicConfig(level=level_num, format="%(message)s")

    is_dev = env == "dev"
    processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        _redact_sensitive,  # 항상 적용 — dev/prod 모두
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
