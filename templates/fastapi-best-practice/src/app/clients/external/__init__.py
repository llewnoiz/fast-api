"""외부 HTTP API 클라이언트 자리 — httpx.AsyncClient 기반.

새 외부 의존성마다 한 파일 (`payments_client.py`, `notifications_client.py` 등).
공통: timeout / retry / circuit breaker / 응답 envelope unwrap.
"""
