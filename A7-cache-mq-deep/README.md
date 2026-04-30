# A7 — 캐시·메시지 큐 심화

11 (Redis) + 13 (Kafka/큐) 의 _운영급 패턴_ 7가지. 현실에서 마주치는 _분산 시스템 어려움_ 들.

## 학습 목표

- **캐시 stampede 방지** — lock-based, **XFetch (Probabilistic Early Refresh)**, SWR
- **Redis HA** — Sentinel vs Cluster, hash tag
- **Saga** — 분산 트랜잭션 + 보상 액션 (orchestration vs choreography)
- **CQRS** — 쓰기 / 읽기 모델 분리
- **Event Sourcing** — 상태 대신 이벤트, replay
- **Schema Registry** — Avro/JSON Schema, 호환성 정책 (BACKWARD/FORWARD/FULL)
- **DLQ** — 독성 메시지 격리 + 재처리 (redrive)

## 디렉토리

```
A7-cache-mq-deep/
├── pyproject.toml
├── Makefile
├── README.md
├── src/cachemqdeep/
│   ├── __init__.py
│   ├── settings.py
│   ├── stampede.py            # lock-based + XFetch
│   ├── redis_ha.py            # Sentinel/Cluster 노트 + HashTag 헬퍼
│   ├── saga.py                # Orchestrator (Step + Compensation)
│   ├── cqrs.py                # Command/Query/Mediator
│   ├── event_sourcing.py      # EventStore + BankAccount.replay
│   ├── schema_registry.py     # JSON Schema + 호환성 검사
│   ├── dlq.py                 # Redis list 기반 DLQ + redrive
│   └── main.py                # FastAPI 앱 (7가지 패턴 라우트)
└── tests/
    ├── conftest.py            # testcontainers Redis
    ├── test_stampede.py       # 동시 100개 → loader 1번
    ├── test_saga.py           # 보상 역순 실행
    ├── test_cqrs.py
    ├── test_event_sourcing.py
    ├── test_schema_registry.py
    ├── test_dlq.py            # retry → dead → redrive
    └── test_app.py            # FastAPI e2e
```

## 실행

```bash
# 1) Redis 인프라 (이미 있으면 생략)
make -C ../05-infra-compose up-cache

# 2) 테스트 (testcontainers 자동 — Redis 컨테이너 별도 안 띄워도 OK)
cd A7-cache-mq-deep
make all

# 3) FastAPI 데모
make run
# → http://127.0.0.1:8007/docs
```

## 1) Cache Stampede

**문제**: 인기 키 TTL 만료 직후 _N 개_ 요청이 동시에 캐시 미스 → 같은 비싼 작업을 N 번 실행.

**해법 3가지**:

```
              ┌─ Lock-based (mutex)
              │   가장 먼저 도착한 요청만 재계산. 나머지는 대기.
              │   문제: 대기 시간 = latency. lock holder 죽으면 timeout 까지 무방비.
              │
 Stampede ────┼─ XFetch (Probabilistic Early Refresh)
              │   _만료 전_ 확률적으로 재계산. 락 없음.
              │   delta * beta * (-ln(rand())) >= TTL_remaining → 재계산
              │
              └─ Stale-While-Revalidate (SWR)
                  _만료 후에도_ 옛 값 반환 + 백그라운드 재계산.
                  HTTP Cache-Control: stale-while-revalidate=N 의 서버측 버전.
```

본 모듈은 1, 2 구현. 3 (SWR) 은 [Caffeine `refreshAfterWrite`](https://github.com/ben-manes/caffeine) 가 우아.

**다국 비교**:
- Spring `@Cacheable(sync = true)` — 1번 자동
- HTTP `Cache-Control: stale-while-revalidate` — 3번 표준
- Cloudflare `cache-rule + stale-while-revalidate` — CDN 레벨

## 2) Redis HA — Sentinel vs Cluster

| 토폴로지 | HA | Sharding | 언제 |
|---|---|---|---|
| Standalone | ❌ | ❌ | 개발/소규모 |
| **Sentinel** | ✅ | ❌ | 데이터 ≤ 메모리, _failover_ 만 필요 |
| **Cluster** | ✅ | ✅ | 데이터 > 단일 노드, _수평 확장_ |

**Cluster 함정**: 다중 키 명령은 _같은 슬롯_ 에 있어야 함. **Hash tag** 사용.

```python
# Cluster-friendly key naming
from cachemqdeep.redis_ha import HashTag
user_tag = HashTag("user:42")
profile_key = user_tag.field("profile")  # → "{user:42}:profile"
cart_key = user_tag.field("cart")        # → "{user:42}:cart"
# 같은 슬롯 → MGET / MSET / MULTI 가능
```

매니지드 옵션: AWS ElastiCache, GCP Memorystore, Redis Enterprise, Valkey OSS.

## 3) Saga — 분산 트랜잭션

**문제**: 마이크로서비스 N 개에 걸친 _원자성_ 이 필요한데 2PC 는 운영 부담 + 가용성 ↓.

**해법**: 각 단계의 _보상 트랜잭션_ 을 정의. 실패 시 _역순_ 으로 보상.

```
Step1 ──Action──▶ ✅
   │
Step2 ──Action──▶ ✅
   │
Step3 ──Action──▶ ❌ FAILED
   │
   └─▶ Step2.compensate ──▶ Step1.compensate
       (역순 실행, idempotent)
```

**두 가지 구현**:

| 방식 | 흐름 | 장단점 |
|---|---|---|
| **Orchestration** | 중앙 코디네이터가 단계 호출 | 흐름 명시적, 디버깅 쉬움 / 단일 장애점 |
| **Choreography** | 이벤트 구독으로 자율 실행 | 결합도 ↓, 추가 단계 자유 / 흐름 추적 어려움 |

본 모듈은 Orchestration. 운영급은 **Temporal** / **AWS Step Functions** / Axon.

**보상 액션 규칙**:
1. **Idempotent** — 같은 보상 두 번 = 한 번
2. 가능하면 **Commutative**, 어렵다면 _역순_ 표준
3. _영원히 실패_ 가능 — 한도 도달 시 _수동 큐_ (DLQ 와 결합)

## 4) CQRS — 읽기/쓰기 분리

**언제 쓰지 말기**: CRUD 단순 앱 — _과한 복잡도_.

**언제 쓰기**:
- 읽기/쓰기 _스케일_ 또는 _패턴_ 이 매우 다름 (대시보드, 검색, 분석)
- 비정규화된 _뷰_ 가 _여러 종류_ 필요
- Event Sourcing 와 _자연 결합_

**점진 단계**:
```
1. 같은 DB 다른 View          ← 가장 가벼움
2. 같은 DB 다른 테이블 (트리거 / outbox 갱신)
3. 다른 DB (write=PG, read=ES)
4. CQRS + Event Sourcing
```

본 모듈은 인메모리 _쓰기 모델 (Order)_ + _읽기 모델 (OrderSummaryView)_.

비교: Spring/Axon `@CommandHandler`, .NET MediatR, Java Akka.

## 5) Event Sourcing

**상태 대신 _이벤트 시퀀스_ 저장**.

```
[AccountOpened balance=0]
[Deposited 100]
[Deposited 50]
[Withdrew 30]
        ↓ replay
balance = 120
```

**장점**:
- 완전한 audit log (자연스러움)
- 시간 여행 (`SELECT WHERE ts <= '2026-01-01'`)
- 새 read model 즉시 생성 (replay)

**함정**:
- 학습 곡선 큼
- 스키마 진화 어려움 → Schema Registry 와 _필수_ 결합
- 매번 replay 비쌈 → **스냅샷** 패턴
- "삭제" 가 어려움 (GDPR 충돌 가능)

**언제 쓰기**:
- audit / 규정 (금융, 의료)
- 도메인이 _변화 자체_ 가 도메인 (회계, 게임 액션)

운영급: **EventStoreDB** (전용), **Marten** (.NET, Postgres jsonb 위), **Axon Server**.

## 6) Schema Registry

**Kafka 같은 broker 는 바이트만 전달** → producer / consumer 가 _구조_ 합의 필요.

**호환성 정책 4종**:

| 정책 | 새 스키마로 _옛_ 데이터 | 옛 스키마로 _새_ 데이터 | 안전한 변경 |
|---|---|---|---|
| BACKWARD | ✅ | ❌ | optional 필드 추가, 필드 삭제 |
| FORWARD | ❌ | ✅ | required 필드 추가 (default), 필드 삭제 |
| FULL | ✅ | ✅ | 위 둘 다 |
| NONE | — | — | 검증 X (위험) |

**Confluent 표준 패턴**: BACKWARD ── consumer 를 _먼저_ 업데이트 (옛+신 둘 다 처리), producer 를 _나중_.

**포맷 비교**:

| 포맷 | 장점 | 단점 |
|---|---|---|
| **JSON Schema** | 사람이 읽기, 디버깅 쉬움 | 큼, 느림 |
| **Avro** | 작고 빠름, 진화 우수 | 스키마 없으면 못 읽음 |
| **Protobuf** | 가장 빠름, gRPC 표준 | Avro 보다 진화 까다로움 |

본 모듈은 JSON Schema 기반 _최소_ registry. 운영: **Confluent Schema Registry**, **Apicurio**, **AWS Glue**.

## 7) Dead Letter Queue (DLQ)

**문제**: 처리 실패 메시지의 _3가지 운명_:
1. 무한 재시도 — _독성 메시지_ 가 큐 막음
2. 그냥 ack — 영원히 사라짐
3. **DLQ 로 격리** ← 정답

```
main_queue ──handler──▶ ✅
   │            │
   │            └──❌ retries++──▶ main_queue (재투입)
   │                       │
   │                       └─ retries >= max ──▶ DLQ
   │
DLQ ──────redrive (수동/스케줄)──────▶ main_queue
```

**DLQ 메타데이터**: `error`, `retries`, `original_topic`, `failed_at` — 디버깅 필수.

**알람**: DLQ 깊이 > 임계 → oncall.

**안티패턴**:
- DLQ 자동 무한 재처리 (영구 깨진 메시지 → 무한 루프)
- DLQ 영원히 보관 (디스크 폭발 — N일 후 archive)
- 재처리 시 _원본 순서_ 무시 (도메인 따라 큰 문제 — 이체 등)

**다국 비교**:
- AWS SQS — DLQ + redrive policy 내장
- RabbitMQ — `x-dead-letter-exchange` 큐 인자
- Kafka Streams — `errors.tolerance=all` + dlq topic
- Sidekiq — dead set + 웹 UI 재처리

## 안티패턴 모음

1. **stampede 무대책** — 인기 키 만료 시 DB 폭발
2. **Saga 보상이 _idempotent_ 아님** — 재시도 중복 효과 (이중 환불 등)
3. **CQRS 를 _초기부터_ 도입** — CRUD 단순 앱에 _과한_ 복잡도
4. **Event Sourcing + 스키마 진화 무대책** — 옛 이벤트 못 읽게 됨
5. **Schema 검증 없이 Kafka** — 잘못된 메시지가 모든 consumer 깨뜨림
6. **DLQ 모니터링 없음** — 메시지 _조용히_ 사라짐
7. **DLQ 메타 없이 격리** — 왜 실패했는지 모름
8. **Saga 동기 호출** — 한 단계 _수 분_ 걸리면 코디네이터 묶임. 비동기 + 영속 상태.
9. **redrive 자동 + 한도 없음** — 깨진 메시지 무한 루프
10. **Cluster 에서 hash tag 무시** — `MGET` / `MULTI` 동작 안 함

## 다국 운영 도구 (참고)

| 영역 | 도구 |
|---|---|
| Saga / Workflow | **Temporal**, AWS Step Functions, Cadence, Camunda, Axon |
| Event Sourcing | **EventStoreDB**, Marten, Axon Server, Apache Kafka + ksqlDB |
| Schema Registry | **Confluent**, Apicurio, AWS Glue |
| DLQ 관리 | AWS SQS console, Sidekiq UI, Kafka UI (provectuslabs), Redpanda Console |
| Redis HA | AWS ElastiCache, GCP Memorystore, Redis Enterprise, Valkey |

## 직접 해보기 TODO

- [ ] `XFetch` 의 _재계산 비율_ 측정 — beta 1.0 vs 2.0, TTL 곡선 plot
- [ ] Saga 에 _재시도 + 백오프_ + DLQ 결합
- [ ] Event Sourcing _스냅샷_ — 100 events 마다 state 저장
- [ ] Schema BACKWARD vs FORWARD vs FULL 직접 시나리오 (필드 추가/제거 후 검증)
- [ ] DLQ + 알람 — Prometheus `redis_list_length{queue="dlq"}` + Grafana
- [ ] Temporal Python SDK 로 Saga 재구현 — 영속 상태 + 자동 재시도
- [ ] CQRS read model 을 _outbox + Kafka_ 로 비동기 갱신 (eventual consistency)

## 다음 단계

**A8 — WebSocket / Server-Sent Events**. 단방향 SSE vs 양방향 WS, Redis pub/sub 으로 다중 인스턴스 브로드캐스트.
