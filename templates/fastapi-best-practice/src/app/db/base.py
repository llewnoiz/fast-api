"""Declarative Base — alembic env.py 가 깔끔하게 import.

`from app.db.base import Base; import app.models` 로 모든 모델 메타데이터 등록.
"""

from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """모든 모델의 베이스. alembic 의 `target_metadata = Base.metadata`."""
