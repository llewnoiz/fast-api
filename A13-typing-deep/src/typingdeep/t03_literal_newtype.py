"""Literal / NewType / TypedDict / Final — _타입 정밀화_ 4종 세트.

목적:
    - `Literal["red", "green"]` ── 문자열을 _그 두 값_ 으로 _제한_
    - `NewType("UserId", int)` ── int 와 _구조적으로 같지만_ 타입 체커는 _구분_
    - `TypedDict` ── dict 의 _키별 타입_ 명시 (JSON 응답 / 외부 API 친화)
    - `Final` ── _재할당 금지_ 상수
"""

from __future__ import annotations

from typing import Final, Literal, NewType, NotRequired, TypedDict

# ── Literal ─────────────────────────────────────────────────────
Color = Literal["red", "green", "blue"]


def paint(color: Color) -> str:
    """`paint("yellow")` 는 type error — Literal 가 _좁은_ 타입."""
    return f"painted {color}"


# Literal 의 _진짜_ 가치 — `match` / 분기 _철저_ 강제 (exhaustive check)
def color_hex(color: Color) -> str:
    match color:
        case "red":
            return "#ff0000"
        case "green":
            return "#00ff00"
        case "blue":
            return "#0000ff"
    # mypy 가 _도달 불가능_ 검증 — Literal 의 모든 case 처리 안 하면 경고
    raise AssertionError("unreachable")


# ── NewType ────────────────────────────────────────────────────
# 런타임은 _그냥 int_ 인데 타입 체커는 _다른 타입_ 으로 봄 → ID 섞임 방지
UserId = NewType("UserId", int)
OrderId = NewType("OrderId", int)


def get_user(uid: UserId) -> str:
    return f"user-{uid}"


# `get_user(OrderId(42))` 는 type error — int 끼리 섞임 방지


# ── TypedDict ───────────────────────────────────────────────────
class UserDict(TypedDict):
    """JSON 응답 / 외부 API 의 dict 모양 명시."""

    id: int
    name: str
    email: str
    is_admin: NotRequired[bool]  # 옵셔널 — 키 없어도 OK


def make_user(name: str, email: str) -> UserDict:
    return {"id": 1, "name": name, "email": email}


# Pydantic 과 비교:
#   TypedDict: _런타임 검증 X_ — 타입 체커만. 외부 데이터 _모양_ 표현.
#   Pydantic:  _런타임 검증_ + 직렬화. _신뢰 안 되는_ 입력엔 Pydantic.


# ── Final ──────────────────────────────────────────────────────
PI: Final = 3.14159
DEFAULT_RETRIES: Final[int] = 3
# `PI = 3.0` 은 type error — 재할당 금지

# `Final` 인스턴스 변수 (생성자에서 한 번만)
class Connection:
    host: Final[str]

    def __init__(self, host: str) -> None:
        self.host = host
        # `self.host = "..."` 는 다른 메서드에서 type error
