"""Locale negotiation 테스트."""

from __future__ import annotations

from i18napp.locale import (
    LangTag,
    negotiate_locale,
    parse_accept_language,
)


def test_parse_simple() -> None:
    tags = parse_accept_language("en")
    assert tags == [LangTag(tag="en", quality=1.0)]


def test_parse_with_quality() -> None:
    tags = parse_accept_language("ko-KR,ko;q=0.9,en;q=0.8")
    assert [t.tag for t in tags] == ["ko-KR", "ko", "en"]
    assert tags[1].quality == 0.9
    assert tags[2].quality == 0.8


def test_parse_sorted_by_quality() -> None:
    """q 큰 것 _먼저_."""
    tags = parse_accept_language("en;q=0.5,ko;q=0.9,ja;q=0.7")
    assert [t.tag for t in tags] == ["ko", "ja", "en"]


def test_parse_empty_or_invalid() -> None:
    assert parse_accept_language(None) == []
    assert parse_accept_language("") == []


def test_negotiate_exact_match() -> None:
    """ko-KR 정확 매치."""
    assert (
        negotiate_locale(
            "ko-KR;q=0.9,en;q=0.5", supported=["ko-KR", "en"], default="en"
        )
        == "ko-kr"
    )


def test_negotiate_primary_match() -> None:
    """ko-KR 요청, 지원은 ko 만 → ko 매치."""
    assert (
        negotiate_locale(
            "ko-KR,en;q=0.5", supported=["ko", "en"], default="en"
        )
        == "ko"
    )


def test_negotiate_falls_back_to_default() -> None:
    """매칭 실패 → default."""
    assert (
        negotiate_locale("zh", supported=["ko", "en"], default="en") == "en"
    )


def test_negotiate_no_header() -> None:
    assert negotiate_locale(None, supported=["ko", "en"], default="en") == "en"


def test_negotiate_q_priority() -> None:
    """en;q=0.9 우선, ko;q=0.1 무시."""
    assert (
        negotiate_locale("en;q=0.9,ko;q=0.1", supported=["en", "ko"], default="en")
        == "en"
    )


def test_negotiate_wildcard() -> None:
    """`*` ── 첫 supported."""
    assert (
        negotiate_locale("*", supported=["ja", "ko", "en"], default="en") == "ja"
    )
