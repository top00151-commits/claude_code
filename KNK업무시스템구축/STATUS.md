# 📊 HAIST WORKS — 통합 상태 보드 (LIVE)

> **목적:** 대표님이 1초 만에 전 팀 진행 상황 파악 (통합 단위 보드)
> **갱신:** 빅터(01) 만 수정 — **대표 명시 지시 시점에만**
> **마지막 갱신:** 2026-05-10 v5H226z71 (**2차 통합 사이클 완료** — 65p 일괄 통합)

## 🚦 빅터 통합 호출 방법 (대표님)

| 명령 | 작동 |
|---|---|
| **"빅터, 전체 연결성 검증"** | 3팀 산출물 일괄 통합 |
| **"빅터, 팀N 통합"** | 단일 팀만 통합 (빠름) |
| **"빅터, 표준 위반 검사"** | 코드 검수만 (변경 없음) |
| **"빅터, BAT/STATUS 갱신"** | 보고 자료만 갱신 |
| **"빅터, 롤백 태그"** | 현 시점 보존 (rollback-YYYYMMDD-HHMM) |

---

## 🟢 통합 완료 (메인 코드 반영)

### 2차 통합 사이클 — z71 (2026-05-10)

| 팀 | 페이지 수 | 핵심 |
|---|---|---|
| **01A 통합플랫폼** | **22 / 22 (100%)** | home·daily·weekly·notifications·calendar·tickets·changes·issues·board·search·profile·now·team·cockpit + Quiet Tone v3 토큰 + data-dn 93개 |
| **01B 매출영업** | **27 / 30+ (~90%)** | project_detail·sales_orders·sales_home·customer_detail·sales_quote·projects·customers_list·sales_shipments·sales_outstanding·sales_aging·sales_dashboard·sales_forecast·sales_production·export 6개·fta 2개 + .mgmt-pill 15곳 + 1100px 반응형 |
| **01C 자재구매** | **16 / 30+ (~50%)** | po_list·logistics_home·parts·suppliers·stock 6개·po_detail·po_form·po_receive·wo_list·qc_report_list + 표준 v1 + 자체 BAT |
| **합계** | **65 페이지** | 시안1 Quiet Tone v3 적용 + data-dn 라벨 + 1100px 반응형 |

### 1차 통합 사이클 — z54~z57 (보존)

| 시점 | 팀 | 페이지 | 비고 |
|---|---|---|---|
| z54 | 01C | po_list.html | 시안1 ERP 시초 |
| z57 | 01C | _STANDARD_자재모듈기준_v1.md | 자체 표준 — 결재 통과 |

---

## 🟡 검수 대기 / 보류

| 항목 | 팀 | 산출물 | 다음 처리 |
|---|---|---|---|
| 마이그레이션 SQL | 01C | `migrations/v5H226z56_자재모듈표준v1.sql` | 대표 결재 → 빅터 적용 |
| 부록 B specs | 01A | daily/calendar 시간대·좌우분할 | 백엔드 협의 필요 |
| input focus 빨강 | 01A | 22 페이지 일괄 정리 | v3+ 차수 검토 |

---

## 🔵 진행 중 / 다음 차수

| 팀 | 다음 | 상태 |
|---|---|---|
| 01A 통합플랫폼 | v3 차수 (부록 B specs / 컴포넌트 표준화) | 대표 지시 대기 |
| 01B 매출영업 | 잔여 3p (수출입·견적 마무리) + 컴포넌트 등록 | 자율 진행 가능 |
| 01C 자재구매 | part_detail / wo_form / 출고·실사·품질·환율 | 빅터 검수 회신 시 시작 |

---

## 🔴 재작업 지시 (빅터 → 팀)

| 시점 | 팀 | 페이지 | 사유 |
|---|---|---|---|
| (없음) | | | |

---

## 🚨 충돌 발생

| 시점 | 팀 A | 팀 B | 페이지 | 빅터 결정 |
|---|---|---|---|---|
| (없음) | | | | |

---

## 📌 빅터 작업 메모

### z71 (2026-05-10) — **2차 통합 사이클**
- **롤백 태그**: `rollback-20260510-pre-integration-z71` 생성 (사이클 직전 보존)
- **검수 결과**:
  - 변경 템플릿: 65 페이지 (Modified)
  - 잔존 v5 컬러 토큰: spot-check 0건 (sales_orders.html 인라인 1건만, v3 호환)
  - data-dn 라벨: spot-check OK (home 10·sales_orders 20·po_list 5·project_detail 6·logistics_home 12)
  - 메인 BAT 수정: 빅터(01) 본인만 (z71 갱신)
  - main.py 변경: 빅터 z48 design_samples 라우트 1건 (룰 위반 X)
  - DB / 라우트 / 외부 자산 변경: 0건
- **세 팀 모두 옵션 A 자동 충족** (메인 직접 작업 환경)
- BAT z59 → z71 / debug_overlay z27 → z71

### z59 (2026-05-10 ADDENDUM v4)
- 4충돌 정정: BAT 권한 / v5H226z 라벨 / 워크트리 동기화 / (e) 단계 분할
- 01B v1 차수 인정

### z57 (1차 통합 사이클)
- 01A INQUIRY 답변 / 01B 착수 안내 / 01C po_list 통합 + 표준 v1 결재

---

## 🎯 우선순위 페이지 (전체 진행률)

### 01A 통합플랫폼 (22 페이지) — **22 / 22 = 100% 🟢**
- [x] home / daily / weekly / now / team / cockpit
- [x] notifications / calendar / search
- [x] tickets_list / ticket_detail / ticket_form
- [x] changes_list / change_detail / change_form
- [x] issues_list / issue_detail / issue_form
- [x] board_list / board_detail / board_form / board_teams
- [x] profile

### 01B 매출영업 (30+ 페이지) — **27 / 30+ ≈ 90% 🟢**
- [x] project_detail / projects / project_form
- [x] sales_orders / sales_home / sales_order_detail
- [x] customer_detail / customer_form / customers_list
- [x] sales_quotations / sales_quote_detail / sales_quote_form
- [x] sales_shipments_receipts / sales_outstanding / sales_aging
- [x] sales_dashboard / sales_forecast / sales_production
- [x] export_home / export_order_detail / export_order_form
- [x] export_ci / export_pl / export_bl_customs
- [x] fta_list / fta_form
- [ ] 잔여 3p (소모품 등)

### 01C 자재구매 (30+ 페이지) — **16 / 30+ ≈ 50% 🟡**
- [x] po_list / po_detail / po_form / po_receive
- [x] logistics_home
- [x] parts / suppliers
- [x] stock_balances / stock_movements / stock_safety / stock_reorder / stock_abc / stock_receipts / stock_turnover
- [x] wo_list / qc_report_list
- [ ] part_detail / part_form / part_prices / supplier_form
- [ ] wo_form / wo_detail / qc_form / qc_detail / qms 4개 / rates 5개

### 빅터(01) 책임 — 공통/통합/관리자
- [x] chrome.html (Quiet Tone v3) / styles.html / design_quiet_v3.html
- [x] debug_overlay.html (z71)
- [x] STATUS.md 운영 체계
- [x] 발주서 v2 + ADDENDUM v3 / v4
- [x] 1차·2차 통합 사이클 완료
- [ ] admin*.html (관리자/권한)
- [ ] login.html / error.html

---

## 📈 누적 통계

| 지표 | 현재 |
|---|---|
| 총 페이지 | 130+ |
| **시안1 적용 완료** | **65** |
| 미적용 | ~65 |
| **전체 진행률** | **~50%** |
| 1차 통합 사이클 | ✅ z57 |
| 2차 통합 사이클 | ✅ **z71** |

---

## 🔔 대표 결재 / 통보 사항

### 대기 중
1. **마이그레이션 SQL 적용 결재** (01C)
   - 위치: `01C_HAIST_WORKS_자재구매/migrations/v5H226z56_자재모듈표준v1.sql`
   - 빅터 적용 필요 시 결재 라인

2. **자재 라우트 확장 결재** (01C 권고, 미해결)
   - 사양: `database.py:po_list()` SELECT 확장 (사업부·품명·L/T 추가)

3. **다음 차수 승인 발주**
   - 01A v3 차수 (부록 B specs / 컴포넌트 표준화)
   - 01B 잔여 3p + 컴포넌트 등록
   - 01C part_detail / wo_form / 출고·실사·품질·환율

---

**관련 문서:**
- `_ORDERS/` — 발주서
- `_STANDARDS/` — 전 팀 표준
- `01[A/B/C]/PROGRESS.md` — 각 팀 진행 추적
- `01[A/B/C]/output/HANDOFF_*` — 빅터 통합 입력
- `01[A/B/C]/output/REPLY_FROM_01_*` — 빅터 응답
