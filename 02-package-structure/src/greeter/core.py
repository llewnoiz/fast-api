"""greeter 패키지의 _공개_ 비즈니스 로직.

Import 스타일:
    - 같은 패키지 안: **상대 import** `from ._internal import ...` 권장
    - 외부 패키지: **절대 import** `from greeter.core import ...` 권장

상대 import 의 장점:
    - 패키지를 다른 이름으로 재배치(rename)해도 안쪽 import 깨지지 않음
    - "이건 같은 패키지 내부 자산" 이라는 의도가 명확

상대 import 의 한계:
    - 깊이가 깊어지면 `..a.b.c` 같이 가독성 떨어짐 → 그땐 절대 import
    - 모듈을 _스크립트_ 로 직접 실행하면 작동 안 함 (`__main__` 일 때 패키지 컨텍스트 없음)
"""

from __future__ import annotations

from ._internal import greeting_for, normalize_name


def greet(name: str, *, locale: str = "ko") -> str:
    """기본 인사말 생성.

    >>> greet("alice", locale="en")
    'Hello, Alice!'
    """
    return f"{greeting_for(locale)}, {normalize_name(name)}!"


def shout(text: str) -> str:
    """대문자 + 느낌표.

    >>> shout("hello")
    'HELLO!!!'
    """
    return text.upper() + "!!!"


def make_card(name: str, lines: list[str], *, locale: str = "ko") -> str:
    """다중 줄 인사 카드.

    >>> print(make_card("alice", ["좋은 하루"], locale="ko"))
    안녕, Alice!
      좋은 하루
    """
    header = greet(name, locale=locale)
    body = "\n".join(f"  {line}" for line in lines)
    return f"{header}\n{body}" if body else header
