# 08 — 테스팅 심화

지금까진 _라우트 응답_ 만 검증했지만, 실제 서비스엔 DB / 캐시 / 외부 API 가 잔뜩. 이 단계에서 **3계층 테스트** 를 정착시킨다.

| 계층 | 외부 의존성 | 속도 | 도커 필요? |
|---|---|---|---|
| **unit** | 없음 | 매우 빠름 (ms) | ❌ |
| **integration** | 진짜 Postgres / Redis (testcontainers) | 보통 (초) | ✅ |
| **e2e** | 풀 스택 (FastAPI + DB + Redis) | 느림 (수 초) | ✅ |

도커 데몬 안 켜져 있으면 integration / e2e 는 _자동 스킵_, unit 만 돈다.

## 학습 목표

- **fixture scope** (function / module / session) — 비싼 자원은 session
- **`pytest.mark.parametrize`** — 입력 표를 한 함수로
- **마커** (`@pytest.mark.integration`) + `pyproject.toml` 등록
- **`testcontainers-python`** — 진짜 Postgres / Redis 컨테이너
- **`app.dependency_overrides`** — 의존성 한 줄 교체
- **커버리지** (`pytest-cov`) — 미커버 라인 보기
- 자동 스킵 패턴 — _도커 없을 때_ 친절하게 동작

## 디렉토리

```
08-testing/
├── pyproject.toml          # psycopg / redis / testcontainers (dev)
├── Makefile                # make test / test-unit / test-integration / test-e2e / cov
├── README.md
├── src/testapp/            # _테스트 대상_ 작은 앱
│   ├── settings.py         # pydantic-settings (override 대상)
│   ├── repository.py       # Postgres + 순수 함수 discounted_price
│   ├── cache.py            # Redis HitCounter
│   └── main.py             # FastAPI + Depends 주입
└── tests/
    ├── conftest.py         # fixture: postgres_url/redis_url (session) + db_conn/redis_client (function) + app_client (e2e)
    ├── test_unit.py        # discounted_price (도커 무관)
    ├── test_integration.py # ItemRepository, HitCounter (testcontainers)
    └── test_e2e.py         # FastAPI 풀 스택 (testcontainers + dependency_overrides)
```

## 실행

```bash
cd .. && uv sync && cd 08-testing

# 도커 안 켜져 있어도 OK — unit 만 돈다
make test

# 도커 켜고 전체
open -a Docker
make test                  # unit + integration + e2e (testcontainers 자동)

# 부분 실행
make test-unit             # unit 만
make test-integration      # 통합만
make test-e2e              # e2e 만

# 커버리지
make cov                   # term-missing + htmlcov/index.html
```

## 다국 언어 비교 — 거의 _동일_ 모델

| 도구 | 가장 가까운 비교 |
|---|---|
| **pytest** | JUnit 5, Jest, Mocha |
| **fixture (scope)** | JUnit `@TestInstance(PER_CLASS)`, Jest `beforeAll/beforeEach` |
| **parametrize** | JUnit `@ParameterizedTest`, Jest `test.each()` |
| **마커** | JUnit `@Tag`, Jest 의 `describe`/`describe.skip` |
| **`testcontainers-python`** | **JUnit Testcontainers** (거의 1:1!), `@nestjs/testing` + testcontainers-node |
| **`dependency_overrides`** | Spring `@MockBean`, NestJS `Test.createTestingModule().overrideProvider(...)` |
| **`pytest-cov`** | JaCoCo, Istanbul (nyc) |
| **마커 자동 스킵** | JUnit `Assumptions.assumeTrue(dockerAvailable)` |

JUnit + Testcontainers 사용해본 사람이면 _모델이 동일_ — 컨테이너를 띄우고, 끝나면 자동 정리, 비싼 거니 `@Container` 가 클래스 단위. pytest 는 fixture scope 로 같은 효과.

## 핵심 개념

### 1) fixture scope — _비싼 자원은 session_

```python
@pytest.fixture(scope="session")    # 전체 세션 _한 번_ — Postgres 컨테이너
def postgres_url(): ...

@pytest_asyncio.fixture              # 기본은 function scope — 매 테스트 새 connection
async def db_conn(postgres_url): ...
```

**규칙**: 컨테이너 자체 = session, connection / 데이터 = function.
function 안에서 데이터를 _초기화_ (`flushdb`, `TRUNCATE`) 해서 격리.

### 2) parametrize — 입력 표를 한 함수로

```python
@pytest.mark.parametrize(
    ("original", "percent", "expected"),
    [
        (1000, 10, 900),
        (1000, 25, 750),
        (1000, 33, 670),
    ],
    ids=["10pct", "25pct", "33pct-truncated"],   # 실패 시 어느 케이스인지 명확히
)
def test_various(original, percent, expected): ...
```

- `ids=` 안 주면 자동 ID — 그래도 보통 명시 권장 (실패 출력 가독성)
- `indirect=True` 로 fixture 자체를 parametrize 가능 (고급)

### 3) 마커 — 카테고리 분리

```python
# 파일 또는 클래스/함수 위에
pytestmark = pytest.mark.integration

# 또는
@pytest.mark.e2e
async def test_full_stack(...): ...
```

루트 `pyproject.toml` 의 `[tool.pytest.ini_options] markers` 에 등록 필요 (안 하면 PytestUnknownMarkWarning).

```bash
pytest -m integration              # 통합만
pytest -m "not integration"        # 그 외 (= unit)
pytest -m "integration and not e2e"
```

### 4) testcontainers — 진짜 Postgres / Redis

```python
@pytest.fixture(scope="session")
def postgres_url() -> Iterator[str]:
    if not _docker_available():
        pytest.skip("도커 데몬 없음")

    from testcontainers.postgres import PostgresContainer
    with PostgresContainer("postgres:16-alpine", driver=None) as pg:
        yield pg.get_connection_url()
    # with 끝 = 자동 정리 ✅
```

- `with` 컨텍스트 매니저 — 예외 발생해도 _컨테이너 정리 보장_
- `driver=None` — psycopg 표준 URL (`postgresql://...`)
- session scope 로 _한 번_ 만 띄우고 모든 통합 테스트 공유

### 5) `dependency_overrides` — Settings 한 줄 교체

```python
@pytest_asyncio.fixture
async def app_client(postgres_url, redis_url):
    app = create_app()

    def _test_settings():
        return Settings(database_url=postgres_url, redis_url=redis_url)

    app.dependency_overrides[get_settings] = _test_settings
    # ... 테스트 ...
    app.dependency_overrides.clear()    # 다음 테스트에 영향 X
```

**FastAPI 테스팅의 마법** — Settings 만 갈아끼우면 _그 아래 의존성 트리 전부_ 자동으로 테스트 컨테이너에 연결. `get_db_conn`, `get_redis` 도 Settings 를 통해 흐르니까.

비교: **Spring `@MockBean`**, **NestJS `overrideProvider`** 와 같은 자리.

### 6) 도커 자동 스킵 — 친절한 디폴트

```python
def _docker_available() -> bool:
    try:
        import docker
        docker.from_env(timeout=2).ping()
        return True
    except Exception:
        return False
```

도커 안 켜져 있어도 unit 은 _그냥 통과_. CI 의 _빠른 PR 검증_ 잡 (도커 X) + _야간 통합_ 잡 (도커 O) 분리도 자연스러움.

## 테스트 피라미드

```
        ▲ e2e (수)
        │
       ▲▲ integration (수십)
       ││
      ▲▲▲ unit (수백~수천)
```

**비율 가이드**: unit ≫ integration > e2e. unit 이 빠르고 결정적이라 _대부분_ 의 검증을 담당. e2e 는 _가장 중요한 골든 패스_ 만.

## 안티패턴

1. **모든 테스트를 e2e 로** — 느리고 fragile. 도메인 로직은 unit, DB 동작은 integration, _플로우_ 만 e2e.
2. **테스트 순서에 의존** — pytest 는 _순서 보장 안 함_. 격리된 fixture + 매 테스트 데이터 정리.
3. **session-scope DB connection** — 한 테스트의 미정리 트랜잭션이 다음 테스트 오염. function scope 권장.
4. **mock 으로 _DB 동작 자체_ 흉내** — 마이그레이션·인덱스·제약조건 검증 못 함. testcontainers 가 답.
5. **`@pytest.fixture(autouse=True)` 남발** — 어디서 적용되는지 추적 어려움. 명시 인자가 가독성 ↑.
6. **테스트 안에서 시간 / UUID 직접 사용** — flaky. `freezegun`, fixture 로 주입.
7. **`requests.get(...)` 으로 진짜 외부 API 호출** — 네트워크 의존. respx (httpx mock) 또는 testcontainers.
8. **커버리지 100% 강박** — 이미 _자명한_ 코드까지 테스트 → 보일러플레이트. 도메인 로직 우선.

## 직접 해보기 TODO

- [ ] `make cov` 후 `htmlcov/index.html` 열어서 미커버 라인 확인
- [ ] `discounted_price` 에 `discount > 0` 입력에서 _최소 1원_ 보장 (즉 `0` 반환 X) 규칙 추가하고 unit 테스트
- [ ] `ItemRepository` 에 `update_price(item_id, new_price)` 추가, integration 테스트
- [ ] `app_client` fixture 를 `module` scope 로 바꾸면 어떻게 되는지 (오염 / 속도 trade-off)
- [ ] testcontainers 의 `with_command(...)` / `with_env(...)` 로 Postgres 의 `shared_buffers` 변경
- [ ] `httpx` 외부 호출 mocking — `respx` 라이브러리 추가해서 `t02_httpx` 패턴 검증
- [ ] CI 에서 도커 켜진 잡과 안 켜진 잡 분리하는 가상 GitHub Actions YAML 작성

## 다음 단계

**09 — 인증·인가**. JWT, OAuth2 password flow, RBAC, 비밀번호 해싱, CORS/CSRF 기본. 08 의 `dependency_overrides` 패턴이 _인증된 사용자_ 를 테스트에서 mock 하는 데 그대로 쓰임.
