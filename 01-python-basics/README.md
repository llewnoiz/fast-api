# 01 — Python 기본 + uv

다른 언어를 쓰던 사람이 Python 의 _감각_ 을 잡는 단계.

## 학습 목표

- Python 의 변수/타입/제어 흐름/함수/클래스 핵심 문법을 직접 짜본다
- `typing` 으로 타입 힌트를 다는 습관을 들인다 (FastAPI/Pydantic 의 기반)
- 모듈/패키지 import 메커니즘을 이해한다
- **`uv`** 로 가상환경 + 의존성 관리하는 흐름에 익숙해진다

## 실행

```bash
# 루트에서 한 번 (모든 단계 의존성 일괄 설치)
cd ..
uv sync

# 이 단계 디렉토리로 들어와서
cd 01-python-basics
make run        # 모든 데모 순차 실행
make demo FILE=src/s05_classes.py    # 하나만 실행
make test       # pytest
make lint       # ruff
make typecheck  # mypy
```

## 핵심 개념 요약

### 1) 들여쓰기가 곧 블록

`{}` 가 없다. 들여쓰기 4칸이 곧 블록의 경계 — 컴파일 에러가 아니라 _문법_ 이다.

### 2) 동적 타입 + 선택적 타입 힌트

런타임은 동적이지만, **타입 힌트는 거의 필수로 작성**한다. FastAPI/Pydantic 이 런타임에 그 힌트로 검증·문서화하기 때문. Java 의 정적 타입과 TypeScript 의 점진적 타입의 중간 감각.

```python
def add(a: int, b: int) -> int:
    return a + b
```

### 3) 모든 것이 객체

`int`, 함수, 클래스, 모듈 자체도 모두 _객체_. 함수도 변수에 넣고 인자로 넘긴다 (Go 의 함수값과 비슷).

### 4) 모듈 = 파일, 패키지 = 폴더

`import foo.bar.baz` 는 `foo/bar/baz.py` 를 찾는다. 패키지로 인정받으려면 `__init__.py` (비어 있어도 됨) 또는 PEP 420 namespace package.

### 5) 진입점 관용구 `if __name__ == "__main__"`

스크립트로 직접 실행될 때만 동작하게 하는 가드. Java `public static void main` 자리.

## Java / Go 와의 비교

| 개념 | Python | Java | Go |
|---|---|---|---|
| 변수 선언 | `x = 1` (타입 추론) / `x: int = 1` | `int x = 1;` | `x := 1` |
| 상수 | 관용 — 대문자 (`MAX = 10`), 강제 X | `final int MAX = 10;` | `const MAX = 10` |
| 컬렉션 | `list / dict / set / tuple` (내장) | `ArrayList / HashMap` | `slice / map` |
| 클래스 | `class Foo:` | `class Foo {}` | 구조체 + 메서드 |
| 데이터 객체 | `@dataclass` | record / Lombok | struct |
| Null | `None` | `null` | `nil` |
| 가상환경 | `uv` / venv | (필요 없음, 클래스패스) | (필요 없음, GOPATH/모듈) |
| 빌드 파일 | `pyproject.toml` | `build.gradle` | `go.mod` |
| 코드 스타일 | PEP 8 + ruff | Spotless / Checkstyle | gofmt |

## 컴프리헨션 빠른 가이드

다른 언어에는 _직접 대응이 없는_ 문법이라 처음엔 낯섭니다. 한 줄로 "기존 컬렉션을 변환·필터링해서 새 컬렉션을 만든다" 는 _레시피_.

### 형태

```
[ 표현식    for 변수 in 컬렉션    if 조건 ]
└─ map ─┘  └──── for ─────┘   └filter┘
```

괄호 종류로 결과 타입이 결정됩니다.

| 괄호 | 결과 | 예시 |
|---|---|---|
| `[ ... ]` | list | `[x*2 for x in xs]` |
| `{ ... : ... }` | dict | `{w: len(w) for w in words}` |
| `{ ... }` | set | `{len(w) for w in words}` |
| `( ... )` | generator (lazy) | `(x*2 for x in xs)` |

### Java Stream 과 1:1 매핑

| 의도 | Python | Java |
|---|---|---|
| map | `[x*2 for x in xs]` | `xs.stream().map(x -> x*2).toList()` |
| filter | `[x for x in xs if x > 0]` | `xs.stream().filter(x -> x > 0).toList()` |
| filter + map | `[x*2 for x in xs if x > 0]` | `xs.stream().filter(...).map(...).toList()` |
| flatMap | `[v for row in m for v in row]` | `m.stream().flatMap(List::stream).toList()` |
| toMap | `{k: f(k) for k in ks}` | `ks.stream().collect(toMap(k->k, k->f(k)))` |
| toSet | `{f(x) for x in xs}` | `xs.stream().map(f).collect(toSet())` |
| lazy | `(x*2 for x in xs)` | intermediate ops 만 (terminal 호출 X) |

### `if` 의 두 가지 위치 — 헷갈리는 핵심 포인트

```python
# (1) 뒤쪽 if — filter (조건이 거짓이면 건너뜀)
[x for x in xs if x > 0]

# (2) 앞쪽 if/else — 표현식 자리의 삼항 (모든 원소가 결과에 들어감)
["+" if x > 0 else "-" for x in xs]
```

뒤쪽 `if` 는 _filter_, 앞쪽 `if/else` 는 _map 안의 분기_. 헷갈리면 "if 만 있으면 뒤", "if/else 면 앞" 으로 기억.

### 언제 _쓰면 안 되는지_ (안티패턴)

1. **부수효과만 원할 때** — `[print(x) for x in xs]` 는 결과 list 가 버려짐. `for x in xs: print(x)` 가 정답.
2. **중첩 3겹 이상** — `[f(x,y,z) for x in xs for y in ys for z in zs]` 는 일반 for 루프가 더 읽힘.
3. **조건이 복잡** — 함수로 빼서 `[label(x) for x in xs]` 형태로.
4. **흐름 제어 필요** — `continue / break / try-except` 가 필요하면 컴프리헨션 못 씀.

가이드: **한 화면(80자) 에 한눈에 들어오면 OK**, 그 이상이면 일반 for 루프를 의심.

샘플 코드는 `src/s02_collections.py` 의 `STEP 1 ~ STEP 7` 함수 참고. `make demo FILE=src/s02_collections.py` 로 실행.

## 구조 분해 & 결합 (Node ↔ Python)

JS/TS 의 destructuring/spread 와 _부분적으로_ 대응되지만 차이도 큽니다. 가장 큰 함정은 **할당문 dict destructuring 이 Python 에 없다** 는 것.

### Node ↔ Python 대조

| 의도 | Node/JS | Python |
|---|---|---|
| 시퀀스 분해 | `const [a, b] = arr` | `a, b = arr` |
| 첫 + 나머지 | `const [first, ...rest] = arr` | `first, *rest = arr` |
| 가운데에 rest | (불가) | `first, *middle, last = xs` ✨ |
| swap | `[a, b] = [b, a]` | `a, b = b, a` (괄호 없이도 OK) |
| **객체/dict 분해** | `const {name, age} = user` | **직접 대응 없음** — 대안 4가지 ↓ |
| 시퀀스 호출 펼치기 | `f(...args)` | `f(*args)` |
| 객체→kwargs 호출 | (불가) | `f(**kwargs)` ✨ |
| list 결합 | `[...a, ...b]` | `[*a, *b]` |
| dict 병합 | `{...a, ...b}` | `{**a, **b}` 또는 `a \| b` (3.9+) |
| 키 충돌 시 | _뒤가 이김_ | _뒤가 이김_ (동일) |

`✨` 는 Python 에만 있는 기능.

### `*` 의 위치별 의미 — 헷갈리는 핵심

| 위치 | 역할 | 예시 |
|---|---|---|
| 좌변 | 나머지 _수집_ (collect) | `first, *rest = xs` |
| 우변 (호출) | 시퀀스 _펼치기_ (spread) | `f(*xs)` |
| 우변 (리터럴) | 컬렉션 안에서 _펼치기_ | `[*a, *b]` |
| 함수 정의 | 가변 위치 인자 (collect) | `def f(*args):` |
| `**` 자리 | dict 버전 (kwargs / 병합) | `f(**d)`, `{**a, **b}` |

좌변=수집, 우변=펼치기로 기억하면 일관됩니다.

### Node `const {name, age} = user` 의 4가지 대안

```python
# 1. index 직접 접근 — 가장 단순, 보일러플레이트 있음
name, age = user["name"], user["age"]

# 2. itemgetter — 키 개수 많을 때 깔끔
from operator import itemgetter
name, age = itemgetter("name", "age")(user)

# 3. match (3.10+) — 구조 분해 + 검증을 한 번에
match user:
    case {"name": name, "age": age}: ...

# 4. dataclass / Pydantic — 실무 표준 (FastAPI 친화적)
@dataclass
class User: name: str; age: int
u = User(**user)         # ← STEP 4 의 dict→kwargs 응용
u.name, u.age
```

**실무 권장**: API 경계 _안쪽_ 이면 4번(Pydantic), 외부 데이터 _일회성 추출_ 이면 1번. 2번은 좌표 같은 의미 같은 키 묶음, 3번은 구조 검증이 동시에 필요한 자리.

### 안티패턴

1. **좌변 `*` 는 한 개만** — `*a, *b = xs` 는 SyntaxError.
2. **얕은 병합 함정** — `{**a, **b}` 는 nested dict 깊은 병합 안 함. 03단계 `jsonpath-ng` / 직접 재귀로.
3. **JS 객체 spread ≠ Python kwargs 호출** — JS `{...obj}` 는 객체 합치기. Python `f(**d)` 는 함수 호출 시 키워드 펼치기 (별개의 일).
4. **`+` vs spread** — `[1,2] + [3,4]` 는 list 한정. spread `[*gen, *xs]` 는 generator 도 펼침 (더 범용).

샘플 코드는 `src/s07_unpacking.py` 의 `STEP 1 ~ STEP 7`. `make demo FILE=src/s07_unpacking.py` 로 실행.

## 안티패턴 (다른 언어에서 넘어온 사람이 자주 함정)

1. **mutable default argument** — `def f(x=[]):` 는 _공유_ 된다. 대신 `def f(x: list | None = None): x = x or []`.
2. **`==` vs `is`** — 값 비교는 `==`, 동일 객체 비교는 `is`. `None` 검사는 `is None`.
3. **얕은 복사 함정** — `b = a` 는 참조 복사. `import copy; b = copy.deepcopy(a)`.
4. **타입 힌트만 달고 끝** — 런타임 검증은 안 됨. 검증은 Pydantic 단계(03)에서.
5. **`for i in range(len(xs))`** — 비파이썬적. `for x in xs:` 또는 `for i, x in enumerate(xs):`.

## uv 핵심 명령

```bash
uv init <name>             # 새 프로젝트 (pyproject.toml + .venv)
uv add <pkg>               # 의존성 추가 (lock + 설치)
uv add --group dev <pkg>   # 개발 의존성
uv remove <pkg>            # 제거
uv sync                    # lock 기반으로 가상환경 동기화
uv lock                    # lock 파일만 갱신
uv run <cmd>               # .venv 안에서 명령 실행 (가상환경 활성화 불필요)
uv tree                    # 의존성 트리
uv tool install <pkg>      # 전역 CLI 도구 설치 (pipx 대체)
```

**패키지 검색**: PyPI 웹(<https://pypi.org>) 또는 `uv add --dry-run <pkg>` 로 버전 후보 확인.
대안 평가 기준: GitHub stars, 최근 커밋 / 릴리스, 다운로드 수(<https://pypistats.org>), 의존성 그래프(`uv tree`).

## 직접 해보기 TODO

- [ ] `src/s05_classes.py` 의 `User` 에 `age` 필드 추가하고 `__post_init__` 으로 음수 검증
- [ ] `src/s04_functions.py` 의 `retry` 데코레이터에 _기본 지연시간(backoff)_ 인자 추가
- [ ] `src/s02_collections.py` 의 list comprehension 예시를 generator expression 으로 바꿔보기 (메모리 차이 체감)
- [ ] `tests/test_basics.py` 에 본인이 추가한 코드를 검증하는 테스트 케이스 1개 이상 작성
- [ ] `uv add httpx` 로 의존성 추가 후 `uv tree` 로 트리 확인 → `uv remove httpx`

> 💡 **파일명 규칙**: Python 모듈명은 _숫자로 시작할 수 없어서_ `s01_`, `s02_` 처럼 `s` (step) 접두사를 붙였습니다. `01_types.py` 같은 이름은 스크립트 실행은 가능하지만 `import` 가 안 됩니다.
