"""전역 예외 핸들러 — 07 단계에서 추출."""

from __future__ import annotations

import structlog
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from fastapi_common.envelope import ApiEnvelope
from fastapi_common.errors import DomainError, ErrorCode

log = structlog.get_logger()


def _to_response(envelope: ApiEnvelope[object], status_code: int) -> JSONResponse:
    return JSONResponse(status_code=status_code, content=envelope.model_dump())


def install_exception_handlers(app: FastAPI) -> None:
    """앱 팩토리에서 한 번 호출."""

    @app.exception_handler(DomainError)
    async def _domain(_req: Request, exc: DomainError) -> JSONResponse:
        log.info("domain.error", code=exc.code, status=exc.status, message=exc.message)
        return _to_response(
            ApiEnvelope[object](code=exc.code, message=exc.message, data=None),
            status_code=exc.status,
        )

    @app.exception_handler(RequestValidationError)
    async def _validation(_req: Request, exc: RequestValidationError) -> JSONResponse:
        return _to_response(
            ApiEnvelope[object](
                code=ErrorCode.VALIDATION.value,
                message="request validation failed",
                data={"errors": exc.errors()},
            ),
            status_code=422,
        )

    @app.exception_handler(HTTPException)
    async def _http(_req: Request, exc: HTTPException) -> JSONResponse:
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
        log.exception("unhandled.exception", error=repr(exc))
        return _to_response(
            ApiEnvelope[object](
                code=ErrorCode.INTERNAL.value,
                message="internal server error",
                data=None,
            ),
            status_code=500,
        )
