"""06 모듈 데모용 헬퍼.

`_` 접두 모듈명: 관용적으로 _내부 사용_ 임을 표시.
"""

from __future__ import annotations


def greet(name: str) -> str:
    return f"안녕, {name}!"


def shout(text: str) -> str:
    return text.upper() + "!!!"
