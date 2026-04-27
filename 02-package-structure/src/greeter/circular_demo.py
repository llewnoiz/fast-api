"""순환 import 안티패턴과 회피 전략 데모 (실행해보지 _말고_ 읽기만)."""

from __future__ import annotations

# ============================================================================
# 안티패턴 — 순환 import (실제로 만들면 ImportError)
# ============================================================================
#
# # a.py
# from greeter.b import b_func
# def a_func() -> str:
#     return b_func()
#
# # b.py
# from greeter.a import a_func   # ← a 가 b 를, b 가 a 를 import → 순환
# def b_func() -> str:
#     return a_func()
#
# 첫 import 시점에 모듈이 _아직 로딩 중_ 인 상태에서 다른 import 가 들어와서
# `ImportError: cannot import name 'a_func' from partially initialized module`
# ============================================================================


# ============================================================================
# 회피 전략 1 — 의존성 역전: 공통 의존성을 _제3 모듈_ 로 추출
# ============================================================================
#
# # types.py (a, b 둘 다 의존)
# from typing import Protocol
# class Greeter(Protocol):
#     def greet(self) -> str: ...
#
# # a.py
# from .types import Greeter   # ← 양쪽이 공통 모듈만 의존
#
# # b.py
# from .types import Greeter
# ============================================================================


# ============================================================================
# 회피 전략 2 — 지연(lazy) import: 함수 _안에서_ import
# ============================================================================
#
# # a.py
# def a_func() -> str:
#     from .b import b_func   # ← 모듈 로딩 시점이 아니라 호출 시점에 import
#     return b_func()
# ============================================================================


# ============================================================================
# 회피 전략 3 — TYPE_CHECKING: 타입 힌트만 필요한 경우
# ============================================================================
#
# from typing import TYPE_CHECKING
# if TYPE_CHECKING:                    # 런타임엔 False, mypy 분석 시에만 True
#     from .heavy_module import HeavyType
#
# def f(x: "HeavyType") -> None:        # 문자열 forward reference
#     ...
#
# `from __future__ import annotations` 가 있으면 모든 어노테이션이 자동으로
# 문자열이 되므로 TYPE_CHECKING 가드 없이도 동작 (가장 깔끔).
# ============================================================================
