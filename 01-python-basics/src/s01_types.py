"""01 — 변수와 타입 힌트.

Python 은 동적 타입이지만 타입 힌트(PEP 484/604) 를 _작성하는 게 표준_.
런타임에 강제되진 않아도 mypy/IDE/Pydantic 이 그 힌트를 활용한다.
"""

from __future__ import annotations

# ---------- 기본 자료형 ----------
i: int = 42
f: float = 3.14
s: str = "hello"
b: bool = True
n: None = None  # 명시적으로 None 타입은 잘 안 씀, 보통 Optional[T] = T | None


def demo_basic_types() -> None:
    print("int:", i, type(i).__name__)
    print("float:", f, type(f).__name__)
    print("str:", s, type(s).__name__)
    print("bool:", b, type(b).__name__)

    # f-string: 다른 언어의 템플릿 리터럴
    name = "Alice"
    score = 87.5
    print(f"{name} 의 점수는 {score:.1f} 점")  # 소수점 1자리


# ---------- Optional / Union (3.10+ 문법) ----------
def find_user(user_id: int) -> str | None:
    """존재하지 않으면 None 반환. Java Optional<String> 자리."""
    db = {1: "Alice", 2: "Bob"}
    return db.get(user_id)  # 없으면 None


# ---------- 컨테이너 타입 힌트 ----------
def stats(numbers: list[int]) -> dict[str, float]:
    """list[int], dict[str, float] 처럼 제네릭 표현 (3.9+)."""
    return {
        "min": float(min(numbers)),
        "max": float(max(numbers)),
        "avg": sum(numbers) / len(numbers),
    }


# ---------- 캐스팅 vs 변환 ----------
def demo_conversions() -> None:
    s_num = "123"
    n_num: int = int(s_num)  # 변환 — 실패 시 ValueError
    print(f"'{s_num}' -> {n_num + 1}")

    # bool 변환은 truthy/falsy 규칙: 0/빈 컬렉션/None/"" → False
    print("bool([]):", bool([]))
    print("bool([0]):", bool([0]))  # 비어 있지 않으면 True (요소가 0이어도)


def main() -> None:
    print("=== 기본 타입 ===")
    demo_basic_types()

    print("\n=== Optional ===")
    print("user 1 ->", find_user(1))
    print("user 99 ->", find_user(99))

    print("\n=== 컬렉션 ===")
    print(stats([1, 2, 3, 4, 5]))

    print("\n=== 변환 ===")
    demo_conversions()


if __name__ == "__main__":
    main()
