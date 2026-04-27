"""콘솔 스크립트 진입점.

`pyproject.toml` 의 `[project.scripts]` 에 등록되면 `uv sync` 후:

    uv run greeter hello Alice --locale en
    uv run greeter shout "hello world"

처럼 호출 가능. Java `MANIFEST.MF` 의 `Main-Class` 또는 Maven `exec:java` 자리.
"""

from __future__ import annotations

import argparse
import sys

# 같은 패키지 안 → 상대 import
from .core import greet, shout


def _build_parser() -> argparse.ArgumentParser:
    """argparse 구성 — argparse 는 표준 라이브러리. 더 풍부한 게 필요하면
    `typer` (FastAPI 와 같은 저자) / `click` 추천."""
    parser = argparse.ArgumentParser(
        prog="greeter",
        description="간단한 인사말 / 외침 CLI (02 단계 학습용)",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_hello = sub.add_parser("hello", help="인사말 출력")
    p_hello.add_argument("name", help="대상 이름")
    p_hello.add_argument("--locale", default="ko", choices=["ko", "en", "ja"])

    p_shout = sub.add_parser("shout", help="외침")
    p_shout.add_argument("text", help="외칠 문장")

    return parser


def main(argv: list[str] | None = None) -> int:
    """프로세스 종료 코드를 반환 (관용: 0 = 정상, 1+ = 에러).

    Spring Boot `SpringApplication.run` 자리.
    """
    args = _build_parser().parse_args(argv)

    if args.cmd == "hello":
        print(greet(args.name, locale=args.locale))
    elif args.cmd == "shout":
        print(shout(args.text))
    else:  # pragma: no cover — argparse 가 required=True 로 막아줌
        return 1
    return 0


# `python -m greeter.cli` 로도 실행 가능
if __name__ == "__main__":
    sys.exit(main())
