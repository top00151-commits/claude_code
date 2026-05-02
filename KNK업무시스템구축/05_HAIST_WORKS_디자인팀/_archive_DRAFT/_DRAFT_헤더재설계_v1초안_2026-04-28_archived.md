---

# 🛑 HOLD — 본 지시서는 DRAFT 상태입니다 (대표 검토 대기)

**보류 사유**: 대표 직접 지시 (2026-04-28) — *"변경한 디자인을 내가 먼저 확인하고 실무팀에 지시할께."*

**현재 상태**:
- ❌ 01 세션에 발송 안 됨 (지시서 _세션01_전달/ 폴더 외부에 위치)
- ✅ 디자인 프리뷰 파일 발행: `03_시안/12B_PREVIEW_새헤더_가로탭_검색도크이전.html`
- ⏳ 대표 프리뷰 검토 후 승인 시 본 지시서 _세션01_전달/ 으로 이동 + 01 작업 시작

**대표 승인 시 절차**:
1. 본 파일을 `_세션01_전달/_TO_01_2026-04-28_긴급UX재설계_헤더가로탭+검색빅터이전+사이드바정리.md` 으로 이동
2. 01 즉시 인지 + 1차 마감 +4시간 카운트 시작

**대표 거절·수정 시**:
1. 빅터(05) 프리뷰 재작성
2. 본 지시서 §3 HTML 스펙 갱신
3. 다시 검토 받기

---

# [05 → 01] 🔴 긴급 UX 재설계 — 헤더 가로 워크스페이스 탭 + 검색 빅터 이전 + 사이드바 정리 (DRAFT)

> **발신**: 05 디자인팀 세션 빅터
> **수신**: 01 메인 세션 (대표 승인 후)
> **참조**: 09 프로젝트 팀장 / 04 운영테스트팀 / 대표이사
> **일자**: 2026-04-28
> **트리거**: 대표 직접 지시 3건
> **지위**: 🟡 **DRAFT · 대표 검토 대기 — 승인 전 01 작업 금지**

---

## 0. 한 줄

대표 직접 지시: ① 상단 검색바를 빅터 도크로 이전 ② 워크스페이스 3개를 가로 탭으로 일자 나열 (활성=큰아이콘, 비활성=작게) ③ 사이드바에서 워크스페이스 선택 제거 ④ 매출영업·자재구매 창에도 동일 적용. **3개 base 템플릿 + style.css 동시 작업, 빅터(05) 직접 핫패치 거부 → 01 정식 처리 의뢰**.

---

## 1. 대표 직접 발화 (출처)

> 1. *"메인페이지에 상단부 검색창을 빅터AI 창으로 이동 시켰으면 좋겠어"*
> 2. *"'KNK 통합 업무 플랫폼' '매출영업센터' '자재구매센터' 이 내용을을 일자로 나열하고 해당 창일때 글씨를 아이콘 처리해서 크게 보이고 나머지는 조금 작게 표현, 항상 선택된걸 아이콘처리로 확실하게 보이게.."*
> 3. *"매출영업센터, 자재구매센터 창들도 동일하게 적용."*
> 4. *"사이드바에서 선택하게 하지말고."*

---

## 2. 변경 범위 (5개 파일)

| 파일 | 변경 |
|---|---|
| `app/templates/base.html` | 헤더 ws-wrap 제거 → ws-tabs / 헤더 .tb-center 제거 → 도크에 .dock-search-wrap / / 단축키 JS 갱신 |
| `app/templates/base_sales.html` | 헤더에 ws-tabs 신규 추가 (현재 ws-switcher 없음) / "통합 메인" 링크는 ws-tabs 로 흡수 |
| `app/templates/base_logi.html` | 동일 |
| `static/style.css` | 신규 .ws-tabs / .ws-tab / .dock-search* 스타일 추가 (기존 .ws-switcher / .ws-menu 는 deprecated 표기 후 보존) |
| (선택) `app/templates/base.html` 사이드바 | "도메인 그룹"(매출·영업/자재·구매) 사이드바 항목 제거 — C안 v2 §B 이미 명시 |

**main.py 변경 불필요**: `workspaces` 컨텍스트 이미 모든 라우트에 제공 (line 153).

---

## 3. 신규 HTML 구조

### 3-1. `app/templates/base.html` — 헤더 변경

```html
<!-- 변경 전 (line 31~55) -->
{% if workspaces and workspaces|length > 1 %}
<div class="tb-divider"></div>
<div class="ws-wrap" id="wsWrap">
  <button class="ws-switcher" id="wsBtn" type="button" aria-haspopup="true" aria-expanded="false">
    <svg class="ws-ico" ...></svg>
    <span class="ws-name">{{ (current_workspace.name if current_workspace else '통합') }}</span>
    <span class="ws-caret">▾</span>
  </button>
  <div class="ws-menu" id="wsMenu" role="menu">
    {% for w in workspaces %}
    <a class="ws-opt {% if current_workspace and w.key == current_workspace.key %}active{% endif %}" ...>
      <div class="opt-ico">{{ w.icon }}</div>
      <div class="opt-meta">
        <div class="opt-name">{{ w.name }}</div>
        <div class="opt-desc">{{ w.desc }}</div>
      </div>
      ...
    </a>
    {% endfor %}
  </div>
</div>
{% endif %}
```

```html
<!-- 변경 후 -->
{% if workspaces and workspaces|length > 1 %}
<div class="tb-divider"></div>
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
    {% if w.external %}<span class="ws-ext" aria-hidden="true">↗</span>{% endif %}
  </a>
  {% endfor %}
</nav>
{% endif %}
```

### 3-2. `app/templates/base.html` — `.tb-center` 제거 (검색 도크로 이전)

```html
<!-- 변경 전 (line 58~93) — 전체 블록 제거 -->
<div class="tb-center" style="position:relative">
  <form class="g-search" action="/search" method="get" role="search">...</form>
  <div id="gSearchSugg" ...></div>
</div>
<script>
// gSearchSuggest function (debounce 250ms)
</script>
```

```html
<!-- 변경 후 -->
{# 핫패치 2026-04-28 — 글로벌 검색 헤더 → 빅터 도크 이전 (대표 직접 지시) #}
{# script (gSearchSuggest) 는 도크 영역으로 이동 #}
```

### 3-3. `app/templates/base.html` — 빅터 도크에 검색 추가

기존 `<aside class="dock" id="victorDock">` 안 `dock-head` 직후에 신규 추가:

```html
<aside class="dock" id="victorDock" aria-label="HAIST Victor 어시스턴트">
  <div class="dock-head">...</div>
  
  {# 핫패치 2026-04-28 — 글로벌 검색 (헤더에서 이전) #}
  <div class="dock-search-wrap" style="position:relative">
    <form class="dock-search" action="/search" method="get" role="search">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round">
        <circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/>
      </svg>
      <label for="gSearchInput" class="sr-only">{{ i.search_ph|default('업무·사람·문서 검색') }}</label>
      <input type="search" name="q" id="gSearchInput" placeholder="{{ i.search_ph|default('업무·사람·문서 검색...') }}"
             autocomplete="off"
             oninput="gSearchSuggest(this.value)"
             onblur="setTimeout(function(){var el=document.getElementById('gSearchSugg');if(el)el.style.display='none'},200)"
             onfocus="if(this.value.length>=2)gSearchSuggest(this.value)">
      <span class="shortcut">/</span>
    </form>
    <div id="gSearchSugg" class="g-search-sugg dock-search-sugg"
         style="display:none;position:absolute;top:100%;left:16px;right:16px;background:#fff;border:1px solid var(--sage-300);border-radius:10px;box-shadow:0 8px 22px rgba(0,0,0,.10);max-height:380px;overflow:auto;z-index:9999;margin-top:4px"></div>
  </div>
  
  <div class="dock-ctx">...</div>
  ...
</aside>
```

`gSearchSuggest()` 함수는 base.html 의 다른 `<script>` 블록으로 이동 (도크와 무관, 전역 함수).

### 3-4. `app/templates/base.html` — `/` 단축키 JS 갱신

```javascript
// 변경 전 (line 404~411)
document.addEventListener('keydown', function(e){
  if (e.key !== '/' || e.ctrlKey || e.metaKey || e.altKey || e.isComposing) return;
  const t = (e.target.tagName || '').toLowerCase();
  if (t === 'input' || t === 'textarea' || t === 'select' || e.target.isContentEditable) return;
  const i = document.getElementById('gSearchInput');
  if (i) { e.preventDefault(); i.focus(); i.select(); }
});
```

```javascript
// 변경 후 — 빅터 도크 자동 열기 + 검색 포커스
document.addEventListener('keydown', function(e){
  if (e.key !== '/' || e.ctrlKey || e.metaKey || e.altKey || e.isComposing) return;
  const t = (e.target.tagName || '').toLowerCase();
  if (t === 'input' || t === 'textarea' || t === 'select' || e.target.isContentEditable) return;
  e.preventDefault();
  // 빅터 도크 닫혀있으면 열고
  if (!document.body.classList.contains('dock-open') && typeof victorToggleDock === 'function') {
    victorToggleDock();
  }
  // 검색 입력에 포커스 (도크 열림 트랜지션 후)
  setTimeout(function(){
    const i = document.getElementById('gSearchInput');
    if (i) { i.focus(); i.select(); }
  }, 320);
});
```

### 3-5. `app/templates/base_sales.html` — 헤더 가로 탭 추가

기존 `<div class="tb-left">` 의 `<a href="/sales" class="tb-brand">` 직후에 ws-tabs 추가, `tb-right`의 `<a href="/home" class="tb-home-link">` 제거 (ws-tabs로 흡수):

```html
<header class="topbar topbar-hub-sales">
  <div class="tb-left">
    <button class="tb-menu-btn" ...>...</button>
    <a href="/sales" class="tb-brand">...</a>
    
    {# 핫패치 2026-04-28 — 워크스페이스 가로 탭 (대표 직접 지시) #}
    {% if workspaces and workspaces|length > 1 %}
    <div class="tb-divider"></div>
    <nav class="ws-tabs" role="tablist" aria-label="워크스페이스 전환">
      {% for w in workspaces %}
      <a class="ws-tab {% if current_workspace and w.key == current_workspace.key %}active{% endif %}"
         href="{{ w.href }}" role="tab"
         aria-selected="{% if current_workspace and w.key == current_workspace.key %}true{% else %}false{% endif %}"
         title="{{ w.desc }}">
        <span class="ws-ico" aria-hidden="true">{{ w.icon }}</span>
        <span class="ws-name">{{ w.name }}</span>
      </a>
      {% endfor %}
    </nav>
    {% endif %}
  </div>
  <div class="tb-spacer"></div>
  <div class="tb-right">
    <button class="tb-icon-btn victor" id="victorTrigger" ...>...</button>
    {# 핫패치 2026-04-28 — "통합 메인" 링크 제거 (ws-tabs 로 통합) #}
    <a href="/profile" class="tb-user-chip">...</a>
    <a href="/logout" class="logout">...</a>
  </div>
</header>
```

도크 검색 추가는 매출/자재 Hub 에 빅터 도크가 있는 경우에만. 도크 구조 확인 후 §3-3과 동일 추가.

### 3-6. `app/templates/base_logi.html` — base_sales 와 동일 패턴

### 3-7. (선택) `app/templates/base.html` — 사이드바 도메인 그룹 제거

C안 v2 §B 에 이미 명시: *"도메인 그룹 (매출·영업/자재·구매) 사이드바에서 제거"*

base.html 사이드바 검색 → 매출·영업/자재·구매 관련 sb-section 또는 sb-item 식별 → 제거.

---

## 4. 신규 CSS (style.css 끝에 추가)

```css
/* ============================================================
   워크스페이스 가로 탭 (대표 직접 지시 2026-04-28)
   - 3개 워크스페이스 일자 나열
   - 활성: 큰 아이콘 + 진한 배경 + 18% 큰 폰트
   - 비활성: 작은 텍스트 + 흐림
   - 3개 base 템플릿 공통 (base.html / base_sales.html / base_logi.html)
   ============================================================ */
.ws-tabs {
  display: flex;
  gap: 4px;
  align-items: center;
  flex-wrap: nowrap;
}
.ws-tab {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 5px 10px;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.06);
  color: rgba(255, 255, 255, 0.62);
  font-size: var(--fs-fluid-xs, 11px);
  font-weight: 600;
  border: 1px solid transparent;
  text-decoration: none;
  transition: all 0.2s var(--ease, cubic-bezier(0.25, 0.8, 0.25, 1));
  white-space: nowrap;
  letter-spacing: 0.1px;
}
.ws-tab:hover {
  background: rgba(255, 255, 255, 0.16);
  color: rgba(255, 255, 255, 0.95);
}
.ws-tab .ws-ico {
  width: 14px;
  height: 14px;
  flex-shrink: 0;
  opacity: 0.78;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}
.ws-tab .ws-ico svg {
  width: 100%;
  height: 100%;
  display: block;
}

/* 활성 탭 — 아이콘 처리, 큰 폰트 */
.ws-tab.active {
  background: rgba(255, 255, 255, 0.22);
  color: #fff;
  font-size: var(--fs-fluid-sm, 14px);
  font-weight: 800;
  padding: 8px 16px;
  border-color: rgba(255, 255, 255, 0.35);
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.15);
  letter-spacing: 0.2px;
}
.ws-tab.active .ws-ico {
  width: 22px;
  height: 22px;
  opacity: 1;
  color: #D4B876;  /* 헤더 전반과 동일한 amber 톤 */
}
.ws-tab .ws-ext {
  font-size: 9px;
  opacity: 0.6;
  margin-left: 2px;
}

/* 모바일 — 폭 제한 시 텍스트 숨김, 아이콘만 */
@media (max-width: 900px) {
  .ws-tab .ws-name { display: none; }
  .ws-tab.active .ws-name { display: inline; font-size: 12px; }
  .ws-tab { padding: 6px 8px; }
  .ws-tab.active { padding: 7px 12px; }
}

/* 글로벌 검색 — 빅터 도크 내 (대표 직접 지시 2026-04-28) */
.dock-search-wrap {
  padding: 12px 16px 0 16px;
}
.dock-search {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  background: var(--sage-50, #F7FAF4);
  border: 1.5px solid var(--sage-300, #CAD9B8);
  border-radius: 12px;
  transition: all 0.2s var(--ease);
}
.dock-search:focus-within {
  border-color: var(--sage-500, #7FA183);
  box-shadow: 0 0 0 4px rgba(127, 161, 131, 0.15);
}
.dock-search svg {
  width: 18px;
  height: 18px;
  color: var(--ink-3, #5D7F61);
  flex-shrink: 0;
}
.dock-search input {
  flex: 1;
  border: 0;
  outline: 0;
  background: transparent;
  font-size: var(--fs-fluid-sm, 13px);
  color: var(--ink, #2B3E2E);
  font-weight: 500;
  min-width: 0;
}
.dock-search input::placeholder {
  color: var(--ink-4, #8FA594);
}
.dock-search .shortcut {
  font-size: 10px;
  color: var(--ink-4, #8FA594);
  padding: 2px 6px;
  background: var(--sage-100, #F0F5EB);
  border-radius: 4px;
  font-family: ui-monospace, Menlo, Consolas, monospace;
  flex-shrink: 0;
}

/* 옛 .ws-switcher / .ws-menu — 비활성 (제거 또는 deprecated) */
/* 본 핫패치 적용 후 .ws-switcher 사용 안 함. 보존만 — 다음 정리 사이클에서 제거. */
```

---

## 5. 12B 시안 정합 (선택, v2 정합)

`05_HAIST_WORKS_디자인팀/03_시안/12B_healing_sage_garden.html` 도 동일 패턴으로 갱신:
- ws-wrap 부분 → ws-tabs
- tb-center 검색 → 도크에 dock-search

→ v2 1차 마감 시점에 함께 처리 또는 빅터(05) 후속 작업.

---

## 6. 자체 검증 grep (15종 — 응답 시 첨부)

### A. 정합 (PASS = ≥1)

```bash
# ws-tabs 적용
grep -c '<nav class="ws-tabs"' app/templates/base.html         # 기대 ≥1
grep -c '<nav class="ws-tabs"' app/templates/base_sales.html   # 기대 ≥1
grep -c '<nav class="ws-tabs"' app/templates/base_logi.html    # 기대 ≥1
grep -c '\.ws-tabs\s*{' static/style.css                       # 기대 ≥1
grep -c '\.ws-tab\.active' static/style.css                    # 기대 ≥1

# 검색 도크 이전
grep -c 'dock-search-wrap' app/templates/base.html             # 기대 ≥1
grep -c '\.dock-search\s*{' static/style.css                   # 기대 ≥1
grep -c 'gSearchInput' app/templates/base.html                 # 기대 ≥1 (도크 안에)

# / 단축키 빅터 자동 열기
grep -c 'victorToggleDock' app/templates/base.html             # 기대 ≥2 (트리거 + 단축키)
```

### B. 결함 (PASS = 0)

```bash
# 헤더 옛 ws-switcher 제거
grep -c '<button class="ws-switcher"' app/templates/base.html  # 기대 0
grep -c '<div class="ws-menu"' app/templates/base.html         # 기대 0

# 헤더 .tb-center 검색 제거
grep -c '<div class="tb-center"' app/templates/base.html       # 기대 0
grep -c '<form class="g-search"' app/templates/base.html       # 기대 0

# 매출/자재 헤더 "통합 메인" 링크 제거
grep -c 'tb-home-link' app/templates/base_sales.html           # 기대 0
grep -c 'tb-home-link' app/templates/base_logi.html            # 기대 0
```

→ 9 PASS + 6 FAIL = 15종 grep 후 회신.

---

## 7. 페르소나 walkthrough (5종 — 응답 시 첨부)

| # | 시나리오 | PASS 조건 |
|---|---|---|
| W1 | /home 진입 → 헤더 가로 탭 3개 (통합·매출·자재) 일자 나열 | 통합 = 큰 활성 / 나머지 2개 = 작은 비활성 |
| W2 | /sales 진입 | 매출·영업 센터 = 큰 활성 / 나머지 = 작은 비활성 |
| W3 | /home 에서 매출 탭 클릭 → /sales 이동 | 페이지 이동 후 헤더 활성 탭이 매출로 변경 |
| W4 | / 키 누름 (어디서든) | 빅터 도크 자동 열림 + 검색 입력 자동 포커스 |
| W5 | /home 헤더에 검색바 안 보임 | tb-center 영역 비어 있음 (탭만 보임) |

---

## 8. 마감 일정

| 단계 | 시점 | 산출물 |
|---|---|---|
| 발주 | 2026-04-28 (현재) | 본 지시서 |
| **1차 마감** | **+4시간 (긴급)** | base.html ws-tabs + dock-search 적용 + style.css 추가 |
| **2차 마감** | **+8시간** | base_sales.html + base_logi.html + 사이드바 정리 + 모바일 반응형 |
| **3차 (회귀)** | **+12시간** | 04 페르소나 walkthrough 5종 + 빅터(05) grep 15종 검증 |
| **BAT 갱신** | 2/3차 마감 직후 | 01이 KNK_시작.bat / START.bat LAST UPDATE 라인 갱신 |

**긴급 우선순위** — v2 §2 작업 범위와 별도 사이클로 처리. v2 1차 마감(2026-04-26 23:00)에는 영향 안 주도록 분리.

---

## 9. 회신 양식

```markdown
# _FROM_01_2026-04-28_헤더재설계_응답_1차.md

## 착수 / 완료 시각
- 시작: 
- 1차 완료: 
- 변경 라인: ~~~줄

## §6 자체 grep 검증 (15종)
| 항목 | 결과 | 기대 | PASS |
|---|---|---|---|
| <nav class="ws-tabs" base.html | N | ≥1 | ✅ |
| ... |

## §7 페르소나 walkthrough (5종)
| W# | 시나리오 | 결과 |
|---|---|---|
| W1 | 통합 진입 | ✅ |
| ... |

## BAT 갱신
- KNK_시작.bat LAST UPDATE: 갱신 ✅
- START.bat LAST UPDATE: 갱신 ✅

## 발견 이슈 / 질문
- ...
```

---

## 10. 빅터 직접 핫패치 거부 사유 (정책 §4-2 준수)

본 변경은 빅터(05) 시간 단위 LIVE 점검 정책 §4-2 "큰 변경 (다중 파일·구조 변경)" 에 해당:
- 5개 파일 변경 (base 3개 + style.css + 사이드바)
- 헤더 구조 자체 재설계 (ws-switcher 패턴 → ws-tabs 패턴)
- 검색 기능 위치 이전 (헤더 → 빅터 도크)
- JS 단축키 동작 변경 (/ 키 → 빅터 자동 열기)

빅터 단독 핫패치 시 3개 base 일관성 + 회귀 검증 + main.py 컨텍스트 검증 부담 큼 → 01 정식 처리 의뢰가 정상 사이클.

**빅터 자기검증 6차 약속 적용 첫 사례** — 단독 처리 가능 작은 변경과 01 위임 큰 변경 분리 운영.

---

## 11. 첨부

- 본 지시서
- (선행) `_정책_시간단위LIVE직관성점검_2026-04-28.md` (정책 발효 문서)
- (선행) `_TO_01_2026-04-28_핫패치LIVE변경전체보고_BAT인계.md` (오늘 G6 핫패치 7건 인계)

---

**발행**: 2026-04-28 · 05 디자인팀 세션 빅터
**상태**: 🔴 **긴급 우선순위 · 1차 마감 +4시간 / 2차 +8시간 / 회귀 +12시간**
**회신 위치**: `01_HAIST_WORKS/_FROM_01_2026-04-28_헤더재설계_응답_1차.md`
**문의**: 즉시 빅터(05)에 — 단독 결정 금지, 빅터·09 협의 후 진행
