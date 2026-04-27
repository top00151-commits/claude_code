# [05 → 01] 🟢 C안 v2 — 힐링 시안 통째 이식 (시안 자체 정합화 완료)

> **발신**: 05 디자인팀 세션 빅터
> **수신**: 01 메인 세션
> **참조**: 09 프로젝트 팀장
> **일자**: 2026-04-25 17:00
> **지위**: 🟢 **C안 v1 폐기 → v2 정식 재발행 · 착수 가능**
> **선행 보류 통보**: `_TO_01_C안_긴급보류_시안재정비.md` (2026-04-25 14:30) — **본 v2 발행으로 해제**

---

## 0. 한 줄

대표 직접 점검 결과 시안 14~20이 12B 마스터 변경(헤더·사이드바·도크 신규 규격) 미반영 상태로 발견 → 빅터(05)가 시안 7개 통일 작업 완료 → 이제 진짜로 "시안 = 정답" 상태 확보 → C안 v2 발행, 착수 부탁드립니다.

---

## 1. v1 → v2 변경 핵심

| 항목 | v1 (2026-04-25 14:00) | v2 (2026-04-25 17:00) |
|---|---|---|
| 시안 정합 | 14~20 미정합 (헤더 작음·도크 없음·사이드바 220px·워크스페이스 없음) | **14~20 모두 12B 마스터와 1:1 일치** |
| 시안 9종 grep | 통과 미검증 | ✅ 8종(12B+14~20) 결함 0건 검증 |
| 진짜 정답 | ❌ 시안 자체가 정답 아니었음 | ✅ "시안=정답" 성립 |
| 작업 보류 통보 | — | `_TO_01_C안_긴급보류_시안재정비.md` (현재 v2로 해제) |

### 빅터 자기검증 결과 (v2 발행 전 직접 grep)

```bash
# 정합 PASS (8종 시안 모두)
brand-logo-wrap     → 12B:20  14:20  15:22  16:22  17:22  18:22  19:22  20:22
ws-switcher         → ✅ 모든 시안에 존재
g-search            → ✅ 모든 시안에 존재
tb-icon-btn victor  → ✅ 모든 시안에 존재 (헤더 빅터 트리거)
class="dock"        → ✅ 모든 시안에 존재 (빅터 도크 영역)
--sidebar-w:264px   → ✅ 모든 시안에 동일
topbar-h clamp(84-108px) → ✅ 모든 시안에 동일

# 결함 0건 (전 시안 검증)
sb-resize    → 0건
.dock-tab    → 0건
width:220px  → 0건 (옛 사이드바)
brand-mark   → 0건 (옛 작은 로고)
topbar-h clamp(64-80px) → 0건 (옛 작은 헤더)
zh-CN        → 0건
中文         → 0건
🇨🇳/🇯🇵    → 0건
```

→ 12/12 PASS. 이제 시안 = 정답.

---

## 2. 작업 계약 (v1과 동일 골격, 시안 정답화 후)

### 2-1. 핵심 원칙

> **시안을 그대로 base.html / style.css / 각 페이지 템플릿에 통째 이식**.
> Jinja2 변수 치환 + 권한 분기 결합 + i18n 키 결합 외 다른 변경 금지.
> 시안에 없는 디테일·창의 결정 추가 금지 (이번엔 시안이 진짜로 완벽함).

### 2-2. 시안 9종 → 템플릿 9종 매핑

| 시안 | 적용 대상 |
|---|---|
| `03_시안/12B_healing_sage_garden.html` | **마스터** · `app/templates/base.html` (헤더+사이드바+도크) + `home.html` |
| `03_시안/13_login_healing.html` | `app/templates/login.html` |
| `03_시안/14_progress_healing.html` | `app/templates/progress_matrix.html` |
| `03_시안/15_dashboard_healing.html` | `app/templates/dashboard.html` |
| `03_시안/16_changes_healing.html` | `app/templates/changes.html` |
| `03_시안/17_tickets_healing.html` | `app/templates/tickets.html` |
| `03_시안/18_issues_healing.html` | `app/templates/issues.html` |
| `03_시안/19_daily_healing.html` | `app/templates/daily.html` |
| `03_시안/20_admin_healing.html` | `app/templates/admin.html` |

→ **14~20도 12B와 동일한 헤더·사이드바·도크를 가지므로 base.html 만 한 번 작성하면 모든 페이지에 자동 적용됨**.

### 2-3. base.html 작업 가이드

12B 시안의 다음 부분을 그대로 base.html에 옮긴다 (Jinja2 변수 치환):

#### A. 헤더 (`<header class="topbar">`)
- 워크스페이스 스위처: 옵션은 `WORKSPACES` context 변수에서 루프 (통합/매출·영업/자재·구매)
- 글로벌 검색바: `/` 키 단축키 작동 (Korean IME 안전 처리)
- 빅터 트리거: `Ctrl+K` / 헤더 아이콘 클릭 토글
- 언어 셀렉터: `i18n.LANGS` 에서 ko/vi/en 만 (zh-CN·ja 추가 금지)
- 사용자 칩: `current_user.name`, `current_user.role_label` 표시
- 로고: `static/logo.png` (clamp wrapper)

#### B. 사이드바 (`<aside class="sidebar">`)
- 264px 고정 (var(--sidebar-w))
- 5개 섹션: 내 업무 / 전사 흐름 / 업무 추적 / 외부·관리 / 팀·프로젝트 (트리)
- **도메인 그룹 (매출·영업/자재·구매) 사이드바에서 제거** (워크스페이스 스위처로 이동)
- 권한 매트릭스: `{% if user.is_executive %}` 등으로 메뉴 노출 분기

#### C. 빅터 도크 (`<aside class="dock" id="dock">`)
- `.layout` flex 컨테이너 내부 (position:fixed 금지)
- 페이지별 dock-sub / dock-ctx-chips / dock-quick 텍스트는 페이지에서 override 가능
- localStorage `haist_victor_dock_open` 키로 상태 유지

#### D. JS
- 시안의 `<script>` 블록 그대로 옮김
- 워크스페이스 토글 / `/` 검색 / 트리 / 도크 토글 / Ctrl+K / Esc

### 2-4. main.py 보강

```python
# 워크스페이스 컨텍스트
WORKSPACES = [
    {"id": "main",  "name": "통합",        "desc": "HAIST WORKS 메인", "active": True},
    {"id": "sales", "name": "매출·영업 센터", "desc": "Sales Hub",          "ext": True},
    {"id": "logi",  "name": "자재·구매 센터", "desc": "Logistics Hub",      "ext": True},
]

# 모든 라우트 컨텍스트에 추가
ctx["WORKSPACES"] = WORKSPACES
ctx["current_workspace"] = "main"
```

### 2-5. style.css 통합

기존 `style.css` 백업 → `style.css.bak.20260425` (1차 작업 시)
12B 시안 `<style>` 블록 + 페이지별 추가 컴포넌트 CSS (14~20 의 페이지별 부분만) 통합.

### 2-6. 라우트·폼·DB·API 변경 금지

- 라우트 URL: 그대로
- 폼 name 속성: 그대로
- DB 스키마: 그대로
- API 응답 형태: 그대로

---

## 3. 마감 일정

| 단계 | 시점 | 산출물 |
|---|---|---|
| **착수** | 2026-04-25 17:00 (현재) | git 브랜치 분리 + style.css 백업 |
| **1차 마감** | 2026-04-26 23:00 (+30시간) | base.html + style.css 통합 (12B 마스터) |
| **2차 마감** | 2026-04-27 23:00 (+54시간) | 페이지 9종 적용 (login/home/progress/dashboard/changes/tickets/issues/daily/admin) |
| **회신** | 1차/2차 마감 직전 | `_FROM_01_힐링_C안_시안이식응답_v2_1차.md` 및 `_v2_2차.md` |

---

## 4. 응답 시 자체 검증 의무 (12종 grep)

응답 회신에 다음 grep 결과를 **반드시 첨부**:

```bash
# 정합 (PASS = ≥1)
grep -c "brand-logo-wrap" app/templates/base.html
grep -c "ws-switcher" app/templates/base.html
grep -c "g-search" app/templates/base.html
grep -c "tb-icon-btn victor" app/templates/base.html
grep -c 'class="dock"' app/templates/base.html
grep -c "victorTrigger" app/templates/base.html

# 토큰 (PASS = 있음)
grep "topbar-h" static/style.css | grep "clamp(84"
grep "sidebar-w" static/style.css | grep "264px"

# 결함 (PASS = 0)
grep -c "sb-resize" app/templates/base.html static/style.css
grep -c "dock-tab" app/templates/base.html static/style.css
grep -c "zh-CN\|中文\|🇨🇳" app/templates/base.html
grep -c "applyFont\|--sb-font-size" app/templates/base.html static/style.css
```

12개 항목 PASS 후 회신.

---

## 5. 회신 양식

```markdown
# _FROM_01_힐링_C안_시안이식응답_v2_1차.md

## 착수
- 시작: 2026-04-XX HH:MM
- 1차 완료: 2026-04-XX HH:MM
- 소요: __h __m
- 변경 라인 수: ~~~줄

## 자체 검증 (§4 의 12종)
| 항목 | 결과 | 기대 | PASS |
|---|---|---|---|
| brand-logo-wrap | N | ≥1 | ✅ |
| ws-switcher | N | ≥1 | ✅ |
| ... |
| dock-tab | 0 | 0 | ✅ |

## 라우트 회귀 확인 (curl 200 OK)
- /login, /home, /progress, /dashboard, /changes, /tickets, /issues, /daily, /admin

## 발견 이슈 (있다면)
- ...

## 질문 (있다면)
- ...
```

---

## 6. 폐기된 이전 지시 (v1 보관, 실행 기준 아님)

```
🟡 _TO_01_힐링_C안_시안통째이식_최종.md (v1)         → 본 v2가 대체
🟡 _TO_01_C안_긴급보류_시안재정비.md                 → 본 v2 발행으로 해제
🟡 _TO_01_디자인제안_07/08/09/10/12 (5건)             → C안 v2에 흡수
🟡 _TO_01_힐링2차/3차 (2건)                          → C안 v2에 흡수
🟡 _TO_01_대표승인_힐링디자인전환_최종.md             → C안 v2 승인 = 대표 직접 발화
```

---

## 7. 1차 작업 인정 (v1 응답 받은 부분)

01 세션의 1차 응답(`_FROM_01_힐링디자인응답.md`)에서 잘 된 부분:
- 힐링 토큰 전면 교체 (sage·ink·grad-sage/header) 정확
- 매출 KPI 3중 방어 견고 (UI·context·route)
- 호환 별칭 유지로 회귀 안전 설계
- 시간대별 인사말 5단계 분기

→ 이 작업물은 v2 base.html 통합 시 **빅터 도크·워크스페이스·헤더 신규 부분만 추가**하면 됨.

---

## 8. 빅터 사과 + 약속

v1 발행 시 시안 자체 grep 검증을 빠뜨려 잘못된 정답을 내려보낼 뻔한 점 사과드립니다.

**약속 (재강조)**:
- ✅ 응답 받으면 즉시 빅터가 §4 12종 grep 직접 실행 → 결과 확인 후 04 회귀 의뢰
- ✅ "% 완료" 보고 거부 — PASS/FAIL 매트릭스로만 진행도 측정
- ✅ 다음 변경 사항 발생 시 시안부터 갱신 → 그 다음 작업 계약 발행

---

## 9. 종합

이번엔 진짜로 시안 = 정답입니다. 14~20 모두 12B 마스터와 동일한 헤더·사이드바·도크 보유. 통째 이식하면 9개 페이지 모두 동일한 레이아웃 자동 적용. 문제 없으시면 1차 30시간 내 회신 부탁드립니다.

---

**발행**: 2026-04-25 17:00 · 05 디자인팀 세션 빅터
**상태**: 🟢 **C안 v2 발행 · 01 착수 가능 · 시안 정합 12/12 PASS**
**회신 위치**: `05_HAIST_WORKS_디자인팀/_FROM_01_힐링_C안_시안이식응답_v2_1차.md`
