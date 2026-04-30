"""Items Application Service — CRUD + owner 권한 가드 + cache invalidate.

owner 가드 = IDOR (CWE-639) 방어 ── _모든_ 단일 조회/수정/삭제에서 호출 필수.
BaseRepo[T] 의 `get_or_404` 가 NotFound 자동 처리.
"""

from __future__ import annotations

from app.cache.client import ItemCache
from app.core.errors import ItemAccessDeniedError
from app.db.models import Item, User
from app.db.repository_base import Page
from app.db.uow import UnitOfWork
from app.domain.items.schemas import ItemCreate, ItemPublic, ItemUpdate


def _to_dict(item: Item) -> dict:
    return ItemPublic.model_validate(item).model_dump(mode="json")


def _assert_owner(item: Item, user: User) -> None:
    if item.owner_id != user.id:
        raise ItemAccessDeniedError()


async def create_item(
    uow: UnitOfWork, cache: ItemCache, *, owner: User, payload: ItemCreate
) -> Item:
    async with uow:
        item = await uow.items.add(
            owner_id=owner.id, title=payload.title, description=payload.description
        )
    # commit 후 _목록 캐시 무효화_
    await cache.invalidate_user_items(owner.id)
    return item


async def get_item(
    uow: UnitOfWork, cache: ItemCache, *, owner: User, item_id: int
) -> Item:
    """단일 조회 + owner 가드 + 캐시 set."""
    async with uow:
        item = await uow.items.get_or_404(item_id)
        _assert_owner(item, owner)
        await cache.set_item(item.id, _to_dict(item))
        return item


async def list_my_items(
    uow: UnitOfWork, *, owner: User, limit: int = 50, offset: int = 0
) -> Page[Item]:
    async with uow:
        return await uow.items.list_by_owner(owner.id, limit=limit, offset=offset)


async def update_item(
    uow: UnitOfWork,
    cache: ItemCache,
    *,
    owner: User,
    item_id: int,
    payload: ItemUpdate,
) -> Item:
    async with uow:
        item = await uow.items.get_or_404(item_id)
        _assert_owner(item, owner)
        item = await uow.items.update(
            item, title=payload.title, description=payload.description
        )
    await cache.invalidate_item(item.id)
    await cache.invalidate_user_items(owner.id)
    return item


async def delete_item(
    uow: UnitOfWork, cache: ItemCache, *, owner: User, item_id: int
) -> None:
    async with uow:
        item = await uow.items.get_or_404(item_id)
        _assert_owner(item, owner)
        await uow.items.delete(item)
    await cache.invalidate_item(item_id)
    await cache.invalidate_user_items(owner.id)
