"""GraphQL 스키마 직접 실행 — Strawberry `schema.execute()` 로 단위 테스트.

장점: HTTP / FastAPI 거치지 않아 _빠름_ + 결정적. 운영 통합은 e2e 에서.
"""

from __future__ import annotations

from gqlapi.schema import GraphQLContext, schema


async def test_query_users_returns_seed(context_with_dataloader: GraphQLContext) -> None:
    result = await schema.execute(
        "{ users { id name email } }",
        context_value=context_with_dataloader,
    )
    assert result.errors is None
    users = result.data["users"]  # type: ignore[index]
    assert len(users) == 3
    assert {u["name"] for u in users} == {"Alice", "Bob", "Carol"}


async def test_query_user_by_id(context_with_dataloader: GraphQLContext) -> None:
    result = await schema.execute(
        "query Q($id: Int!) { user(id: $id) { name email } }",
        variable_values={"id": 1},
        context_value=context_with_dataloader,
    )
    assert result.errors is None
    assert result.data["user"]["name"] == "Alice"  # type: ignore[index]


async def test_query_unknown_user_returns_null(
    context_with_dataloader: GraphQLContext,
) -> None:
    result = await schema.execute(
        "query Q($id: Int!) { user(id: $id) { name } }",
        variable_values={"id": 9999},
        context_value=context_with_dataloader,
    )
    assert result.errors is None
    assert result.data["user"] is None  # type: ignore[index]


async def test_nested_query_users_with_posts(context_with_dataloader: GraphQLContext) -> None:
    result = await schema.execute(
        """
        {
            users {
                name
                posts { title }
            }
        }
        """,
        context_value=context_with_dataloader,
    )
    assert result.errors is None
    users = result.data["users"]  # type: ignore[index]
    alice = next(u for u in users if u["name"] == "Alice")
    assert len(alice["posts"]) == 3


async def test_post_to_author_resolver(context_with_dataloader: GraphQLContext) -> None:
    result = await schema.execute(
        "{ posts { id title author { name } } }",
        context_value=context_with_dataloader,
    )
    assert result.errors is None
    posts = result.data["posts"]  # type: ignore[index]
    # 모든 post 가 author 를 가짐
    assert all(p["author"] is not None for p in posts)


async def test_create_post_mutation(context_with_dataloader: GraphQLContext) -> None:
    result = await schema.execute(
        """
        mutation M($input: CreatePostInput!) {
            createPost(input: $input) { id title }
        }
        """,
        variable_values={"input": {"authorId": 1, "title": "new", "body": "hi"}},
        context_value=context_with_dataloader,
    )
    assert result.errors is None
    new_post = result.data["createPost"]  # type: ignore[index]
    assert new_post["title"] == "new"


async def test_create_post_unknown_author_errors(
    context_with_dataloader: GraphQLContext,
) -> None:
    """존재 안 하는 author_id → GraphQL `errors` 필드.

    REST 의 4xx 와 다른 모델: HTTP 200 + body 의 errors. 클라이언트가 errors 검사 필수.
    """
    result = await schema.execute(
        """
        mutation M($input: CreatePostInput!) {
            createPost(input: $input) { id }
        }
        """,
        variable_values={"input": {"authorId": 99, "title": "x", "body": "y"}},
        context_value=context_with_dataloader,
    )
    assert result.errors is not None
    assert "unknown author_id" in str(result.errors[0])
