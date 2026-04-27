"""04 — 함수.

기본 인자 / 키워드 인자 / 가변 인자 / 람다 / 1급 함수 / 데코레이터.
FastAPI 의 라우트와 의존성 주입은 _전부 함수_ 위에서 돌아가므로 핵심.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from functools import wraps
from typing import Any


# ---------- 기본 인자 + 키워드 인자 ----------
def greet(name: str, greeting: str = "안녕", excited: bool = False) -> str:
    """기본값이 있는 인자는 _뒤로_ 몰아야 함. 호출 시 키워드로 명시 가능."""
    msg = f"{greeting}, {name}"
    return msg + "!" if excited else msg


# ---------- 가변 인자 ----------
def sum_all(*nums: int, label: str = "합") -> str:
    """*nums 는 위치 가변 (Java varargs), **kwargs 는 키워드 가변."""
    return f"{label}: {sum(nums)}"


def build_user(**fields: Any) -> dict[str, Any]:
    """**fields 는 키워드 인자 dict 수집."""
    fields.setdefault("created_at", time.time())
    return fields


# ---------- 키워드 전용 인자 (* 뒤는 무조건 키워드) ----------
def paginate(query: str, *, page: int = 1, size: int = 20) -> str:
    """page/size 는 _반드시_ 키워드로 호출해야 함 — 가독성 강제."""
    return f"{query}?page={page}&size={size}"


# ---------- 1급 함수 + 람다 ----------
def apply(fn: Callable[[int], int], x: int) -> int:
    """함수도 인자로. Java 의 functional interface 자리지만 더 간결."""
    return fn(x)


# ---------- 데코레이터 ----------
# PEP 695 (Python 3.12+) 의 새 제네릭 문법: `def f[T](...)`.
# 예전 코드에서는 `TypeVar("T")` / `ParamSpec("P")` 를 모듈 변수로 선언했음.

def timed[**P, R](fn: Callable[P, R]) -> Callable[P, R]:
    """함수 실행 시간 측정 데코레이터 — Spring AOP `@Around` 의 가장 단순한 형태."""
    @wraps(fn)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        t0 = time.perf_counter()
        try:
            return fn(*args, **kwargs)
        finally:
            elapsed_ms = (time.perf_counter() - t0) * 1000
            print(f"  [timed] {fn.__name__} took {elapsed_ms:.2f}ms")
    return wrapper


def retry(times: int = 3) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """파라미터를 받는 데코레이터 (factory 패턴)."""
    def decorator[**P, R](fn: Callable[P, R]) -> Callable[P, R]:
        @wraps(fn)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            last_exc: BaseException | None = None
            for i in range(1, times + 1):
                try:
                    return fn(*args, **kwargs)
                except Exception as e:  # noqa: BLE001 — 학습용 광범위 캐치
                    last_exc = e
                    print(f"  [retry] {fn.__name__} 시도 {i}/{times} 실패: {e}")
            assert last_exc is not None
            raise last_exc
        return wrapper
    return decorator


@timed
@retry(times=2)
def flaky_call(n: int) -> int:
    """홀수 호출은 실패. 데코레이터 두 개 쌓아본 예시."""
    flaky_call.calls = getattr(flaky_call, "calls", 0) + 1  # type: ignore[attr-defined]
    if flaky_call.calls % 2 == 1:  # type: ignore[attr-defined]
        raise RuntimeError("일시 실패")
    return n * 2


def main() -> None:
    print("=== 기본/키워드 인자 ===")
    print(greet("Alice"))
    print(greet("Bob", excited=True))
    print(greet(name="Carol", greeting="hi", excited=True))

    print("\n=== 가변 인자 ===")
    print(sum_all(1, 2, 3, 4, 5))
    print(sum_all(10, 20, label="총합"))
    print(build_user(name="Alice", email="a@x.com"))

    print("\n=== 키워드 전용 ===")
    print(paginate("users"))
    print(paginate("users", page=3, size=50))
    # paginate("users", 3, 50)  # ← TypeError: 키워드 강제

    print("\n=== 1급 함수 / 람다 ===")
    print("apply(double):", apply(lambda x: x * 2, 21))
    nums = [3, 1, 4, 1, 5, 9, 2, 6]
    print("정렬(절대값):", sorted(nums, key=lambda x: -x))

    print("\n=== 데코레이터 ===")
    print("결과:", flaky_call(10))


if __name__ == "__main__":
    main()
