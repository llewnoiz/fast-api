"""A6 학습용 모델 — 인덱스 / jsonb / FTS / Expand-Contract 마이그레이션 데모.

스키마 개요:

    User ──┬── Post (1:N)              ── tags JSONB GIN, search tsvector FTS
           │       └── Comment (1:N)
           └── (Post.author_id index)

핵심 학습 포인트:
    - **B-tree 인덱스** — `index=True` (가장 흔함, =, <, >, BETWEEN, ORDER BY)
    - **복합 인덱스** — `Index("ix_a_b", "a", "b")` 순서 중요 (왼쪽 prefix 만 활용)
    - **부분 인덱스** — `postgresql_where=...` (소수의 행만 인덱싱 — 디스크 절약)
    - **GIN 인덱스** — jsonb / tsvector / 배열 (다값 컬럼) 검색
    - **expression 인덱스** — `func.lower(...)` 같은 _계산식_ 에 인덱스
    - **UNIQUE 인덱스** — 자동으로 unique 제약 + 빠른 조회
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import Computed, ForeignKey, Index, String, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """A6 데모용 베이스. 10 단계와 _격리_ 된 테이블 사용 (deep_ 접두사)."""


class User(Base):
    __tablename__ = "deep_users"

    id: Mapped[int] = mapped_column(primary_key=True)
    # username — 단일 컬럼 unique 인덱스 (자동 생성)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(100))
    # email_lower — Expand-Contract 마이그레이션 (0002, 0003) 결과. 검색용 정규화.
    # 운영에선 dual-write 단계에서 컬럼 등장 → 점진적 백필 → NOT NULL.
    email_lower: Mapped[str] = mapped_column(String(100))
    # is_active — 부분 인덱스 후보. 비활성 사용자는 _드물게_ 조회. (아래 __table_args__ 참고)
    is_active: Mapped[bool] = mapped_column(default=True, server_default=text("true"))
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
    )

    posts: Mapped[list[Post]] = relationship(back_populates="author", cascade="all, delete-orphan")

    __table_args__ = (
        # email 검색은 보통 lower(email) — expression 인덱스
        Index("ix_deep_users_email_lower", func.lower(text("email"))),
        # 부분 인덱스: 활성 사용자만. 인덱스 크기 ↓, 조회 속도 ↑
        Index(
            "ix_deep_users_active_created",
            "created_at",
            postgresql_where=text("is_active = true"),
        ),
    )


class Post(Base):
    __tablename__ = "deep_posts"

    id: Mapped[int] = mapped_column(primary_key=True)
    author_id: Mapped[int] = mapped_column(
        ForeignKey("deep_users.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(Text())
    # ── jsonb: 동적 스키마 (태그/메타데이터). GIN 인덱스로 jsonb_path_ops 검색
    tags: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    # ── tsvector: full-text search 미리 계산해 저장 (GENERATED ALWAYS — Postgres 12+).
    # `Computed(persisted=True)` — SQLAlchemy 가 INSERT/UPDATE 시 _제외_. DB 가 자동 채움.
    # 마이그레이션 0001 의 식과 _동일_ 해야 함 (둘 다 정답).
    search: Mapped[str | None] = mapped_column(
        TSVECTOR,
        Computed(
            "setweight(to_tsvector('english', coalesce(title, '')), 'A') "
            "|| setweight(to_tsvector('english', coalesce(body, '')), 'B')",
            persisted=True,
        ),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    author: Mapped[User] = relationship(back_populates="posts")
    comments: Mapped[list[Comment]] = relationship(
        back_populates="post", cascade="all, delete-orphan"
    )

    __table_args__ = (
        # GIN — jsonb 검색 (`tags @> '{"category": "tech"}'`)
        Index("ix_deep_posts_tags_gin", "tags", postgresql_using="gin"),
        # GIN — full-text search (`search @@ tsquery(...)`)
        Index("ix_deep_posts_search_gin", "search", postgresql_using="gin"),
        # 복합 인덱스 — author 의 _최신_ 글 조회 (author_id, created_at DESC)
        Index("ix_deep_posts_author_created", "author_id", "created_at"),
    )


class Comment(Base):
    __tablename__ = "deep_comments"

    id: Mapped[int] = mapped_column(primary_key=True)
    post_id: Mapped[int] = mapped_column(
        ForeignKey("deep_posts.id", ondelete="CASCADE"), index=True
    )
    body: Mapped[str] = mapped_column(Text())
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    post: Mapped[Post] = relationship(back_populates="comments")
