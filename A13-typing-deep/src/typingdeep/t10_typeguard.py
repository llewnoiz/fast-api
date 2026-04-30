"""TypeGuard / TypeIs — _런타임 타입 좁히기_ + 정적 타입 narrowing.

문제:
    `isinstance(x, int)` 는 mypy 가 _자동 narrowing_.
    하지만 `is_int_list(x)` 같은 _커스텀_ 함수는 mypy 가 모름.

해법:
    `def is_int_list(x: object) -> TypeGuard[list[int]]: ...`
    → mypy 가 _True 분기_ 에서 `x: list[int]` 로 좁힘.

`TypeIs` (3.13+):
    `TypeGuard` 의 _개선판_. 더 정확한 narrowing (false 분기에서도 정보 유지).
    3.12 에선 typing_extensions 로 쓸 수 있지만 본 모듈은 _TypeGuard_ 로 통일.

비교:
    TypeScript: `is` 구문 (`function isFish(p): p is Fish`)
    Kotlin: smart cast (`is Fish` 후 자동)
"""

from __future__ import annotations

from typing import TypeGuard


def is_int_list(value: object) -> TypeGuard[list[int]]:
    """list 이고 모든 요소가 int 면 True. mypy 가 narrowing 적용."""
    return isinstance(value, list) and all(isinstance(x, int) for x in value)


def sum_if_ints(value: object) -> int:
    """`is_int_list` 가 True 면 mypy 는 `value: list[int]` 로 _좁혀서_ 봄."""
    if is_int_list(value):
        return sum(value)  # mypy: list[int] OK
    return 0


# ── 비교: 그냥 isinstance 만 쓰면 mypy 가 못 좁힘 ──
def sum_if_ints_naive(value: object) -> int:
    if isinstance(value, list) and all(isinstance(x, int) for x in value):
        # mypy 입장: value 는 list[Any] (요소 타입 못 좁힘)
        return sum(value)
    return 0
