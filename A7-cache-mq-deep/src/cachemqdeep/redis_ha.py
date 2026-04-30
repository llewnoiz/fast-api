"""Redis HA — Sentinel / Cluster 클라이언트 패턴 (학습용 노트).

운영 Redis 토폴로지:

1. **Standalone** ── 단일 노드. 개발/소규모. 노드 죽으면 _서비스 중단_.
2. **Sentinel** ── master 1 + replica N + sentinel 3+. master 죽으면 자동 failover.
   클라이언트는 _master 주소를 sentinel 에 물어봄_.
3. **Cluster** ── 16384 슬롯을 N 노드에 분산 (sharding). 노드 추가/제거로 _수평 확장_.
   클라이언트는 _슬롯 → 노드_ 매핑 캐시. MOVED / ASK 응답 시 갱신.

**선택 가이드**:
- 데이터 < 메모리 / 단일 region → **Sentinel** (HA)
- 데이터 > 메모리 / 멀티 region → **Cluster** (sharding)
- 둘 다 필요 → AWS ElastiCache "Cluster mode enabled" / Valkey OSS / Redis Enterprise

**핵심 제약**:
- Cluster 에선 _다중 키 명령_ (`MGET`, `MSET`, `EVAL` 등) 이 _같은 슬롯_ 에 있어야 동작.
  → Hash tag 사용: `{user:42}:profile`, `{user:42}:cart` ── 중괄호 안 부분이 슬롯 결정.
- Lua/Redlock 같은 _노드 간 일관성 의존_ 패턴은 cluster 에서 _주의_.

본 모듈은 _코드 데모_ 가 아니라 _패턴 노트_. 운영 코드 예시:

```python
# Sentinel
from redis.asyncio.sentinel import Sentinel
sentinel = Sentinel([("sentinel-1", 26379), ("sentinel-2", 26379)], socket_timeout=0.5)
master = sentinel.master_for("mymaster", decode_responses=True)
replica = sentinel.slave_for("mymaster", decode_responses=True)  # 읽기 전용

# Cluster
from redis.asyncio.cluster import RedisCluster
rc = RedisCluster(host="cluster-node-1", port=7000)
await rc.set("{user:42}:profile", "...")
```

비교:
    Spring `LettuceConnectionFactory` + `RedisSentinelConfiguration` / `RedisClusterConfiguration`
    NestJS `redis-cluster-client` 또는 ioredis Cluster 모드
    AWS ElastiCache — Sentinel/Cluster 양쪽 매니지드, _failover 자동_
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class HashTag:
    """Cluster 호환 키 빌더 — 같은 hash tag 끼리 _같은 슬롯_.

    예:
        tag = HashTag("user:42")
        tag.field("profile")  # → "{user:42}:profile"
        tag.field("cart")     # → "{user:42}:cart"
    """

    name: str

    def field(self, field: str) -> str:
        return f"{{{self.name}}}:{field}"
