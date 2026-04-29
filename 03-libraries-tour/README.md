# 03 — 자주 쓰는 Python 라이브러리 투어

FastAPI 베스트 프랙티스의 _구성 요소_ 들. 이 단계에서 한 번씩 만져두면 04~13 단계가 훨씬 매끄럽습니다.

## 다루는 라이브러리

| # | 라이브러리 | 가장 가까운 비교 | 학습 모듈 |
|---|---|---|---|
| t01 | **pydantic** v2 | TS `zod`, Kotlin data class + jakarta.validation | `src/libtour/t01_pydantic.py` |
| t02 | **httpx** | TS `axios`/`fetch`, Kotlin `ktor-client` | `src/libtour/t02_httpx.py` |
| t03 | **orjson** | Node 내장 `JSON`, Java `Jackson` | `src/libtour/t03_orjson.py` |
| t04 | **jsonpath-ng** + deep merge | JS `lodash.get`/`lodash.merge`, Java Jayway JsonPath | `src/libtour/t04_jsonpath.py` |
| t05 | **datetime + zoneinfo + dateutil** | Kotlin `java.time`, JS `dayjs`/`date-fns` | `src/libtour/t05_datetime.py` |
| t06 | **structlog** | Node `pino`, Java SLF4J + MDC | `src/libtour/t06_logging.py` |
| t07 | **dotenv + pydantic-settings** | Spring `@ConfigurationProperties`, Node `dotenv` | `src/libtour/t07_dotenv.py` |

## 실행

```bash
# 루트에서 한 번 (의존성 + 패키지 install)
cd .. && uv sync
cd 03-libraries-tour

make run                          # 7개 데모 순차 실행
make demo M=t01_pydantic          # 하나만
make test                         # pytest (mock 으로 외부 호출 없음)
make all                          # lint + typecheck + test
```

## 핵심 학습 포인트 — 다국 언어 비교

### pydantic ≈ TS `zod`

```typescript
// TS / zod
const User = z.object({ id: z.number(), name: z.string() });
User.parse(data);
```

```python
# Python / pydantic
class User(BaseModel):
    id: int
    name: str
User.model_validate(data)
```

**FastAPI 의 모든 요청·응답 검증 = pydantic**. 04 단계의 핵심 의존성. zod 와 거의 같은 모델 — 타입 힌트만 달면 _런타임 검증_ 까지.

### httpx — sync/async 둘 다

| 도구 | sync | async |
|---|---|---|
| `requests` | ✅ | ❌ |
| `aiohttp` | ❌ | ✅ |
| **`httpx`** | ✅ | ✅ |
| Node `axios` | ✅ | ✅ (Promise) |
| Kotlin `ktor-client` | ✅ | ✅ (suspend) |

FastAPI 가 권장. `asyncio.gather` 로 병렬 호출 → Kotlin `coroutineScope { async {} }` 자리.

### structlog — MDC 패턴 그대로

```python
log = structlog.get_logger().bind(request_id="req-abc", user_id=42)
log.info("order.created", order_id="ord-123")
# → {"event": "order.created", "request_id": "req-abc", "user_id": 42, "order_id": "ord-123"}
```

Java SLF4J + MDC 와 같은 자리. 12 단계 (correlation-id, OpenTelemetry) 의 기반.

### orjson — datetime 자동 직렬화

표준 `json` 은 `datetime` / `UUID` 직렬화 못 함 (TypeError). `orjson` 은 그냥 됨. 더불어 _훨씬 빠름_ — Rust 작성. FastAPI `ORJSONResponse` 가 이걸 사용.

### deep merge — `{**a, **b}` 의 한계 보완

```python
{**{"meta": {"x": 1}}, **{"meta": {"y": 2}}}    # → {"meta": {"y": 2}}  ❌ x 잃음
deep_merge({"meta": {"x": 1}}, {"meta": {"y": 2}})  # → {"meta": {"x": 1, "y": 2}} ✅
```

JS lodash `_.merge` 와 동일. 환경별 설정 병합(`default + local + secret`) 의 표준 도구.

### datetime 의 _가장 큰 함정_ — naive vs aware

```python
datetime.now()                       # ❌ naive — tzinfo 없음, 사고 빈발
datetime.now(UTC)                    # ✅ aware UTC — 권장
datetime.now(ZoneInfo("Asia/Seoul")) # ✅ aware KST
```

**규칙**: 코드/DB 는 UTC aware, 사용자 표시는 그 사람 타임존. Kotlin `Instant`/`ZonedDateTime` 모델과 동일.

### pydantic-settings ≈ Spring `@ConfigurationProperties`

```python
class Settings(BaseSettings):
    database_url: str = "postgresql://localhost/dev"
    debug: bool = False
    api_timeout_ms: int = Field(default=5000, ge=100, le=30_000)

settings = Settings()    # ← 환경변수/.env 자동 로드 + 타입 변환 + 검증
```

04 단계에서 본격 도입. Java Spring 의 type-safe configuration 그대로.

## 라이브러리 검색·평가 기준

### 검색

| 도구 | 어디서 |
|---|---|
| **PyPI** | <https://pypi.org> — 공식 인덱스 |
| **GitHub** | 보통 PyPI 페이지에 링크 |
| **uv add --dry-run pkg** | 설치 안 하고 버전 후보 확인 |
| **Awesome Python** | <https://github.com/vinta/awesome-python> — 큐레이션 |

### 평가 기준 (npm 평가와 거의 동일)

| 기준 | 어디서 보나 |
|---|---|
| **GitHub stars** | 절대 수보다 _최근 활동_ 이 더 중요 |
| **최근 릴리스 / 커밋** | 1년 이상 잠잠하면 의심 |
| **다운로드 수** | <https://pypistats.org> (npm `npm-stat` 자리) |
| **이슈 / PR 응답성** | 메인테이너가 살아있는가 |
| **의존성 그래프** | `uv tree` 로 _깊이_ 와 _라이센스_ 확인 |
| **타입 힌트 지원** | `py.typed` 마커 있는지 (mypy 친화) |
| **보안 취약점** | `pip-audit`, GitHub Dependabot |

### 안티패턴

1. **stars 만 보고 결정** — 옛날 인기 라이브러리가 _죽어있을_ 수 있음
2. **`pip install` 으로 즉흥 추가** — `uv add` 로 lockfile 갱신 + 재현성 확보
3. **다중 라이브러리 _기능 중복_** — `requests` + `httpx` 같이 쓰면 의존성 부풀음
4. **메이저 버전 업그레이드 _바로_ 적용** — pydantic v1→v2 처럼 _대규모_ 마이그레이션 함정. 주변이 v2 안정화 후 따라가는 게 보통

## 안티패턴 — 라이브러리별 함정

| 라이브러리 | 함정 |
|---|---|
| **pydantic** | v1 코드 _그대로_ v2 사용 (`@validator` → `@field_validator`, `dict()` → `model_dump()`) |
| **httpx** | 매 요청마다 `AsyncClient()` 새로 만들기 → 커넥션 풀 못 씀. 앱 lifespan 동안 _하나_ 만들고 주입 |
| **orjson** | bytes 반환을 잊고 `str` 로 처리 시도 → `decode()` 필요 또는 `loads(bytes)` 직접 |
| **jsonpath** | 복잡한 표현식 남발 — 가독성 ↓. 단순 dict 접근이면 그냥 `data["a"]["b"]` |
| **datetime** | `datetime.now()` (naive) 그대로 비교/저장 — 사고. 항상 `datetime.now(UTC)` |
| **structlog** | 표준 `logging` 과 _혼용_ — 출력 포맷 깨짐. 앱 시작 시 한 번 configure, 이후 `structlog.get_logger()` |
| **dotenv** | 운영에서 `.env` 파일 _커밋_ — 시크릿 유출. `.env.example` 만 커밋, 실제 값은 secret manager |

## 직접 해보기 TODO

- [ ] `t01_pydantic` 의 `Customer` 에 `phone: str` 필드 추가하고 정규식 `pattern=r"^\d{2,3}-\d{3,4}-\d{4}$"` 검증
- [ ] `t02_httpx` 의 `make_mock_client` 에 `/orders/{id}` 라우트 추가
- [ ] `t04_jsonpath` 의 `deep_merge` 가 _list_ 를 만나면 어떻게 동작하는지 확인 (덮어쓰기 vs 합치기) — 도메인에 따라 정책 다름
- [ ] `t05_datetime` 에 `format_for_user(dt: datetime, locale: str) -> str` 추가
- [ ] `uv add pendulum --dry-run` 으로 datetime 의 _대안 라이브러리_ 후보 확인
- [ ] 본인이 자주 쓰는 다른 언어 라이브러리(zod / axios / lodash 등) 의 Python 대응을 PyPI 에서 찾아보기

## 다음 단계

**04 — FastAPI Hello + OpenAPI + 설정 관리**. 여기서 만진 pydantic + pydantic-settings + structlog + httpx 를 _실제 웹 서버_ 위에 올림.
