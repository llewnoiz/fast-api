"""DataLoader vs naive — _round-trip 횟수_ 비교로 N+1 검증.

핵심 검증:
    - naive (`use_dataloader=False`): N 개 post → N 번 author 조회
    - DataLoader (`use_dataloader=True`): N 개 post → _1 번_ author 조회
"""

from __future__ import annotations

from gqlapi.data import DataStore
from gqlapi.schema import GraphQLContext, schema


async def test_naive_resolver_causes_n_plus_one(
    store: DataStore, context_naive: GraphQLContext
) -> None:
    """`posts { author }` ── naive: post 7 개 마다 author 조회 → 7 round-trip."""
    store.users_by_ids_calls = 0

    result = await schema.execute(
        "{ posts { id author { name } } }",
        context_value=context_naive,
    )
    assert result.errors is None
    assert len(result.data["posts"]) == 7  # type: ignore[index]
    # naive: 7 번 (각 post 마다)
    assert store.users_by_ids_calls == 7


async def test_dataloader_collapses_to_1_round_trip(
    store: DataStore, context_with_dataloader: GraphQLContext
) -> None:
    """DataLoader: post 7개 → author 한 번에 조회 (1 round-trip)."""
    store.users_by_ids_calls = 0

    result = await schema.execute(
        "{ posts { id author { name } } }",
        context_value=context_with_dataloader,
    )
    assert result.errors is None
    # 7 post 가 각각 load(authorId) 호출 → 한 tick 후 batch 1번
    assert store.users_by_ids_calls == 1


async def test_dataloader_dedupes_same_id(
    store: DataStore, context_with_dataloader: GraphQLContext
) -> None:
    """같은 author_id 를 여러 post 가 공유 → DataLoader 가 자동 중복 제거.

    Alice 글 3개, Bob 글 2개, Carol 글 2개 → 총 7 post 지만 _고유 author 3 명_.
    DataLoader 의 batch 함수는 _고유 ID 3개_ 만 조회하면 됨.
    """
    store.users_by_ids_calls = 0
    await schema.execute(
        "{ posts { author { id } } }",
        context_value=context_with_dataloader,
    )
    # batch 호출 자체는 1번. _그 안에서_ 3개 고유 ID 만 조회.
    assert store.users_by_ids_calls == 1


async def test_users_with_posts_uses_dataloader(
    store: DataStore, context_with_dataloader: GraphQLContext
) -> None:
    """users { posts } ── 3 명 user, 각자 posts 조회 → DataLoader 1 번."""
    store.posts_by_author_calls = 0

    result = await schema.execute(
        "{ users { name posts { title } } }",
        context_value=context_with_dataloader,
    )
    assert result.errors is None
    # 3 user → load(authorId) 3 번 → batch 1 번
    assert store.posts_by_author_calls == 1


async def test_naive_users_with_posts_n_plus_1(
    store: DataStore, context_naive: GraphQLContext
) -> None:
    """naive: 3 user → 3 번 posts_by_author 조회."""
    store.posts_by_author_calls = 0

    await schema.execute(
        "{ users { posts { title } } }",
        context_value=context_naive,
    )
    assert store.posts_by_author_calls == 3
