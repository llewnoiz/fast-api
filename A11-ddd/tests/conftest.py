"""A11 fixture — 인메모리 UoW + Notifier (도커 불필요)."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from tenderdomain.adapters.api.main import create_app
from tenderdomain.adapters.inmemory import (
    CollectingNotifier,
    InMemoryOrderRepository,
    InMemoryUnitOfWork,
    InMemoryUserRepository,
)


@pytest.fixture
def user_repo() -> InMemoryUserRepository:
    repo = InMemoryUserRepository()
    repo.add(1)
    repo.add(2)
    return repo


@pytest.fixture
def order_repo() -> InMemoryOrderRepository:
    return InMemoryOrderRepository()


@pytest.fixture
def notifier() -> CollectingNotifier:
    return CollectingNotifier()


@pytest.fixture
def uow(
    user_repo: InMemoryUserRepository, order_repo: InMemoryOrderRepository
) -> InMemoryUnitOfWork:
    return InMemoryUnitOfWork(orders=order_repo, users=user_repo)


@pytest.fixture
def client() -> Iterator[TestClient]:
    app = create_app()
    with TestClient(app) as c:
        yield c
