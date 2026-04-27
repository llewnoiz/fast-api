"""내부 헬퍼 — 외부에 노출되지 않는 모듈.

관용: 모듈명에 `_` 접두를 붙이면 "이 모듈은 패키지 내부 전용" 이라는 신호.
강제 X. 그래도 IDE / linter 가 외부 import 시 경고를 띄움.

Java 비교: package-private 가 정확한 대응 (public 선언 안 한 것).
"""

from __future__ import annotations


def normalize_name(raw: str) -> str:
    """이름 다듬기 — 공백 제거, Title Case."""
    return raw.strip().title()


# 다국어 인사말 — 다국어 처리 본격은 부록 A1 단계에서 다룸.
_GREETINGS: dict[str, str] = {
    "ko": "안녕",
    "en": "Hello",
    "ja": "こんにちは",
}


def greeting_for(locale: str) -> str:
    """locale 코드 → 인사말. 모르는 locale 은 영어로 폴백."""
    return _GREETINGS.get(locale, _GREETINGS["en"])
