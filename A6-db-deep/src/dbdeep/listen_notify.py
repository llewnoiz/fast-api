"""Postgres LISTEN / NOTIFY — _경량 pub/sub_.

용도:
    - 캐시 무효화 신호 (다른 인스턴스에 "이 키 만료시켜")
    - 마이그레이션 후 _재로딩_ 트리거
    - 이벤트 전파 (Kafka 까지 안 갈 _가벼운_ 케이스)

특징 / 한계:
    - 같은 DB 에 _연결된_ 클라이언트 끼리만 (Kafka 처럼 외부 brokered X)
    - **메시지 누락 가능** — LISTEN 안 하고 있던 시점의 NOTIFY 는 사라짐 (durable X)
    - 페이로드 _8000 바이트_ 제한 (실용 기준 ~5 KiB)
    - 트랜잭션 _커밋_ 시점에 발송 (롤백되면 안 보냄 — outbox 와 비슷한 효과)

→ _가벼운_ 신호용. 영속성/순서/내구성 필요하면 _Kafka_.

여기선 sync **psycopg** (3.x) 로 간단히 시연. asyncpg 도 LISTEN 지원하나 API 가 다름.

비교:
    Redis pub/sub — 비슷한 _비영속_ 모델
    Kafka — 영속성/재처리/스케일 ─ 13 단계 참고
    Postgres LOGICAL replication / WAL → 더 강력하지만 운영급
"""

from __future__ import annotations

import json
import select as select_module
from collections.abc import Iterator
from typing import Any

import psycopg


def notify(database_url_sync: str, channel: str, payload: dict[str, Any]) -> None:
    """한 번 NOTIFY 보내고 종료. URL 은 _psycopg sync_ 형식 (postgresql://..., 드라이버 prefix 없음)."""
    with psycopg.connect(database_url_sync, autocommit=True) as conn, conn.cursor() as cur:
        # NOTIFY 는 파라미터 바인딩 X — _SQL injection 위험_ 이라 채널/페이로드 직접 검증 필요.
        # 학습 코드라 단순화. 운영은 채널을 화이트리스트, 페이로드는 json.dumps 후 길이 체크.
        cur.execute(
            "SELECT pg_notify(%s, %s)",
            (channel, json.dumps(payload)),
        )


def listen_once(
    database_url_sync: str, channel: str, timeout: float = 5.0
) -> Iterator[dict[str, Any]]:
    """채널을 LISTEN 하고 들어오는 NOTIFY 를 yield. timeout 까지 받은 만큼 반환.

    학습용 — 운영은 _별도 백그라운드 태스크_ + 재연결 / 헬스체크 / 종료 시그널 처리 필요.
    """
    with psycopg.connect(database_url_sync, autocommit=True) as conn:
        with conn.cursor() as cur:
            # 채널 이름은 식별자라 quote_ident 사용 권장 — 학습용 단순화
            cur.execute(f'LISTEN "{channel}"')

        # 폴링 루프 — `select` 로 소켓이 _읽기 가능_ 해질 때까지 대기
        while True:
            r, _, _ = select_module.select([conn], [], [], timeout)
            if not r:
                return  # timeout
            # generator 가 새 NOTIFY 를 가져옴 (psycopg 3 의 notifies() 는 iterable)
            for notify_msg in conn.notifies(timeout=0.1, stop_after=1):
                try:
                    yield json.loads(notify_msg.payload)
                except json.JSONDecodeError:
                    yield {"raw": notify_msg.payload}
                return
