# 10 — DB + 트랜잭션

09 의 인메모리 `_USERS` 가 _진짜 Postgres_ 로. SQLAlchemy 2.0 async + Alembic + Unit of Work + 트랜잭션 / savepoint.

## 학습 목표

- **SQLAlchemy 2.0** 새 스타일 — `Mapped[T]` + `mapped_column`
- **AsyncEngine + async_sessionmaker** — 앱 lifespan 동안 _하나_ 의 engine, _요청 단위_ session
- **Alembic** 마이그레이션 — async 앱과 _드라이버 분리_ (psycopg sync)
- **Unit of Work** — 트랜잭션 경계를 _서비스_ 에, 라우트는 깨끗
- **`async with session.begin_nested()`** — savepoint 부분 롤백
- **N+1 회피** — `selectinload(User.orders)`
- **testcontainers + Alembic 자동** — 테스트 시작 시 진짜 DB 띄우고 마이그레이션 적용

## 실행

```bash
cd .. && uv sync && cd 10-db-transaction

# 도커 db profile 띄우고 마이그레이션 후 서버
cd ../05-infra-compose && make up-db && cd ../10-db-transaction
make migrate                # alembic upgrade head
make run                    # uvicorn

# 새 마이그레이션 자동 생성 (모델 변경 후)
make migrate-autogen M="add column foo to users"
make migrate-down           # 한 단계 되돌리기

make all                    # ruff + mypy + pytest (testcontainers)
```

## 디렉토리

```
10-db-transaction/
├── pyproject.toml          # sqlalchemy[asyncio] / alembic / asyncpg / psycopg
├── alembic.ini
├── alembic/
│   ├── env.py              # async 모델 metadata 와 sync Alembic 의 다리
│   ├── script.py.mako
│   └── versions/2026_04_29_0001_initial.py
├── Makefile                # make migrate / migrate-autogen / run / test
├── README.md
├── src/dbapp/
│   ├── settings.py         # database_url (asyncpg)
│   ├── models.py           # User, Order — Mapped[T] + relationship
│   ├── database.py         # make_engine + make_sessionmaker
│   ├── repository.py       # UserRepository, OrderRepository (selectinload)
│   ├── uow.py              # UnitOfWork — async with 자동 commit/rollback
│   └── main.py             # FastAPI + Depends(get_uow)
└── tests/
    ├── conftest.py         # testcontainers Postgres + Alembic 자동 적용
    ├── test_repository.py
    ├── test_transaction.py # savepoint / 롤백 검증
    └── test_app.py
```

## 다국 언어 비교

| 개념 | 가장 가까운 비교 |
|---|---|
| **SQLAlchemy 2.0 `Mapped[T]`** | Spring Data JPA `@Entity` + `@Id`, NestJS TypeORM `@Entity`, Kotlin Exposed `IntIdTable` |
| **`mapped_column`** | JPA `@Column`, TypeORM `@Column` |
| **`relationship` + `selectinload`** | JPA `@OneToMany(fetch=EAGER)` / `JOIN FETCH`, TypeORM `relations` |
| **`AsyncSession`** | JPA `EntityManager`, TypeORM `EntityManager` |
| **`Alembic`** | **Flyway** (가장 가까움), Liquibase, TypeORM migrations |
| **Unit of Work** | Spring `@Transactional`, NestJS `QueryRunner.startTransaction()` |
| **`begin_nested` savepoint** | Spring `Propagation.NESTED`, JDBC Savepoint |
| **N+1 함정** | _모든_ ORM 의 공통 문제 |

## 핵심 개념

### 1) `Mapped[T]` + `mapped_column` — _타입 힌트가 진짜로_ 모델 정의

```python
class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    orders: Mapped[list[Order]] = relationship(back_populates="owner")
```

옛 1.x 스타일 (`Column(Integer, primary_key=True)`) 보다 _훨씬_ 짧고 mypy/Pyright 가 _쿼리 결과 타입_ 까지 추론. JPA `@Entity` 와 비슷하지만 _Python 타입 시스템 활용_ 이 핵심.

### 2) Engine 은 _하나_, Session 은 _짧게_

```python
# lifespan: 앱 시작 시 한 번
engine = create_async_engine(url)        # 커넥션 풀 내장
SessionLocal = async_sessionmaker(engine)

# 요청 단위
async with SessionLocal() as session:    # 짧은 수명
    ...
```

비교: Spring 의 `DataSource` (싱글톤) + `EntityManager` (요청). _Engine 을 매 요청마다 만드는 건 안티패턴_.

### 3) Alembic — 마이그레이션 _버전 관리_

```bash
alembic revision --autogenerate -m "add email column"   # 모델 변경 감지 → 마이그레이션 생성
alembic upgrade head                                     # 최신까지 적용
alembic downgrade -1                                     # 1단계 되돌리기
```

비교: Flyway (`V1__init.sql` 자동 적용), Liquibase (`changelog.xml`).

`env.py` 는 sync (psycopg) — Alembic 자체가 sync. 앱은 async (asyncpg). _같은 Postgres_ 를 가리키는 _두 URL_:

```
asyncpg:  postgresql+asyncpg://...    ← 앱 런타임
psycopg:  postgresql+psycopg://...    ← Alembic
```

### 4) Unit of Work — 트랜잭션 경계의 단순화

```python
# 라우트 한 줄로 _업무 단위_ 의 트랜잭션
async def create_order(uow: Annotated[UnitOfWork, Depends(get_uow)]):
    user = await uow.users.add(...)
    order = await uow.orders.add(user_id=user.id, ...)
    # 함수 종료 = with 블록 종료 = commit (예외 시 rollback)
```

라우트가 _커밋/롤백 안 함_. UoW 가 자동 처리. Spring `@Transactional` 한 줄과 같은 효과.

### 5) Savepoint — 부분 롤백

```python
async with UnitOfWork(sessionmaker) as uow:
    await uow.users.add(username="alice")        # 살아남을 데이터

    try:
        async with uow.session.begin_nested():    # SAVEPOINT
            await uow.users.add(username="alice") # UNIQUE 위반 → savepoint 만 롤백
    except IntegrityError:
        pass

    await uow.users.add(username="bob")          # 정상 진행
# 바깥 트랜잭션 commit — alice, bob 둘 다 살아남음
```

JPA `Propagation.NESTED` 자리. _부분 실패_ 가 허용되는 시나리오에 유용.

### 6) N+1 회피 — 명시적 fetch

```python
# ❌ N+1
users = await session.execute(select(User))
for u in users.scalars():
    print(u.orders)         # 매번 추가 쿼리 발생

# ✅ selectinload — 별도 IN 쿼리 _한 번_
stmt = select(User).options(selectinload(User.orders))
users = await session.execute(stmt)
for u in users.scalars():
    print(u.orders)         # 추가 쿼리 X
```

옵션:
- `selectinload`: 자식 IDs 로 IN 쿼리 (보통 권장)
- `joinedload`: LEFT OUTER JOIN (행 폭발 주의)
- `subqueryload`: 서브쿼리

JPA 의 `JOIN FETCH`, TypeORM 의 `relations: { orders: true }` 자리.

## 안티패턴

1. **라우트 핸들러에서 직접 `session.commit()` / `rollback()`** — UoW 또는 dependency yield 로 자동화. 휴먼 에러 방지.
2. **`session.close()` 누락** — 커넥션 풀 고갈. `async with` 또는 의존성 yield 로 자동.
3. **N+1** — 위 6) 참고. 로깅 / 모니터링으로 _눈에 띄게_.
4. **Engine 매 요청마다 생성** — 풀 못 씀. lifespan 동안 _하나_.
5. **autocommit 모드 + 임시 트랜잭션 혼용** — 일관성 깨짐. 명시적 `begin()` 권장.
6. **마이그레이션 _수동 SQL_ 만 사용** — 버전 관리 X. Alembic / Flyway 로 _자동 추적_.
7. **모델 변경 후 `--autogenerate` 결과 _리뷰 안 하고_ 적용** — autogenerate 가 _완벽 X_, 컬럼 rename 을 _drop+add_ 로 잘못 인식 등.
8. **Postgres CHECK 제약 / FK 없이 ORM 만 의존** — 직접 SQL 또는 외부 도구로 잘못된 데이터 들어가면 무방비.
9. **`expire_on_commit=True` 그대로** — 라우트 응답 직렬화 시 `session detached` 에러. `False` 로 두는 게 FastAPI 친화.

## 직접 해보기 TODO

- [ ] `User` 모델에 `email: Mapped[str] = mapped_column(unique=True)` 추가, `make migrate-autogen M="add email"` 으로 자동 생성된 마이그레이션 파일 _리뷰_
- [ ] `OrderStatus` Enum 컬럼 추가 (`PENDING / PAID / SHIPPED`) — Postgres ENUM 또는 String + CHECK
- [ ] `list_with_orders` 의 N+1 안티패턴 데모 — `list_lazy()` + 로깅 ON 으로 쿼리 수 비교
- [ ] `uow.session.execute(text("SELECT pg_sleep(0.1)"))` 로 트랜잭션 _길이_ 측정
- [ ] **격리 수준** — `engine.execution_options(isolation_level="SERIALIZABLE")` 와 `READ COMMITTED` 차이 실험
- [ ] 동시 두 트랜잭션이 같은 row UPDATE → SELECT FOR UPDATE / 낙관적 락 (`version_id_col`)
- [ ] Alembic 마이그레이션 두 개 만들고 `downgrade base` → `upgrade head` 사이클

## 다음 단계

**11 — Redis + Rate Limit**. 09 의 토큰 blocklist + 11 의 rate limit (slowapi 또는 fastapi-limiter), 캐시 cache-aside 패턴, 분산 락. 도커 compose `cache` profile 사용.
