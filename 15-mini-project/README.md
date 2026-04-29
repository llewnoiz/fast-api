# 15 — tender (통합 미니 프로젝트)

🎓 **커리큘럼의 졸업 작품**. 04~14 의 _모든 패턴_ 이 한 앱에서 어떻게 결합되는지 보여줍니다.

## 학습 목표

이 단계는 _새 개념 도입_ 이 아니라 **이미 배운 모든 것의 통합**.

- **fastapi-common** (14) 을 _의존성_ 으로 사용 — 사내 패키지 배포 시뮬
- **계층화** (API / Domain / Repository / Cache / Events) — 클린 아키텍처
- **풀 스택** — 인증 + DB 트랜잭션 + Redis 캐시 + outbox + v1/v2
- **시나리오 e2e 테스트** — 한 주문 흐름이 _모든 컴포넌트_ 통과

## 아키텍처

```
                                   클라이언트
                                       │
                                       ▼
                  ┌─────────────────────────────────────────┐
                  │ FastAPI 앱 (tender)                      │
                  │                                          │
                  │  ┌─ Middleware (14 fastapi-common) ──┐  │
                  │  │  CorrelationIdMiddleware (12)      │  │
                  │  │  Exception Handlers     (07)       │  │
                  │  └────────────────────────────────────┘  │
                  │                                          │
                  │  ┌─ API ─────────────────────────────┐  │
                  │  │  /auth/token       (09 JWT)        │  │
                  │  │  /v1/orders        (07 deprecated) │  │
                  │  │  /v2/orders        (07 현재)       │  │
                  │  │  /healthz                          │  │
                  │  └────────────────────────────────────┘  │
                  │                ▼                         │
                  │  ┌─ Domain ──────────────────────────┐  │
                  │  │  UnitOfWork (10)                   │  │
                  │  │  ├─ UserRepo  ├─ OrderRepo         │  │
                  │  │  └─ OutboxRepo                     │  │
                  │  └────────────────────────────────────┘  │
                  └────────┬─────────────┬──────────────────┘
                           │             │
                  ┌────────▼─────┐  ┌────▼─────────┐
                  │ Postgres     │  │ Redis        │
                  │ (10 SQLAlc)  │  │ (11 cache)   │
                  └──────────────┘  └──────────────┘
```

## 디렉토리

```
15-mini-project/
├── pyproject.toml          # fastapi-common 의존 + 풀 스택
├── alembic.ini + alembic/  # users + orders + outbox_events 마이그레이션
├── Makefile                # make run / migrate / test
├── README.md
├── src/tender/
│   ├── settings.py         # 04 — pydantic-settings
│   ├── errors.py           # 07 — 도메인 예외 + fastapi-common.DomainError 베이스
│   ├── auth.py             # 09 — JWT + bcrypt + get_current_user + require_role
│   ├── models.py           # 10 — User / Order / OutboxEvent
│   ├── schemas.py          # 07 — v1/v2 분리 Pydantic
│   ├── repository.py       # 10 — UserRepo / OrderRepo / OutboxRepo
│   ├── uow.py              # 10 — UnitOfWork 트랜잭션 경계
│   ├── cache.py            # 11 — OrderCache (cache-aside + invalidation)
│   ├── api/
│   │   ├── auth.py         # POST /auth/token
│   │   ├── v1.py           # /v1/orders (deprecated 헤더 자동)
│   │   └── v2.py           # /v2/orders (현재)
│   └── main.py             # 04~14 모두 결합
└── tests/
    ├── conftest.py         # testcontainers Postgres + Redis + Alembic 자동
    └── test_scenario.py    # 6개 e2e 시나리오
```

## 단계별 패턴 적용 매핑

| 단계 | 어디서 활용 |
|---|---|
| **04** Hello | `main.py` 의 `create_app()` + `lifespan` |
| **05** Compose | 운영 시 `db` + `cache` profile 사용 (테스트는 testcontainers) |
| **06** async | 모든 라우트 / Repo / Cache 가 async |
| **07** envelope/에러/버전 | `fastapi-common.ApiEnvelope` + v1/v2 분리 + Deprecation 헤더 |
| **08** 테스팅 | testcontainers + dependency_overrides 패턴 그대로 |
| **09** 인증 | `auth.py` JWT + bcrypt + OAuth2PasswordBearer |
| **10** DB | SQLAlchemy 2.0 + Alembic + UoW + savepoint 가능 |
| **11** Redis | `OrderCache` cache-aside + invalidation |
| **12** 관측가능성 | `fastapi-common` 의 `CorrelationIdMiddleware` |
| **13** outbox | `OutboxRepo.record` — 같은 트랜잭션 안에서 이벤트 적재 (relay 워커는 별도) |
| **14** 공통 패키지 | `fastapi-common` 을 _의존성_ 으로 import |

## 실행

```bash
cd .. && uv sync && cd 15-mini-project

# 도커 인프라
cd ../05-infra-compose && make up && cd ../15-mini-project

# 마이그레이션
make migrate

# 서버
make run
# → http://localhost:8000/docs
```

### 시나리오 — curl 따라가기

```bash
# 1) 사용자 등록 (학습용 — 직접 DB INSERT 또는 테스트 fixture 통해)
# 2) 로그인
TOKEN=$(curl -s -X POST http://localhost:8000/auth/token \
    -d 'username=alice&password=alice123' | jq -r .access_token)

# 3) v2 주문 생성
curl -s -X POST http://localhost:8000/v2/orders \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"sku":"PEN-001","quantity":3}' | jq

# 4) 같은 주문 GET — 첫 호출 DB, 두 번째 캐시
curl -s http://localhost:8000/v2/orders/1 -H "Authorization: Bearer $TOKEN" | jq

# 5) v1 (deprecated 헤더)
curl -si -X POST http://localhost:8000/v1/orders \
    -H "Authorization: Bearer $TOKEN" \
    -d '{"item":"Pencil","quantity":1}' | head -10
```

## 시나리오 e2e — 6 케이스

`tests/test_scenario.py` 가 _모든 패턴_ 결합을 검증:

1. **`test_full_order_flow`** — 등록 → 로그인 → v2 주문 → 응답 envelope + correlation-id + 캐시
2. **`test_unauthorized_returns_envelope`** — 토큰 없음 → 401 + envelope
3. **`test_invalid_token_envelope`** — 위조 토큰 → 401 + envelope
4. **`test_v1_has_deprecation_headers`** — v1 응답에 `Deprecation/Sunset/Link` 자동
5. **`test_validation_422_envelope`** — sku 패턴 위반 → 422 + envelope
6. **`test_out_of_stock_409_envelope`** — `DISCONTINUED-001` → 409 + `ORDER_OUT_OF_STOCK`

## fastapi-common 활용 요약

```python
from fastapi_common import (
    ApiEnvelope,                       # 응답 envelope (07)
    DomainError, ErrorCode,            # 도메인 예외 베이스 (07)
    install_correlation_middleware,    # X-Request-ID (12)
    install_exception_handlers,        # 4단 핸들러 (07)
    configure_logging,                 # structlog dev/prod (04/12)
    success,                           # envelope 헬퍼
)

# tender 도메인 예외는 fastapi_common.DomainError 상속
class OrderNotFoundError(DomainError):
    def __init__(self, order_id: int) -> None:
        super().__init__(
            code="ORDER_NOT_FOUND",
            message=f"order {order_id} not found",
            status=404,
        )
```

이게 사내 _라이브러리 사용_ 의 실제 모습 — 14 가 _진짜 가치_ 를 발휘하는 자리.

## 안티패턴 (졸업 단계 종합)

1. **모든 로직을 라우트 함수에 직접** — Domain / Repository 계층 분리.
2. **outbox 안 쓰고 라우트에서 _직접_ Kafka.send()** — DB commit 후 Kafka 실패 시 _데이터 불일치_. 항상 outbox + relay.
3. **공통 패키지 (fastapi-common) 변경 후 사용 측 _버전 안 올림_** — 의존성 캐시 충돌. SemVer + CHANGELOG.
4. **테스트가 _느린 e2e_ 만** — unit / integration / e2e 3계층 균형.
5. **lifespan 안에서 _블로킹_ 작업** — 앱 부팅 지연. async 또는 _빠른 실패_ (11 의 conn_retries=0).
6. **운영에서 `--reload`** — 파일 감시 오버헤드.
7. **`.env` 커밋** — 시크릿 유출. `.env.example` 만 커밋.

## 부하 테스트 — 다음 단계 가이드

`locust` 또는 `k6` 로 _진짜_ 측정:

```bash
# locust 설치 후
locust -f tests/load.py --host http://localhost:8000

# 시나리오:
# - 동시 사용자 100 명이 1분 동안 주문 생성 + 조회
# - sync 라우트 vs async 라우트 처리량 비교 (06 단계 부하 비교 패턴)
# - 캐시 hit rate 측정 (Prometheus 메트릭 활용 — 12 단계)
```

## 끝!

축하합니다 — **15 단계 + 부록 A1 (선택) 의 학습 여정 완주**.

| # | 단계 | 핵심 |
|---|---|---|
| 01 | python-basics | Python 기본, 컴프리헨션, 구조 분해 |
| 02 | package-structure | src layout, pyproject.toml, ruff/mypy |
| 03 | libraries-tour | pydantic, httpx, orjson, jsonpath, structlog, dotenv |
| 04 | fastapi-hello | FastAPI 앱, OpenAPI, settings |
| 05 | infra-compose | Docker Compose 인프라 |
| 06 | async-deep | asyncio 심화, sync 안티패턴 |
| 07 | request-error-version | envelope, 에러, v1/v2 |
| 08 | testing | pytest + testcontainers |
| 09 | auth | JWT, OAuth2, RBAC |
| 10 | db-transaction | SQLAlchemy 2.0, Alembic, UoW |
| 11 | redis-ratelimit | cache-aside, 분산 락, rate limit |
| 12 | service-comm-observability | 재시도, 회로차단기, OTel, Prometheus |
| 13 | kafka-queue | aiokafka, arq, outbox |
| 14 | shared-package | fastapi-common 라이브러리 + 사내 배포 |
| **15** | **mini-project** | **_모든 것의 결합_** ✅ |

이제 _실무 FastAPI 서비스_ 를 처음부터 끝까지 만들 수 있습니다. 부록 A1 (i18n) 은 선택.
