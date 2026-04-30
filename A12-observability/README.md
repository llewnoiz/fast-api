# A12 — 관측가능성 운영급

12 단계 (OTel + Prometheus 자동 계측) 의 _운영_ 확장. SRE 가 _실제로_ 쓰는 도구 / 패턴.

## 학습 목표

- **Sentry** 에러 추적 — stacktrace + breadcrumbs + release tracking
- **구조화 로그** (JSON) — Loki / ELK / CloudWatch 친화 + 민감정보 redact
- **OTel 분산 trace** — 운영 backend (Jaeger / Tempo / Datadog) 통합 패턴
- **SLO / SLI / Error Budget** — _운영의 신뢰성 계약_, burn rate 알람
- **Grafana Dashboard JSON** — 코드로 정의 (RED / SLO 대시보드)
- **Prometheus Alert Rules** — Multi-window multi-burn-rate (Google SRE 표준)

## 디렉토리

```
A12-observability/
├── pyproject.toml
├── Makefile
├── README.md
├── src/obsdeep/
│   ├── __init__.py
│   ├── settings.py
│   ├── structured_logging.py    # structlog + Loki/ELK 친화 JSON + redact
│   ├── sentry_setup.py          # Sentry SDK + before_send scrubber
│   ├── slo.py                   # Slo / burn rate / error budget
│   ├── tracing.py               # OTel TracerProvider + FastAPI 자동 계측
│   ├── dashboards.py            # Grafana Dashboard JSON 빌더 (RED / SLO)
│   ├── alerting.py              # Prometheus alert rules (multi-window)
│   └── main.py                  # FastAPI 앱 + 모든 통합
└── tests/
    ├── test_slo.py              # burn rate / error budget 산수 검증
    ├── test_logging_redaction.py
    ├── test_dashboards.py       # Grafana JSON 구조 검증
    ├── test_alerting.py         # PromQL 문자열 + multi-window 검증
    └── test_app.py              # FastAPI e2e
```

## SLO / SLI / Error Budget

```
SLI (측정값) → 성공률 / p95 latency
SLO (목표) → 99.9% / 30일 윈도우
Error Budget → 30일 × 0.1% = 43.2분 다운 허용
```

**Burn rate** = 현재 _예산 소비 속도_:
```
burn_rate = (현재 에러율) / (1 - SLO target)
```

**Google SRE Workbook 표준 4종 알람** (multi-window multi-burn-rate):

| 알람 | 빠른 윈도우 | 느린 윈도우 | burn rate | 의미 |
|---|---|---|---|---|
| critical | 5m | 1h | 14.4 | 1시간에 _2%_ 예산 소진 |
| critical | 30m | 6h | 6 | 6시간에 _5%_ 예산 소진 |
| warning | 2h | 1d | 3 | 1일에 _10%_ 예산 소진 |
| warning | 6h | 3d | 1 | 3일에 _10%_ 예산 소진 |

빠른 + 느린 _둘 다_ true 일 때만 fire → false positive 줄임.

```python
from obsdeep.alerting import slo_burn_rate_alerts, to_rules_yaml
rules = slo_burn_rate_alerts(service="tender", slo_target=0.999)
# rules 를 prometheus_rules.yaml 에 dump
```

## Sentry vs OpenTelemetry

| 도구 | 강점 | 약점 |
|---|---|---|
| **Sentry** | 에러 _stacktrace + 변수값_, breadcrumbs, release tracking, user context | trace 부족 |
| **OTel + Tempo/Jaeger** | _분산 trace_ 표준, vendor-neutral, 메트릭/로그 통합 | 에러 알람 약함 |
| **Datadog APM** | 매니지드 통합 (에러+APM+로그) | 비쌈, vendor lock |

→ **둘 다 쓰는 게 정석** — Sentry 로 에러, OTel 로 trace.

본 모듈은 _학습_ 모드: DSN 비어있으면 Sentry _no-op_ + ConsoleSpanExporter.

## 구조화 로그 — Loki / ELK 친화

```python
import structlog
log = structlog.get_logger()

log.info("order_placed", order_id=42, user_id=7, total=15000)
# 출력 (prod 모드, JSON):
# {"timestamp":"2026-04-30T01:23:45Z","level":"info","event":"order_placed",
#  "request_id":"abc-123","order_id":42,"user_id":7,"total":15000}
```

**민감정보 redact**: `password` / `token` / `authorization` / `cookie` / `api_key` / `secret` 자동 `***REDACTED***`.

**Loki vs ELK**:
- **Loki** ─ 라벨 인덱싱, 가벼움, 비용 ↓. _라벨로 grep_.
- **ELK** ─ 전문 인덱싱, 모든 필드 검색 가능, 비쌈.

수집:
- `Promtail` (Loki) — stdout 의 JSON 한 줄 자동 파싱
- `Filebeat` / `Fluent Bit` (ELK) — 같은 패턴
- AWS / GCP / Azure — 자체 에이전트

## OTel + 운영 backend

```python
# 학습용
from obsdeep.tracing import setup_tracing, instrument_fastapi
provider = setup_tracing(service_name="tender", environment="prod")
instrument_fastapi(app)

# 운영 — OTLP exporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
exporter = OTLPSpanExporter(endpoint="http://otel-collector:4317", insecure=True)
provider = setup_tracing(service_name="tender", exporter=exporter)
```

**OTel Collector** 가 _벤더 무관_ ── Jaeger / Tempo / Datadog / Honeycomb 모두 같은 OTLP 받음.

| Backend | 특징 |
|---|---|
| Jaeger | 오픈소스, 단순 |
| **Tempo** | Grafana 패밀리, 저비용 (S3 만 사용) |
| Honeycomb | 매니지드, 고차원 분석 |
| Datadog APM | 통합 (에러 + APM + 로그), 비쌈 |

## Grafana Dashboard 코드 정의

```python
from obsdeep.dashboards import red_dashboard
import json

dash = red_dashboard(service="tender")
print(json.dumps(dash.to_json()))   # Grafana import 가능 JSON
```

**RED 메서드** (Tom Wilkie, Weaveworks):
- **R**ate: `sum(rate(http_requests_total{service="X"}[5m]))`
- **E**rrors: `100 * sum(rate(http_requests_total{status=~"5..",service="X"}[5m])) / sum(rate(http_requests_total{service="X"}[5m]))`
- **D**uration: `histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[5m])) by (le))`

**왜 코드로?**
- git 버전 관리 / PR 리뷰
- 환경별 변형 (dev / staging / prod)
- 자동 배포 (Terraform `grafana` provider, `grafana-provisioning`)

운영 도구: `grafonnet` (Jsonnet), `grafanalib` (Python).

## 안티패턴

1. **알람이 _리소스 메트릭_ (CPU / 메모리)** — 사용자에게 영향 없는 값. _증상_ 알람으로.
2. **알람이 _actionable 하지 않음_** — runbook URL 없거나, 잠시 대기 외 행동 X.
3. **Burn rate 단일 윈도우** — false positive 폭발. _multi-window_ AND 조건.
4. **Sentry 모든 환경에서 활성** — dev / test 의 _노이즈_ 가 prod 알람 묻음. 환경 분리.
5. **`traces_sample_rate=1.0`** — 운영 비용 폭발. 0.01~0.1 권장.
6. **민감정보 평문 로그** — `password` / 토큰 / PII (개인정보 보호법 위반 위험).
7. **로그 레벨 무차별 INFO** — 운영 비용 + grep 어려움. DEBUG 는 _상세_, INFO 는 _이벤트_, ERROR 는 _문제_.
8. **분산 trace 없이 마이크로서비스** — _어디서 느린지_ 추정만. trace 가 _진실_.
9. **SLO 가 _내부_ 메트릭** — 사용자 안 보는 메트릭은 SLO 안 됨. _사용자 경험_ 측정.
10. **알람 받고도 _silence_ 만 누름** — fix 안 함. 결국 _fire 안 함_ 만 못함.

## 운영 도구 (참고)

| 영역 | 도구 |
|---|---|
| **에러 추적** | Sentry, Rollbar, Bugsnag, Datadog Error Tracking |
| **로그** | Loki + Grafana, ELK (Elasticsearch + Logstash + Kibana), Datadog Logs, Splunk |
| **분산 trace** | Jaeger, **Tempo** (Grafana), Honeycomb, Datadog APM, NewRelic |
| **메트릭** | Prometheus + Grafana, VictoriaMetrics, Mimir, Datadog |
| **알람** | Alertmanager, PagerDuty, OpsGenie, Slack (라이트), VictorOps |
| **SLO 도구** | **Sloth** (오픈소스, Prometheus rules 자동 생성), Datadog SLOs, Grafana SLO, Nobl9 |
| **OTel 수집** | OpenTelemetry Collector, Vector, Fluent Bit |

## 직접 해보기 TODO

- [ ] `docker compose up otel-collector jaeger` 띄우고 OTLP exporter 로 trace 송출
- [ ] Sloth 로 PromQL rules 자동 생성 ── 본 모듈의 `slo_burn_rate_alerts` 와 비교
- [ ] Sentry 무료 티어 가입 후 `/boom` 호출 → Sentry UI 에서 stacktrace 확인
- [ ] Loki + Promtail + Grafana 띄우고 본 앱의 JSON 로그 _라벨로_ 검색
- [ ] `make run` 후 vegeta 로 부하 → `/slo/burn` 가 _증가_ 확인 + alerts.yaml 의 PromQL 가 _Prometheus 에서 동작_ 확인
- [ ] **runbook 작성** — `tender_SLOFastBurn1h` 알람 발동 시 _뭘 봐야 하는지_ (Grafana 링크 / 대시보드 / 가능 원인 / mitigation)
- [ ] **Postmortem 템플릿** — Google SRE Workbook 의 blameless postmortem 형식 채택

## 다음 단계

**A13 — Python 고급 typing & 메타프로그래밍**. `Generic`, `Protocol`, `TypeVar` bounds, `Literal`, `NewType`, `TypedDict`, 메타클래스, 디스크립터, 컨텍스트 매니저, `functools` 심화.
