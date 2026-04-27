"""07 — 구조 분해(unpacking) & 결합 (spread/merge).

Node/JS 의 destructuring 과 spread 가 _부분적으로_ 대응되지만 차이도 큰 영역.
특히 **할당문 dict destructuring 은 Python 에 _없다_** 는 점이 가장 중요한 차이.

기본 형태 요약:
    a, b = (1, 2)              # 시퀀스 unpacking — JS: const [a, b] = arr
    first, *rest = [1, 2, 3]   # star 로 나머지 수집 — JS: const [first, ...rest] = arr
    f(*args)                   # 호출 측: 시퀀스를 위치 인자로 펼침
    f(**kwargs)                # 호출 측: dict 를 키워드 인자로 펼침
    [*a, *b]                   # PEP 448: 리터럴 안에서 결합 — JS: [...a, ...b]
    {**a, **b}                 # dict 병합 — JS: {...a, ...b}
    d1 | d2                    # 3.9+ dict union — JS 직접 대응 없음
"""

from __future__ import annotations

from dataclasses import dataclass
from operator import itemgetter
from typing import Any

# ============================================================================
# STEP 1 — 시퀀스 unpacking 기본
# ============================================================================
#
# 좌변의 변수 개수와 우변의 길이가 _정확히_ 같아야 함.
# 안 맞으면 ValueError("not enough values" / "too many values").
#
# JS: const [a, b] = arr;
# ============================================================================

def split_pair[T](pair: tuple[T, T]) -> tuple[T, T]:
    """가장 단순한 형태 — 길이 2 의 시퀀스를 두 변수로."""
    a, b = pair
    return a, b


def parse_csv_row(row: str) -> tuple[str, str, str]:
    """CSV 한 줄 → 3개 필드. split() 결과(list) 도 unpacking 가능."""
    name, email, role = row.split(",")
    return name, email, role


# ============================================================================
# STEP 2 — star (`*`) 로 나머지 수집
# ============================================================================
#
# 좌변의 한 변수에 `*` 를 붙이면 그 자리에 _나머지 전부_ 가 list 로 들어감.
# `*` 는 좌변 통틀어 _최대 1개_.
#
# JS: const [first, ...rest] = arr;
# ============================================================================

def split_first_rest[T](xs: list[T]) -> tuple[T, list[T]]:
    """첫 원소 + 나머지 list."""
    first, *rest = xs
    return first, rest


def split_head_last[T](xs: list[T]) -> tuple[list[T], T]:
    """앞 전부 + 마지막 원소."""
    *head, last = xs
    return head, last


def split_first_middle_last[T](xs: list[T]) -> tuple[T, list[T], T]:
    """첫 / 중간 list / 마지막 — JS 에는 없는 _가운데에 ..._ 가 가능."""
    first, *middle, last = xs
    return first, middle, last


# ============================================================================
# STEP 3 — 중첩 unpacking + swap 관용구
# ============================================================================

def first_xy_and_label(data: tuple[tuple[float, float], str]) -> tuple[float, float, str]:
    """중첩 구조도 한 번에 분해.

        ((x, y), label) = data
    """
    (x, y), label = data
    return x, y, label


def swap[T, U](a: T, b: U) -> tuple[U, T]:
    """Python 의 우아한 swap — 임시변수 불필요.

    내부 동작: 우변이 먼저 tuple `(b, a)` 로 평가된 뒤 좌변에 unpacking.
    JS 도 같은 패턴(`[a, b] = [b, a]`) 가능하지만 Python 이 _괄호 없이_ 도 됨.
    """
    a, b = b, a  # type: ignore[assignment]  # 학습 의도상 의도적 타입 변경
    return a, b  # type: ignore[return-value]


# ============================================================================
# STEP 4 — 함수 호출 측 unpacking (caller-side)
# ============================================================================
#
# 함수 _정의_ 의 `*args / **kwargs` 는 04 에서 다뤘음 (수집).
# 여기는 _호출_ 측에서 펼치는 쪽 — 같은 별 기호인데 _반대 방향_.
#
# JS: f(...args) 는 시퀀스 펼치기. JS 의 객체 펼치기(`{...obj}`)는
#     "객체를 새 객체에 합치기" 이지 _kwargs 호출_ 이 아님 (Python 만의 기능).
# ============================================================================

def _greet(greeting: str, name: str, excited: bool = False) -> str:
    return f"{greeting}, {name}{'!' if excited else ''}"


def call_with_list_unpacking() -> str:
    """위치 인자로 펼치기 — 어떤 sequence(list/tuple) 든 동작.

    mypy 가 _길이까지_ 검증하려면 tuple 리터럴이 안전 (list 는 길이가 정적으로 무한정).
    런타임은 list 도 똑같이 OK.
    """
    args: tuple[str, str] = ("안녕", "Alice")
    return _greet(*args)  # ≡ _greet("안녕", "Alice")


def call_with_dict_unpacking() -> str:
    """dict 를 키워드 인자로 펼침. 키 이름이 매개변수명과 일치해야 함.

    실무 팁: 헤테로지니어스(타입 다른 값들이 섞인) dict 를 mypy 친화적으로
    검증하려면 `TypedDict` 사용. 학습 단계에선 type: ignore 로 충분.
    """
    kwargs = {"greeting": "hi", "name": "Bob", "excited": True}
    return _greet(**kwargs)  # type: ignore[arg-type]  # mypy: TypedDict 없으면 검증 한계


def call_mixed_unpacking() -> str:
    """위치+키워드 동시 — 위치가 먼저 와야 함."""
    args: tuple[str] = ("yo",)
    kwargs = {"name": "Carol", "excited": True}
    return _greet(*args, **kwargs)  # type: ignore[arg-type]


# ============================================================================
# STEP 5 — PEP 448: 리터럴 안에서 결합 (spread)
# ============================================================================
#
# JS 의 `[...a, ...b]` / `{...a, ...b}` 와 1:1 대응되는 Python 의 가장 흔한 결합 방식.
# `+` 보다 _범용_: list 에서만 되는 `+` 와 달리 generator/iterable 도 펼친다.
# ============================================================================

def concat_lists[T](a: list[T], b: list[T]) -> list[T]:
    """list 합치기 — `+` 와 결과 같지만 spread 가 더 일반적."""
    return [*a, *b]


def insert_in_middle[T](a: list[T], x: T, b: list[T]) -> list[T]:
    """리터럴 사이에 단일 원소 끼워넣기 — `+` 보다 깔끔."""
    return [*a, x, *b]


def union_sets(a: set[int], b: set[int]) -> set[int]:
    """set 합집합 — `a | b` 와 동일하지만 spread 도 가능."""
    return {*a, *b}


def merge_dicts(a: dict[str, Any], b: dict[str, Any]) -> dict[str, Any]:
    """dict 병합 — _뒤가 앞을 덮어씀_ (key 충돌 시 b 가 이김).

    JS `{...a, ...b}` 와 동일 동작.
    얕은 복사 (nested dict 는 그대로 공유) — 안티패턴 #4 참고.
    """
    return {**a, **b}


# ============================================================================
# STEP 6 — dict union 연산자 (Python 3.9+)
# ============================================================================
#
# `{**a, **b}` 와 결과는 같지만 _의도가 명시적_ 이라 더 권장됨.
# JS 에는 직접 대응 없음 (그래서 항상 spread 만 씀).
# ============================================================================

def merge_dicts_via_union(a: dict[str, Any], b: dict[str, Any]) -> dict[str, Any]:
    """`|` 로 신규 dict 생성. 양쪽 다 변경 안 함."""
    return a | b


def merge_dicts_in_place(a: dict[str, Any], b: dict[str, Any]) -> dict[str, Any]:
    """`|=` 는 a 를 _제자리_ 갱신 (mutate)."""
    a |= b
    return a


# ============================================================================
# STEP 7 — Node `const {a, b} = obj` 의 부재 + 대안 4가지
# ============================================================================
#
# Python 에는 _할당문 dict destructuring 이 없다_. 가장 큰 차이.
#
# JS:    const { name, age } = user;
# Py:    name, age = user["name"], user["age"]    # ← 직접 대응 없음, 우회
# ============================================================================

# 대안 1 — 가장 단순. 보일러플레이트가 있지만 명시적.
def pick_via_index(user: dict[str, Any]) -> tuple[str, int]:
    name, age = user["name"], user["age"]
    return name, age


# 대안 2 — operator.itemgetter. 키 개수가 많아질수록 깔끔.
def pick_via_itemgetter(user: dict[str, Any]) -> tuple[str, int]:
    name, age = itemgetter("name", "age")(user)
    return name, age


# 대안 3 — 패턴 매칭 (3.10+). dict 구조 분해 + 검증을 한 번에.
def pick_via_match(user: dict[str, Any]) -> tuple[str, int]:
    match user:
        case {"name": name, "age": age}:
            return name, age
        case _:
            raise ValueError("name/age 키 없음")


# 대안 4 — Pydantic / dataclass 로 변환해 속성 접근. _실무에서 가장 흔함_.
# (여기서는 dataclass 시연. Pydantic 은 03단계에서.)


@dataclass
class _User:
    name: str
    age: int


def pick_via_dataclass(user: dict[str, Any]) -> tuple[str, int]:
    u = _User(**user)  # ← dict 를 kwargs 로 펼쳐서 생성자 호출 (STEP 4 응용)
    return u.name, u.age


# ============================================================================
# 안티패턴 — 헷갈리거나 함정인 케이스
# ============================================================================
#
# 1) 좌변 `*` 는 한 개만 가능
#       *a, *b = [1, 2, 3]      # ❌ SyntaxError
#       a, *b = [1, 2, 3]       # ✅
#
# 2) `+` vs spread
#       [1, 2] + [3, 4]         # ✅ list 한정
#       [*gen1, *gen2]          # ✅ generator/iterable 도 펼침 (더 범용)
#
# 3) dict 병합 시 키 충돌은 _뒤가 이김_
#       {**{"a": 1}, **{"a": 2}}    # → {"a": 2}
#
# 4) spread/merge 는 _얕은 복사_ — 깊은 병합 아님
#       a = {"meta": {"x": 1}}
#       b = {"meta": {"y": 2}}
#       {**a, **b}              # → {"meta": {"y": 2}}  ← x 잃어버림
#       # 깊은 병합이 필요하면 03 단계의 jsonpath / 직접 재귀 함수
#
# 5) JS 의 객체 spread(`{...obj}`) 와 Python 의 `f(**kwargs)` 호출은 _다른 일_
#       JS:  Object.assign({}, obj)  ← 객체 합치기
#       Py:  f(**d)                  ← dict 를 함수의 키워드 인자로 펼치기
#       Python 의 객체 합치기는 STEP 5/6 (`{**a, **b}` / `a | b`) 쪽.
# ============================================================================


def demo_unpacking() -> None:
    print("STEP 1: 시퀀스 unpacking 기본")
    print("  split_pair((1, 2)):", split_pair((1, 2)))
    print("  parse_csv_row('Alice,a@x.com,admin'):", parse_csv_row("Alice,a@x.com,admin"))

    print("\nSTEP 2: star 로 나머지 수집")
    print("  split_first_rest([1,2,3,4]):", split_first_rest([1, 2, 3, 4]))
    print("  split_head_last([1,2,3,4]):", split_head_last([1, 2, 3, 4]))
    print("  split_first_middle_last([1,2,3,4,5]):", split_first_middle_last([1, 2, 3, 4, 5]))

    print("\nSTEP 3: 중첩 unpacking + swap")
    print("  first_xy_and_label(((3,4), 'P')):", first_xy_and_label(((3.0, 4.0), "P")))
    print("  swap('a', 1):", swap("a", 1))

    print("\nSTEP 4: 호출 측 unpacking")
    print("  call_with_list_unpacking():", call_with_list_unpacking())
    print("  call_with_dict_unpacking():", call_with_dict_unpacking())
    print("  call_mixed_unpacking():", call_mixed_unpacking())

    print("\nSTEP 5: PEP 448 spread")
    print("  concat_lists([1,2],[3,4]):", concat_lists([1, 2], [3, 4]))
    print("  insert_in_middle([1,2], 99, [3,4]):", insert_in_middle([1, 2], 99, [3, 4]))
    print("  union_sets({1,2},{2,3}):", union_sets({1, 2}, {2, 3}))
    a, b = {"x": 1, "y": 2}, {"y": 99, "z": 3}
    print(f"  merge_dicts({a},{b}):", merge_dicts(a, b))

    print("\nSTEP 6: dict union 연산자")
    print(f"  merge_dicts_via_union({a},{b}):", merge_dicts_via_union(a, b))
    a_copy = a.copy()
    print("  merge_dicts_in_place(a,b) → a 가 변경됨:", merge_dicts_in_place(a_copy, b))

    print("\nSTEP 7: Node-style dict destructuring 의 4가지 대안")
    user = {"name": "Alice", "age": 30}
    print("  대안 1 (index):     ", pick_via_index(user))
    print("  대안 2 (itemgetter):", pick_via_itemgetter(user))
    print("  대안 3 (match):     ", pick_via_match(user))
    print("  대안 4 (dataclass): ", pick_via_dataclass(user))


if __name__ == "__main__":
    demo_unpacking()
