"""Item Repository — BaseRepo[Item] 상속 + 소유자별 목록 + cross-domain 쿼리.

Layered 구조이므로 _다른 모델 (User 등)_ 자유 import 가능. owner 정보 포함 조회 등은
이 repository 가 _직접_ join 작성 가능 — 격리 신화 없음.
"""

from __future__ import annotations

from sqlalchemy.orm import selectinload

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

    async def get_with_owner(self, item_id: int) -> Item:
        """`Item.owner` (User) 까지 eager load — Layered 구조에서 cross-relation 자유.

        응답에 owner 정보 포함 시 사용. `selectinload` 가 N+1 회피.
        """
        stmt = self._base_select(Item.id == item_id).options(selectinload(Item.owner))
        item = (await self._s.execute(stmt)).scalar_one_or_none()
        if item is None:
            raise self.not_found_error()
        return item
