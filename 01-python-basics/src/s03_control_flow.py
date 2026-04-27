"""03 — 제어 흐름.

if / for / while / match (3.10+) / 예외.
"""

from __future__ import annotations


# ---------- if / elif / else ----------
def grade(score: int) -> str:
    # 삼항 표현 — Java `cond ? a : b` 와 _순서가 다름_
    label = "음수" if score < 0 else "정상"
    if label == "음수":
        return label
    if score >= 90:
        return "A"
    elif score >= 80:
        return "B"
    elif score >= 70:
        return "C"
    else:
        return "F"


# ---------- for ----------
def demo_for() -> None:
    # 인덱스가 필요하면 enumerate (Java 의 indexed for 자리)
    fruits = ["사과", "바나나", "체리"]
    for i, fruit in enumerate(fruits, start=1):
        print(f"{i}. {fruit}")

    # 두 시퀀스 동시 순회 — zip
    names = ["Alice", "Bob"]
    ages = [30, 25]
    for name, age in zip(names, ages, strict=True):
        print(f"{name} ({age})")

    # range 는 끝값 제외 (Java for(int i=0;i<10;i++) 와 동일)
    total = 0
    for i in range(1, 11):  # 1..10
        total += i
    print("1~10 합:", total)


# ---------- while + break / continue / else ----------
def demo_while() -> None:
    """while/for 의 else 절: break 없이 정상 종료될 때만 실행 — Python 만의 특이 문법."""
    n = 17
    # 소수 판별
    if n < 2:
        print(f"{n} 은 소수 아님")
        return
    i = 2
    while i * i <= n:
        if n % i == 0:
            print(f"{n} 은 소수 아님 ({i} 로 나눠짐)")
            break
        i += 1
    else:
        # break 가 한 번도 호출되지 않았을 때만 실행
        print(f"{n} 은 소수")


# ---------- match (3.10+) — Java 17 sealed switch 비슷 ----------
def describe(value: object) -> str:
    match value:
        case int() if value < 0:
            return "음수 정수"
        case 0:
            return "영"
        case int():
            return "양의 정수"
        case [x, y]:
            return f"2-요소 리스트: ({x}, {y})"
        case {"type": "user", "name": name}:
            return f"user dict, name={name}"
        case str() as s:
            return f"문자열 길이 {len(s)}"
        case _:
            return "기타"


# ---------- 예외 ----------
class InvalidScoreError(ValueError):
    """도메인 예외 — 표준 예외를 상속해 의미 부여."""


def parse_score(s: str) -> int:
    try:
        n = int(s)
    except ValueError as e:
        # raise X from Y — 원본 예외 체인 보존 (Java cause 와 동일 개념)
        raise InvalidScoreError(f"점수 파싱 실패: {s!r}") from e
    else:
        # try 가 성공한 경우만 실행
        if not 0 <= n <= 100:
            raise InvalidScoreError(f"범위 밖: {n}")
        return n
    finally:
        # 항상 실행 — 자원 해제용. 단 Python 은 with 문이 더 흔함
        pass


def main() -> None:
    print("=== if ===")
    for s in [95, 82, 70, 50, -1]:
        print(f"  {s} -> {grade(s)}")

    print("\n=== for ===")
    demo_for()

    print("\n=== while + else ===")
    demo_while()

    print("\n=== match ===")
    for v in [-3, 0, 7, [1, 2], {"type": "user", "name": "Alice"}, "hello", 3.14]:
        print(f"  {v!r} -> {describe(v)}")

    print("\n=== 예외 ===")
    for raw in ["50", "abc", "150"]:
        try:
            print(f"  '{raw}' -> {parse_score(raw)}")
        except InvalidScoreError as e:
            print(f"  '{raw}' -> ERR: {e}")


if __name__ == "__main__":
    main()
