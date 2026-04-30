"""Items 라우터 — CRUD, 모두 인증 + owner 가드."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, status

from app.core.envelope import ApiEnvelope, success
from app.db.models import User
from app.db.repository_base import PageResponse
from app.db.uow import UnitOfWork
from app.deps.auth import get_current_user, get_uow
from app.domain.items import service
from app.domain.items.schemas import ItemCreate, ItemPublic, ItemUpdate

router = APIRouter(prefix="/items", tags=["items"])


def _cache(request: Request):
    """라우트에서 cache 추출 헬퍼."""
    return request.app.state.cache


@router.post(
    "",
    response_model=ApiEnvelope[ItemPublic],
    status_code=status.HTTP_201_CREATED,
)
async def create_item(
    payload: ItemCreate,
    request: Request,
    current: Annotated[User, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> ApiEnvelope[ItemPublic]:
    item = await service.create_item(uow, _cache(request), owner=current, payload=payload)
    return success(ItemPublic.model_validate(item), message="created")


@router.get("", response_model=ApiEnvelope[PageResponse[ItemPublic]])
async def list_items(
    current: Annotated[User, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> ApiEnvelope[PageResponse[ItemPublic]]:
    page = await service.list_my_items(uow, owner=current, limit=limit, offset=offset)
    return success(
        PageResponse[ItemPublic].from_page(page, transform=ItemPublic.model_validate)
    )


@router.get("/{item_id}", response_model=ApiEnvelope[ItemPublic])
async def get_item(
    item_id: int,
    request: Request,
    current: Annotated[User, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> ApiEnvelope[ItemPublic]:
    item = await service.get_item(uow, _cache(request), owner=current, item_id=item_id)
    return success(ItemPublic.model_validate(item))


@router.put("/{item_id}", response_model=ApiEnvelope[ItemPublic])
async def update_item(
    item_id: int,
    payload: ItemUpdate,
    request: Request,
    current: Annotated[User, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> ApiEnvelope[ItemPublic]:
    item = await service.update_item(
        uow, _cache(request), owner=current, item_id=item_id, payload=payload
    )
    return success(ItemPublic.model_validate(item))


@router.delete(
    "/{item_id}",
    response_model=ApiEnvelope[None],
    status_code=status.HTTP_200_OK,
)
async def delete_item(
    item_id: int,
    request: Request,
    current: Annotated[User, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> ApiEnvelope[None]:
    await service.delete_item(uow, _cache(request), owner=current, item_id=item_id)
    return success(None, message="deleted")
