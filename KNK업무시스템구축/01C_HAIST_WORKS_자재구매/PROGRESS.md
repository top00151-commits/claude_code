# 📊 작업 진행 추적

> 매 페이지 작업 시작·완료 시 이 파일 갱신.

## 작업 상태 표기
- 🔘 미착수 / 🟡 진행중 / 🟢 완료 / 🔴 차단

## 진행 현황

| 그룹 | 페이지 | 파일 | 상태 | 완료일 | 비고 |
|---|---|---|---|---|---|
| **STD** | **자재모듈 기준서 v1** | `_STANDARD_자재모듈기준_v1.md` | 🟢 | 2026-05-10 | 참고 SaaS ERP A 흡수 + 익명화 + 결재 5건 통과 |
| **MIG** | **마이그레이션 SQL** | `migrations/v5H226z56_자재모듈표준v1.sql` | 🟡 | 2026-05-10 | 작성 완료 / 적용은 빅터01·대표 라인 |
| **MIG** | **자재모듈 표준 v2 (VAT+품목)** | `migrations/v5H226z58_VAT_품목강화_v2.sql` | 🟡 | 2026-05-11 | z58 — VAT 모드 + 공급가액/부가세 + 불량갯수 + 환산계수 + 재고잠금일자 / 적용 위임 |
| **TOOL** | **자체 도구 BAT** | `01C_도구.bat` | 🟢 | 2026-05-11 | 메뉴 12종 (서버·INBOX·migrations·DB백업·git status) |
| **A 자재 홈** | **자재구매 홈 ⭐** | `logistics_home.html` | 🟢 | 2026-05-10 | z56+z57 — Quiet Ops + KPI 6 + 발주흐름 + 사업부 + data-dn 11개 |
| **B 발주** | **발주 목록 ⭐** | `po_list.html` | 🟢 | 2026-05-10 | z54+z57 — chip-po + tbl-dense + filterbar |
| **B 발주** | **발주 상세** | `po_detail.html` | 🟢 | 2026-05-11 | z57→**z58** — VAT 모드·과세구분·공급가액·부가세 4줄 추가 |
| **B 발주** | **발주 작성·수정** | `po_form.html` | 🟢 | 2026-05-11 | z57→**z58** — VAT 모드 + 과세구분 select + 합계 분리 (3종 동적 계산 JS) |
| **B 발주** | **입고 처리** | `po_receive.html` | 🟢 | 2026-05-11 | z57→**z58** — VAT 모드 + 공급가액/부가세 표시 추가 |
| **C 부품** | **부품 목록** | `parts.html` | 🟢 | 2026-05-11 | z57→**z58** — chip-acc 컬럼 추가 (품목계정 5종 시각화) |
| **C 부품** | **부품 상세** | `part_detail.html` | 🟢 | 2026-05-11 | **z58** — KPI 5 + FIFO 레이어 + 단가 이력 + 적용일자 단가 + BOM/7단가 placeholder + 입출고 + 프로젝트 사용 + 첨부 갤러리 + 단가 등록 폼 + 사이드(마스터 + 공급사 요약 + 빠른 액션) |
| **C 부품** | **부품 등록·수정** | `part_form.html` | 🟢 | 2026-05-11 | **z58** — 7섹션 폼 + 13 신규 필드 + 사이드 요약·가이드·삭제 |
| **C 부품** | **단가 이력·등록** | `part_prices.html` | 🟢 | 2026-05-11 | **z58** — KPI 3 + 신규 등록 폼 9필드 + 이력 표 (활성 색상) / Form name 정정 (applied_date→effective_from 422 방지) |
| **D 공급사** | **공급사 목록** | `suppliers.html` | 🟢 | 2026-05-11 | z57 — 카드 그리드 + KPI 4 + 검색 |
| **D 공급사** | **공급사 등록·수정** | `supplier_form.html` | 🟢 | 2026-05-11 | **z58** — 4 섹션 폼 + 사이드 (요약 / 리드타임 통계 / 가이드 / 삭제) — 단일 페이지 신규·수정 통합 |
| **E 재고** | **재고 현황 ⭐** | `stock_balances.html` | 🟢 | 2026-05-11 | z57 — KPI 5 + dense 표 + tfoot 합계 |
| **E 재고** | **재고 이동** | `stock_movements.html` | 🟢 | 2026-05-11 | z57 — chip-mv 4종 + 기간·유형 필터 |
| **E 재고** | **ABC 분석** | `stock_abc.html` | 🟢 | 2026-05-11 | z57 — chip-abc + 누적 비중 막대 |
| **E 재고** | **FIFO 레이어** | `stock_fifo.html` | 🟢 | 2026-05-11 | **z58** — KPI 3 (활성레이어/총잔량/총가치) + 잔량/입고량 비율 막대 + PO·LOT 참조 |
| **E 재고** | **안전재고** | `stock_safety.html` | 🟢 | 2026-05-11 | z57 — KPI 4 + 행 인라인 입력 (safety/ROP/ROQ) |
| **E 재고** | **회전율** | `stock_turnover.html` | 🟢 | 2026-05-11 | z57 — chip-band FAST/NORMAL/SLOW |
| **E 재고** | **재주문** | `stock_reorder.html` | 🟢 | 2026-05-11 | z57 — chip-pri HIGH/MID/LOW + 발주 액션 |
| **E 재고** | **QC 분리 / 부적합** | `stock_qc.html` | 🟢 | 2026-05-11 | **z58** — 입고 QC 양 모드 (PASS/PARTIAL/HOLD/FAIL) + 부적합 처리 (RETURN/SPECIAL_ACCEPT/SCRAP) |
| **E 재고** | **출고 등록 폼** | `stock_issue.html` | 🟢 | 2026-05-11 | **z58** — 자재 select + 출고 후 재고 미리보기 + 안전재고 색상 + FIFO 자동 차감 + JS 동적 |
| **E 재고** | **출고 이력** | `stock_issues.html` | 🟢 | 2026-05-11 | **z58** — KPI 4 + chip-iss 3상태(PENDING/ISSUED/CANCELLED) + ?success/error 배너 + stock_receipts 대칭 |
| **E 재고** | **입고 이력** | `stock_receipts.html` | 🟢 | 2026-05-11 | z57 — chip-rs 5상태 |
| **E 재고** | **재고 조정** | `stock_adjust.html` | 🟢 | 2026-05-11 | **z58** — 부호 토글(+/-) + 자재 정보 자동 + 조정 후 재고 미리보기(음수 차단) + 사유 11종 grouped + JS 동적 |
| **E 재고** | **재고 조정 이력 (실사 보정)** | `stock_adjustment.html` | 🟢 | 2026-05-11 | **z58** — 목록+첨부 양 모드 / 승인·반려 액션 / 잠재 버그 9건 복구 (PROGRESS 표기 오류: "미사용" → 실제 라우터 2곳 사용) |
| **E 재고** | **실사 목록·상세** | `stock_audits.html`, `stock_audit.html` | 🟢 | 2026-05-11 | **z58** — 목록 KPI 3 + chip-au OPEN/CLOSED / 상세 라인 추가 + 마감 액션 + 차이 자동 보정 안내 |
| **F 작업지시** | **WO 목록** | `wo_list.html` | 🟢 | 2026-05-11 | z57 — chip-wo 5상태 + KPI 6 |
| **F 작업지시** | **WO 작성·상세** | `wo_form.html` | 🟢 | 2026-05-11 | **z58** — 신규 폼 + 상세 통합 / KPI 4 + 정보 + 공정 라인 + 표준공정 자동·발행 액션 |
| **F 작업지시** | **WO 인쇄** | `wo_print.html` | 🟢 | 2026-05-11 | **z58** — 시안1 모노 A4 인쇄 친화 + KNK 회사정보 + 도장란 4종 + chip 5상태 + 자동인쇄(?auto=1) |
| **G 품질** | **검사성적서 목록** | `qc_report_list.html` | 🟢 | 2026-05-11 | z57 — chip-q PASS/COND/FAIL + KPI 4 |
| **G 품질** | **검사 성적서 작성·상세** | `qc_report_form.html` | 🟢 | 2026-05-11 | **z58** — 신규 폼 + 상세 통합 / 표준 6항목 자동 / chip-q PASS·COND·FAIL / 발급 액션 (DRAFT→ISSUED) |
| **G 품질** | **검사 성적서 인쇄** | `qc_report_print.html` | 🟢 | 2026-05-11 | **z58** — 시안1 모노 A4 + 종합판정 강조 박스(색상) + KPI 4 + 도장란 3종 + 자동인쇄 + 외부자산 0건 |
| **G 품질** | **QMS 대시보드** | `qms_dashboard.html` | 🟢 | 2026-05-11 | **z58** — KPI 6 (total/open/critical/breached/recurrence/ca_open) + 미해결 이슈 표 + chip-sev/chip-sla |
| **G 품질** | **QMS Pareto** | `qms_pareto.html` | 🟢 | 2026-05-11 | **z58** — KPI 4 + 빈도+막대+누적비중 + 80% 영역 강조 |
| **G 품질** | **QMS 재발 분석** | `qms_recurrence.html` | 🟢 | 2026-05-11 | **z58** — RID/RC 양그룹 + chip-cnt + 잠재 버그 5개 키 복구 (gid/cnt/first_at/last_at) |
| **G 품질** | **QMS CAPA** | `qms_capa.html` | 🟢 | 2026-05-11 | **z58** — KPI 4 (avg_closure/verify_rate/completed/verified) + CA/PA 라이프사이클 5단계 + 부서별 분포 + 잠재 버그 복구 |
| **H 환율·원가** | **FX 환율 관리** | `fx_rates.html` | 🟢 | 2026-05-11 | **z58** — 통화별 KPI + 등록 폼 5필드 + 통화 필터 + 이력 표 |
| **H 환율·원가** | **환율 대시보드** | `rates_dashboard.html` | 🟢 | 2026-05-11 | **z58** — 통화별 KPI + 알림 카드 + 30일 추이 표 + 스파크 |
| **H 환율·원가** | **단가 변경 이력** | `rates_history.html` | 🟢 | 2026-05-11 | **z58** — KPI 4 (상승/하락 분리) + 변동률 색상 + 잠재 버그 5개 키 복구 |
| **H 환율·원가** | **환율 알림** | `rates_alerts.html` | 🟢 | 2026-05-11 | **z58** — KPI 4 + 카드 그리드 + 발동/활성/비활성 상태 + 잠재 버그 4건 복구 (Form name 2 + 키 2) |
| **H 환율·원가** | **원가 시뮬** | `rates_cost_sim.html` | 🟢 | 2026-05-11 | **z58** — KPI 4 + 시뮬 폼 + 라이브 미리보기 JS + 공식 가이드 사이드 + 잠재 버그 10건 복구 (path+Form 5+키 5) |

**진행 요약:** **46 페이지 + 도구 BAT + 기준서 + 마이그레이션 SQL 2종** / 30+ 페이지 중 46 완료 (153% — **자재구매센터 전 그룹 풀체인 ✅ + 사내 환율·재고조정·QMS 이슈·FTA 보강**).

**추가 그룹 (30~35차, 2026-05-11 추가):**
- 사내 환율 메인 (`rates.html`) — fx_rates 관리자 페이지와 사내 사용자 페이지 분리 완성
- 재고 조정 (`stock_adjustment.html`) — PROGRESS 표기 오류 발견·정정 + 양 모드 통합
- QMS 이슈 (`issue_detail.html` + `issue_form.html`) — G 품질 그룹 진입점 보강
- FTA 원산지 (`fta_list.html` + `fta_print.html`) — 수출 모듈 (active="export") 시안1 통일

**완성 그룹 (A~H 8개 그룹 / 전 풀체인):**
- A 자재 홈 (1) · B 발주 (4) · C 부품 (4) · D 공급사 (2) · E 재고 (14) · F 작업지시 (3) · G 품질 (7) · H 환율·원가 (5) = **40 페이지**

**검증 1패스 누적 복구 잠재 버그 (코드 안전성 강화):**
- 17차 stock_audits/audit · 18차 stock_fifo · 19차 stock_qc — 라우터 form name 정합
- 22차 qms_recurrence — 키 5개 복구 (rid/title/root_cause/issue_ids/last_occurred → gid/cnt/first_at/last_at)
- 23차 qms_capa — 키 6개 복구 (kind/title/detail/status/owner_name/deadline → lifecycle_status/action/due_date)
- 24차 part_prices — Form name 1건 복구 (applied_date → effective_from, 422 방지)
- 27차 rates_history — 키 5개 복구 (applied_date/currency/unit_price_krw/rate/source → effective_date/supplier_name/old_price/new_price/change_pct)
- 28차 rates_alerts — Form 2 + 키 2 + 미구현 라우터 1건 복구
- 29차 rates_cost_sim — action path + Form 5 + 키 5 = **10건 복구**
백엔드 확장: database.py parts_create/update + po_create/update + main.py 라우터 4개 (13+2 신규 Form 필드 / VAT 계산 헬퍼 2개).

## 7시간 자율 작업 누적 (2026-05-10 ~ 11)

### 1차 (5/10) — 기반 구축
1. po_list.html (z54 → 빅터 통합 통과)
2. _STANDARD_자재모듈기준_v1.md (대표 결재 5건 통과)
3. logistics_home.html (z56)
4. v4 룰 정렬 — po_list/logistics_home 양쪽 (z57)
5. migrations/v5H226z56_자재모듈표준v1.sql (작성, 적용 위임)

### 2차 (5/10~11) — 7시간 자율 작업
6. 01C_도구.bat (자체 점검 도구, 룰 v4 §1 자율)
7. parts.html (z57)
8. suppliers.html (z57)
9. stock_balances.html (z57)
10. stock_movements.html (z57)
11. stock_safety.html (z57)
12. stock_reorder.html (z57)
13. po_detail.html (z57)
14. wo_list.html (z57)
15. qc_report_list.html (z57)
16. stock_abc.html (z57)
17. stock_receipts.html (z57)
18. stock_turnover.html (z57)

### 3차 (5/11) — 발주 풀체인 완성
19. po_form.html (z57) — 4-step + 폼 카드 + 라인 자동매핑 (datalist + active-price fetch)
20. po_receive.html (z57) — KPI 4 + LOT/유효기한/비고 라인 + **라우터 form name 정렬** (po_item_id/receive_qty/item_note/lot_no/expiry_date getlist 호환)

### 4차 (5/11) — 매뉴얼 분석 + IP 안전 자재모듈 표준 v2
21. ERP_물류관리매뉴얼.pdf 분석 보고서 (Ch1/3/8 추출, _분석보고서_자재물류.md)

### 5차 (5/11) — z58 마이그레이션 SQL
22. v5H226z58_VAT_품목강화_v2.sql — 자재모듈 표준 v2 (VAT 모드 / 공급가액·부가세 / 불량갯수 / 환산계수 / 재고잠금일자)
    - **검증 1패스 결함**: reorder_point/reorder_qty 가 database.py 자동 마이그레이션과 중복 → 즉시 제거

### 6차 (5/11) — parts 마스터 + part_form 신규
23. part_form.html (z58) — 7섹션 폼: 기본정보 / 분류(품목계정 5종+조달구분) / 단가 / 재고관리(ROP/ROQ/환산계수) / 추가규격 / 문서출력명 / 기타 + 사이드 요약·가이드·삭제
24. parts.html (z57→z58) — 표 컬럼 "품목계정" 추가 + chip-acc 5색 (RAW/SUB/SEMI/FIN/CONS)
25. database.py parts_create/parts_update — PRAGMA gate 동적 컬럼 확장 (z58 SQL 미적용 환경 호환)
26. main.py POST /parts/new + POST /parts/{pid}/edit — Form 파라미터 13 신규 (item_account/procurement_kind/category_main/series/reorder_point/qty/conversion_factor/sub_spec1-3/tax_invoice_name/trade_invoice_name/default_warehouse/hs_code)

### 7차 (5/11) — VAT 모드 발주 풀체인
27. po_form.html (z57→z58) — VAT 모드 select(3종) + 과세구분 select(4종) + 합계 라벨 동적 + JS recalcTotals (vat_excluded/included/none 분기)
28. po_detail.html (z57→z58) — VAT 모드 + 과세구분 + 공급가액 + 부가세 4줄 def 추가 (z58 미적용 fallback 안전)
29. po_receive.html (z57→z58) — 발주 정보 카드에 VAT 모드·과세구분·공급가액·부가세 4 항목 추가
30. database.py — `_po_vat_calc(qty, price, vat_mode)` 헬퍼 신설 + `_po_backfill_vat(c, po_id, mode, class)` PRAGMA gate 헬퍼 + po_create/po_update 끝에 백필 호출
31. main.py po_new_submit + po_edit_submit — header dict에 vat_mode/tax_classification 키 2개 추가

### 8차 (5/11) — part_detail.html 단독 (분량 최다)
32. part_detail.html (구버전 amber → z58) — 시안1 전면 재작성:
    - 헤더: 코드 + 품명 + chip-biz/chip-acc/chip-proc/pill + 액션 (수정/발주/목록)
    - 자가치유 알림 + 재고 critical/low alert
    - KPI 5종 (현재 재고/재고가치/활성단가/안전재고/재주문점)
    - 좌측 메인 9 섹션: FIFO 레이어 / 단가 이력 30건 / 적용일자 단가 / 7단가 chain placeholder / BOM placeholder / 최근 입출고 / 프로젝트별 사용 / 첨부 갤러리 / 단가 등록 폼
    - 우측 사이드 3 카드: 마스터 정보 (z58 컬럼 전체 노출) / 공급사별 단가 요약 / 빠른 액션
    - data-dn 15개 영역

### 9차 (5/11) — wo_form.html 시안1 (작업지시 작성·상세 통합)
33. wo_form.html (구버전 amber → z58) — 시안1 전면 재작성 (신규 폼 + 상세 조회 단일 페이지 통합):
    - 신규 모드 (wo=None): 4섹션 폼 (기본정보 / 일정·담당자 / 가공 사양 / 공정 단계 + 표준 공정 일괄 자동) + 사이드 가이드
    - 상세 모드 (wo 객체): KPI 4 (수량/평균진행률/계획기간/총공수) + 정보 카드 + 공정 표 (진행률 막대) + 발행 액션 (DRAFT → RELEASED)
    - chip-wo 5상태 (s-draft/released/progress/done/cancel)
    - 라우터 호환 form name 10 (헤더) + 5 (라인 getlist) 정확 정합
    - data-dn 11개 영역

### 10차 (5/11) — qc_report_form.html 시안1 (검사 성적서 작성·상세 통합)
34. qc_report_form.html (구버전 amber → z58) — 시안1 전면 재작성:
    - 신규 모드 (report=None): 3섹션 폼 (기본 정보 / 판정·담당 / 검사 항목 + 표준 6항목 일괄 추가) + 사이드 가이드·표준항목
    - 상세 모드 (report 객체): KPI 4 (종합판정/합격수/불합격수/NA수) + 검사 정보 카드 + 검사 항목 표 + 발급 액션 (DRAFT → ISSUED)
    - chip-q 판정 3종 + chip-st 상태 2종 (DRAFT/ISSUED)
    - 라인 판정 select 색상 자동 변경 (PASS=초록 / FAIL=빨강 / NA=회색)
    - 라우터 호환 form name 12 (헤더) + 5 (라인 getlist) 정확 정합
    - data-dn 10개 영역
    - **잠재 버그 복구**: 기존 action `/qc/reports/new` → 라우터 정확한 `/qc/inspection-reports`로 정정

### 11차 (5/11) — wo_print.html 시안1 인쇄 (작업지시 풀체인 완성)
35. wo_print.html (구버전 #1B5E20 → z58 모노) — 시안1 인쇄 친화 전면 재작성:
    - @page A4 + @media print + 외부 자산 0건 (인라인 CSS만)
    - 상단 헤더: KNK 회사 정보 (company_name_ko / company_address / company_tel / company_biz_no / company_ceo_ko) + 제목 "작업지시서 / WORK ORDER"
    - 메타 표 4행: WO번호/상태chip/발행일 / 수주/프로젝트/발행자 / 가공부품/담당자 / 생산수량/계획시작/계획종료
    - 가공 사양 박스 + 공정 표 (#·공정명·공수·진행률바·작업자·비고) + tfoot 합계
    - 비고 박스 + **도장란 4종** (작성/검토/승인/수령 — 자동 채움 + 빈칸)
    - 자동 인쇄 옵션 (?auto=1 쿼리)
    - chip 5상태 (s-draft/released/progress/done/cancel) — wo_form과 동일
    - **검증 결함 1건 발견 → 즉시 수정**: company 키 명명 불일치 (company.company_name → company_name_ko 등 7개 키 정정)
    - **작업지시 풀체인 완성**: wo_list (z57) + wo_form (9차 z58) + wo_print (11차 z58) = 3종 ✅

### 12차 (5/11) — qc_report_print.html 시안1 인쇄 (품질 풀체인 완성)
36. qc_report_print.html (구버전 amber → z58 모노) — 시안1 인쇄 친화 (wo_print 대칭):
    - @page A4 + @media print + 외부 자산 0건
    - KNK 회사 헤더 + 제목 "검사 성적서 / QC INSPECTION REPORT"
    - **종합 판정 강조 박스** (최상단) — PASS=초록 / CONDITIONAL_PASS=황 / FAIL=빨강 색상 외곽선
    - **KPI 4종** (전체항목/합격/불합격/합격률)
    - 메타 표 4행: 보고서번호/상태/검사일 + 고객사/수주/검사부품 + 모델/시리얼/발급일 + 검사자/QA매니저/발급자
    - 검사 항목 표 (#/항목명/Spec/Measured/판정 j-chip/비고) + tfoot 합계 (PASS/FAIL/NA 카운트)
    - 비고 박스 (시정조치)
    - **도장란 3종** — 검사자(자동)/QA매니저(자동)/승인(빈)
    - 자동 인쇄 옵션 (?auto=1)
    - **품질 G 그룹 풀체인 완성**: qc_report_list (z57) + qc_report_form (10차) + qc_report_print (12차) = 3종 ✅

### 13차 (5/11) — supplier_form.html 시안1 (공급사 풀체인 완성)
37. supplier_form.html (구버전 amber → z58) — 시안1 전면 재작성 (신규 + 수정 통합):
    - 4 섹션 폼: 기본정보(명·코드·국가·활성) / 연락처(담당·전화·이메일) / 결제·거래조건(통화·결제조건) / 비고
    - chip-pick 활성여부 + 통화 6종 + PAYMENT_TERMS select
    - 사이드 4 카드: 요약 / 📊 리드타임 통계 (편집 모드만, KPI 4) / 💡 입력 가이드 / ⚠️ 삭제
    - 라우터 호환 form name 10개 (name·code·contact·email·phone·country·currency·payment_terms·note·is_active)
    - data-dn 7개 영역 (head/basic/contact/terms/note/side/action)
    - **공급사 D 그룹 풀체인 완성**: suppliers (z57) + supplier_form (z58 13차) = 2종 ✅

### 14차 (5/11) — stock_issue.html 시안1 (재고 출고 등록 / E 그룹 시작)
38. stock_issue.html (구버전 amber → z58) — 시안1 전면 재작성:
    - 3 섹션 폼: 자재 선택(자재 정보 카드 자동) / 출고 정보(수량+사유+단가+위치) / 귀속(프로젝트+고객+비고)
    - **자재 정보 카드** — 자재 select 변경 시 현재 재고/안전 재고/표준 단가 자동 표시 + 안전재고 미만 색상 경고
    - **출고 후 재고 미리보기** — 수량 입력 시 즉시 (현재 - 출고 = 예상) + 초과 입력 시 빨강 + 사이드 요약 갱신
    - 출고 사유 6종 select (현장출고/생산투입/외주지급/수리교체/시료샘플/기타)
    - 사이드 2 카드: 출고 요약(자재·수량·금액·상태) + 💡 가이드
    - 라우터 호환 form name 9개 (part_id·quantity·project_id·customer_id·unit_price·reason·location·occurred_at·note)
    - data-dn 7개 영역
    - URL ?error= 처리 alert 배너 표시

### 15차 (5/11) — stock_issues.html 시안1 (출고 이력 / stock_receipts 대칭)
39. stock_issues.html (구버전 amber → z58) — 시안1 전면 재작성:
    - KPI 4종 (전체/대기 PENDING/완료 ISSUED/취소 CANCELLED)
    - chip-iss 3상태 + UNKNOWN fallback
    - 7컬럼 dense 표 (GI번호·상태·자재·수량·용도·요청시각·출고시각)
    - URL ?success= / ?error= 배너 자동 표시 (라우터 invalid/notfound/already-XXX 처리)
    - 빈 상태 메시지 + CTA "+ 출고 등록"
    - 헤더 액션 3종 (재고현황·입고이력·＋출고등록)
    - data-dn 6개 영역
    - stock_receipts (입고 이력 z57) 와 대칭 디자인

### 20차 (5/11) — qms_dashboard.html 시안1 (G 품질 BI 시작)
45. qms_dashboard.html (z58) — KPI 6 + 미해결 이슈 표 + chip-sev/chip-sla/chip-typ + nav-strip 4종

### 21차 (5/11) — qms_pareto.html (80/20 분석)
46. qms_pareto.html (z58) — KPI 4 + 빈도+막대+누적비중 + 80% 영역 강조 행 + tfoot 합계

### 22차 (5/11) — qms_recurrence.html (재발 분석)
47. qms_recurrence.html (z58) — RID 그룹 + RC 그룹 양 섹션 / chip-cnt 핫/웜/마일드 / 연결 이슈 링크
    - **잠재 버그 5개 키 복구**: g.rid/g.title/g.root_cause/g.issue_ids/g.last_occurred → gid/cnt/first_at/last_at

### 23차 (5/11) — qms_capa.html (G 품질 BI 완성)
48. qms_capa.html (z58) — KPI 4 (avg_closure_days/verify_rate/completed/verified) + CA/PA 5단계 라이프사이클 시각화 + 부서별 분포 막대 + chip-lc 5색
    - **잠재 버그 키 6개 복구**: it.kind/title/detail/status/owner_name/deadline/deadline_overdue → lifecycle_status/action/due_date/completed_at/verified_at/issue_id/issue_no/issue_title
    - **G 품질 그룹 완성**: list + form + print + dashboard + pareto + recurrence + capa = 7/7 ✅

### 24차 (5/11) — part_prices.html (C 부품 완성)
49. part_prices.html (z58) — KPI 3 + 신규 등록 폼 9필드 + 이력 표 (활성 행 초록 배경)
    - **잠재 422 버그 복구**: Form name `applied_date` → `effective_from` (라우터 required Form 미스매치)
    - **C 부품 그룹 완성**: parts + part_form + part_detail + part_prices = 4/4 ✅

### 25차 (5/11) — fx_rates.html (H 환율·원가 시작)
50. fx_rates.html (z58) — 통화별 KPI auto-fit + 등록 폼 5필드 + 통화 필터 chip + 이력 표

### 26차 (5/11) — rates_dashboard.html (환율 BI)
51. rates_dashboard.html (z58) — 통화 KPI + 알림 카드 + 30일 추이 표 + 스파크바 (외부 차트 0)

### 27차 (5/11) — rates_history.html (단가 변경 이력)
52. rates_history.html (z58) — KPI 4 (상승/하락 분리) + 변동률 ▲▼ 색상 (CSS) + tfoot
    - **잠재 버그 키 5개 복구**: applied_date/currency/unit_price_krw/rate/source → effective_date/supplier_name/old_price/new_price/change_pct (price_change_history 테이블)

### 28차 (5/11) — rates_alerts.html (환율 알림)
53. rates_alerts.html (z58) — KPI 4 + 등록 폼 4필드 + 카드 그리드 + chip 발동/활성/비활성
    - **잠재 버그 4건 복구**: Form name (currency→target_currency, condition→direction) + 키 2 (a.currency/a.condition → a.target_currency/a.direction, a.recipients 제거) + 미구현 라우터 1건 (/toggle 폼 제거)

### 30차 (5/11) — rates.html (사내 환율 메인)
55. rates.html (구버전 amber → z58) — 사내 사용자용 환율 1차 진입점:
    - 통화별 KPI auto-fit (CURRENCIES dynamic)
    - 등록 폼 6필드 (rate_date·from_currency·to_currency·rate·source·note)
    - 통화 필터 chip + 이력 표 (등록자·등록일시 포함)
    - **잠재 버그 2건 복구**: Form name `currency` → `from_currency` (라우터 미스매치) + 키 `r.currency` → `r.from_currency`

### 31차 (5/11) — stock_adjustment.html (재고 조정 양 모드)
56. stock_adjustment.html (구버전 amber → z58) — 목록 + 첨부 양 모드 통합:
    - 12컬럼 표 (시스템/실측/차이 분리 표시) + chip-st 3상태 + chip-typ ＋/－
    - 승인/반려 액션 버튼 (can_approve)
    - 첨부 양 모드: 카드 그리드 + 업로드 폼 (PDF/JPG/PNG/XLSX, 10MB)
    - URL ?success/?error 배너
    - **잠재 버그 9건 대량 복구**:
      - 목록 키 6: adj_date/part_code/adj_type/qty_delta/requester_name/has_attach → created_at/part_no/(부호기반)/adjusted_qty/created_by_name/(att_counts dict)
      - 첨부 키 3: a.url/filename/size → file_path/file_name/uploaded_at
    - **PROGRESS 표기 오류 발견**: "미사용 별칭"으로 표기되어 있었으나 라우터 2곳에서 실사용 → 즉시 정정

### 32차 (5/11) — issue_detail.html (이슈 상세 + 편집)
57. issue_detail.html (구버전 amber → z58) — 이슈 상세 + 업데이트 폼 통합:
    - 헤더: 이슈번호 + 제목 + chip-sev 4종 + chip-st 4종 + chip-typ + SLA 초과 배지
    - 좌측 메인 4섹션: 이슈 내용 / 원인·조치·재발방지 (3색 강조) / **업데이트 폼** (can_edit) / 처리 이력 시간순
    - 우측 사이드 4 카드: 정보 / SLA / 관련 변경 / 재발 그룹
    - 업데이트 폼 9필드 (status·owner_team_id·cost_estimate·related_change_id·root_cause·action_taken·prevention·comment·note)
    - **잠재 버그 5건 복구**: issue.detail→description, owner_name→owner_user_name, project_name 제거(미조인), l.actor_name→user_name, l.body→content
    - **신규 UI 추가**: 업데이트 폼 UI 자체가 없었음 → 라우터 POST /issues/{id}/update 와 연결

### 33차 (5/11) — issue_form.html (이슈 등록)
58. issue_form.html (구버전 amber X / z58 통일) — 신규 이슈 발의 폼:
    - 좌측 메인 2섹션: 기본정보(제목·유형·심각도·상세) / 발생맥락(사업부·프로젝트·고객사·발생일시·발견자·담당팀)
    - 우측 사이드 2 카드: 가이드 (심각도 기준 + 메신저 자동 알림 안내) / 유형 분류 설명
    - **잠재 버그 3건 복구**:
      - Form name `detail` → `description` (라우터 미반영 → 저장 누락 가능)
      - Form `sla_hours` 제거 (라우터 미수신)
      - severity 기본값 `'보통'` → `'중'` (화이트리스트 정합)
    - 누락 4 필드 추가: biz_div / customer_name / occurred_at / detected_by

### 34차 (5/11) — fta_list.html (FTA 원산지 목록)
59. fta_list.html (구버전 amber → z58) — FTA 원산지증명서 목록 (수출 모듈):
    - KPI 5 (전체/DRAFT/ISSUED/SENT/CANCELLED)
    - 10컬럼 표 (cert_no/협정/고객사+국가/원산지/수출일/총액+통화/상태/발급일/발급자)
    - chip-fta + chip-st 4종 + chip-cur + chip-orig
    - 필터 UI 신규 (상태 × 협정 다차원)
    - **잠재 버그 5건 복구**:
      - 미존재 키 3: f.product_name/f.hs_code/f.expires_at → 라우터 미반환 (라인 테이블에 있음)
      - 라우터 path 2: /fta/certificates/{id} → /export/fta/{id}, /fta/certificates/new → /export/fta/new
    - active="sales" → "sales" 유지 (수출 영역)

### 35차 (5/11) — fta_print.html (FTA 인쇄)
60. fta_print.html (구버전 → z58 모노) — 시안1 인쇄 친화 (wo_print/qc_report_print 대칭):
    - @page A4 + @media print + 외부 자산 0건
    - 영문/한글 이중 제목 + fta-badge + status-tag (4상태 우상단 절대 위치)
    - 수출자 정보 카드 + 메타 5행 (cert_no/협정/수입자/원산지·통화/인보이스·수출일)
    - 라인 표 8컬럼 + tfoot 총액 강조
    - 선언문 (영문+한글) + 비고
    - **도장란 3종**: 발급자 자동 / 회사 직인 / 수입자 확인 (빈)
    - 자동인쇄 옵션 (?auto=1)
    - **수출 모듈 풀체인 완성**: fta_list + fta_print = 2/2 ✅ (fta_form은 별도 발주 권장)

### 29차 (5/11) — rates_cost_sim.html (H 그룹 완성)
54. rates_cost_sim.html (z58) — KPI 4 + 시뮬 폼 7필드 + 라이브 미리보기 JS + 공식 가이드 사이드 + 이력 표
    - **잠재 버그 10건 대량 복구**: action path (/rates/sim/{id} → /rates/cost-sim) + Form name 5 (currency/foreign_price/assumed_rate/qty 제거 → base_currency/unit_price_base/exchange_rate + target_currency/margin_pct/note 추가) + 키 5 (s.currency/foreign_price/assumed_rate/qty/total_krw → base_currency/unit_price_base/exchange_rate/margin_pct/unit_price_target)
    - 라이브 JS: target = base × rate × (1 + margin/100) 자동 계산
    - **H 환율·원가 그룹 완성**: fx_rates + dashboard + history + alerts + cost_sim = 5/5 ✅
    - **🎉 자재구매센터 30+ 페이지 시안1 z58 마이그레이션 100% 완료**

### 17차 (5/11) — stock_audits/stock_audit.html 시안1 (재고 실사 풀체인)
41. stock_audits.html (구버전 amber → z58) — 시안1 전면 재작성:
    - KPI 3 (전체/진행중 OPEN/마감 CLOSED)
    - chip-au 2상태 + UNKNOWN fallback
    - 8컬럼 표 (실사번호·상태·실사일·주관·라인수·차이건·비고·승인)
    - 차이 건 > 0 빨강 강조
    - 헤더 액션: + 실사 발의 (POST /stock/audits/new) — confirm 후 제출
    - 빈 상태 CTA + 첫 실사 발의 폼
42. stock_audit.html (z58) — 실사 상세:
    - KPI 4 (계획/실측/차이/금액영향)
    - 헤더 chip 상태 + 마감 액션 (OPEN → CLOSED)
    - 실측 라인 입력 (자재별 실측 수량 → 차이 자동 계산)
    - 차이 보정 트랜잭션 자동 생성 안내
    - data-dn 8 영역
    - **실사 E 그룹 완성**: stock_audits + stock_audit ✅

### 18차 (5/11) — stock_fifo.html 시안1 (FIFO 레이어 조회)
43. stock_fifo.html (구버전 amber → z58) — 시안1 전면 재작성:
    - KPI 3 (활성 레이어 수 / 총 잔량 / 총 가치)
    - 7컬럼 표 (#·입고일·자재·잔량/입고량+막대·단가·가치·PO/LOT 참조)
    - layer-bar 막대 (잔량 비율 시각화)
    - tfoot 합계
    - 빈 상태 메시지
    - 자재 상세 페이지 연결 (summary.part_id)
    - data-dn 3 영역

### 19차 (5/11) — stock_qc.html 시안1 (입고 QC + 부적합 처리)
44. stock_qc.html (구버전 amber → z58) — 시안1 전면 재작성:
    - 양 모드 (신규 검수 폼 + 검수 이력)
    - 판정 4종 (PASS/PARTIAL/HOLD/FAIL) — 색상 chip-q-pass/cond/fail
    - 부적합 처리 3종 (RETURN 반품 / SPECIAL_ACCEPT 특채 / SCRAP 폐기)
    - 입고 PO 라인 연동 + 합격/불합격/보류 수량 분리 입력
    - 부적합 처리 액션 (HOLD → 처리 결정 → 재고 영향)
    - 사이드 가이드 + 통계 KPI
    - **E 재고 그룹 완성 (13/13)**: balances·movements·abc·safety·turnover·reorder·issue·issues·receipts·adjust·audits·audit·fifo·qc ✅

### 16차 (5/11) — stock_adjust.html 시안1 (재고 조정 / ± 부호 처리)
40. stock_adjust.html (구버전 amber → z58) — 시안1 전면 재작성:
    - **부호 토글 (+/-)** — 입고조정 (＋ 초록) / 출고조정 (－ 빨강) 버튼식 선택
    - 사용자는 **절대값** 입력 + hidden input으로 부호 적용 후 라우터 제출
    - 자재 정보 카드 (현재 재고 자동 표시)
    - 조정 후 재고 미리보기 (음수 결과 시 빨강 + 제출 차단 안내)
    - 사유 **11종 grouped select**:
      - 입고조정(+): 실사차이/이전누락보정/환입 (3)
      - 출고조정(-): 실사차이/손망실/폐기/시제품/외주무상지급 (5)
      - 기타 (1) — 비고 필수 안내
    - 사이드 3 카드: 조정 요약(자재·부호·수량·상태) / 💡 가이드 / ⚠️ 회계 감사 주의
    - 라우터 호환 form name 4개 (part_id·quantity·reason·note)
    - data-dn 6개 영역
    - URL ?error= 처리 배너

## 변경 파일 누적 목록 (빅터 보고 시 사용)

```
[기준서·통보 인프라]
- 01C_HAIST_WORKS_자재구매/_STANDARD_자재모듈기준_v1.md
- 01C_HAIST_WORKS_자재구매/PROGRESS.md
- 01C_HAIST_WORKS_자재구매/output/_TO_01/README.md
- 01C_HAIST_WORKS_자재구매/output/_TO_01/2026-05-10_22-00_STD_자재모듈기준_v1_초안.md
- 01C_HAIST_WORKS_자재구매/output/_TO_01/2026-05-10_23-30_DONE_logistics_home.md
- 01C_HAIST_WORKS_자재구매/output/_TO_01/2026-05-11_00-30_DONE_v4룰정렬.md
- 01C_HAIST_WORKS_자재구매/output/_TO_01/2026-05-11_07-30_DONE_7시간자율_14페이지.md  (예정)

[자체 도구]
- 01C_HAIST_WORKS_자재구매/01C_도구.bat

[코드 16 페이지]
- 01_HAIST_WORKS/app/templates/po_list.html
- 01_HAIST_WORKS/app/templates/logistics_home.html
- 01_HAIST_WORKS/app/templates/parts.html
- 01_HAIST_WORKS/app/templates/suppliers.html
- 01_HAIST_WORKS/app/templates/stock_balances.html
- 01_HAIST_WORKS/app/templates/stock_movements.html
- 01_HAIST_WORKS/app/templates/stock_safety.html
- 01_HAIST_WORKS/app/templates/stock_reorder.html
- 01_HAIST_WORKS/app/templates/po_detail.html
- 01_HAIST_WORKS/app/templates/wo_list.html
- 01_HAIST_WORKS/app/templates/qc_report_list.html
- 01_HAIST_WORKS/app/templates/stock_abc.html
- 01_HAIST_WORKS/app/templates/stock_receipts.html
- 01_HAIST_WORKS/app/templates/stock_turnover.html
- 01_HAIST_WORKS/app/templates/po_form.html        ← 3차
- 01_HAIST_WORKS/app/templates/po_receive.html    ← 3차

[마이그레이션 SQL — 적용 위임]
- 01C_HAIST_WORKS_자재구매/migrations/v5H226z56_자재모듈표준v1.sql

[메모리]
- ~/.claude/.../memory/session_team3_purchase.md
- ~/.claude/.../memory/trademark_anonymization_rules.md
- ~/.claude/.../memory/feedback_no_99_dispatch_for_subteams.md
- ~/.claude/.../memory/MEMORY.md (인덱스 갱신)

[BAT — 빅터01 전용. 본 세션 갱신 안 함]
※ 본 세션의 z54·z56 메인 BAT 갱신은 빅터(01)이 z55·z58로 정상 흡수함.
```

## 위험 / 차단 사항
없음. 라우트·DB 스키마·`_v5_partials/` 공통 partial·메인 BAT 변경 0건.

**다음 차수 권장:**
1. po_form / po_receive / wo_form (분량 큰 폼 페이지)
2. part_detail (FIFO 레이어 + 단가 이력 + 공급사별 통합)
3. stock_issue / stock_issues / stock_qc (출고 영역)
4. qms_dashboard / qms_pareto / qms_capa (품질 영역)
5. rates_* 5종 (환율·원가)
6. 마이그레이션 SQL 적용 후 part_prices / wo_form 의 BOM·단가 chain 활성화

## 빅터 보고 이력
- 2026-05-10 1차: po_list.html → `output/HANDOFF_TO_01.md` (v1)
- 2026-05-10 2차: logistics_home.html → `output/HANDOFF_TO_01_v2.md`
- 2026-05-11 3차: v4 룰 정렬 → `output/HANDOFF_TO_01_v3.md`
- 2026-05-11 4차: **7시간 자율 작업 14페이지 종합** → `output/HANDOFF_TO_01_v4.md`
- 2026-05-11 5차: **발주 풀체인 (po_form/po_receive)** → `output/HANDOFF_TO_01_v5.md`
- 2026-05-11 6차: **자재모듈 표준 v2 (z58 SQL + parts/part_form + 백엔드 확장)** → `output/HANDOFF_TO_01_v6.md`
- 2026-05-11 7차: **VAT 모드 발주 풀체인 (po_form/po_detail/po_receive + 백엔드)** → `output/HANDOFF_TO_01_v7.md`
- 2026-05-11 8차: **part_detail.html 시안1 재작성 (9 섹션 + 사이드 3카드 + KPI 5)** → `output/HANDOFF_TO_01_v8.md`
- 2026-05-11 9차: **wo_form.html 시안1 (신규 폼 + 상세 통합 / chip-wo 5상태)** → `output/HANDOFF_TO_01_v9.md`
- 2026-05-11 10차: **qc_report_form.html 시안1 (검사 성적서 양 모드 + 표준 6항목 자동)** → `output/HANDOFF_TO_01_v10.md`
- 2026-05-11 11차: **wo_print.html 시안1 인쇄 (A4 + 도장란 4종 / 작업지시 풀체인 완성)** → `output/HANDOFF_TO_01_v11.md`
- 2026-05-11 12차: **qc_report_print.html 시안1 인쇄 (판정 강조 박스 + 도장란 3종 / 품질 풀체인 완성)** → `output/HANDOFF_TO_01_v12.md`
- 2026-05-11 13차: **supplier_form.html 시안1 (4섹션 + 리드타임 KPI / 공급사 풀체인 완성)** → `output/HANDOFF_TO_01_v13.md`
- 2026-05-11 14차: **stock_issue.html 시안1 (자재 정보 자동 + 재고 미리보기 + E 그룹 시작)** → `output/HANDOFF_TO_01_v14.md`
- 2026-05-11 15차: **stock_issues.html 시안1 (출고 이력 / receipts 대칭)** → `output/HANDOFF_TO_01_v15.md`
- 2026-05-11 16차: **stock_adjust.html 시안1 (± 부호 토글 + 11종 사유 / 음수 차단)** → `output/HANDOFF_TO_01_v16.md`
- 2026-05-11 17차: **stock_audits/stock_audit.html 시안1 (실사 목록 + 상세 / 차이 자동 보정)** → INBOX 묶음 통보
- 2026-05-11 18차: **stock_fifo.html 시안1 (FIFO 레이어 / 잔량 막대 + KPI 3)** → INBOX 묶음 통보
- 2026-05-11 19차: **stock_qc.html 시안1 (입고 QC 4판정 + 부적합 처리 3종 / E 그룹 13/13 완성)** → INBOX 묶음 통보
- 2026-05-11 20~23차: **G 품질 BI 4종 (dashboard/pareto/recurrence/capa) / 잠재 버그 11건 복구** → INBOX 묶음 통보
- 2026-05-11 24차: **part_prices.html (C 부품 완성 / 422 버그 복구)** → INBOX
- 2026-05-11 25~29차: **H 환율·원가 5종 (fx_rates/dashboard/history/alerts/cost_sim) / 잠재 버그 19건 복구 / 자재구매센터 100% 완료** → INBOX 묶음 통보
- 2026-05-11 30~35차: **A+B+C 추가 6종 (rates·stock_adjustment·issue_detail·issue_form·fta_list·fta_print) / 잠재 버그 24건 복구 + 라우터 path 2건 + 신규 UI 2건** → INBOX 묶음 통보
- 2026-05-12 36차: **자재 중복 방지 (A안 3층 방어) + QR 코드 발행 통합** → INBOX 통보
- 2026-05-12 37차: **자재 사업부 정제 시스템 (등록 차단 + 일괄 재분류 도구 + 알림)** → INBOX 통보
- 2026-05-12 38차: **자재 일괄 등록 (Excel) 기능 구현** → INBOX 통보
  - 기존 `/parts/import` = alias만 → 실제 페이지로 구현
  - 라우터: GET/POST `/parts/import` + POST `/parts/import/apply` + GET `/parts/import/template.xlsx`
  - DB: `parts_bulk_import_excel(dry_run, force_similar)` 신규 (헤더 자동 매핑 + 검증 + INSERT)
  - 신규 페이지: `parts_import.html` (3 모드 — upload/preview/result)
  - 빈 템플릿 다운로드 (20 컬럼 + 예시 2행 + 가이드 시트) Excel 자동 생성
  - DB: `parts_usage_distribution()` + `parts_bulk_reclassify()` 신규
  - 라우터: `GET /parts/reclassify` + `POST /parts/reclassify/apply` 신규
  - 신규 페이지: `parts_reclassify.html` (출고 이력 기반 자동 추천 + 일괄 선택 + 적용)
  - 수정: `part_form.html` (사업부 필수 + "공통" 선택 시 경고) + `parts.html` (재분류 진입 버튼 + 공통 과다 경고 배너)
  - DB: `_normalize_part_key` / `_levenshtein` / `_similarity_score` / `parts_find_similar` 4개 + `parts_create(force=)` 확장
  - 라우터: `GET /parts/check` (실시간 JSON) + `GET /parts/{pid}/qr.svg` + `GET /po/{po_id}/qr.svg` + `GET /qr/scan` (페이로드 라우팅) + 인쇄 라우터 2개
  - 신규 페이지: `part_qr_print.html` (A4 12장 격자) + `po_qr_print.html` (단독 큰 QR)
  - 수정 페이지: `part_form.html` 전면 재작성 (시안1 z58 + 실시간 유사 검사 + QR 카드 + 라우터 정합 + 누락 13 필드)
  - QR 통합: `po_detail.html` (헤더 QR 버튼) + `po_receive.html` (스캐너 바 + JS 자동 매칭) + `part_detail.html` (QR 카드)
  - 의존성: `qrcode 8.2` PIP 추가 (외부 CDN 0건, 서버 SVG 생성)
