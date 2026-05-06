"""Redis 기반 refresh token 저장 — jti 화이트리스트 + revoke.

저장 형식:
    key:  refresh:{jti}
    val:  {user_id} (또는 username)
    TTL:  refresh_expire_days × 86400

흐름:
    1) login → create_refresh_token (jti 생성) + `add_jti(jti, sub)` Redis 저장
    2) /auth/refresh → decode_refresh_token + `is_valid(jti)` 검사 → 유효하면 새 페어 발급 +
       옛 jti `revoke(jti)` (rotation)
    3) /auth/logout → 현재 jti `revoke(jti)`
    4) 전체 logout (모든 디바이스) → `revoke_all_for(sub)` ── KEYS / SCAN 으로 user 의 모든 refresh 삭제

Rotation 의 보안 가치:
    공격자가 _훔친 refresh_ 를 사용하면, _합법 사용자_ 가 다음 refresh 시도 시 _이미 revoke_ 된
    것을 발견 → 의심 활동 알람 + 모든 세션 강제 logout 가능.

대안 (운영 옵션):
    - DB (`refresh_tokens` 테이블): 영속, audit log 자연. 학습용 Redis 가 가벼움.
    - 그냥 stateless (JWT 만): rotation 불가, revoke 불가. 보안 약함.
"""

from __future__ import annotations

from redis.asyncio import Redis

KEY_PREFIX = "refresh:"


def _key(jti: str) -> str:
    return f"{KEY_PREFIX}{jti}"


async def add_jti(redis: Redis, *, jti: str, subject: str, ttl_seconds: int) -> None:
    """login / refresh 시 호출 — _발급_ 된 jti 를 Redis 에 _화이트리스트_ 등록."""
    await redis.setex(_key(jti), ttl_seconds, subject)


async def is_valid(redis: Redis, *, jti: str, subject: str) -> bool:
    """refresh 시도 시 호출 — _아직 살아있고_ subject 가 일치하는지."""
    stored = await redis.get(_key(jti))
    return stored == subject


async def revoke(redis: Redis, *, jti: str) -> None:
    """logout / rotation 시 호출 — 단일 jti 삭제."""
    await redis.delete(_key(jti))


async def revoke_all_for(redis: Redis, *, subject: str, batch: int = 100) -> int:
    """`logout-all-devices` — subject 의 _모든_ refresh 삭제.

    SCAN + 값 비교 — 큰 user 풀에서도 안전 (KEYS 는 _운영 차단_).
    반환: 삭제된 jti 수.
    """
    deleted = 0
    cursor = 0
    while True:
        cursor, keys = await redis.scan(
            cursor=cursor, match=f"{KEY_PREFIX}*", count=batch
        )
        if keys:
            # MGET 으로 한 번에 값 조회 → 일치하는 키만 삭제
            values = await redis.mget(keys)
            to_delete = [k for k, v in zip(keys, values, strict=False) if v == subject]
            if to_delete:
                deleted += await redis.delete(*to_delete)
        if cursor == 0:
            break
    return deleted
