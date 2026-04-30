"""Locale negotiation — `Accept-Language` 헤더 → 지원 locale 중 최선.

RFC 4647 (Matching of Language Tags):
    클라이언트:  `Accept-Language: ko-KR,ko;q=0.9,en;q=0.8,*;q=0.5`
    서버: 지원 locale (예: ko, en, ja) 중 _가장 잘 맞는_ 하나 선택.

규칙:
    1. q-value 큰 것 우선
    2. 정확 매치 (`ko-KR`) 우선, 없으면 prefix 매치 (`ko`)
    3. 없으면 default
"""

from __future__ import annotations

import contextlib
import contextvars
from dataclasses import dataclass


@dataclass(frozen=True)
class LangTag:
    """`ko-KR;q=0.9` → tag="ko-KR", q=0.9."""

    tag: str
    quality: float

    @property
    def primary(self) -> str:
        """`ko-KR` → `ko`."""
        return self.tag.split("-")[0].lower()


def parse_accept_language(header: str | None) -> list[LangTag]:
    """`ko-KR,ko;q=0.9,en;q=0.8` → 정렬된 LangTag 리스트.

    잘못된 부분은 _조용히 무시_. 헤더 없으면 빈 리스트.
    """
    if not header:
        return []
    tags: list[LangTag] = []
    for part in header.split(","):
        part = part.strip()
        if not part:
            continue
        tag, _, params = part.partition(";")
        tag = tag.strip()
        if not tag:
            continue
        quality = 1.0
        for param in params.split(";"):
            param = param.strip()
            if param.startswith("q="):
                with contextlib.suppress(ValueError):
                    quality = float(param[2:])
        tags.append(LangTag(tag=tag, quality=quality))
    # q 내림차순, 동일 q 면 _원래 순서_ 유지
    tags.sort(key=lambda t: -t.quality)
    return tags


def negotiate_locale(
    header: str | None,
    *,
    supported: list[str],
    default: str,
) -> str:
    """클라이언트 Accept-Language + 지원 locale → 최선 매치.

    `supported` 는 `["ko", "en", "ja"]` 형식 — 본 모듈은 _primary subtag_ 만 비교.
    """
    if not supported:
        return default
    candidates = parse_accept_language(header)
    supported_set = {s.lower() for s in supported}

    for cand in candidates:
        # 1) 정확 매치 (ko-KR == ko-KR)
        if cand.tag.lower() in supported_set:
            return cand.tag.lower()
        # 2) primary 매치 (ko-KR → ko)
        if cand.primary in supported_set:
            return cand.primary
        # 3) `*` wildcard → 첫 supported
        if cand.tag == "*":
            return supported[0]
    return default


# ── contextvars 기반 _요청 단위_ locale 저장 ──
_current_locale: contextvars.ContextVar[str] = contextvars.ContextVar(
    "current_locale", default="en"
)


def set_locale(locale: str) -> None:
    """미들웨어가 호출 — 요청 시작 시점에."""
    _current_locale.set(locale)


def get_locale() -> str:
    """리졸버 / 라우트가 호출 — 현재 요청의 locale."""
    return _current_locale.get()
