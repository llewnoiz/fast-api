"""httpx.AsyncClient 재사용 + tenacity 재시도 + purgatory 회로 차단기.

규칙:
    - **AsyncClient 는 _하나_** — 앱 lifespan 동안 재사용. 매 요청마다 새로 만들면 _커넥션 풀 못 씀_.
    - **재시도** — _idempotent_ 호출(GET/PUT)에만. POST 는 _신중히_ (중복 처리 위험).
    - **회로 차단기** — 연속 실패 후 _빠른 실패_ → upstream 부담 ↓, 자기 보호.

비교:
    Spring:    RestTemplate / WebClient + RetryTemplate + Resilience4j CircuitBreaker
    NestJS:    HttpService + axios-retry + opossum
    Go:        net/http + retry-go + sony/gobreaker
"""

from __future__ import annotations

from typing import Any

import httpx
import structlog
from purgatory import AsyncCircuitBreakerFactory
from tenacity import (
    AsyncRetrying,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

log = structlog.get_logger()


# ============================================================================
# 회로 차단기 — 앱 단위 _하나_
# ============================================================================
#
# 상태:
#   CLOSED   : 정상. 호출 통과
#   OPEN     : 실패 누적 → _빠른 실패_, upstream 호출 안 함
#   HALF_OPEN: 일정 시간 후 한 번 시도 → 성공 시 CLOSED, 실패 시 OPEN 복귀
# ============================================================================


def make_breaker_factory(threshold: int, recovery_s: float) -> AsyncCircuitBreakerFactory:
    return AsyncCircuitBreakerFactory(
        default_threshold=threshold,
        default_ttl=int(recovery_s),
    )


# ============================================================================
# 재시도 정책 — 일시 실패에만, 영구 실패엔 재시도 _안_ 함
# ============================================================================


def _is_retryable(exc: BaseException) -> bool:
    """5xx, 타임아웃, 네트워크 오류만 재시도. 4xx 는 _영구_ 실패."""
    if isinstance(exc, httpx.TimeoutException | httpx.NetworkError):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code >= 500
    return False


# ============================================================================
# 재사용 가능한 ResilientClient
# ============================================================================


class ResilientClient:
    """httpx.AsyncClient 를 _감싸_ 재시도 + 회로 차단기 추가."""

    def __init__(
        self,
        client: httpx.AsyncClient,
        breaker_factory: AsyncCircuitBreakerFactory,
        *,
        retry_attempts: int = 3,
    ) -> None:
        self._client = client
        self._breakers = breaker_factory
        self._retry_attempts = retry_attempts

    async def get_json(self, url: str, **kwargs: Any) -> Any:
        """GET 호출 — 재시도 + 회로 차단기 적용. 응답 JSON 반환.

        회로 차단기 키: URL host. 같은 호스트 누적 실패 ↑ → 빠른 실패.
        """
        host = httpx.URL(url).host or "unknown"
        breaker = await self._breakers.get_breaker(host)

        async with breaker:
            async for attempt in AsyncRetrying(
                stop=stop_after_attempt(self._retry_attempts),
                wait=wait_exponential(multiplier=0.1, min=0.05, max=1.0),
                retry=retry_if_exception(_is_retryable),
                reraise=True,
            ):
                with attempt:
                    log.debug("http.request", url=url, attempt=attempt.retry_state.attempt_number)
                    response = await self._client.get(url, **kwargs)
                    response.raise_for_status()  # 4xx/5xx → HTTPStatusError
                    return response.json()
        return None  # pragma: no cover — reraise=True 라 도달 X
