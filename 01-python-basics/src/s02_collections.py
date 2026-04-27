"""02 — 컬렉션과 컴프리헨션.

list / tuple / dict / set 의 _감각_ 익히기.
Python 의 시그니처 기능: list/dict/set comprehension.
"""

from __future__ import annotations

from collections.abc import Iterator


# ---------- list ----------
def demo_list() -> None:
    xs: list[int] = [1, 2,3 ]
    xs.append(4)             # 끝에 추가
    xs.extend([5, 6])        # 여러 개 추가
    xs.insert(0, 0)          # 인덱스에 삽입
    # xs.remove(3)             # 값 제거 (없으면 ValueError)
    print("list:", xs)

    # 슬라이싱 — Java/Go 보다 표현력이 훨씬 강함
    print("xs[1:4]:", xs[1:4])      # 1~3
    print("xs[::-1]:", xs[::-1])    # 뒤집기
    print("xs[::2]:", xs[::2])      # 짝수 인덱스만


# ---------- tuple (불변 list) ----------
def demo_tuple() -> None:
    point: tuple[float, float] = (3.0, 4.0)
    x, y = point  # 언패킹 — Go 의 다중 반환값 받기와 비슷
    print(f"x={x}, y={y}")

    # 함수에서 다중 값 반환은 사실 tuple 반환
    a, b = divmod(17, 5)  # (몫, 나머지)
    print(f"17/5 = {a} 나머지 {b}")


# ---------- dict ----------
def demo_dict() -> None:
    user: dict[str, str | int] = {"name": "Alice", "age": 30}
    user["email"] = "a@x.com"
    print("user:", user)
    print("name:", user.get("name"))
    print("missing:", user.get("missing", "기본값"))

    # 순회: items() 가 가장 흔함
    for k, v in user.items():
        print(f"  {k} = {v}")


# ---------- set ----------
def demo_set() -> None:
    a = {1, 2, 3}
    b = {2, 3, 4}
    print("교집합:", a & b)
    print("합집합:", a | b)
    print("차집합:", a - b)


# ============================================================================
# 컴프리헨션 — Python 의 시그니처 기능
# ============================================================================
#
# 한 줄로 "기존 컬렉션을 변환/필터링해서 새 컬렉션을 만든다".
#
# 기본 형태 (괄호 종류로 결과 타입이 결정됨):
#
#       [ 표현식    for 변수 in 컬렉션    if 조건 ]
#       └─ map ─┘  └──── for ─────┘   └filter┘
#       │
#       └─ [...] = list,  {...:...} = dict,  {...} = set,  (...) = generator
#
# 다른 언어 대응:
#       Java Stream:  xs.stream().filter(...).map(...).toList()
#       Kotlin:       xs.filter { ... }.map { ... }
#       JS:           xs.filter(...).map(...)
#       Go:           대응 없음 — for 루프로 직접 작성
#
# 핵심: "결과를 만드는 _레시피_ 가 한눈에 보인다" 는 게 가치.
# 일반 for 루프는 "어떻게" 만드는지 절차를 보여주고,
# 컴프리헨션은 "무엇을" 만드는지 결과 형태를 보여준다 (선언형).
# ============================================================================


# ---------- STEP 1: for 루프 → 컴프리헨션 변환 ----------
def squares_for_loop(n: int) -> list[int]:
    """일반 for 루프로 0..n-1 제곱 리스트 만들기 (다른 언어 스타일)."""
    result: list[int] = []
    for x in range(n):
        result.append(x * x)
    return result


def squares_comprehension(n: int) -> list[int]:
    """위와 _완전히 같은 결과_, 컴프리헨션으로 한 줄.

    Java Stream:  IntStream.range(0, n).map(x -> x * x).boxed().toList()
    """
    return [x * x for x in range(n)]


# ---------- STEP 2: filter (`if` 절) ----------
def even_numbers(n: int) -> list[int]:
    """0..n-1 중 짝수만.

    Java Stream:  IntStream.range(0, n).filter(x -> x % 2 == 0).boxed().toList()
    """
    return [x for x in range(n) if x % 2 == 0]


# ---------- STEP 3: filter + map 조합 ----------
def even_squares(n: int) -> list[int]:
    """짝수만 골라 제곱.

    Java Stream:
        IntStream.range(0, n)
                 .filter(x -> x % 2 == 0)
                 .map(x -> x * x)
                 .boxed().toList()

    구문 위치 주의:
        [  x * x       for x in range(n)     if x % 2 == 0  ]
           └ map ┘     └─── for ────┘        └── filter ──┘
        # filter 가 뒤에 오지만 _실행 순서_ 는 for → if → map.
    """
    return [x * x for x in range(n) if x % 2 == 0]


# ---------- STEP 4: dict / set comprehension ----------
def word_lengths(words: list[str]) -> dict[str, int]:
    """단어 → 길이 매핑.

    Java Stream:
        words.stream().collect(Collectors.toMap(w -> w, String::length))
    """
    return {w: len(w) for w in words}


def unique_lengths(words: list[str]) -> set[int]:
    """등장한 길이의 _집합_ (중복 제거).

    Java Stream:
        words.stream().map(String::length).collect(Collectors.toSet())
    """
    return {len(w) for w in words}


# ---------- STEP 5: 중첩 (nested) ----------
def flatten(matrix: list[list[int]]) -> list[int]:
    """2차원 리스트를 1차원으로 평탄화.

    중첩 컴프리헨션 읽는 법: _왼쪽에서 오른쪽 for 순서대로_, 일반 중첩 for 와 동일.

        [val   for row in matrix   for val in row]
        # ≡
        # for row in matrix:
        #     for val in row:
        #         result.append(val)

    Java Stream:
        matrix.stream().flatMap(List::stream).toList()
    """
    return [val for row in matrix for val in row]


def pairs_with_sum(xs: list[int], target: int) -> list[tuple[int, int]]:
    """합이 target 이 되는 모든 (i 인덱스 < j 인덱스) 쌍.

    중첩 + filter 조합 — 가독성을 위해 줄바꿈 권장.
    """
    return [
        (xs[i], xs[j])
        for i in range(len(xs))
        for j in range(i + 1, len(xs))
        if xs[i] + xs[j] == target
    ]


# ---------- STEP 6: 조건부 _값_ (if/else 가 표현식 자리로) ----------
def label_signs(xs: list[int]) -> list[str]:
    """각 원소를 '+'/'-'/'0' 으로 라벨링.

    if/else 가 _표현식 자리_(왼쪽)에 오는 점 주의 — STEP 2 의 filter `if` 와 다름.

        [ "+" if x > 0 else "-" if x < 0 else "0"  for x in xs ]
        └────── 표현식(삼항 연쇄) ──────┘  └─ for ─┘
    """
    return ["+" if x > 0 else "-" if x < 0 else "0" for x in xs]


# ---------- STEP 7: generator expression — lazy / 메모리 절약 ----------
def squares_lazy(n: int) -> Iterator[int]:
    """list 가 아니라 generator (즉시 계산 X, 한 번에 한 값씩).

        ( ... )   ← 괄호가 [] 가 아니라 () 면 generator
        ─ list 였다면 100만 개 메모리 차지, gen 은 즉시 평가하지 않아 메모리 거의 0.

    Java 비교:  Stream 의 _intermediate operation_ 과 동일한 lazy semantics.
                terminal operation(toList/forEach 등) 호출 전에는 계산되지 않음.
    """
    return (x * x for x in range(n))


# ---------- 안티패턴: 컴프리헨션을 _쓰지 말아야_ 할 때 ----------
#
# 1) 부수효과(I/O, 출력) 만 필요할 때 — for 루프 쓰기
#       [print(x) for x in xs]   # ❌ 결과 list 가 버려짐, 의도가 흐려짐
#       for x in xs: print(x)     # ✅
#
# 2) 너무 길거나 중첩이 3겹 이상 — 가독성 떨어짐
#       [f(x, y, z) for x in xs for y in ys for z in zs if g(x, y, z)]   # 😵
#       → 일반 for 루프 + append 가 더 읽힘
#
# 3) 조건이 여러 줄에 걸친 복잡한 if/else — 함수로 빼기
#       [complex_logic(x) for x in xs]   # ✅ logic 은 별도 함수로
#
# 4) `if x is None: continue` 처럼 흐름 제어가 필요한 경우 — for 루프 쓰기
#
# 가이드라인:
#   - "한 화면 안에서 한눈에 들어오면" 컴프리헨션 OK.
#   - 80자 넘어가거나 if 가 두 개 이상이면 일반 for 루프를 의심.


def demo_comprehensions() -> None:
    print("STEP 1: for 루프 vs 컴프리헨션 (같은 결과)")
    print("  for 루프      :", squares_for_loop(5))
    print("  컴프리헨션    :", squares_comprehension(5))

    print("\nSTEP 2: filter (`if` 절)")
    print("  even_numbers(10):", even_numbers(10))

    print("\nSTEP 3: filter + map")
    print("  even_squares(10):", even_squares(10))

    print("\nSTEP 4: dict / set comprehension")
    words = ["foo", "bar", "hello", "ab", "a"]
    print(f"  word_lengths({words}):", word_lengths(words))
    print(f"  unique_lengths({words}):", unique_lengths(words))

    print("\nSTEP 5: 중첩")
    matrix = [[1, 2, 3], [4, 5], [6]]
    print(f"  flatten({matrix}):", flatten(matrix))
    print("  pairs_with_sum([1,2,3,4,5], 6):", pairs_with_sum([1, 2, 3, 4, 5], 6))

    print("\nSTEP 6: 조건부 값 (if/else 표현식)")
    print("  label_signs([3,-1,0,5,-7]):", label_signs([3, -1, 0, 5, -7]))

    print("\nSTEP 7: generator (lazy)")
    gen = squares_lazy(1_000_000)  # list 면 수백 MB, gen 은 즉시 평가 안 됨
    print("  타입:", type(gen).__name__)
    print("  처음 5개만 꺼내기:", [next(gen) for _ in range(5)])
    


def main() -> None:
    print("=== list ===")
    demo_list()
    print("\n=== tuple ===")
    demo_tuple()
    print("\n=== dict ===")
    demo_dict()
    print("\n=== set ===")
    demo_set()
    print("\n=== comprehensions ===")
    demo_comprehensions()


if __name__ == "__main__":
    main()
