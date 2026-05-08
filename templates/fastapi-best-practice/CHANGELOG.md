# Changelog

본 문서는 [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) 형식을 따른다.
버전은 [Semantic Versioning](https://semver.org/spec/v2.0.0.html) 준수.

## [Unreleased]

## [0.4.0] - 2026-05-07

### Changed — Production BFF 구조 정렬 (breaking change)

사용자가 _실제 운영 중_ 인 BFF 프로젝트 트리 (`svc-etprs-bff-fastapi`) 를 보여주며
"레이어드 구조를 이걸 참고 해서 변경" 요청. _이론적_ Layered (0.3.0) 는 자체 일관이지만
_현장 컨벤션_ 과 시각 차이가 큼. 템플릿이 _쓸 수 있는_ 시작점이 되려면 현장 트리와 _일치_ 해야.

**구조 변경 요약**:

| Before (0.3.0) | After (0.4.0) | 비고 |
|---|---|---|
| `api/v1.py` 단일 파일 | `api/v1/{users,auth,me,items,router}.py` 폴더 | feature 별 분리 + `router.py` 통합 |
| `main.py` 인라인 `/healthz`, `/readyz` | `api/health.py` | 라우터 분리 |
| `db/models.py` | `models/{users,items}.py` + `__init__.py` re-export | 도메인별 split |
| `db/repositories/{users,items}.py` (`UserRepo`/`ItemRepo`) | `repositories/{users,items}_repository.py` (`UserRepository`/`ItemRepository`) | flat layout + `_repository` suffix + 클래스명 |
| `db/repository_base.py` | `repositories/_base.py` | underscore prefix |
| `services/{users,items}.py` | `services/{users,items}_service.py` | `_service` suffix |
| `core/{correlation,handlers,security_headers,ratelimit}.py` | `middleware/{correlation,handlers,security_headers,throttling}.py` | 미들웨어성 코드 분리. `ratelimit` → `throttling` 모듈명 |
| `routers/` 폴더 | _삭제_ | `api/v1/` 가 대체 |

### Added
- **`__main__.py`** — `python -m app` 실행 엔트리 (BFF 컨벤션, IDE Run + 로컬 디버깅 + Docker CMD 통합)
- **`schemas/_base.py`** — `BaseSchema(BaseModel)` 공통 베이스 (`ConfigDict(from_attributes=True)`). `UserPublic`, `OwnerSummary`, `ItemPublic`, `ItemDetail` 가 상속
- **`clients/external/`, `clients/kafka/`, `ws/`** — 빈 placeholder 폴더 + docstring (성장 시 외부 통신 / WebSocket 자리)
- **`deploy/Dockerfile`, `deploy/run.sh`, `deploy/build-spec`** — 운영 배포 컨벤션 자리. 루트 Dockerfile 도 _유지_ (개발/CI 동일)
- `models/__init__.py` re-export — `from app.models import User, Item` 가능. alembic env.py 가 한 줄로 메타데이터 로드

### Migration guide (fork 한 사용자)
import 경로 변경 (sed 자동화 가능):
- `from app.db.models import` → `from app.models import`
- `from app.db.repositories.users import UserRepo` → `from app.repositories.users_repository import UserRepository`
- `from app.db.repositories.items import ItemRepo` → `from app.repositories.items_repository import ItemRepository`
- `from app.db.repository_base import` → `from app.repositories._base import`
- `from app.services import users as` → `from app.services import users_service as`
- `from app.services import items as` → `from app.services import items_service as`
- `from app.core.correlation import` → `from app.middleware.correlation import`
- `from app.core.handlers import` → `from app.middleware.handlers import`
- `from app.core.security_headers import` → `from app.middleware.security_headers import`
- `from app.core.ratelimit import` → `from app.middleware.throttling import`
- `from app.routers.{users,auth,me,items} import` → `from app.api.v1.{users,auth,me,items} import`
- `from app.api.v1 import router as v1_router` → `from app.api.v1.router import router as v1_router`

클래스명 (호출처):
- `UserRepo(...)` → `UserRepository(...)`
- `ItemRepo(...)` → `ItemRepository(...)`

alembic:
- `import app.db.models` → `import app.models`

## [0.3.0] - 2026-05-06

### Changed — Layered 구조 refactor (시니어 review 반영, breaking change)

사용자 우려: "repository 도 이게 하나의 서비스 라고 한다면 서로 조인 하거나 반복해서 쓸 수 있는데
폴더별로 나눠 쓰면 나중에 import 할 때 저 도메인에서 임포트해야 함."

본 템플릿은 _단일 서비스 (모놀리식)_ — 진짜 bounded context 가 _아님_. 도메인 폴더 분리는
_격리_ 보단 _import 부담_ 만 만듦. **Layered 구조** (Spring Boot 식) 로 전환:

**Before** (`domain/users/` + `domain/items/` 격리):
```
src/app/domain/{users,items}/{schemas,repository,service,router}.py
```

**After** (data layer 공유 + service/router 도메인별):
```
src/app/db/repositories/{users,items}.py    ← cross-join 자유
src/app/schemas/{users,items}.py            ← cross-import 자유 (한 방향: items → users)
src/app/services/{users,items}.py
src/app/routers/{users,auth,me,items}.py    ← auth 분리
```

### Added
- **Cross-domain 시연** — `GET /api/v1/items/{id}/detail` (owner 정보 포함) + `ItemRepo.get_with_owner` (selectinload eager) + `ItemDetail` 스키마 + `OwnerSummary` 가벼운 user 표현.
- README "새 도메인 추가" 섹션 — 5 곳 파일 추가 가이드 (db/models, db/repositories, schemas, services, routers).

### Removed
- `src/app/domain/` 폴더 _전체_ 삭제.

### Migration guide (fork 한 사용자)
import 경로 변경:
- `from app.domain.users.repository` → `from app.db.repositories.users`
- `from app.domain.items.repository` → `from app.db.repositories.items`
- `from app.domain.users.schemas` → `from app.schemas.users`
- `from app.domain.items.schemas` → `from app.schemas.items`
- `from app.domain.users import service` → `from app.services import users as service`
- `from app.domain.items import service` → `from app.services import items as service`
- `from app.domain.users.router import users_router, auth_router, me_router` → `from app.routers.{users,auth,me} import router`
- `from app.domain.items.router import router` → `from app.routers.items import router`

## [0.2.0] - 2026-05-06

### Added — 운영급 강화 (시니어 review 반영)
- **Refresh token (Redis 기반 + rotation)** — `/auth/refresh`, `/auth/logout`, `/auth/logout-all` 엔드포인트. access(15분) + refresh(7일) 페어. 사용된 refresh 즉시 revoke (token reuse 탐지).
- **Rate limit (login 보호)** — `core/ratelimit.py` Redis fixed-window. IP 당 분당 N회 (settings 조절). 429 + Retry-After + envelope.
- **Security 헤더 미들웨어** — `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `Content-Security-Policy`, `Permissions-Policy`. HSTS 는 prod 만.
- **CORS 미들웨어** — Settings 의 `cors_origins` 쉼표 구분 파싱, `allow_credentials` 옵션.
- **DB 풀 튜닝 노출** — Settings 에 `db_pool_size` / `max_overflow` / `recycle` / `timeout`.
- **`/readyz` readiness probe** — DB / Redis 응답 가능 검사. K8s readiness probe 용 분리.
- **PII redaction** — `core/logging.py` 에 `_redact_sensitive` structlog processor (`password` / `token` / `authorization` / `secret` / `api_key` 자동 마스킹).
- **Service unit tests** — `test_user_service.py` / `test_item_service.py` UoW + Cache mock. integration 보다 100x 빠름.
- **Repository BaseRepo[T] + Page/PageResponse** — PEP 695 generic 공통 CRUD. 새 도메인 = 5 줄.
- **Dockerfile 강화** — `--no-install-recommends`, `curl` 기반 HEALTHCHECK, `APP_ENV=prod` default.
- **README 운영 체크리스트 + Alembic Expand-Contract 패턴**.

### Changed
- `create_token` → `create_access_token` (별칭 유지). access token 에 `jti` 추가 (같은 초 발급도 매번 다른 토큰).
- `TokenResponse` — `refresh_token` 필드 추가.
- HTTPException 핸들러가 `headers` 보존 (Retry-After / WWW-Authenticate).

## [0.1.0] - 2026-04-30

### Added
- 초기 템플릿: FastAPI + Postgres + Redis + JWT 인증 + ApiEnvelope + correlation-id + 구조화 로그.
- 도메인: users (signup / login / me) + items (CRUD + owner 가드 + cache-aside).
- 인프라: Docker multi-stage, docker-compose (db + cache profile), GitHub Actions (lint+typecheck+unit+integration / GHCR push).
- 테스트: testcontainers Postgres + Redis 통합 테스트, asgi-lifespan, unit/integration 분리.
- 문서: README (한국어, Rename guide + Pitfalls), MIT LICENSE.
