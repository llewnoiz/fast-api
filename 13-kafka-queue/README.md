# 13 — Kafka + 백그라운드 큐

세 가지 비동기 작업 메커니즘과 _언제 무엇을_ 쓰는지.

## 학습 목표

- **`aiokafka`** — async Kafka 프로듀서/컨슈머
- **컨슈머 그룹** + **수동 commit** (at-least-once)
- **transactional outbox** — DB 변경과 메시지 발행 일관성
- **`arq`** — Redis 기반 async 백그라운드 큐 (Celery 비교)
- **FastAPI `BackgroundTasks`** — 가장 가벼운 fire-and-forget

## 디렉토리

```
13-kafka-queue/
├── pyproject.toml          # aiokafka, arq, sqlalchemy, asyncpg
├── Makefile                # make run / worker / test
├── README.md
├── src/mqapp/
│   ├── settings.py         # kafka_bootstrap, redis_url, database_url
│   ├── kafka_producer.py   # KafkaPublisher + make_producer
│   ├── kafka_consumer.py   # consume_loop (수동 commit, at-least-once)
│   ├── outbox.py           # OutboxEvent + record_event + relay_once
│   ├── arq_worker.py       # send_email / process_order + WorkerSettings
│   └── main.py             # FastAPI 라우트 (publish/enqueue/bg)
└── tests/
    ├── conftest.py
    ├── test_background_tasks.py   # FastAPI BackgroundTasks
    └── test_outbox.py              # Postgres testcontainers + 가짜 Publisher
```

## 실행

```bash
cd .. && uv sync && cd 13-kafka-queue

# 도커 인프라 (kafka + redis 필요)
cd ../05-infra-compose && make up-cache && make up-kafka && cd ../13-kafka-queue

# FastAPI 앱
make run

# arq 워커 (별도 터미널)
make worker

# 검증
make all
```

## 세 가지 비동기 작업 메커니즘 — 언제 무엇을?

| 도구 | 언제 | 비교 |
|---|---|---|
| **FastAPI `BackgroundTasks`** | 짧은 fire-and-forget (수 백 ms), 손실 OK | NestJS 응답 후 비동기, Spring `@Async` |
| **`arq` (Redis 큐)** | 수 초~수 분 작업, 재시도/스케줄링/모니터링 | **Celery** (Python 표준), Bull (Node), Sidekiq (Ruby) |
| **`aiokafka` (이벤트 스트리밍)** | 다중 컨슈머, 영속성, 시간 윈도, 감사 로그 | Spring Kafka, NestJS `@MessagePattern` |

선택 기준:
```
손실 OK + 짧음            → BackgroundTasks
영속성 + 재시도 + 단순     → arq (또는 Celery)
다중 컨슈머 + 영속성 + 순서 → Kafka
```

## 다국 언어 비교

| 개념 | 가장 가까운 비교 |
|---|---|
| **aiokafka** | Spring Kafka `KafkaTemplate` + `@KafkaListener` |
| **컨슈머 그룹** | 동일 — Kafka 표준 개념 |
| **transactional outbox** | **Spring Modulith** Application Events, **Debezium CDC** |
| **arq** | **Celery** (가장 가까움), Bull (Node), Sidekiq (Ruby) |
| **arq vs Celery** | arq = async 친화·가벼움, Celery = 풍부·sync 친화 |

## 핵심 패턴

### 1) Kafka producer — 앱 단위 _하나_

```python
async def lifespan(app):
    producer = await make_producer(bootstrap)   # acks="all" + idempotence
    app.state.kafka = KafkaPublisher(producer, topic)
    yield
    await producer.stop()
```

`acks="all"` + `enable_idempotence=True` 조합 = 메시지 _exactly-once_ 의 절반 (Kafka transactional API 까지면 완성).

### 2) Consumer — 수동 commit

```python
async for msg in consumer:
    try:
        await handler(...)
        await consumer.commit()    # ← 처리 _성공 후_ commit
    except:
        # commit 안 함 → 재처리 (at-least-once)
        ...
```

**at-least-once**: 같은 메시지 _두 번 처리될 수도_ → handler 가 _idempotent_ 해야 함 (예: DB UPSERT, dedup key).

### 3) Transactional Outbox — DB + Kafka 일관성

```python
# 같은 트랜잭션 안에 _둘 다_
async with session.begin():
    await session.execute(insert(Order).values(...))
    await record_event(session, topic="order.created", ...)
# ↑ 트랜잭션 커밋 → DB + outbox 둘 다 살거나 둘 다 안 살거나

# 별도 워커가 폴링하며 outbox → Kafka relay
await relay_once(session, publisher)
```

**왜?** 이상적으로 `db.commit() + kafka.send()` _둘 다_ 원자적이어야 하지만, 두 시스템 분산 트랜잭션은 _복잡/느림_. outbox 는 _DB 단일 트랜잭션_ 만 사용.

대안:
- **Debezium CDC** — DB log (WAL) 직접 읽음. outbox 테이블 _없이도_ 가능.
- **Spring Modulith** — Spring 생태계 자동.

### 4) arq — _async 친화_ 큐

```python
# 작업 정의
async def send_email(ctx, to: str, subject: str) -> str: ...

class WorkerSettings:
    functions = [send_email]
    redis_settings = ...
    max_tries = 3
    job_timeout = 30

# enqueue (FastAPI 안에서)
job = await arq.enqueue_job("send_email", "a@x.com", "hi")
```

**vs Celery**: Celery 는 sync 코드 잘 맞음, arq 는 async 표준 (FastAPI 와 자연). 커뮤니티 / 기능 수는 Celery 가 압도적.

### 5) BackgroundTasks — _가장 가벼움_

```python
@app.post("/bg/touch")
async def touch(bg: BackgroundTasks):
    bg.add_task(do_work)              # 응답 _후_ 실행
    return {"status": "scheduled"}    # 즉시 반환
```

장점: 외부 의존성 X, 가장 단순.
단점: 같은 프로세스 — _재시작 시 유실_, _재시도 X_, _모니터링 X_, _분산 X_.

## 안티패턴

1. **producer 매 publish 마다 만들기** — 커넥션 비용 ↑. lifespan _하나_.
2. **auto-commit + 처리 실패** — 메시지 유실. 수동 commit + idempotent handler.
3. **DB + Kafka 분산 트랜잭션 시도** — 복잡/느림. outbox 또는 CDC.
4. **outbox 테이블 무한 증가** — `SENT` 행 주기 청소 또는 파티션.
5. **POST 라우트에서 무거운 작업 _직접_ 처리** — 응답 시간 폭발. arq/Celery 로.
6. **BackgroundTasks 에 _중요_ 작업** — 손실 위험. 결제/주문 등은 무조건 큐.
7. **Kafka 토픽 무제한 retention** — 디스크 폭발. retention.ms 또는 log compaction.
8. **컨슈머 그룹 같은 이름 _다른 토픽_** — 오프셋 충돌. 의미 단위로 그룹명 분리.
9. **idempotent 하지 않은 handler** — at-least-once 환경에서 _중복 처리_ 사고. dedup key 또는 UPSERT.

## 직접 해보기 TODO

- [ ] `kafka_consumer.consume_loop` 를 `arq` cron job 으로 등록 (대안 패턴)
- [ ] outbox 의 `SENT` 행 주기 정리 — `arq` cron 으로 1일 보관 후 삭제
- [ ] dead-letter topic — handler 실패 시 _다른 토픽_ 으로 보내고 commit
- [ ] arq 작업에 `@retry(max_tries=5, backoff=...)` 정책 커스텀
- [ ] `BackgroundTasks` 와 arq 의 _실패 시나리오_ 비교 (앱 재시작 시 어떻게 다른지)
- [ ] Kafka 헤더에 12 의 `traceparent` 자동 첨부 → consumer 측에서 이어진 trace 확인

## 다음 단계

**14 — 공통 모듈 패키징/팀 공유**. 06~13 에서 만든 envelope / 인증 / httpx 클라이언트 / 로깅 설정을 _별도 패키지_ 로 추출해서 사내 PyPI 또는 git+ssh 로 배포.
