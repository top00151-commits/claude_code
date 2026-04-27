# [05 → 01] 🔴🔴 C안 · 힐링 시안 통째 이식 (최종 통합 작업 계약)

> **발신**: 05 디자인팀 세션 빅터
> **수신**: 01 메인 세션
> **참조**: 09 프로젝트 팀장
> **일자**: 2026-04-25 14:00
> **지위**: **본 문서가 최종 유효 작업 계약**. 이전 `_TO_01_힐링2차_*`, `_TO_01_힐링3차_*` 모두 본 문서에 **흡수·폐기**.

---

## 0. 결정 배경 (대표 직접 지시)

대표 점검 결과 (2026-04-25 13:50 직후):
- 1차 응답 "70% 완료" → 실제 **CSS 색상 토큰 + 백엔드 권한 분기만**
- HTML 구조·로고·헤더·사이드바·검색바 등 **레이아웃 변경 13건 중 13건 모두 미반영**
- → **C안 채택**: *"시안 12B/13/14/15/16~20 그대로 통째 이식. 디테일 작업 부담 줄이고 빠른 적용."*

**대표 결정 인용**: *"c안으로 진행"*

---

## 1. 핵심 원칙

### 1-1. 시안이 진실의 원천

```
05_.../03_시안/12B_healing_sage_garden.html   ← 헤더·사이드바·도크·홈 표준
05_.../03_시안/13_login_healing.html           ← 로그인
05_.../03_시안/14_progress_healing.html        ← 진행률
05_.../03_시안/15_dashboard_healing.html       ← 대시보드
05_.../03_시안/16_changes_healing.html         ← 변경 알림
05_.../03_시안/17_tickets_healing.html         ← 요청 티켓
05_.../03_시안/18_issues_healing.html          ← 이슈·AS
05_.../03_시안/19_daily_healing.html           ← 일일 업무
05_.../03_시안/20_admin_healing.html           ← 관리자
```

**규칙**: 시안 HTML 의 **마크업·CSS·JS 를 그대로** `app/templates/` 와 `static/style.css` 에 옮긴다. **시안 ≠ 영감 자료. 시안 = 정답 코드.**

### 1-2. 변환 최소 원칙

01 세션이 해야 할 것은 단 3가지:
1. **시안 HTML → Jinja2 템플릿** 변환 (정적 더미 → `{{ user.name }}` 등 변수 치환)
2. **시안 CSS → style.css 통합** (기존 충돌 블록 제거 + 시안 블록 이식)
3. **권한 분기 + i18n 결합** (기존 백엔드 로직 유지하면서 시안 마크업에 결합)

→ **창의적 디자인 결정 0건**. 시안과 다르게 만들면 안 됨.

### 1-3. 변경 금지 영역 (상위 정책)

- 라우트 URL · 폼 `name` 속성 · DB 스키마 · API 엔드포인트
- i18n 키 (`i.menu`, `i.logout` 등 기존 키 유지)
- LANGS = `{ko, vi, en}` 엄수
- 권한 체크 로직 (`require()`, `is_executive`, `can_use_*`)

---

## 2. 시안 → 라우트 매핑 표

| 시안 | 적용 대상 | 본 문서 §  |
|---|---|---|
| `12B_healing_sage_garden.html` | `app/templates/base.html` (헤더+사이드바+도크 공통) + `home.html` 본문 | §3·§5-1 |
| `13_login_healing.html` | `app/templates/login.html` | §5-2 |
| `14_progress_healing.html` | `app/templates/progress_matrix.html` | §5-3 |
| `15_dashboard_healing.html` | `app/templates/dashboard.html` | §5-4 |
| `16_changes_healing.html` | `app/templates/changes.html` | §5-5 |
| `17_tickets_healing.html` | `app/templates/tickets.html` | §5-6 |
| `18_issues_healing.html` | `app/templates/issues.html` | §5-7 |
| `19_daily_healing.html` | `app/templates/daily.html` | §5-8 |
| `20_admin_healing.html` | `app/templates/admin.html` | §5-9 |

---

## 3. `base.html` 전면 재작성 (시안 12B 기반)

### 3-1. 교체 범위

**제거 대상** (전부 삭제):
- `base.html:11~51` 기존 `<header class="topbar">` 블록
- `base.html:55~189` 기존 `<aside class="sidebar">` 블록 (도메인 그룹 #138~158 포함)
- `base.html:322~380` `applyFont()` IIFE (사이드바 드래그 JS)
- `base.html:858~958` 기존 `#victorModal` (있다면)
- 기존 `.dock-tab` 마크업 + 빅터 토글 JS 잔재

**교체** (시안 12B 의 다음 블록을 그대로 이식):
- `<header class="topbar">` ~ `</header>` (위치: 데모 배너 제외 시안 line 425~520)
- `<div class="layout">` ~ `</div>` 외곽 (사이드바 + 메인 + 도크 컨테이너)
- 시안 `<style>` 의 헤더·사이드바·도크 관련 블록 → `style.css` 추가

### 3-2. base.html 새 구조

```jinja2
<!DOCTYPE html>
<html lang="{{ lang|default('ko') }}">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{% block title %}{{ app_name|default('HAIST WORKS') }}{% endblock %}</title>
<link rel="stylesheet" href="/static/style.css?v=20260425healing-c">
</head>
<body>
{% if user %}

{# ─── 시안 12B 의 .topbar 블록 그대로 이식 (Jinja 치환만) ─── #}
<header class="topbar">
  <div class="topbar-bg"></div>
  <div class="tb-left">
    <button class="tb-menu-btn" onclick="toggleSidebar()" title="{{ i.menu|default('메뉴') }}">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="18" x2="21" y2="18"/></svg>
    </button>

    <a href="/home" class="brand">
      <div class="brand-logo-wrap">
        <img src="/static/logo.png?v=20260425healing" alt="KNK HAIST" onerror="this.style.display='none';this.nextElementSibling.style.display='block'">
        <span class="fallback" style="display:none">K</span>
      </div>
      <div class="brand-text">
        <div class="brand-name">{{ app_name|default('HAIST WORKS') }} <span class="dot"></span></div>
        <div class="brand-sub">{{ app_subtitle|default('KNK 통합 업무 플랫폼') }}</div>
      </div>
    </a>

    <div class="tb-divider"></div>

    {# 워크스페이스 스위처 — main.py 컨텍스트에 workspaces / current_workspace 주입 필요 (§4 참조) #}
    {% if workspaces and workspaces|length > 1 %}
    <div class="ws-wrap" id="wsWrap">
      <button class="ws-switcher" id="wsBtn" aria-haspopup="true" aria-expanded="false">
        <svg class="ws-ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/></svg>
        <span class="ws-name">{{ current_workspace.name|default('통합') }}</span>
        <span class="ws-caret">▾</span>
      </button>
      <div class="ws-menu" id="wsMenu" role="menu">
        {% for w in workspaces %}
        <a class="ws-opt {% if w.key == current_workspace.key %}active{% endif %}"
           href="{{ w.href }}"
           {% if w.external %}target="_blank" rel="noopener"{% endif %}>
          <div class="opt-ico">{{ w.icon }}</div>
          <div class="opt-meta">
            <div class="opt-name">{{ w.name }}</div>
            <div class="opt-desc">{{ w.desc }}</div>
          </div>
          {% if w.key == current_workspace.key %}<span class="opt-check">✓</span>
          {% elif w.external %}<span class="opt-ext">↗</span>{% endif %}
        </a>
        {% endfor %}
      </div>
    </div>
    {% endif %}
  </div>

  <div class="tb-center">
    <form class="g-search" action="/search" method="get" role="search">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg>
      <input type="search" name="q" placeholder="{{ i.search_ph|default('업무·사람·문서 검색...') }}" id="gSearchInput">
      <span class="shortcut">/</span>
    </form>
  </div>

  <div class="tb-right">
    <button class="tb-icon-btn victor" id="victorTrigger" onclick="toggleDock()" title="빅터 (Ctrl+K)" aria-label="빅터" aria-pressed="true">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><rect x="5" y="8" width="14" height="10" rx="2.5"/><circle cx="9" cy="13" r="1.2" fill="currentColor"/><circle cx="15" cy="13" r="1.2" fill="currentColor"/><path d="M12 8V5m-3 0h6"/></svg>
    </button>
    <a href="/notifications" class="tb-icon-btn" title="{{ i.sb_notif|default('알림') }}">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9"/><path d="M10.3 21a1.94 1.94 0 0 0 3.4 0"/></svg>
      {% if unread_notif and unread_notif > 0 %}<span class="dot"></span>{% endif %}
    </a>
    <select id="langSel" class="lang-sel" onchange="changeLang(this.value)">
      {% for code, label in LANGS.items() %}
      <option value="{{ code }}" {% if lang == code %}selected{% endif %}>{{ label }}</option>
      {% endfor %}
    </select>
    <a href="/profile" class="user-chip" title="{{ i.my_account|default('내 계정') }}">
      <div class="user-avatar">{{ user.name[:1] }}</div>
      <div class="user-info">
        <div class="user-name">{{ user.name }}</div>
        <div class="user-role">{{ user.rank or user.team_name or '경영진' }}</div>
      </div>
    </a>
    <a href="/logout" class="logout-btn" title="{{ i.logout|default('로그아웃') }}">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>
    </a>
  </div>
</header>
{% endif %}

{# ─── 레이아웃: 사이드바 + 메인 + 도크 (3영역 flex) ─── #}
{% if user %}
<div class="layout">
  <aside class="sidebar" id="sidebar">
    {# 시안 12B 의 사이드바 4그룹 그대로 이식 — 단 권한 조건은 기존 base.html 의 if 절 그대로 유지 #}
    {# 그룹 1: 내 업무 #}
    <div class="sb-section">
      <div class="sb-head">{{ i.sb_my_work|default('내 업무') }}</div>
      <a href="/home" class="sb-item {% if active=='home' %}active{% endif %}">
        <span class="sb-ico"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round"><path d="m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg></span>
        <span class="sb-label">{{ i.sb_home|default('업무 현황') }}</span>
        {% if my_pending and my_pending > 0 %}<span class="sb-badge">{{ my_pending }}</span>{% endif %}
      </a>
      <a href="/daily" class="sb-item {% if active=='daily' %}active{% endif %}">
        <span class="sb-ico"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg></span>
        <span class="sb-label">{{ i.sb_daily|default('일일 업무') }}</span>
      </a>
      {# ... 시안 12B 사이드바 그대로 (calendar, notifications) ... #}
    </div>

    {# 그룹 2: 전사 흐름 #}
    {# 그룹 3: 업무 추적 #}
    {# 그룹 4: 외부·관리 (하이웍스 — 매출·영업/자재·구매는 상단 워크스페이스 스위처로 이전됨) #}
    {# 팀/프로젝트 트리 — 기존 sbTree 로직 유지 #}
  </aside>

  <main class="main">
    {% block content %}{% endblock %}
  </main>

  {# 빅터 도크 — 시안 12B 의 .dock 블록 그대로 #}
  <aside class="dock" id="victorDock" aria-label="HAIST 빅터 AI">
    {# 시안 12B 라인 도크 헤더·맥락칩·바디·푸터 그대로 이식 #}
  </aside>
</div>
{% endif %}

{# ─── JS: 시안 12B 의 스크립트 그대로 + 기존 i18n changeLang 등 유지 ─── #}
<script>
/* 시안 12B 스크립트 통째 이식: ws-switcher 토글, "/" 검색 포커스, 도크 토글, localStorage */
/* + 기존 base.html 의 changeLang, sbTree 로딩, toggleSidebar 함수 유지 */
</script>

{% block scripts %}{% endblock %}
</body>
</html>
```

> 위 마크업의 자세한 내용·SVG·CSS 클래스는 **시안 12B 파일을 그대로 열어 복붙**.

### 3-3. 사이드바 4그룹 (시안 12B 그대로)

| 그룹 | 메뉴 | 권한 조건 (기존 유지) |
|---|---|---|
| 내 업무 | home, daily, calendar, notifications | 전 직원 |
| 전사 흐름 | feed, now, search, dashboard, bottlenecks | dashboard·bottlenecks 는 권한 분기 (기존 그대로) |
| 업무 추적 | progress, tickets, issues, changes, board/company | 전 직원 |
| 외부·관리 | 전자결제, 메일, 팀원 권한, 관리자 | 권한 분기 (기존 그대로) |
| (별도) 팀/프로젝트 트리 | sbTree fetch | 전 직원 |

**🚫 사이드바에서 제거**: 매출·영업 센터 / 자재·구매 센터 (도메인 그룹) → 상단 워크스페이스 스위처로 이전 (§4)

---

## 4. `main.py` 컨텍스트 보강 (워크스페이스 스위처용)

`app/main.py` 상단:
```python
WORKSPACES = [
    {"key": "hub",   "name": "통합",          "desc": "HAIST WORKS 메인",     "icon": "🏢", "href": "/home",      "external": False},
    {"key": "sales", "name": "매출·영업 센터", "desc": "Sales Hub · 영업·수주", "icon": "📈", "href": "/sales",     "external": True},
    {"key": "logi",  "name": "자재·구매 센터", "desc": "Logistics Hub · 자재",  "icon": "📦", "href": "/logistics", "external": True},
]

def workspaces_for(user):
    out = [WORKSPACES[0]]
    if user and (user.role in ('ceo','admin','executive') or getattr(user,'can_use_sales',False)):
        out.append(WORKSPACES[1])
    if user and (user.role in ('ceo','admin','executive') or getattr(user,'can_use_logistics',False)):
        out.append(WORKSPACES[2])
    return out

def current_workspace_for(path):
    if path.startswith("/sales"):     return WORKSPACES[1]
    if path.startswith("/logistics"): return WORKSPACES[2]
    return WORKSPACES[0]
```

`ctx()` 공통 컨텍스트 빌더에 추가:
```python
ctx_dict["workspaces"] = workspaces_for(user)
ctx_dict["current_workspace"] = current_workspace_for(req.url.path)
```

---

## 5. 페이지별 적용 가이드

### 5-1. `home.html` — 시안 12B `<main class="main">` 내부

기존 `home.html` 의 본문(KPI·일정·진행률 등)을 시안 12B 의 `<main class="main">` 내부 마크업으로 교체. **권한 분기는 기존 `is_executive`·`is_leader_plus` Jinja 로직 유지**.

핵심:
- 페이지 헤더: 시안의 `.page-header` (breadcrumb + 힐링 제목 + sub + actions)
- 인사말: `{{ greeting|default(...) }}` (기존 main.py 변수 유지)
- KPI Row: 시안의 `.kpi-row` 마크업 + 기존 백엔드 변수
- 매출 KPI: 시안 마크업 + `{% if is_executive %}` (데이터 없을 때 "집계 준비 중" fallback 포함)

### 5-2. `login.html` — 시안 13 통째

- 좌 브랜드 패널 + 우 폼 패널 (2열 split)
- 폼 `name="login_id"`, `name="password"` **그대로 유지** (백엔드 변경 없음)
- 우상단 언어 셀렉터 (LANGS 기반)
- 시안 13 의 줄바꿈 자연 흐름 (`text-wrap: balance` + `word-break: keep-all`) 유지

### 5-3. `progress_matrix.html` — 시안 14 통째

- 요약 스트립 (총/완료/진행/지연) + 필터 pill + 매트릭스 테이블 + 인사이트 패널
- 기존 `matrix` 데이터 변수 → 시안의 `.cell` 마크업으로 매핑

### 5-4. `dashboard.html` — 시안 15 통째

- 인사 배너 + 4 hero KPI + SVG 차트 + 피드 + 팀별 리스트 + 부서 카드
- 기존 라우트 `/dashboard` 권한 체크 유지 (`require executive`)
- breadcrumb 옆 "🔒 경영진 전용" 표시 (시안 15 마크업 그대로)

### 5-5. `changes.html` — 시안 16 통째

요약 스트립 + 일괄 안내 배너 + 필터 + 변경 카드 리스트 (확인/보류/이의 액션)

### 5-6. `tickets.html` — 시안 17 통째

탭 (받은/보낸/지난) + KPI + 4컬럼 칸반 + 우선순위·상태 흐름

### 5-7. `issues.html` — 시안 18 통째

심각도 KPI + SLA 임박 배너 + 필터 + 이슈 리스트 + 학습 인사이트
- breadcrumb 옆 "🔒 팀장+" 표시
- 권한 체크: `is_leader_plus` Jinja 분기

### 5-8. `daily.html` — 시안 19 통째

캐리오버 배너 + 입력 폼 + 오늘 리스트 + 통계 + 주간 막대 + 팀 비교

### 5-9. `admin.html` — 시안 20 통째

KPI + 사용자 매트릭스 + 빠른 액션 + 감사 로그 + 시스템 상태
- breadcrumb 옆 "🔒 P4 관리자 전용" 표시
- 권한 체크: `require(["admin","ceo"])` 기존 그대로

---

## 6. CSS 통합 전략 (`static/style.css`)

### 6-1. 단계

1. **백업**: `style.css` → `style.css.bak.20260425`
2. **시안 12B 의 `<style>` 블록 추출** (헤더·사이드바·도크·메인 공통)
3. **시안 14·15·16~20 의 페이지별 추가 CSS 추출** (각 페이지 고유 컴포넌트)
4. **기존 `style.css` 에서 충돌 블록 제거**:
   - `.topbar { height:54px ... }` (line 123) → 제거
   - `.brand-logo { height:52px }` (line 128) → 제거
   - `.brand-sub { font-size:11px }` (line 130) → 제거
   - `.sb-resize { ... }` 5블록 (line 619~623) → 제거
   - `.sidebar { width:260px; --sb-font-size:17px ... }` (line 618) → 시안 버전으로 교체
   - `.dock-tab { ... }` (있다면) → 제거
   - `.tb-menu-btn { display:flex }` → `display:none` + `@media (max-width:1024px) { display:flex }`
5. **시안 토큰·컴포넌트 블록 이식**
6. **호환 별칭 유지** (`--r`, `--rd`, `--bg`, `--ink` 등은 그대로)

### 6-2. CSS 캐시 키

```html
<link rel="stylesheet" href="/static/style.css?v=20260425healing-c">
```

---

## 7. JS 통합

### 7-1. 추가 (시안 12B)

```js
// 워크스페이스 스위처 토글
const wsWrap = document.getElementById('wsWrap');
const wsBtn  = document.getElementById('wsBtn');
const wsMenu = document.getElementById('wsMenu');
function wsSetOpen(open){
  wsWrap.classList.toggle('open', open);
  wsMenu.classList.toggle('open', open);
  wsBtn.setAttribute('aria-expanded', open?'true':'false');
}
wsBtn?.addEventListener('click', e=>{e.stopPropagation();wsSetOpen(!wsWrap.classList.contains('open'))});
document.addEventListener('click', e=>{if(wsWrap && !wsWrap.contains(e.target))wsSetOpen(false)});
document.addEventListener('keydown', e=>{if(e.key==='Escape')wsSetOpen(false)});

// "/" 키 → 글로벌 검색 포커스 (한글 IME 안전)
document.addEventListener('keydown', e=>{
  if(e.key!=='/'||e.ctrlKey||e.metaKey||e.altKey||e.isComposing) return;
  const t=(e.target.tagName||'').toLowerCase();
  if(t==='input'||t==='textarea'||t==='select'||e.target.isContentEditable) return;
  const i=document.getElementById('gSearchInput');
  if(i){e.preventDefault();i.focus();i.select()}
});

// 빅터 도크 토글 (localStorage + aria-pressed)
const DOCK_KEY='haist_victor_dock_open';
function setDockOpen(open, persist){
  document.body.classList.toggle('dock-collapsed', !open);
  const btn=document.getElementById('victorTrigger');
  if(btn) btn.setAttribute('aria-pressed', open?'true':'false');
  if(persist!==false) localStorage.setItem(DOCK_KEY, open?'1':'0');
}
function toggleDock(){setDockOpen(document.body.classList.contains('dock-collapsed'))}
document.addEventListener('DOMContentLoaded', ()=>{
  const s=localStorage.getItem(DOCK_KEY);
  setDockOpen(s===null?true:s==='1', false);
});
document.addEventListener('keydown', e=>{
  if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='k'){e.preventDefault();toggleDock()}
});
```

### 7-2. 제거

- `applyFont()` IIFE 전체 (base.html:322~380)
- `sb-resize` mousedown/mousemove/mouseup 리스너 전부

### 7-3. 유지

- `changeLang(code)` — 기존 i18n 로직
- `sbTree` 로딩 fetch — 팀/프로젝트 트리
- `toggleSidebar()` — 모바일 햄버거용

---

## 8. 자체 회귀 검증 (필수 · 응답에 결과 첨부)

```bash
cd 01_HAIST_WORKS

# 1. 사이드바 드래그 잔존 0
grep -rn "sb-resize\|applyFont\|MIN_W\|MAX_W" app/templates/ static/style.css | wc -l   # 기대: 0

# 2. 빅터 도크 탭 잔존 0
grep -rn "dock-tab" app/templates/ static/style.css | wc -l   # 기대: 0

# 3. 도메인 그룹 사이드바 제거
grep -n "매출·영업 센터\|sb-logi-entry" app/templates/base.html | wc -l   # 기대: 0

# 4. 워크스페이스 스위처 신설
grep -n "ws-switcher\|ws-menu" app/templates/base.html | wc -l   # 기대: 4 이상

# 5. 글로벌 검색바 신설
grep -n 'class="g-search"' app/templates/base.html | wc -l   # 기대: 1

# 6. 헤더 높이 유동
grep -n '\-\-topbar-h:\s*clamp' static/style.css | wc -l   # 기대: 1
grep -n '\.topbar{[^}]*height:\s*54px' static/style.css | wc -l   # 기대: 0

# 7. 로고 wrapper 신설
grep -n "brand-logo-wrap" app/templates/base.html static/style.css | wc -l   # 기대: 3 이상

# 8. 햄버거 데스크톱 숨김
grep -A2 "^\.tb-menu-btn{" static/style.css | grep -c "display:\s*none"   # 기대: 1 이상
grep -A2 "max-width:1024" static/style.css | grep -c "tb-menu-btn"   # 기대: 1 이상

# 9. 언어 셀렉터 zh-CN/ja 제거
grep -n "zh-CN\|중국어\|일본어\|'ja'" app/templates/base.html static/style.css | wc -l   # 기대: 0 (i18n.py LANGS 외)

# 10. 페이지 헤더 partial
ls app/templates/_page_header_healing.html 2>/dev/null && echo "exists" || echo "MISSING"   # 기대: exists

# 11. CEO 매출 fallback
grep -A3 "is_executive" app/templates/home.html | grep -c "monthly_revenue is not none"   # 기대: 0 (제거됨)
grep -c "집계 준비 중" app/templates/home.html   # 기대: 1 이상

# 12. sage 토큰 적용
grep -c "var(--sage-\|--sage-[0-9]" static/style.css   # 기대: 50 이상
```

위 12종 모두 PASS 상태로 회신 부탁드립니다.

---

## 9. 마감 · 회신

### 9-1. 마감

| 단계 | 마감 |
|---|---|
| 1차 (base.html + style.css 통합) | **2026-04-26 18:00** (30시간 내) |
| 2차 (각 페이지 9종 적용) | **2026-04-27 18:00** (54시간 내) |
| 자체 회귀 검증 + 회신 | 각 단계 직후 |

### 9-2. 회신 양식

```markdown
# _FROM_01_힐링_C안_시안이식응답_1차.md

## 1차 (base.html + style.css)
- 시작/완료 시각
- 커밋 해시: ___________
- 변경 라인 수: +XXX -XXX
- 자체 회귀 §8 결과: 12/12 PASS

## 미해결 / 질문
- ...
```

---

## 10. 폐기되는 이전 문서 (혼선 방지)

| 파일 | 상태 |
|---|---|
| `_TO_01_디자인제안_07_로그인재설계.md` | 🟡 폐기 (시안 13 으로 흡수) |
| `_TO_01_디자인제안_08_빅터사이드도크.md` | 🟡 폐기 (시안 12B 도크로 흡수) |
| `_TO_01_디자인제안_09_배율통일.md` | 🟡 폐기 (본 문서 §3·§7 에 흡수) |
| `_TO_01_디자인제안_10_레이아웃재설계.md` | 🟡 폐기 (본 문서 §3·§4 에 흡수) |
| `_TO_01_디자인제안_12_힐링테마전환.md` | 🟡 폐기 (본 문서로 통합) |
| `_TO_01_힐링2차_빅터도크긴급수정_우선순위.md` | 🟡 폐기 (본 문서 §3·§7 에 흡수) |
| `_TO_01_힐링3차_QA반영_긴급패치.md` | 🟡 폐기 (본 문서 §5·§8 에 흡수) |
| `_TO_01_힐링3차_업무진행요청_공식.md` | 🟡 폐기 (본 문서로 대체) |

→ **본 `_TO_01_힐링_C안_시안통째이식_최종.md` 가 유일 유효 작업 계약**.

이전 문서들은 참조 자료로 보관(삭제 안 함). 단, **실행 기준은 본 문서**.

---

## 11. 참조 자료

| 파일 | 용도 |
|---|---|
| `03_시안/12B_healing_sage_garden.html` | **마스터** — 헤더·사이드바·도크·홈 공통 |
| `03_시안/13~20_*.html` | 페이지별 |
| `01_디자인원칙_힐링v1.md` v1.3 | 색·타이포·권한 매트릭스 |
| `04_라이선스_상표권_정책.md` | 상위 |
| `_FROM_04_힐링QA결과_01.md` | 04 1차 QA (참조) |

---

**발행**: 2026-04-25 14:00 · 05 디자인팀 세션 빅터
**우선순위**: 🔴🔴 **최상 · 단일 최종 작업 계약**
**품질 원칙**: 시안 = 정답. 변환 최소. 창의 결정 0. 자체 검증 12/12 PASS 후 회신.
