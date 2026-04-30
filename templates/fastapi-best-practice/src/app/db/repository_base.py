"""BaseRepo[T] — 모든 Repository 의 공통 CRUD + 페이지네이션.

설계 원칙:
    - **PEP 695 generic** (`class BaseRepo[T: Base]`) ── 타입 안전 + 보일러플레이트 ↓
    - **선언적 model** ── 자식이 `model = User` 한 줄로 바인딩
    - **선언적 not_found_error** ── 도메인 특화 예외 (`UserNotFoundError`) 매핑
    - 도메인 _특화_ 쿼리는 자식 Repo 에 (예: `UserRepo.get_by_email`)
    - 80% 의 단순 CRUD 는 _베이스_ 가 처리 → 새 도메인 추가가 5 줄

새 도메인 Repo 작성 흐름:
    1. `db/models.py` 에 모델 추가
    2. `core/errors.py` 에 `XxxNotFoundError` 추가 (선택 — `NotFoundError` 그대로 써도 OK)
    3. `domain/xxx/repository.py`:
       ```python
       class XxxRepo(BaseRepo[Xxx]):
           model = Xxx
           not_found_error = XxxNotFoundError
           # 도메인 특화 쿼리만 여기
       ```
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel
from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.db.base import Base


@dataclass(frozen=True, slots=True)
class Page[T]:
    """페이지네이션 _내부_ 결과 (Repository 반환).

    응답으로 _그대로_ 직렬화하려면 `PageResponse[XxxPublic]` (Pydantic) 로 변환:
        Page[Item] (ORM) → PageResponse[ItemPublic] (Pydantic)

    dataclass 인 이유: ORM 객체 (Item 등) 를 _그대로_ 담아도 Pydantic schema 검증 안 거침.
    Pydantic 가 generic + ORM 조합에서 까다로워 _내부 표현은 분리_.
    """

    items: list[T]
    total: int
    limit: int
    offset: int
    has_next: bool


class PageResponse[T](BaseModel):
    """페이지네이션 _응답_ 모델 — `response_model=ApiEnvelope[PageResponse[XxxPublic]]`.

    T 는 _Pydantic_ 타입이어야 (ItemPublic 등). OpenAPI 스키마 정상 생성.
    라우터에서 `Page[Item]` → `PageResponse[ItemPublic]` 로 _명시 변환_.
    """

    items: list[T]
    total: int
    limit: int
    offset: int
    has_next: bool

    @classmethod
    def from_page[U](
        cls, page: Page[U], *, transform: Callable[[U], T]  # noqa: F821
    ) -> PageResponse[T]:
        """`Page[OrmModel]` → `PageResponse[Pydantic]` 변환 헬퍼."""
        return cls(
            items=[transform(i) for i in page.items],
            total=page.total,
            limit=page.limit,
            offset=page.offset,
            has_next=page.has_next,
        )


from collections.abc import Callable  # noqa: E402, I001 — forward ref


class BaseRepo[T: Base]:
    """공통 CRUD. 자식이 `model` (필수) + `not_found_error` (선택) 클래스 속성 바인딩.

    `update`/`delete` 는 _ORM 객체_ 인자 ── 호출자가 _이미 owner 가드_ 등 검사 후 전달.
    `get_or_404` 는 도메인 특화 NotFoundError 발생 (자식이 `not_found_error` 안 정하면 일반 NotFoundError).
    """

    model: type[T]
    not_found_error: type[NotFoundError] = NotFoundError

    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    # ── 생성 ────────────────────────────────────────────────────
    async def add(self, **fields: Any) -> T:
        """`**fields` 가 모델 생성자에 그대로 전달. flush 까지만 (UoW 가 commit)."""
        obj = self.model(**fields)
        self._s.add(obj)
        await self._s.flush()
        return obj

    # ── 조회 ────────────────────────────────────────────────────
    async def get(self, id_: int) -> T | None:
        return await self._s.get(self.model, id_)

    async def get_or_404(self, id_: int) -> T:
        obj = await self.get(id_)
        if obj is None:
            raise self.not_found_error()
        return obj

    async def list_(
        self, *, limit: int = 50, offset: int = 0, where: Any = None
    ) -> Page[T]:
        """단순 페이지네이션. `where` 인자로 도메인 필터 추가 가능 (`User.role == "admin"`).

        Note: SQL 키워드 충돌 방지로 메서드명은 `list_` (Python builtin `list` 와 다름).
        """
        return await self._paginate(self._base_select(where), limit=limit, offset=offset)

    # ── 수정 / 삭제 ─────────────────────────────────────────────
    async def update(self, obj: T, **fields: Any) -> T:
        """None 이 아닌 필드만 _부분 업데이트_ (PATCH 의미). flush + refresh 후 반환.

        refresh 는 server-side `onupdate=func.now()` 같은 컬럼이 _현재 값_ 으로 채워지도록.
        """
        for key, value in fields.items():
            if value is not None:
                setattr(obj, key, value)
        await self._s.flush()
        await self._s.refresh(obj)
        return obj

    async def delete(self, obj: T) -> None:
        await self._s.delete(obj)
        await self._s.flush()

    # ── 도우미 (자식이 도메인 쿼리 작성 시 재사용) ──────────────
    def _base_select(self, where: Any = None) -> Select[tuple[T]]:
        stmt = select(self.model)
        if where is not None:
            stmt = stmt.where(where)
        return stmt

    async def _paginate(
        self, stmt: Select[tuple[T]], *, limit: int, offset: int
    ) -> Page[T]:
        """주어진 SELECT 문에 LIMIT/OFFSET 적용 + total count.

        운영 주의: `count(*) OVER ()` 윈도우 함수가 _같은 쿼리_ 로 합치는 게 더 빠름 (1 round-trip).
        본 구현은 학습 단순성을 위해 _2 round-trip_ (rows + count). 큰 테이블에선 윈도우 함수 권장.
        """
        # count
        count_stmt = select(func.count()).select_from(stmt.order_by(None).subquery())
        total = (await self._s.execute(count_stmt)).scalar_one()

        # rows
        rows_stmt = stmt.limit(limit).offset(offset)
        rows = list((await self._s.execute(rows_stmt)).scalars().all())

        return Page(
            items=rows,
            total=total,
            limit=limit,
            offset=offset,
            has_next=offset + len(rows) < total,
        )
