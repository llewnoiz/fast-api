# FastAPI + Python 학습 커리큘럼

Java/Spring·Go 백엔드 경험자가 FastAPI 베스트 프랙티스로 직접 코딩하며 Python을 함께 익히는 단계별 학습 저장소.

전체 설계는 [`/.claude/plans/fast-api-python-tender-key.md`](file:///Users/hyunmin.song/.claude/plans/fast-api-python-tender-key.md) 참고.

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
| 03 | 03-libraries-tour | pydantic / httpx / orjson / jsonpath 등 | ⚪ 대기 |
| 04 | 04-fastapi-hello | FastAPI Hello + OpenAPI + 설정 관리 | ⚪ 대기 |
| 05 | 05-infra-compose | Docker Compose 인프라 (Postgres/Redis/Kafka) | ⚪ 대기 |
| 06 | 06-async-deep | asyncio 심화, sync vs async 안티패턴 | ⚪ 대기 |
| 07 | 07-request-error-version | 요청·응답·에러·API 버전 관리 | ⚪ 대기 |
| 08 | 08-testing | pytest + httpx + testcontainers | ⚪ 대기 |
| 09 | 09-auth | JWT, OAuth2, RBAC | ⚪ 대기 |
| 10 | 10-db-transaction | SQLAlchemy 2.0 async + Alembic + UoW | ⚪ 대기 |
| 11 | 11-redis-ratelimit | Redis 캐시·락 + 쓰로틀링 | ⚪ 대기 |
| 12 | 12-service-comm-observability | httpx 재시도/회로차단기, structlog, OTel | ⚪ 대기 |
| 13 | 13-kafka-queue | aiokafka + arq 큐 | ⚪ 대기 |
| 14 | 14-shared-package | 공통 모듈 패키징·팀 공유 | ⚪ 대기 |
| 15 | 15-mini-project | 통합 미니 tender 서비스 | ⚪ 대기 |
| A1 | A1-i18n | (부록) 다국어 처리 | ⚪ 선택 |

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
