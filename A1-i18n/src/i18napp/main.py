"""FastAPI 앱 — 다국어 데모.

엔드포인트:
    GET  /healthz                    헬스체크
    GET  /greet?name=alice           greeting (locale 별 다름)
    GET  /items?n=5                  복수형 데모 (ngettext)
    POST /orders                     검증 메시지 다국어 (Pydantic)
    GET  /money?amount=1234&cur=KRW  Babel 통화 포맷
    GET  /date                       Babel 날짜 포맷
    GET  /lang                       현재 locale
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr, Field, ValidationError

from i18napp.babel_setup import (
    display_locale_name,
    format_d,
    format_dt,
    format_money,
)
from i18napp.catalog import gettext, ngettext
from i18napp.locale import get_locale
from i18napp.middleware import LocaleMiddleware
from i18napp.pydantic_messages import translate_validation_error

SUPPORTED = ["en", "ko", "ja"]


class CreateOrder(BaseModel):
    name: str = Field(min_length=2)
    email: EmailStr
    amount: int = Field(ge=1)


def create_app() -> FastAPI:
    app = FastAPI(title="A1 — 다국어 (i18n)")
    app.add_middleware(LocaleMiddleware, supported=SUPPORTED, default="en")

    @app.exception_handler(ValidationError)
    async def validation_handler(_request: Request, exc: ValidationError) -> JSONResponse:
        # Pydantic 에러를 _현재 locale_ 로 번역
        errors = translate_validation_error(exc)
        return JSONResponse(status_code=400, content={"errors": errors})

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/greet")
    async def greet(name: str) -> dict[str, str]:
        return {"message": gettext("greeting", name=name)}

    @app.get("/items")
    async def items(n: int) -> dict[str, str]:
        return {"message": ngettext("items_one", "items_other", n)}

    @app.post("/orders")
    async def create_order(payload: dict[str, Any]) -> dict[str, str]:
        # 수동 검증 → ValidationError handler 가 다국어 에러 반환
        try:
            order = CreateOrder.model_validate(payload)
        except ValidationError as e:
            # 명시적으로 핸들러로
            raise HTTPException(
                status_code=400,
                detail={"errors": translate_validation_error(e)},
            ) from e
        return {
            "message": gettext(
                "order.created",
                id="42",
                total=format_money(order.amount, "KRW", get_locale()),
            )
        }

    @app.get("/money")
    async def money(amount: float, cur: str = "USD") -> dict[str, str]:
        return {"formatted": format_money(amount, cur, get_locale())}

    @app.get("/date")
    async def show_date() -> dict[str, str]:
        now = datetime.now()
        return {
            "date": format_d(now.date(), locale=get_locale()),
            "datetime": format_dt(now, locale=get_locale()),
        }

    @app.get("/lang")
    async def lang() -> dict[str, str]:
        loc = get_locale()
        return {
            "locale": loc,
            "display_self": display_locale_name(loc, in_locale=loc),
            "display_en": display_locale_name(loc, in_locale="en"),
        }

    return app


app = create_app()
