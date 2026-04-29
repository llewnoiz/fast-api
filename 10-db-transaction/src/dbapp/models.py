"""SQLAlchemy 2.0 모델 — _새로운_ Mapped[T] + mapped_column 스타일.

비교 (가장 가까운 것):
    Spring Data JPA: `@Entity class User { @Id @GeneratedValue Long id; ... }`
    Kotlin Exposed:  Object User: IntIdTable() { val username = varchar("username", 50) }
    NestJS TypeORM:  @Entity class User { @PrimaryGeneratedColumn id: number; ... }

2.0 스타일의 핵심:
    - `Mapped[T]` 타입 어노테이션 — 타입 힌트가 _진짜로_ 모델 정의에 쓰임
    - `mapped_column(...)` 가 옛 `Column(...)` 대체
    - `relationship` 도 `Mapped[...]` 어노테이션으로 정확한 타입
    - Pyright/mypy 가 _쿼리 결과 타입_ 까지 추론
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import ForeignKey, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """모든 모델의 베이스. Alembic 의 `target_metadata = Base.metadata`."""


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    # User 1:N Order — Mapped[list["Order"]] 로 정확한 타입
    orders: Mapped[list[Order]] = relationship(back_populates="owner", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"User(id={self.id!r}, username={self.username!r})"


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    item: Mapped[str] = mapped_column(String(100))
    quantity: Mapped[int] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    owner: Mapped[User] = relationship(back_populates="orders")

    def __repr__(self) -> str:
        return f"Order(id={self.id!r}, user_id={self.user_id!r}, item={self.item!r})"
