# FastAPI Best Practice 템플릿 — 실무 시작 키트

git clone 후 _바로_ 실무 백엔드 작성 시작 가능한 FastAPI 템플릿.

## 빠른 시작

```bash
cp .env.example .env

# DB + Redis 띄우기
make compose-up

# 의존성 + 마이그레이션 + 서버
uv sync
make migrate
make run

# 다른 터미널에서
curl http://127.0.0.1:8000/healthz
open http://127.0.0.1:8000/docs
```

테스트 (도커 데몬 필요):

```bash
make test       # 39 tests (14 unit + 25 integration)
make all        # ruff + mypy + test
```

## 포함 ✅ / 제외 ❌

| 영역 | 포함 ✅ | 제외 ❌ |
|---|---|---|
| Web | FastAPI factory + lifespan + correlation-id 미들웨어 | API v1/v2 분리 |
| 인증 | JWT + bcrypt + RBAC (`require_role`) | OAuth 3rd party / mTLS / API key |
| DB | SQLAlchemy 2.0 async + Alembic + UoW | DDD 헥사고날 (단순 layered) |
| Cache | Redis cache-aside + invalidate | stampede 방지 / Saga / CQRS |
| Messaging | — | Kafka / outbox |
| 관측 | structlog JSON + correlation-id | Sentry / OTel / SLO / Grafana |
| 배포 | Docker multi-stage + GH Actions + GHCR | Helm chart / K8s manifests |
| i18n | — | Babel / gettext |

필요한 영역은 _학습 모노레포_ 의 해당 단계에서 _복사_:
- Kafka outbox → `13-kafka-queue/` + `15-mini-project/src/tender/models.py:OutboxEvent`
- Sentry/OTel/SLO → `A12-observability/`
- DDD 헥사고날 → `A11-ddd/`
- Helm chart → `A4-kubernetes/helm/`
- i18n → `A1-i18n/`
- 캐시 stampede / Saga → `A7-cache-mq-deep/`

## 디렉토리 구조

```
src/app/
├── main.py             create_app() factory + lifespan + /healthz
├── core/               인프라 공통 (envelope/errors/handlers/correlation/logging/settings/security)
├── db/                 base / session / models / uow
├── cache/              ItemCache (cache-aside)
├── deps/               get_current_user + require_role
├── domain/
│   ├── users/          schemas + repository + service + router (signup/login/me)
│   └── items/          schemas + repository + service + router (CRUD + owner 가드)
└── api/v1.py           /api/v1 prefix 통합

alembic/                마이그레이션
tests/
├── unit/               DB 없는 순수 로직 (security, schemas, envelope)
└── integration/        testcontainers Postgres + Redis (e2e)
```

## API 엔드포인트

| 메서드 | 경로 | 인증 | 설명 |
|---|---|---|---|
| GET | `/healthz` | — | Docker HEALTHCHECK (envelope 미적용 — 단순 200) |
| POST | `/api/v1/users` | — | 회원가입 |
| POST | `/api/v1/auth/login` | — | 이메일+비밀번호 → JWT |
| GET | `/api/v1/me` | ✅ | 본인 정보 |
| POST | `/api/v1/items` | ✅ | 아이템 생성 |
| GET | `/api/v1/items` | ✅ | 본인 아이템 목록 (limit/offset 페이지) |
| GET | `/api/v1/items/{id}` | ✅ | 단건 조회 (owner 만) |
| PUT | `/api/v1/items/{id}` | ✅ | 부분 업데이트 (owner 만) |
| DELETE | `/api/v1/items/{id}` | ✅ | 삭제 (owner 만) |

모든 응답 (healthz 제외) 은 `ApiEnvelope`:
```json
{ "code": "OK", "message": "ok", "data": { ... } }
```

에러도 같은 형식 (4xx / 5xx):
```json
{ "code": "NOT_FOUND", "message": "item not found", "data": null }
```

## Rename guide — fork 후 _4가지 토큰_ 검색-치환

다른 프로젝트로 시작할 때 이 4개를 자기 이름으로:

| # | 위치 | 변경 전 | 변경 후 (예) |
|---|---|---|---|
| 1 | `pyproject.toml` `[project] name` | `app` | `myapi` |
| 2 | `pyproject.toml` `[tool.hatch.build.targets.wheel] packages` + 디렉토리 `src/app/` | `app` | `myapi` |
| 3 | `src/app/core/settings.py` `env_prefix` + `.env.example` 의 `APP_*` | `APP_` | `MYAPI_` |
| 4 | `src/app/main.py` FastAPI `title="app"` | `app` | `MyAPI` |

전체 치환 도우미 (sed):

```bash
# 1) 모든 .py 의 `from app.` / `import app.` → `from myapi.` 로
grep -rl "from app\." src tests alembic | xargs sed -i '' 's/from app\./from myapi./g'
grep -rl "import app\." src tests alembic | xargs sed -i '' 's/import app\./import myapi./g'

# 2) 디렉토리 이동
git mv src/app src/myapi

# 3) pyproject.toml 의 packages
sed -i '' 's|packages = \["src/app"\]|packages = ["src/myapi"]|' pyproject.toml
sed -i '' 's|^name = "app"|name = "myapi"|' pyproject.toml

# 4) env_prefix
sed -i '' 's/env_prefix="APP_"/env_prefix="MYAPI_"/' src/myapi/core/settings.py
sed -i '' 's/^APP_/MYAPI_/' .env.example

# 5) FastAPI title
sed -i '' 's/title="app"/title="MyAPI"/' src/myapi/main.py

# 6) 검증
grep -rn "app\." src tests alembic --include="*.py"  # 누락 확인
make all  # 전부 통과해야
```

> macOS sed 는 `-i ''` (빈 인자), Linux 는 `-i` 만.

## Repository 패턴 — `BaseRepo[T]` + `Page[T]` / `PageResponse[T]`

본 템플릿은 _도메인별 Repository 분리_ 와 _공통 CRUD 추상화_ 를 _둘 다_ 가짐:

```python
# db/repository_base.py — 공통
class BaseRepo[T: Base]:        # PEP 695 generic
    model: type[T]
    not_found_error: type[NotFoundError] = NotFoundError

    async def add(**fields)        -> T
    async def get(id)              -> T | None
    async def get_or_404(id)       -> T          # 자동 도메인 예외
    async def list_(*, limit, offset, where=None) -> Page[T]
    async def update(obj, **fields) -> T          # PATCH 의미 (None 무시) + refresh
    async def delete(obj)          -> None
    def _base_select(where)        -> Select[T]   # 자식이 도메인 쿼리 시 재사용
    async def _paginate(stmt, ...)  -> Page[T]    # 자식이 도메인 페이지 시 재사용

# 도메인 Repository = 5 줄
class ItemRepo(BaseRepo[Item]):
    model = Item
    not_found_error = ItemNotFoundError

    # 도메인 특화 쿼리만
    async def list_by_owner(self, owner_id, *, limit, offset) -> Page[Item]:
        stmt = self._base_select(Item.owner_id == owner_id).order_by(Item.id.desc())
        return await self._paginate(stmt, limit=limit, offset=offset)
```

**페이지네이션 — `Page[T]` (내부) vs `PageResponse[T]` (응답)**:
- `Page[T]` 는 **dataclass** — Repository 가 ORM 객체 (Item 등) 그대로 담음
- `PageResponse[T]` 는 **Pydantic BaseModel** — 라우터 응답 (`response_model`) 으로 OpenAPI 정상 생성
- 라우터에서 `PageResponse[ItemPublic].from_page(page, transform=ItemPublic.model_validate)` 로 변환

> Pydantic generic + ORM 조합은 까다로워 (PydanticSchemaGenerationError) _내부/응답 표현 분리_.

응답 형식:
```json
{
  "code": "OK",
  "message": "ok",
  "data": {
    "items": [...],
    "total": 42,
    "limit": 10,
    "offset": 0,
    "has_next": true
  }
}
```

## 새 도메인 추가 가이드

5 줄 Repository:

```python
# domain/products/repository.py
class ProductRepo(BaseRepo[Product]):
    model = Product
    not_found_error = ProductNotFoundError
```

체크리스트:
- [ ] `db/models.py` 에 `Product` 모델 추가
- [ ] `core/errors.py` 에 `ProductNotFoundError(NotFoundError)` 추가 (선택)
- [ ] `db/uow.py` 에 `products: ProductRepo` 필드 + `__aenter__` 인스턴스화
- [ ] `domain/products/repository.py` — `BaseRepo[Product]` 상속, _도메인 특화 쿼리만_
- [ ] `domain/products/schemas.py` — Pydantic (Create/Update/Public)
- [ ] `domain/products/service.py` — UoW + owner 가드 (필요 시) + cache invalidate
- [ ] `domain/products/router.py` — `BaseRepo` 의 `add`/`get_or_404`/`update`/`delete` 활용
- [ ] `api/v1.py` — `router.include_router(products_router)` 추가
- [ ] `alembic/versions/0002_add_products.py` — 마이그레이션
- [ ] `tests/integration/test_products_crud.py` — e2e 테스트

## 알려진 한계 / Pitfalls

운영 fork 시 자주 막히는 부분:

1. **`get_settings` `@lru_cache` + 환경변수 변경**
   테스트에서 `os.environ[...] = ...` 후 반드시 `get_settings.cache_clear()` 호출. `tests/conftest.py` 의 `app_client` fixture 가 정확히 이 패턴.

2. **bcrypt 4.1+ passlib 호환성**
   `pyproject.toml` 에 `bcrypt<4.1` 핀 유지 필수. passlib 1.7.4 가 bcrypt 4.1+ 의 `__about__` 속성 제거에 적응 못함.

3. **Alembic sync vs async URL**
   앱은 `postgresql+asyncpg://`, alembic 은 `postgresql+psycopg://`. testcontainer 양쪽 URL 다 만드는 패턴.

4. **testcontainers ryuk + macOS**
   `os.environ.setdefault("TESTCONTAINERS_RYUK_DISABLED", "true")` 가 conftest 최상단 (다른 import 전) 에. 위치 잘못 잡으면 컨테이너 정리 안 됨.

5. **owner 권한 가드 누락 = IDOR (CWE-639)**
   `items/service.py` 의 모든 단일 조회/수정/삭제에 `_assert_owner` 호출 필수. integration 테스트로 강제 (`test_owner_guard_blocks_other_user`).

6. **OAuth2PasswordBearer tokenUrl 와 라우터 prefix 불일치**
   `tokenUrl="/api/v1/auth/login"` 이어야 Swagger UI Authorize 동작. `/auth/login` 만 쓰면 Swagger 에서 401 만 보고 헤맴.

7. **`response_model=ApiEnvelope[T]` 와 4xx 의 dual response**
   DomainError 핸들러가 4xx/5xx envelope 반환하지만 OpenAPI 스키마에는 _200 응답만_ 등록. 운영 SDK 자동생성 시엔 [`responses=...`](https://fastapi.tiangolo.com/advanced/additional-responses/) 추가 검토.

8. **`onupdate=func.now()` + DetachedInstanceError**
   `Item.updated_at` 같은 server-side onupdate 컬럼은 flush 후 `await session.refresh(item)` 필수. 안 하면 session close 후 속성 접근 시 lazy refresh 실패.

9. **lifespan 안에서 alembic 자동 실행 유혹**
   "편하게" `await alembic.upgrade(...)` 호출 유혹 → 멀티 인스턴스 race / 권한 분리 어려움. _절대 금지_. 별도 `make migrate` 또는 K8s init container.

10. **`/healthz` envelope 미적용** (의도적)
    Docker HEALTHCHECK 가 단순 HTTP 200 만 봄. 일관성보단 _운영성_ 우선.

11. **Docker compose 호스트명 차이**
    호스트 (개발자) → `localhost:5432`, 컨테이너 안 → `db:5432`. `.env.example` 은 호스트 기준, compose 의 app 서비스가 environment 로 컨테이너 URL 덮어씀.

## 다음 단계 (선택)

- [ ] **API 버전 분리** — v2 추가 → `api/v1.py` + `api/v2.py` + Deprecation 헤더 (모노레포 `07-request-error-version/`, `15-mini-project/src/tender/api/v1.py` 참고)
- [ ] **Sentry + OTel** — `A12-observability/` 의 `sentry_setup.py`, `tracing.py` 포팅
- [ ] **Kafka outbox** — `13-kafka-queue/` + `15-mini-project/src/tender/models.py:OutboxEvent`
- [ ] **Helm chart** — `A4-kubernetes/helm/tender/` 복사 + values 조정
- [ ] **Property-based testing** — `Hypothesis` 로 schemas 검증 강화
- [ ] **OpenAPI codegen** — 클라이언트 SDK 자동 생성 (`openapi-generator-cli`)
- [ ] **Rate limit** — `11-redis-ratelimit/src/cacheapp/ratelimit.py` 포팅
- [ ] **DB 인덱스 전략** — `A6-db-deep/src/dbdeep/models.py` 의 GIN/부분/expression 인덱스 패턴

## 참고 자료 (학습 모노레포)

이 템플릿은 다음 모노레포 단계의 _운영급 패턴_ 추출:
- `15-mini-project/` — main.py / settings / models / uow / cache / auth 패턴
- `14-shared-package/` — envelope / handlers / correlation / logging
- `05-infra-compose/` — Dockerfile multi-stage
- `.github/workflows/` — CI / Docker build
