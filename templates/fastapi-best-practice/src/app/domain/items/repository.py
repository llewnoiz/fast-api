"""Item Repository — BaseRepo[Item] 상속 + 소유자별 목록만 도메인 특화."""

from __future__ import annotations

from app.core.errors import ItemNotFoundError
from app.db.models import Item
from app.db.repository_base import BaseRepo, Page


class ItemRepo(BaseRepo[Item]):
    model = Item
    not_found_error = ItemNotFoundError

    async def list_by_owner(
        self, owner_id: int, *, limit: int = 50, offset: int = 0
    ) -> Page[Item]:
        """소유자 필터 + 최신순. BaseRepo 의 _base_select / _paginate 헬퍼 재사용."""
        stmt = self._base_select(Item.owner_id == owner_id).order_by(Item.id.desc())
        return await self._paginate(stmt, limit=limit, offset=offset)
