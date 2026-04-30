"""OWASP Top 10 — 안티패턴 vs 방어 코드 (학습용).

OWASP Top 10 (2021):
    A01 — Broken Access Control          (IDOR, 권한 체크 누락)
    A02 — Cryptographic Failures         (평문 비번, 약한 해시)
    A03 — Injection                      (SQL/NoSQL/OS command/SSRF)
    A04 — Insecure Design                (설계 차원)
    A05 — Security Misconfiguration      (CORS *, debug=True, default secret)
    A06 — Vulnerable Components          (의존성 취약점 — pip-audit, dependabot)
    A07 — Authentication Failures        (약한 비번 정책, brute-force 방치)
    A08 — Software/Data Integrity        (서명 안 된 업데이트, supply chain)
    A09 — Logging/Monitoring Failures    (12 단계 떡밥)
    A10 — SSRF                           (사용자 입력 URL 그대로 호출)
"""

from __future__ import annotations

import re
import urllib.parse
from ipaddress import ip_address

import httpx

# ============================================================================
# A01 — IDOR (Insecure Direct Object Reference)
# ============================================================================
#
# ❌ 안티패턴:
#   @app.get("/orders/{id}")
#   async def get_order(id: int, db):
#       return await db.get(Order, id)   # ← 다른 사용자 주문 조회 가능!
#
# ✅ 방어:
# ============================================================================


def authorize_order_access(*, current_user_id: int, order_owner_id: int) -> None:
    """본인 주문만 — admin role 은 별도 검사."""
    if current_user_id != order_owner_id:
        # FastAPI 라우트에서: raise HTTPException(403)
        raise PermissionError("forbidden — not your order")


# ============================================================================
# A03 — Injection
# ============================================================================
#
# ❌ SQL injection (raw query 절대 X):
#   await session.execute(f"SELECT * FROM users WHERE name = '{name}'")
#
# ✅ 파라미터 바인딩 (10 단계의 SQLAlchemy 가 _자동_):
#   stmt = select(User).where(User.name == name)
#   await session.execute(stmt)
#
# ❌ OS command:
#   os.system(f"convert {filename} out.png")    # filename 에 ; rm -rf 가능
#
# ✅ 인자 분리:
#   subprocess.run(["convert", filename, "out.png"], check=True, shell=False)
# ============================================================================


# ============================================================================
# A10 — SSRF (Server-Side Request Forgery)
# ============================================================================
#
# 사용자 입력 URL 을 _그대로_ 호출하면, 내부 메타데이터 서비스(AWS 169.254.169.254)
# 또는 사내망 접근 가능 → 자격증명 유출.
# ============================================================================


_PRIVATE_HOSTS = re.compile(
    r"^(localhost|127\.|10\.|172\.(1[6-9]|2\d|3[01])\.|192\.168\.|169\.254\.|::1$|fc00:|fe80:)"
)


def is_private_host(host: str) -> bool:
    """internal/loopback/link-local 검사. SSRF 1차 방어."""
    if _PRIVATE_HOSTS.match(host):
        return True
    try:
        ip = ip_address(host)
        return bool(ip.is_private or ip.is_loopback or ip.is_link_local)
    except ValueError:
        return False


def safe_external_url(url: str, *, allowed_hosts: set[str] | None = None) -> str:
    """외부 호출 _전_ 검증.

    1) URL 파싱 — 스킴/호스트 추출
    2) 스킴 화이트리스트 (http/https 만)
    3) 호스트 _차단_ (private IP / localhost) — DNS rebinding 방어 위해
       _재조회_ + IP 검사 권장 (운영급)
    4) (선택) allowed_hosts 화이트리스트
    """
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError(f"scheme not allowed: {parsed.scheme}")
    if not parsed.hostname:
        raise ValueError("no hostname")
    if is_private_host(parsed.hostname):
        raise ValueError(f"private host blocked: {parsed.hostname}")
    if allowed_hosts and parsed.hostname not in allowed_hosts:
        raise ValueError(f"host not in allowlist: {parsed.hostname}")
    return url


async def fetch_with_ssrf_guard(client: httpx.AsyncClient, url: str) -> httpx.Response:
    """외부 호출 _안전_ wrapper."""
    safe = safe_external_url(url)
    return await client.get(safe, timeout=5.0, follow_redirects=False)
    # follow_redirects=False — 302 로 internal 리다이렉트 방지. 또는 redirect 도 체크.


# ============================================================================
# A02 — Cryptographic Failures
# ============================================================================
#
# ❌ MD5 / SHA1 패스워드 해시 — 무지개 테이블 / GPU 공격
# ✅ bcrypt / argon2 (09 단계)
#
# ❌ 비밀번호 복호화 가능한 양방향 암호화 저장
# ✅ 단방향 해시 — 복구는 _재설정_ 만
#
# ❌ 비밀 헤더 / 시크릿 평문 로깅
# ✅ structlog 의 _processor_ 로 민감 키 마스킹 (12 단계 응용)
# ============================================================================


# ============================================================================
# A05 — Security Misconfiguration
# ============================================================================
#
# 체크리스트:
#   - DEBUG=False (운영)
#   - CORS allow_origins=["*"] + allow_credentials=True _금지_ (브라우저 거부)
#   - secret 기본값 X (.env / Vault)
#   - admin endpoint 외부 노출 X (네트워크 ACL)
#   - 에러 응답에 _스택트레이스_ 노출 X (07 단계 핸들러)
#   - HTTP 헤더: Strict-Transport-Security, X-Content-Type-Options, X-Frame-Options
# ============================================================================


def secure_headers() -> dict[str, str]:
    """미들웨어로 모든 응답에 추가할 보안 헤더."""
    return {
        # HTTPS 강제 (1년)
        "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
        # MIME sniffing 방지 (XSS 한 단계 방어)
        "X-Content-Type-Options": "nosniff",
        # iframe 임베딩 방지 (clickjacking)
        "X-Frame-Options": "DENY",
        # Referer 정책
        "Referrer-Policy": "strict-origin-when-cross-origin",
        # 권한 정책 — 카메라/마이크 등 차단 기본
        "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
    }
