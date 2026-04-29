"""fastapi-common — 사내 공통 FastAPI 유틸.

`__init__.py` 가 _공개 API 표면_ 이다. 내부 구조 (envelope.py / errors.py 등)는
바꿔도 사용자는 `from fastapi_common import ApiEnvelope, ErrorCode` 로 안전.

비교:
    npm 패키지: index.ts 가 export
    Java:       module-info.java
    Rust:       lib.rs

버전 정책:
    SemVer (https://semver.org/lang/ko/)
    - MAJOR (2.x → 3.0): 깨짐 변경. 사용자 코드 수정 필요.
    - MINOR (2.1 → 2.2): 기능 추가, 하위 호환.
    - PATCH (2.1.0 → 2.1.1): 버그 수정만.
"""

from __future__ import annotations

__version__ = "0.1.0"

from fastapi_common.correlation import (
    REQUEST_ID_HEADER,
    CorrelationIdMiddleware,
    install_correlation_middleware,
)
from fastapi_common.envelope import ApiEnvelope, success
from fastapi_common.errors import DomainError, ErrorCode
from fastapi_common.handlers import install_exception_handlers
from fastapi_common.http_client import ResilientClient, make_breaker_factory
from fastapi_common.logging_setup import configure_logging

__all__ = [
    "REQUEST_ID_HEADER",
    "ApiEnvelope",
    "CorrelationIdMiddleware",
    "DomainError",
    "ErrorCode",
    "ResilientClient",
    "__version__",
    "configure_logging",
    "install_correlation_middleware",
    "install_exception_handlers",
    "make_breaker_factory",
    "success",
]
