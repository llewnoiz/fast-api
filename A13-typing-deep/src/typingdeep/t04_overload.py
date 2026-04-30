"""@overload / ParamSpec / TypeVarTuple — _고급_ 함수 시그니처.

언제 사용?
    - 같은 함수가 _입력 따라_ 다른 _출력 타입_ 을 가질 때
    - 데코레이터가 _감싼 함수의 시그니처를 보존_ 해야 할 때

비교:
    TypeScript: function overloads — 거의 동일
    Java/Kotlin: 메서드 오버로딩 — _시그니처 다른_ 진짜 함수
    Python: 진짜 오버로드 X — 타입 체커용 _힌트_
"""

from __future__ import annotations

from collections.abc import Callable
from typing import ParamSpec, TypeVar, TypeVarTuple, overload

# ── @overload ──────────────────────────────────────────────────
# 같은 함수가 _입력 따라_ 다른 출력 타입.

@overload
def split(data: str) -> list[str]: ...
@overload
def split(data: bytes) -> list[bytes]: ...


def split(data: str | bytes) -> list[str] | list[bytes]:
    """실제 구현 — 마지막 정의가 진짜.

    호출자 입장:
        x = split("a,b,c")    # type: list[str]
        y = split(b"a,b,c")   # type: list[bytes]
    """
    return data.split(b",") if isinstance(data, bytes) else data.split(",")


# ── ParamSpec — 데코레이터의 _시그니처 보존_ ────────────────────
P = ParamSpec("P")
R = TypeVar("R")


def timed[**P, R](fn: Callable[P, R]) -> Callable[P, R]:
    """데코레이터 — 원함수의 _인자/반환_ 시그니처 _그대로_ 보존.

    `P.args` / `P.kwargs` 가 _wildcard_ 처럼 _임의 인자_ 통과.
    PEP 695 (3.12+) 에선:
        def timed[**P, R](fn: Callable[P, R]) -> Callable[P, R]: ...
    """
    import time  # noqa: PLC0415

    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        start = time.monotonic()
        result = fn(*args, **kwargs)
        _ = time.monotonic() - start
        return result

    return wrapper


# PEP 695 새 문법
def retried[**P, R](fn: Callable[P, R]) -> Callable[P, R]:
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        try:
            return fn(*args, **kwargs)
        except Exception:
            return fn(*args, **kwargs)  # 한 번만 재시도 — 학습용

    return wrapper


# ── TypeVarTuple — _가변 길이_ generic ──
# `*Ts` 가 _여러 타입_ 한 번에 받음. tuple / array shape 에 유용.
Ts = TypeVarTuple("Ts")


def first_and_rest[*Ts](items: tuple[int, *Ts]) -> tuple[int, tuple[*Ts]]:
    """`(int, str, bool)` → `int, (str, bool)`.

    학습용 — 실제로는 numpy / 텐서 shape 추적에 _운영급_ 사용.
    """
    head, *rest = items
    return head, tuple(rest)  # type: ignore[return-value]
