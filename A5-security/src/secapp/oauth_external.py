"""OAuth 2.0 3rd party 로그인 (Google / GitHub).

09 의 _password flow_ 와 다른 _authorization code flow + PKCE_:
    1. 사용자 → /auth/google 클릭 → Google 로 redirect
    2. Google 에서 로그인 + 동의 → 우리 서비스 콜백 (/auth/callback?code=...)
    3. 우리 서버 → Google 에 code + secret 으로 _토큰 교환_
    4. access_token 으로 사용자 정보 조회 → 우리 DB 에 사용자 생성/연결
    5. 우리 JWT 발급해서 반환

비교:
    Spring Security:  oauth2 client (yml 설정만으로 활성화)
    NestJS:           passport-google, passport-github
    Auth0/Clerk:      managed 솔루션

PKCE (RFC 7636):
    Authorization code 가중간자에게 탈취돼도 _verifier_ 없이는 토큰 교환 불가.
    SPA / 모바일 앱 권장. authlib 가 자동 처리.

⚠️ 본 코드는 _구조 시연_. 실제 동작엔 Google/GitHub Developer Console 에서
   Client ID / Secret 발급 + Redirect URI 등록 필요. 환경변수 설정 후 사용.
"""

from __future__ import annotations

from authlib.integrations.starlette_client import OAuth
from fastapi import APIRouter, FastAPI, Request
from starlette.config import Config

# Settings — 운영에선 pydantic-settings 와 통합. 학습용 starlette Config.
_config = Config(".env")


def configure_oauth() -> OAuth:
    """OAuth 클라이언트 설정 — 환경변수에서 client_id/secret 읽음."""
    oauth = OAuth(_config)

    # Google — OpenID Connect 자동 metadata
    oauth.register(
        name="google",
        client_id=_config("GOOGLE_CLIENT_ID", default=""),
        client_secret=_config("GOOGLE_CLIENT_SECRET", default=""),
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )

    # GitHub — OAuth 2.0 (OIDC X)
    oauth.register(
        name="github",
        client_id=_config("GITHUB_CLIENT_ID", default=""),
        client_secret=_config("GITHUB_CLIENT_SECRET", default=""),
        access_token_url="https://github.com/login/oauth/access_token",
        authorize_url="https://github.com/login/oauth/authorize",
        api_base_url="https://api.github.com/",
        client_kwargs={"scope": "user:email"},
    )

    return oauth


def install_oauth_routes(app: FastAPI, oauth: OAuth) -> None:
    """앱 팩토리에서 호출 — /auth/google, /auth/google/callback 등록."""
    router = APIRouter(prefix="/auth", tags=["oauth-external"])

    @router.get("/google")
    async def login_google(request: Request) -> object:
        # PKCE 자동, state 자동 (CSRF 방지 — authlib 가 세션에 저장)
        redirect_uri = request.url_for("auth_google_callback")
        return await oauth.google.authorize_redirect(request, str(redirect_uri))

    @router.get("/google/callback", name="auth_google_callback")
    async def google_callback(request: Request) -> dict:
        # code → 토큰 교환 + ID 토큰 검증
        token = await oauth.google.authorize_access_token(request)
        user_info = token.get("userinfo")
        # 실무: 우리 DB 에 사용자 upsert + JWT 발급해서 반환 (또는 쿠키 + redirect)
        return {
            "provider": "google",
            "email": user_info.get("email") if user_info else None,
            "name": user_info.get("name") if user_info else None,
        }

    @router.get("/github")
    async def login_github(request: Request) -> object:
        redirect_uri = request.url_for("auth_github_callback")
        return await oauth.github.authorize_redirect(request, str(redirect_uri))

    @router.get("/github/callback", name="auth_github_callback")
    async def github_callback(request: Request) -> dict:
        token = await oauth.github.authorize_access_token(request)
        # GitHub 은 user info 별도 호출
        resp = await oauth.github.get("user", token=token)
        return {"provider": "github", "user": resp.json()}

    app.include_router(router)
