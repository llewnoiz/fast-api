"""2FA / TOTP — RFC 6238.

흐름:
    1. 사용자에게 _시크릿_ 발급 (base32) — 한 번만
    2. QR 코드 (otpauth://...) 스캔 → Google Authenticator 등록
    3. 로그인 시 6자리 코드 입력 → 검증

비교:
    Spring Security:  GoogleAuthenticator 라이브러리
    NestJS:           speakeasy (Node)
    Java 표준:        java-totp

저장:
    secret 은 _DB 에 암호화_ 후 보관 (서비스 마스터 키로 envelope encryption)
    backup codes (1회용) — 단방향 해시로 보관
"""

from __future__ import annotations

import pyotp


def generate_secret() -> str:
    """base32 인코딩된 _랜덤_ 시크릿 생성. 한 번만 호출, DB 에 저장."""
    return pyotp.random_base32()


def provisioning_uri(*, secret: str, account: str, issuer: str = "tender") -> str:
    """`otpauth://...` URI — QR 코드로 만들어 사용자에게 보여줌.

    예:
        otpauth://totp/tender:alice?secret=ABCD...&issuer=tender
    """
    return pyotp.TOTP(secret).provisioning_uri(name=account, issuer_name=issuer)


def verify(secret: str, code: str, *, valid_window: int = 1) -> bool:
    """6자리 코드 검증.

    `valid_window=1` — 시계 차이 보정 (이전/현재/다음 30초 윈도 허용).
    재사용 방지(replay): _처음 통과한 윈도_ 를 DB 에 기록 → 같은 윈도 재요청 거부.
    """
    return bool(pyotp.TOTP(secret).verify(code, valid_window=valid_window))
