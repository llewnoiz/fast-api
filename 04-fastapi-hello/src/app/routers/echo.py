"""echo 라우터 — 요청/응답 모델 + 자동 검증 데모.

비교:
    Spring:   @PostMapping + @Valid @RequestBody DTO  (Lombok 으로 보일러플레이트 줄임)
    NestJS:   @Body() ValidationPipe + class-validator
    Express:  body-parser + 직접 검증 (보일러플레이트 많음)

이 라우트가 보여주는 것:
    1. 요청 본문(body) 을 Pydantic 모델로 _자동 파싱·검증_
    2. 검증 실패 시 _422 자동 응답_ — 우리 코드는 try/except 안 함
    3. OpenAPI `/docs` 에 요청·응답 스키마가 _자동 노출_
"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, status
from pydantic import BaseModel, Field

router = APIRouter(tags=["echo"])


class EchoRequest(BaseModel):
    """요청 본문. Field 의 제약이 OpenAPI 스키마에도 표시됨."""

    message: str = Field(min_length=1, max_length=200)
    repeat: int = Field(default=1, ge=1, le=10)


class EchoResponse(BaseModel):
    echoed: list[str]
    received_at: datetime


@router.post(
    "/echo",
    response_model=EchoResponse,
    status_code=status.HTTP_200_OK,
    summary="입력 메시지를 repeat 번 반향",
)
async def echo(payload: EchoRequest) -> EchoResponse:
    return EchoResponse(
        echoed=[payload.message] * payload.repeat,
        received_at=datetime.now(),
    )
