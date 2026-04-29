"""/admin/* — 관리자 전용 라우트. RBAC 데모.

라우터 _전체_ 에 `dependencies=[Depends(require_role(...))]` 적용 — 모든 엔드포인트
보호. 일부만 보호하려면 라우트별 dependencies 또는 함수 인자로.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from authapp.deps import require_role
from authapp.users import User

# 라우터 전체 가드
router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(require_role("admin"))],
)


@router.get("/secret", summary="관리자 비밀")
async def admin_secret(
    current: Annotated[User, Depends(require_role("admin"))],
) -> dict[str, str]:
    return {"who": current.username, "secret": "🔑 nuclear codes"}


# 보너스: 'admin' 또는 'auditor' 둘 중 하나만 있어도 OK
auditor_or_admin_router = APIRouter(prefix="/audit", tags=["audit"])


@auditor_or_admin_router.get(
    "/log",
    dependencies=[Depends(require_role("admin", "auditor"))],
    summary="감사 로그 (admin 또는 auditor)",
)
async def view_audit_log() -> list[dict[str, str]]:
    return [
        {"event": "login", "user": "alice"},
        {"event": "delete_order", "user": "bob"},
    ]
