"""Babel 포맷팅 테스트."""

from __future__ import annotations

from datetime import date

from i18napp.babel_setup import (
    display_locale_name,
    format_d,
    format_money,
    format_number,
    format_relative,
)


def test_format_money_usd_en() -> None:
    formatted = format_money(1234.56, "USD", "en")
    # `$1,234.56` 또는 `US$1,234.56` 등 — 핵심: 천 단위 콤마 + . 소수점
    assert "1,234.56" in formatted
    assert "$" in formatted or "US" in formatted


def test_format_money_krw_no_decimals() -> None:
    """KRW 는 소수점 _없는_ 통화."""
    formatted = format_money(1234, "KRW", "ko")
    assert "1,234" in formatted
    assert "₩" in formatted or "KRW" in formatted


def test_format_money_eur_german() -> None:
    """독일어 — 천 단위 `.` 소수점 `,` ── _다름_."""
    formatted = format_money(1234.56, "EUR", "de")
    # de: `1.234,56 €` 형태 (Babel 버전 따라 미세 차이)
    assert "1.234" in formatted
    assert "," in formatted


def test_format_number_locale_difference() -> None:
    en = format_number(1234567.89, "en")
    de = format_number(1234567.89, "de")
    assert en != de
    assert en == "1,234,567.89"
    assert de == "1.234.567,89"


def test_format_date_long() -> None:
    d = date(2026, 4, 30)
    en = format_d(d, "en", "long")
    ko = format_d(d, "ko", "long")
    # _다른 형식_ — 정확한 문자열보단 _둘이 다름_ 검증 (Babel 버전 안정)
    assert en != ko
    assert "2026" in en
    assert "2026" in ko


def test_format_relative_seconds() -> None:
    """1시간 전."""
    en = format_relative(-3600, "en")
    ko = format_relative(-3600, "ko")
    assert "hour" in en or "ago" in en
    assert "1" in ko
    assert en != ko


def test_display_locale_name() -> None:
    assert display_locale_name("ko", in_locale="en") == "Korean"
    # 자기 언어로
    assert "한국" in display_locale_name("ko", in_locale="ko")
