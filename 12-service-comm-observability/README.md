# 12 — 서버간 통신 + 관측가능성

마이크로서비스 운영 수준의 _기반_. 03/11 의 라이브러리들이 _진짜 운영_ 패턴으로 결합.

## 학습 목표

- **`httpx.AsyncClient` 재사용** — 앱 lifespan 동안 _하나_, 의존성 주입
- **재시도** (`tenacity`) — 5xx/네트워크 오류만, 지수 백오프
- **회로 차단기** (`purgatory`) — 연속 실패 시 _빠른 실패_, upstream 보호
- **correlation-id 미들웨어** — `X-Request-ID` 인바운드/아웃바운드 전파
- **`structlog.contextvars`** — 요청별 로그 컨텍스트 자동 첨부
- **OpenTelemetry** 자동 계측 — FastAPI/httpx 코드 변경 _없이_
- **Prometheus 메트릭** — `/metrics` 자동 노출

## 디렉토리

```
12-service-comm-observability/
├── pyproject.toml          # tenacity, purgatory, opentelemetry-*, prometheus-fastapi-instrumentator
├── Makefile
├── README.md
├── src/obsapp/
│   ├── settings.py         # http timeout / retry / breaker 정책
│   ├── correlation.py      # X-Request-ID 미들웨어 + structlog contextvars
│   ├── http_client.py      # ResilientClient = AsyncClient + retry + breaker
│   ├── observability.py    # OTel + Prometheus 셋업
│   └── main.py             # 통합 (lifespan + 라우트 + 미들웨어)
└── tests/
    ├── conftest.py
    ├── test_correlation.py        # X-Request-ID 발급/전파
    ├── test_resilient_client.py   # MockTransport 로 재시도/breaker 검증
    └── test_metrics.py            # /metrics 형식 검증
```

## 실행

```bash
cd .. && uv sync && cd 12-service-comm-observability

make run                   # uvicorn dev
# 다른 터미널
curl -i http://localhost:8000/healthz
# → X-Request-ID 헤더 자동 포함
curl http://localhost:8000/metrics | head -20
# → Prometheus 형식

make all                   # ruff + mypy + pytest
```

## 다국 언어 비교

| 개념 | 가장 가까운 비교 |
|---|---|
| **httpx 재사용 + lifespan** | Spring `WebClient.Builder` 빈, NestJS `HttpService` |
| **tenacity 재시도** | Spring `RetryTemplate` / `@Retryable`, axios-retry, NestJS `RetryInterceptor` |
| **purgatory 회로 차단기** | **Resilience4j `CircuitBreaker`** (가장 가까움), opossum (Node), sony/gobreaker (Go) |
| **correlation-id** | Spring **Sleuth/Brave** (MDC traceId/spanId), NestJS `cls-rs` |
| **structlog.contextvars** | Spring SLF4J **MDC** |
| **OpenTelemetry** | _표준 자체_ — 모든 언어 동일 모델 |
| **Prometheus** | _표준 자체_ — Micrometer (Spring), prom-client (Node) |

## 핵심 개념

### 1) 재시도 정책 — _idempotent_ 만 + 5xx/네트워크만

```python
def _is_retryable(exc):
    if isinstance(exc, httpx.TimeoutException | httpx.NetworkError):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code >= 500   # 4xx 는 _영구_ 실패
    return False

AsyncRetrying(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=0.1, min=0.05, max=1.0),
    retry=retry_if_exception(_is_retryable),
)
```

**규칙**:
- _idempotent_ 호출 (GET/PUT/DELETE) 만 자동 재시도
- POST 는 _신중_ — 결제처럼 _중복_ 안 되는 것 retry 금지 또는 idempotency key
- 4xx (인증/검증) 는 _영구 실패_ — 재시도해도 같은 결과
- 지수 백오프 + jitter — thundering herd 방지

### 2) 회로 차단기 — 3가지 상태

```
        ┌─────────┐
        │ CLOSED  │ ←─────── 정상. 모든 요청 통과.
        └────┬────┘
             │ 임계치 N번 실패
             ▼
        ┌─────────┐
        │  OPEN   │ ←─────── _빠른 실패_. upstream 호출 X.
        └────┬────┘
             │ recovery_s 후
             ▼
        ┌──────────┐
        │HALF_OPEN │ ←────── 한 번 시도. 성공 → CLOSED, 실패 → OPEN
        └──────────┘
```

**효과**:
- upstream 죽었을 때 _내가도 같이_ 느려지는 cascading failure 방지
- 빠른 실패 → 클라가 _빠르게_ 다른 경로 / 폴백 시도

### 3) correlation-id — 분산 추적의 _최소 버전_

```python
# 인바운드 헤더 그대로 사용 (또는 발급)
rid = request.headers.get("X-Request-ID") or uuid.uuid4().hex
structlog.contextvars.bind_contextvars(request_id=rid)
# 이 요청 안의 _모든_ 로그에 자동 첨부

# 응답에도 포함
response.headers["X-Request-ID"] = rid
```

다음 단계 (운영 표준): **W3C `traceparent`** — OTel 가 자동 처리. correlation-id 는 사람이 읽기 좋은 _보조_.

### 4) OTel 자동 계측 — _마법_

```python
FastAPIInstrumentor.instrument_app(app)    # 모든 라우트 trace 자동
HTTPXClientInstrumentor().instrument()      # 모든 httpx 호출 trace 자동
```

**코드 한 줄도 안 바꾸고** 모든 진입/외부 호출이 trace span 으로 기록. `traceparent` 헤더 자동 전파 → 분산 시스템에서 _하나의 trace_ 로 보임.

비교: Spring **Sleuth/Brave** 가 같은 자리. Spring 은 옛날부터 자동, OTel 은 _벤더 중립_ 표준.

### 5) Prometheus 자동 메트릭

```python
Instrumentator().instrument(app).expose(app, endpoint="/metrics")
```

자동 메트릭 (RED 패턴):
- **Rate**: `http_requests_total{method, path, status}`
- **Errors**: 위에서 `status` 라벨로 분리
- **Duration**: `http_request_duration_seconds_bucket{...}` (히스토그램)

`/metrics` 엔드포인트가 _Prometheus exposition format_ 으로 노출 — Prometheus 서버가 scrape.

## 안티패턴

1. **요청마다 `httpx.AsyncClient()` 새로 만들기** — 커넥션 풀 못 씀. lifespan 동안 _하나_.
2. **POST 도 자동 재시도** — 중복 처리 위험. idempotency key (`Idempotency-Key` 헤더) 필요.
3. **4xx 도 재시도** — 영구 실패. 자원 낭비 + 클라이언트 오해.
4. **재시도 + 회로 차단기 둘 다 _넓게_** — 폭증 가능. 보통 _재시도는 짧게_, _breaker 는 host 단위_.
5. **`correlation-id` 누락** — 운영에서 _한 요청 추적_ 불가. 모든 외부 호출에 _전파_ 필수.
6. **OTel exporter 누락 → 메모리 폭증** — span 이 buffer 에 쌓임. 항상 exporter 또는 BatchSpanProcessor 명시.
7. **`/metrics` 인증 X 운영 노출** — 내부 정보 유출. 게이트웨이 / 사이드카로 보호.
8. **OTel 자동 계측 + 수동 span 중복** — 같은 span 두 번. _자동에 맡기고 비즈니스 로직만 수동_ 으로.
9. **structlog 와 표준 logging 혼용** — 출력 형식 깨짐. 한 가지로 통일.

## 직접 해보기 TODO

- [ ] `tenacity` 의 `before_sleep_log` 추가해서 재시도 로그 확인
- [ ] `purgatory` 의 `Hook` 으로 OPEN/CLOSED 전이 시 로그/알림
- [ ] OTLP endpoint 를 _진짜_ Tempo/Jaeger 에 연결 (도커 compose 추가)
- [ ] Prometheus 서버 (도커) 에서 `/metrics` scrape, Grafana 로 대시보드
- [ ] correlation-id 를 _httpx 호출_ 에 자동 전파하는 미들웨어 / 인터셉터
- [ ] `OAuth2 token` 을 외부 호출에 자동 첨부하는 `httpx.Auth` 클래스
- [ ] `httpx.Limits(max_connections=100, max_keepalive_connections=20)` 튜닝

## 다음 단계

**13 — Kafka + 큐**. aiokafka 프로듀서/컨슈머, transactional outbox, arq 백그라운드 큐.
