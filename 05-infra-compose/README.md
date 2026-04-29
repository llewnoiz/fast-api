# 05 — Docker Compose 인프라 일괄 도입

지금까지 만든 04 FastAPI 앱이 _진짜_ 백엔드처럼 동작하려면 DB / 캐시 / 메시지 브로커 가 옆에 있어야 한다. 이 단계에서 **Postgres + Redis + Kafka(Redpanda)** 를 _하나의 compose 파일_ 로 띄우고, 04 fastapi-hello 를 _컨테이너_ 로도 띄울 수 있게 만든다.

**중요**: `docker-compose.yml` 과 `.env.example` 은 _리포 루트_ 에 있다. 이후 06~15 단계가 모두 _그 한 파일_ 을 재사용한다.

## 디렉토리 분배

```
fast-api/                       ← 리포 루트
├── docker-compose.yml          ← ⭐ 인프라 정의 (06~15 가 모두 사용)
├── .env.example                ← 자격증명 템플릿
├── .dockerignore               ← Docker 빌드 컨텍스트 제외 목록
└── 05-infra-compose/           ← 이 단계의 _학습 자료_
    ├── Dockerfile              ← 04 fastapi-hello 컨테이너 이미지
    ├── Makefile                ← make up / down / logs / psql / redis-cli
    └── README.md               (← 지금 보고 있는 파일)
```

## 사전 준비

```bash
# Docker Desktop 실행 (macOS)
open -a Docker

# 데몬 살아있는지 확인
docker info | head -5

# .env 만들기 (한 번만)
cp .env.example .env             # 리포 루트에서

# (선택) 이미지 미리 받기 — 느린 네트워크에서
cd 05-infra-compose && make pull
```

## 가장 자주 쓰는 명령

```bash
cd 05-infra-compose

make up                # db + cache (기본 조합)
make up-kafka          # 추가로 Kafka
make up-all            # 전부

make ps                # 떠 있는 서비스 + 헬스체크 상태
make logs              # 실시간 로그
make psql              # Postgres 접속
make redis-cli         # Redis 접속

make down              # 컨테이너 정리 (볼륨은 유지)
make down-clean        # 볼륨까지 삭제 (데이터 초기화)

make config            # YAML 합치기 + 문법 검증 (도커 데몬 없어도 일부 동작)
make build             # 04 fastapi-hello 이미지 빌드
make up-app            # 그 이미지를 떠서 db/cache 와 함께 (depends_on healthcheck 대기)
```

## 다국 언어 / 다른 도구와 비교

| 개념 | Docker Compose | 가장 가까운 비교 |
|---|---|---|
| 서비스 정의 | `services:` 블록 | **K8s** Deployment + Service, **NestJS** 모놀리식 → 분리하는 단계 |
| 호스트명 = 서비스 이름 | `db`, `cache`, `kafka` | **K8s** Service DNS (`my-svc.namespace.svc.cluster.local`) |
| profiles | 선택적 서비스 | **Spring Profiles** (`dev`, `prod`) 와 비슷한 _스위치_ 개념 |
| depends_on + healthcheck | 시작 순서 + 준비 대기 | **K8s** initContainers / readiness probe |
| 볼륨 | `db-data:`, `cache-data:` | **K8s** PersistentVolumeClaim |
| 네트워크 (자동) | 같은 compose 안 서비스끼리 자동 통신 | **K8s** ClusterIP, **Spring** Eureka 자동 디스커버리 자리 |
| `Dockerfile` | 이미지 빌드 레시피 | **Spring Boot** `Dockerfile` (Buildpacks 도 인기), **NestJS** Dockerfile |
| multi-stage build | builder + runner 분리 | **Java** distroless 이미지, **Node** `node:slim` runner |
| `.dockerignore` | 빌드 컨텍스트 줄이기 | **Git** `.gitignore` 의 빌드 버전 |

**Docker Compose ≈ "1대 짜리 K8s"**. 학습/개발에선 충분하고, 실제 운영 배포는 K8s / ECS / Cloud Run 등으로 _자연스럽게 옮겨감_ — 개념이 같아서 마이그레이션 쉬움.

## 핵심 개념

### 1) `profiles` — 필요한 것만 띄우기

서비스마다 `profiles: [db, all]` 같이 라벨 붙임. `--profile db up` 하면 그 라벨 가진 서비스만 시작. 단계마다 _필요한 인프라 다른데 매번 새 compose 안 만들어도_ 됨.

| 단계 | 필요한 profile |
|---|---|
| 10 (DB+트랜잭션) | `db` |
| 11 (Redis+RateLimit) | `cache` |
| 12 (서버간 통신) | (의존성 없음, FastAPI 만) |
| 13 (Kafka+큐) | `kafka` + `cache` |
| 15 (통합) | `all` |

### 2) 컨테이너 _안에서_ vs _호스트에서_ 호스트명

```
┌─────────────────────────┐
│ docker compose 네트워크   │
│ ┌────┐  ┌────┐  ┌────┐   │
│ │ db │  │cache│ │ app │   │     ← 컨테이너끼리: 서비스 이름으로
│ └────┘  └────┘  └────┘   │       (예: postgres://db:5432)
└──────────┬──────────────┘
           │ 포트 매핑 (5432, 6379, 9092, 8000)
           ▼
       ┌─────────┐
       │ macOS    │           ← 호스트(개발 머신) 에선:
       │ 호스트    │             localhost:5432, localhost:6379
       └─────────┘             localhost:8000
```

**규칙**: 도커 _컨테이너 안에서_ 다른 서비스 호출은 _서비스 이름_ (예: `db`), _호스트(맥)에서_ 는 `localhost:매핑포트`.

### 3) `depends_on` + `healthcheck` — 진짜 _준비된 후_ 시작

```yaml
app:
  depends_on:
    db:
      condition: service_healthy   # ← db 의 healthcheck 가 통과해야 app 시작
```

Postgres 가 _프로세스만_ 떠있는 게 아니라 _쿼리 받을 준비_ 가 됐는지 (`pg_isready`) 까지 확인. **K8s readiness probe** 와 같은 모델.

### 4) Multi-stage Dockerfile — _작은_ 이미지 만들기

```
┌─ builder (uv 이미지, 무거움) ──────────────┐
│   uv 가 의존성 wheel 빌드, virtualenv 생성  │
└─────────────────────────────────────────┘
              │ COPY --from=builder
              ▼
┌─ runner (python:slim, 가벼움) ────────────┐
│   builder 가 만든 .venv + 코드만 복사       │
│   uv 자체는 _최종 이미지에 안 포함_         │
└─────────────────────────────────────────┘
```

장점:
- 최종 이미지 ↓ (수백 MB 절약)
- 빌드 도구 / 시크릿이 _최종 이미지에 없음_ → 보안 ↑
- 레이어 캐시 — `pyproject.toml + uv.lock` 만 바뀌어도 의존성 레이어만 다시 빌드

비교: **Spring Boot** Buildpacks 자동 multi-stage, **Node** `node:alpine` 흔히 사용.

### 5) Non-root 사용자

```dockerfile
RUN groupadd --system --gid 1000 app && useradd --system --uid 1000 ...
USER app
```

**컨테이너 안에서 root 로 실행하지 말 것** — 컨테이너 탈출 시도 시 호스트 권한 노출 위험. K8s 에선 `securityContext.runAsNonRoot: true` 강제 가능.

## 안티패턴

1. **`latest` 태그 운영 사용** — 어느 버전인지 모름. 항상 명시 (`postgres:16-alpine`).
2. **컨테이너 안에서 root 실행** — 보안 사고 시 피해 ↑.
3. **시크릿을 환경변수 평문** — 운영에선 _Secret Manager_ (AWS / Vault) 또는 K8s Secret (마운트).
4. **빌드 컨텍스트에 `.env` / `.git/` 포함** — `.dockerignore` 누락 → 시크릿 / 큰 파일 빌드에 들어감.
5. **`pip install --no-cache-dir` 안 씀** — 캐시가 이미지에 남음. `uv` 는 `--no-cache` 또는 `UV_NO_CACHE`.
6. **`HEALTHCHECK` 없음** — 죽었는지 살았는지 도커가 판단 못 함.
7. **단일 stage Dockerfile** — 빌드 도구가 최종 이미지에 남음. multi-stage 표준.
8. **`docker compose` 와 `docker-compose` 혼용** — 후자는 v1, 이미 deprecated. 항상 _공백_ 형태.
9. **`depends_on` 만 쓰고 `condition: service_healthy` 안 씀** — 그냥 _시작 순서_ 만 보장. 진짜 _준비_ 는 헬스체크 필요.

## 빠른 동작 확인 (도커 켜진 후)

```bash
cd 05-infra-compose

# 1) compose 문법 검증 (데몬 일부 필요)
make config | head -30

# 2) db + cache 띄우기
make up
make ps                  # → STATUS: healthy 확인
docker compose ps        # 또는 직접

# 3) 진짜 접속
make psql
# postgres=#   \dt              ← 테이블 (지금은 비어있음)
# postgres=#   SELECT version();
# postgres=#   \q

make redis-cli
# 127.0.0.1:6379>  PING         ← PONG
# 127.0.0.1:6379>  SET hi 1
# 127.0.0.1:6379>  GET hi
# 127.0.0.1:6379>  exit

# 4) 04 fastapi-hello 컨테이너로 띄우기
make up-app              # build + up + 의존성(db/cache) 대기
curl http://localhost:8000/healthz
# → {"status":"ok","app":"fastapi-hello","version":"0.1.0","env":"dev"}

# 5) 정리
make down                # 컨테이너만 종료
make down-clean          # 볼륨까지 삭제 (DB 데이터 초기화)
```

## 직접 해보기 TODO

- [ ] `.env.example` 을 `.env` 로 복사 후 `POSTGRES_PORT=5433` 으로 바꾸고 `make up-db` — 5433 포트로 뜨는지
- [ ] `make psql` 로 접속해서 `CREATE TABLE foo(id int);` `INSERT` 한 다음 `make down` (볼륨 유지) 후 `make up` 다시 → 데이터 _남아있는지_ 확인
- [ ] 이번엔 `make down-clean` 후 `make up-db` → 데이터 _사라졌는지_
- [ ] `docker compose --profile kafka up -d` 후 `make rpk-topics` 로 토픽 목록 (비어있음)
- [ ] `docker compose exec kafka rpk topic create test-topic` 로 토픽 생성, 다시 `make rpk-topics`
- [ ] `make build` 로 fastapi-hello 이미지 빌드 후 `docker images | grep hello` 로 사이즈 확인 (수백 MB 이내가 정상)
- [ ] `make up-app` 후 `docker compose ps` 의 `STATUS` 가 `healthy` 가 되는지 (HEALTHCHECK 동작 확인)

## 다음 단계

**06 — async 심화**. 이벤트 루프, `asyncio.gather`, sync/async 안티패턴. 지금까지 _async 코드를 쓰기만_ 했다면 06 에서 _내부 동작_ 까지. 04 의 `lifespan`, 03 의 `httpx.AsyncClient`, 그리고 06 이후의 DB / Redis / Kafka 클라이언트 모두 async — 이걸 _제대로_ 이해해야 11~13 단계가 매끄러움.
