"""Items 라우터 — CRUD, 모두 인증 + owner 가드.

cross-domain 시연 — `GET /items/{id}/detail` 응답에 owner 정보 포함 (Layered 구조의 가치).
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, status

from app.core.envelope import ApiEnvelope, success
from app.db.uow import UnitOfWork
from app.deps.auth import get_current_user, get_uow
from app.models import User
from app.repositories._base import PageResponse
from app.schemas.items import ItemCreate, ItemDetail, ItemPublic, ItemUpdate
from app.services import items_service as item_service

router = APIRouter(prefix="/items", tags=["items"])


def _cache(request: Request):
    """라우트에서 cache 추출 헬퍼."""
    return request.app.state.cache


@router.post(
    "",
    response_model=ApiEnvelope[ItemPublic],
    status_code=status.HTTP_201_CREATED,
    summary="아이템 생성",
)
async def create_item(
    payload: ItemCreate,
    request: Request,
    current: Annotated[User, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> ApiEnvelope[ItemPublic]:
    item = await item_service.create_item(
        uow, _cache(request), owner=current, payload=payload
    )
    return success(ItemPublic.model_validate(item), message="created")


@router.get(
    "",
    response_model=ApiEnvelope[PageResponse[ItemPublic]],
    summary="본인 아이템 목록",
)
async def list_items(
    current: Annotated[User, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> ApiEnvelope[PageResponse[ItemPublic]]:
    page = await item_service.list_my_items(
        uow, owner=current, limit=limit, offset=offset
    )
    return success(
        PageResponse[ItemPublic].from_page(page, transform=ItemPublic.model_validate)
    )


@router.get(
    "/{item_id}",
    response_model=ApiEnvelope[ItemPublic],
    summary="단건 조회",
)
async def get_item(
    item_id: int,
    request: Request,
    current: Annotated[User, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> ApiEnvelope[ItemPublic]:
    item = await item_service.get_item(
        uow, _cache(request), owner=current, item_id=item_id
    )
    return success(ItemPublic.model_validate(item))


@router.get(
    "/{item_id}/detail",
    response_model=ApiEnvelope[ItemDetail],
    summary="단건 + owner 정보 (cross-domain 시연)",
)
async def get_item_detail(
    item_id: int,
    current: Annotated[User, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> ApiEnvelope[ItemDetail]:
    """Layered 구조의 cross-domain 패턴 — `selectinload(Item.owner)` 로 1 query 에 owner 까지 로드.

    이 엔드포인트가 `repository.get_with_owner` 호출 → ItemDetail 변환 (owner 포함).
    """
    from app.core.errors import ItemAccessDeniedError  # noqa: PLC0415

    async with uow:
        item = await uow.items.get_with_owner(item_id)
        if item.owner_id != current.id:
            raise ItemAccessDeniedError()
        return success(ItemDetail.model_validate(item))


@router.put(
    "/{item_id}",
    response_model=ApiEnvelope[ItemPublic],
    summary="부분 업데이트 (owner 만)",
)
async def update_item(
    item_id: int,
    payload: ItemUpdate,
    request: Request,
    current: Annotated[User, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> ApiEnvelope[ItemPublic]:
    item = await item_service.update_item(
        uow, _cache(request), owner=current, item_id=item_id, payload=payload
    )
    return success(ItemPublic.model_validate(item))


@router.delete(
    "/{item_id}",
    response_model=ApiEnvelope[None],
    status_code=status.HTTP_200_OK,
    summary="삭제 (owner 만)",
)
async def delete_item(
    item_id: int,
    request: Request,
    current: Annotated[User, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> ApiEnvelope[None]:
    await item_service.delete_item(
        uow, _cache(request), owner=current, item_id=item_id
    )
    return success(None, message="deleted")
