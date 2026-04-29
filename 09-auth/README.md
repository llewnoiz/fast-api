# 09 — 인증·인가

JWT 발급/검증 + OAuth2 password flow + RBAC + 보안 기본. 08 의 `dependency_overrides` 패턴이 _인증된 사용자_ 를 mock 으로 갈아끼우는 데 그대로 쓰임.

## 학습 목표

- **비밀번호 해싱** (bcrypt) — 단방향, salt 자동
- **JWT** (HS256) — `sub` / `exp` / `iat` / `roles` 클레임
- **OAuth2 password flow** — `/auth/token` 으로 토큰 발급
- **`Depends(get_current_user)`** — 라우트 한 줄 보호
- **RBAC** — `Depends(require_role("admin"))` / `("admin", "auditor")` (OR)
- **CORS 미들웨어**, 시크릿 관리 가이드

## 디렉토리

```
09-auth/
├── pyproject.toml          # passlib[bcrypt], pyjwt, python-multipart
├── Makefile                # make run / curl-demo / test / lint
├── README.md
├── src/authapp/
│   ├── settings.py         # JWT_SECRET, expire, CORS origins
│   ├── users.py            # 인메모리 user 저장 + 시드 (alice/bob/carol)
│   ├── security.py         # 해싱(bcrypt) + JWT 발급/검증
│   ├── deps.py             # OAuth2PasswordBearer + get_current_user + require_role
│   ├── routers/
│   │   ├── auth.py         # POST /auth/token (form-data)
│   │   ├── me.py           # GET /me
│   │   └── admin.py        # GET /admin/secret + /audit/log
│   └── main.py             # CORS + 라우터 등록
└── tests/
    ├── conftest.py         # client + alice_token / bob_token / carol_token fixture
    └── test_auth.py        # 14 tests (해싱·JWT·로그인·me·RBAC)
```

## 실행

```bash
cd .. && uv sync && cd 09-auth

make run                              # uvicorn dev
# → http://localhost:8000/docs   ← Swagger UI 의 "Authorize" 버튼 사용 가능

# 다른 터미널 — 5가지 시나리오 한 번에
make curl-demo

make all                              # ruff + mypy + pytest
```

## 시드 사용자

| username | password | roles |
|---|---|---|
| `alice` | `alice123` | admin, user |
| `bob` | `bob123` | user |
| `carol` | `carol123` | user, auditor |

## 다국 언어 비교 — _개념은 거의 동일_

| 개념 | 가장 가까운 비교 |
|---|---|
| **JWT 발급/검증** | Spring Security `JwtEncoder/JwtDecoder`, NestJS `@nestjs/jwt JwtService`, Auth0 |
| **OAuth2PasswordBearer** | Spring `OAuth2ResourceServerConfigurer`, NestJS `Passport` JwtStrategy |
| **`Depends(get_current_user)`** | Spring `Authentication` 매개변수, NestJS `@CurrentUser()` |
| **`require_role("admin")`** | Spring `@PreAuthorize("hasRole('ADMIN')")`, NestJS `@Roles('admin')` |
| **bcrypt** | Spring `BCryptPasswordEncoder`, Node `bcrypt` |
| **CORSMiddleware** | Spring `CorsConfigurationSource`, NestJS `app.enableCors()` |

## 핵심 흐름 — 한 화면

```
[ 클라이언트 ]                      [ FastAPI ]
   │                                    │
   │  POST /auth/token                  │
   │  username + password (form-data)   │
   │ ──────────────────────────────►    │
   │                              ┌─ verify_password (bcrypt) ─┐
   │                              │  hash_password 와 일치?     │
   │                              └────────────────────────────┘
   │                                    │
   │                              ┌─ create_access_token ─┐
   │                              │  HS256 + claims        │
   │                              │  (sub, roles, exp)     │
   │                              └────────────────────────┘
   │  ◄────  { "access_token": "eyJ...", "token_type": "bearer" }
   │                                    │
   │  GET /me                           │
   │  Authorization: Bearer eyJ...      │
   │ ──────────────────────────────►    │
   │                              ┌─ get_current_user ─────────┐
   │                              │  decode_access_token        │
   │                              │  get_user(sub) → User       │
   │                              │  user.disabled? 401         │
   │                              └────────────────────────────┘
   │  ◄────  { "username": "alice", "roles": [...], ... }
   │                                    │
   │  GET /admin/secret                 │
   │  Authorization: Bearer eyJ...      │
   │ ──────────────────────────────►    │
   │                              ┌─ require_role("admin") ─┐
   │                              │  set(required) ∩ roles ?│
   │                              │  비어있으면 403          │
   │                              └────────────────────────┘
   │  ◄────  { "secret": "..." }   또는   403 Forbidden
```

## OAuth2 Password Flow — _form-data_ 가 핵심

```bash
# ❌ JSON 으로 보내면 422 — 표준 OAuth2 가 아님
curl -X POST /auth/token -H 'Content-Type: application/json' \
     -d '{"username":"alice","password":"alice123"}'

# ✅ application/x-www-form-urlencoded
curl -X POST /auth/token \
     -H 'Content-Type: application/x-www-form-urlencoded' \
     -d 'username=alice&password=alice123'
```

`OAuth2PasswordRequestForm` 의존성이 표준 OAuth2 스펙을 따름. Swagger UI 의 "Authorize" 버튼도 같은 형식으로 호출.

## 401 vs 403 — 명확히 구분

| 상태 | 의미 | 예 |
|---|---|---|
| **401** Unauthorized | _인증 자체 실패_ — 토큰 없음/만료/위조 | `/me` 토큰 없이 |
| **403** Forbidden | _인증은 됐지만 권한 부족_ | `bob` 이 `/admin/secret` |

라우트는 _순서대로_ 검사: 토큰 없으면 401, 토큰 OK 인데 역할 부족이면 403.

## 보안 안티패턴

1. **JWT_SECRET 을 코드에 박기** — 환경변수 / Secret Manager 로만. 노출 시 _누구나 토큰 위조_.
2. **만료(exp) 없는 토큰** — 분실 시 영원히 유효. 짧게 (15~30분) + refresh token.
3. **민감 데이터를 JWT payload 에** — payload 는 _서명만_ 되고 _암호화 X_, base64 디코드로 누구나 봄. PII 넣지 말 것.
4. **로그인 실패 시 사용자 존재 여부 노출** — `"user not found"` vs `"wrong password"` 분리하면 _계정 열거_ 공격. 우리 코드는 같은 메시지.
5. **HTTPS 없이 비밀번호 전송** — 도청 위험. 운영 무조건 TLS.
6. **CORS `allow_origins=["*"]` + `allow_credentials=True`** — 브라우저가 거부함. 둘 중 하나 선택.
7. **bcrypt 72바이트 초과 패스워드** — 잘림. 긴 패스프레이즈 허용하려면 `argon2-cffi` 또는 사전 SHA-256.
8. **로그인 rate limit 없음** — 무차별 대입 공격. 11 단계 (Redis Rate Limit) 에서.
9. **stateful 세션 + JWT 혼용** — 모델 일관성 깨짐. 하나만 선택.
10. **`/admin/*` 만 보호하고 `/api/*` 평문** — 정책을 _라우터 dependencies_ 또는 _전역 미들웨어_ 로 일관되게.

## 시크릿 관리 — 환경별

| 환경 | 어디 두나 |
|---|---|
| **로컬 개발** | `.env` (gitignore), `secrets.token_urlsafe(32)` |
| **CI** | Repository secrets / OIDC |
| **운영** | AWS Secrets Manager, HashiCorp Vault, GCP Secret Manager, K8s Secret + IRSA/Workload Identity |

**절대** `.env` 를 _커밋_ 하지 말 것 — 우리 `.gitignore` 가 막고 있음.

## scope vs role — 두 가지 다른 인가 모델

본 단계는 _RBAC_ (Role-Based) 만 다룸. **OAuth2 scope** (예: `read:items`, `write:items`) 는 _권한 단위가 더 잘게_ 쪼개진 모델 — 외부 클라이언트가 _필요한 만큼만_ 권한 위임받을 때.

```python
# scope 패턴 (참고만, 본 코드엔 없음)
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/auth/token",
    scopes={"read:items": "Read items", "write:items": "Write items"},
)

@router.get(...)
async def f(token: str = Security(oauth2_scheme, scopes=["read:items"])): ...
```

GitHub OAuth, Google OAuth 같은 _3rd party 위임_ 환경에서 쓰임. 사내 RBAC 면 본 단계 패턴이 더 단순.

## 직접 해보기 TODO

- [ ] 만료된 토큰 시뮬레이션: `jwt_expire_minutes=0` 으로 Settings 오버라이드, 1초 후 호출 → 401 확인
- [ ] **refresh token** 추가 — 짧은 access (15분) + 긴 refresh (14일), `/auth/refresh` 라우트
- [ ] `/auth/logout` 추가 (JWT 는 stateless 라 _서버 상태_ 없음 — Redis blocklist 패턴, 11 단계 떡밥)
- [ ] `users.disabled = True` 인 사용자 시드 추가 + 401 확인
- [ ] `/admin/users` 라우트로 사용자 목록 조회 (admin 만)
- [ ] OAuth2 scope 모델로 변환 — `OAuth2PasswordBearer(scopes=...)` + `Security(...)` 사용
- [ ] HTTPS 강제 미들웨어 (운영 전용) — `from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware`

## 다음 단계

**10 — DB + 트랜잭션**. SQLAlchemy 2.0 async, Alembic 마이그레이션, Unit of Work, 트랜잭션 / nested savepoint, N+1 안티패턴. 09 의 인메모리 `_USERS` 가 _진짜 Postgres_ 로 옮겨갑니다.
