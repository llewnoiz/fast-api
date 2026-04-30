"""Strawberry 스키마 — GraphQL 타입 + Query + Mutation.

핵심 개념:
    - **타입**: `@strawberry.type` 클래스. 필드는 _쿼리 가능한_ 데이터.
    - **resolver**: 필드를 _계산_ 하는 함수. 동기/비동기 둘 다 가능.
    - **Info / context**: 모든 resolver 가 받는 _요청 단위_ 컨텍스트 (DataLoader / 인증 등).
    - **Query / Mutation**: 진입점. Subscription 도 있지만 본 모듈 _범위 밖_.

비교:
    Spring Boot `graphql-java` — annotation 기반
    NestJS `@Resolver` / `@Query()` / `@Mutation()` decorator
    Apollo Server (Node) — schema-first vs code-first 두 방식
    Strawberry — code-first + Python 타입 힌트 _그대로_ 활용 (가장 Pythonic)

**code-first vs schema-first**:
    - **code-first** (Strawberry, graphene) — Python 코드가 진실. 스키마는 _자동 생성_.
    - **schema-first** (Ariadne) — `.graphql` 파일이 진실. 코드는 _바인딩_.
    code-first 가 _타입 안전성_ + _리팩토링 친화_. schema-first 는 _프론트엔드와 명세 공유_ 친화.
"""

from __future__ import annotations

import strawberry
from strawberry.fastapi import BaseContext
from strawberry.types import Info

from gqlapi.data import DataStore, PostRow, UserRow


class GraphQLContext(BaseContext):
    """매 요청마다 _새로_ 만들어지는 컨텍스트. DataLoader 는 _여기에_.

    Strawberry FastAPI 통합을 위해 `BaseContext` 상속 (request / background_tasks 자동 주입).
    schema.execute() 직접 호출 시도 동일하게 동작.
    """

    def __init__(
        self,
        store: DataStore,
        user_loader: object,
        posts_by_author_loader: object,
        use_dataloader: bool = True,
    ) -> None:
        super().__init__()
        self.store = store
        self.user_loader = user_loader
        self.posts_by_author_loader = posts_by_author_loader
        self.use_dataloader = use_dataloader


# ─────────────────────────────────────────────────────────────────
# 타입
# ─────────────────────────────────────────────────────────────────


@strawberry.type
class User:
    id: int
    name: str
    email: str

    @strawberry.field
    async def posts(self, info: Info) -> list[Post]:
        """이 user 의 posts. DataLoader 또는 naive."""
        ctx: GraphQLContext = info.context
        if ctx.use_dataloader:
            rows = await ctx.posts_by_author_loader.load(self.id)  # type: ignore[attr-defined]
        else:
            rows = ctx.store.get_posts_by_author(self.id)
        return [Post.from_row(r) for r in rows]

    @classmethod
    def from_row(cls, row: UserRow) -> User:
        return cls(id=row.id, name=row.name, email=row.email)


@strawberry.type
class Post:
    id: int
    author_id: strawberry.Private[int]
    title: str
    body: str

    @strawberry.field
    async def author(self, info: Info) -> User | None:
        """이 post 의 author. DataLoader 또는 naive."""
        ctx: GraphQLContext = info.context
        if ctx.use_dataloader:
            row = await ctx.user_loader.load(self.author_id)  # type: ignore[attr-defined]
        else:
            rows = ctx.store.get_users_by_ids([self.author_id])
            row = rows[0]
        return User.from_row(row) if row else None

    @classmethod
    def from_row(cls, row: PostRow) -> Post:
        return cls(id=row.id, author_id=row.author_id, title=row.title, body=row.body)


# ─────────────────────────────────────────────────────────────────
# Query
# ─────────────────────────────────────────────────────────────────


@strawberry.type
class Query:
    @strawberry.field
    async def users(self, info: Info) -> list[User]:
        ctx: GraphQLContext = info.context
        return [User.from_row(r) for r in ctx.store.list_users()]

    @strawberry.field
    async def user(self, info: Info, id: int) -> User | None:
        ctx: GraphQLContext = info.context
        if ctx.use_dataloader:
            row = await ctx.user_loader.load(id)  # type: ignore[attr-defined]
        else:
            rows = ctx.store.get_users_by_ids([id])
            row = rows[0]
        return User.from_row(row) if row else None

    @strawberry.field
    async def posts(self, info: Info) -> list[Post]:
        ctx: GraphQLContext = info.context
        return [Post.from_row(r) for r in ctx.store.list_posts()]


# ─────────────────────────────────────────────────────────────────
# Mutation
# ─────────────────────────────────────────────────────────────────


@strawberry.input
class CreatePostInput:
    author_id: int
    title: str
    body: str


@strawberry.type
class Mutation:
    @strawberry.mutation
    async def create_post(self, info: Info, input: CreatePostInput) -> Post:
        ctx: GraphQLContext = info.context
        if input.author_id not in ctx.store.users:
            # GraphQL 에러: HTTP 200 + `errors` 필드. REST 의 4xx 와 다른 모델.
            raise ValueError(f"unknown author_id: {input.author_id}")

        new_id = max(ctx.store.posts.keys(), default=0) + 1
        row = PostRow(id=new_id, author_id=input.author_id, title=input.title, body=input.body)
        ctx.store.posts[new_id] = row
        return Post.from_row(row)


schema = strawberry.Schema(query=Query, mutation=Mutation)
