# 04 — FastAPI Hello + OpenAPI + 설정 관리

03 에서 만진 라이브러리들이 _진짜 웹 서버_ 위에 올라간다. 이 단계가 끝나면 `make run` 으로 실제 HTTP 서버가 떠 있고, 자동 생성된 OpenAPI 문서를 브라우저에서 볼 수 있다.

## 실행

```bash
# 루트에서 동기화 (한 번)
cd .. && uv sync
cd 04-fastapi-hello

# 개발 서버 — 자동 reload
make run
# → http://127.0.0.1:8000     (앱)
# → http://127.0.0.1:8000/docs  (Swagger UI)
# → http://127.0.0.1:8000/redoc (ReDoc)

# 다른 터미널에서 빠른 검증
make curl-demo

# 검증
make all     # ruff + mypy + pytest
```

## 디렉토리

```
04-fastapi-hello/
├── pyproject.toml          # fastapi, uvicorn[standard], pydantic, pydantic-settings, structlog, orjson
├── Makefile                # make run / test / lint / curl-demo
├── README.md
├── .env.example
├── src/app/
│   ├── __init__.py
│   ├── main.py             # FastAPI() + lifespan + 라우터 등록
│   ├── settings.py         # pydantic-settings 기반 Settings + Depends 싱글톤
│   ├── logging_setup.py    # structlog 환경별 설정 (dev=콘솔 / prod=JSON)
│   └── routers/
│       ├── health.py       # /healthz, /readyz (K8s liveness/readiness)
│       ├── items.py        # /items, /items/{id} — path/query 파라미터
│       └── echo.py         # /echo — POST 요청 본문 검증
└── tests/
    ├── conftest.py         # httpx.AsyncClient + ASGITransport 픽스처
    └── test_app.py         # 헬스 / 아이템 / 에코 / OpenAPI 검증
```

## 다국 언어 비교 — FastAPI 와 가장 가까운 것

| FastAPI | 가장 가까운 비교 |
|---|---|
| `FastAPI(...)` | **NestJS** `NestFactory.create(AppModule)`, **Spring Boot** `@SpringBootApplication` |
| `@app.get("/x")` | **Spring** `@GetMapping("/x")`, **NestJS** `@Get("x")`, **Express** `app.get("/x", ...)` |
| `APIRouter` | **NestJS** Module + Controller, **Spring** `@RestController` |
| `Pydantic 모델` 요청/응답 | **NestJS** `class-validator` DTO, **Spring** `@Valid @RequestBody` |
| `Depends()` | **Spring** `@Autowired`, **NestJS** constructor injection |
| `lifespan` | **Spring** `@PostConstruct` + `@PreDestroy`, **NestJS** `OnModuleInit` / `OnModuleDestroy` |
| 자동 OpenAPI | **Spring** Springdoc, **NestJS** `@nestjs/swagger` (이쪽들은 _수동 설정_ 필요, FastAPI 는 _자동_) |
| `HTTPException(404)` | **Spring** `ResponseStatusException`, **NestJS** `NotFoundException` |
| `/healthz` `/readyz` | **Spring Boot** `/actuator/health`, **K8s** liveness / readiness probe |

**FastAPI 의 차별점**: OpenAPI 가 _자동_. Pydantic 모델이 곧 OpenAPI 스키마. 별도 `@ApiProperty` / `@Schema` 안 붙여도 됨.

## 핵심 학습 포인트

### 1) 앱 팩토리 + lifespan

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup: DB pool, httpx client, Kafka producer 만들기
    yield
    # shutdown: close, dispose

def create_app() -> FastAPI:
    app = FastAPI(lifespan=lifespan, ...)
    app.include_router(...)
    return app
```

- `@asynccontextmanager` 가 _yield 이전/이후_ 를 startup/shutdown 으로 가르는 트릭
- `@app.on_event("startup")` 는 _deprecated_ — lifespan 이 표준
- 앱 팩토리 함수 (`create_app()`) 로 분리 — 테스트에서 _깨끗한 인스턴스_ 만들기 쉬움

### 2) `pydantic-settings` + `Depends(get_settings)` 싱글톤

```python
@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()

@router.get("/healthz")
async def healthz(settings: Annotated[Settings, Depends(get_settings)]) -> ...:
    return ...
```

`@lru_cache(maxsize=1)` 가 _순수 함수_ 결과를 캐시 → 첫 호출에 한 번만 만들고 이후 같은 객체 재사용. **Spring `@Bean` 싱글톤 자리**. 테스트에선 `app.dependency_overrides[get_settings] = lambda: TestSettings(...)` 로 _덮어쓰기_ 가능.

### 3) 자동 검증 — try/except 안 씀

```python
class EchoRequest(BaseModel):
    message: str = Field(min_length=1, max_length=200)
    repeat: int = Field(default=1, ge=1, le=10)

@router.post("/echo")
async def echo(payload: EchoRequest) -> EchoResponse:
    return EchoResponse(echoed=[payload.message] * payload.repeat, ...)
```

검증 실패하면 **FastAPI 가 _자동_ 으로 422 응답 + 어느 필드, 어떤 규칙 위반인지 JSON 으로**. 우리 코드는 try/except 한 번도 안 씀. 07 단계에서 _커스텀 에러 envelope_ 으로 모양 정리.

### 4) 헬스체크 — `/healthz` vs `/readyz`

| 엔드포인트 | 의미 | 실패 시 K8s 동작 |
|---|---|---|
| `/healthz` | _liveness_ — 프로세스 살아있는지 | **재시작** |
| `/readyz` | _readiness_ — 트래픽 받을 준비 (DB/Redis 등 의존성 OK) | **트래픽 차단** (재시작 X) |

이 단계에선 단순 OK. **10 단계 (DB)** 부터 `/readyz` 에 진짜 의존성 ping 추가.

### 5) 빠른 JSON 직렬화 — 이젠 자동

**옛 버전 FastAPI**:
```python
from fastapi.responses import ORJSONResponse
app = FastAPI(default_response_class=ORJSONResponse)
```

**FastAPI 0.111+**: ORJSONResponse 는 _deprecated_. Pydantic 이 _직접_ JSON bytes 로 직렬화하면서 자체 최적화 — 별도 설정 없이 빠름. 03 단계에서 본 orjson 의 _개념_ 은 여전히 유효하지만, FastAPI 라우트 응답엔 이제 **자동**.

## 안티패턴

1. **`@app.on_event("startup")` 사용** — deprecated. 항상 `lifespan`.
2. **앱을 모듈 최상위에서 `app = FastAPI(...)` 로만 만들기 — 테스트에서 격리 어려움**. 팩토리(`create_app()`) + 모듈 최하단에 `app = create_app()` 패턴이 표준.
3. **`Settings()` 를 매 요청마다 새로 만들기** — `lru_cache` 누락. 환경변수가 변하지 않는데 매번 파일 IO + 검증 비용 발생.
4. **검증 로직을 라우트 함수 안에 직접 작성** — Pydantic Field 제약으로 가능한 건 거기에. 도메인 검증만 함수 안에서 `HTTPException` 발생.
5. **`try/except` 로 422 직접 변환** — FastAPI 가 알아서 함. 직접 잡으면 OpenAPI 스키마와 불일치 위험.
6. **운영에서 `--reload` 켠 채 배포** — 파일 감시 오버헤드. `make run-prod` 처럼 워커 여러 개로.
7. **`/docs` 항상 노출** — 운영에선 공개 정보 적은 게 안전. `docs_enabled=False` 옵션으로 끔.

## TestClient vs httpx.AsyncClient — 어느 걸?

| 도구 | 언제 |
|---|---|
| `from fastapi.testclient import TestClient` | _동기_ 테스트, 빠른 데모 |
| **`httpx.AsyncClient + ASGITransport`** | _async_ 테스트, 실제 라우트가 async 일 때 |

이 단계에선 후자 사용 — 라우트가 `async def` 라 `pytest-asyncio` + `AsyncClient` 가 자연스러움. **NestJS `INestApplication.getHttpServer()` + supertest** 와 같은 자리.

## 직접 해보기 TODO

- [ ] `make run` 후 브라우저로 `/docs` 열기 — 자동 생성된 Swagger UI 확인
- [ ] `/docs` 의 "Try it out" 으로 `/echo` POST 호출
- [ ] `.env.example` 을 `.env` 로 복사 후 `APP_PORT=9000` 으로 바꾸고 재실행 — 9000 포트로 뜨는지
- [ ] `APP_DOCS_ENABLED=false` 로 설정 후 `/docs` 가 404 인지 확인
- [ ] `routers/items.py` 에 `POST /items` 추가 — 새 아이템 만들기 (Pydantic 요청 모델)
- [ ] `routers/items.py` 에 `DELETE /items/{id}` 추가 — `_DB.pop(item_id, None)`
- [ ] `app.dependency_overrides[get_settings]` 로 테스트에서 `env="prod"` 강제하는 케이스 작성

## 다음 단계

**05 — Docker Compose 인프라 일괄 도입**. Postgres / Redis / Kafka 를 _하나의 compose_ 로 띄우고, FastAPI 컨테이너화 (Dockerfile multi-stage). 06 이후 단계가 _전부 이 위에서_ 동작.
