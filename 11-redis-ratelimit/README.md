# 11 — Redis 캐시 + 분산 락 + Rate Limit

03 의 redis.asyncio + 05 의 docker compose `cache` profile + 09 의 인증을 _진짜 운영_ 수준 패턴으로 발전.

## 학습 목표

- **cache-aside** 패턴 — `get_or_set(key, loader)`
- **TTL + 키 prefix** — 환경/테넌트 분리
- **분산 락** — `SET NX EX`, redis-py `lock()`, 동시성 직렬화
- **Rate Limit** — `fastapi-limiter` (Redis 기반 atomic 카운터)
- **JWT blocklist** — logout 토큰 무효화 (09 떡밥 회수)
- 캐시 무효화 (write-through invalidation)

## 디렉토리

```
11-redis-ratelimit/
├── pyproject.toml          # redis>=5, fastapi-limiter
├── Makefile
├── README.md
├── src/cacheapp/
│   ├── settings.py         # redis_url, cache_prefix, default_ttl
│   ├── cache.py            # Cache class — get/set/get_or_set/invalidate
│   ├── lock.py             # distributed_lock 컨텍스트 매니저
│   ├── token_blocklist.py  # JWT blocklist (09 떡밥)
│   └── main.py             # FastAPI + lifespan + 라우트 (cache/lock/limit)
└── tests/
    ├── conftest.py         # testcontainers Redis
    ├── test_cache.py       # cache-aside 검증
    ├── test_lock.py        # 동시 워커 직렬화 검증
    └── test_app.py         # e2e (cache hit/invalidate, rate limit, lock)
```

## 실행

```bash
cd .. && uv sync && cd 11-redis-ratelimit

# 도커 cache profile 띄우기
cd ../05-infra-compose && make up-cache && cd ../11-redis-ratelimit

make run                   # uvicorn dev
# 다른 터미널
curl http://localhost:8000/items/1     # 첫 — 200ms (외부 hit)
curl http://localhost:8000/items/1     # 두 번째 — <1ms (캐시 hit)
for i in 1 2 3 4; do curl -si http://localhost:8000/limited | head -1; done
# → 200, 200, 200, 429

make all                   # ruff + mypy + pytest (testcontainers 자동)
```

## 다국 언어 비교

| 개념 | 가장 가까운 비교 |
|---|---|
| **`cache.get_or_set`** | Spring `@Cacheable("key")`, NestJS `cache.wrap(key, loader)` |
| **TTL + prefix** | Spring `RedisCacheConfiguration.entryTtl()`, NestJS CacheModule |
| **분산 락** | Spring `RedisLockRegistry`, **Redisson `RLock`**, NestJS `redlock` |
| **Rate Limit** | Spring Cloud Gateway `RequestRateLimiter`, **NestJS `ThrottlerGuard`**, AWS WAF |
| **JWT blocklist** | Spring Security 의 token revocation, Auth0 logout |

## 핵심 개념

### 1) cache-aside 의 _기본 흐름_

```python
async def get_or_set(key, loader, ttl):
    cached = await cache.get(key)
    if cached is not None:
        return cached                    # 1) 캐시 hit
    value = await loader()               # 2) 캐시 miss → 원본
    await cache.set(key, value, ttl)     # 3) 캐시에 저장
    return value
```

**효과** — 우리 데모:
- `/items/1` 첫 호출: 200ms (가짜 외부 API)
- 두 번째: <1ms (Redis 1라운드)
- 외부 API 호출 카운터: 1번만 증가

비교:
- Spring `@Cacheable("items")` 어노테이션 한 줄
- NestJS `cache.wrap("items", () => loader())`

### 2) 키 네이밍 — _prefix + 콜론 구분_

```
app:items:42                    ← 환경 prefix + 도메인 + id
app:user:42:cart                ← 사용자별
prod:rate_limit:ip:1.2.3.4      ← rate limit 키
```

규칙:
- _콜론(:)_ 으로 계층 구분 — Redis 의 _de facto_ 표준
- _prefix_ 로 환경 분리 (`dev:`, `prod:`)
- TTL 항상 명시 — _영원히_ 사는 키 만들지 말 것

### 3) 분산 락 — 동시성 직렬화

```python
async with distributed_lock(redis, f"order:{id}", timeout=5, blocking_timeout=0.1) as got:
    if not got:
        raise HTTPException(429, "다른 요청 처리 중")
    # critical section — 한 번에 하나만
```

**파라미터 의미**:
- `timeout`: 락 _자동 해제_ 시간 (워커 죽었을 때 deadlock 방지)
- `blocking_timeout`: 락 _획득 대기_ 최대 시간 (못 잡으면 False)

**언제 쓰나**:
- 결제 중복 방지 (같은 주문 동시 처리 차단)
- cron leader election (분산 환경에서 한 인스턴스만)
- 캐시 stampede 방지 (rebuild 시 락)

**주의** — 단일 Redis 는 SPOF. 본격적인 분산 환경엔 **Redlock** 알고리즘 (여러 Redis 노드 다수결).

### 4) Rate Limit — `fastapi-limiter`

```python
@app.get(
    "/api/expensive",
    dependencies=[Depends(RateLimiter(times=10, seconds=60))],
)
async def expensive(): ...
```

내부 동작: Lua 스크립트로 Redis 에 _atomic 카운터_ 갱신. 여러 워커/인스턴스 간 _공유_ — 단일 인스턴스 in-memory rate limit 의 한계 해결.

기본은 _IP 기반_ 식별. 사용자 기반은 `identifier` 콜백 커스텀:

```python
async def user_id(request: Request) -> str:
    return request.state.user_id   # 인증 후 미들웨어가 채움

RateLimiter(times=10, seconds=60, identifier=user_id)
```

비교:
- Spring Cloud Gateway `RequestRateLimiter` 토큰 버킷 (Redis 백엔드)
- NestJS `@Throttle(10, 60) @UseGuards(ThrottlerGuard)`
- AWS WAF rate-based rule

### 5) 캐시 무효화 (write-through invalidation)

```python
@app.put("/items/{id}")
async def update_item(id: int, payload: ItemIn):
    await db.update_item(id, payload)
    await cache.invalidate(f"item:{id}")    # ← 다음 read 가 _새 값_ 로드
```

**Phil Karlton**: _"There are only two hard things in Computer Science: cache invalidation and naming things."_

### 6) JWT blocklist — 09 떡밥 회수

```python
# /auth/logout
async def logout(token = Depends(oauth2)):
    payload = decode(token)
    ttl = payload["exp"] - now()
    await blocklist.add(payload["jti"], ttl_seconds=ttl)

# get_current_user 안에서
if await blocklist.contains(payload["jti"]):
    raise 401
```

장점: TTL 자동 만료 — 토큰 _진짜 만료 시점_ 까지만 블록. 메모리 절약.

## 안티패턴

1. **TTL 없는 캐시** — 영원히 살아 메모리 폭발. 항상 `setex` 또는 `EXPIRE`.
2. **`flushall` 운영에서** — 모든 키 삭제. 절대 금지. 무효화는 _패턴 매칭_ 또는 _개별 키_.
3. **rate limit 을 _in-memory_ 딕셔너리로** — 멀티 워커/인스턴스에서 무력. 무조건 Redis (또는 외부 게이트웨이).
4. **분산 락 timeout 너무 짧게** — 작업이 안 끝났는데 다른 워커 진입. 작업 시간 + 안전 마진.
5. **분산 락 timeout 너무 길게** — 워커 죽으면 다른 워커가 그만큼 대기. trade-off.
6. **단일 Redis 로 _금융 트랜잭션_ 동시성 제어** — Redlock 알고리즘 + DB 트랜잭션 결합 필요.
7. **캐시 키에 _전체 객체_ JSON 박기** — 부분 갱신 어려움. 정규화된 키 (`item:42:price`, `item:42:stock`).
8. **rate limit 응답에 `Retry-After` 헤더 누락** — 클라이언트가 _언제 재시도_ 할지 모름. fastapi-limiter 는 자동 추가.
9. **블록리스트만 있고 jti 없는 토큰** — 토큰 자체를 키로 쓰면 길어짐. JWT 발급 시 `jti` claim 포함.

## 직접 해보기 TODO

- [ ] `Cache` 에 `get_many` / `set_many` (pipeline) 추가
- [ ] rate limit 에 `identifier` 커스텀 (인증 사용자 ID 기반)
- [ ] `RateLimiter` 의 `Retry-After` 헤더 — curl 로 응답 헤더 확인
- [ ] `distributed_lock` 안의 `timeout` 을 0.5 로 줄이고 `await asyncio.sleep(1)` — 락 만료 후 다른 워커 진입 시뮬레이션
- [ ] cache stampede 방지 — `get_or_set` 안에서 `distributed_lock` 으로 _한 워커만 rebuild_
- [ ] `TokenBlocklist` 를 09 의 `get_current_user` 에 통합 (실제 logout 라우트)
- [ ] Redis pub/sub 으로 _캐시 무효화 broadcast_ (다중 인스턴스)

## 다음 단계

**12 — 서버간 통신 + 관측가능성**. httpx.AsyncClient 재사용, 재시도(`tenacity`), 회로 차단기, correlation-id 미들웨어, OpenTelemetry, Prometheus 메트릭.
