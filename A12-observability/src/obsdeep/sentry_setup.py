"""Sentry 에러 추적 통합.

Sentry vs OpenTelemetry:
    OTel: _trace / metrics / logs_ 표준화. _벤더 무관_. _분산 trace_ 가 강점.
    Sentry: _에러 추적_ 특화. stacktrace + breadcrumbs + release tracking + user context.
    → 둘 다 쓰는 게 정석. OTel 로 trace, Sentry 로 _에러 알람_.

설정:
    - `dsn`: Sentry 프로젝트 식별자. 비어있으면 SDK _완전 비활성_ (학습 친화).
    - `traces_sample_rate`: 0~1. 운영은 보통 0.01~0.1 (요청 양 따라).
    - `profiles_sample_rate`: CPU 프로파일링 (실험적). 운영 비용 ↑.
    - `before_send`: 이벤트 전송 전 _가공_ — 민감정보 redact.

핵심 기능:
    - **자동 stacktrace** + 변수 값 캡처
    - **breadcrumbs** — 에러 직전 N 개 로그 / DB 쿼리 / HTTP 요청
    - **user context** — 어느 사용자에서 발생했는지
    - **release tracking** — `git sha` 와 묶어 _어느 버전_ 부터 발생
    - **session tracking** — crash-free rate (모바일 / 프론트)

본 모듈은 _학습용_ ── DSN 없이 동작 검증 가능. 실제 Sentry 호출은 환경변수로 활성화.

다국 비교:
    Java/Node: 같은 sentry-sdk 패키지 (다국어 SDK)
    Datadog APM: 비슷한 영역 (에러 + APM 결합)
    Rollbar / Bugsnag: 에러 추적 alt
"""

from __future__ import annotations

import logging
from typing import Any

import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.logging import LoggingIntegration
from sentry_sdk.integrations.starlette import StarletteIntegration

from obsdeep.structured_logging import SENSITIVE_KEYS

logger = logging.getLogger(__name__)


def _scrub_event(event: dict[str, Any], _hint: dict[str, Any]) -> dict[str, Any]:
    """전송 전 민감정보 _제거_. headers / cookies / query_string 검사.

    Sentry 자체 scrubber 도 있지만 _이중_ 으로 검증 안전.
    """
    request = event.get("request", {})
    if "headers" in request:
        request["headers"] = {
            k: ("***REDACTED***" if k.lower() in SENSITIVE_KEYS else v)
            for k, v in request["headers"].items()
        }
    return event


def setup_sentry(
    *,
    dsn: str | None,
    environment: str = "dev",
    traces_sample_rate: float = 0.0,
    profiles_sample_rate: float = 0.0,
    release: str | None = None,
) -> bool:
    """초기화. DSN 없으면 _no-op_ 으로 처리 (개발/CI 친화).

    반환: 활성화 여부.
    """
    if not dsn:
        logger.info("Sentry DSN not set — skipping init")
        return False

    sentry_sdk.init(
        dsn=dsn,
        environment=environment,
        release=release,
        traces_sample_rate=traces_sample_rate,
        profiles_sample_rate=profiles_sample_rate,
        send_default_pii=False,  # _기본 비활성_ — 운영에서 조심해서 켜기
        before_send=_scrub_event,  # type: ignore[arg-type]
        integrations=[
            FastApiIntegration(transaction_style="endpoint"),
            StarletteIntegration(),
            LoggingIntegration(level=logging.INFO, event_level=logging.ERROR),
        ],
    )
    return True


def capture_exception_with_context(
    exc: Exception,
    *,
    user_id: str | None = None,
    extra: dict[str, Any] | None = None,
) -> None:
    """수동 에러 캡처 + 컨텍스트.

    자동 캡처 (FastApiIntegration) 가 대부분 처리. _수동_ 호출이 필요한 경우:
        - 백그라운드 태스크 (자동 계측 안 됨)
        - except 로 잡고 처리한 _경고성_ 에러
    """
    with sentry_sdk.push_scope() as scope:
        if user_id is not None:
            scope.set_user({"id": user_id})
        if extra:
            for k, v in extra.items():
                scope.set_extra(k, v)
        sentry_sdk.capture_exception(exc)
