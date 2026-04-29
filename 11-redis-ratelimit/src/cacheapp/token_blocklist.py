"""JWT blocklist — logout 토큰 무효화.

JWT 의 본질적 한계: _stateless_ → 발급된 토큰은 _서버가_ 즉시 무효화 못 함.
해결: _짧은 TTL 의 Redis 블록리스트_ 에 등록 — 만료까지만 거부, 메모리 절약.

흐름:
    POST /auth/logout
        → blocklist.add(jti, exp - now)   ← TTL 자동 만료
    이후 요청에서 토큰 검증 시:
        → if blocklist.contains(jti): raise 401
"""

from __future__ import annotations

from redis.asyncio import Redis


class TokenBlocklist:
    KEY = "blocklist:jti:"

    def __init__(self, client: Redis) -> None:
        self._client = client

    async def add(self, jti: str, ttl_seconds: int) -> None:
        """토큰 만료 시점까지만 보관 — 그 이후엔 자동 정리."""
        if ttl_seconds <= 0:
            return  # 이미 만료된 토큰은 등록 불필요
        await self._client.setex(f"{self.KEY}{jti}", ttl_seconds, "1")

    async def contains(self, jti: str) -> bool:
        return await self._client.exists(f"{self.KEY}{jti}") == 1
