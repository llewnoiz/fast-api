"""ResilientClient — httpx + tenacity + purgatory. 12 단계에서 추출."""

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


def _is_retryable(exc: BaseException) -> bool:
    if isinstance(exc, httpx.TimeoutException | httpx.NetworkError):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code >= 500
    return False


def make_breaker_factory(threshold: int = 3, recovery_s: float = 5.0) -> AsyncCircuitBreakerFactory:
    return AsyncCircuitBreakerFactory(default_threshold=threshold, default_ttl=int(recovery_s))


class ResilientClient:
    """재시도 + 회로 차단기 적용 httpx 래퍼."""

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
                    response.raise_for_status()
                    return response.json()
        return None  # pragma: no cover
