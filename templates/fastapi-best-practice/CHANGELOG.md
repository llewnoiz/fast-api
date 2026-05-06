# Changelog

본 문서는 [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) 형식을 따른다.
버전은 [Semantic Versioning](https://semver.org/spec/v2.0.0.html) 준수.

## [Unreleased]

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
