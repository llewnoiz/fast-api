# A5 — 보안 심화

09 의 JWT/OAuth password flow + RBAC 위에 _운영급 보안_.

## 학습 목표

- **2FA / TOTP** (RFC 6238) — Google Authenticator 호환
- **API key 인증** — 서버↔서버 (Stripe/GitHub 패턴)
- **OAuth 2.0 3rd party** — Google/GitHub 로그인 (authlib + PKCE)
- **OWASP Top 10** 점검 + 방어 코드 (IDOR / Injection / SSRF / 보안 헤더)
- **시크릿 관리** — Vault / AWS Secrets Manager / sops / External Secrets Operator

## 디렉토리

```
A5-security/
├── pyproject.toml          # pyotp, authlib, cryptography
├── Makefile
├── README.md
├── src/secapp/
│   ├── totp.py             # 2FA TOTP 발급 + 검증
│   ├── api_key.py          # API key 발급/해시/검증 의존성
│   ├── oauth_external.py   # Google/GitHub OAuth (authlib)
│   ├── owasp_examples.py   # IDOR/SSRF/보안 헤더 방어 코드
│   └── main.py             # 통합 라우트 + 보안 헤더 미들웨어
└── tests/
    └── test_security.py    # TOTP + API key + SSRF + 헤더 검증
```

## 다국 언어 비교

| 개념 | 가장 가까운 비교 |
|---|---|
| **TOTP (pyotp)** | Spring `GoogleAuthenticator`, NestJS `speakeasy` |
| **API Key** | Spring `@PreAuthorize("hasAuthority('SCOPE_api')")`, Stripe Bearer key |
| **OAuth2 3rd party (authlib)** | Spring Security `oauth2 client`, NestJS `passport-google` |
| **PKCE** | RFC 7636 — 모든 언어 표준 |
| **mTLS** | Spring `client-auth=NEED`, nginx ssl_verify_client |
| **시크릿 관리** | Vault (모든 언어), AWS Secrets Manager + IRSA |

## 핵심 개념

### 1) TOTP (Time-based One-Time Password)

```python
# 발급 — 한 번만
secret = totp.generate_secret()             # base32
uri = totp.provisioning_uri(secret=secret, account="alice@x.com", issuer="tender")
# uri 를 QR 코드로 → Google Authenticator 등록

# 검증 — 매 로그인
totp.verify(secret, "123456", valid_window=1)
```

**핵심**:
- 시크릿 발급은 _한 번_, DB 에 _암호화_ 저장
- `valid_window=1` — 시계 차이 30초 정도 허용
- **재사용 방지**: 한 번 통과한 윈도 _카운터_ 를 DB 에 기록 → 같은 코드 재요청 거부 (replay 공격)
- Backup codes — 1회용 8자리 8개 같이 발급 (단방향 해시 저장)

### 2) API Key — 서버↔서버

```python
raw, h = ak.generate_api_key()         # ("ak_abc...", "sha256_hash")
# raw 는 _한 번만_ 사용자에게 노출 (다시는 못 봄)
# h 는 DB 에 저장

# 검증 시점
if hash_key(received_key) != stored_hash:
    raise 401
```

**규칙**:
- prefix (`pk_live_`, `sk_test_`, `ak_`) — UI 에서 _마지막 4자리_ 만 보여줌
- scope/permission 분리 — 키마다 _허용 범위_
- 회전 — 90일 정도 정기 갱신, 두 키 _공존 기간_ 두고 마이그레이션
- 평문 저장 _절대 X_ — sha256 (또는 bcrypt) 단방향 해시

### 3) OAuth 2.0 3rd party — Authorization Code Flow + PKCE

```
사용자 → /auth/google
       → Google 동의 화면
       → /auth/google/callback?code=xxx
서버 → Google 토큰 엔드포인트에 code + secret 교환
     → access_token + id_token 받음
     → 사용자 정보 조회 → DB upsert + 우리 JWT 발급
```

**PKCE (RFC 7636)** — code_verifier + code_challenge:
- 발급 단계에서 _랜덤 verifier_ 생성, 그 sha256 을 challenge 로 보냄
- 토큰 교환 시 _원본 verifier_ 함께 → 중간자가 code 만 탈취해도 토큰 X
- authlib 가 _자동_ 처리

### 4) mTLS (Mutual TLS) — 서버↔서버 _최강_ 인증

본 코드엔 미포함 (FastAPI 자체 X, 보통 nginx/Envoy 앞단). 개념:

```
클라이언트 ↔ 서버 _둘 다_ 인증서 제시 — _둘 다_ 검증
```

- _내부_ 서비스 메시 (Istio mTLS 자동) 또는 _파트너 API_
- API key 보다 강함 (탈취 불가능 — 인증서 기반)
- 단점: 인증서 발급/회전 운영 부담 → cert-manager / SPIFFE

### 5) OWASP Top 10 — 5가지 핵심

| # | 위협 | 방어 |
|---|---|---|
| **A01** Broken Access Control (IDOR) | `/orders/{id}` _누구나_ 접근 | 본인 또는 admin 만 — `authorize_order_access()` |
| **A03** Injection (SQL/SSRF) | raw query, 사용자 입력 URL 직접 호출 | SQLAlchemy 파라미터 바인딩 / `safe_external_url()` |
| **A05** Security Misconfiguration | CORS *, debug=True, default secret | 환경별 분리 + 보안 헤더 미들웨어 |
| **A07** Auth Failures | 약한 비번, brute force 방치 | 09 + 11 rate limit + 2FA |
| **A10** SSRF | AWS 메타데이터 (169.254.169.254) | private host 차단 + allowlist |

### 6) 보안 헤더 (필수)

```python
{
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
}
```

미들웨어로 _모든 응답_ 에 자동 추가. mozilla.org/observatory 로 점수 측정 가능.

## 시크릿 관리 — 환경별

| 환경 | 도구 | 비고 |
|---|---|---|
| 로컬 개발 | `.env` (gitignore) + `secrets.token_urlsafe(32)` | git 절대 커밋 X |
| CI | GitHub Actions secrets / OIDC | A3 참고 |
| 운영 (간단) | AWS Secrets Manager / GCP Secret Manager | IAM 으로 권한 |
| 운영 (K8s) | **External Secrets Operator** + Vault/AWS SM | A4 의 K8s Secret 보강 |
| GitOps | **sealed-secrets** | git 에 _암호화_ 형태 저장 |
| 다중 클라우드 | HashiCorp Vault | dynamic secrets, leasing |

권장 패턴:
1. 로컬: `.env` (개발 전용 값)
2. 운영: External Secrets Operator → AWS Secrets Manager (또는 Vault) → K8s Secret 자동 생성
3. **장기 access key 절대 X** — IRSA (AWS) / Workload Identity (GCP) / OIDC 로 단명 토큰

## 안티패턴

1. **TOTP 시크릿 _평문 DB 저장_** — 유출 시 모든 사용자 2FA 무력. 마스터 키로 암호화 후.
2. **API key 평문 저장** — 유출 시 영구. 단방향 해시.
3. **API key 만료 X** — 회전 정책 필수.
4. **OAuth state 검증 누락** — CSRF 공격. authlib 가 자동 처리하니 _안 끄는_ 게 중요.
5. **PKCE 없는 모바일/SPA** — code 탈취 위험. 항상 PKCE.
6. **CORS `allow_origins=["*"]` + `allow_credentials=True`** — 브라우저가 거부함. 둘 중 하나.
7. **error 응답에 stack trace** — 보안 정보 노출. 07 단계 envelope 핸들러로 통일.
8. **사용자 입력 URL 그대로 호출** — SSRF. private host 차단 + redirect 따라가기 X.
9. **시크릿 _git 커밋_** — git history 영구. 발견 즉시 회전.
10. **로그에 비밀번호/JWT 평문** — log aggregator 유출. structlog processor 로 마스킹.

## 직접 해보기 TODO

- [ ] 09 의 `/auth/token` 에 TOTP 단계 추가 — 비번 OK 이후 TOTP 코드까지
- [ ] backup codes 8개 발급 + 단방향 해시 + 1회 사용 마킹
- [ ] OAuth 3rd party 실제 연동 — Google Console 에서 Client ID 발급 + 콜백 등록
- [ ] **`mozilla observatory`** 로 운영 도메인 보안 헤더 점수 측정
- [ ] **`pip-audit`** / **`safety`** — 의존성 취약점 스캔
- [ ] **`bandit`** — Python 코드 정적 보안 분석
- [ ] **`trivy`** — 도커 이미지 취약점 스캔 (A4 의 image 에 적용)
- [ ] mTLS 시뮬레이션 — nginx 프록시 + 자체 서명 CA + client cert
- [ ] sealed-secrets 설치 후 A4 의 secret.yaml 을 _암호화 형태_ 로 git 커밋
- [ ] 12 의 structlog processor 에 _민감 키 마스킹_ (`password`, `token`, `secret`) 추가

## 다음 단계

**A6 — DB 심화**. 인덱스 전략, EXPLAIN ANALYZE, N+1 디버깅, zero-downtime 마이그레이션 (Expand-Contract), Postgres jsonb / full-text / LISTEN/NOTIFY.
