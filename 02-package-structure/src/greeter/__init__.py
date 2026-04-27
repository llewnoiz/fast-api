"""greeter — 인사말 생성 미니 라이브러리 (02 단계 학습용 패키지).

`__init__.py` 의 역할:
    1. 디렉토리를 _패키지_ 로 등록 (3.3+ 에선 빈 폴더도 namespace package 지만,
       명시 패키지가 도구 호환성 더 좋음).
    2. **공개 API 표면(surface)** 을 정의 — 외부에서 `from greeter import greet` 하면
       core.py 의 `greet` 가 보임.
    3. `__version__`, `__all__` 같은 메타데이터 노출.

Java 비교: `package-info.java` + 패키지 레벨 `public` 함수 export 의 자리.
"""

from __future__ import annotations

from greeter.core import greet, make_card, shout

__version__ = "0.1.0"

# `from greeter import *` 시 노출되는 이름. `*` import 자체는 권장 X 지만
# 명시적인 공개 API 목록 역할도 함 (linter/IDE 가 참고).
__all__ = ["greet", "make_card", "shout", "__version__"]
