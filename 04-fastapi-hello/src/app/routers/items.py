"""items 라우터 — path/query 파라미터 + Pydantic 응답 모델.

비교:
    Spring:    @RestController + @GetMapping("/items/{id}") + @RequestParam
    NestJS:    @Controller("items") + @Get(":id") + @Query()
    Express:   app.get("/items/:id", (req, res) => ...) + req.query

FastAPI 의 _마법_:
    - path 파라미터 (`{id}`) 와 query 파라미터 (함수 인자) 를 _타입 힌트_ 로 자동 구분
    - Pydantic 모델 반환 시 OpenAPI 스키마 자동 생성
    - 검증 실패하면 _422 자동 응답_ (직접 try/except 불필요)

이 모듈은 _학습용 인메모리 데이터_. 10 단계에서 SQLAlchemy 로 교체.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

router = APIRouter(prefix="/items", tags=["items"])


# ============================================================================
# 응답 모델 — `response_model=` 으로 라우트에 바인딩
# ============================================================================


class Item(BaseModel):
    id: int
    name: str
    price: float = Field(ge=0)
    in_stock: bool = True


# ============================================================================
# 학습용 인메모리 저장소 (10 단계에서 DB 로 교체)
# ============================================================================


_DB: dict[int, Item] = {
    1: Item(id=1, name="Pencil", price=1500),
    2: Item(id=2, name="Notebook", price=3000),
    3: Item(id=3, name="Eraser", price=500, in_stock=False),
}


# ============================================================================
# 라우트
# ============================================================================


@router.get("", summary="아이템 목록")
async def list_items(
    in_stock_only: bool = Query(False, description="재고 있는 것만"),
    limit: int = Query(10, ge=1, le=100, description="최대 개수"),
) -> list[Item]:
    """query 파라미터:
        - in_stock_only: bool 자동 변환 ("true"/"false"/"1"/"0" 모두 OK)
        - limit: int 자동 검증 (1~100 밖이면 422)
    """
    items = list(_DB.values())
    if in_stock_only:
        items = [i for i in items if i.in_stock]
    return items[:limit]


@router.get("/{item_id}", summary="단일 아이템 조회")
async def get_item(item_id: int) -> Item:
    """path 파라미터 `item_id`. int 자동 변환 — `abc` 들어오면 422."""
    item = _DB.get(item_id)
    if item is None:
        # FastAPI 가 자동 JSON 응답으로 변환
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"item {item_id} not found")
    return item
