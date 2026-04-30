"""Literal / NewType / TypedDict 테스트."""

from __future__ import annotations

from typingdeep.t03_literal_newtype import (
    Connection,
    OrderId,
    UserId,
    color_hex,
    get_user,
    make_user,
    paint,
)


def test_literal_paint() -> None:
    assert paint("red") == "painted red"
    assert paint("blue") == "painted blue"


def test_literal_match_exhaustive() -> None:
    assert color_hex("red") == "#ff0000"
    assert color_hex("green") == "#00ff00"
    assert color_hex("blue") == "#0000ff"


def test_newtype_runtime_is_int() -> None:
    """NewType 는 _런타임_ 에는 그냥 int — wrapping 함수가 int 반환."""
    uid = UserId(42)
    assert uid == 42
    assert isinstance(uid, int)


def test_newtype_distinct_at_typecheck() -> None:
    """런타임은 같지만 _타입 체커_ 가 섞임 잡음.

    `get_user(OrderId(1))` 는 mypy 에서 error — 런타임은 동작.
    학습용 검증 — _구분되는_ ID 사용 강조.
    """
    assert get_user(UserId(1)) == "user-1"


def test_typed_dict_creation() -> None:
    user = make_user("alice", "alice@example.com")
    assert user["name"] == "alice"
    assert user["email"] == "alice@example.com"
    assert user["id"] == 1
    # NotRequired 키는 _없어도_ OK
    assert user.get("is_admin") is None


def test_final_attribute_set_in_init() -> None:
    """Final 인스턴스 변수 — 생성자에선 OK."""
    conn = Connection("localhost")
    assert conn.host == "localhost"
    # `conn.host = "..."` 은 _다른 메서드에서_ mypy error (런타임은 가능)


def test_newtype_does_not_collide_at_runtime() -> None:
    uid = UserId(1)
    oid = OrderId(1)
    assert uid == oid  # 런타임은 그냥 int (== True)
