"""A10 fixture — Strawberry 스키마 직접 실행 + FastAPI TestClient.

도커 / Redis 불필요 (인메모리 데이터).
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from gqlapi.data import DataStore, seed
from gqlapi.dataloader import make_posts_by_author_loader, make_user_loader
from gqlapi.main import create_app
from gqlapi.schema import GraphQLContext


@pytest.fixture
def store() -> DataStore:
    s = DataStore()
    seed(s)
    return s


@pytest.fixture
def context_with_dataloader(store: DataStore) -> GraphQLContext:
    return GraphQLContext(
        store=store,
        user_loader=make_user_loader(store),
        posts_by_author_loader=make_posts_by_author_loader(store),
        use_dataloader=True,
    )


@pytest.fixture
def context_naive(store: DataStore) -> GraphQLContext:
    return GraphQLContext(
        store=store,
        user_loader=make_user_loader(store),
        posts_by_author_loader=make_posts_by_author_loader(store),
        use_dataloader=False,
    )


@pytest.fixture
def client() -> Iterator[TestClient]:
    app = create_app()
    with TestClient(app) as c:
        yield c
