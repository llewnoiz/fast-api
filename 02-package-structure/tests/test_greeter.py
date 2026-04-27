"""greeter 패키지 테스트.

01 단계와 다른 점: **conftest.py 가 sys.path 를 조작하지 않는다**.
src layout + `pyproject.toml` 의 `packages = ["src/greeter"]` 설정으로
패키지가 _진짜로 설치_ 되어 있어 그냥 `from greeter import ...` 가 동작.

이게 src layout 이 권장되는 가장 큰 이유:
    "테스트가 _설치된 패키지_ 를 import 하도록 강제" → 빌드/배포 시점에야
    드러나는 import 에러를 _개발 중_ 에 미리 잡아낸다.
"""

from __future__ import annotations

import subprocess
import sys

import pytest
from greeter import __version__, greet, make_card, shout
from greeter._internal import greeting_for, normalize_name
from greeter.cli import main as cli_main


# ---------- 공개 API ----------
class TestPublicAPI:
    def test_version(self) -> None:
        assert __version__ == "0.1.0"

    @pytest.mark.parametrize(
        ("name", "locale", "expected"),
        [
            ("alice", "ko", "안녕, Alice!"),
            ("alice", "en", "Hello, Alice!"),
            ("BOB", "ja", "こんにちは, Bob!"),  # title() 가 BOB → Bob
            (" charlie ", "en", "Hello, Charlie!"),  # 공백 제거
            ("alice", "fr", "Hello, Alice!"),  # 모르는 locale → 영어 폴백
        ],
    )
    def test_greet(self, name: str, locale: str, expected: str) -> None:
        assert greet(name, locale=locale) == expected

    def test_shout(self) -> None:
        assert shout("hello") == "HELLO!!!"

    def test_make_card(self) -> None:
        card = make_card("alice", ["좋은 하루", "good day"], locale="ko")
        assert card == "안녕, Alice!\n  좋은 하루\n  good day"

    def test_make_card_no_lines(self) -> None:
        # 빈 lines 면 헤더만
        assert make_card("alice", [], locale="en") == "Hello, Alice!"


# ---------- 내부 모듈 (`_internal`) ----------
class TestInternal:
    """`_` 접두 모듈도 테스트는 가능. 단 외부 사용자에겐 노출 안 됨."""

    def test_normalize_name(self) -> None:
        assert normalize_name("  alice  ") == "Alice"

    @pytest.mark.parametrize(
        ("locale", "expected"),
        [("ko", "안녕"), ("en", "Hello"), ("ja", "こんにちは"), ("xx", "Hello")],
    )
    def test_greeting_for(self, locale: str, expected: str) -> None:
        assert greeting_for(locale) == expected


# ---------- CLI 진입점 ----------
class TestCLI:
    def test_hello_subcommand(self, capsys: pytest.CaptureFixture[str]) -> None:
        """argv 를 함수에 직접 넘겨 단위 테스트.

        capsys: pytest fixture, stdout/stderr 캡처 (Java 의 SystemOutRule 자리).
        """
        exit_code = cli_main(["hello", "alice", "--locale", "en"])
        assert exit_code == 0
        out = capsys.readouterr().out
        assert out.strip() == "Hello, Alice!"

    def test_shout_subcommand(self, capsys: pytest.CaptureFixture[str]) -> None:
        cli_main(["shout", "hello"])
        assert capsys.readouterr().out.strip() == "HELLO!!!"

    def test_module_run_via_python_dash_m(self) -> None:
        """`python -m greeter.cli ...` 도 동작해야 함 (관용적 진입 방식)."""
        result = subprocess.run(
            [sys.executable, "-m", "greeter.cli", "hello", "Bob", "--locale", "en"],
            capture_output=True,
            text=True,
            check=True,
        )
        assert result.stdout.strip() == "Hello, Bob!"


# ---------- 패키지 설치 상태 확인 ----------
class TestPackageInstallation:
    def test_console_script_installed(self) -> None:
        """`pyproject.toml` 의 [project.scripts] 가 등록되어 `greeter` 명령이 PATH 에 있음."""
        result = subprocess.run(
            ["greeter", "hello", "Alice", "--locale", "en"],
            capture_output=True,
            text=True,
            check=True,
        )
        assert result.stdout.strip() == "Hello, Alice!"
