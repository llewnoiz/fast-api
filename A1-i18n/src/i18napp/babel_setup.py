"""Babel — 날짜 / 숫자 / 통화 _로케일별 포맷_.

번역과 _별개_ 로 _포맷_ 도 다국어:
    숫자: `1,234,567.89` (en) vs `1.234.567,89` (de) vs `1,234,567.89` (ko)
    날짜: `Apr 30, 2026` (en-US) vs `2026年4月30日` (ja) vs `30/04/2026` (en-GB)
    통화: `$1,234.56` (en-US) vs `₩1,234` (ko-KR) vs `€1.234,56` (de-DE)

Babel = 가장 표준 라이브러리. CLDR (Unicode Common Locale Data Repository) 기반.

비교:
    Java: `java.util.Locale` + `NumberFormat` / `DateTimeFormatter`
    JS: `Intl.NumberFormat` / `Intl.DateTimeFormat` (ECMAScript Internationalization API)
    Rust: ICU4X
"""

from __future__ import annotations

from datetime import date, datetime

from babel import Locale
from babel.dates import format_date, format_datetime, format_timedelta
from babel.numbers import format_currency, format_decimal


def format_money(amount: float | int, currency: str, locale: str = "en") -> str:
    """`format_money(1234.56, "USD", "en")` → `"$1,234.56"`.

    `format_money(1234.56, "KRW", "ko")` → `"₩1,235"` (KRW 는 정수 통화).
    """
    return format_currency(amount, currency, locale=locale)


def format_number(value: float | int, locale: str = "en") -> str:
    """천 단위 구분 + 소수점 _로케일별_."""
    return format_decimal(value, locale=locale)


def format_d(d: date, locale: str = "en", fmt: str = "long") -> str:
    """`fmt`: `"short" / "medium" / "long" / "full"`."""
    return format_date(d, format=fmt, locale=locale)


def format_dt(dt: datetime, locale: str = "en", fmt: str = "medium") -> str:
    return format_datetime(dt, format=fmt, locale=locale)


def format_relative(seconds: int, locale: str = "en") -> str:
    """`-3600` (1시간 전) → `"1 hour ago"` (en) / `"1시간 전"` (ko)."""
    from datetime import timedelta  # noqa: PLC0415

    return format_timedelta(timedelta(seconds=seconds), add_direction=True, locale=locale)


def display_locale_name(target: str, *, in_locale: str = "en") -> str:
    """`display_locale_name("ko", in_locale="en")` → `"Korean"`.

    UI 의 _언어 선택 드롭다운_ 에 유용 — 자기 언어로 표시.
    """
    return Locale.parse(target).get_display_name(in_locale) or target
