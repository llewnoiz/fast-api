# A1 — 다국어 처리 (i18n) 🎓

전체 부록의 _마지막 빈 자리_. 다국어 (영어 / 한국어 / 일본어) FastAPI 앱.

## 학습 목표

- **Accept-Language 협상** — RFC 4647 헤더 파싱 + q-value 정렬 + supported 매칭
- **gettext 인터페이스** — `_()` / `gettext` / `ngettext` 단복수
- **메시지 카탈로그** — dict 기반 (학습) vs `.po` / `.mo` (운영)
- **Pydantic 검증 메시지 번역** — `ValidationError` → 다국어 envelope
- **Babel 포맷팅** — 통화 / 숫자 / 날짜 / 상대 시간 _로케일별_
- **미들웨어** — 매 요청에 `contextvars` locale 설정 + `Content-Language` 응답 헤더

## 디렉토리

```
A1-i18n/
├── pyproject.toml
├── Makefile
├── README.md
├── src/i18napp/
│   ├── __init__.py
│   ├── locale.py              # Accept-Language 파싱 + negotiate + contextvars
│   ├── catalog.py             # MESSAGES dict + gettext + ngettext
│   ├── babel_setup.py         # format_money / format_d / format_relative / display_locale_name
│   ├── pydantic_messages.py   # ValidationError → 다국어 변환
│   ├── middleware.py          # LocaleMiddleware (cookie > Accept-Language > default)
│   └── main.py                # FastAPI 앱 + 데모 라우트
└── tests/
    ├── test_locale.py         # 헤더 파싱 / negotiation
    ├── test_catalog.py        # gettext / ngettext / fallback
    ├── test_babel_setup.py    # 통화 / 숫자 / 날짜 / 상대시간
    ├── test_pydantic_messages.py
    └── test_app.py            # FastAPI e2e (미들웨어 동작)
```

## 실행

```bash
cd A1-i18n
make all          # ruff + mypy + 41 tests
make run          # http://127.0.0.1:8001/docs

# 헤더로 locale 변경
curl -H 'Accept-Language: ko' http://127.0.0.1:8001/greet?name=alice
# → {"message": "안녕하세요, alice 님!"}
```

## Accept-Language 협상

```
Accept-Language: ko-KR,ko;q=0.9,en;q=0.8,*;q=0.5
       ↓ 파싱 (q 내림차순 정렬)
       [ko-KR (q=1), ko (q=0.9), en (q=0.8), * (q=0.5)]
       ↓ supported = ["ko", "en", "ja"]
       1) ko-KR 정확 매치? supported 에 없음
       2) ko-KR 의 primary "ko"? ✅ → "ko"
```

**locale 우선순위 (운영 권장)**:
1. **URL prefix** (`/ko/...`, `/en/...`) — SEO 친화 (검색엔진이 언어별 URL 좋아함)
2. **쿠키** (`lang=ko`) — 사용자 선택 영구화
3. **사용자 프로필** — 로그인 시 DB 값
4. **JWT claim** — 토큰에 `locale`
5. **Accept-Language** 헤더
6. **default** (en)

## gettext 인터페이스

```python
from i18napp.catalog import gettext, ngettext, _

# 단순
_("greeting", name="alice")             # locale=현재 contextvars → "Hello, alice!"
_("greeting", locale="ko", name="alice")  # 명시 → "안녕하세요, alice 님!"

# 단복수
ngettext("items_one", "items_other", 5)   # → "5 items" (en) / "5 개 항목" (ko)
```

**누락 fallback 체인**:
```
요청 locale 의 catalog → primary subtag (ko-KR → ko) → en → key 자체 (디버깅 친화)
```

## 운영 vs 학습 메시지 관리

**학습** (본 모듈):
```python
MESSAGES = {"ko": {"greeting": "안녕하세요, $name 님!"}, ...}   # 인메모리 dict
```

**운영** (Babel + gettext 표준):
```bash
# 1) 코드에서 _("...") 마커
# 2) 추출
pybabel extract -o messages.pot src/

# 3) 언어별 .po 생성 / 갱신
pybabel init -i messages.pot -d locales -l ko
# 또는 갱신: pybabel update -i messages.pot -d locales

# 4) 번역가가 ko/messages.po 편집
# 5) .mo 컴파일
pybabel compile -d locales

# 6) 런타임
import gettext
trans = gettext.translation("messages", "locales", languages=["ko"])
trans.install()    # 또는 _ = trans.gettext
```

## Pydantic 검증 메시지 번역

```python
class UserModel(BaseModel):
    name: str = Field(min_length=2)
    email: EmailStr

try:
    UserModel.model_validate({})
except ValidationError as e:
    errors = translate_validation_error(e, locale="ko")
    # [{"field": "name", "type": "missing", "message": "name 은(는) 필수입니다"}, ...]
```

**한계**:
- Pydantic 의 영문 메시지는 _커스터마이즈 못 함_ (v2 부터 옵션은 있지만 제한적)
- `pydantic-core` 가 Rust 작성 — 메시지 _직접 변환_ 어려움
- 실용 패턴: 위처럼 _후처리_ 또는 클라이언트가 _key 로 받고 자체 번역_

## Babel 포맷팅 (CLDR 기반)

```python
from i18napp.babel_setup import format_money, format_number, format_relative

format_money(1234.56, "USD", "en")    # → "$1,234.56"
format_money(1234, "KRW", "ko")        # → "₩1,234" (KRW 정수)
format_money(1234.56, "EUR", "de")     # → "1.234,56 €" (독일어 형식)

format_number(1234567.89, "en")        # → "1,234,567.89"
format_number(1234567.89, "de")        # → "1.234.567,89"

format_relative(-3600, "en")           # → "1 hour ago"
format_relative(-3600, "ko")           # → "1시간 전"
```

비교:
- Java: `java.util.Locale` + `NumberFormat` / `DateTimeFormatter`
- JS: `Intl.NumberFormat` / `Intl.DateTimeFormat` (ECMAScript Internationalization API)
- Rust: ICU4X

## 미들웨어 — contextvars 패턴

```python
class LocaleMiddleware:
    async def dispatch(self, request, call_next):
        # 1) 쿠키 우선
        # 2) Accept-Language
        # 3) default
        locale = ...
        set_locale(locale)         # contextvars 에 저장
        response = await call_next(request)
        response.headers["content-language"] = locale
        return response
```

**왜 `contextvars`?**
- 비동기 안전 — 동시 요청끼리 _격리_
- 라우트 / 의존성 / 도메인 layer 어디서든 `get_locale()` 으로 접근 — _인자로 전달 X_

## 안티패턴

1. **메시지 _코드에 하드코딩_** — 번역 불가. 항상 `_("...")` 마커.
2. **f-string 안에 변수 보간** — `_(f"hello {name}")` ── 키가 _매번_ 달라져 추출 불가. `_("hello {name}", name=name)`.
3. **단복수를 `if n == 1:`** — 영어만 OK. 폴란드어 / 러시아어 _3가지_ 형태. `ngettext` 또는 ICU MessageFormat.
4. **클라이언트 IP 로 locale 추측** — VPN / 여행 / proxy 부정확. 사용자 _명시적 선택_ 가능해야.
5. **응답에 `Content-Language` 누락** — CDN / 캐시가 _다른 언어 응답_ 섞어 캐싱.
6. **카탈로그를 _런타임 reload 안 함_** — 새 언어 추가 시 재배포. 운영은 _hot reload_ 옵션.
7. **Accept-Language q-value 무시** — `en;q=0.1,ko;q=0.9` → `en` 선택 = 잘못. 정렬 필수.
8. **번역가에게 `.py` 파일 직접 줌** — 번역가는 `.po` 또는 _전용 도구_ (Crowdin, Weblate, Lokalise) 친화.
9. **숫자 / 날짜 포맷도 영어로** — 통화 `$` 가 한국 사용자에 _불편_. Babel 사용.
10. **언어 _전환 UI_ 없음** — Accept-Language 만 신뢰. 명시적 선택 + 쿠키 영구화 권장.

## 운영 도구 (참고)

| 영역 | 도구 |
|---|---|
| **번역 관리** | Crowdin, Weblate (오픈소스), Lokalise, Phrase, Transifex |
| **메시지 추출** | pybabel (`extract` / `init` / `update` / `compile`) |
| **카탈로그 형식** | `.po` / `.mo` (gettext), JSON (i18next), YAML (Rails) |
| **고급 메시지 형식** | ICU MessageFormat (Java/JS/Python via `babel`), Mozilla Fluent |
| **시간대** | `zoneinfo` (Python 3.9+), `babel.dates` 의 timezone-aware |
| **RTL 언어** | 아랍어 / 히브리어 — CSS `dir="rtl"` + 메시지 양방향 |

## 직접 해보기 TODO

- [ ] `pybabel` 로 _진짜_ `.po` / `.mo` 워크플로우 ── extract → init → translate → compile
- [ ] 본 카탈로그를 `.po` 로 변환 + `gettext.translation()` 으로 로딩 (dict 대체)
- [ ] **ICU MessageFormat** 도입 ── 폴란드어 _복수형 3가지_ 정확히 처리
- [ ] URL prefix 라우팅 ── `/ko/orders` / `/en/orders` ── SEO 친화
- [ ] 클라이언트 측 i18n ── 백엔드는 _key + params_ 만 반환, 프론트엔드 (i18next / formatjs) 가 번역
- [ ] **RTL** 지원 ── 아랍어 (`ar`) 또는 히브리어 (`he`) 추가, `dir="rtl"` 응답
- [ ] Crowdin / Weblate 같은 SaaS 통합 ── 번역가 워크플로
- [ ] 본편 15 단계 (`tender`) 에 본 i18n 통합 ── 검증 메시지 / 응답 envelope 다국어

## 🎓 진짜 마지막 — 전체 졸업

본 트랙으로 **본편 15단계 + 부록 A1 ~ A14 = 28 단계** 완성.
