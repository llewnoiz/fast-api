"""DataLoader 패턴 — GraphQL 의 _N+1 표준 해결책_.

문제:
    GraphQL `posts { author { name } }` 쿼리 시 _각 post 마다_ author resolver 가 호출.
    naive 구현은 post 100개면 author 조회 100번 → DB 폭발.

해법 (Facebook 의 dataloader 패턴):
    - 한 _이벤트 루프 tick_ 동안 들어온 ID 들을 _버퍼에 모음_
    - tick 끝나면 _배치 함수_ 한 번 호출 (ID 리스트 → row 리스트)
    - 결과를 ID 별로 분배해 각 resolver 에 반환
    - 같은 ID 중복 조회는 _캐시_ (요청 단위)

흐름:
```
resolver A: load(1) ──┐
resolver B: load(2) ──┼──▶ batch fn([1, 2, 3]) ──▶ DB (1 round-trip)
resolver C: load(3) ──┘                  └──▶ {1: row1, 2: row2, 3: row3}
                                              │
                                              ▼
                       resolver A 받음 row1, B 받음 row2, ...
```

**중요**:
    - DataLoader 는 _요청 단위_ ── 매 GraphQL 요청마다 _새로_ 만들어야 캐시가 stale 안 됨.
    - 동일 ID 중복 조회는 _자동 dedupe_ (캐시 hit).
    - 배치 함수의 _반환 순서_ 가 입력 ID 순서와 _일치_ 해야 (DataLoader 가 그렇게 매핑).

비교:
    Node `dataloader` ── Facebook 원조
    Java `graphql-java` `BatchLoader`
    Go `graph-gophers/dataloader`
    Strawberry `strawberry.dataloader.DataLoader` ── 본 모듈
"""

from __future__ import annotations

from strawberry.dataloader import DataLoader

from gqlapi.data import DataStore, PostRow, UserRow


def make_user_loader(store: DataStore) -> DataLoader[int, UserRow | None]:
    """user_id → UserRow. 같은 요청 내 중복 ID 는 _캐시_."""

    async def batch_load_users(keys: list[int]) -> list[UserRow | None]:
        # 단일 round-trip 으로 모든 ID 한 번에
        return store.get_users_by_ids(keys)

    return DataLoader(load_fn=batch_load_users, cache=True)


def make_posts_by_author_loader(store: DataStore) -> DataLoader[int, list[PostRow]]:
    """author_id → list[PostRow]. 1:N 관계용."""

    async def batch_load_posts(keys: list[int]) -> list[list[PostRow]]:
        grouped = store.get_posts_by_authors(keys)
        return [grouped.get(k, []) for k in keys]

    return DataLoader(load_fn=batch_load_posts, cache=True)
