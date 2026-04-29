"""전역 예외 핸들러.

Spring `@ControllerAdvice` + `@ExceptionHandler`,
NestJS `@Catch() ExceptionFilter` 자리.

**핵심 규칙**: 라우트 함수에선 `raise OrderNotFoundError(...)` 만 하면 끝.
`HTTPException` 직접 만들지 _말 것_ — 도메인 예외 → 핸들러가 envelope 변환.

핸들러 우선순위:
    1. DomainError (우리 도메인)
    2. HTTPException (FastAPI 기본)
    3. RequestValidationError (Pydantic 검증 실패)
    4. Exception (catch-all, 운영에선 _자세한 메시지 노출 X_)
"""

from __future__ import annotations

import structlog
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from errver.envelope import ApiEnvelope
from errver.errors import DomainError, ErrorCode

log = structlog.get_logger()


def _to_response(envelope: ApiEnvelope[object], status_code: int) -> JSONResponse:
    return JSONResponse(status_code=status_code, content=envelope.model_dump())


def install_exception_handlers(app: FastAPI) -> None:
    """앱 팩토리에서 한 번 호출."""

    @app.exception_handler(DomainError)
    async def _domain(_req: Request, exc: DomainError) -> JSONResponse:
        # 도메인 예외 — _예측된_ 케이스. info 레벨 OK
        log.info("domain.error", code=exc.code.value, status=exc.status, message=exc.message)
        return _to_response(
            ApiEnvelope[object](code=exc.code.value, message=exc.message, data=None),
            status_code=exc.status,
        )

    @app.exception_handler(RequestValidationError)
    async def _validation(_req: Request, exc: RequestValidationError) -> JSONResponse:
        """Pydantic 검증 실패 — FastAPI 가 _기본_ 422 응답을 envelope 모양으로 갈음."""
        return _to_response(
            ApiEnvelope[object](
                code=ErrorCode.VALIDATION.value,
                message="request validation failed",
                data={"errors": exc.errors()},   # 어느 필드/규칙 실패인지 그대로 노출
            ),
            status_code=422,
        )

    @app.exception_handler(HTTPException)
    async def _http(_req: Request, exc: HTTPException) -> JSONResponse:
        """라우트가 직접 던진 HTTPException 도 envelope 으로 통일."""
        # detail 이 dict 면 _구조 보존_, 문자열이면 message 로
        msg = exc.detail if isinstance(exc.detail, str) else "http error"
        return _to_response(
            ApiEnvelope[object](
                code=f"HTTP_{exc.status_code}",
                message=msg,
                data=exc.detail if not isinstance(exc.detail, str) else None,
            ),
            status_code=exc.status_code,
        )

    @app.exception_handler(Exception)
    async def _unhandled(_req: Request, exc: Exception) -> JSONResponse:
        """예상 못 한 예외 — 운영에선 _내부 메시지 노출 X_, 로그만."""
        log.exception("unhandled.exception", error=repr(exc))
        return _to_response(
            ApiEnvelope[object](
                code=ErrorCode.INTERNAL.value,
                message="internal server error",
                data=None,
            ),
            status_code=500,
        )
