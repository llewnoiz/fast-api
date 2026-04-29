# 학습 진행 상황 (이어 작업용 노트)

> **내일 시작할 때**: 새 Claude 세션에서 이 파일을 보여주거나 "STATUS.md 보고 ..." 라고 말하면 됨.

마지막 작업: 2026-04-29 — **🎓 15 단계 완료. 커리큘럼 _전체_ 완주!**

---

## 🎓 졸업

**FastAPI + Python 학습 커리큘럼 본편 (15단계) 완주.**

총 누적 테스트: **210**
- 도커가 필요한 통합/e2e 테스트가 약 60% — testcontainers 자동 셋업
- 단위 테스트는 도커 없이 실행 가능
- 일부 단계는 데모 실행 (uvicorn + curl) 으로도 검증

이제 만들 수 있는 것:
- 실무급 FastAPI 마이크로서비스 (인증 / DB / 캐시 / 메시지큐 / 관측가능성)
- 사내 공통 라이브러리 (`fastapi-common` 패턴)
- 3계층 테스트 (unit / integration / e2e)
- Docker Compose 기반 로컬 개발환경
- Alembic 마이그레이션 + Unit of Work 트랜잭션 경계

다음 단계 후보:
- **A1 i18n** (부록) — Babel + gettext + Accept-Language 미들웨어
- **부하 테스트** — 15 의 tender 위에 locust 시나리오
- **K8s 매니페스트** — 05 의 docker-compose 를 _Helm_ 또는 raw YAML 로
- **CI/CD 파이프라인** — GitHub Actions + 14 의 패키지 자동 배포

---

## 진행 체크

| # | 단계 | 상태 |
|---|---|---|
| 01 | python-basics | ✅ 완료 (60 tests) |
| 02 | package-structure | ✅ 완료 (18 tests) |
| 03 | libraries-tour | ✅ 완료 (17 tests) |
| 04 | fastapi-hello | ✅ 완료 (14 tests) |
| 05 | infra-compose | ✅ 완료 (compose 문법, 도커 실제 검증은 사용자 몫) |
| 06 | async-deep | ✅ 완료 (8 tests) |
| 07 | request-error-version | ✅ 완료 (9 tests) |
| 08 | testing | ✅ 완료 (21 tests) |
| 09 | auth | ✅ 완료 (17 tests) |
| 10 | db-transaction | ✅ 완료 (10 tests) |
| 11 | redis-ratelimit | ✅ 완료 (10 tests) |
| 12 | service-comm-observability | ✅ 완료 (7 tests) |
| 13 | kafka-queue | ✅ 완료 (4 tests) |
| 14 | shared-package | ✅ 완료 (9 tests) |
| **15** | **mini-project** | ✅ **완료!** (6 e2e tests, fastapi-common + 04~14 모두 결합) |
| A1 | i18n (선택) | ⚪ 부록 |

총 누적 테스트: **210** (60+18+17+14+8+9+21+17+10+10+7+4+9+6)
**🎓 커리큘럼 본편 완주!**

전체 커리큘럼: [`/Users/hyunmin.song/.claude/plans/fast-api-python-tender-key.md`](file:///Users/hyunmin.song/.claude/plans/fast-api-python-tender-key.md)

## 1단계 완료 — `01-python-basics/`

기본 학습:
- `s01_types.py` — 타입 힌트, Optional, 컬렉션 힌트
- `s02_collections.py` — list/tuple/dict/set + **컴프리헨션 STEP 1~7 build-up** (사용자 질문에 따라 확장)
- `s03_control_flow.py` — if/for/while-else/match(3.10+)/예외
- `s04_functions.py` — 가변·키워드 인자, PEP 695 데코레이터
- `s05_classes.py` — 클래스, dataclass, Enum, Protocol(duck typing)
- `s06_modules.py` — 모듈/패키지/import (사용자가 try/except 폴백을 단순화함)
- `s07_unpacking.py` — **구조 분해/결합 STEP 1~7** (사용자 질문에 따라 확장, Node/JS 비교 중심)
- `tests/test_basics.py` — 60개 pytest 통과

세션 중 **사용자가 추가 설명을 요구했던 주제** (다시 헷갈리면 README 참고):
- 컴프리헨션 — `if` 의 두 가지 위치 (filter vs 표현식 자리 삼항)
- `zip` — 리액티브 X, 그냥 동기 컬렉션 짝짓기
- `while/else` — `while` 에 붙은 else (break 없이 끝났을 때만 실행)
- `match` 의 `case ... if ...` (guard) + `case _:` (와일드카드)
- 구조 분해 / 결합 — Node `const {a, b} = obj` 의 부재 + 4가지 대안
- `try/except/else/finally` 4단 + `raise X from Y` 예외 체인
- `pass` — 빈 블록을 표현하는 키워드 (Python 의 `{}` 자리)

## 2단계 완료 — `02-package-structure/`

`greeter` 미니 라이브러리 + CLI 로 패키지 구조 학습:
- src layout (`src/greeter/`)
- `pyproject.toml` PEP 621 + `[project.scripts]` 콘솔 스크립트 등록
- 절대 vs 상대 import
- 순환 import 회피 3가지 (`circular_demo.py` 주석)
- ruff / mypy / pre-commit 도입 — 루트 `.pre-commit-config.yaml`

핵심 함정 (디버깅함): **워크스페이스 멤버는 자동 install 안 됨**.
루트 `pyproject.toml` 의 `[project.dependencies]` 에 멤버 이름 추가 + `[tool.uv.sources]` 로 `{ workspace = true }` 명시 필요.

## 3단계 완료 — `03-libraries-tour/`

자주 쓰는 라이브러리 7개 투어 + Node/Kotlin/TS 비교:
- t01 **pydantic v2** — 모델/검증, TS zod 와 가장 가까움
- t02 **httpx** — sync/async, asyncio.gather 로 병렬 호출, MockTransport
- t03 **orjson** — datetime/UUID 자동 직렬화, bytes 반환, 빠름
- t04 **jsonpath-ng** + deep merge — `{**a, **b}` 의 얕은 병합 한계 보완
- t05 **datetime + zoneinfo + dateutil** — naive vs aware 함정, ISO 8601, 타임존 변환
- t06 **structlog** — MDC 패턴, 개발(콘솔)/운영(JSON) 분리
- t07 **python-dotenv + pydantic-settings** — 12-factor 환경변수, 타입 안전 설정

세션 중 디버깅한 부분 (메모용):
- `EmailStr` 은 `pydantic[email]` extra 필요
- `jsonpath_ng.ext` 의 `?(@.active)` 는 _존재 검사_, `?(@.active==true)` 가 truthy 비교
- `orjson` 기본은 set 미지원 (OPT_PASSTHROUGH 필요) — 데모는 list 로
- `dateutil` 은 stub 별도 (`types-python-dateutil` 추가)
- `uv sync` 는 _루트에서_ 만 — 멤버 디렉토리에서 실행하면 dev 도구 사라짐

## 환경 / 도구 (확정된 선택)

- Python 3.12 (uv 가 자동 다운로드, `.python-version` 에 고정)
- 패키지 매니저: **uv** (poetry/pip 아님)
- 워크스페이스 구조: 루트 `pyproject.toml` + 단계별 멤버
- 인프라: 05단계에서 단일 Docker Compose 도입 예정 (Postgres/Redis/Kafka, profiles 토글)
- 사용자 배경: **Java/Spring · Kotlin · Go · TypeScript · JavaScript · PHP · C/C++** 경험, Python 거의 처음
  - 03 단계부터 README/주석에서 주제별로 _가장 와닿는 한두 언어_ 와 비교 (전부 나열 X):
    - 타입/구조분해/Pydantic → **TypeScript**
    - dataclass / null safety / pattern matching → **Kotlin**
    - async / 코루틴 → **Kotlin coroutines**, TS async/await
    - 이벤트 루프 / I/O 모델 → **Node**
    - 패키지 매니저 → **npm/pnpm**, Cargo
    - 메모리/참조/가변 기본값 함정 → **C/C++**
    - DI/AOP/데코레이터 → **Spring**
    - 구조적 타이핑/Protocol → **Go**, TS
  - 01/02 의 기존 Java·Go 비교는 그대로 유지(개정 X)

## 4단계 완료 — `04-fastapi-hello/`

진짜 FastAPI 웹 서버 등장:
- `app/main.py` — `create_app()` 팩토리 + `lifespan` 컨텍스트 매니저
- `app/settings.py` — `pydantic-settings` + `@lru_cache` 싱글톤 + `Depends(get_settings)`
- `app/logging_setup.py` — 환경별 structlog (dev=콘솔 / prod=JSON)
- `app/routers/` — health (liveness/readiness), items (path+query 파라미터), echo (POST 본문 검증)
- 14 tests + uvicorn 으로 _실제_ 7가지 엔드포인트 응답 확인

세션 중 디버깅한 부분 (메모용):
- FastAPI 0.111+ 부터 `ORJSONResponse` 가 _deprecated_ — Pydantic 이 직접 JSON bytes 직렬화. 학습 의도 코멘트로 보존하고 코드에선 제거.
- `@app.on_event("startup")` 도 deprecated — `lifespan` 컨텍스트 매니저가 표준.
- 테스트는 `httpx.AsyncClient + ASGITransport` 사용 (진짜 네트워크 X).

## 5단계 완료 — `05-infra-compose/` + 루트 인프라

루트에 도커 인프라 (이후 모든 단계 재사용):
- `docker-compose.yml` — Postgres 16 / Redis 7 / Redpanda(Kafka) / FastAPI app, 4가지 profile (db/cache/kafka/app/all)
- `.env.example` — 자격증명 템플릿 (POSTGRES_*, REDIS_*, KAFKA_*, APP_*)
- `.dockerignore` — venv/캐시/.env 제외

학습 자료 디렉토리:
- `05-infra-compose/Dockerfile` — uv builder + python:3.12-slim runner, non-root, HEALTHCHECK
- `05-infra-compose/Makefile` — make up / down / ps / logs / psql / redis-cli / build / up-app
- `05-infra-compose/README.md` — K8s/Spring/NestJS 비교, 운영 컨테이너 안티패턴 9개

서비스 호스트명 규칙:
- 컨테이너 _안에서_: 서비스 이름 (`db`, `cache`, `kafka`)
- 호스트(macOS) _에서_: `localhost:매핑포트`

세션 중 결정/메모:
- compose 위치: 루트 (06+ 가 다 재사용) → `05-infra-compose/` 는 _학습 자료_ 만
- Kafka 대신 Redpanda — Zookeeper 불필요로 가벼움 (Kafka API 호환)
- profile 기본 (no flag) 은 _아무것도 안 띄움_ — 의도적. `--profile db --profile cache` 등 명시
- 이번 세션에 도커 데몬이 꺼져 있어 `docker compose config --quiet` 로 _문법 검증만_ 통과 확인. 실제 `up` / `make psql` / `make redis-cli` 검증은 다음 세션에 도커 켜진 상태에서.

## 6단계 완료 — `06-async-deep/`

asyncio 심화 7개 데모 build-up:
- t01 event loop — 코루틴 객체 / await / asyncio.run
- t02 concurrent — gather / TaskGroup (3.11+) / return_exceptions
- t03 antipattern — sync I/O 가 async 를 죽이는 _시각적 증명_ (201ms vs 611ms)
- t04 executor — asyncio.to_thread (sync I/O), ProcessPoolExecutor (CPU)
- t05 timeout/cancel — asyncio.timeout (3.11+), Task.cancel, ExceptionGroup
- t06 async iter — async generator + 변환 파이프라인
- t07 FastAPI sync vs async 라우트 부하 비교 (동시 50개: 419ms vs 211ms)

세션 중 메모:
- **t07 테스트 한계**: ASGITransport 인메모리 환경에선 sync/async 차이가 작아 (이벤트 루프가 sync 라우트도 효율적 처리) 부하 _차이 자동 검증_ 은 신뢰 어려움. _상태 검증_ + _make demo 실행_ 으로 분리.
- mypy 가 `asyncio.gather` 가변 인자에서 list 가 아니라 tuple 추론 → `list(results)` 로 명시 변환.
- 117개 누적 테스트 모두 회귀 통과.

## 7단계 완료 — `07-request-error-version/`

응답 envelope + 전역 에러 핸들러 + API 버전 관리:
- `errver/envelope.py` — `ApiEnvelope[T]` (PEP 695 제네릭)
- `errver/errors.py` — `ErrorCode(StrEnum)` + `DomainError` + 도메인 구체 예외
- `errver/handlers.py` — 도메인/검증/HTTP/미처리 4단 핸들러, 모두 envelope 으로 통일
- `errver/api/v1/orders.py` — 구식 (`item`), 모든 응답에 Deprecation/Sunset/Link 헤더 자동
- `errver/api/v2/orders.py` — 현재 (`sku` + `created_at`), OpenAPI `responses={...}` examples
- 9 tests 통과 + uvicorn 으로 6가지 시나리오 (정상/404/422/409/201/v1 헤더) 직접 확인

세션 중 디버깅한 부분 (메모용):
- **패키지 이름 충돌**: 04 와 07 둘 다 `src/app/` 으로 패키지 이름이 같아 _하나의 venv_ 에서 충돌. 07 을 `src/errver/` 로 변경해 해결. **이후 단계마다 _고유 이름_ 사용**: 08=`testapp`, 09=`auth`, 10=`db`, 11=`cache`, 12=`obs`, 13=`mq`, 14=`shared`, 15=`tender` 같은 식.
- httpx 헤더는 _소문자 정규화_ 됨 (HTTP/1.1 RFC). 테스트에서 `headers["Sunset"]` 이 아니라 `headers["sunset"]`.
- `class X(str, Enum)` 패턴은 _구식_ — `class X(StrEnum)` 가 표준 (3.11+).
- Pydantic v2 + PEP 695 제네릭 (`class ApiEnvelope[T](BaseModel)`) 정상 동작.

## 8단계 완료 — `08-testing/`

3계층 테스트 (unit / integration / e2e) + testcontainers + dependency_overrides + 커버리지:
- `testapp/repository.py` — Postgres async (psycopg 3) + 순수 함수 `discounted_price`
- `testapp/cache.py` — Redis HitCounter
- `testapp/main.py` — FastAPI + Depends 주입 (Settings → DB conn → Repo)
- `tests/conftest.py` — _도커 자동 감지_ + session-scope testcontainers + dependency_overrides
- 21 tests (10 unit + 7 integration + 4 e2e), 94% 커버리지
- 두번째 실행부턴 testcontainers 재사용으로 26초 → 2.4초

세션 중 메모:
- **dev 그룹은 _루트_ 에**: 멤버 `[dependency-groups]` 는 루트 sync 에서 미활성. testcontainers/pytest-cov 도 루트에.
- **testcontainers Redis 의 DeprecationWarning** — 라이브러리 내부 문제, 우리 코드 책임 아님.
- **도커 자동 감지 패턴**: `docker.from_env(timeout=2).ping()` 시도 → 실패하면 `pytest.skip`. CI 의 빠른 PR 잡 / 야간 통합 잡 분리에 유용.
- 도커 켜져 있을 때 testcontainers 가 진짜 Postgres/Redis 띄움 — 마이그레이션·CHECK 제약·INCR 등 _진짜 동작_ 검증.

## 9단계 완료 — `09-auth/`

JWT + OAuth2 password flow + RBAC + CORS:
- `authapp/security.py` — bcrypt 해싱 + JWT 발급/검증 (HS256)
- `authapp/users.py` — 인메모리 user 저장 (alice/bob/carol 시드)
- `authapp/deps.py` — `OAuth2PasswordBearer` + `get_current_user` + `require_role(*roles)` 팩토리
- `authapp/routers/{auth,me,admin}.py` — POST /auth/token, GET /me, GET /admin/secret, GET /audit/log
- `authapp/main.py` — CORS 미들웨어 + 라우터 등록
- 17 tests + 5가지 시나리오 실서버 확인 (없음→401 / 로그인 / /me / admin OK / non-admin 403 / 잘못된 비번 401)

세션 중 메모:
- **bcrypt 4.1+ 와 passlib 1.7.4 호환 깨짐** → `bcrypt<4.1` 핀.
- `passlib` 의 `crypt` 모듈 DeprecationWarning (Python 3.13 에서 제거 예정) — 우리 책임 아님.
- `OAuth2PasswordRequestForm` 은 _form-data_ (application/x-www-form-urlencoded). JSON 으로 보내면 422.
- 401 vs 403 구분 — 인증 우선, 그 다음 인가.
- `WWW-Authenticate: Bearer` 헤더 — 401 일 때 표준 응답.

## 10단계 완료 — `10-db-transaction/`

SQLAlchemy 2.0 async + Alembic + Unit of Work:
- `dbapp/models.py` — `Mapped[T]` + `mapped_column` 새 스타일, User 1:N Order
- `dbapp/database.py` — `make_engine` + `make_sessionmaker`
- `dbapp/repository.py` — UserRepository / OrderRepository, **`selectinload`** 로 N+1 회피
- `dbapp/uow.py` — `async with` 자동 commit/rollback, `__aenter__/__aexit__`
- `dbapp/main.py` — `Request` 매개변수로 app.state.sessionmaker 자동 주입
- `alembic/` — env.py async metadata + 초기 스키마 마이그레이션
- 10 tests + savepoint 부분 롤백 검증
- testcontainers 가 Alembic 자동 적용

세션 중 디버깅한 부분:
- **session-scope async fixture + function-scope event loop 충돌** — engine/sessionmaker 를 _function scope_ 로 변경 (컨테이너만 session). pytest-asyncio 1.x 에서 흔한 함정.
- `Depends(lambda r: r.app.state.sessionmaker)` 안 됨 — `Request` 매개변수로 받아야 자동 주입.
- **같은 UoW 안에서 IntegrityError 후 다음 작업 → PendingRollbackError**. 업무 단위(UoW) 분리가 정석.
- `expire_on_commit=False` 가 FastAPI 친화 — 응답 직렬화 시 detached 에러 방지.

## 11단계 완료 — `11-redis-ratelimit/`

Redis 캐시 + 분산 락 + Rate Limit + JWT blocklist:
- `cacheapp/cache.py` — `Cache` 클래스 + `get_or_set(loader)` cache-aside
- `cacheapp/lock.py` — `distributed_lock` async 컨텍스트 매니저 (`SET NX EX`)
- `cacheapp/ratelimit.py` — _직접_ 작성한 fixed-window RateLimiter (Redis pipeline INCR + EXPIRE NX)
- `cacheapp/token_blocklist.py` — JWT jti blocklist (TTL 자동 만료)
- `cacheapp/main.py` — lifespan + 라우트 (cache/lock/limit 데모)
- 10 tests (cache 4 + lock 2 + e2e 4) testcontainers Redis 자동

세션 중 디버깅한 부분:
- **`fastapi-limiter` PyPI 0.2.0 은 _다른_ 패키지** (동명이인). 진짜 long2ice 의 0.1.6 도 있지만 _직접 작성_ 이 학습 가치 ↑. 외부 의존성 _제거_, fixed-window 알고리즘 직접.
- **`httpx ASGITransport` 는 lifespan 자동 트리거 X** → `asgi-lifespan` 의 `LifespanManager` 필요.
- pipeline `incr + expire(nx=True)` 로 _첫 호출 한 번만_ TTL 설정 (race 줄임).
- `Retry-After` 헤더 — rate limit 응답에 표준 포함.

## 12단계 완료 — `12-service-comm-observability/`

마이크로서비스 운영 패턴 5종:
- `obsapp/correlation.py` — `X-Request-ID` 미들웨어 + structlog contextvars
- `obsapp/http_client.py` — `ResilientClient` (httpx + tenacity 재시도 + purgatory 회로차단기)
- `obsapp/observability.py` — OTel TracerProvider (FastAPI/httpx 자동 계측) + Prometheus `/metrics`
- `obsapp/main.py` — lifespan 에서 AsyncClient 한 번 + 라우트 (relay/healthz/flaky)
- 7 tests — correlation 2 + retry/breaker 4 + metrics 1, MockTransport 로 결정적

세션 중 디버깅한 부분:
- **`fastapi-limiter` 0.2.0 동명이인 패키지** (11 단계 메모) → 12 에선 `pybreaker` 대신 **`purgatory`** 선택 (async 친화).
- `tenacity.retry_if_exception` 으로 _콜러블 predicate_ 사용 (5xx만 재시도, 4xx 즉시 실패).
- ConsoleSpanExporter 가 _프로세스 종료 후_ stdout 닫힌 상태에서 호출되어 무해한 ValueError 출력 — 테스트 결과엔 영향 없음.
- prometheus-fastapi-instrumentator 의 `expose(...)` 가 라우터에 `/metrics` 자동 추가.
- 미들웨어 등록 _순서_: correlation-id → Prometheus → OTel (자동 계측 시 다른 미들웨어 감싸야 trace 완전).

## 13단계 완료 — `13-kafka-queue/`

세 가지 비동기 작업 메커니즘 한 단계에 통합:
- `mqapp/kafka_producer.py` — `KafkaPublisher` + `make_producer` (acks=all, idempotent)
- `mqapp/kafka_consumer.py` — `consume_loop` (수동 commit, at-least-once)
- `mqapp/outbox.py` — `OutboxEvent` + `record_event` + `relay_once` (DB 트랜잭션 일관성)
- `mqapp/arq_worker.py` — `send_email`/`process_order` + `WorkerSettings`
- `mqapp/main.py` — BackgroundTasks vs Kafka vs arq 비교 라우트
- 4 tests + Postgres testcontainers (outbox 원자성 검증)

세션 중 디버깅한 부분:
- **outbox `DateTime` 컬럼**은 `timezone=True` 필수 — `datetime.now(UTC)` 와 매칭.
- **arq `create_pool` retry** 가 30초 → lifespan timeout. `RedisSettings.conn_retries=0` 으로 빠른 실패.
- **testcontainers 잔여 ryuk 컨테이너** — 이전 테스트의 ryuk 가 살아있어 포트 충돌. `docker rm -f` 정리 후 재실행.
- 매 테스트마다 `metadata.drop_all + create_all` 로 outbox 격리.

## 14단계 완료 — `14-shared-package/`

`fastapi-common` 라이브러리 추출:
- `__init__.py` — 공개 API surface (`__all__`) + `__version__`
- `envelope.py` (07), `errors.py` (07), `handlers.py` (07)
- `correlation.py` (12), `http_client.py` (12), `logging_setup.py` (04/12)
- CHANGELOG.md (Keep a Changelog 형식)
- 9 tests (공개 API 안정성 + 미니 FastAPI 통합 + ResilientClient)
- `make build` → `dist/fastapi_common-0.1.0-{tar.gz,whl}` (10KB wheel)

세션 중 디버깅:
- hatchling 빌드는 `pyproject.toml` 의 `readme = "README.md"` 가 _존재_ 해야 함. 빈 README 도 OK.
- `uv build` 산출물은 _워크스페이스 루트_ 의 `dist/` (각 멤버 디렉토리 X).

## 15단계 완료 — `15-mini-project/` 🎓

**졸업 작품** — 04~14 의 모든 패턴이 한 앱에 결합:
- `tender/main.py` — `fastapi-common` 의 `install_correlation_middleware` + `install_exception_handlers`
- `tender/auth.py` — JWT + bcrypt + `get_current_user` + `require_role` (09)
- `tender/models.py` — User + Order + OutboxEvent (10 + 13)
- `tender/schemas.py` — v1/v2 분리 Pydantic (07)
- `tender/repository.py` + `uow.py` — UserRepo / OrderRepo / OutboxRepo + UnitOfWork (10)
- `tender/cache.py` — OrderCache cache-aside + invalidation (11)
- `tender/api/{v1,v2,auth}.py` — `fastapi-common.ApiEnvelope` 사용 + Deprecation 헤더 (07)
- `alembic/versions/...initial.py` — 3개 테이블 마이그레이션
- 6 e2e 시나리오 (testcontainers Postgres + Redis)

세션 중 디버깅:
- `OAuth2PasswordBearer` 자동 401 은 `HTTPException` 경로 → `code="HTTP_401"` (envelope 변환은 정상). 도메인 `AuthError` 만 `code="UNAUTHORIZED"`.
- testcontainers ryuk 컨테이너가 macOS 환경에서 _가끔_ 포트 충돌 → `TESTCONTAINERS_RYUK_DISABLED=true` 로 비활성. `with` 컨텍스트 매니저가 정리 보장.
- `fastapi-common` 의 `py.typed` 마커 추가 (mypy stub 인식).
- 테스트 격리는 매번 `TRUNCATE users, orders, outbox_events RESTART IDENTITY CASCADE`.

## 다음 (선택) — `A1-i18n/` 부록

본편 끝. 부록은 _필요 시_ 진행:
- Babel + gettext + 메시지 카탈로그 (.po/.mo)
- Accept-Language 헤더 기반 로케일
- Pydantic 검증 메시지 다국어화

또는 이미 만든 15 위에 _부하 테스트_ (locust/k6) 직접 시도해보는 것도 좋음.
- 04~14 의 _모든 개념_ 결합
- `fastapi-common` (14) 을 _의존성_ 으로 사용 — 사내 배포 시뮬
- 시나리오: 인증된 사용자 → 주문 생성 → DB 트랜잭션 → Kafka 이벤트 → 컨슈머가 알림 처리 → 캐시 갱신
- v1/v2 라우터 공존, 공통 에러, rate limit, 관측가능성
- 부하 테스트 (`locust` 또는 `k6`) — async 처리량 직접 측정

산출물:
```
15-mini-project/
├── pyproject.toml          # fastapi-common + 모든 인프라 의존성
├── docker-compose.yml      # 또는 05 의 루트 compose 재사용
├── Makefile
├── README.md               # 전체 아키텍처 다이어그램 + 시나리오 흐름
├── alembic/                # DB 마이그레이션
├── src/tender/             # 패키지 이름
│   ├── api/v1/, api/v2/
│   ├── domain/             # 도메인 모델 + 서비스
│   ├── repository/         # SQLAlchemy
│   ├── events/             # Kafka producer + consumer
│   ├── workers/            # arq 워커
│   ├── deps.py
│   └── main.py
└── tests/                  # 03계층 + 시나리오 e2e
```

이게 _커리큘럼의 졸업 작품_. 04~14 의 모든 패턴이 _하나의 앱_ 에 어떻게 들어가는지 보여줌.


## 진행 방식 권장 (이미 정착된 패턴)

1. **단계당 1세션** — 한 번에 다음 단계까지 가지 말고 체크인.
2. **사용자가 "이거 감이 안 잡힘" 류 질문하면 build-up 학습 모듈로 _확장_** (s02 컴프리헨션, s07 구조 분해 패턴).
3. **각 단계 완료 시 루트 `README.md` 의 체크리스트 ✅ 갱신**.
4. **`make all` 녹색이면 단계 완료**. 추가로 데모/CLI 동작도 직접 확인.

## 검증 명령 (지금 상태 확인용)

```bash
cd /Users/hyunmin.song/Desktop/bespin/fast-api

# 환경 동기화
uv sync

# 01 회귀
cd 01-python-basics && make all
# → 60 passed

# 02 회귀
cd ../02-package-structure && make all
# → 18 passed

# CLI 동작
uv run greeter hello Alice --locale en
# → Hello, Alice!
```
