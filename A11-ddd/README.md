# A11 — DDD / 헥사고날 아키텍처 (Ports & Adapters)

15 의 tender 를 _전술적 DDD_ + _Ports & Adapters_ 로 정련. _도메인이 인프라를 모르는_ 구조.

## 학습 목표

- **Value Object** — 불변, 값으로 동일성, 자가 검증 (Money / Quantity / SKU)
- **Aggregate** — 불변식 보호 경계 (Order, 상태 머신, OrderLine 합산)
- **Domain Event** — 과거형 이름, 영속 후 publish (OrderPlaced / OrderCancelled)
- **Domain Service** — Aggregate 에 안 맞는 도메인 로직 (DiscountPolicy)
- **Ports** (Protocol) — 도메인이 _필요한 것_ 만 선언 (Repository / Notifier / UoW)
- **Adapters** — Port 구현 (인메모리 / SQLAlchemy / Kafka …)
- **Use Case** (Application Service) — 얇은 layer, 트랜잭션 경계
- **Composition Root** — 모든 와이어링이 모이는 한 곳

## 디렉토리 (4계층)

```
A11-ddd/
├── pyproject.toml
├── Makefile
├── README.md
├── src/tenderdomain/
│   ├── domain/                ← 순수 도메인 (외부 의존성 X)
│   │   ├── exceptions.py        DomainError / InvariantViolation / ...
│   │   ├── value_objects.py     Money / Quantity / SKU / OrderId / UserId
│   │   ├── events.py            OrderPlaced / OrderCancelled (과거형)
│   │   ├── order.py             Order Aggregate (Root) + OrderLine + OrderStatus
│   │   └── services.py          DiscountPolicy (Domain Service)
│   │
│   ├── ports/                 ← Protocol 인터페이스 (도메인이 선언, 어댑터가 구현)
│   │   ├── repositories.py      OrderRepository / UserRepository
│   │   ├── notifier.py          Notifier
│   │   └── uow.py               UnitOfWork
│   │
│   ├── application/           ← Use Case (얇은 코디네이션)
│   │   ├── place_order.py
│   │   ├── cancel_order.py
│   │   └── get_order.py
│   │
│   └── adapters/              ← 인프라 구현
│       ├── inmemory.py          InMemoryOrderRepo / Notifier / UoW (테스트/dev)
│       └── api/
│           ├── router.py        FastAPI 라우터 (DTO 변환 + use case 호출)
│           └── main.py          Composition Root + lifespan DI
│
└── tests/
    ├── test_value_objects.py    VO 자가 검증 (잘못된 값은 _존재 X_)
    ├── test_order_aggregate.py  Aggregate 행동 (순수, 인프라 X)
    ├── test_use_cases.py        도메인+어댑터 통합 (인메모리)
    └── test_api.py              FastAPI e2e
```

## 의존성 방향 (한 방향만)

```
   ┌─────────────────────────────────────┐
   │   Adapters (FastAPI, SQLAlchemy)    │
   └────────────────────┬────────────────┘
                        │ implements
                        ▼
   ┌─────────────────────────────────────┐
   │   Ports (Protocol)                  │
   └────────────────────┬────────────────┘
                        │ used by
                        ▼
   ┌─────────────────────────────────────┐
   │   Application (Use Case)            │
   └────────────────────┬────────────────┘
                        │ uses
                        ▼
   ┌─────────────────────────────────────┐
   │   Domain (Aggregate / VO / Event)   │
   └─────────────────────────────────────┘
```

**규칙**: 화살표는 _한 방향_. 도메인은 어댑터 _절대_ 모름. 시도하면 _import 순환_ 발생.

## Value Object — 불변 + 자가 검증

```python
@dataclass(frozen=True)
class Money:
    amount: int      # 부동소수점 _절대 X_ (KRW 원 단위 정수)
    currency: str    # ISO 4217

    def __post_init__(self) -> None:
        if self.amount < 0:
            raise InvariantViolation(...)

    def add(self, other: Money) -> Money:
        if self.currency != other.currency:
            raise InvariantViolation(...)
        return Money(self.amount + other.amount, self.currency)
```

**핵심**:
- _잘못된 VO 는 존재 X_ → 코드 어디서든 `Money` 면 _유효_ 가정 가능
- 부동소수점 금액 X (`0.1 + 0.2 != 0.3` 함정)
- 변경 메서드는 _새 인스턴스_ 반환

비교: Java `record`, Kotlin `data class`, C# `readonly struct`.

## Aggregate — 불변식 보호 경계

```python
@classmethod
def place(cls, *, order_id, user_id, lines) -> Order:
    if not lines:
        raise InvariantViolation("order must have at least 1 line")
    merged = cls._merge_same_sku(lines)
    order = cls(...)
    order.events.append(OrderPlaced.now(...))   # ← 도메인 이벤트
    return order

def cancel(self, reason: str) -> None:
    if self.status in (SHIPPED, COMPLETED):
        raise IllegalStateTransition("must refund instead")
    self.status = CANCELLED
    self.events.append(OrderCancelled.now(...))
```

**규칙**:
- Aggregate Root 만 외부에서 접근 — 내부 OrderLine 직접 수정 X
- 한 트랜잭션 = 한 Aggregate (보통)
- 외부 참조는 _ID 로_: `Order` 가 `User` 객체 X, `UserId` (VO)
- _Application Service_ 가 여러 Aggregate 코디네이션

## Domain Event 패턴

```
# 1. Aggregate 가 자기 변경 + 이벤트 _기록_
order.cancel("reason")
# order.events == [OrderCancelled(...)]

# 2. UoW commit _후_ Notifier publish
async with uow:
    order.cancel("reason")
    await uow.orders.save(order)
    events = order.pull_events()
# commit 성공 → 여기 도달
for event in events:
    await notifier.publish(event)
```

**왜 commit _후_ publish?**
- commit 실패 시 이벤트 _발행하면 안 됨_ ── 시스템 inconsistency
- 운영급은 **Outbox 패턴** (13 단계) — 이벤트도 같은 트랜잭션에 _영속화_, 별도 워커가 발행

## Ports & Adapters (헥사고날)

```python
# ports/repositories.py — 도메인이 _선언_
class OrderRepository(Protocol):
    async def add(self, order: Order) -> None: ...
    async def get(self, order_id: OrderId) -> Order | None: ...

# adapters/inmemory.py — 어댑터가 _구현_
class InMemoryOrderRepository:
    async def add(self, order: Order) -> None: ...

# adapters/sqla.py — 같은 Protocol 의 _다른_ 구현 (운영용)
class SQLAlchemyOrderRepository:
    def __init__(self, session: AsyncSession): ...
    async def add(self, order: Order) -> None: ...
```

도메인은 _어떤 어댑터_ 가 사용되는지 모름 → **테스트는 인메모리로**, 운영은 SQLAlchemy.

## Use Case (Application Service)

```python
class PlaceOrderUseCase:
    uow: UnitOfWork
    notifier: Notifier

    async def __call__(self, input: PlaceOrderInput) -> PlaceOrderOutput:
        async with self.uow:                          # ← 트랜잭션 시작
            if not await self.uow.users.exists(...):  # ← 검증
                raise UserNotFound(...)
            order = Order.place(...)                  # ← 도메인 호출
            await self.uow.orders.add(order)
            events = order.pull_events()
        # commit 후
        for event in events:
            await self.notifier.publish(event)
        return PlaceOrderOutput(...)                  # ← DTO 반환
```

**규칙** (얇은 layer):
- 비즈니스 _법칙_ X — 도메인에
- 코디네이션 + 트랜잭션 + DTO 변환만
- 테스트 가능 (인메모리 어댑터 주입)

## Composition Root

```python
# adapters/api/main.py — _이 한 곳에서만_ 구체 어댑터 선택
async def lifespan(app):
    user_repo = InMemoryUserRepository()  # ← 운영은 SQLAlchemyUserRepository
    order_repo = InMemoryOrderRepository()
    notifier = CollectingNotifier()        # ← 운영은 KafkaNotifier
    uow = InMemoryUnitOfWork(orders=order_repo, users=user_repo)

    app.state.place_order_uc = PlaceOrderUseCase(uow=uow, notifier=notifier)
    ...
```

다른 어댑터 (CLI / GraphQL / arq worker) 도 _같은 use case_ 재사용 → 테스트 가능 + 인터페이스 다양화.

## 다국 비교

| 개념 | Spring/Java DDD | NestJS | Go (Clean Arch) |
|---|---|---|---|
| Aggregate | `@AggregateRoot` (Axon) | DDD 라이브러리 | struct + 메서드 |
| VO | `record` | class + readonly | struct |
| Repository Port | interface | interface (token) | interface |
| Use Case | `@Service` | `@Injectable` Service | struct + Execute() |
| Composition | Spring Context | Module | main.go wire-up |
| Domain Event | `ApplicationEventPublisher` | EventEmitter | channel 또는 outbox |

## 안티패턴

1. **도메인이 인프라 import** — `from sqlalchemy import ...` 가 domain/ 에 등장 = 설계 깨짐
2. **Aggregate 끼리 직접 호출** — Order 가 User 객체 메서드 호출. _Application Service_ 가 코디.
3. **DTO 가 도메인 타입 노출** — Pydantic 응답에 `Money` 그대로. _직렬화_ 시점에 `int` + `str` 분리.
4. **트랜잭션이 여러 Aggregate** — 락 경합 + consistency 압박. 한 트랜잭션 = 한 Aggregate.
5. **이벤트를 commit _전에_ publish** — 트랜잭션 실패 시 이벤트 _이미 나감_. Outbox 패턴 (13).
6. **VO 가 setter 가짐** — 불변 깨짐. `@dataclass(frozen=True)` + 새 인스턴스 반환.
7. **Aggregate 에 ORM 매핑 어노테이션** — 도메인이 SQLAlchemy 의존. _분리_ (mapper / data class).
8. **Use Case 가 비즈니스 로직 보유** — Anemic Domain Model 안티패턴. 로직은 _도메인_ 에.
9. **Repository 가 _도메인 객체 외_ 반환** — `dict` / `Row` 노출 X. _Aggregate / VO_ 만.
10. **모든 곳에 DDD 적용** — 단순 CRUD 는 _과한 복잡도_. 도메인 _복잡한 부분만_ 전술 DDD.

## 운영급 추가 도구 (참고)

| 영역 | 도구 |
|---|---|
| Java DDD | Axon Framework, Spring Modulith |
| .NET | MediatR + Domain layer + EF Core |
| Python | _직접_ (본 모듈), `cosmic-python` 책 패턴 |
| 매핑 | SQLAlchemy `imperative mapping` (데이터 클래스 분리) |
| Event | Kafka + Outbox (13), EventStoreDB (A7) |
| Workflow | Temporal (Saga 영속, A7) |

## 직접 해보기 TODO

- [ ] `SQLAlchemyOrderRepository` 어댑터 추가 — 같은 Protocol, _도메인 변경 X_
- [ ] `KafkaNotifier` 어댑터 — 13 단계 outbox 와 결합
- [ ] `DiscountPolicy` 를 PlaceOrderUseCase 에 주입 → 할인 적용된 total 반환
- [ ] CLI 어댑터 추가 — `python -m tenderdomain.adapters.cli place ...` 같은 use case 재사용
- [ ] Aggregate 를 _이벤트 시퀀스_ 로 재구성 (Event Sourcing — A7 의 BankAccount 패턴)
- [ ] Bounded Context 분리 — `orders` / `payments` / `shipping` 각자 도메인
- [ ] **Anti-Corruption Layer** — 외부 API 의 모델을 도메인 VO 로 _번역_

## 다음 단계

**A12 — 관측가능성 운영급**. 12 의 OTel/Prometheus 를 _운영_ 으로 — Sentry, Loki/Grafana, Jaeger/Tempo, SLO/SLI 알람.
