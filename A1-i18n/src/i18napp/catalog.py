"""메시지 카탈로그 — `gettext` 호환 인터페이스.

학습 단순화:
    표준 gettext 는 `.po` / `.mo` 파일 — 운영 권장.
    본 모듈은 _Python dict_ 기반 — 의존성 X, 작은 앱 친화.

운영 패턴:
    1. 코드에 `_("hello, {name}")` 같은 _문자열 마커_
    2. `pybabel extract -o messages.pot src/` ── 모든 마커 수집
    3. `pybabel init -i messages.pot -d locales -l ko` ── ko/messages.po 생성
    4. 번역가가 `.po` 편집
    5. `pybabel compile -d locales` ── `.mo` 컴파일
    6. 런타임에 `gettext.translation("messages", "locales", [locale]).gettext(...)`

본 모듈의 단순화 (학습용):
    `MESSAGES = {"ko": {"hello": "안녕"}}` ── dict 직접.

비교:
    Java: ResourceBundle (`Messages_ko.properties`) — 비슷한 dict 기반
    Spring: MessageSource — 자동 reload, fallback
    Node: i18next, formatjs — JSON 기반
    Rust: fluent (Mozilla) — 더 강력한 메시지 형식
"""

from __future__ import annotations

from string import Template

from i18napp.locale import get_locale

# ── 메시지 카탈로그 ── (학습용 인메모리)
# 운영은 `.po` 파일 + `gettext.translation()`
MESSAGES: dict[str, dict[str, str]] = {
    "en": {
        "greeting": "Hello, $name!",
        "items_one": "$count item",
        "items_other": "$count items",
        "validation.required": "$field is required",
        "validation.email": "$field must be a valid email",
        "validation.min_length": "$field must be at least $min characters",
        "order.created": "Order #$id placed for $total",
        "order.cancelled": "Order #$id was cancelled",
    },
    "ko": {
        "greeting": "안녕하세요, $name 님!",
        "items_one": "$count 개 항목",
        "items_other": "$count 개 항목",  # 한국어는 단복수 형태 같음
        "validation.required": "$field 은(는) 필수입니다",
        "validation.email": "$field 은(는) 유효한 이메일이어야 합니다",
        "validation.min_length": "$field 은(는) 최소 $min 자 이상이어야 합니다",
        "order.created": "주문 #$id 이(가) $total 으로 생성되었습니다",
        "order.cancelled": "주문 #$id 이(가) 취소되었습니다",
    },
    "ja": {
        "greeting": "こんにちは、$name さん!",
        "items_one": "$count 個のアイテム",
        "items_other": "$count 個のアイテム",
        "validation.required": "$field は必須です",
        "validation.email": "$field は有効なメールアドレスでなければなりません",
        "validation.min_length": "$field は最低 $min 文字必要です",
        "order.created": "注文 #$id が $total で作成されました",
        "order.cancelled": "注文 #$id がキャンセルされました",
    },
}

DEFAULT_LOCALE = "en"


def gettext(key: str, locale: str | None = None, **params: object) -> str:
    """`_(key, name="alice")` 같은 형식. 누락 키는 _key 자체_ 반환 (디버깅 친화)."""
    loc = locale or get_locale()
    catalog = MESSAGES.get(loc) or MESSAGES.get(loc.split("-")[0]) or MESSAGES[DEFAULT_LOCALE]
    template = catalog.get(key)
    if template is None:
        # _번역 누락 fallback_ ── 영어 시도, 그것도 없으면 key 자체
        template = MESSAGES[DEFAULT_LOCALE].get(key, key)
    return Template(template).safe_substitute(params)


# `_()` 별칭 ── gettext 표준 관용구
_ = gettext


def ngettext(
    singular_key: str,
    plural_key: str,
    n: int,
    locale: str | None = None,
    **params: object,
) -> str:
    """단복수 (`ngettext`) — 한국어는 형태 같지만, 영어 / 폴란드어 등은 _복잡_.

    실 운영은 ICU MessageFormat 또는 Babel 의 `ngettext` (`.po` 의 plural rules) 권장.
    학습 단순화: `n == 1` 이면 singular, 아니면 plural.
    """
    key = singular_key if n == 1 else plural_key
    return gettext(key, locale=locale, count=n, **params)
