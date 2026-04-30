"""FastAPI 앱 — A6 학습 API.

엔드포인트:
    GET  /healthz                       헬스체크
    POST /seed                          학습 데이터 시드
    GET  /n-plus-one/naive              N+1 발생 — 쿼리 수와 함께 반환
    GET  /n-plus-one/selectin           selectinload — 2 쿼리
    GET  /n-plus-one/joined             joinedload  — 1 쿼리
    GET  /jsonb/by-category/{cat}       jsonb @> 검색
    GET  /jsonb/by-label/{lab}          jsonb labels 배열 검색
    GET  /fts/search?q=...              full-text search
    GET  /fts/search-ranked?q=...       FTS + ts_rank 정렬

운영 학습:
    - 12 단계 OTel 미들웨어를 여기 끼우면 모든 쿼리에 trace 자동
    - 11 단계 Redis 캐시 + LISTEN/NOTIFY 로 _분산 캐시 무효화_
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from dbdeep import fts, jsonb, n_plus_one
from dbdeep.database import make_engine, make_sessionmaker
from dbdeep.seed import seed_data
from dbdeep.settings import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    engine = make_engine(settings.database_url, echo=settings.sql_echo)
    app.state.engine = engine
    app.state.sessionmaker = make_sessionmaker(engine)
    try:
        yield
    finally:
        await engine.dispose()


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    sm = request.app.state.sessionmaker
    async with sm() as session:
        yield session


def get_engine(request: Request) -> AsyncEngine:
    engine: AsyncEngine = request.app.state.engine
    return engine


SessionDep = Annotated[AsyncSession, Depends(get_session)]
EngineDep = Annotated[AsyncEngine, Depends(get_engine)]


def create_app() -> FastAPI:
    app = FastAPI(title="A6 — DB 심화", lifespan=lifespan)

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/seed")
    async def seed_endpoint(session: SessionDep) -> dict[str, str]:
        await seed_data(session)
        return {"status": "seeded"}

    @app.get("/n-plus-one/naive")
    async def n_plus_one_naive(session: SessionDep, engine: EngineDep) -> dict[str, int]:
        with n_plus_one.count_queries(engine) as q:
            users = await n_plus_one.fetch_users_with_posts_naive(session)
        return {"users": len(users), "queries": q.count}

    @app.get("/n-plus-one/selectin")
    async def n_plus_one_selectin(session: SessionDep, engine: EngineDep) -> dict[str, int]:
        with n_plus_one.count_queries(engine) as q:
            users = await n_plus_one.fetch_users_with_posts_selectin(session)
        return {"users": len(users), "queries": q.count}

    @app.get("/n-plus-one/joined")
    async def n_plus_one_joined(session: SessionDep, engine: EngineDep) -> dict[str, int]:
        with n_plus_one.count_queries(engine) as q:
            users = await n_plus_one.fetch_users_with_posts_joined(session)
        return {"users": len(users), "queries": q.count}

    @app.get("/jsonb/by-category/{category}")
    async def by_category(category: str, session: SessionDep) -> dict[str, list[int]]:
        posts = await jsonb.find_posts_by_category(session, category)
        return {"post_ids": [p.id for p in posts]}

    @app.get("/jsonb/by-label/{label}")
    async def by_label(label: str, session: SessionDep) -> dict[str, list[int]]:
        posts = await jsonb.find_posts_by_label(session, label)
        return {"post_ids": [p.id for p in posts]}

    @app.get("/fts/search")
    async def fts_search(q: str, session: SessionDep) -> dict[str, list[int]]:
        if not q.strip():
            raise HTTPException(status_code=400, detail="query empty")
        posts = await fts.search_posts(session, q)
        return {"post_ids": [p.id for p in posts]}

    @app.get("/fts/search-ranked")
    async def fts_search_ranked(q: str, session: SessionDep) -> dict[str, list[int]]:
        if not q.strip():
            raise HTTPException(status_code=400, detail="query empty")
        posts = await fts.search_posts_ranked(session, q)
        return {"post_ids": [p.id for p in posts]}

    return app


app = create_app()
