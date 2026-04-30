"""메시지 카탈로그 테스트."""

from __future__ import annotations

from i18napp.catalog import gettext, ngettext


def test_gettext_english() -> None:
    assert gettext("greeting", locale="en", name="alice") == "Hello, alice!"


def test_gettext_korean() -> None:
    assert gettext("greeting", locale="ko", name="alice") == "안녕하세요, alice 님!"


def test_gettext_japanese() -> None:
    assert "alice" in gettext("greeting", locale="ja", name="alice")


def test_gettext_falls_back_to_english() -> None:
    """알 수 없는 locale → 영어."""
    assert gettext("greeting", locale="zh", name="x") == "Hello, x!"


def test_gettext_falls_back_to_key() -> None:
    """알 수 없는 key → 그 key 자체 (디버깅 친화)."""
    assert gettext("nonexistent.key", locale="en") == "nonexistent.key"


def test_ngettext_singular() -> None:
    assert ngettext("items_one", "items_other", 1, locale="en") == "1 item"


def test_ngettext_plural() -> None:
    assert ngettext("items_one", "items_other", 5, locale="en") == "5 items"


def test_ngettext_korean_same_form() -> None:
    """한국어는 단복수 형태 같음."""
    assert ngettext("items_one", "items_other", 1, locale="ko") == "1 개 항목"
    assert ngettext("items_one", "items_other", 5, locale="ko") == "5 개 항목"


def test_gettext_primary_subtag_match() -> None:
    """ko-KR → ko catalog 사용."""
    assert (
        gettext("greeting", locale="ko-KR", name="x") == "안녕하세요, x 님!"
    )
