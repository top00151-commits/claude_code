# 🔴 UX 결함 진단서 — 가로 스크롤 매트릭스 5종 + 필터 라벨 시스템 일관성

> **작성**: 05 디자인팀 세션 빅터
> **일자**: 2026-04-25 17:50
> **트리거**: 대표 직접 점검 — *"실제 사람이 사용하는건데.. 빅터 너가 직접 테스트하는 조건으로만 만든게 아닌가"*
> **범위**: LIVE 코드(01_HAIST_WORKS) 5개 페이지 + 시안(03_시안) 1개
> **심각도**: 🔴 **S1 (페르소나 핵심 동선 마비)**

---

## 0. 한 줄

진행률 매트릭스 결함 점검 중 **시스템 차원 동일 결함 5개 페이지** 동시 발견. 시안에도 결함 존재 → v2 통째 이식해도 결함 잔존. **빅터 자기검증 결정적 실패**.

---

## 1. 트리거 — 대표 점검 발화

> 1. *"전체사업부에 검사기 또는 자동화를 선택하고 나서 해당 사업부만 검색을 할려고할때... 확인 검색 이런 버튼이 없어.. 필터, 초기화 이건 다른 기능인것 같고.."*
> 2. *"매트릭스로 보기를 하면 부서가 옆으로 다 보이질 않아 옆으로 이동시키는 스크롤바도 제일 밑으로 내려야만 볼수있는데.. 그렇게하면 내가 보고있던 제일 윗줄은 또 안보고이고..."*
> 3. *"이런 편이성에 대한 조건들이 너무 부족해.. 실제 사람이 사용하는건데.. 빅터 너가 직접 테스트하는 조건으로만 만든게 아닌가 싶네"*

→ 두 개의 구체 결함 + 한 개의 프로세스 비판.

---

## 2. 결함 매트릭스 (S = 심각, A = 중대, B = 폴리시)

### S1. 필터 버튼 라벨 시스템 비일관 (1페이지)

| 페이지 | 버튼 라벨 | 라인 |
|---|---|---|
| `progress_matrix.html` | **"필터"** ❌ (의미 모호) | line 88 |
| `changes_list.html` | "검색" ✅ | line 52 |
| `issues_list.html` | "검색" ✅ | line 59 |
| `tickets_list.html` | "검색" ✅ | line 41 |
| `parts.html` | "검색" ✅ | line 27 |
| `po_list.html` | "검색" ✅ | line 24 |
| `projects.html` | "검색" ✅ | line 32 |
| `stock_movements.html` | "검색" ✅ | line 64 |
| `stock_safety.html` | "검색" ✅ | line 34 |
| `suppliers.html` | "검색" ✅ | line 15 |
| `admin_permissions_matrix.html` | "조회" 🟡 | line 38 |
| `admin_permissions_audit.html` | "필터 적용" 🟡 | line 52 |

**진단**: `progress_matrix` 만 단독 "필터" — 나머지 페이지 **9개가 "검색"으로 통일**. 시스템 일관성 결함.

**페르소나 영향**:
- **P1 영업** 매일 본 페이지 사용 → 다른 페이지에서는 "검색" 익숙한데 여기만 "필터" → 인지 부담
- **P3 기구설계 PM** 동일

### S2. 가로 스크롤 매트릭스 sticky left column 누락 (5페이지)

| 페이지 | min-width | overflow-x | sticky thead | sticky left col | 페르소나 영향 |
|---|---|---|---|---|---|
| `progress_matrix.html` | 1400px | auto | ✅ top:0 | ❌ **없음** | P1·P3·CEO 핵심 화면 |
| `stock_safety.html` | 1300+px | auto | ❌ | ❌ **없음** | P6 자재팀 매일 본 화면 |
| `stock_reorder.html` | 1200+px | auto | ❌ | ❌ **없음** | P6 자재팀 |
| `sales_outstanding.html` | 1300+px | auto | ❌ | ❌ **없음** | P1 영업 매일 |
| `sales_aging.html` | 1300+px | auto | ❌ | ❌ **없음** | P1 영업 |
| `admin_permissions_matrix.html` | — | — | — | ✅ **있음** (P4 관리자만) | 결함 없음 |

**진단**: **일반 사용자 페이지 5개 모두 sticky left column 0건**. 관리자 전용(P4) 1개만 적용. 즉 **임원·영업·자재·PM 전 직원이 영향**.

**구체 사용자 행동 분석**:
1. 진행률 매트릭스 열기 → 84개 프로젝트 행 + 16개 컬럼 (관리코드·프로젝트·전체·12공정·납기) 보임
2. 우측 컬럼(가공·구매·조립·검사·납품) 보려면 가로 스크롤 필요
3. 컨테이너에 `max-height` 없음 → 84행 모두 렌더 → 가로 스크롤바 위치는 84행 후 = **페이지 맨 아래**
4. 사용자 페이지 스크롤다운 → 가로 스크롤바 도달 → 좌우 스크롤 → **방금 보던 윗행은 시야 밖**
5. 페이지 위로 다시 스크롤 → 스크롤다운하면 가로 스크롤도 리셋됨? 아니면 위치 유지? 불확실 → 인지 부담 폭증

**해결**:
- A) 컨테이너 `max-height: calc(100vh - 320px); overflow: auto` → 가로 스크롤바가 항상 화면 안 보임
- B) 첫 2 컬럼(관리코드·프로젝트) `position: sticky; left: 0` → 우측 스크롤해도 행 정체 유지
- C) thead `position: sticky; top: 0` → 이미 있음

### S3. 가로 스크롤 컨테이너 max-height 미설정 (5페이지)

S2와 같은 5개 페이지 모두 `max-height` 없음 → S2 #4 시나리오 발생.

### A1. 매트릭스 컬럼 밀도 과다

진행률 매트릭스 16 컬럼 (관리코드·프로젝트·전체·수주·컨셉·기구설계·전장설계·소프트웨어·가공·구매·조립·검사·도장·포장·납품·납기). 14인치 노트북(1366px) 기준 모두 안 보임. 카드뷰 토글 있으나 우측 작은 버튼.

**해결**: 
- 컬럼 우선순위 분류 → 기본 표시 8개 + "추가 컬럼" 토글
- 또는: 컬럼 너비 균등 압축 시 가독성 손실 → 기본 sticky+max-height만으로도 80% 해결

### A2. 필터 폼 인라인 스타일 (시스템 일관성 손실)

```html
<form method="get" style="display:flex;gap:8px;flex-wrap:wrap;...">
  <select name="biz_div" style="padding:8px 12px;border:1px solid #D1D5DB;...">
```

`.filter-bar` 클래스 정의 (style.css line 618) 있으나 **사용 안 함**. 인라인으로 직접 스타일링 → 다른 페이지와 외형 불일치.

### A3. 적용된 필터 표시 chip 없음

필터 적용 후 어떤 조건인지 화면 상단에 보이지 않음. 사용자가 dropdown 다시 열어봐야 확인 가능.

**해결**: 필터 적용 후 상단에 chip 표시 (예: `[검사기 ✕] [고객사: 삼성 ✕] [상태: 진행중 ✕]`)

### A4. 고객사 검색 자동완성 없음

```html
<input type="text" name="customer" placeholder="고객사 검색" ...>
```

84명 시드의 고객사 목록 있음에도 자동완성 없음. P1 영업이 매일 사용 → 큰 불편.

### B1. 행 hover 효과만 있고 클릭 cue 약함

```html
<tr ... onclick="location.href='/progress/{{ p.id }}'" onmouseover="this.style.background='#FAFBFC'">
```

cursor:pointer 있으나 시각 cue 약함. "행 클릭 → 상세" 명시되어 있으나 처음 사용자는 모름.

### B2. 페이지 행수 표시 위치

```html
<p style="text-align:right;margin-top:8px;font-size:var(--text-xs);color:#6B7280;">총 {{ matrix|length }}건 · 셀 클릭 시 공정 상세</p>
```

표 아래 작은 글자 우측. 84건이면 페이지네이션 또는 "스크롤로 모두 보기" cue 필요.

---

## 3. 시안 v2 정합 검증 (이번에 실패한 이유)

| 시안 | sticky left col | 필터 라벨 | 필터 인라인 | 결함 |
|---|---|---|---|---|
| `14_progress_healing.html` | ❌ 없음 | (시안 없음) | 시안에선 검색바 형태 | **시안에 없는 기능** |
| `15~20` | (페이지별 다름) | — | — | 동일 |

**진단**: v2 작업 계약(`_TO_01_힐링_C안_시안통째이식_v2.md`) §4 12종 grep 검증 항목에 **sticky left column / 필터 라벨 / max-height 미포함**. 즉 v2 통째 이식 시:
- 빅터 시안 grep PASS → 통과
- 그러나 LIVE의 위 5개 결함은 **그대로 잔존**
- 30시간 후 또 대표 점검 사고 발생

**근본 원인**: 빅터가 v2 시안 정합 검증을 "외형 정합" (헤더·사이드바·도크 위치)에만 집중. **사용자 동선 검증은 누락**.

---

## 4. 페르소나별 영향도

| 페르소나 | 매일 본 페이지 (영향 받음) | 영향도 |
|---|---|---|
| **CEO 김정락** | progress_matrix, sales_outstanding, sales_aging | 🔴 매일 결함 노출 |
| **P1 영업** | sales_outstanding, sales_aging, progress_matrix | 🔴 핵심 동선 |
| **P3 기구설계 PM** | progress_matrix | 🔴 핵심 화면 |
| **P6 자재팀** | stock_safety, stock_reorder | 🔴 매일 사용 |
| **P10 베트남 외주** | progress_matrix (모바일 카드뷰 기본) | 🟡 카드뷰는 OK, 데스크톱 매트릭스만 결함 |

→ **CEO 포함 전 핵심 페르소나 영향**. 04 운영테스트팀 페르소나 보고에 잡히지 않은 이유 = 04도 매트릭스 가로 스크롤 시나리오를 시뮬레이션하지 않음. **04 시뮬레이션 매트릭스에도 누락 항목**.

---

## 5. 권장 수정 (S 등급 즉시 / A 등급 1차 마감 동시)

### 5-1. S1 — 필터 라벨 통일 (5분)
```diff
-  <button type="submit" ...>필터</button>
+  <button type="submit" ...>🔍 검색</button>
```
- 시스템 9개 페이지 표준 "검색" 채택
- (옵션) sage-gradient CTA 스타일 적용

### 5-2. S2+S3 — sticky left col + max-height (페이지당 15분)

```html
<!-- 변경 전 -->
<div style="...overflow-x:auto;">
<table style="width:100%;border-collapse:collapse;min-width:1400px;">

<!-- 변경 후 -->
<div class="mtx-scroll" style="max-height:calc(100vh - 320px);overflow:auto;border:1px solid #E5E7EB;border-radius:14px;">
<table class="mtx-table" style="width:100%;border-collapse:separate;border-spacing:0;min-width:1400px;">
```

```css
/* style.css — 신규 추가 */
.mtx-scroll { /* 컨테이너 — 가로·세로 모두 스크롤 자체에서 처리 */ }
.mtx-table thead th {
  position: sticky; top: 0; z-index: 3;
  background: var(--sage-100);
}
.mtx-table thead th.col-pin,
.mtx-table tbody td.col-pin {
  position: sticky; left: 0; z-index: 2;
  background: #fff;
  box-shadow: 2px 0 4px rgba(0,0,0,.05);
}
.mtx-table thead th.col-pin { z-index: 4; }   /* 좌상귀 */
.mtx-table thead th.col-pin-2,
.mtx-table tbody td.col-pin-2 {
  position: sticky; left: 140px; z-index: 2;   /* 첫 컬럼 width = 140 */
  background: #fff;
}
```

```html
<!-- 첫 2 컬럼에 col-pin 클래스 추가 -->
<th class="col-pin">관리코드</th>
<th class="col-pin-2">프로젝트</th>
<!-- ... -->
<td class="col-pin">{{ p.mgmt_code }}</td>
<td class="col-pin-2">{{ p.name }}</td>
```

→ 5페이지 동일 패턴 적용.

### 5-3. A1~A4 — 1차 마감(30h) 동시 처리

A1 컬럼 밀도: 시안 v2 동일 — 추후 별도 검토
A2 인라인 스타일: `.filter-bar` 클래스 사용으로 통일
A3 적용 chip: 추후 별도 검토 (1차 마감 후)
A4 자동완성: `<datalist>` 또는 `/api/customers/search` 추가 (1차 마감 동시)

---

## 6. 빅터 자기검증 실패 분석

### 6-1. 무엇을 놓쳤나 (3차 자기검증 실패)
1. v1 발행: 시안 자체 grep 누락 (대표 점검으로 발견)
2. v2 발행: LIVE 옛 코드 grep 누락 (대표 점검으로 발견 — 빅터·사이드바 화살표)
3. v2 발행 후 즉시: **사용자 동선 검증 누락** (대표 점검으로 발견 — 본건)

### 6-2. 왜 놓쳤나
"시안 = 정답" 가정에 매달려, **시안 자체가 페르소나 시뮬레이션 거치지 않은 상태**임을 놓침. 시안은 원래 디자이너의 상상력 기반 — 실사용자 검증 없음. v2 검증을 "시안 = LIVE" 일치성에만 집중 → "시안 + LIVE 둘 다 같은 결함" 패턴을 놓침.

### 6-3. 대표 비판 정확
> *"빅터 너가 직접 테스트하는 조건으로만 만든게 아닌가 싶네"*

✅ 맞음. 빅터 자체 페르소나 시뮬레이션 안 함. 04 운영테스트팀 의뢰도 v1 발행 시점에만 했고, v2 발행 직후 재의뢰 안 함.

### 6-4. 자기 개선 (4차 약속)
- ✅ 모든 작업 계약 발행 시 §4 grep 외에 **§4-2 페르소나 walkthrough 체크리스트 의무화**
- ✅ 매트릭스류 페이지는 sticky-pin / max-height / scroll-position 표준 패턴 명시
- ✅ 시안 변경 시 "시안 ↔ LIVE ↔ 페르소나" 3중 검증 확보

---

## 7. 참조 문서

- `_TO_01_힐링_C안_시안통째이식_v2.md` (작업 계약 v2)
- `_TO_01_긴급핫패치_빅터덮음_사이드바화살표.md` (이번 세션 17:30 핫패치)
- `_FROM_04_힐링QA결과_01.md` (04 1차 검증 결과 — 본 결함 미발견)
- 본 진단서

---

**작성**: 2026-04-25 17:50 · 05 디자인팀 세션 빅터
**상태**: 🔴 **S1 결함 5페이지 + A 등급 4건 진단 완료 · 부서 지시 문서 발행 단계**
**다음**: _TO_01 / _TO_04 / _TO_09 3건 발행
