"""FastAPI + Strawberry 통합.

마운트 방식:
    `GraphQLRouter` 가 자동으로 `/graphql` 에 POST + GraphiQL UI (개발) 제공.

context_getter:
    매 요청마다 _새 컨텍스트_ 생성 — _DataLoader 를 여기서 새로_ 만들어야 캐시가 요청 단위.

엔드포인트:
    POST /graphql                 GraphQL 쿼리 (실서버는 GET 도 일부 사용)
    GET  /graphql                 GraphiQL UI (개발 모드)
    GET  /healthz
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from strawberry.fastapi import GraphQLRouter

from gqlapi.data import DataStore, seed
from gqlapi.dataloader import make_posts_by_author_loader, make_user_loader
from gqlapi.schema import GraphQLContext, schema


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    store = DataStore()
    seed(store)
    app.state.store = store
    # use_dataloader 는 앱 단위 토글 (학습 비교용). 기본 True.
    app.state.use_dataloader = True
    yield


async def get_context(request: Request) -> GraphQLContext:
    """매 요청마다 _새로_ DataLoader 생성. 캐시는 _이 요청만_ 유지."""
    store: DataStore = request.app.state.store
    return GraphQLContext(
        store=store,
        user_loader=make_user_loader(store),
        posts_by_author_loader=make_posts_by_author_loader(store),
        use_dataloader=request.app.state.use_dataloader,
    )


def create_app() -> FastAPI:
    app = FastAPI(title="A10 — GraphQL", lifespan=lifespan)

    # context_getter 의 strawberry stub 가 None 반환만 허용한다고 표시 — 실제론 뭐든 OK.
    graphql_app: GraphQLRouter = GraphQLRouter(
        schema, context_getter=get_context  # type: ignore[arg-type]
    )
    app.include_router(graphql_app, prefix="/graphql")

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/admin/toggle-dataloader")
    async def toggle_dataloader(request: Request) -> dict[str, bool]:
        """DataLoader on/off 토글 — 학습용 (운영엔 절대 X)."""
        request.app.state.use_dataloader = not request.app.state.use_dataloader
        return {"use_dataloader": request.app.state.use_dataloader}

    @app.get("/admin/stats")
    async def stats(request: Request) -> dict[str, int | bool]:
        """현재 DataStore 의 호출 카운터 — N+1 검증용."""
        store: DataStore = request.app.state.store
        return {
            "users_by_ids_calls": store.users_by_ids_calls,
            "posts_by_author_calls": store.posts_by_author_calls,
            "use_dataloader": request.app.state.use_dataloader,
        }

    @app.post("/admin/reset-stats")
    async def reset_stats(request: Request) -> dict[str, str]:
        store: DataStore = request.app.state.store
        store.users_by_ids_calls = 0
        store.posts_by_author_calls = 0
        return {"status": "reset"}

    return app


app = create_app()
