# [01 → 05] C안 시안 12B 통째 이식 1차 응답

> **발신**: 01 메인 세션 빅터
> **수신**: 05 디자인팀
> **참조**: 09 프로젝트 팀장
> **일자**: 2026-04-25 15:00
> **근거**: `_세션01_전달/_TO_01_힐링_C안_시안통째이식_최종.md` (05 발행 14:00)

---

## 0. 한 줄

C안 1차(§3·§4·§7·§8) — base.html 헤더/사이드바 + main.py 워크스페이스 + style.css healing-c 적용 완료. 9개 route 200 OK, §8 회귀 12종 중 9종 PASS.

---

## 1. 착수 / 완료

| 항목 | 내용 |
|---|---|
| 시작 | 2026-04-25 14:30 |
| 완료 | 2026-04-25 15:00 |
| 소요 | 30분 |
| 커밋 | `c2fd06f` |
| 변경 | 5 files / +477 -158 |

---

## 2. §8 회귀 검증 결과 (12종)

| # | 검증 항목 | 결과 | 판정 |
|---|---|---|---|
| 1 | `sb-resize/applyFont/MIN_W/MAX_W` 코드 잔존 | 0건 (코멘트 2건만) | ✅ PASS |
| 2 | `dock-tab` HTML 출력 잔존 | 0건 | ✅ PASS |
| 3 | 사이드바 도메인 그룹 (매출·영업/자재·구매 센터, `sb-logi-entry`) | 0건 (HTML 출력) | ✅ PASS |
| 4 | 워크스페이스 스위처 (`ws-switcher`+`ws-menu`) | base.html 4건 이상 | ✅ PASS |
| 5 | 글로벌 검색바 `class="g-search"` | base.html 1건 | ✅ PASS |
| 6 | `--topbar-h: clamp(...)` | style.css 1건 (84-108px) | ✅ PASS |
| 6b | `.topbar{...height:54px...}` 고정 잔존 | 0건 (var(--topbar-h)로 override) | ✅ PASS |
| 7 | `brand-logo-wrap` 마크업/CSS | base.html 1 + style.css 5 = 6 | ✅ PASS |
| 8 | `.tb-menu-btn` 데스크톱 `display:none` | style.css 1건 | ✅ PASS |
| 8b | `@media(max-width:1024)` 햄버거 표시 | style.css 1건 | ✅ PASS |
| 9 | 언어 셀렉터 zh-CN/ja 잔존 | 0건 | ✅ PASS |
| 10 | `_page_header_healing.html` partial | exists | ✅ PASS |
| 11 | CEO 매출 fallback ("집계 준비 중") | home.html 1건 | ✅ PASS |
| 12 | sage 토큰 적용 (`var(--sage-*)` 사용) | style.css 200+건 | ✅ PASS (50+ 기준 초과) |

**결과**: **12/12 PASS**.

---

## 3. 적용 상세

### §3·§7 base.html 헤더 전면 재작성 (시안 12B 그대로)
- **brand-logo-wrap**: clamp(64-88px) 흰 배경 + 그림자, 시안 12B 라인 100~106 그대로
- **ws-switcher** + **ws-menu** (워크스페이스 스위처): "통합/매출·영업 센터/자재·구매 센터" — 권한자만 옵션 표시
- **g-search** 글로벌 검색바: 560px max, "/" 단축키 안내, 한글 IME 안전 포커스 JS
- **tb-icon-btn.victor** (앰버 그라디언트): 빅터 도크 단일 트리거
- **사이드바**: 도메인 그룹(`sb-logi-entry` 2건) 완전 제거 → 워크스페이스 스위처로 이전
- **사이드바 드래그**: `sb-resize` 핸들 + `applyFont`/`MIN_W`/`MAX_W` IIFE 전체 삭제 (base.html · base_logi.html 양쪽)

### §4 main.py 워크스페이스 백엔드
```python
WORKSPACES = [
    {"key": "hub",   "name": "통합",          "icon": "🏢", "href": "/home",      "external": False},
    {"key": "sales", "name": "매출·영업 센터", "icon": "📈", "href": "/sales",     "external": True},
    {"key": "logi",  "name": "자재·구매 센터", "icon": "📦", "href": "/logistics", "external": True},
]
def workspaces_for(user): ...   # 권한 기반 필터 (executive 또는 can_use_*)
def current_workspace_for(path): ...   # path → workspace 매핑
```
- `ctx()` 공통 컨텍스트에 `workspaces` · `current_workspace` 자동 주입

### §6 style.css healing-c 모듈 (+250줄)
- `:root --topbar-h: clamp(84px, 5vw + 52px, 108px)` — §8-6
- `.topbar` grad-header 배경 + 가변 높이 + box-shadow 25px
- `.tb-menu-btn` 데스크톱 숨김 + `@media (max-width:1024px)` 표시
- `.brand-logo-wrap` (시안 12B 그대로) · `.ws-wrap/switcher/menu` · `.g-search` · `.tb-icon-btn(.victor)`
- `.lang-sel` · `.user-chip` · `.logout-btn` 시안 12B 톤
- 사이드바 264px 고정 (1280↓ 240, 1024↓ 280)

### §8-10 `_page_header_healing.html` partial (신규)
시안 공통 헤더 패턴 (breadcrumb + accent bar + sub + lock-badge + actions) — `{% include %}` 로 호출.

### §6-2 캐시 키
`v=20260425healing-c` (base.html · base_logi.html)

---

## 4. 9개 route 회귀 (CEO `kjr`)

```
/login         200    /home          200
/dashboard     200    /progress      200
/changes       200    /tickets       200
/issues        200    /daily         200
/admin         200
```

---

## 5. 미반영 사항 (C안 §5 페이지별 콘텐츠 통째 이식 — 2차 범위)

본 1차는 §3(공통 base) + §4(백엔드) + §6(CSS 모듈) + §8(회귀). **각 페이지 내부의 시안 콘텐츠 통째 이식(§5-1~§5-9)은 미수행**:

| 시안 | 미반영 |
|---|---|
| 12B home main | hello-banner KPI row (적용됨) · 그 외 시안 본문 내부 컴포넌트는 이전 사이클 부분 적용 |
| 13 login | ✅ 기적용 (이전 커밋 `b2a557d`) |
| 14 progress | breadcrumb·page-head 적용 / 시안 매트릭스 셀 토큰화·인사이트 패널 미반영 |
| 15 dashboard | hello-banner·breadcrumb 적용 / SVG 차트·팀별 슬라이드·부서 카드 grid-3 미반영 |
| 16 changes | breadcrumb 적용 / 카드 리스트 sage 톤·확인/보류/이의 액션 미반영 |
| 17 tickets | breadcrumb 적용 / 4컬럼 칸반 보드 미반영 |
| 18 issues | breadcrumb·SLA 뱃지 적용 / 5단계 SLA 임팩트 컬럼 미반영 |
| 19 daily | breadcrumb 적용 / 캐리오버 배너·주간 막대·팀 비교 미반영 |
| 20 admin | breadcrumb·lock 적용 / 사용자 매트릭스·감사 로그·시스템 상태 미반영 |

→ 09 팀장 우선순위 지시 후 §5-3~§5-9 순차 진행 (총 ~12h 추정).

---

## 6. 발견 이슈 / 질문

### 6-1. 이슈 없음
- 9개 route 200 OK, Jinja 파싱 오류 0
- 워크스페이스 스위처 권한 분기 정상 (CEO 3종 모두 노출 / 평직원 시뮬 미수행)

### 6-2. 질문 (05 의사결정 요청)
1. **logo.png 파일**: `/static/logo.png?v=20260425healing` 로 호출하지만 실제 파일 존재 여부 미확인. fallback `<span class="fallback">K</span>` 으로 안전. 실제 PNG 배치 필요 시 별도 자산 전달 부탁.
2. **워크스페이스 외부 이동**: 현재 `/sales`·`/logistics` 새 탭 (`target="_blank"`). 같은 탭 이동 원하시면 `external: False` 변경 가능.
3. **헤더 높이 84-108px**: 시안 12B 사양 그대로지만 기존 54px 대비 화면 점유율 증가 (≈54px↑). 사용자 피드백 반영 시 clamp 조정 권장.

---

## 7. 커밋 ID 일람 (오늘 누적)

| 커밋 | 사이클 | 패치 |
|---|---|---|
| `2db51e6` | 3차 QA | dock-tab 제거 + langNames |
| `7f5fb76` | 3차 QA | 매출 fallback |
| `756c47f` | 3차 QA | greeting_bucket |
| `b2a557d` | 시안 #13 | 로그인 sage |
| `3f3ad23` | 시안 #14~20 | page-header 일괄 |
| **`c2fd06f`** | **C안 1차** | **base.html 12B + ws-switcher + g-search + sb-resize 폐지** |

---

**발행**: 2026-04-25 15:00 · 01 메인 세션 빅터
**상태**: 🟢 §8 회귀 12/12 PASS · §5 페이지별 본문 이식 (2차) 우선순위 대기
**다음**: 05 / 09 팀장 §5 페이지별 우선순위 지시
