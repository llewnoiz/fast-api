"""pytest 가 src/ 안의 모듈을 import 할 수 있도록 sys.path 조정."""

from __future__ import annotations

import sys
from pathlib import Path

# tests/ 의 부모 = 01-python-basics/, 그 아래 src/ 를 path 에 추가
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
