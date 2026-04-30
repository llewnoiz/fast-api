# A13 — Python 고급 typing & 메타프로그래밍

01 의 기본 typing 을 _운영급_ 으로 확장. 라이브러리 작성 / 프레임워크 설계 / 타입 안전 DI 에 필수.

## 학습 목표 — 10가지 모듈

| 모듈 | 주제 | 핵심 |
|---|---|---|
| t01 | **Generics** | `TypeVar`, PEP 695 `class Box[T]`, bounds, constraints |
| t02 | **Protocol** | 구조적 typing, `runtime_checkable`, Generic Protocol |
| t03 | **Literal / NewType / TypedDict / Final** | 타입 정밀화 |
| t04 | **@overload / ParamSpec / TypeVarTuple** | 고급 함수 시그니처 |
| t05 | **Descriptor** | `__get__/__set__`, `__set_name__`, lazy property |
| t06 | **Metaclass / `__init_subclass__`** | 99% 안 씀 — 대안이 더 좋음 |
| t07 | **Generator** | `yield from`, `send`, `throw`, async generator |
| t08 | **Context Manager** | `__enter__/__exit__`, `@contextmanager`, async |
| t09 | **functools 심화** | `singledispatch`, `cache`, `partial`, `wraps`, `reduce` |
| t10 | **TypeGuard** | 커스텀 narrowing 함수 |

## 디렉토리

```
A13-typing-deep/
├── pyproject.toml
├── Makefile
├── README.md
├── src/typingdeep/
│   ├── __init__.py
│   ├── t01_generics.py
│   ├── t02_protocols.py
│   ├── t03_literal_newtype.py
│   ├── t04_overload.py
│   ├── t05_descriptors.py
│   ├── t06_metaclass.py
│   ├── t07_generators.py
│   ├── t08_context_managers.py
│   ├── t09_functools_advanced.py
│   └── t10_typeguard.py
└── tests/  ← 모듈별 1:1 매핑, 56 tests
```

## 핵심 메시지 — 가장 중요한 검증은 **mypy**

이 모듈은 _런타임 동작_ 보다 _타입 시스템 정확성_ 이 학습 목표.
`make typecheck` 가 깨끗하면 학습 _완료_. `make test` 는 _런타임 보강_.

## PEP 695 — Python 3.12+ 새 문법

```python
# 옛 (3.5+)
T = TypeVar("T")
class Box(Generic[T]):
    def __init__(self, value: T) -> None: ...

# PEP 695 (3.12+) — 더 간결
class Box[T]:
    def __init__(self, value: T) -> None: ...

# 함수도
def first[T](items: list[T]) -> T | None: ...

# bound + constraints
def maximum[T: Comparable](items: list[T]) -> T: ...   # bound
def add_numeric[N: (int, float)](a: N, b: N) -> N: ... # constraints

# ParamSpec / TypeVarTuple
def timed[**P, R](fn: Callable[P, R]) -> Callable[P, R]: ...
def first_and_rest[*Ts](items: tuple[int, *Ts]) -> tuple[int, tuple[*Ts]]: ...
```

비교: TypeScript `class Box<T>`, Java `class Box<T>`, Go `type Box[T any] struct`, C++ `template<typename T>`.

## Protocol — 구조적 타이핑

```python
class Greeter(Protocol):
    def greet(self) -> str: ...

class English:                    # Protocol 상속 X
    def greet(self) -> str: ...   # 구조만 맞으면 OK

def greet_all(gs: Iterable[Greeter]) -> list[str]: ...

# `English()` 는 Greeter 가 _아니지만_ greet_all 에 _전달 가능_
```

**왜?** Java 의 명시적 implements 와 다르게 _이미 있는 클래스_ 도 Protocol 만족 가능.

**`@runtime_checkable`**: `isinstance(x, MyProto)` 가능.

## Literal / NewType / TypedDict

```python
# Literal — 좁은 타입
Color = Literal["red", "green", "blue"]
def paint(color: Color) -> str: ...   # paint("yellow") → type error

# NewType — int 와 _구조적 동일_, 타입 체커는 _구분_
UserId = NewType("UserId", int)
OrderId = NewType("OrderId", int)
get_user(OrderId(1))   # type error — int 끼리 섞임 방지

# TypedDict — dict 의 키별 타입 (외부 JSON 친화)
class UserDict(TypedDict):
    id: int
    name: str
    is_admin: NotRequired[bool]   # 옵셔널
```

**Pydantic vs TypedDict**:
- TypedDict: _런타임 검증 X_, 타입 체커만. _이미 dict 인_ 외부 데이터.
- Pydantic: _런타임 검증_ + 직렬화. _신뢰 안 되는_ 입력.

## @overload — 입력별 출력 타입

```python
@overload
def split(data: str) -> list[str]: ...
@overload
def split(data: bytes) -> list[bytes]: ...
def split(data: str | bytes) -> list[str] | list[bytes]: ...

x = split("a,b,c")   # x: list[str]
y = split(b"a,b,c")  # y: list[bytes]
```

## ParamSpec — 데코레이터 시그니처 보존

```python
def timed[**P, R](fn: Callable[P, R]) -> Callable[P, R]:
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        return fn(*args, **kwargs)
    return wrapper

@timed
def greet(name: str, *, loud: bool = False) -> str: ...

greet("alice")            # OK — 시그니처 보존
greet("alice", loud=True) # OK
greet(123)                # type error
```

## Descriptor

```python
class Positive:
    def __set_name__(self, owner, name):
        self._name = f"_{name}"
    def __get__(self, obj, objtype=None):
        return getattr(obj, self._name, 0) if obj else self
    def __set__(self, obj, value):
        if value < 0:
            raise ValueError("must be positive")
        setattr(obj, self._name, value)

class Account:
    balance = Positive()  # 클래스 _속성_ 으로

acc = Account()
acc.balance = 100   # OK
acc.balance = -1    # ValueError
```

`@property` 도 _내부적으로_ descriptor. 모든 _bound method_ 도 descriptor (self 자동 바인딩).

## Metaclass — 99% 안 씀

```python
# 90% 의 경우 — __init_subclass__ 로 충분
class Plugin:
    registry = []
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        Plugin.registry.append(cls)

class HelloPlugin(Plugin): ...   # 자동 등록
class WorldPlugin(Plugin): ...   # 자동 등록
```

**진짜 metaclass 가 필요한 경우**:
- 프레임워크 내부 (SQLAlchemy `DeclarativeBase`, Django `Model`)
- DSL — 클래스 정의 _자체_ 가 도메인

**대안 우선순위**:
1. 데코레이터 → 충분하면 그것
2. `__init_subclass__` → 자식 등록 / 검증
3. mixin / 상속 → 행동 추가
4. **metaclass** → 위 셋이 _다 안 되는_ 경우만

## Generator — `yield` 의 깊이

```python
# 1. 단순
def count(n): yield from range(n)

# 2. 양방향 (send)
def echo():
    while True:
        received = yield "give me text"   # ← gen.send(value) 가 received 에

# 3. async
async def stream(n):
    async for ... :
        yield item   # async for 로 소비
```

용도: 메모리 효율 (무한 시퀀스), 협력형 프로토콜 (asyncio 의 기반), 변환 파이프라인.

## Context Manager — 자원 관리

```python
class Timer:
    def __enter__(self): ...
    def __exit__(self, exc_type, exc, tb):
        # exc 가 None 아니면 _예외 발생_, return True 로 _삼킬 수 있음_
        ...

# 또는 데코레이터로 짧게
@contextmanager
def timer():
    start = ...
    try:
        yield {"start": start}
    finally:
        ...   # 정상/예외 둘 다 잡음
```

비교: Java `try-with-resources`, C# `using`, Go `defer`, Rust RAII.

## functools 심화

| 도구 | 용도 |
|---|---|
| `@cache` / `@lru_cache` | 메모이제이션. 인자가 _해시 가능_ 해야 |
| `cached_property` | _인스턴스 단위_ 캐시 (인스턴스 죽으면 같이 죽음) |
| `@singledispatch` | 첫 인자 _타입 기반_ 분기 (Java 메서드 오버로딩) |
| `partial(fn, x=1)` | 부분 적용 (lambda 대안 — 더 빠름) |
| `@wraps` | 데코레이터에서 원함수 메타 보존 (`__name__`, `__doc__`) |
| `reduce` | 누적 연산. 단순 합산은 `sum()` 가 가독성 좋음 |

## TypeGuard — 커스텀 narrowing

```python
def is_int_list(x: object) -> TypeGuard[list[int]]:
    return isinstance(x, list) and all(isinstance(v, int) for v in x)

def sum_if_ints(x: object) -> int:
    if is_int_list(x):
        return sum(x)   # mypy: x: list[int] OK (narrowing)
    return 0
```

`TypeIs` (3.13+) — TypeGuard 의 개선판 (false 분기에서도 narrowing).

## 안티패턴

1. **`Any` 남발** — 타입 시스템 _포기_. `object` 또는 `Unknown` 가 더 안전.
2. **`# type: ignore` 무차별** — 진짜 버그 가림. 줄여 쓰기 + 코멘트.
3. **모든 곳에 Protocol** — 단순 함수 인자엔 _구체 타입_ 이 명확.
4. **metaclass 로 데코레이터 흉내** — 이해 어려움. 데코레이터 / `__init_subclass__` 우선.
5. **Generator 무한 루프 + 종료 안 함** — 메모리 누수. `take` / `islice` 로 한도.
6. **Context Manager 안 쓰고 직접 close** — 예외 시 누수. 항상 `with`.
7. **`@cache` 인스턴스 메서드** — self 가 키 → 인스턴스 영원히 산다. `cached_property` 사용.
8. **`@overload` 단일 시그니처** — 그냥 일반 함수. overload 는 _2개 이상_ 시그니처일 때.
9. **`Literal` 대신 `Enum`** — Enum 은 _런타임 객체_, Literal 은 _컴파일 타임_. 용도 다름.
10. **descriptor 를 _instance 속성_ 으로** — 작동 안 함. **클래스 속성** 만 동작.

## 직접 해보기 TODO

- [ ] `make typecheck` 가 _깨끗_ 한 상태에서 일부러 타입 오류 만들고 mypy 메시지 읽기
- [ ] PEP 695 `[**P, R]` 로 09 단계의 `@require_role` 데코레이터 _시그니처 보존_
- [ ] `Protocol` 로 11 의 RateLimiter / 13 의 KafkaPublisher 추상화
- [ ] `TypedDict` 로 외부 API 응답 타입 정의 (예: GitHub PR JSON)
- [ ] `@singledispatch` 로 errver 의 `_domain_exc_to_http` 매핑 재작성 (A11)
- [ ] 메타클래스로 _플러그인 자동 등록_ vs `__init_subclass__` 로 같은 효과 — 비교
- [ ] `cached_property` 로 A11 의 `Order.total()` 캐시 (Aggregate 저장 후 한 번만 계산)
- [ ] `TypeGuard` 로 GraphQL union type narrowing — Strawberry 와 결합

## 다음 단계

**A14 — 성능 / 프로파일링**. `py-spy` (sampling), `cProfile`, `line_profiler`, 메모리 (`memray`, `tracemalloc`), gunicorn vs uvicorn workers, async 성능 함정.
