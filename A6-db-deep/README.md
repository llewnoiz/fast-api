# A6 — DB 심화 (인덱스 / N+1 / jsonb / FTS / LISTEN-NOTIFY / Zero-downtime 마이그레이션)

10 단계 (DB 트랜잭션) 의 _자연 확장_. _운영급 DB_ 에서 가장 자주 마주치는 6가지 주제.

## 학습 목표

- **인덱스 전략** — B-tree / 복합 / 부분 / expression / GIN / GiST
- **EXPLAIN [ANALYZE]** 읽는 법 — Seq Scan vs Index Scan vs Bitmap Heap Scan
- **N+1** 문제 — selectinload / joinedload / 디버깅 기법
- **Postgres jsonb** — `@>`, `?`, GIN 인덱스, jsonb_path_ops
- **Postgres FTS** — `tsvector` / `tsquery` / `ts_rank` / `websearch_to_tsquery`
- **LISTEN / NOTIFY** — 가벼운 pub/sub
- **Zero-downtime 마이그레이션** — Expand → Dual-write → Backfill → Switch read → Contract

## 디렉토리

```
A6-db-deep/
├── pyproject.toml
├── alembic.ini
├── alembic/
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│       ├── 0001_initial.py                            # 테이블 + 인덱스 모음 + tsvector GENERATED
│       ├── 0002_expand_add_email_lower.py             # Expand: 컬럼 추가 + CONCURRENTLY 인덱스 + 백필
│       └── 0003_contract_set_not_null.py              # Contract: NOT NULL 제약
├── Makefile
├── README.md
├── src/dbdeep/
│   ├── __init__.py
│   ├── settings.py
│   ├── database.py
│   ├── models.py                  # User / Post / Comment + 6가지 인덱스
│   ├── seed.py                    # 학습용 데이터 시드
│   ├── n_plus_one.py              # naive / selectinload / joinedload + 쿼리 카운터
│   ├── jsonb.py                   # @>, GIN 활용
│   ├── fts.py                     # tsvector + ts_rank
│   ├── listen_notify.py           # psycopg sync NOTIFY/LISTEN
│   └── main.py                    # FastAPI 앱
└── tests/
    ├── conftest.py                # testcontainers Postgres + Alembic
    ├── test_indexes.py            # B-tree / 부분 인덱스 / N+1 쿼리 카운트
    ├── test_jsonb_fts.py          # @> / FTS / GIN 카탈로그 검증
    ├── test_zero_downtime_migration.py
    └── test_app.py                # FastAPI e2e
```

## 실행

```bash
# 1) 인프라 — 05 단계의 docker-compose
make -C ../05-infra-compose up

# 2) 마이그레이션 (psycopg sync)
cd A6-db-deep
make migrate

# 3) FastAPI 앱
make run
# → http://127.0.0.1:8006/docs
# → POST /seed 후 /n-plus-one/* 비교
```

## EXPLAIN 가이드 — 핵심만

```
EXPLAIN ANALYZE SELECT ... ;
```

| 노드 | 의미 | 언제 |
|---|---|---|
| **Seq Scan** | 테이블 _전체_ 스캔 | 데이터 적거나 인덱스 없음 |
| **Index Scan** | 인덱스 _순회_ → 행 직접 접근 | 결과 적고 정렬 활용 |
| **Index Only Scan** | 인덱스에서 _전부 충족_, 테이블 안 봄 | 가장 빠름. covering index. |
| **Bitmap Heap Scan** | 인덱스로 페이지 비트맵 → 일괄 읽기 | 결과 _중간_ 크기 |
| **Hash Join** / **Merge Join** | JOIN 알고리즘 | 통계가 좌우 |

**비용 (cost=…)**: planner 가 _선택_ 한 추정치. `ANALYZE` 가 실측 시간/행 수 표시.

```
EXPLAIN (ANALYZE, BUFFERS, FORMAT text) SELECT ...;
```

`BUFFERS` 키워드 — 캐시 hit/miss 까지. _운영 분석_ 의 정석.

## 인덱스 6종 치트시트

| 종류 | 만드는 법 (SQLAlchemy) | 언제 |
|---|---|---|
| **B-tree** (기본) | `mapped_column(..., index=True)` | =, <, >, BETWEEN, ORDER BY, LIKE 'prefix%' |
| **복합** | `Index("ix", "a", "b")` | _왼쪽 prefix_ 우선. (a) 만 검색해도 활용 |
| **UNIQUE** | `mapped_column(..., unique=True)` | 자동 unique 제약 + 빠른 조회 |
| **부분** | `Index(..., postgresql_where=...)` | 소수 행만 인덱싱 (디스크 ↓) |
| **expression** | `Index("ix", func.lower("col"))` | `WHERE lower(col) = ...` |
| **GIN** | `Index(..., postgresql_using="gin")` | jsonb / tsvector / 배열 |
| **GiST** | `postgresql_using="gist"` | tsvector (작고 update 친화), 지오메트리 |

**안티패턴**:
- 모든 컬럼에 인덱스 — 쓰기 비용 ↑, 디스크 ↑. 인덱스도 _자원_.
- LIKE `%suffix` — B-tree 못 씀. 역방향 인덱스 또는 trigram (`pg_trgm`).
- WHERE 안 쓰는 컬럼에 인덱스.

## N+1 디버깅

**증상**: 응답 느림 / 로그에 _같은 모양 SELECT_ 가 N 번 반복.

**탐지**:
```python
# 12 단계 OTel 또는 본 모듈 count_queries 로 _쿼리 수 측정_
with count_queries(engine) as q:
    do_request()
assert q.count <= expected
```

**해결**:
```python
# Bad — lazy load 가 N+1
users = (await session.scalars(select(User))).all()
for u in users:
    print(u.posts)  # 매번 쿼리

# Good — selectinload (1 + 1 = 2 쿼리)
users = (await session.scalars(
    select(User).options(selectinload(User.posts))
)).all()
```

**선택 가이드**:
- 1:N 다수 → **selectinload** (`WHERE id IN (...)`)
- N:1 단일 → **joinedload** (LEFT JOIN)
- 깊은 트리 → 아래로 내려갈 수록 selectinload 가 안전 (joinedload 는 행 폭발)

비교: Spring Data JPA `@EntityGraph(attributePaths = "posts")`, NestJS TypeORM `relations: ["posts"]`.

## jsonb 활용 패턴

```sql
-- containment — GIN 활용
SELECT * FROM deep_posts WHERE tags @> '{"category": "tech"}';

-- 배열 포함
SELECT * FROM deep_posts WHERE tags @> '{"labels": ["fastapi"]}';

-- 키 존재
SELECT * FROM deep_posts WHERE tags ? 'category';

-- 텍스트 추출 + 캐스팅
SELECT * FROM deep_posts WHERE (tags->>'views')::int > 100;
```

**경험칙**:
- _자주 쿼리되는_ 필드 → 정식 컬럼으로 빼는 게 정석.
- _가변/스파스/메타_ 데이터 → jsonb 가 적합.
- jsonb 깊은 병합은 PG `||` 가 _얼고_ 만 — 깊은 병합은 PL/pgSQL 또는 앱 레이어.

## Postgres FTS

```sql
-- tsvector 미리 계산 (GENERATED ALWAYS AS) — 본 마이그레이션 0001 이 적용
SELECT id, title FROM deep_posts
WHERE search @@ websearch_to_tsquery('english', 'fastapi python');

-- 관련도 정렬
SELECT id, ts_rank(search, q) AS rank
FROM deep_posts, websearch_to_tsquery('english', 'fastapi') q
WHERE search @@ q
ORDER BY rank DESC LIMIT 10;
```

**가중치**: `setweight(to_tsvector('english', title), 'A') || setweight(to_tsvector('english', body), 'B')` — 본 마이그레이션 0001 의 GENERATED 식 참고.

**한계**: 대규모 / 다국어 / 동의어 / 자동완성 → **Elasticsearch / OpenSearch / Meilisearch**.

## LISTEN / NOTIFY

```python
# 발신자
notify(sync_url, "cache_invalidate", {"key": "user:123"})

# 수신자 (별도 프로세스/연결)
for msg in listen_once(sync_url, "cache_invalidate"):
    cache.delete(msg["key"])
```

**용도**:
- 다중 인스턴스 _캐시 무효화_ (가벼움)
- 마이그레이션 후 모듈 _재로드_
- 작은 이벤트 fan-out (Kafka 에 비해 _가볍고 즉시_)

**주의**: 영속성 X / 페이로드 8KB 제한 / LISTEN 안 하던 시점은 누락. 영속/순서/스케일 → Kafka.

## Zero-downtime 마이그레이션 — Expand-Contract

운영에서 _다운타임 없이_ 스키마 바꾸는 5단계:

```
[Code v1, Schema v1]
        │ (1) Expand 마이그레이션 — 새 컬럼/인덱스 _추가만_
        ▼
[Code v1, Schema v2]    ← 구 코드는 새 컬럼 무시 (호환)
        │ (2) Code v2 배포 — dual-write (구+신 양쪽에 쓰기)
        ▼
[Code v2, Schema v2]
        │ (3) Backfill 배치 — 과거 데이터를 신 컬럼으로 채우기
        ▼
[Code v2, Schema v2 (filled)]
        │ (4) Code v3 배포 — 신 컬럼만 읽기/쓰기
        ▼
[Code v3, Schema v2]
        │ (5) Contract 마이그레이션 — 구 컬럼 drop / NOT NULL 강화
        ▼
[Code v3, Schema v3]
```

**해서는 안 되는 패턴 (전부 다운타임 / 깨지는 배포)**:

| 안티 | 왜 |
|---|---|
| `ADD COLUMN x NOT NULL` (기본값 없음) | _전 테이블 락_ + 기존 행 검증 |
| `ALTER COLUMN TYPE` (대형 변경) | 행 _재작성_ — 락 + 디스크 |
| `CREATE INDEX` (CONCURRENTLY 없이) | 테이블 _쓰기 락_ |
| `RENAME COLUMN` _그 자리에서_ | 구 코드 즉시 깨짐 |
| `DROP COLUMN` 배포 _직전_ | 구 코드 깨짐 |

**Postgres 만의 운영급 도구**:

| 옵션 | 효과 |
|---|---|
| `CREATE INDEX CONCURRENTLY` | 인덱스 생성 _락 없이_. Alembic `op.get_context().autocommit_block()` 안에서 |
| `ALTER TABLE ... ADD CONSTRAINT ... NOT VALID` + `VALIDATE CONSTRAINT` | 큰 테이블에 제약 추가를 _두 단계로_ 쪼개기 |
| `pg_repack` | dead tuple 정리 _락 없이_ |
| `lock_timeout` / `statement_timeout` | 마이그레이션이 _영원히 락_ 못 잡게 |
| `SET LOCAL maintenance_work_mem = ...` | VACUUM / CREATE INDEX 빠르게 |

## 비교 — 다국 도구

| 개념 | 대응 |
|---|---|
| Alembic | Flyway / Liquibase (Spring), TypeORM migrations, Knex.js, golang-migrate, sqlx-cli |
| testcontainers | 동일 라이브러리 — Java / Node / Go / .NET 다 있음 |
| Postgres jsonb | MongoDB document, MySQL JSON, Cassandra UDT |
| Postgres FTS | MySQL FULLTEXT, SQLite FTS5, Elasticsearch (운영급) |
| LISTEN/NOTIFY | Redis pub/sub, NATS, AWS SNS 가벼운 버전 |
| EXPLAIN ANALYZE | MySQL `EXPLAIN ANALYZE` (8.0+), MongoDB `explain("executionStats")` |

## 운영 추가 도구 (이 학습 범위 밖, 참고)

| 영역 | 도구 |
|---|---|
| 모니터링 | `pg_stat_statements`, `auto_explain`, `pg_stat_activity` |
| 풀 | PgBouncer (transaction pooling), Pgpool-II |
| HA | Patroni, Crunchy / Zalando Postgres Operator (K8s) |
| 백업 | `pgBackRest`, `barman`, WAL-G |
| 마이그레이션 가드 | Rails `strong_migrations` gem 같은 도구 (Python: `pg-osc`, `gh-ost` 는 MySQL) |
| Slow query | `pgbadger` 로그 분석, Datadog DBM, pganalyze |

## 안티패턴 모음

1. **`SELECT *`** — 모델 추가/제거 시 _브레이킹 변경_. 컬럼 명시.
2. **N+1 무시** — 로컬에서 빠르게 보이지만 운영 트래픽에서 폭발.
3. **lazy load 의존** — SQLAlchemy 2.0 async 가 _기본 비허용_ (좋은 디자인). 명시적 eager.
4. **인덱스 무한 추가** — 쓰기 ↑ / 디스크 ↑. _쓰는 인덱스만_ (`pg_stat_user_indexes` 로 unused 검출).
5. **마이그레이션이 길게 락 잡음** — `lock_timeout = 5s` 로 안전 가드.
6. **EXPLAIN 만 보고 ANALYZE 안 봄** — 추정 vs 실측 다름. ANALYZE 가 진실.
7. **transaction 안에서 외부 API 호출** — DB 락 점유 + 외부 지연 → 풀 고갈.
8. **autovacuum 끔** — bloat 폭발. 끄고 수동 VACUUM 은 _전문가만_.
9. **운영에서 ORM `lazy='joined'`** — 모든 쿼리에 JOIN. 명시적 eager 가 깨끗.
10. **운영 DB 에 직접 마이그레이션** — 항상 _스테이징 → 카나리 → 운영_.

## 직접 해보기 TODO

- [ ] `make migrate` 후 psql 로 `\d+ deep_posts` — 인덱스 종류 _전부_ 확인
- [ ] `EXPLAIN ANALYZE SELECT * FROM deep_posts WHERE tags @> '{"category": "tech"}'` — Bitmap Index Scan 채택되도록 시드 양 늘리기 (백만 행)
- [ ] `pg_stat_statements` 켜고 가장 느린 쿼리 5개 추출
- [ ] `ts_rank_cd` 와 `ts_rank` 결과 비교 — 단어 근접도 가중 차이
- [ ] `pg_trgm` 확장 + `gin_trgm_ops` — `LIKE '%foo%'` 도 인덱스 활용
- [ ] LISTEN/NOTIFY 로 _다른_ FastAPI 인스턴스의 캐시 무효화 (11 + A6)
- [ ] Expand-Contract 의 _Phase 4 (switch read)_ 까지 코드로 시뮬레이션
- [ ] `pg_repack` 로 bloat 정리 (dev container 에 설치 후)

## 다음 단계

**A7 — 캐시·메시지 큐 심화**. 11 의 cache-aside 를 _stampede 방지_ + Redis cluster + Saga / CQRS / Event Sourcing 으로 한 단계 더.
