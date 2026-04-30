# FastAPI + Python 학습 커리큘럼

Java/Spring·Go 백엔드 경험자가 FastAPI 베스트 프랙티스로 직접 코딩하며 Python을 함께 익히는 단계별 학습 저장소.

전체 설계는 [`/.claude/plans/fast-api-python-tender-key.md`](file:///Users/hyunmin.song/.claude/plans/fast-api-python-tender-key.md) 참고.

## 🚀 실무 시작 키트 — `templates/fastapi-best-practice/`

본 학습 모노레포의 _운영급 패턴_ 만 추려 모은 **자체 완결 FastAPI 템플릿**. 새 프로젝트 시작 시 _이 디렉토리 통째로 복사_ 하면 됨.

포함: FastAPI factory + Settings + JWT/RBAC + Postgres(SQLAlchemy 2.0 + Alembic) + Redis cache-aside + ApiEnvelope/에러 핸들러/correlation-id/구조화 로그 + 테스트(testcontainers) + Docker multi-stage + GitHub Actions. 39 tests, ruff/mypy clean.

자세한 내용은 [`templates/fastapi-best-practice/README.md`](./templates/fastapi-best-practice/README.md) 참고.

## 사전 준비

```bash
# uv 설치 확인 (없다면 brew install uv)
uv --version

# Python 3.12 자동 다운로드 + 가상환경 생성
uv sync

# (선택) 도커 데몬 실행 — 05단계 이후 필요
docker info
```

루트에서 `uv sync` 한 번이면 워크스페이스 전체 의존성이 `.venv` 에 설치됩니다.

## 단계별 진행 체크리스트

| # | 디렉토리 | 주제 | 상태 |
|---|---|---|---|
| 01 | [01-python-basics](./01-python-basics/) | Python 기본 + uv | ✅ 완료 |
| 02 | [02-package-structure](./02-package-structure/) | Python 패키지/모듈 구조, ruff/mypy/pre-commit | ✅ 완료 |
| 03 | [03-libraries-tour](./03-libraries-tour/) | pydantic / httpx / orjson / jsonpath / datetime / structlog / dotenv | ✅ 완료 |
| 04 | [04-fastapi-hello](./04-fastapi-hello/) | FastAPI Hello + OpenAPI + 설정 관리 | ✅ 완료 |
| 05 | [05-infra-compose](./05-infra-compose/) | Docker Compose 인프라 (Postgres/Redis/Kafka) | ✅ 완료 |
| 06 | [06-async-deep](./06-async-deep/) | asyncio 심화, sync vs async 안티패턴 | ✅ 완료 |
| 07 | [07-request-error-version](./07-request-error-version/) | 요청·응답·에러·API 버전 관리 | ✅ 완료 |
| 08 | [08-testing](./08-testing/) | pytest + httpx + testcontainers (3계층 테스트) | ✅ 완료 |
| 09 | [09-auth](./09-auth/) | JWT, OAuth2 password flow, RBAC | ✅ 완료 |
| 10 | [10-db-transaction](./10-db-transaction/) | SQLAlchemy 2.0 async + Alembic + UoW | ✅ 완료 |
| 11 | [11-redis-ratelimit](./11-redis-ratelimit/) | Redis 캐시·락 + 쓰로틀링 | ✅ 완료 |
| 12 | [12-service-comm-observability](./12-service-comm-observability/) | httpx 재시도/회로차단기, structlog, OTel, Prometheus | ✅ 완료 |
| 13 | [13-kafka-queue](./13-kafka-queue/) | aiokafka + arq 큐 + transactional outbox | ✅ 완료 |
| 14 | [14-shared-package](./14-shared-package/) | 공통 모듈 패키징·팀 공유 (fastapi-common) | ✅ 완료 |
| 15 | [15-mini-project](./15-mini-project/) | 🎓 통합 미니 tender 서비스 (04~14 결합) | ✅ **완료** |
| A1 | [A1-i18n](./A1-i18n/) | (부록) 다국어 처리 (Accept-Language / gettext / Pydantic / Babel) | ✅ 완료 |
| A2 | [A2-load-test](./A2-load-test/) | (부록) 부하 테스트 (locust) | ✅ 완료 |
| A3 | [A3-cicd](./A3-cicd/) + `.github/` | (부록) CI/CD (GitHub Actions + dependabot) | ✅ 완료 |
| A4 | [A4-kubernetes](./A4-kubernetes/) | (부록) Kubernetes (raw manifests + Helm chart) | ✅ 완료 |
| A5 | [A5-security](./A5-security/) | (부록) 보안 심화 (TOTP, API key, OAuth 3rd, OWASP, 시크릿) | ✅ 완료 |
| A6 | [A6-db-deep](./A6-db-deep/) | (부록) DB 심화 (인덱스 / N+1 / jsonb / FTS / LISTEN-NOTIFY / Expand-Contract) | ✅ 완료 |
| A7 | [A7-cache-mq-deep](./A7-cache-mq-deep/) | (부록) 캐시·MQ 심화 (stampede / Saga / CQRS / Event Sourcing / Schema Registry / DLQ) | ✅ 완료 |
| A8 | [A8-realtime](./A8-realtime/) | (부록) WebSocket / SSE / Redis pub/sub fan-out (다중 인스턴스) | ✅ 완료 |
| A9 | [A9-file-io](./A9-file-io/) | (부록) 파일 업로드/다운로드 (multipart / Range / presigned / chunked upload) | ✅ 완료 |
| A10 | [A10-graphql](./A10-graphql/) | (부록) GraphQL (Strawberry) — Query/Mutation/DataLoader/N+1 회피 | ✅ 완료 |
| A11 | [A11-ddd](./A11-ddd/) | (부록) DDD / 헥사고날 (Aggregate / VO / Domain Event / Ports & Adapters) | ✅ 완료 |
| A12 | [A12-observability](./A12-observability/) | (부록) 관측가능성 운영급 (Sentry / 구조화 로그 / OTel / SLO / Grafana / Alertmanager) | ✅ 완료 |
| A13 | [A13-typing-deep](./A13-typing-deep/) | (부록) Python 고급 typing & 메타프로그래밍 (PEP 695 / Protocol / Descriptor / Generator / Context Manager) | ✅ 완료 |
| A14 | [A14-perf](./A14-perf/) | (부록) 성능 / 프로파일링 (cProfile / tracemalloc / async 함정 / 알고리즘 / 워커) | ✅ 완료 🎓 |

## 단계별 표준 산출물

각 단계 디렉토리는 다음 형태로 구성됩니다.

```
NN-topic/
├── README.md       # 학습 목표 / 핵심 개념 / Java·Go 비교 / 안티패턴 / TODO
├── pyproject.toml  # uv 의존성
├── Makefile        # make run / test / lint
├── src/            # 실행 가능한 샘플 코드
└── tests/          # pytest 샘플
```

## 진행 방식

1. 단계당 1세션. 개념 → 샘플 코드 → 실행 → TODO 도전 → 다른 언어 비교 정리.
2. 각 단계 완료 시 위 체크리스트(🟢→✅)와 단계별 README의 TODO 박스를 갱신.
3. 어느 단계 폴더에서든 `make run / test / lint` 가 동작하도록 통일.
4. 05단계 이후는 모두 루트 `docker-compose.yml` 위에서 동작 (필요한 profile만 up).
