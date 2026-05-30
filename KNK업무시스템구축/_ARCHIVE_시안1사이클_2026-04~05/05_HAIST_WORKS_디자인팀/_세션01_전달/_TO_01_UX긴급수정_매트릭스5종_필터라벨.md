# [05 → 01] 🔴 UX 긴급 수정 — 매트릭스 5페이지 sticky 좌측·max-height + 필터 라벨 통일

> **발신**: 05 디자인팀 세션 빅터
> **수신**: 01 메인 세션
> **참조**: 09 프로젝트 팀장 / 04 운영테스트팀
> **일자**: 2026-04-25 17:55
> **선행**: `_DIAG_UX결함_매트릭스다중페이지_진행률포함.md` (진단 보고서 — 반드시 함께 읽기)
> **트리거**: 대표 직접 점검 — *"실제 사람이 사용하는건데..."*
> **지위**: 🔴 **C안 v2 작업 계약에 추가 — 1차 마감(+30h) 안에 본건 동시 처리 필수**

---

## 0. 한 줄

진행률 매트릭스 결함 점검 중 **5페이지 동일 결함** 발견 (sticky left col 0건 / max-height 0건). v2 통째 이식해도 결함 잔존 → v2 §2 작업 범위에 본 5건 표준 패턴 추가 + 필터 라벨 통일 1건.

---

## 1. 영향 페이지 5종

| 페이지 | 영향 페르소나 | 우선순위 |
|---|---|---|
| `progress_matrix.html` | CEO + P1 영업 + P3 PM | **🔴 1순위** |
| `sales_outstanding.html` | CEO + P1 영업 | 🔴 |
| `sales_aging.html` | CEO + P1 영업 | 🔴 |
| `stock_safety.html` | P6 자재팀 매일 | 🔴 |
| `stock_reorder.html` | P6 자재팀 | 🔴 |

---

## 2. 표준 패턴 — 매트릭스 컨테이너

### 2-1. HTML 변경 (5페이지 모두 동일 패턴 적용)

```html
<!-- 변경 전 (현재 LIVE) -->
<div style="...overflow-x:auto;">
  <table style="width:100%;border-collapse:collapse;min-width:1400px;">
    <thead style="...position:sticky;top:0;">
      <tr>
        <th style="...">관리코드</th>
        <th style="...">프로젝트</th>
        ...
```

```html
<!-- 변경 후 (표준 패턴) -->
<div class="mtx-scroll">
  <table class="mtx-table" style="min-width:1400px;">
    <thead>
      <tr>
        <th class="col-pin col-pin-1">관리코드</th>
        <th class="col-pin col-pin-2">프로젝트</th>
        <th>전체</th>
        ...
        <th>납기</th>
      </tr>
    </thead>
    <tbody>
      {% for p in matrix %}
      <tr>
        <td class="col-pin col-pin-1">{{ p.mgmt_code }}</td>
        <td class="col-pin col-pin-2">{{ p.name }}</td>
        ...
```

### 2-2. CSS 신규 (style.css 끝에 추가)

```css
/* ============================================================
   매트릭스 표준 패턴 (UX-2026-04-25 · 대표 직접 점검 결과)
   - 가로·세로 모두 컨테이너 자체에서 스크롤
   - thead 상단 고정 / 좌측 1~2 컬럼 좌측 고정
   - 5페이지 공통: progress_matrix · sales_outstanding · sales_aging · stock_safety · stock_reorder
   ============================================================ */

.mtx-scroll {
  max-height: calc(100vh - 320px);
  overflow: auto;
  border: 1px solid var(--sage-200, #E5E7EB);
  border-radius: 14px;
  background: #fff;
  position: relative;
}

.mtx-table {
  width: 100%;
  border-collapse: separate;     /* sticky left에 필수 */
  border-spacing: 0;
}

.mtx-table thead th {
  position: sticky;
  top: 0;
  z-index: 3;
  background: var(--sage-100, #F9FAFB);
  border-bottom: 1px solid var(--sage-200, #E5E7EB);
  padding: 10px;
  text-align: left;
  font-size: var(--fs-fluid-xs, 11px);
  color: var(--ink-3, #6B7280);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.mtx-table tbody td {
  padding: 10px;
  border-bottom: 1px solid #F1F2F4;
  background: #fff;
  font-size: var(--fs-fluid-sm, 13px);
}

/* 좌측 핀 — 1번째 컬럼 */
.mtx-table .col-pin-1 {
  position: sticky;
  left: 0;
  z-index: 2;
  box-shadow: inset -1px 0 0 var(--sage-200, #E5E7EB);
  min-width: 140px;
}
.mtx-table thead th.col-pin-1 { z-index: 4; }   /* 좌상귀 */

/* 좌측 핀 — 2번째 컬럼 */
.mtx-table .col-pin-2 {
  position: sticky;
  left: 140px;       /* 1번째 컬럼 min-width와 일치 */
  z-index: 2;
  box-shadow: inset -1px 0 0 var(--sage-200, #E5E7EB);
  min-width: 200px;
}
.mtx-table thead th.col-pin-2 { z-index: 4; }   /* 좌상귀 */

/* 행 hover — sticky 컬럼도 동일 색 */
.mtx-table tbody tr:hover td { background: #FAFBFC; }

/* 모바일 — sticky 해제, 카드뷰 권장 */
@media (max-width: 768px) {
  .mtx-scroll { max-height: none; }
  .mtx-table .col-pin-1,
  .mtx-table .col-pin-2 { position: static; }
}
```

### 2-3. 페이지별 핀 컬럼 매핑

| 페이지 | 1번 핀 | 2번 핀 |
|---|---|---|
| `progress_matrix.html` | 관리코드 | 프로젝트 |
| `sales_outstanding.html` | 관리코드 (또는 거래처) | 프로젝트 |
| `sales_aging.html` | 거래처 | 관리코드/프로젝트 |
| `stock_safety.html` | 부품번호 | 부품명 |
| `stock_reorder.html` | 부품번호 | 부품명 |

→ 페이지별로 1번·2번 핀 결정. 의문 시 빅터(05)에 즉시 질의.

---

## 3. 필터 라벨 통일

### 3-1. progress_matrix.html line 88

```diff
-  <button type="submit" style="padding:8px 18px;background:#fff;border:1px solid #D1D5DB;border-radius:8px;font-weight:600;cursor:pointer;">필터</button>
+  <button type="submit" style="padding:8px 18px;background:#fff;border:1px solid #D1D5DB;border-radius:8px;font-weight:600;cursor:pointer;">🔍 검색</button>
```

→ 시스템 9개 페이지 표준 "검색"으로 통일.

### 3-2. (선택) admin_permissions_audit.html / admin_permissions_matrix.html
이미 "필터 적용" / "조회" 사용 — 관리자 전용 페이지이므로 우선순위 낮음. 1차 마감에 포함하지 않아도 됨. (B 등급)

---

## 4. v2 §4 grep 검증 항목 확장 (기존 12종 → 15종 → 추가 4종)

본 패치가 LIVE에 들어왔는지 확인하기 위한 grep 추가:

```bash
# 정합 (PASS = ≥1 — 5개 페이지 모두)
grep -c 'class="mtx-scroll"' app/templates/progress_matrix.html
grep -c 'class="mtx-scroll"' app/templates/sales_outstanding.html
grep -c 'class="mtx-scroll"' app/templates/sales_aging.html
grep -c 'class="mtx-scroll"' app/templates/stock_safety.html
grep -c 'class="mtx-scroll"' app/templates/stock_reorder.html

# 정합 (PASS = ≥1 — style.css)
grep -c 'class\.col-pin-1' static/style.css
grep -c 'mtx-table thead th' static/style.css

# 결함 (PASS = 0 — 옛 패턴 전멸)
grep -nE 'min-width:\s*1[0-9]{3}px' app/templates/progress_matrix.html  # 컨테이너로 옮겨짐 (테이블 min-width는 OK, 인라인이면 0건)
grep -c '>필터</button>' app/templates/progress_matrix.html              # 기대 0
```

→ 1차 응답에 본 4종 grep 결과 첨부. v2 §4 12종 + 핫패치 §6 3종 + 본건 7종 = **22종 grep PASS** 의무.

---

## 5. 페르소나 walkthrough 체크리스트 (응답 시 첨부)

응답에 다음 시나리오 PASS/FAIL 기록:

| # | 시나리오 | PASS 조건 | 페르소나 |
|---|---|---|---|
| 1 | 매트릭스 우측 끝까지 가로 스크롤 | 좌측 2 컬럼(관리코드·프로젝트) 화면에 보임 | P3 PM |
| 2 | 매트릭스 아래쪽 50번째 행까지 세로 스크롤 | thead(컬럼명) 화면 상단에 보임 | P3 PM |
| 3 | 매트릭스 가로+세로 동시 스크롤 | 좌상귀(관리코드 헤더) 항상 보임 | CEO |
| 4 | 사업부 dropdown → "검사기" 선택 → 검색 버튼 클릭 | 검사기 프로젝트만 표시, "필터"가 아닌 "검색" 라벨 | P1 영업 |
| 5 | 모바일 (768px 이하) 매트릭스 열기 | sticky 해제, 정상 스크롤 가능 | P10 베트남 |
| 6 | sales_outstanding 84개 행 | sticky 패턴 동일 | P1 영업 |
| 7 | stock_safety 부품 검색 | sticky 패턴 동일 | P6 자재 |

→ 7/7 PASS 후 응답.

---

## 6. v2 본건 vs 본 추가 작업 — 통합 일정

| 단계 | 시점 | 산출물 |
|---|---|---|
| 현재 (17:55) | — | 본 지시서 발행 |
| **+30h (1차 마감)** | 2026-04-26 23:00 | **base.html + style.css + 5페이지 매트릭스 패턴 + 필터 라벨** |
| **+54h (2차 마감)** | 2026-04-27 23:00 | 페이지 9종 (login/home/progress/dashboard/changes/tickets/issues/daily/admin) — 시안 기반 |

→ 1차 마감 시점에 매트릭스 패턴 5건 모두 들어가야 함. 별건 의뢰 아니라 **v2 §2 작업 범위 확장**으로 처리.

---

## 7. 빅터 사과 + 약속

v2 발행 시 시안·LIVE grep만 했고 **사용자 동선 walkthrough 누락**. 그 결과 매트릭스 가로 스크롤 사용자 시나리오 검증이 빠졌음. 본 §5의 페르소나 walkthrough를 향후 모든 작업 계약에 의무화.

**의문 사항 즉시 빅터(05)에 질의** — 즉각 응답.

---

## 8. 회신 양식 (1차 응답에 추가)

```markdown
## §추가-A. 매트릭스 5페이지 표준 패턴 적용
| 페이지 | mtx-scroll | col-pin-1 | col-pin-2 | max-height | PASS |
|---|---|---|---|---|---|
| progress_matrix | ✅ | 관리코드 | 프로젝트 | calc(100vh-320px) | ✅ |
| sales_outstanding | ✅ | ... | ... | ... | ✅ |
| ... | | | | | |

## §추가-B. 필터 라벨 통일
| 페이지 | 변경 전 | 변경 후 | PASS |
|---|---|---|---|
| progress_matrix | 필터 | 🔍 검색 | ✅ |

## §추가-C. 페르소나 walkthrough (7종)
| # | 시나리오 | 결과 | 페르소나 |
|---|---|---|---|
| 1 | 우측 끝 스크롤 — 좌측 2컬럼 보임 | ✅ | P3 |
| ... | | | |
```

---

**발행**: 2026-04-25 17:55 · 05 디자인팀 세션 빅터
**상태**: 🔴 **v2 §2 작업 범위 확장 · 1차 마감(+30h) 안에 본건 동시 처리 필수**
**회신 위치**: `_FROM_01_힐링_C안_시안이식응답_v2_1차.md` 에 §추가-A/B/C 포함
