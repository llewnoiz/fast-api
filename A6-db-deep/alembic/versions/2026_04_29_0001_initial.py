"""initial — deep_users / deep_posts / deep_comments + 인덱스 모음 + tsvector GENERATED

Revision ID: 0001
Revises:
Create Date: 2026-04-29

핵심 학습 포인트:
    - jsonb 컬럼 + GIN 인덱스
    - tsvector 컬럼은 _GENERATED ALWAYS AS_ 로 자동 채움 (Postgres 12+)
    - 부분 인덱스 (`postgresql_where`)
    - expression 인덱스 (`func.lower(...)`)
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "deep_users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("username", sa.String(length=50), nullable=False, unique=True),
        sa.Column("email", sa.String(length=100), nullable=False),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )
    op.create_index("ix_deep_users_username", "deep_users", ["username"], unique=True)
    op.create_index(
        "ix_deep_users_email_lower",
        "deep_users",
        [sa.text("lower(email)")],
    )
    op.create_index(
        "ix_deep_users_active_created",
        "deep_users",
        ["created_at"],
        postgresql_where=sa.text("is_active = true"),
    )

    op.create_table(
        "deep_posts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "author_id",
            sa.Integer(),
            sa.ForeignKey("deep_users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("tags", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        # tsvector — GENERATED ALWAYS AS (Postgres 12+)
        # title 가중치 'A', body 가중치 'B' — ts_rank 가 자연히 title 매치를 우선
        sa.Column(
            "search",
            TSVECTOR(),
            sa.Computed(
                "setweight(to_tsvector('english', coalesce(title, '')), 'A') "
                "|| setweight(to_tsvector('english', coalesce(body, '')), 'B')",
                persisted=True,
            ),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )
    op.create_index("ix_deep_posts_author_id", "deep_posts", ["author_id"])
    op.create_index(
        "ix_deep_posts_author_created",
        "deep_posts",
        ["author_id", "created_at"],
    )
    # GIN — jsonb_path_ops 가 _더 작고 빠름_ (`@>` 만 지원하지만 90% 케이스).
    # 학습용으로 기본 jsonb_ops 사용. 운영에선 패턴 따라 선택.
    op.create_index("ix_deep_posts_tags_gin", "deep_posts", ["tags"], postgresql_using="gin")
    op.create_index("ix_deep_posts_search_gin", "deep_posts", ["search"], postgresql_using="gin")

    op.create_table(
        "deep_comments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "post_id",
            sa.Integer(),
            sa.ForeignKey("deep_posts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )
    op.create_index("ix_deep_comments_post_id", "deep_comments", ["post_id"])


def downgrade() -> None:
    op.drop_index("ix_deep_comments_post_id", table_name="deep_comments")
    op.drop_table("deep_comments")
    op.drop_index("ix_deep_posts_search_gin", table_name="deep_posts")
    op.drop_index("ix_deep_posts_tags_gin", table_name="deep_posts")
    op.drop_index("ix_deep_posts_author_created", table_name="deep_posts")
    op.drop_index("ix_deep_posts_author_id", table_name="deep_posts")
    op.drop_table("deep_posts")
    op.drop_index("ix_deep_users_active_created", table_name="deep_users")
    op.drop_index("ix_deep_users_email_lower", table_name="deep_users")
    op.drop_index("ix_deep_users_username", table_name="deep_users")
    op.drop_table("deep_users")
