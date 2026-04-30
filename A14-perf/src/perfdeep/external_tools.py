"""외부 도구 가이드 (코드 X — 사용법 노트).

본 모듈은 `pip install` 한 _후_ CLI 로 쓰는 도구들의 _사용 패턴_ 만 노트.
"""

# ──────────────────────────────────────────────────────────────
# py-spy — sampling profiler. 운영 _live_ 프로세스 분석.
#
# 설치:  uv tool install py-spy   또는  pip install py-spy
#
# 패턴:
#   py-spy top --pid <PID>                # top 같은 실시간 함수별 CPU%
#   py-spy record -o flame.svg --pid <PID> --duration 30
#                                          # 30초 flame graph
#   py-spy dump --pid <PID>               # 현재 stacktrace (모든 스레드)
#
# 강점:
#   - 운영 프로세스 _건드리지 않음_ (별도 프로세스가 ptrace)
#   - CPython 내부 stack 직접 읽음 — 거의 0 오버헤드
#   - Rust 작성 — 안정적
#
# 약점:
#   - macOS 는 `sudo` 필요 (System Integrity Protection)
#   - 컨테이너 내부는 SYS_PTRACE capability 필요
# ──────────────────────────────────────────────────────────────

# ──────────────────────────────────────────────────────────────
# memray — Bloomberg 의 메모리 프로파일러. flame graph + native.
#
# 설치:  pip install memray
#
# 패턴:
#   memray run -o out.bin script.py        # 추적 시작
#   memray flamegraph out.bin              # SVG flame graph
#   memray summary out.bin                 # 텍스트 요약
#   memray live                             # 실시간 monitor
#
# tracemalloc 보다 좋은 점:
#   - C 확장 메모리 추적 (numpy / Pillow)
#   - flame graph 시각화 강력
#   - jupyter 통합 (`%%memray_flamegraph`)
# ──────────────────────────────────────────────────────────────

# ──────────────────────────────────────────────────────────────
# pyinstrument — call tree sampling. cProfile 보다 가볍고 _읽기 쉬움_.
#
# 설치:  pip install pyinstrument
#
# 패턴:
#   pyinstrument script.py
#   pyinstrument --html -o report.html script.py
#
#   # FastAPI 미들웨어로
#   from pyinstrument import Profiler
#   @app.middleware("http")
#   async def profile_request(request, call_next):
#       p = Profiler(async_mode="enabled")
#       p.start()
#       resp = await call_next(request)
#       p.stop()
#       print(p.output_text())
#       return resp
#
# 강점: async 잘 추적. 짧은 보고서 (cProfile 길이 1/10).
# ──────────────────────────────────────────────────────────────

# ──────────────────────────────────────────────────────────────
# line_profiler — 라인 단위 시간. cProfile 다음 단계 (좁힌 후 사용).
#
# 설치:  pip install line_profiler
#
# 패턴:
#   @profile          # ← 데코레이터 (kernprof CLI 가 주입)
#   def slow_function(): ...
#
#   kernprof -l -v script.py   # -l 라인 단위, -v 결과 출력
#
# 흐름:
#   1. cProfile 로 _느린 함수_ 식별
#   2. line_profiler 로 _그 함수의 어느 라인_ 인지
# ──────────────────────────────────────────────────────────────

# ──────────────────────────────────────────────────────────────
# scalene — CPU + 메모리 + GPU. CMU 작품.
#
# 설치:  pip install scalene
#
# 패턴:
#   scalene script.py
#
# 강점: AI 기반 _최적화 제안_ ── "이 라인을 numpy 로 바꾸세요" 같은 제안
# ──────────────────────────────────────────────────────────────

# ──────────────────────────────────────────────────────────────
# CPU bound 가속 옵션
#
# 1. NumPy/SciPy ── 벡터 연산. 순수 Python 루프보다 _수십 배_ 빠름.
# 2. Numba `@njit` ── JIT 컴파일. 수치 코드만.
# 3. Cython ── C 로 컴파일. 모든 코드 가능. 컴파일 빌드 필요.
# 4. PyO3 (Rust) ── Rust 모듈 ── 가장 모던. cryptography / pydantic-core / polars 가 사용.
# 5. C 확장 (직접) ── 가장 빠르지만 부담 ↑.
#
# 추천 우선순위 (CPU 핫스팟 발견 시):
#   numpy 가능? → 벡터화
#   안 되면 → numba @njit (한 줄 추가)
#   더 깊으면 → Rust + PyO3
# ──────────────────────────────────────────────────────────────
