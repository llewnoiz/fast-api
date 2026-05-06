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
make test       # 69 tests (21 unit + 48 integration)
make all        # ruff + mypy + test
```

## 포함 ✅ / 제외 ❌

| 영역 | 포함 ✅ | 제외 ❌ |
|---|---|---|
| Web | FastAPI factory + lifespan + correlation-id + CORS + Security 헤더 | API v1/v2 분리 |
| 인증 | JWT access + refresh (Redis rotation) + bcrypt + RBAC + logout-all | OAuth 3rd party / mTLS / API key |
| 보안 | Rate limit (login) + PII 로그 redaction + CSP/HSTS/X-Frame-Options | mTLS / WAF / CSRF token |
| DB | SQLAlchemy 2.0 async + Alembic + UoW + 풀 튜닝 (Settings) | DDD 헥사고날 (단순 layered) |
| Cache | Redis cache-aside + invalidate | stampede 방지 / Saga / CQRS |
| 관측 | structlog JSON (PII redact) + correlation-id + `/healthz` + `/readyz` | Sentry / OTel / SLO / Grafana |
| 테스트 | unit (service mock) + integration (testcontainers) | 트랜잭션 롤백 격리 (savepoint) |
| 배포 | Docker multi-stage + non-root + HEALTHCHECK + GH Actions + GHCR | Helm chart / K8s manifests |
| i18n | — | Babel / gettext |

필요한 영역은 _학습 모노레포_ 의 해당 단계에서 _복사_:
- Kafka outbox → `13-kafka-queue/` + `15-mini-project/src/tender/models.py:OutboxEvent`
- Sentry/OTel/SLO → `A12-observability/`
- DDD 헥사고날 → `A11-ddd/`
- Helm chart → `A4-kubernetes/helm/`
- i18n → `A1-i18n/`
- 캐시 stampede / Saga → `A7-cache-mq-deep/`

## 디렉토리 구조 (Layered)

```
src/app/
├── main.py                  create_app() factory + lifespan + /healthz + /readyz
├── core/                    인프라 공통
│   ├── settings.py
│   ├── envelope.py / errors.py / handlers.py
│   ├── correlation.py / logging.py
│   ├── security.py / refresh_store.py
│   ├── security_headers.py
│   └── ratelimit.py
├── db/                      _데이터 layer 공유_ (cross-import 자유)
│   ├── base.py              DeclarativeBase
│   ├── session.py           engine + sessionmaker
│   ├── models.py            User + Item (한 파일 — 5+ 모델 되면 폴더 split)
│   ├── repository_base.py   BaseRepo[T] + Page + PageResponse
│   ├── repositories/
│   │   ├── users.py         UserRepo
│   │   └── items.py         ItemRepo (cross-join: get_with_owner)
│   └── uow.py
├── schemas/                 Pydantic — cross-import 한 방향 (items → users)
│   ├── users.py             UserCreate / UserPublic / OwnerSummary / Login / Token
│   └── items.py             ItemCreate / ItemUpdate / ItemPublic / ItemDetail (with owner)
├── cache/client.py          ItemCache (cache-aside)
├── deps/auth.py             get_current_user / require_role / get_uow
├── services/                얇은 layer — UoW 시작 + 도메인 호출 + cache invalidate
│   ├── users.py             signup / authenticate
│   └── items.py             create / get / list / update / delete + owner 가드
├── routers/                 FastAPI routers
│   ├── users.py             POST /users (signup)
│   ├── auth.py              POST /auth/{login, refresh, logout, logout-all}
│   ├── me.py                GET /me
│   └── items.py             items CRUD + /items/{id}/detail (cross-domain)
└── api/v1.py                APIRouter(prefix="/api/v1") + 4 router include

alembic/                     마이그레이션
tests/
├── unit/                    DB 없는 순수 로직 (security / schemas / envelope / services)
└── integration/             testcontainers Postgres + Redis (e2e)
```

> **왜 Layered?** 본 템플릿은 _단일 서비스_ (모놀리식). 도메인 폴더 분리는 _격리_ 보단
> _import 부담_ 만 만든다. repository 끼리 _서로 조인 자유_ + schemas cross-import 자유.
> 진짜 bounded context (마이크로서비스) 결정 시 _그때_ 재구조화. 0.3.0 의 핵심 변경.

## API 엔드포인트

| 메서드 | 경로 | 인증 | 설명 |
|---|---|---|---|
| GET | `/healthz` | — | Liveness probe (envelope 미적용) |
| GET | `/readyz` | — | Readiness probe — DB / Redis 응답 가능 검사 |
| POST | `/api/v1/users` | — | 회원가입 |
| POST | `/api/v1/auth/login` | — (rate-limited) | 이메일+비밀번호 → access + refresh 페어 |
| POST | `/api/v1/auth/refresh` | — | refresh → 새 페어 (rotation, 옛 토큰 자동 revoke) |
| POST | `/api/v1/auth/logout` | — | 현재 디바이스 logout (refresh 1개 revoke) |
| POST | `/api/v1/auth/logout-all` | ✅ | 모든 디바이스 logout |
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

## 새 도메인 추가 가이드 (Layered)

5 곳에 파일 추가. 5 줄 Repository:

```python
# db/repositories/products.py
class ProductRepo(BaseRepo[Product]):
    model = Product
    not_found_error = ProductNotFoundError
    # 도메인 특화 쿼리만 — cross-join 자유 (Layered 구조)
```

체크리스트:
- [ ] `db/models.py` 에 `Product` 모델 추가 (relationship 도 자유 선언)
- [ ] `core/errors.py` 에 `ProductNotFoundError(NotFoundError)` 추가 (선택)
- [ ] `db/repositories/products.py` — `BaseRepo[Product]` 상속, _도메인 특화 쿼리만_
- [ ] `db/uow.py` 에 `products: ProductRepo` 필드 + `__aenter__` 인스턴스화
- [ ] `schemas/products.py` — Pydantic (Create/Update/Public)
- [ ] `services/products.py` — UoW 시작 + owner 가드 (필요 시) + cache invalidate
- [ ] `routers/products.py` — `BaseRepo` 의 `add`/`get_or_404`/`update`/`delete` 활용
- [ ] `api/v1.py` — `router.include_router(products_router)` 추가
- [ ] `alembic/versions/0002_add_products.py` — 마이그레이션
- [ ] `tests/integration/test_products_crud.py` — e2e 테스트
- [ ] (필요 시) `tests/unit/test_product_service.py` — UoW mock

## Cross-domain 패턴 (Layered 의 가치)

본 템플릿이 보여주는 cross-domain 시연 — `GET /api/v1/items/{id}/detail`:

```python
# db/repositories/items.py — relation eager load (selectinload 으로 N+1 회피)
async def get_with_owner(self, item_id: int) -> Item:
    stmt = self._base_select(Item.id == item_id).options(selectinload(Item.owner))
    item = (await self._s.execute(stmt)).scalar_one_or_none()
    if item is None:
        raise self.not_found_error()
    return item

# schemas/items.py — schema cross-import (단방향: items → users)
from app.schemas.users import OwnerSummary

class ItemDetail(ItemPublic):
    owner: OwnerSummary

# routers/items.py — owner 정보 포함 응답
@router.get("/{item_id}/detail", response_model=ApiEnvelope[ItemDetail])
async def get_item_detail(...):
    async with uow:
        item = await uow.items.get_with_owner(item_id)
        # owner 가드 등 service 처럼 활용 가능 (또는 service 호출)
        return success(ItemDetail.model_validate(item))
```

다른 패턴:
- **Service 가 다른 repo 호출**: `services/items.py` 에서 `await uow.users.get_or_404(...)` 자유.
- **Router 가 여러 service 호출**: `routers/users.py` 가 `from app.services import users, items` 둘 다 import.
- **Composite view**: 큰 앱이면 `app/views/` 또는 `app/queries/` 신규 layer — `UserProfileView` 같은 read model 이 user + items + ... 종합. 본 템플릿엔 미도입 (도메인 2개 / 과한 layer).

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

## 운영 체크리스트 (배포 전)

### Secrets / 환경변수
- [ ] `APP_JWT_SECRET` / `APP_REFRESH_SECRET` — `python -c "import secrets; print(secrets.token_urlsafe(32))"` 로 생성, KMS / Vault / SealedSecrets 에 저장
- [ ] 두 secret 은 _서로 다름_ (액세스/리프레시 분리)
- [ ] `APP_CORS_ORIGINS` — 운영 도메인만, `*` 절대 X
- [ ] `.env` 는 git X (`.gitignore` 확인)

### DB
- [ ] `APP_DB_POOL_SIZE` — 부하 측정 후 조정 (워커당 보통 5~20)
- [ ] `APP_DB_POOL_RECYCLE` — 클라우드 DB idle timeout 보다 _작게_ (RDS 기본 8시간 → 1800s 권장)
- [ ] read replica 분리 (읽기 위주 트래픽 → SQLAlchemy `bind` 분기)
- [ ] 마이그레이션은 _별도_ `make migrate` (또는 K8s init container) — lifespan 자동 X

### 보안
- [ ] HTTPS 필수 (HSTS 자동 활성)
- [ ] CSP — SPA 호스팅 시 `script-src` / `connect-src` 추가
- [ ] CDN/WAF (Cloudflare / AWS WAF) 가 _앱 도달 전_ rate limit (본 모듈은 세컨드 라인)
- [ ] `bcrypt<4.1` 핀 유지 (passlib 호환)
- [ ] Audit log — 운영은 _감사 추적_ 별도 테이블 또는 외부 로그 인덱싱

### 관측가능성 (다음 단계)
- [ ] Sentry — `A12-observability/src/obsdeep/sentry_setup.py` 포팅
- [ ] OTel + Tempo / Jaeger / Datadog — `A12-observability/src/obsdeep/tracing.py`
- [ ] SLO + 알람 — `A12-observability/src/obsdeep/{slo,alerting,dashboards}.py`

### 인프라
- [ ] K8s Helm chart — `A4-kubernetes/helm/tender/`
- [ ] readiness probe = `/readyz`, liveness probe = `/healthz`
- [ ] HPA — CPU 70% 또는 RPS 기준
- [ ] Docker 이미지 보안 스캔 — Trivy / Grype CI 통합
- [ ] image 태그 = sha 또는 semver, _절대_ `latest` X

## 다음 단계 (도메인 / 기능 확장)

- [ ] **API 버전 분리** — v2 추가 → `api/v1.py` + `api/v2.py` + Deprecation 헤더 (`07-request-error-version/`, `15-mini-project/src/tender/api/v1.py` 참고)
- [ ] **Kafka outbox** — `13-kafka-queue/` + `15-mini-project/src/tender/models.py:OutboxEvent`
- [ ] **Property-based testing** — `Hypothesis` 로 schemas 검증 강화
- [ ] **OpenAPI codegen** — `openapi-generator-cli` 로 클라이언트 SDK 자동 생성
- [ ] **DB 인덱스 전략** — `A6-db-deep/` 의 GIN / 부분 / expression 인덱스 패턴
- [ ] **i18n** — `A1-i18n/` (Babel + gettext + Accept-Language)
- [ ] **DDD 헥사고날** — `A11-ddd/` (Aggregate / VO / Domain Event)
- [ ] **트랜잭션 롤백 테스트 격리** — TRUNCATE 대신 SAVEPOINT (테스트 빠르게)
- [ ] **WebSocket / SSE** — `A8-realtime/` (실시간 기능)

## Alembic 운영 패턴 — Expand-Contract 마이그레이션

스키마 변경 시 _zero-downtime_ 보장 패턴 (자세한 노트는 `A6-db-deep/README.md` 참고):

```
[Code v1, Schema v1]
        │ (1) Expand 마이그레이션 — 새 컬럼/인덱스 _추가만_ (NULL 허용)
        ▼
[Code v1, Schema v2]    ← 구 코드는 새 컬럼 무시 (호환)
        │ (2) Code v2 배포 — dual-write (구+신 양쪽에 쓰기)
        ▼
[Code v2, Schema v2]
        │ (3) Backfill 배치 — 과거 데이터 신 컬럼으로 채우기
        ▼
[Code v2, Schema v2 (filled)]
        │ (4) Code v3 배포 — 신 컬럼만 읽기/쓰기
        ▼
[Code v3, Schema v2]
        │ (5) Contract 마이그레이션 — 구 컬럼 drop / NOT NULL 강화
        ▼
[Code v3, Schema v3]
```

**해서는 안 되는 패턴** (모두 다운타임):
- `ADD COLUMN x NOT NULL` (기본값 없음) — _전 테이블 락_
- `ALTER COLUMN TYPE` (대형 변경) — 행 _재작성_
- `CREATE INDEX` (CONCURRENTLY 없이) — _쓰기 락_
- `RENAME COLUMN` _그 자리에서_ — 구 코드 즉시 깨짐

**Postgres 운영급 도구**:
- `CREATE INDEX CONCURRENTLY` — 락 없이 (Alembic `op.get_context().autocommit_block()` 안에서)
- `ALTER TABLE ... ADD CONSTRAINT ... NOT VALID` + `VALIDATE CONSTRAINT` — 큰 테이블 제약 추가 두 단계 분리
- `lock_timeout = '5s'` — 마이그레이션이 _영원히 락_ 못 잡게 가드

## 알려진 한계 / Pitfalls

운영 fork 시 자주 막히는 부분:

1. **`get_settings` `@lru_cache` + 환경변수 변경**
   테스트에서 `os.environ[...] = ...` 후 반드시 `get_settings.cache_clear()` 호출. `tests/conftest.py` 의 `app_client` fixture 가 이 패턴.

2. **bcrypt 4.1+ passlib 호환성**
   `pyproject.toml` 에 `bcrypt<4.1` 핀 유지 필수. passlib 1.7.4 가 bcrypt 4.1+ 의 `__about__` 속성 제거에 적응 못함.

3. **Alembic sync vs async URL**
   앱은 `postgresql+asyncpg://`, alembic 은 `postgresql+psycopg://`. testcontainer 양쪽 URL 다 만드는 패턴.

4. **testcontainers ryuk + macOS**
   `os.environ.setdefault("TESTCONTAINERS_RYUK_DISABLED", "true")` 가 conftest 최상단 (다른 import 전).

5. **owner 권한 가드 누락 = IDOR (CWE-639)**
   `items/service.py` 의 모든 단일 조회/수정/삭제에 `_assert_owner` 호출 필수. integration 테스트로 강제.

6. **OAuth2PasswordBearer tokenUrl 와 라우터 prefix 불일치**
   `tokenUrl="/api/v1/auth/login"` 이어야 Swagger UI Authorize 동작.

7. **Refresh token rotation 의 의미**
   사용된 refresh 는 _즉시_ revoke. 공격자가 훔친 refresh 사용 시 합법 사용자가 다음 시도에서 _이미 무효화_ 발견 → 의심 활동 알람.

8. **Rate limit 식별자**
   본 모듈은 IP 기준. 운영은 _IP + 인증된 user_ 이중. IPv6 회전 / NAT 공유 IP 고려.

9. **CORS `allow_credentials=True` + `allow_origins=["*"]` _금지_**
   CORS 사양 위반 — 브라우저가 차단. `allow_credentials=True` 면 명시적 origin 필수.

10. **`onupdate=func.now()` + DetachedInstanceError**
    server-side onupdate 컬럼은 flush 후 `await session.refresh(item)` 필수 (`BaseRepo.update` 가 이미 처리).

11. **lifespan 안에서 alembic 자동 실행 유혹**
    멀티 인스턴스 race / 권한 분리 어려움. _절대 금지_. 별도 `make migrate` 또는 K8s init container.

12. **DB 풀 고갈**
    `APP_DB_POOL_SIZE × 워커 수` 가 DB `max_connections` 보다 _작게_. 풀 고갈 시 `pool_timeout` 후 503 → SLO 위반.

13. **`/healthz` envelope 미적용** (의도적)
    Liveness probe 는 _프로세스 살아있음_ 만. 일관성보단 _운영성_ 우선.

14. **Docker compose 호스트명 차이**
    호스트 → `localhost:5432`, 컨테이너 안 → `db:5432`. `.env.example` 은 호스트 기준, compose 의 app 서비스가 environment 로 override.

## 참고 자료 (학습 모노레포)

이 템플릿은 다음 모노레포 단계의 _운영급 패턴_ 추출:
- `15-mini-project/` — main.py / settings / models / uow / cache / auth 패턴
- `14-shared-package/` — envelope / handlers / correlation / logging
- `11-redis-ratelimit/` — RateLimiter
- `A12-observability/` — PII redaction (`structured_logging.py`)
- `A6-db-deep/` — Alembic Expand-Contract
- `05-infra-compose/` — Dockerfile multi-stage
- `.github/workflows/` — CI / Docker build

## 참고 자료 (학습 모노레포)

이 템플릿은 다음 모노레포 단계의 _운영급 패턴_ 추출:
- `15-mini-project/` — main.py / settings / models / uow / cache / auth 패턴
- `14-shared-package/` — envelope / handlers / correlation / logging
- `05-infra-compose/` — Dockerfile multi-stage
- `.github/workflows/` — CI / Docker build
