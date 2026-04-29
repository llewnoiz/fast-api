# 07 — 요청·응답 모델 + 공통 에러 + API 버전 관리

04 의 미니 라우트들이 _실무 구조_ 로 발전. 응답 envelope, 전역 예외 핸들러, 도메인 에러 코드, /v1·/v2 라우터 분리.

## 학습 목표

- **공통 응답 envelope** `{code, message, data}` — 성공·실패 같은 모양
- **전역 exception handler** — `@ControllerAdvice` 자리, 라우트는 `raise DomainError` 만
- **에러 코드 표준화** — `ErrorCode` Enum + 도메인별 예외 클래스
- **HTTP status vs 도메인 코드 분리** — 같은 404 도 `ORDER_NOT_FOUND` / `USER_NOT_FOUND` 분기 가능
- **/v1, /v2 라우터 분리** + `Deprecation` / `Sunset` / `Link` 헤더 (IETF draft + RFC 8594)
- **OpenAPI examples / responses** 풍부화 — `Field(examples=[...])`, `responses={409: {...}}`

## 실행

```bash
cd .. && uv sync && cd 07-request-error-version

make run                           # uvicorn dev
# → http://localhost:8000/docs

# 다른 터미널
make curl-demo                     # envelope / 에러 / Deprecation 헤더 한 번에 확인

make all                           # ruff + mypy + pytest
```

## 디렉토리

```
07-request-error-version/
├── pyproject.toml
├── Makefile
├── README.md
├── src/errver/                    # 패키지 이름이 `errver` (04 의 `app` 과 충돌 회피)
│   ├── main.py                    # 04 와 비슷, install_exception_handlers 추가
│   ├── envelope.py                # ApiEnvelope[T] (제네릭)
│   ├── errors.py                  # ErrorCode Enum + DomainError + 구체 예외
│   ├── handlers.py                # 전역 예외 핸들러 4개 (도메인/검증/HTTP/미처리)
│   └── api/
│       ├── deprecation.py         # Deprecation/Sunset/Link 헤더 의존성
│       ├── v1/orders.py           # 구식 — item, deprecated 헤더 자동
│       └── v2/orders.py           # 현재 — sku + created_at
└── tests/test_app.py              # 13 케이스 (envelope, 에러, 버전, OpenAPI)
```

## 다국 언어 비교 — 가장 가까운 자리

| 개념 | 가장 가까운 비교 |
|---|---|
| 공통 envelope | **NestJS** ResponseInterceptor + ExceptionFilter, **Spring** `ResponseEntity<ApiResponse<T>>` |
| 전역 예외 핸들러 | **Spring** `@RestControllerAdvice` + `@ExceptionHandler`, **NestJS** `@Catch() ExceptionFilter` |
| 도메인 예외 트리 | **Java** 체크드 예외 계층, **Kotlin** `sealed class Result.Error` |
| ErrorCode Enum | **Stripe** `error.type` 필드, **GitHub** API `documentation_url` |
| `/v1`, `/v2` 경로 | **Stripe** `Stripe-Version` 헤더, **GitHub** Accept 미디어타입 — _다양한 전략 중 하나_ |
| Deprecation 헤더 | IETF draft (모든 언어 공통 표준) |
| Sunset 헤더 | RFC 8594 |
| RFC 7807 Problem Details | 에러 응답의 _공식_ 표준 (`application/problem+json`) — 우리 envelope 대안 |

## 핵심 패턴 — 라우트는 깨끗하다

```python
@router.get("/{order_id}", response_model=ApiEnvelope[OrderOutV2])
async def get_order(order_id: int) -> ApiEnvelope[OrderOutV2]:
    order = _DB.get(order_id)
    if order is None:
        raise OrderNotFoundError(order_id)        # 핸들러가 envelope 변환
    return success(order)                          # 성공 envelope 헬퍼
```

라우트 함수는 **`raise DomainError` 와 `success(...)`** 두 가지만. HTTP 상세는 _전부 핸들러_ 가 담당. 각자 자기 일에 집중.

## 응답 형태 — 4가지 케이스 한눈에

### 1) 성공 200/201

```json
{
  "code": "OK",
  "message": "ok",
  "data": { "id": 1, "sku": "PEN-001", "quantity": 2, "created_at": "2026-..." }
}
```

### 2) 도메인 예외 — 404

```json
{
  "code": "ORDER_NOT_FOUND",
  "message": "order 999 not found",
  "data": null
}
```

### 3) 검증 실패 — 422

```json
{
  "code": "VALIDATION_ERROR",
  "message": "request validation failed",
  "data": {
    "errors": [
      {"loc": ["body", "sku"], "msg": "String should match pattern '^[A-Z0-9-]+$'", ...}
    ]
  }
}
```

### 4) 미처리 예외 — 500

```json
{
  "code": "INTERNAL_ERROR",
  "message": "internal server error",
  "data": null
}
```

운영에선 _내부 메시지 노출 X_ (보안). 자세한 건 _서버 로그_ 에만.

## 도메인 에러 추가하는 법

```python
# errors.py
class ErrorCode(str, Enum):
    USER_NOT_FOUND = "USER_NOT_FOUND"   # ← 추가

class UserNotFoundError(DomainError):
    def __init__(self, user_id: int) -> None:
        super().__init__(
            code=ErrorCode.USER_NOT_FOUND,
            message=f"user {user_id} not found",
            status=404,
        )

# 라우트 어디서든
raise UserNotFoundError(123)
```

핸들러는 _아무 변경 없이_ 동작. `DomainError` 베이스만 잡으면 끝.

## API 버전 관리 — 4가지 전략과 우리 선택

| 전략 | 예 | 장단점 |
|---|---|---|
| **경로 기반** ⭐ (이 단계) | `/v1/orders` | 가장 명시적, OpenAPI 분리 깔끔 |
| 헤더 기반 | `Stripe-Version: 2024-01-01` | URL 깨끗, 클라가 헤더 관리 |
| Accept 미디어타입 | `Accept: application/vnd.api.v2+json` | RESTful 순수주의 |
| 쿼리 파라미터 | `?version=2` | 가장 단순, 캐시 분리 어려움 |

**경로 기반** 이 학습/소규모에 가장 직관적. 본격적으로 _세분화_ 가 필요하면 Stripe 처럼 헤더로 갈 수 있음.

### Deprecation 헤더 패턴

```
HTTP/1.1 200 OK
Deprecation: true
Sunset: Sat, 31 Dec 2026 23:59:59 GMT
Link: </v2/orders>; rel="successor-version"
```

- `Deprecation: true` — 이 엔드포인트는 _deprecated_ 됨 (IETF draft)
- `Sunset` — _이 날짜_ 에 제거됨 (RFC 8594)
- `Link rel="successor-version"` — 후속 버전 위치 안내

클라이언트의 _자동 모니터링_ 도구가 이 헤더들을 보고 _업그레이드 알림_ 을 띄움.

## 안티패턴

1. **라우트 안에서 `HTTPException` 직접 만들기** — envelope 깨지고 핸들러 우회. 도메인 예외 → 핸들러로.
2. **모든 에러를 같은 `code` 로** — 클라가 분기 못 함. 도메인별 코드 분리.
3. **ErrorCode 이름을 _바꾸는_ 변경** — 기존 클라이언트 코드와 _계약 위반_. 추가만 OK, 변경/삭제는 _버전 변경_ 동반.
4. **운영에서 unhandled exception 메시지를 응답에 노출** — 스택트레이스 / SQL / 경로 등 보안 정보 새어나감.
5. **`/v1`·`/v2` 를 _복붙_** — 공통 로직은 도메인 서비스로 빼고 라우터만 분리. 우리 코드의 `_DB`/`_OUT_OF_STOCK` 도 사실 도메인 서비스로 빼는 게 정석.
6. **`Deprecation` 헤더 없이 _조용히_ 제거** — 서비스 장애. 항상 _Sunset 충분히 미래로_.
7. **검증 에러 응답에 `errors` _전체 노출_** — 보통은 OK 지만, 민감한 페이로드 (예: 비밀번호 정책 상세) 는 _가공_ 해서 노출.

## 직접 해보기 TODO

- [ ] `errors.py` 에 `UserNotFoundError` 추가, v2 에 `/v2/users/{id}` 라우트 만들기
- [ ] v2 의 `OrderCreateV2` 에 `customer_id: int` 필드 추가하고, 존재하지 않으면 `UserNotFoundError`
- [ ] `handlers.py` 에 `correlation_id` 를 응답 envelope 에 포함시키기 (다음 단계 12 떡밥)
- [ ] RFC 7807 Problem Details 형태 (`application/problem+json`) 로 _대체_ 응답 핸들러 만들어 보기
- [ ] `/v3/orders` 추가 — `quantity` 를 `Decimal` 로 바꿔서 `0.5kg` 같은 실수 수량 허용
- [ ] OpenAPI `/docs` 에서 v1/v2 가 _태그로 분리_ 되어 보이는지 확인

## 다음 단계

**08 — 테스팅**. pytest 심화, fixture, parametrize, **testcontainers** 로 진짜 Postgres/Redis 띄워 통합 테스트, 커버리지. 지금까지 우리는 _라우트 단위 테스트_ 만 했지만 08 부터 _DB 트랜잭션·Redis 캐시_ 등이 들어가는 통합 테스트가 본격화.
