# A10 — GraphQL (Strawberry)

REST 의 _대안_. 단일 엔드포인트로 _필요한 필드만_ 가져오는 쿼리 언어 + 런타임.

## 학습 목표

- **Strawberry** — Python code-first GraphQL (가장 Pythonic, 타입 힌트 그대로 활용)
- **Query / Mutation** — 진입점 + resolver
- **N+1 문제** — GraphQL 의 _구조적_ 함정 (10/A6 의 ORM N+1 과 같은 패턴, 다른 원인)
- **DataLoader 패턴** — 한 tick 동안 ID 모아 _배치 1번_ + 캐시
- **Context** — 요청 단위 DI (DataLoader / 인증 / DB 세션)
- **REST vs GraphQL** 트레이드오프

## 디렉토리

```
A10-graphql/
├── pyproject.toml
├── Makefile
├── README.md
├── src/gqlapi/
│   ├── __init__.py
│   ├── data.py                # 인메모리 DataStore + 시드 + 호출 카운터 (N+1 검증용)
│   ├── dataloader.py          # make_user_loader / make_posts_by_author_loader
│   ├── schema.py              # User / Post 타입 + Query / Mutation
│   └── main.py                # FastAPI + GraphQLRouter 통합
└── tests/
    ├── conftest.py
    ├── test_schema.py         # schema.execute() 직접 — 빠른 단위 테스트
    ├── test_dataloader.py     # N+1 vs DataLoader 호출 카운터 비교
    └── test_app.py            # FastAPI POST /graphql e2e
```

## 실행

```bash
cd A10-graphql
make all
make run
# → GraphiQL UI: http://127.0.0.1:8010/graphql
```

## REST vs GraphQL

| 항목 | REST | GraphQL |
|---|---|---|
| 엔드포인트 | 리소스 별 (`/users`, `/users/1/posts`) | 단일 (`/graphql`) |
| 데이터 모양 | 서버 결정 | 클라이언트 _쿼리_ 가 결정 (over/under fetch 해소) |
| 버전 관리 | URL 경로 (`/v1/`, `/v2/`) | 필드 deprecation 으로 _점진_ |
| 캐싱 | HTTP 캐시 자연스러움 | 어려움 (POST + 동적 응답) — Apollo Client 캐시 등 |
| 파일 업로드 | multipart 자연스러움 | multipart spec 별도 — REST 가 단순 |
| Subscription | SSE / WebSocket 따로 | GraphQL Subscription 표준화 |
| 학습 곡선 | 낮음 | 중간~높음 (스키마 + resolver + DataLoader) |
| 도구 | curl / Postman | GraphiQL / Apollo Studio (자동완성 강력) |
| N+1 | ORM 레벨에서 회피 | _resolver 레벨_ DataLoader 필수 |

**언제 GraphQL?**
- 모바일 / 다양한 클라이언트 — 각자 _필요한 필드만_ 가져가게
- 도메인 _그래프_ 가 풍부 (소셜, e-commerce, 게시판)
- 백엔드 팀 vs 프론트엔드 팀의 _데이터 협상_ 비용이 큼

**언제 REST?**
- 단순 CRUD / 마이크로서비스 _내부 통신_
- 캐싱 / CDN 이 핵심 (콘텐츠 사이트)
- 파일 IO 가 주 — multipart / Range / S3 직통

## DataLoader 패턴 — N+1 회피

**문제** (시드 7 post + 3 user):

```graphql
{ posts { id author { name } } }
```

naive resolver:
```
post 1 → load author 1   ← DB 1 round-trip
post 2 → load author 1   ← DB 1 round-trip (또 호출)
post 3 → load author 1   ← DB 1 round-trip
post 4 → load author 2   ← DB 1 round-trip
...
post 7 → load author 3   ← DB 1 round-trip
                          총 7 round-trip
```

**DataLoader**:

```
post 1 → loader.load(1)──┐
post 2 → loader.load(1)──┤
post 3 → loader.load(1)──┤
post 4 → loader.load(2)──┼──▶ batch_load([1, 1, 1, 2, 2, 3, 3])
post 5 → loader.load(2)──┤    DataLoader dedupe → [1, 2, 3]
post 6 → loader.load(3)──┤    DB 1 round-trip
post 7 → loader.load(3)──┘
                              ▼
                              { 1: row, 2: row, 3: row }
                              ▼
                              각 resolver 가 자기 row 받음
```

**테스트** (`test_dataloader.py`):
```python
# naive: 7 round-trip
assert store.users_by_ids_calls == 7
# DataLoader: 1 round-trip
assert store.users_by_ids_calls == 1
```

**핵심 규칙**:
1. DataLoader 는 _요청 단위_ — `context_getter` 에서 새로 만들기 (캐시가 stale 안 되도록)
2. 배치 함수 반환 _순서_ 가 입력 ID 순서와 _일치_ 해야
3. ID 별 None 도 자리 채우기 (`get_users_by_ids(ids)` 가 ids 길이만큼 반환)

비교:
- Node `dataloader` (Facebook 원조)
- Java `graphql-java` `BatchLoader`
- Go `graph-gophers/dataloader`

## Strawberry 기본 패턴

```python
@strawberry.type
class User:
    id: int
    name: str

    @strawberry.field
    async def posts(self, info: Info) -> list[Post]:
        ctx: GraphQLContext = info.context
        rows = await ctx.posts_by_author_loader.load(self.id)
        return [Post.from_row(r) for r in rows]

@strawberry.type
class Query:
    @strawberry.field
    async def users(self, info: Info) -> list[User]:
        return [User.from_row(r) for r in info.context.store.list_users()]

schema = strawberry.Schema(query=Query, mutation=Mutation)
```

**code-first vs schema-first**:
- **code-first** (Strawberry, graphene) — Python 코드가 진실, 스키마 자동 생성. _리팩토링 친화_
- **schema-first** (Ariadne) — `.graphql` 파일이 진실, 코드는 _바인딩_. _프론트와 명세 공유_ 친화

## Context 패턴

```python
class GraphQLContext(BaseContext):  # FastAPI 통합엔 BaseContext 상속 필수
    def __init__(self, store, user_loader, posts_by_author_loader, use_dataloader=True):
        super().__init__()
        self.store = store
        self.user_loader = user_loader
        ...

async def get_context(request: Request) -> GraphQLContext:
    """_매 요청마다 새로_. DataLoader 캐시는 이 요청에만."""
    return GraphQLContext(
        store=request.app.state.store,
        user_loader=make_user_loader(request.app.state.store),
        ...
    )

GraphQLRouter(schema, context_getter=get_context)
```

## GraphQL 에러 모델

REST: `4xx`/`5xx` HTTP 코드.

GraphQL: HTTP `200` + 응답 body 의 `errors` 필드.
```json
{
    "data": { "createPost": null },
    "errors": [{"message": "unknown author_id: 99", "path": ["createPost"]}]
}
```

**부분 성공도 가능**: `data` 가 일부 채워지고 `errors` 가 _부분_ 실패 알림.

→ 클라이언트가 `errors` _필수 검사_. Apollo Client 같은 라이브러리는 자동.

## 안티패턴

1. **DataLoader 없이 nested resolver** — N+1 폭발. _기본 인프라_ 로 항상 끼우기.
2. **DataLoader 를 _전역 싱글톤_ 으로** — 캐시가 _요청 사이_ 공유 → stale + 메모리 누수. _요청 단위_ 가 정답.
3. **resolver 에서 _큰 객체_ 반환** — GraphQL 은 클라이언트가 _필드 선택_ 하지만 resolver 는 _전체_ 가져옴. SQL `SELECT *` 와 동일한 함정.
4. **Mutation 입력 검증 안 함** — `errors` 필드는 표시될 뿐, _서버 측_ 검증 필수 (Pydantic).
5. **인증/인가 resolver 안 검사** — REST 미들웨어 한 번 vs GraphQL _resolver 마다_. 보통 _필드/타입 단위_ 권한.
6. **Subscription 스케일 무시** — _장기 연결_ + _상태_. WebSocket 인프라 (08) 필요.
7. **모든 것을 GraphQL 로** — 파일 업로드 / 단순 CRUD / OAuth callback 은 REST 가 단순.
8. **서버 측 페이지네이션 무시** — `posts` 가 100만 개면 _전체 반환_. **Relay Cursor Connection** 표준 따라가기.
9. **public API 에 introspection on** — 스키마 노출 — 운영은 _내부 GraphiQL_ 만.
10. **N+1 를 _ORM eager load_ 로 해결 시도** — GraphQL 은 _쿼리 모양_ 이 동적 → ORM 만으론 부족. DataLoader + ORM 둘 다 필요.

## 운영 도구 (참고)

| 영역 | 도구 |
|---|---|
| Python lib | **Strawberry** (code-first), Ariadne (schema-first), graphene (legacy) |
| 게이트웨이 | Apollo Router, GraphQL Mesh, GraphQL Hive |
| 모니터링 | Apollo Studio, GraphQL Hive, NewRelic GraphQL |
| 클라이언트 | Apollo Client, urql, Relay (Facebook), graphql-request |
| Federation | Apollo Federation (스키마 합치기 - 마이크로서비스) |
| Codegen | graphql-code-generator (TS), graphql-codegen, strawberry codegen |
| 보안 | graphql-armor (rate limit / depth limit), persisted queries |

## 직접 해보기 TODO

- [ ] GraphiQL 에서 `users { posts { author { posts { ... } } } }` _순환 쿼리_ — depth limit 의 필요성 체감
- [ ] `pagination` 추가: `posts(first: 10, after: "cursor")` Relay 표준 cursor connection
- [ ] `Subscription` 추가 — A8 의 SSE / WebSocket 으로 새 post 알림
- [ ] DataLoader 의 `cache_key_fn` 으로 _복합 키_ 지원
- [ ] 에러 처리 정교화 — Union type 으로 `CreatePostResult = Post | ValidationError`
- [ ] `@strawberry.permission_classes` 로 인증/인가 — A5 의 JWT 와 결합
- [ ] persisted queries — 클라이언트가 _쿼리 hash_ 만 보내고 서버는 매핑 (대역폭 절감)
- [ ] Federation — A1~A15 의 마이크로서비스를 GraphQL 게이트웨이로 통합

## 다음 단계

**A11 — DDD / 헥사고날 아키텍처**. 15 의 tender 를 _전술적 DDD_ 로 정련 — Aggregate / Value Object / Domain Event + Ports & Adapters 분리.
