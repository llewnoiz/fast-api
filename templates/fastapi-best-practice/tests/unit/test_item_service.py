"""Item Service 단위 테스트 — UoW + Cache + Repo mock."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import pytest

from app.core.errors import ItemAccessDeniedError, ItemNotFoundError
from app.db.repository_base import Page
from app.schemas.items import ItemCreate, ItemUpdate
from app.services import items as service


@dataclass
class FakeUser:
    id: int
    username: str = "test"
    role: str = "user"


@dataclass
class FakeItem:
    id: int
    owner_id: int
    title: str
    description: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class FakeItemRepo:
    items: dict[int, FakeItem] = field(default_factory=dict)
    _next_id: int = 1

    async def add(
        self, *, owner_id: int, title: str, description: str | None
    ) -> FakeItem:
        item = FakeItem(
            id=self._next_id, owner_id=owner_id, title=title, description=description
        )
        self.items[item.id] = item
        self._next_id += 1
        return item

    async def get_or_404(self, item_id: int) -> FakeItem:
        item = self.items.get(item_id)
        if item is None:
            raise ItemNotFoundError()
        return item

    async def list_by_owner(
        self, owner_id: int, *, limit: int, offset: int
    ) -> Page[FakeItem]:
        all_items = sorted(
            (i for i in self.items.values() if i.owner_id == owner_id),
            key=lambda x: -x.id,
        )
        sliced = all_items[offset : offset + limit]
        return Page(
            items=sliced,
            total=len(all_items),
            limit=limit,
            offset=offset,
            has_next=offset + len(sliced) < len(all_items),
        )

    async def update(
        self,
        item: FakeItem,
        *,
        title: str | None = None,
        description: str | None = None,
    ) -> FakeItem:
        if title is not None:
            item.title = title
        if description is not None:
            item.description = description
        item.updated_at = datetime.now(UTC)
        return item

    async def delete(self, item: FakeItem) -> None:
        self.items.pop(item.id, None)


class FakeUoW:
    def __init__(self) -> None:
        self.items = FakeItemRepo()

    async def __aenter__(self) -> FakeUoW:
        return self

    async def __aexit__(self, *_args: Any) -> None:
        pass


@dataclass
class FakeCache:
    """ItemCache 인터페이스 흉내 — 호출 _횟수_ 만 추적."""

    set_calls: int = 0
    invalidate_item_calls: int = 0
    invalidate_user_items_calls: int = 0

    async def set_item(self, item_id: int, value: dict[str, Any]) -> None:
        self.set_calls += 1

    async def invalidate_item(self, item_id: int) -> None:
        self.invalidate_item_calls += 1

    async def invalidate_user_items(self, user_id: int) -> None:
        self.invalidate_user_items_calls += 1


# ── tests ──


async def test_create_item_invalidates_user_items_cache() -> None:
    uow = FakeUoW()
    cache = FakeCache()
    owner = FakeUser(id=1)

    item = await service.create_item(
        uow, cache, owner=owner, payload=ItemCreate(title="x")
    )

    assert item.owner_id == 1
    assert item.title == "x"
    assert cache.invalidate_user_items_calls == 1


async def test_get_item_owner_guard_passes() -> None:
    uow = FakeUoW()
    cache = FakeCache()
    owner = FakeUser(id=1)
    await service.create_item(
        uow, cache, owner=owner, payload=ItemCreate(title="my")
    )

    item = await service.get_item(uow, cache, owner=owner, item_id=1)
    assert item.id == 1
    # cache set 호출됨
    assert cache.set_calls == 1


async def test_get_item_other_user_blocked() -> None:
    """다른 사용자의 item GET → ItemAccessDeniedError (IDOR 방어)."""
    uow = FakeUoW()
    cache = FakeCache()
    alice = FakeUser(id=1)
    bob = FakeUser(id=2)
    await service.create_item(
        uow, cache, owner=alice, payload=ItemCreate(title="alice's")
    )

    with pytest.raises(ItemAccessDeniedError):
        await service.get_item(uow, cache, owner=bob, item_id=1)


async def test_get_unknown_item_raises_404() -> None:
    uow = FakeUoW()
    with pytest.raises(ItemNotFoundError):
        await service.get_item(uow, FakeCache(), owner=FakeUser(id=1), item_id=99)


async def test_update_item_partial_only_changes_provided() -> None:
    uow = FakeUoW()
    cache = FakeCache()
    owner = FakeUser(id=1)
    await service.create_item(
        uow, cache, owner=owner, payload=ItemCreate(title="orig", description="d1")
    )

    updated = await service.update_item(
        uow,
        cache,
        owner=owner,
        item_id=1,
        payload=ItemUpdate(description="new desc"),  # title 안 보냄
    )
    assert updated.title == "orig"  # 변경 X
    assert updated.description == "new desc"
    # update 에서 단일 캐시 1번, user 목록 1번 (create 1번 + update 1번 = 2)
    assert cache.invalidate_item_calls == 1
    assert cache.invalidate_user_items_calls == 2


async def test_update_other_user_blocked() -> None:
    uow = FakeUoW()
    cache = FakeCache()
    alice = FakeUser(id=1)
    bob = FakeUser(id=2)
    await service.create_item(
        uow, cache, owner=alice, payload=ItemCreate(title="alice's")
    )
    with pytest.raises(ItemAccessDeniedError):
        await service.update_item(
            uow, cache, owner=bob, item_id=1, payload=ItemUpdate(title="hacked")
        )


async def test_delete_item_owner_pass() -> None:
    uow = FakeUoW()
    cache = FakeCache()
    owner = FakeUser(id=1)
    await service.create_item(
        uow, cache, owner=owner, payload=ItemCreate(title="x")
    )

    await service.delete_item(uow, cache, owner=owner, item_id=1)
    # 정말 사라졌는지
    with pytest.raises(ItemNotFoundError):
        await service.get_item(uow, cache, owner=owner, item_id=1)


async def test_delete_other_user_blocked() -> None:
    uow = FakeUoW()
    cache = FakeCache()
    alice = FakeUser(id=1)
    bob = FakeUser(id=2)
    await service.create_item(
        uow, cache, owner=alice, payload=ItemCreate(title="alice's")
    )
    with pytest.raises(ItemAccessDeniedError):
        await service.delete_item(uow, cache, owner=bob, item_id=1)


async def test_list_my_items_returns_only_own() -> None:
    uow = FakeUoW()
    cache = FakeCache()
    alice = FakeUser(id=1)
    bob = FakeUser(id=2)

    await service.create_item(
        uow, cache, owner=alice, payload=ItemCreate(title="a1")
    )
    await service.create_item(
        uow, cache, owner=alice, payload=ItemCreate(title="a2")
    )
    await service.create_item(
        uow, cache, owner=bob, payload=ItemCreate(title="b1")
    )

    page = await service.list_my_items(uow, owner=alice, limit=10, offset=0)
    assert page.total == 2
    assert all(i.owner_id == 1 for i in page.items)
