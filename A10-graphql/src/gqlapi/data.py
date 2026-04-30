"""학습용 인메모리 데이터 + 시드 + 액세스 카운터 (N+1 시연용).

운영은 SQLAlchemy / async DB. 본 모듈은 _GraphQL 패턴_ 에 집중하기 위해 단순화.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class UserRow:
    id: int
    name: str
    email: str


@dataclass
class PostRow:
    id: int
    author_id: int
    title: str
    body: str


@dataclass
class CommentRow:
    id: int
    post_id: int
    author_id: int
    body: str


@dataclass
class DataStore:
    """학습 데이터 + _쿼리 호출 카운터_ (N+1 검증용).

    `users_by_ids_calls` / `posts_by_author_calls` 같은 카운터는 _DB round-trip 횟수_ 시뮬.
    DataLoader 적용 후 1로 감소하는지 테스트가 검증.
    """

    users: dict[int, UserRow] = field(default_factory=dict)
    posts: dict[int, PostRow] = field(default_factory=dict)
    comments: dict[int, CommentRow] = field(default_factory=dict)

    # ── 카운터 ── 매 쿼리 헬퍼 호출 시 1 증가
    users_by_ids_calls: int = 0
    posts_by_author_calls: int = 0

    # ── access helpers (DB round-trip 흉내) ──
    def list_users(self) -> list[UserRow]:
        return list(self.users.values())

    def list_posts(self) -> list[PostRow]:
        return list(self.posts.values())

    def get_users_by_ids(self, ids: list[int]) -> list[UserRow | None]:
        """ids 순서대로 None or row. DataLoader 의 기반 함수.

        호출 1번 = DB round-trip 1번 (ID IN (...) WHERE 절 한 번).
        """
        self.users_by_ids_calls += 1
        return [self.users.get(i) for i in ids]

    def get_posts_by_author(self, author_id: int) -> list[PostRow]:
        """단일 author 의 posts. naive resolver 가 사용 → N+1."""
        self.posts_by_author_calls += 1
        return [p for p in self.posts.values() if p.author_id == author_id]

    def get_posts_by_authors(self, author_ids: list[int]) -> dict[int, list[PostRow]]:
        """여러 author 한 번에 — DataLoader 가 사용. 1 round-trip 으로 압축."""
        self.posts_by_author_calls += 1
        result: dict[int, list[PostRow]] = {aid: [] for aid in author_ids}
        for p in self.posts.values():
            if p.author_id in result:
                result[p.author_id].append(p)
        return result


def seed(store: DataStore) -> None:
    """3 명 사용자 + 각 2~3 개 글 + 글당 0~3 댓글."""
    users = [
        UserRow(id=1, name="Alice", email="alice@example.com"),
        UserRow(id=2, name="Bob", email="bob@example.com"),
        UserRow(id=3, name="Carol", email="carol@example.com"),
    ]
    for u in users:
        store.users[u.id] = u

    posts_data = [
        (1, 1, "Alice's first post", "..."),
        (2, 1, "Alice on FastAPI", "async FastAPI 좋다"),
        (3, 1, "Alice on Postgres", "jsonb 가 좋다"),
        (4, 2, "Bob's intro", "Hi I'm Bob"),
        (5, 2, "Bob on Kafka", "이벤트 기반"),
        (6, 3, "Carol on GraphQL", "DataLoader 가 핵심"),
        (7, 3, "Carol on Redis", "stampede 방지"),
    ]
    for pid, aid, title, body in posts_data:
        store.posts[pid] = PostRow(id=pid, author_id=aid, title=title, body=body)

    comments_data = [
        (1, 1, 2, "Bob: 좋은 글"),
        (2, 2, 3, "Carol: async 가 강력"),
        (3, 6, 1, "Alice: DataLoader 잘 정리"),
        (4, 6, 2, "Bob: 동의"),
    ]
    for cid, pid, aid, body in comments_data:
        store.comments[cid] = CommentRow(id=cid, post_id=pid, author_id=aid, body=body)
