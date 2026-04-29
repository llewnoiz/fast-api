"""t06 — structlog: 구조화 로깅(structured logging).

비교:
    Node:        winston, pino (pino 가 가장 유사)
    Java:        SLF4J + Logback + MDC (MDC = correlation context)
    Kotlin:      kotlin-logging (KotlinLogger), 또는 Java SLF4J
    Spring:      logback-spring.xml + Logback JSON encoder
    Go:          zap, slog (1.21+)

표준 logging 의 한계:
    - 메시지가 _포맷 문자열_ → 검색·집계 어려움
    - 컨텍스트 (request_id, user_id) 를 매번 _수동_ 포함시켜야 함

structlog 의 핵심:
    - 로그가 _구조화된 dict_ → JSON 으로 출력하면 그대로 ELK/Datadog 인덱싱
    - **bind()** 로 컨텍스트 한 번 묶으면 이후 로그에 자동 첨부
    - 12 단계 (correlation-id, OpenTelemetry) 의 기반

이 모듈에서:
    1. 표준 logging 의 _한계_ 보여주기
    2. structlog 기본 사용
    3. bind() 로 컨텍스트 첨부
    4. JSON 출력 vs 사람이 읽기 좋은 출력 (개발/운영 분리)
"""

from __future__ import annotations

import logging

import structlog

# ============================================================================
# 1) 표준 logging 의 한계 — 검색이 어려움
# ============================================================================


def demo_stdlib_pain() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    log = logging.getLogger("stdlib")

    user_id = 42
    order_id = "ord-123"
    log.info("Order created for user %s, order %s", user_id, order_id)
    # → "... INFO Order created for user 42, order ord-123"
    #
    # 운영에서 user_id=42 _만_ 으로 검색하려면? 정규식 짜야 함.
    # JSON 으로 보내면? 또 직접 dict 만들어 추가 — 보일러플레이트.


# ============================================================================
# 2) structlog 기본
# ============================================================================
#
# Java SLF4J 비교:
#   logger.info("Order created", kv("user_id", 42), kv("order_id", "ord-123"))
#
# structlog (key=value 인자):
#   log.info("order.created", user_id=42, order_id="ord-123")
#
# 이게 그대로 JSON 으로 출력되면:
#   {"event": "order.created", "user_id": 42, "order_id": "ord-123", "timestamp": "..."}
# → ELK 에서 user_id:42 한 줄로 검색 가능.
# ============================================================================


def configure_structlog_dev() -> None:
    """개발 환경 — 컬러풀하고 사람이 읽기 좋은 출력."""
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer(colors=False),  # 데모용 colors=False
        ],
    )


def configure_structlog_prod() -> None:
    """운영 환경 — JSON 한 줄(JSONL) 출력. 로그 수집기 친화."""
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
    )


# ============================================================================
# 3) bind() — 컨텍스트 한 번 묶고 _이후 로그에 자동 첨부_
# ============================================================================
#
# Java SLF4J 의 MDC (Mapped Diagnostic Context) 와 같은 자리.
# 한 요청 안에서 user_id, request_id 를 매 로그마다 적지 않아도 됨.
# ============================================================================


def demo_bind() -> None:
    log = structlog.get_logger()

    # request 단위 컨텍스트 묶기
    request_log = log.bind(request_id="req-abc", user_id=42)

    request_log.info("processing.started")
    request_log.info("db.query", table="orders", rows=15)
    request_log.warning("cache.miss", key="user:42")
    request_log.info("processing.finished", duration_ms=120)
    # 모든 로그에 request_id, user_id 자동 첨부됨 — 일일이 안 적어도 됨


def main() -> None:
    print("=== 1) 표준 logging 한계 ===")
    demo_stdlib_pain()

    print("\n=== 2) structlog (개발 환경 — 사람이 읽기) ===")
    configure_structlog_dev()
    log = structlog.get_logger()
    log.info("server.starting", port=8000, env="dev")
    log.warning("cache.miss", key="user:42")

    print("\n=== 3) bind() 로 컨텍스트 첨부 ===")
    demo_bind()

    print("\n=== 4) 운영 환경 (JSON 한 줄) ===")
    configure_structlog_prod()
    log = structlog.get_logger()
    log.info("order.created", user_id=42, order_id="ord-123", amount=15000)
    log.error("payment.failed", user_id=42, reason="insufficient_funds", retry_count=3)


if __name__ == "__main__":
    main()
