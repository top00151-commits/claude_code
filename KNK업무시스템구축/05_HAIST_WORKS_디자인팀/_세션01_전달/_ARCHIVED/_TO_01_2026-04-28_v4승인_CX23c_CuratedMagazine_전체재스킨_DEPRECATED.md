# [05 → 01] 🟢 v4 디자인 정식 발주 — CX23c Curated Magazine 전체 재스킨

> **발신**: 05 디자인팀 세션 빅터
> **수신**: 01 메인 세션 (실무팀)
> **참조**: 09 프로젝트 팀장 / 04 운영테스트팀 / 대표이사
> **일자**: 2026-04-28
> **트리거**: 대표 직접 선택 — *"CX23c_CuratedMagazine_매거진70 이걸로 진행할께"*
> **선행 시안**: `03_시안/_03_v4_탐색_6옵션/CX23c_CuratedMagazine_매거진70.html` (대표 승인본)
> **선행 라운드**: 라운드 1 (6) → 라운드 2 (6 변형) → 라운드 3 (CX1·CX2·CX3) → **라운드 4 CX23a/b/c → CX23c 최종 선택**
> **지위**: 🟢 **정식 발주 · v4 전체 재스킨 · 긴급 우선순위**

---

## 0. 한 줄

대표 4라운드 검토 끝에 **CX23c (매거진 70 + 갤러리 30)** 최종 승인. 기존 sage green healing 톤 → **monochrome 인쇄지 + KNK 레드 단일 액센트 + 시리프 헤드라인** 으로 전체 재스킨. 3개 base + style.css + 9개 페이지 + 로그인 + 빅터 도크 모두 변환.

---

## 1. 디자인 철학 (CX23c Curated Magazine)

### 1-1. 컨셉
**우아한 신문 데스크** — Monocle / Wallpaper / GQ / The Gentleman's Journal 매거진 톤
- 권위감 + 정보 정확성 (강한 마스트헤드 · VOL/NO · 카테고리 라벨)
- 우아한 본문 (시리프 weight 300 가벼움 + bold 700 강조)
- 절제된 컬러 (모노크롬 + KNK 레드 한 점)
- 인쇄지 질감 (#FAFAF7 paper white)

### 1-2. 핵심 비율 — 매거진 70 + 갤러리 30
- **CX2 매거진 강함 (70%)**: 3px 상단 검정 + VOL/NO 마스트헤드 + COVER 빨간 라벨 + 신문 카테고리
- **CX3 갤러리 절제 (30%)**: 시리프 본문 weight 300 가벼움 + 카드 1px 라인

### 1-3. 정체성 유지
- 힐링 컨셉의 차분함 → 시리프 활자의 우아함으로 변환
- 녹색 정원 → 모노크롬 인쇄지로 전환
- KNK 빨강은 액센트 1점 (절제된 강조)

---

## 2. 변경 범위 — 5단계 Phase

| Phase | 시점 | 산출물 | 파일 |
|---|---|---|---|
| **Phase 1: 토큰 + 헤더** | +6h | style.css 토큰 + 3 base 헤더 | base.html / base_sales.html / base_logi.html / static/style.css |
| **Phase 2: 페이지 본체** | +14h | 카드/폼/테이블/매트릭스 매거진톤 | home/progress/dashboard/changes/tickets/issues/daily/admin |
| **Phase 3: 로그인 + 빅터 도크** | +20h | 로그인 매거진 spread + 도크 모드탭 톤 | login.html + base.html dock 영역 |
| **Phase 4: 04 회귀 검증** | +24h | 페르소나 walkthrough + grep | 검증 결과 |
| **Phase 5: BAT 갱신** | 직후 | KNK_시작.bat / START.bat | LAST UPDATE |

---

## 3. 신규 컬러/폰트 토큰 (style.css 에 추가)

```css
:root {
  /* === CX23c Curated Magazine v4 (대표 승인 2026-04-28) ===
     기존 --sage-* 변수는 deprecated 표시 후 보존, 신규 변수 우선 적용 */

  /* Paper & Ink (모노크롬 베이스) */
  --paper:        #FAFAF7;     /* 인쇄지 베이지화이트 — body bg */
  --paper-2:      #F0EDE3;     /* 페이지 fill */
  --paper-3:      #E5E2D8;     /* 카드 sub */
  --ink:          #0A0A0A;     /* 본문 검정 (#000 아님 — 약간 따뜻) */
  --ink-2:        #2A2A26;     /* 보조 검정 */
  --ink-3:        rgba(10, 10, 10, .70);
  --ink-4:        rgba(10, 10, 10, .55);
  --ink-5:        rgba(10, 10, 10, .40);

  /* Structure lines */
  --line-strong:  #0A0A0A;
  --line-soft:    #D8D4CC;
  --line-dashed:  rgba(10, 10, 10, .20);

  /* KNK Red (단일 액센트) */
  --accent:       #A5282C;
  --accent-dk:    #8B1E22;
  --accent-soft:  #F5E4E2;
  --accent-glow:  0 0 12px rgba(165, 40, 44, .55);

  /* Typography */
  --font-serif:   'Times New Roman', Georgia, 'Pretendard Variable', Pretendard, serif;
  --font-sans:    -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Pretendard Variable', Pretendard, system-ui, sans-serif;
  --font-mono:    ui-monospace, Menlo, Consolas, monospace;

  /* Topbar */
  --topbar-h:        96px;
  --topbar-h-row1:   36px;     /* 마스트헤드 */
  --topbar-h-row2:   60px;     /* 메인 */

  /* 기존 --sage-* 변수는 호환성 위해 유지 (deprecated)
     C안 v2 통째 이식 사양은 --sage-* 사용 중이므로 즉시 제거 시 회귀 위험 */
}

/* 기본 body 재정의 */
body {
  font-family: var(--font-serif);
  font-weight: 400;
  font-size: var(--fs-md);
  background: var(--paper);
  color: var(--ink);
  line-height: 1.6;
}

/* UI 요소는 sans (라벨·버튼·폼) */
button, input, select, textarea,
.sb-item, .ws-tab, .lang-sel, .tb-icon-btn,
.btn, .label, .badge, .breadcrumb {
  font-family: var(--font-sans);
}

/* 헤드라인 시리프 */
h1, h2, h3, .page-title, .sample-h2, .brand-name {
  font-family: var(--font-serif);
}
```

---

## 4. CSS 정식 — 헤더 (style.css 에 추가)

```css
/* ============================================================
   CX23c TOPBAR — 매거진 마스트헤드 (대표 승인 2026-04-28)
   2-row 구조: row1 = 마스트헤드 (날짜 + VOL/NO)
                row2 = 로고 + ws-tabs + 우측 아이콘
   ============================================================ */

.topbar {
  background: var(--paper);
  color: var(--ink);
  padding: 12px 36px 0;
  border-top: 3px solid var(--ink);     /* 마스트헤드 강조 */
  border-bottom: 1px solid var(--ink);
  position: sticky;
  top: 0;
  z-index: 150;
  height: auto;                          /* 2-row 자동 높이 */
}

/* Row 1 — 마스트헤드 (날짜 + 에디션) */
.tb-masthead {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--line-soft);
}
.tb-date {
  font-family: var(--font-sans);
  font-size: 11px;
  color: var(--ink);
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: .15em;
}
.tb-edition {
  font-family: var(--font-sans);
  font-size: 11px;
  color: var(--accent);
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: .20em;
}

/* Row 2 — 메인 헤더 (로고 + 탭 + 우측) */
.tb-main {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 0;
  gap: 28px;
}

.tb-left {display: flex; align-items: center; gap: 28px; flex-shrink: 0}
.tb-center {flex: 1}
.tb-right {display: flex; align-items: center; gap: 8px; flex-shrink: 0}

/* Logo */
.brand {display: flex; align-items: center; gap: 14px}
.brand-logo-wrap {
  height: 48px;
  min-width: 48px;
  padding: 0;
  background: transparent;
  border-radius: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: none;
}
.brand-logo-wrap img {
  height: 42px;
  max-width: 200px;
  object-fit: contain;
  filter: none;                          /* CX23c는 원본 색상 그대로 */
}
.tb-divider {width: 1px; height: 36px; background: var(--ink)}

/* 기존 brand-text 는 숨김 (마스트헤드와 활성 탭에 정보 있어 중복) */
.topbar .brand-text {display: none !important}

/* ============================================================
   WS-TABS — 매거진 카테고리 + COVER 빨간 라벨 (CX23c 핵심)
   ============================================================ */

.ws-tabs {
  display: flex;
  gap: 0;
  align-items: stretch;
  flex-wrap: nowrap;
}
.ws-tab {
  display: inline-flex;
  align-items: center;
  gap: 9px;
  padding: 11px 20px;
  background: transparent;
  color: var(--ink);
  font-family: var(--font-sans);
  font-size: 12px;
  font-weight: 600;
  letter-spacing: .10em;
  text-transform: uppercase;
  border: 0;
  border-right: 1px solid var(--ink);
  transition: all var(--dur-fast) var(--ease);
  white-space: nowrap;
  position: relative;
}
.ws-tab:first-child {border-left: 1px solid var(--ink)}
.ws-tab:hover {background: var(--paper-2); color: var(--ink)}
.ws-tab .ws-ico {
  width: 14px;
  height: 14px;
  flex-shrink: 0;
  color: inherit;
  opacity: .85;
}
.ws-tab .ws-ico svg {width: 100%; height: 100%; stroke-width: 2}

/* 활성 탭 — 검정 + COVER 빨간 라벨 + 빨간 점 */
.ws-tab.active {
  background: var(--ink);
  color: var(--paper);
  font-weight: 900;
}
.ws-tab.active::after {
  content: "COVER";
  position: absolute;
  top: -9px;
  left: 50%;
  transform: translateX(-50%);
  background: var(--accent);
  color: #fff;
  padding: 2px 10px;
  font-family: var(--font-sans);
  font-size: 9px;
  font-weight: 900;
  letter-spacing: .20em;
  white-space: nowrap;
}
.ws-tab.active::before {
  content: "";
  display: inline-block;
  width: 5px;
  height: 5px;
  background: var(--accent);
  border-radius: 50%;
  margin-right: 0;
  animation: cx23cPulse 2s ease-in-out infinite;
}
.ws-tab.active .ws-ico {color: var(--accent)}

@keyframes cx23cPulse {
  0%, 100% {opacity: 1; transform: scale(1)}
  50%      {opacity: .4; transform: scale(1.3)}
}

/* 모바일 — 1100px 이하 */
@media (max-width: 1100px) {
  .ws-tab .ws-name {display: none}
  .ws-tab.active .ws-name {display: inline; font-size: 11px}
  .ws-tab {padding: 9px 12px}
  .ws-tab.active {padding: 9px 14px}
}

/* ============================================================
   우측 영역 — 매거진 톤 아이콘 버튼
   ============================================================ */

.tb-icon-btn {
  position: relative;
  width: 38px;
  height: 38px;
  background: transparent;
  color: var(--ink);
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--ink);
  border-radius: 0;                      /* 매거진 사각형 */
  font-family: var(--font-sans);
  transition: all var(--dur-fast) var(--ease);
  box-shadow: none;
}
.tb-icon-btn:hover {background: var(--ink); color: var(--paper)}
.tb-icon-btn svg {width: 17px; height: 17px; stroke-width: 2}

/* 빅터 트리거 — KNK 레드 솔리드 */
.tb-icon-btn.victor {
  background: var(--accent);
  color: #FFFFFF;
  border-color: var(--accent);
  font-weight: 900;
  box-shadow: none;
}
.tb-icon-btn.victor:hover {
  background: var(--ink);
  border-color: var(--ink);
  color: var(--accent);
}

/* 알림 dot */
.tb-icon-btn .dot {
  position: absolute;
  top: 4px;
  right: 4px;
  width: 6px;
  height: 6px;
  background: var(--accent);
  border-radius: 50%;
  border: 1px solid var(--paper);
  box-shadow: var(--accent-glow);
}

/* 언어 셀렉터 */
.lang-sel {
  background: transparent;
  color: var(--ink);
  border: 1px solid var(--ink);
  border-radius: 0;
  padding: 8px 11px;
  font-family: var(--font-sans);
  font-size: 11px;
  font-weight: 700;
  cursor: pointer;
  outline: none;
  text-transform: uppercase;
  letter-spacing: .10em;
}

/* 사용자 칩 */
.user-chip {
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 3px 13px 3px 3px;
  background: transparent;
  border: 1px solid var(--ink);
  border-radius: 0;
  font-family: var(--font-sans);
  transition: all var(--dur-fast) var(--ease);
}
.user-chip:hover {background: var(--ink); color: var(--paper)}
.user-chip:hover .user-avatar {background: var(--accent)}
.user-avatar {
  width: 30px;
  height: 30px;
  background: var(--ink);
  color: var(--paper);
  font-family: var(--font-serif);
  font-style: italic;
  font-weight: 600;
  font-size: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  transition: all var(--dur-fast) var(--ease);
}
.user-info {display: flex; flex-direction: column; line-height: 1.2}
.user-name {font-size: 12px; font-weight: 700; letter-spacing: .04em}
.user-role {
  font-size: 9px;
  font-weight: 700;
  color: var(--accent);
  text-transform: uppercase;
  letter-spacing: .15em;
}

/* 로그아웃 */
.logout-btn {
  width: 34px;
  height: 34px;
  background: transparent;
  color: var(--ink);
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--ink);
  border-radius: 0;
  transition: all var(--dur-fast) var(--ease);
}
.logout-btn:hover {background: var(--accent); color: #fff; border-color: var(--accent)}
.logout-btn svg {width: 14px; height: 14px; stroke-width: 2}

/* 옛 sage green 헤더 그라디언트 비활성 — 호환성 위해 보존 */
/* .topbar 의 sage 그라디언트를 위 .topbar 정의가 오버라이드 */
```

---

## 5. CSS — 페이지 본체

```css
/* ============================================================
   CX23c PAGE BODY — 매거진 인쇄 + 갤러리 절제
   ============================================================ */

/* 페이지 헤드 */
.page-header,
.page-head {
  background: var(--paper);
  border-bottom: 1px solid var(--line-soft);
  padding: 36px 40px 26px;
}
.page-title h1,
h1.page-title,
.sample-h2 {
  font-family: var(--font-serif);
  font-size: var(--fs-2xl);
  font-weight: 300;            /* 가벼운 시리프 */
  color: var(--ink);
  letter-spacing: -1px;
  line-height: 1.15;
}
.page-title h1 b,
.sample-h2 b,
.headline-strong {font-weight: 700}

.page-overline {
  font-family: var(--font-sans);
  font-size: 10px;
  font-weight: 900;
  color: var(--accent);
  letter-spacing: .30em;
  text-transform: uppercase;
  margin-bottom: 12px;
}
.page-byline {
  font-family: var(--font-serif);
  font-style: italic;
  font-size: 11px;
  color: var(--ink-3);
  margin-top: 14px;
}
.page-byline b {
  font-style: normal;
  font-family: var(--font-sans);
  font-weight: 900;
  font-size: 10px;
  letter-spacing: .05em;
  text-transform: uppercase;
  color: var(--ink);
}

/* KPI 카드 (매거진 카테고리 라벨 톤) */
.kpi-card,
.sum-card,
.sample-card {
  background: var(--paper);
  border: 1px solid var(--line-soft);
  border-radius: 0;             /* 사각형 (매거진) */
  padding: 24px;
  position: relative;
}
.kpi-card.alert::before,
.sum-card.alert::before {
  content: "";
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: var(--accent);
}
.kpi-card .lab,
.sum-card .lab {
  font-family: var(--font-sans);
  font-size: 9px;
  color: var(--ink);
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: .22em;
  margin-bottom: 10px;
}
.kpi-card.alert .lab {color: var(--accent)}
.kpi-card .num,
.sum-card .num {
  font-family: var(--font-serif);
  font-size: 48px;
  font-weight: 300;
  color: var(--ink);
  letter-spacing: -2px;
  line-height: 1;
}
.kpi-card .sub {
  font-family: var(--font-serif);
  font-style: italic;
  font-size: 12px;
  color: var(--ink-3);
  margin-top: 12px;
  line-height: 1.6;
}

/* 사이드바 */
.sidebar {
  background: var(--paper);
  border-right: 1px solid var(--ink);
  padding: 0;
  width: var(--sidebar-w);
}
.sb-section {padding: 0; margin: 0}
.sb-head {
  font-family: var(--font-sans);
  font-weight: 900;
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: .18em;
  color: var(--paper);
  background: var(--ink);
  padding: 14px 20px;
}
.sb-item {
  display: block;
  padding: 13px 20px;
  font-family: var(--font-sans);
  font-size: 13px;
  color: var(--ink);
  font-weight: 300;
  border-bottom: 1px solid var(--line-soft);
  letter-spacing: .02em;
}
.sb-item.sb-active,
.sb-item.active {
  background: var(--ink);
  color: var(--paper);
  font-weight: 700;
  border-left: 5px solid var(--accent);
  padding-left: 15px;
}

/* 폼 (검색·필터 등) */
.filter-bar,
form.filter,
.sample-filter {
  background: var(--paper);
  border: 1px solid var(--line-soft);
  padding: 16px 20px;
  border-radius: 0;
}
.filter-bar input,
.filter-bar select,
input[type="text"],
input[type="search"],
select {
  font-family: var(--font-sans);
  background: var(--paper);
  color: var(--ink);
  border: 1px solid var(--ink);
  border-radius: 0;
  padding: 8px 12px;
  font-size: 13px;
  font-weight: 500;
}
input[type="text"]:focus,
input[type="search"]:focus,
select:focus {
  outline: none;
  border-color: var(--accent);
  box-shadow: 0 0 0 1px var(--accent);
}

/* 버튼 — 매거진 톤 */
.btn,
button[type="submit"] {
  font-family: var(--font-sans);
  background: transparent;
  color: var(--ink);
  border: 1px solid var(--ink);
  border-radius: 0;
  padding: 9px 18px;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: .10em;
  text-transform: uppercase;
  cursor: pointer;
  transition: all var(--dur-fast) var(--ease);
}
.btn:hover {background: var(--ink); color: var(--paper)}

/* CTA = KNK 레드 솔리드 (B-2 원칙 유지) */
.btn-primary,
.btn-cta,
.btn-knk {
  background: var(--accent);
  color: #fff;
  border-color: var(--accent);
}
.btn-primary:hover {background: var(--ink); border-color: var(--ink); color: var(--accent)}

/* 테이블 */
table {
  width: 100%;
  border-collapse: collapse;
  font-family: var(--font-sans);
}
table thead th {
  background: var(--ink);
  color: var(--paper);
  font-size: 10px;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: .15em;
  padding: 12px 16px;
  text-align: left;
  border: 0;
}
table tbody td {
  padding: 14px 16px;
  border-bottom: 1px solid var(--line-soft);
  font-size: 13px;
  color: var(--ink);
  font-weight: 400;
}
table tbody tr:hover {background: var(--paper-2)}
```

---

## 6. HTML 정식 — 3 base 헤더

### 6-1. `app/templates/base.html`

```html
{% if user %}
<header class="topbar">
  <!-- Row 1: 마스트헤드 (CX23c 핵심) -->
  <div class="tb-masthead">
    <div class="tb-date">
      {{ today_kor|default('2026 · 4월 28일 화요일') }} · KNK INTEGRATED EDITION
    </div>
    <div class="tb-edition">
      VOL. 26 · NO. {{ edition_no|default('118') }}
    </div>
  </div>
  
  <!-- Row 2: 메인 -->
  <div class="tb-main">
    <div class="tb-left">
      <button class="tb-menu-btn" onclick="toggleSidebar()" title="{{ i.menu|default('메뉴') }}">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round"><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="18" x2="21" y2="18"/></svg>
      </button>
      
      <a href="/home" class="brand">
        <div class="brand-logo-wrap">
          <img src="/static/logo.png?v=20260428cx23c" alt="KNK HAIST Innovation"
               onerror="this.style.display='none';this.nextElementSibling.style.display='block'">
          <span class="fallback" style="display:none">K</span>
        </div>
      </a>
      
      <div class="tb-divider"></div>
      
      {% if workspaces and workspaces|length > 1 %}
      <nav class="ws-tabs" role="tablist" aria-label="워크스페이스 전환">
        {% for w in workspaces %}
        <a class="ws-tab {% if current_workspace and w.key == current_workspace.key %}active{% endif %}"
           href="{{ w.href }}"
           {% if w.external %}target="_blank" rel="noopener"{% endif %}
           role="tab"
           aria-selected="{% if current_workspace and w.key == current_workspace.key %}true{% else %}false{% endif %}"
           title="{{ w.desc }}">
          <span class="ws-ico" aria-hidden="true">{{ w.icon }}</span>
          <span class="ws-name">{{ w.name }}</span>
        </a>
        {% endfor %}
      </nav>
      {% endif %}
    </div>
    
    <div class="tb-center"></div>
    
    <div class="tb-right">
      <button class="tb-icon-btn victor" id="victorTrigger" onclick="victorToggleDock()" title="{{ i.victor|default('빅터') }} (Ctrl+K)">
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
          <div class="user-role">{{ user.rank or user.team_name or '대표이사' }}</div>
        </div>
      </a>
      <a href="/logout" class="logout-btn" title="{{ i.logout|default('로그아웃') }}">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>
      </a>
    </div>
  </div>
</header>
{% endif %}
```

### 6-2. `app/templates/base_sales.html` / `base_logi.html`

위 §6-1 헤더 구조와 동일하게 적용. 차이:
- `<a href="/sales">` (sales) / `<a href="/logistics">` (logi) — 로고 클릭 링크
- `tb-edition` 라벨 변경: "SALES EDITION" / "LOGISTICS EDITION"

---

## 7. main.py 컨텍스트 추가

```python
# 매거진 마스트헤드용 날짜·에디션 번호 (Phase 1)
import datetime

def get_edition_context():
    """CX23c 마스트헤드 컨텍스트 — 날짜 한글화 + edition NO."""
    today = datetime.date.today()
    weekdays = ['월', '화', '수', '목', '금', '토', '일']
    today_kor = f"{today.year} · {today.month}월 {today.day}일 {weekdays[today.weekday()]}요일"
    
    # Edition NO. = 일년 중 N번째 발행 (1월 1일 = 1)
    edition_no = today.timetuple().tm_yday
    
    return {
        "today_kor": today_kor,
        "edition_no": edition_no,
    }

# 모든 라우트 컨텍스트에 추가
ctx.update(get_edition_context())
```

---

## 8. 페이지별 변환 가이드 (Phase 2)

| 페이지 | 변환 핵심 |
|---|---|
| `home.html` | h1 시리프 weight 300 + KPI 카드 매거진 카테고리 라벨 + alert 카드 빨간 상단 라인 |
| `progress_matrix.html` | 매트릭스 thead 검정 솔리드 + 카테고리 라벨 (필터바도 매거진 톤) |
| `dashboard.html` | 매거진 spread 레이아웃 + KPI 4개 시리프 큰 숫자 |
| `changes.html` / `tickets.html` / `issues.html` | 카드 1px 라인 + 카테고리 라벨 + byline italic |
| `daily.html` | 일일 보고서 매거진 톤 (날짜 헤더 마스트헤드) |
| `admin.html` | 관리자 페이지 톤 매거진 (테이블 강한 검정 thead) |

---

## 9. 로그인 페이지 (Phase 3)

`login.html` 매거진 spread 형태로 재설계:
- 좌측 80% — 인쇄지 베이지 + 큰 시리프 헤드라인 + 마스트헤드
- 우측 20% — 폼 (sans 라벨)
- 빅터(05) Phase 3 시점에 별도 시안 발행 예정 (CX23c 로그인 spread 시안)

→ Phase 3 시작 시점에 빅터(05)에 시안 요청. 발주서 받기 전 임시: 현재 sage 로그인 유지.

---

## 10. 빅터 도크 (Phase 3)

- 도크 head: 매거진 톤 (검정 + 흰색 시리프 "HAIST 빅터")
- 모드 탭 (빅터/검색): COVER 라벨 스타일 차용 (작은 빨간 점)
- 검색 input: sans + 1px 검정 라인
- 채팅 버블: 사용자(검정) / AI(흰색 + 1px 라인) 분리

상세 시안 Phase 3 시점 빅터(05) 발주.

---

## 11. 자체 검증 grep (20종 — 응답 시 첨부)

### A. 정합 (PASS = ≥1)

```bash
# 토큰 적용 확인
grep -c "\-\-paper:" static/style.css                          # ≥1
grep -c "\-\-ink:" static/style.css                            # ≥1
grep -c "\-\-accent:" static/style.css                         # ≥1
grep -c "\-\-font-serif" static/style.css                      # ≥1

# 헤더 마스트헤드
grep -c 'class="tb-masthead"' app/templates/base.html          # ≥1
grep -c 'class="tb-masthead"' app/templates/base_sales.html    # ≥1
grep -c 'class="tb-masthead"' app/templates/base_logi.html     # ≥1
grep -c 'class="tb-edition"' app/templates/base.html           # ≥1

# WS-tabs COVER 라벨 (CX23c 핵심)
grep -c 'content: "COVER"' static/style.css                    # ≥1

# 시리프 헤드라인
grep -c "font-family: var(\-\-font-serif)" static/style.css    # ≥3 (h1, h2, kpi-num)

# 빅터 트리거 KNK 레드
grep -c "tb-icon-btn.victor" static/style.css                  # ≥1

# main.py 마스트헤드 컨텍스트
grep -c "today_kor" app/main.py                                # ≥1
grep -c "edition_no" app/main.py                               # ≥1
```

### B. 결함 (PASS = 0)

```bash
# 옛 sage 그라디언트 헤더 사용 안 함
grep -c "background: var(\-\-grad-header)" app/templates/base.html        # 기대 0
grep -c "background: var(\-\-grad-aurora" app/templates/base.html         # 기대 0

# brand-text 표시 안 됨 (활성 탭에 정보)
grep -nE "\.brand-text\s*\{[^}]*display:\s*none" static/style.css         # ≥1

# v3 가로탭 패턴 잔존 (현재 LIVE 적용된 amber 펄스 → CX23c COVER 라벨로 대체)
grep -c "wsActivePulse" static/style.css                                   # 0 (CX23c는 cx23cPulse)
```

→ **15 PASS + 5 FAIL = 20종 grep 후 회신**.

---

## 12. 페르소나 walkthrough (8종 — 응답 시 첨부)

| # | 시나리오 | PASS 조건 |
|---|---|---|
| W1 | /home 진입 | 마스트헤드 (날짜·VOL/NO) 보임 / 통합 활성 + COVER 빨간 라벨 |
| W2 | /sales 진입 | 매출·영업 활성 + COVER 라벨 / 마스트헤드 SALES EDITION (선택) |
| W3 | /logistics 진입 | 자재·구매 활성 + COVER 라벨 |
| W4 | 활성 탭 클릭 → 다른 워크스페이스 이동 | COVER 라벨이 새 활성 탭으로 이동 |
| W5 | / 키 누름 | 빅터 도크 자동 열림 + 검색 모드 진입 |
| W6 | 헤드라인 시각 확인 | 시리프 폰트 (Times New Roman) + 가벼운 weight 300 |
| W7 | KPI 카드 alert 확인 | 상단에 3px 빨간 라인 보임 |
| W8 | 모바일 (1100px 이하) | 비활성 탭 텍스트 숨김, 활성만 작은 텍스트 |

---

## 13. BAT 갱신 (Phase 5 — 01 책임)

```
LAST UPDATE: 2026-04-28 G8_v4_CX23c_매거진70_전체재스킨_3base+style.css+9페이지+로그인+도크_매거진톤+시리프헤드라인+모노크롬+KNK레드한점
```

또는 짧게:
```
2026-04-28 G8_v4_CX23c_매거진재스킨_(05디자인,대표승인) 
```

**갱신 대상**: `KNK_시작.bat` line 3 + line 7 / `START.bat` line 3 + line 7.

---

## 14. 마감 일정

| Phase | 시점 | 산출물 | 검증 |
|---|---|---|---|
| 발주 (현재) | 2026-04-28 | 본 정식 지시서 | — |
| **Phase 1** | **+6h** | 토큰 + 3 base 헤더 + main.py | grep §11-A 6종 |
| **Phase 2** | **+14h** | 9개 페이지 본체 + 카드/폼/테이블 | grep §11-A 12종 |
| **Phase 3** | **+20h** | 로그인 매거진 spread + 빅터 도크 (별도 시안 요청) | grep §11-A 16종 |
| **Phase 4** | **+24h** | 04 페르소나 walkthrough W1~W8 + grep 20종 | 회귀 통과 |
| **Phase 5** | 직후 | BAT 갱신 | LAST UPDATE 확인 |

---

## 15. 회신 양식

```markdown
# _FROM_01_2026-04-28_v4CX23c_응답_PhaseN.md

## Phase N 착수 / 완료
- 시작: 2026-04-28 HH:MM
- 완료: 2026-04-28 HH:MM
- 변경 라인: ~~~줄

## §11 자체 grep 검증 (Phase N 누적)
| 항목 | 결과 | 기대 | PASS |
|---|---|---|---|
| --paper 토큰 | N | ≥1 | ✅ |
| tb-masthead in base.html | N | ≥1 | ✅ |
| ... |

## §12 페르소나 walkthrough (해당 Phase)
| W# | 시나리오 | 결과 |
|---|---|---|
| W1 | /home 마스트헤드 | ✅ |
| ... |

## BAT 갱신 (Phase 5)
- KNK_시작.bat: 갱신 ✅
- START.bat: 갱신 ✅

## 발견 이슈 / 질문
- 빅터(05)에 즉시 질의: 매거진 톤 페이지 변환 시 sage 변수 처리 방식 (보존 vs 제거)
- ...
```

---

## 16. 주요 사양 변경 요약 (sage v2 → CX23c v4)

| 영역 | sage v2 | CX23c v4 |
|---|---|---|
| Body bg | sage-100 (#F0F5EB) | **#FAFAF7 (paper)** |
| Body text | sage-800 (#2B3E2E) | **#0A0A0A (ink)** |
| Topbar bg | grad-aurora 그라디언트 | **#FAFAF7 + 3px 검정 상단 + 마스트헤드** |
| Topbar font | sans 모두 | **시리프 헤드라인 + sans UI 혼용** |
| Workspace tabs | amber 펄스 활성 | **COVER 빨간 라벨 + 작은 빨간 점** |
| Logo wrap | 흰 배경 박스 | **투명 + 원본 색상** (filter:none) |
| KPI 숫자 | sans bold | **시리프 weight 300 큰 숫자** |
| 카드 | radius 14px sage 톤 | **사각형 (radius 0) + 1px 검정 라인** |
| Alert | sage-warning 톤 | **상단 3px 빨간 라인** |
| 사이드바 | sage-50 sans | **paper + sans + 활성 검정+빨강 라인** |

---

## 17. 첨부

```
✅ 03_시안/_03_v4_탐색_6옵션/CX23c_CuratedMagazine_매거진70.html  ← 대표 승인본 (시각 참고)
✅ 03_시안/_03_v4_탐색_6옵션/README.md                            ← 19개 옵션 비교 인덱스
✅ 본 지시서
```

---

## 18. 빅터 후속 작업 (병행)

빅터(05)는 본 지시서 발행 직후 다음 작업 병행:
1. 시안 12B 마스터 + 14~20 (페이지 시안 9종) → CX23c 톤 갱신
2. 시안 13 (로그인) → 매거진 spread 톤 시안
3. Phase 1 완료 후 04 운영테스트팀에 페르소나 walkthrough 의뢰
4. 매시간 LIVE 점검 (정책 §시간단위LIVE점검) 시 CX23c 정합 grep 추가

→ 01 진행 상황과 별개로 빅터 자체 시안·검증 진행. 1차 마감 시점에 양쪽 정합 확인.

---

## 19. 신 프로토콜 적용 (정상)

```
[1] 빅터(05) 디자인 시안 (4 라운드 19개) ✅
[2] 대표 검토 + 선택 ✅ ("CX23c 진행할께")
[3] 빅터 → 01 정식 지시서 발행 ✅ (현재)
[4] 01 작업 (~24h, 5 phase)
[5] 01 → BAT 갱신
[6] 04 회귀 + 빅터 grep 검증
[7] 09 → 정상 사이클 보고
```

---

**발행**: 2026-04-28 · 05 디자인팀 세션 빅터
**상태**: 🟢 **v4 CX23c 정식 발주 (대표 직접 승인) · 5 phase 약 24h · BAT 갱신 01 책임**
**회신 위치**: `01_HAIST_WORKS/_FROM_01_2026-04-28_v4CX23c_응답_Phase[N].md`
**문의**: 즉시 빅터(05)에 — 단독 결정 금지, 빅터·09 협의 후 진행
