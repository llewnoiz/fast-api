"""사용자 모델 + _인메모리_ 저장소.

10 단계 (DB) 에서 SQLAlchemy 로 교체. 학습 흐름에 집중하려고 일단 dict.

규칙:
    - 비밀번호는 _절대_ 평문으로 저장 X — 항상 _해시_
    - 응답 모델엔 `password_hash` 절대 노출 X
"""

from __future__ import annotations

from pydantic import BaseModel

from authapp.security import hash_password


class User(BaseModel):
    """내부 표현 — `password_hash` 포함."""

    username: str
    full_name: str
    roles: list[str] = []
    password_hash: str
    disabled: bool = False


class UserPublic(BaseModel):
    """외부 응답용 — `password_hash` _없음_."""

    username: str
    full_name: str
    roles: list[str]


# 학습용 시드 — 비밀번호는 부팅 시 _해싱_
_SEED = [
    ("alice", "Alice Kim",  "alice123",  ["admin", "user"]),
    ("bob",   "Bob Park",   "bob123",    ["user"]),
    ("carol", "Carol Lee",  "carol123",  ["user", "auditor"]),
]

_USERS: dict[str, User] = {
    username: User(
        username=username,
        full_name=full_name,
        roles=roles,
        password_hash=hash_password(plain_pw),
    )
    for username, full_name, plain_pw, roles in _SEED
}


def get_user(username: str) -> User | None:
    return _USERS.get(username)
