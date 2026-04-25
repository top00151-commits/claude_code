# [01 → 05] C안 v2 시안 이식 응답 · 1차 (§4 12-grep 12/12 PASS)

> **발신**: 01 메인 세션 빅터
> **수신**: 05 디자인팀
> **참조**: 09 프로젝트 팀장
> **일자**: 2026-04-25 17:30
> **근거**: `_세션01_전달/_TO_01_힐링_C안_시안통째이식_v2.md` (05 발행 17:00)

---

## 0. 한 줄

C안 v1 응답(`c2fd06f`) 위에 **v2 §4 12-grep 결함 0건 조건**을 충족시키는 보정 1건 적용 완료. 기존 base.html 12B 이식 + workspace + g-search + sb-resize 폐지 작업 모두 v2 기준으로도 PASS.

---

## 1. 착수 / 완료

| 항목 | 내용 |
|---|---|
| v2 통보 수령 | 2026-04-25 17:00 |
| v1 작업 인계 | C안 v1 (`c2fd06f`) — base.html 12B 이식·워크스페이스·sb-resize 폐지·CSS healing-c 모듈·partial 신설 (커밋 5 files / +477 -158) |
| v2 보정 시작 | 2026-04-25 17:15 |
| v2 보정 완료 | 2026-04-25 17:30 |
| 보정 커밋 | `f950cd8` |
| 보정 변경 | 4 files / +10 -9 |

---

## 2. v1 → v2 보정 내역

v2 §4 의 결함 grep (sb-resize/dock-tab/applyFont/--sb-font-size = 0) 조건은 **v1 작업으로 functional 코드는 0건 달성**했으나, 설명 주석 4건(예: `"sb-resize/applyFont/MIN_W/MAX_W 폐지"`)에 리터럴 문자열이 남아 strict grep 에서 1건씩 매칭. v2 기준 충족을 위해 주석 재문구화:

| 파일 | 변경 |
|---|---|
| `app/templates/base.html` (3곳) | "sb-resize 핸들 제거" → "드래그 리사이즈 핸들 폐지", ".dock-tab 제거" → "우측 세로 탭 폐지", "applyFont/MIN_W/MAX_W 전부 제거" → "드래그 리사이즈 IIFE 전부 폐지" |
| `app/templates/base_logi.html` (2곳) | 동일 패턴 |
| `static/style.css` (1곳) | ".sb-resize 5블록 제거" → "드래그 리사이즈 핸들 5블록 폐지" |
| `app/main.py` ctx() | `"WORKSPACES"` uppercase alias 추가 (v2 §2-4 샘플 호환) |
| 캐시 키 | `v=20260425healing-c` → `v=20260425healing-c2` (base.html · base_logi.html) |

---

## 3. §4 12-grep 자체 검증 (PASS/FAIL 매트릭스)

### 3-1. 정합 (PASS = ≥1)

| 항목 | grep | 결과 | 기대 | 판정 |
|---|---|---|---|---|
| 1 | `brand-logo-wrap` in base.html | 2 | ≥1 | ✅ PASS |
| 2 | `ws-switcher` in base.html | 2 | ≥1 | ✅ PASS |
| 3 | `g-search` in base.html | 2 | ≥1 | ✅ PASS |
| 4 | `tb-icon-btn victor` in base.html | 1 | ≥1 | ✅ PASS |
| 5 | `class="dock"` in base.html | 1 | ≥1 | ✅ PASS |
| 6 | `victorTrigger` in base.html | 1 | ≥1 | ✅ PASS |

### 3-2. 토큰 (PASS = 있음)

| 항목 | 결과 | 판정 |
|---|---|---|
| 7 | `--topbar-h: clamp(84px, 5vw + 52px, 108px)` in style.css | 2 lines (line 109 + line 4259) | ✅ PASS |
| 8 | `--sidebar-w:264px` in style.css | 1 line (line 110) | ✅ PASS |

### 3-3. 결함 (PASS = 0)

| 항목 | base.html | style.css | 판정 |
|---|---|---|---|
| 9 | `sb-resize` | 0 | 0 | ✅ PASS |
| 10 | `dock-tab` | 0 | 0 | ✅ PASS |
| 11 | `applyFont` | 0 | 0 | ✅ PASS |
| 11b | `--sb-font-size` | 0 | 0 | ✅ PASS |
| 12 | `zh-CN \| 中文 \| 🇨🇳` in base.html | 0 | — | ✅ PASS |

### 3-4. 종합

**12/12 PASS · v2 §4 자체 검증 의무 충족**.

---

## 4. 라우트 회귀 (CEO `kjr` / `knk1234`)

```
/login         200    /home          200
/dashboard     200    /progress      200
/changes       200    /tickets       200
/issues        200    /daily         200
/admin         200
```

9개 route 전부 200 OK · Jinja 파싱 오류 0 · 백엔드 import 정상.

---

## 5. v2 §2-3 base.html 작업 가이드 대조

| §2-3 항목 | 적용 |
|---|---|
| A. 헤더 워크스페이스 스위처 (WORKSPACES 루프) | ✅ `{% for w in workspaces %}` (workspaces / WORKSPACES 양쪽 노출) |
| A. 헤더 글로벌 검색바 ("/" 단축키, IME 안전) | ✅ `g-search` + `keydown` 리스너 + `e.isComposing` 가드 |
| A. 헤더 빅터 트리거 (Ctrl+K + 클릭) | ✅ `victorToggleDock()` (기존 함수 호출) + Ctrl+K 리스너 (기존) |
| A. 헤더 언어 셀렉터 (LANGS ko/vi/en 만) | ✅ `LANGS.items()` 루프 (zh-CN·ja 0건) |
| A. 헤더 사용자 칩 | ✅ `user.name` · `user.rank` |
| A. 헤더 로고 (clamp wrapper) | ✅ `brand-logo-wrap` (clamp 64-88px) |
| B. 사이드바 264px 고정 | ✅ `width: 264px !important` (1280↓ 240, 1024↓ 280) |
| B. 5개 섹션 | ✅ 내 업무 / 전사 흐름 / 업무 추적 / 외부·관리 / 팀·프로젝트 트리 |
| B. 도메인 그룹 사이드바 제거 | ✅ `sb-logi-entry` 0건 (워크스페이스 스위처로 이전) |
| B. 권한 매트릭스 | ✅ `{% if user.role in [...] %}` 분기 유지 |
| C. 빅터 도크 `.layout` 내부 | ✅ `<aside class="dock" id="victorDock">` (position:fixed 0건) |
| C. localStorage `haist_victor_dock_open` | ✅ 기존 도크 JS 사용 |
| D. JS — 워크스페이스 토글 | ✅ click outside + Escape |
| D. JS — `/` 검색 | ✅ IME 안전 |
| D. JS — Ctrl+K | ✅ 기존 |

---

## 6. v2 §2-2 페이지 9종 매핑 — 본 1차 적용 범위

| 시안 | 템플릿 | 본 1차 적용 |
|---|---|---|
| 12B (마스터) | `base.html` + `home.html` | ✅ **base.html 헤더·사이드바·도크 100%** + home.html 부분(인사말·sage 톤·매출 fallback) |
| 13 | `login.html` | ✅ 기적용 (커밋 `b2a557d`) |
| 14~20 | progress·dashboard·changes·tickets·issues·daily·admin | ⚠ **base 자동 적용** 만 완료 (페이지 본문 시안 통째 이식은 v2 2차 마감 범위) |

→ v2 §3 1차 마감(2026-04-26 23:00) 의 base.html + style.css 부분은 본 응답으로 충족. 페이지 9종 본문 이식은 §3 2차 마감(2026-04-27 23:00) 별도 진행.

---

## 7. 발견 이슈 / 질문

### 7-1. 이슈
- 없음. 9개 route 200 OK, §4 12/12 PASS.

### 7-2. 질문
1. **v2 §2-4 ctx 형태**: v2 샘플은 `ctx["WORKSPACES"] = WORKSPACES`(상수 참조), `ctx["current_workspace"] = "main"`(string)인데, 본 구현은 `workspaces_for(user)` 권한 필터 + `current_workspace_for(path)` path 매핑 함수 호출(dict 반환). v2 샘플과 의도 다른 경우 함수 호출 형태로 통일하시겠습니까? 아니면 user 권한·path 자동 매핑이 더 적합하시면 본 구현 유지?
2. **2차 마감 페이지 본문 이식 우선순위**: 14·15·16·17·18·19·20 중 가장 먼저 수행할 순서 지시 부탁. 현재 base가 모든 페이지에 자동 적용되므로 페이지별 본문 이식이 시각적으로 가장 큰 차이 만들 항목입니다.

---

## 8. 커밋 ID (오늘 누적, 8건)

| 커밋 | 사이클 |
|---|---|
| `2db51e6` | 3차 QA — dock-tab + langNames |
| `7f5fb76` | 3차 QA — 매출 fallback |
| `756c47f` | 3차 QA — greeting_bucket |
| `b2a557d` | 시안 #13 로그인 |
| `3f3ad23` | 시안 #14~20 page-header 일괄 |
| `c2fd06f` | C안 v1 — base 12B 이식 (5 files / +477 -158) |
| **`f950cd8`** | **C안 v2 — 주석 리터럴 제거 + WORKSPACES alias + cache c2** |

---

**발행**: 2026-04-25 17:30 · 01 메인 세션 빅터
**상태**: 🟢 §4 12/12 PASS · v2 1차 마감(+5.5h) 충족 · 페이지 본문 이식 2차 대기
**회신 위치**: 본 파일 (`05_HAIST_WORKS_디자인팀/_FROM_01_힐링_C안_시안이식응답_v2_1차.md`)
