# 학습 진행 상황 (이어 작업용 노트)

> **내일 시작할 때**: 새 Claude 세션에서 이 파일을 보여주거나 "STATUS.md 보고 ..." 라고 말하면 됨.

마지막 작업: 2026-04-30 — **🚀 `templates/fastapi-best-practice/` 생성** (28단계 완주 후 운영급 패턴 추출 → Mid 범위 실무 시작 키트).

---

## 🚀 `templates/fastapi-best-practice/` — 실무 시작 키트 (2026-04-30 생성)

28 단계 완주 후 _운영급 패턴_ 추출 → 자체 완결 FastAPI 앱 템플릿:
- 위치: `templates/fastapi-best-practice/` (워크스페이스 멤버 X, 독립 프로젝트)
- 범위 (Mid): FastAPI factory + Settings + JWT/RBAC + Postgres(SQLAlchemy + Alembic) + Redis cache-aside + ApiEnvelope/에러/correlation-id/구조화 로그 + 테스트(testcontainers) + Docker + GitHub Actions
- 도메인: users (signup/login/me) + items (CRUD + owner 가드)
- 39 tests (14 unit + 25 integration), ruff/mypy clean
- README 에 Rename guide (4 토큰 sed 치환) + 11 Pitfalls + 다음 단계 가이드

세션 중 디버깅:
- **`Item.updated_at` `onupdate=func.now()` + DetachedInstanceError**: server-side 계산 → flush 후 `await session.refresh(item)` _필수_. 안 하면 session close 후 lazy refresh 실패.
- **`/api/v1/items` route 등록 누락**: Phase 3 stub Write → Phase 4 full Write 가 _덮어쓰지 않음_ (Write 가 silent fail). Read → Write 재시도로 해결. 학습 메모 — Edit/Write 세션 어디 단계에서 stale 인지 항상 확인.
- **`OAuth2PasswordBearer` `tokenUrl` prefix 일치**: `/api/v1/auth/login` 으로 _라우터 prefix 와 동일_ 해야 Swagger Authorize 동작.
- **`bcrypt<4.1` pin 유지**: passlib 1.7.4 가 bcrypt 4.1+ 의 `__about__` 제거에 적응 못함.

Critical files (참조용, 절대 경로):
- `/Users/hyunmin.song/Desktop/bespin/fast-api/templates/fastapi-best-practice/src/app/main.py`
- `/Users/hyunmin.song/Desktop/bespin/fast-api/templates/fastapi-best-practice/src/app/core/handlers.py`
- `/Users/hyunmin.song/Desktop/bespin/fast-api/templates/fastapi-best-practice/tests/conftest.py`
- `/Users/hyunmin.song/Desktop/bespin/fast-api/templates/fastapi-best-practice/Dockerfile`

검증: 템플릿 디렉토리에서 `make all` (ruff + mypy + 39 tests) 통과. `docker build --check .` 통과. `docker compose config --quiet` 통과.

---

## 🎓 졸업 + 부록 진행

**FastAPI + Python 학습 커리큘럼 본편 (15단계) 완주 + 부록 트랙 진행 중.**

### 부록 진행 체크

| # | 트랙 | 상태 |
|---|---|---|
| **A1** | **i18n** | ✅ 완료 🎓🎓 — Accept-Language / gettext / Pydantic / Babel (41 tests) |
| A2 | load-test (locust) | ✅ 완료 |
| A3 | CI/CD (GitHub Actions) | ✅ 완료 |
| A4 | Kubernetes | ✅ 완료 |
| A5 | 보안 심화 | ✅ 완료 — TOTP/API key/OAuth 3rd/OWASP/보안 헤더 (23 tests) |
| A6 | DB 심화 | ✅ 완료 — 인덱스/N+1/jsonb/FTS/LISTEN-NOTIFY/Expand-Contract (21 tests) |
| A7 | 캐시·MQ 심화 | ✅ 완료 — stampede/Saga/CQRS/Event Sourcing/Schema Registry/DLQ (33 tests) |
| A8 | WebSocket / SSE | ✅ 완료 — ConnectionManager / RedisBroker / 채팅 / 알림 (19 tests) |
| A9 | 파일 IO | ✅ 완료 — multipart / Range / presigned / S3 multipart upload (33 tests) |
| A10 | GraphQL | ✅ 완료 — Strawberry / Query / Mutation / DataLoader N+1 회피 (19 tests) |
| A11 | DDD / 헥사고날 | ✅ 완료 — Aggregate / VO / Domain Event / Ports & Adapters (36 tests) |
| A12 | 관측가능성 운영급 | ✅ 완료 — Sentry / 구조화 로그 / OTel / SLO / Grafana / Alertmanager (31 tests) |
| A13 | Python 고급 typing & 메타 | ✅ 완료 — PEP 695 / Protocol / Descriptor / Generator / Context Manager (56 tests) |
| **A14** | **성능 / 프로파일링** | ✅ 완료 🎓 — cProfile / tracemalloc / async 함정 / 알고리즘 / 워커 (25 tests) |

부록 트랙 13개 전체 정의는 `~/.claude/plans/fast-api-python-tender-key.md` 참고.


총 누적 테스트: **547** (본편 210 + A1~A14 = 41 + 23 + 21 + 33 + 19 + 33 + 19 + 36 + 31 + 56 + 25)
**🎓🎓 본편 15단계 + 부록 A1~A14 = 28/28 _진짜_ 전체 완주**
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

## A6 완료 — `A6-db-deep/`

**DB 심화** — 인덱스 / N+1 / jsonb / FTS / LISTEN-NOTIFY / Zero-downtime 마이그레이션:
- `dbdeep/models.py` — User/Post/Comment + 6가지 인덱스 (B-tree / 복합 / 부분 / expression / GIN x2)
- `dbdeep/n_plus_one.py` — naive (N+1) / selectinload (2쿼리) / joinedload (1쿼리) + `count_queries` 카운터
- `dbdeep/jsonb.py` — `tags @> '...'` containment, GIN 인덱스 활용
- `dbdeep/fts.py` — `websearch_to_tsquery` + `ts_rank` (가중치 setweight)
- `dbdeep/listen_notify.py` — psycopg sync NOTIFY/LISTEN (가벼운 pub/sub)
- `dbdeep/main.py` — FastAPI 데모 라우트 (Request → app.state 패턴, 10 단계와 동일)
- `alembic/versions/0001_initial.py` — 테이블 + tsvector GENERATED ALWAYS AS + GIN
- `alembic/versions/0002_expand_add_email_lower.py` — Expand: ADD COLUMN + CONCURRENTLY 인덱스 + 백필
- `alembic/versions/0003_contract_set_not_null.py` — Contract: SET NOT NULL (가드: NULL 행 검증)
- 21 tests (인덱스 EXPLAIN + N+1 카운트 + jsonb @> + FTS + 마이그레이션 + e2e)

세션 중 디버깅:
- **`search` GENERATED 컬럼** — 모델에 `Computed(persisted=True)` 추가 안 하면 ORM 이 INSERT 에 포함 → `cannot insert a non-DEFAULT value into column "search"`. SQLAlchemy 가 컬럼을 _제외_ 하도록 `Computed` 명시.
- **FastAPI Depends 패턴**: `get_session(request: Request)` _module-level_ + `Annotated[..., Depends(...)]` _module-level_ 정의가 정석. `create_app()` 안 closure 로 만들면 422 발생 (FastAPI 가 의존성 트리 구축 단계에서 못 풀어냄).
- **EXPLAIN 검증의 한계**: 시드 30~100 행에선 planner 가 Seq Scan 채택할 수 있음. 인덱스 _존재_ 확인은 `pg_indexes` 카탈로그로, _사용_ 확인은 운영 규모에서.
- **`ix_deep_users_email_lower_v2`** 같은 _이름 변경 패턴_ — Expand 단계에서 신 인덱스를 _다른 이름_ 으로 만들고 Contract 에서 정리. 운영급 패턴.

## A7 완료 — `A7-cache-mq-deep/`

**캐시·MQ 심화** — 7가지 분산 시스템 패턴:
- `cachemqdeep/stampede.py` — `get_or_set_with_lock` (lock-based) + `get_or_set_xfetch` (Probabilistic Early Refresh)
- `cachemqdeep/redis_ha.py` — Sentinel/Cluster 패턴 노트 + `HashTag` 헬퍼 (cluster 다중 키)
- `cachemqdeep/saga.py` — Orchestrator + 보상 액션 _역순_ 실행
- `cachemqdeep/cqrs.py` — Order (쓰기 모델) + OrderSummaryView (읽기 모델) + Mediator
- `cachemqdeep/event_sourcing.py` — EventStore + BankAccount.replay + 오버드래프트 검증
- `cachemqdeep/schema_registry.py` — JSON Schema + BACKWARD/FORWARD/FULL/NONE 호환성
- `cachemqdeep/dlq.py` — Redis list 기반 DLQ + 재시도 카운터 + redrive
- `cachemqdeep/main.py` — FastAPI 데모 라우트 (7가지 패턴 모두)
- 33 tests (stampede 3 + saga 3 + cqrs 4 + ES 5 + schema 5 + dlq 4 + e2e 9)

세션 중 메모:
- **stampede 동시성 테스트**: `asyncio.gather(*[get_or_set_with_lock(...) for _ in range(20)])` 으로 20개 동시 실행 후 `call_count <= 2` 검증. 락 획득 race window 가 있어 _정확히 1_ 보단 _상한_ 으로.
- **XFetch 식**: `delta * beta * (-ln(rand())) < TTL_remaining` ── delta(직전 계산 시간), beta(공격성), rand 균등분포. 비싼 작업일수록 일찍 재계산.
- **Saga 보상 idempotent** — 같은 보상 두 번 = 한 번. 재시도 중복 효과 막기.
- **Schema 호환성 단순화**: 실제 Confluent 알고리즘은 _필드 단위 정밀_ 비교. 본 모듈은 _필드 집합_ 차이만 (학습 친화).
- **mypy `jsonschema`** stub 없음 → 루트 mypy.overrides 에 추가.
- **Redis hash tag** ── `{user:42}:profile` 의 중괄호 _안_ 부분이 슬롯 결정. cluster 다중 키 명령 필수.

## A8 완료 — `A8-realtime/`

**WebSocket / SSE / Redis pub/sub 다중 인스턴스 fan-out**:
- `realtime/manager.py` — `ConnectionManager` (room 단위 연결, lock 안 변경 / lock 밖 send)
- `realtime/pubsub.py` — `RedisBroker` (PSUBSCRIBE 백그라운드 + publish → 모든 인스턴스 broadcast)
- `realtime/sse.py` — sse-starlette `EventSourceResponse` 래핑 (자동 ping / X-Accel-Buffering / disconnect 감지)
- `realtime/main.py` — FastAPI: WebSocket 채팅 (`/ws/chat/{room}?user=`) + HTTP broadcast + SSE notifications
- 19 tests (manager 7 unit + pubsub 3 integration + websocket e2e 6 + sse 3)

세션 중 디버깅:
- **`@dataclass` 가 `__hash__ = None` 만듦** — set 에 못 넣음. `@dataclass(eq=False)` 로 기본 hash 유지.
- **`from tests.test_module import X` 패턴은 fragile** — `tests/__init__.py` 있어도 collection rootdir 따라 깨짐. 공유 fixture 는 `conftest.py` 로.
- **TestClient + sse-starlette 무한 스트림 → 무한 hang** — `client.stream("GET", sse_url)` 이 끝나지 않음 (브라우저 EventSource 없음). 스트림 _내용_ 검증은 _httpx 비동기_ + 진짜 서버 권장. 테스트는 _큐 동작_ 만 검증 (POST /notify).
- **uv editable install .pth 누락** — `uv sync --reinstall-package realtime` 으로 복구. site-packages 에 `_editable_impl_realtime.pth` 가 _존재_ 해야 import 가능.
- **WS 인증 패턴**: 연결 시점 1회 (쿼리/첫 메시지) — 매 메시지 검증은 _과한 비용_. 짧은 TTL JWT + 재연결 갱신.
- **SSE 운영 함정**: nginx `proxy_buffering off`, LB idle timeout 늘리기, 브라우저 동도메인 SSE 6개 한계 (HTTP/2 무제한).

## A9 완료 — `A9-file-io/`

**파일 업로드/다운로드** — 5가지 운영 패턴:
- `fileio/storage.py` — `LocalStorage` (atomic `.part` rename + Range get + traversal 차단)
- `fileio/upload.py` — `sanitize_filename` (basename만) + `stream_with_size_limit` (누적 카운트) + MIME 화이트리스트
- `fileio/download.py` — `parse_range_header` (RFC 7233 — `bytes=N-`, `bytes=-N` suffix, 416 시 `Content-Range: */size`)
- `fileio/presigned.py` — HMAC-SHA256 + `hmac.compare_digest` (timing attack 방지)
- `fileio/multipart_upload.py` — S3 호환 (`initiate` → uploadId / `upload_part` → ETag(MD5) / `complete` ETag 검증 / `abort`)
- `fileio/main.py` — FastAPI: `/files` POST/GET (Range)/DELETE, `/presign`, `/uploads/...` 라이프사이클
- 33 tests (storage 6 + download 9 + presigned 4 + e2e 14)

세션 중 메모:
- **빈 패키지 디렉토리** (`__init__.py` 없음) 으로 `uv sync` 하면 `.pth` 안 만들어짐 → import 안 됨. **항상 `__init__.py` 먼저** 생성 후 sync.
- **파일명 sanitize 정책** ── `../escape.txt` 같은 traversal 은 _basename `escape.txt` 만 사용_ (이게 이 모듈의 "관대한" 정책). 공백/특수문자는 _거부_ (엄격 화이트리스트). 운영은 도메인에 맞게 _균형_ 조정.
- **`UploadFile`** 의 `.read()` 전체 호출은 OOM ── `.read(chunk_bytes)` 루프 + 누적 크기 카운트.
- **`StreamingResponse` + Range 206**: `Content-Length: rng.length`, `Content-Range: bytes start-end/total`, `Accept-Ranges: bytes` 셋트.
- **presigned 변조 검증**: 마지막 글자만 바꿔도 `compare_digest` 가 _상수 시간_ 으로 거부 — timing attack 막음.
- **multipart upload state** ── 학습용 인메모리 dict, 운영은 Redis/DB. abort 안 한 incomplete uploads 는 lifecycle / cron 으로 정리.
- **`aiofiles` mypy stub 없음** → 루트 `mypy.overrides` 에 추가.

## A10 완료 — `A10-graphql/`

**GraphQL with Strawberry** — REST 대안, code-first 패턴, N+1 자동 회피:
- `gqlapi/data.py` — 인메모리 `DataStore` + 시드 (3 user, 7 post, 4 comment) + _호출 카운터_ (N+1 검증)
- `gqlapi/dataloader.py` — `make_user_loader` / `make_posts_by_author_loader` (Strawberry `DataLoader` 활용)
- `gqlapi/schema.py` — `@strawberry.type` `User`/`Post` + `Query`/`Mutation` + `GraphQLContext(BaseContext)`
- `gqlapi/main.py` — FastAPI + `GraphQLRouter` 통합, `context_getter` 에서 _요청 단위_ DataLoader 새로 생성
- 19 tests (schema 7 + dataloader 5 + e2e 7)

**DataLoader 검증 — N+1 vs 1**:
- 7 post → naive: `users_by_ids_calls == 7` (각 post 마다 author 조회)
- 7 post → DataLoader: `users_by_ids_calls == 1` (한 tick 동안 모아 batch + dedupe)

세션 중 디버깅:
- **Strawberry FastAPI `context_getter`** ── `BaseContext` 상속 또는 dict 반환 _필수_. 일반 dataclass 는 `InvalidCustomContext` 에러. 학습용으로 `GraphQLContext(BaseContext)` + `super().__init__()` 채택.
- **`context_getter` 타입 stub** ── strawberry 의 stub 가 `Awaitable[None]` 만 허용한다고 표시 → `# type: ignore[arg-type]` 한 줄. 실제 동작은 정상.
- **GraphQL 에러 모델 vs REST**: HTTP 200 + body 의 `errors` 필드. 클라이언트가 errors 검사 필수. _부분 성공_ 도 가능 (data 일부 + errors 일부).
- **DataLoader 캐시 _요청 단위_** ── 전역 싱글톤이면 stale + 메모리 누수. `context_getter` 에서 매번 새로.
- **`strawberry.Private[T]`** ── 내부 필드를 GraphQL 스키마에 노출 안 함 (예: `Post.author_id` 는 resolver 에서만 쓰고 클라이언트엔 `author { ... }` 만).

## A11 완료 — `A11-ddd/`

**DDD + 헥사고날** — 15 의 tender 를 _4계층_ 으로 정련:
- `domain/` — Order Aggregate + OrderLine + OrderStatus(상태머신) + Money/Quantity/SKU VO + OrderPlaced/OrderCancelled 이벤트 + DiscountPolicy 도메인 서비스
- `ports/` — `OrderRepository` / `UserRepository` / `Notifier` / `UnitOfWork` (Protocol — 도메인이 선언, 어댑터가 구현)
- `application/` — `PlaceOrderUseCase` / `CancelOrderUseCase` / `GetOrderUseCase` (얇은 코디네이션, 트랜잭션 경계, 이벤트는 commit 후 publish)
- `adapters/inmemory.py` — InMemoryOrderRepository / InMemoryUserRepository / CollectingNotifier / InMemoryUnitOfWork
- `adapters/api/router.py` + `main.py` — FastAPI 어댑터 + Composition Root (DI 와이어링)
- 36 tests (VO 12 + Aggregate 11 + Use Case 7 + API e2e 7) — 모두 도커 불필요

**핵심 메시지**:
- _도메인은 인프라 모름_ — `domain/` 에서 `sqlalchemy` / `fastapi` import 0개
- 의존성 방향 _한 방향_: Adapter → Port (Protocol) → Application → Domain
- 같은 use case 가 FastAPI / CLI / GraphQL / arq worker 어댑터에서 _재사용_
- 도메인 예외 (`DomainError` 계열) → 어댑터에서 HTTP 코드 매핑 (404/400/409)
- 이벤트는 _commit 후_ publish — 운영급은 outbox 패턴 (13)

세션 중 메모:
- **`Annotated[..., Depends(...)]` 별칭은 _module level_ 에 정의** ── `make_router()` 안 closure 로 만들면 FastAPI 가 못 풀어 422. (A6 와 동일 함정 재발생, 재학습)
- **VO `__post_init__`** 으로 자가 검증 ── `@dataclass(frozen=True)` + raise. 잘못된 값은 _존재 X_.
- **Aggregate 의 `pull_events()`** ── 이벤트 _꺼내며 비움_ (이중 발행 방지).
- **`UnitOfWork.__aexit__`** ── 예외 X 면 commit, 있으면 rollback. 도메인 예외 (UserNotFound) → rollback → notifier publish 안 함.
- **N818 / N802 / N806** ── ruff naming 규칙 (Exception suffix, snake_case 함수, lowercase 변수). 도메인 명명 우선시 `# noqa` 로 일부 허용.

## A12 완료 — `A12-observability/`

**관측가능성 운영급** — 12 단계의 자동 계측을 _SRE 도구_ 와 결합:
- `obsdeep/structured_logging.py` — `setup_logging` (dev=콘솔 / prod=JSON) + `_redact_sensitive` (password/token/authorization 자동 마스킹) + contextvars 기반 request_id 주입
- `obsdeep/sentry_setup.py` — `setup_sentry` (DSN 없으면 no-op) + `_scrub_event` before_send + FastApi/Starlette/Logging Integration
- `obsdeep/slo.py` — `Slo` 데이터클래스 + `compute_burn_rate` + `remaining_budget` + `is_alerting` (SRE 14.4 임계값)
- `obsdeep/tracing.py` — OTel TracerProvider + `instrument_fastapi` + OTLP exporter 패턴 노트
- `obsdeep/dashboards.py` — `red_dashboard` (Rate/Errors/Duration RED 메서드) + `slo_dashboard` (burn rate + 남은 예산), Grafana JSON 직접 생성
- `obsdeep/alerting.py` — `slo_burn_rate_alerts` Google SRE Workbook 표준 4종 (multi-window multi-burn-rate)
- `obsdeep/main.py` — FastAPI: correlation-id 미들웨어 + /work(span)/`/boom`(에러)/`/slo/burn`/`/admin/dashboard.json`/`/admin/alerts.yaml`
- 31 tests (SLO 9 + 로그 redact 4 + dashboards 5 + alerting 5 + e2e 8)

**핵심 메시지**:
- **SLI = 측정값 / SLO = 목표 / Error Budget = 허용량** ── 99.9% / 30일 = 43.2분 다운 허용
- **Burn rate** = 에러율 / (1 - target). burn 14.4 = 1시간에 2% 예산 소진 → page
- **multi-window AND** → false positive 줄임 (5m + 1h 윈도우 _둘 다_ true 일 때만 fire)
- **runbook URL 필수** ── 알람은 _actionable_ 이어야

세션 중 메모:
- **f-string 안 PromQL `{service="X"}`** — `.format()` 호출 시 `KeyError` (Python 이 placeholder 로 해석). 해결: `.format()` 자체를 _제거_ 하고 rate 도 f-string 변수로 직접.
- **Grafana JSON 의 camelCase** (`legendFormat` / `refId` / `gridPos` / `schemaVersion`) — Python naming 규칙 위배 → `# noqa: N815` 다섯 곳.
- **Sentry DSN 없으면 no-op** ── 학습 / CI 친화. 운영은 환경변수 (`A12_SENTRY_DSN=https://...@sentry.io/...`).
- **`traces_sample_rate` 운영 기본 0.0** ── 학습용. 운영은 0.01~0.1 (요청량 따라).
- **OTel ConsoleSpanExporter 의 process tear-down race** ── 12 단계와 동일한 현상 (test 끝난 뒤 stdout 닫힌 상태에서 export 시도하는 무해 ValueError).
- **`from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter`** ── 운영용. 별도 의존성 (`opentelemetry-exporter-otlp-proto-grpc`) 추가하면 패턴 그대로 동작.

## A13 완료 — `A13-typing-deep/`

**Python 고급 typing & 메타프로그래밍** — 10개 학습 모듈 build-up:
- `t01_generics.py` — `TypeVar`, PEP 695 `class Box[T]`, bounded `[T: Comparable]`, constrained `[N: (int, float)]`
- `t02_protocols.py` — 구조적 typing, `runtime_checkable`, Generic Protocol `Repository[T]`
- `t03_literal_newtype.py` — `Literal["red", "green"]` exhaustive match, `NewType("UserId", int)`, `TypedDict` + `NotRequired`, `Final`
- `t04_overload.py` — `@overload` (입력별 출력), PEP 695 `[**P, R]` ParamSpec, `[*Ts]` TypeVarTuple
- `t05_descriptors.py` — `__set_name__` + `__get__/__set__` (validator), LazyProperty (instance dict 캐시)
- `t06_metaclass.py` — `__init_subclass__` (대안 90% 충분) + Singleton metaclass + AutoRepr metaclass
- `t07_generators.py` — `yield from`, `send/throw/close`, async generator
- `t08_context_managers.py` — `__enter__/__exit__`, `@contextmanager`, async, `SuppressErrors` 패턴
- `t09_functools_advanced.py` — `@singledispatch`, `@cache`/`@lru_cache`, `partial`, `@wraps`, `reduce`
- `t10_typeguard.py` — `TypeGuard` 커스텀 narrowing
- 56 tests — 모듈별 1:1 매핑, **mypy clean** 이 가장 중요한 검증

**핵심 메시지**:
- 이 모듈은 _런타임 동작_ 보다 _타입 시스템 정확성_ 학습 — `make typecheck` 깨끗 = 학습 완료
- PEP 695 (3.12+) 새 문법이 _훨씬_ 간결 (`class Box[T]` vs `TypeVar` + `Generic[T]`)
- metaclass 는 _99% 안 씀_ ── `__init_subclass__` / 데코레이터 / mixin 우선

세션 중 메모:
- **Comparable Protocol 의 빈 메서드** — `def __lt__(self, other: object) -> bool: ...` 만 있으면 mypy `empty-body` 경고. 학습용 default 반환값 추가.
- **`__repr__` 함수 이름이 dunder** — ruff N807 경고 (함수명에 `__` 안 됨). 메타클래스 안에서 정의할 땐 `auto_repr` 같은 일반 이름 → `cls.__repr__ = auto_repr`.
- **`first_and_rest` TypeVarTuple 반환** — mypy 가 `tuple(rest)` 를 `tuple[object, ...]` 로 좁히지 못해 `# type: ignore[return-value]`. 실용 가치 보단 _문법 시연_ 우선.
- **PEP 695 `[**P, R]` 데코레이터** — 옛 `ParamSpec` 변수 선언 _불필요_, 한 줄로.
- **`@cache` 인스턴스 메서드 함정** — self 가 캐시 키 → 인스턴스 영원히 살아있음. `cached_property` 가 인스턴스 단위 캐시.

## A14 완료 — `A14-perf/` 🎓

**성능 / 프로파일링 — 마지막 트랙**:
- `bench_utils.py` — `bench[T](...)` + BenchResult (p50/p95/p99) + `faster(a, b)` 비율 (PEP 695 새 문법 적용)
- `cprofile_demo.py` — `profile_call[T]` + fib_naive(O(2^n)) vs fib_iterative(O(n)) + slow vs fast 문자열 연결
- `tracemalloc_demo.py` — `measure_memory[T]` + snapshot diff + leaky_function (전역 dict 누적) vs clean_function 시뮬
- `async_pitfalls.py` — 5가지 함정 (blocking sleep / 순차 await / CPU bound / fire-and-forget / slow_callback_duration 탐지) + `to_thread` / `ProcessPoolExecutor`
- `algorithm_complexity.py` — linear vs binary search, has_duplicate quadratic vs set, count 3가지, cumulative quadratic vs linear
- `cache_bench.py` — `@cache` fib 효과 + `cached_property` 인스턴스 단위 캐시
- `workers.py` — gunicorn / uvicorn 운영 가이드 (코드 X — 노트)
- `external_tools.py` — py-spy / memray / pyinstrument / scalene / line_profiler / Numba / PyO3 사용 패턴
- 25 tests — _측정_ 으로 알고리즘 차이 검증 (binary > 5x, set > 10x, cumulative > 10x, cached fib > 5x)

**핵심 메시지**:
- **"measure, don't assume"** — intuition 거의 항상 틀림
- 짧은 함수 `@cache` 는 _오히려 느려짐_ — overhead > 연산 비용
- async 안 blocking 호출 = 이벤트 루프 _전체_ 멈춤
- 인스턴스 메서드 `@cache` = 메모리 누수 (self 가 키 → 인스턴스 영원)
- 운영 hot path 분석은 _live_ py-spy, 메모리는 memray flame graph

세션 중 메모:
- **PEP 695 적용**: `bench[T](...)`, `profile_call[T](...)`, `measure_memory[T](...)` ── A13 에서 배운 새 문법 활용 (ruff `UP047` 자동 변환)
- **테스트 시 timing assert**: `faster(set_, qua) > 10` 같은 _느슨한 lower bound_ ── flaky 방지. 정확한 ratio 보단 "충분히 빠르다" 검증.
- **leaky_function 시뮬**: 전역 dict 에 계속 추가 → 매 호출마다 RSS 증가 (실제 누수 케이스: 캐시 TTL 없음 / 이벤트 리스너 미해제 / 닫지 않은 파일).
- **`asyncio.to_thread` 가 GIL 우회 X**: I/O bound 만 진짜 병렬. CPU bound 진짜 병렬은 ProcessPoolExecutor (IPC 비용).
- **워커 수 공식**: `2 × CPU + 1` (gunicorn 기본) ── I/O bound 가정. CPU bound 면 `CPU` 만큼.

## 🎓 졸업 마무리 — 전체 부록 완주 (2026-04-30)

본편 15단계 + 부록 13개 (A1 i18n 만 ⚪ 선택) = **27 단계 / 506 tests**.

총괄:
- 01~03: Python 기초 + 패키지 + 라이브러리
- 04~05: FastAPI + 인프라 (Docker Compose)
- 06: async 심화
- 07~08: 응답/에러/버전 + 테스팅
- 09~13: 인증 / DB / Redis / 관측가능성 / Kafka
- 14~15: 공통 라이브러리 (`fastapi-common`) + 졸업 미니 프로젝트 (`tender`)
- A2~A4: 부하 / CI/CD / Kubernetes
- A5~A7: 보안 / DB / 캐시·MQ 심화
- A8~A10: 실시간 / 파일 IO / GraphQL
- A11~A14: DDD 헥사고날 / 관측가능성 운영 / typing 메타 / 성능 프로파일링

**다음 단계 (선택)**:
- A1 i18n (Babel + gettext) — 다국어가 필요해질 때
- 본편 + 부록 _재방문_ — 운영 환경에서 직접 띄워보기 (testcontainers 한계 넘어)
- 새 프로젝트 시작 — 본 모노레포를 _참조 자료_ 로

학습 자료 패턴 (정착됨):
1. 단계별 디렉토리 + uv workspace 멤버
2. `make all` (lint + typecheck + test) 통과 = 단계 완료
3. README 의 다국 비교 (Java/Spring · Kotlin · Go · Node · TS · C/C++)
4. testcontainers 자동 셋업 (도커 있으면 통합 테스트)
5. 사용자 질문 → build-up 학습 모듈 (s02 컴프리헨션 / s07 unpacking 패턴)

## A1 완료 — `A1-i18n/` 🎓🎓

**다국어 처리 (i18n)** — _진짜 마지막_ 트랙:
- `i18napp/locale.py` — `parse_accept_language` (RFC 4647 q-value 정렬) + `negotiate_locale` (정확/primary/wildcard) + `contextvars` 기반 `set_locale`/`get_locale`
- `i18napp/catalog.py` — MESSAGES dict (en/ko/ja) + `gettext` (key 누락 → en → key 자체 fallback) + `ngettext` 단복수
- `i18napp/babel_setup.py` — `format_money` / `format_number` / `format_d` / `format_relative` / `display_locale_name` (Babel + CLDR)
- `i18napp/pydantic_messages.py` — `ValidationError` → 다국어 envelope (`{field, type, message}` 리스트)
- `i18napp/middleware.py` — `LocaleMiddleware` (쿠키 > Accept-Language > default) + `Content-Language` 응답 헤더
- `i18napp/main.py` — FastAPI: `/greet`, `/items` (단복수), `/orders` (Pydantic 검증 다국어), `/money`, `/date`, `/lang`
- 41 tests (locale 9 + catalog 8 + babel 7 + pydantic 4 + e2e 11) — 도커 불필요

**핵심 메시지**:
- locale 우선순위: URL prefix > 쿠키 > 사용자 프로필 > Accept-Language > default
- `contextvars` 기반 → 비동기 안전 + 라우트/도메인 어디서든 `get_locale()` 접근
- 운영급 워크플로: pybabel `extract` → `init` → 번역가가 `.po` 편집 → `compile` → `gettext.translation()`
- Pydantic 영문 메시지는 _후처리_ 또는 _클라이언트 측 번역_ 가 실용
- 숫자/날짜/통화 포맷도 _번역과 별개_ — Babel + CLDR

세션 중 메모:
- **`Accept-Language` q-value 무시 시 함정**: `en;q=0.1,ko;q=0.9` → `en` 선택 = 잘못. q 내림차순 정렬 필수.
- **단복수 영어만 OK 함정**: 폴란드어/러시아어 _3가지_ 형태. ICU MessageFormat 또는 Babel `ngettext` (`.po` plural rules) 권장.
- **번역가 워크플로**: Crowdin / Weblate / Lokalise 같은 SaaS — 번역가는 `.py` 파일 직접 X.
- **f-string 안 변수 보간 X**: `_(f"hello {name}")` → 키가 매번 달라져 _추출 불가_. 항상 `_("hello {name}", name=name)`.
- **CDN/캐시 함정**: `Content-Language` 헤더 응답 안 하면 다른 언어 응답 _섞여서 캐싱_.

## 🎓🎓 _진짜_ 전체 졸업 — 28/28 (2026-04-30)

본편 15단계 + 부록 A1~A14 = **28 단계 / 547 tests** ── _완전 완주_.

총괄 (수정):
- 01~03: Python 기초 + 패키지 + 라이브러리
- 04~05: FastAPI + 인프라 (Docker Compose)
- 06: async 심화
- 07~08: 응답/에러/버전 + 테스팅
- 09~13: 인증 / DB / Redis / 관측가능성 / Kafka
- 14~15: 공통 라이브러리 (`fastapi-common`) + 졸업 미니 프로젝트 (`tender`)
- **A1**: 다국어 (i18n) — Accept-Language / gettext / Babel / Pydantic 메시지
- A2~A4: 부하 / CI/CD / Kubernetes
- A5~A7: 보안 / DB / 캐시·MQ 심화
- A8~A10: 실시간 / 파일 IO / GraphQL
- A11~A14: DDD 헥사고날 / 관측가능성 운영 / typing 메타 / 성능 프로파일링

이 모노레포 = **다음 프로젝트의 참조 자료**. 개념 / 패턴 / 운영 함정 / 다국 비교가 한 곳에.



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
