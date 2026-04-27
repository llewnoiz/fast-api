"""06 — 모듈 / 패키지 / import.

- 모듈 = .py 파일 하나
- 패키지 = `__init__.py` 가 있는 디렉토리
- 같은 src/ 안의 다른 모듈을 import 해본다
"""

from __future__ import annotations

# 절대 import: 가장 명시적이고 권장 (PEP 328)
# 같은 src 패키지 안의 모듈을 가져온다.
# 실행 방식에 따라 모듈 경로가 다를 수 있어 try/except 로 폴백.
# try:
import _helpers  # `python -m src.s06_modules` 실행 시
# except ImportError:
#     import os
#     import sys

#     # 직접 `python src/s06_modules.py` 실행 시 src/ 를 sys.path 에 추가
#     sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
#     import _helpers  # type: ignore[no-redef,import-not-found]


def main() -> None:
    print("=== 모듈 import ===")
    print("greet:", _helpers.greet("Alice"))
    print("upper:", _helpers.shout("hello"))
    print("module name:", _helpers.__name__)
    print("module file:", _helpers.__file__)

    print("\n=== if __name__ == '__main__' 가드 ===")
    print(f"이 파일이 직접 실행되면 __name__ == '__main__' → 현재: {__name__!r}")


if __name__ == "__main__":
    main()
