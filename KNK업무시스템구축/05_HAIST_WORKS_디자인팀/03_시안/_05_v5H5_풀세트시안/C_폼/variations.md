# C. 폼 카테고리 — 변형 가이드

> 마스터: `master_C_form_po_v5H5.html` (`/po/new` 발주서 작성)
> 본 가이드: 같은 마스터로 처리할 22종 폼 페이지의 변형 명세
> **발주서가 가장 복잡한 폼이라 마스터로 채택** — 다른 폼은 단순화 변형

---

## 적용 대상 22 페이지 (01 응답서 §3-C)

### 그룹 1 — 거래·발주 폼 (4종, 최복잡)
| # | 페이지 | 라우트 | 템플릿 | base | P | M-코드 | 변형 키 |
|---|---|---|---|---|---|---|---|
| 1 | **발주서** | `/po/new`·`/po/{id}/edit` | `po_form.html` | base_logi | **P0** | M-02-04 | 마스터 자체 |
| 2 | 견적서 | `/sales/quotations/new` | `quotation_form.html` | base_sales | **P0** | — | A |
| 3 | 부품 등록 | `/parts/new` | `part_form.html` | base_logi | P1 | — | B |
| 4 | 공급사 등록 | `/suppliers/new` | `supplier_form.html` | base_logi | P1 | — | C |

### 그룹 2 — 워크플로우 폼 (5종)
| # | 페이지 | 변형 키 | 특수 사항 |
|---|---|---|---|
| 5 | 입고 처리 `/po/{id}/receive` | D | 발주 라인 → 입고 매칭 + QC 분기 |
| 6 | 출고 등록 `/stock/issue` (M-02-08) | E | 안전재고 모달 confirm |
| 7 | 실사 조정 `/stock/adjust` (M-02-09) | F | 단건/다건 토글 |
| 8 | 검수·부적합 `/stock/qc/{id}` (M-02-12) | G | 사진 첨부 + disposition 모달 |
| 9 | 작업지시 `/production/work-orders/new` | H | 라인별 BOM |

### 그룹 3 — 일반 폼 (8종, 단순)
| # | 페이지 | 변형 키 | 단순화 정도 |
|---|---|---|---|
| 10 | 일일업무 `/daily` (M-00-02) | I | 4 카드 입력 (오전·오후·이슈·내일) |
| 11 | 게시글 작성 `/board/new` | J | 제목 + 본문 + 카테고리 + 첨부 |
| 12 | 이슈 등록 `/issues/new` | K | 제목 + 분류 + 우선순위 + 본문 |
| 13 | 변경공지 `/changes/new` | L | 제목 + 영향 범위 + 일정 + 첨부 |
| 14 | 티켓 작성 `/tickets/new` (M-00-12) | M | 분류 (admin/business) + 긴급도 |
| 15 | 관리코드 등록 `/projects/new` | N | 코드 + 거래처 + 일정 + 인원 |
| 16 | QC 검사보고서 `/qc/inspection-reports/new` | O | 사진 + 항목별 OK/NG + 서명 |
| 17 | 수출 오더 `/export/orders/new` | P | Incoterms + FTA 옵션 + 통화 |

### 그룹 4 — 수출 양식 (5종, 인쇄겸용)
| # | 페이지 | 변형 키 | 특수 사항 |
|---|---|---|---|
| 18 | CI 발행 `/export/ci/{id}` | Q | 제품·금액·통화 + 인쇄 |
| 19 | PL 발행 `/export/pl/{id}` | R | 포장 단위 + 무게 |
| 20 | B/L·통관 `/export/bl/{id}` | S | 운송 + 통관 항목 |
| 21 | 통관 양식 `/export/customs/{id}` | T | (B/L 재사용) |
| 22 | FTA 원산지 `/export/fta/new` (M-01-11) | U | HSK + 원산지 판정 + 서명 |

---

## 마스터 핵심 컴포넌트 (모든 변형 재사용)

1. **상단 폼 단계 인디케이터** (`.form-stepper`) — 4 step (기본·품목·결제·검토)
   - 단순 폼은 1~2 step 으로 축소
2. **섹션 표준** (`.form-section`) — h3 + 4px 앰버 강조 바
3. **필드 표준** (`.field`) — label·필수 표시·info 텍스트·hint
4. **인풋 포커스** — amber border + amber-glow box-shadow (3px)
5. **라인 항목** (`.lines`) — 그리드 7-컬럼 표 (#·품목·코드·수량·단가·금액·삭제)
6. **합계 영역** (`.totals`) — 소계·세금·운송·총액 (총액은 그라데이션 텍스트)
7. **첨부 박스** (`.attach-box`) — dashed border + 호버 amber-glow
8. **우측 사이드** (`.form-side`) — 요약 / 빅터 도움말 / 최근 활동
9. **하단 액션 바** (`.action-bar`) — sticky bottom · 자동저장 정보 + 4 버튼

---

## 변형 키 — 페이지별 차이 spec

### A. 견적서 (`/sales/quotations/new`)
- base 변경: `extends "base_sales.html"`
- 단계 변경: `1.고객→ 2.품목→ 3.조건→ 4.발행`
- 라인 항목: 7-컬럼 (마스터 동일) + 부가세 별표시 옵션
- 합계: 견적 유효기간 추가 (필드)
- 우측 사이드: 빅터 도움말 = "이 고객의 작년 동기 견적 패턴" 분석

### B. 부품 등록 (`/parts/new`)
- 단계 제거: 단일 폼
- 섹션 5개: 기본정보 / 사양 / 단가 / 거래처 / 첨부
- 라인 항목 없음 (단일 자재)
- 우측: 카테고리 자동 추천

### C. 공급사 등록 (`/suppliers/new`)
- 단계 제거
- 섹션: 기본정보 / 담당자 / 결제조건 / 거래분류
- 신용등급 자동 조회 버튼

### D. 입고 처리 (`/po/{id}/receive`)
- 발주 라인 → 입고 라인 자동 매칭
- 라인 항목에 "입고 수량 / 잔량 / QC 분기" 컬럼 추가
- 검수 동시 — 부적합 즉시 모달 (F 카테고리)

### E. 출고 등록 (`/stock/issue` M-02-08)
- 단계 2: 자재 선택 → 출고 확정
- **안전재고 미만 confirm 모달** (F 카테고리 모달 5종 중 1)
- 빅터 도움말: 출고 패턴 분석

### F. 실사 조정 (`/stock/adjust` M-02-09)
- 토글: 단건 / 다건
- 단건: 마스터 단순화 (2 섹션)
- 다건: 표 형태 + 일괄 조정

### G. 검수 (`/stock/qc/{id}` M-02-12)
- 사진 첨부 (필수)
- 항목별 OK/NG 토글 표
- NG 시 disposition 모달 (F 카테고리)

### H. 작업지시 (`/production/work-orders/new`)
- 단계 4: 기본·라인·BOM·검수
- 라인별 BOM 표 펼침 (트리)

### I. 일일업무 (`/daily` M-00-02)
- 4 카드: 오전 / 오후 / 이슈 / 내일
- 단계 없음
- 자동저장 표시 강조 (16:30 마감 카운트다운)

### J. 게시글 / K. 이슈 / L. 변경공지 / M. 티켓
- 단계 없음
- 단순 폼: 제목 + 분류 + 본문 + 첨부 (마스터 첨부 박스 재사용)
- 서식 도구: 마크다운 또는 리치 에디터 (separate)

### N. 관리코드 (`/projects/new`)
- 섹션 4: 기본·일정·인원·산출물

### O. QC 검사보고서
- 사진 첨부 + 항목별 OK/NG (G와 유사)
- 서명 영역 (e-signature)

### P. 수출 오더
- Incoterms 드롭다운 (FOB·CIF·EXW...)
- 통화 + FTA 옵션 (체크박스)

### Q-U. 수출 양식 5종
- 발주서 마스터 단순화 (라인 형식 유지)
- 인쇄 전용 미디어 쿼리 (`@media print`) — 표준 토큰 §19 활용
- 회사정보 미입력 시 빨간 배너 (G standalone 카테고리와 정합)

---

## 폼 검증·모달 표준 (F 카테고리에서 정의)

| 모달 | 트리거 | 위치 |
|---|---|---|
| 안전재고 미만 | 출고 등록 (E) | `F_모달/stock_safety_modal.html` |
| 부적합 disposition | 검수 (G) | `F_모달/qc_disposition_modal.html` |
| 견적 라인 추가 | 견적·발주 (A·마스터) | `F_모달/line_add_modal.html` |
| 거래처 신규 등록 | 발주·견적 거래처 선택 | `F_모달/supplier_quick_modal.html` |
| 발주 발행 확인 | 마스터 발행 버튼 | `F_모달/confirm_modal.html` |

(상세는 Phase 3 F_모달 카테고리에서 발행)

---

## 01팀 반영 체크리스트

| 변형 | 핵심 변경 | 검증 grep |
|---|---|---|
| po_form (마스터) | 4 step + 라인 + 합계 + 첨부 + 사이드 | `class="form-stepper"`·`class="lines"` |
| quotation_form | base_sales + 견적 유효기간 | `extends "base_sales.html"` |
| 일반 폼 (게시·이슈·티켓) | step 제거 + 단순 4 필드 | (`.form-stepper` 없음) |
| 입고·검수·실사 | 워크플로 분기 + 모달 | `<div class="modal"` |
| 수출 양식 | `@media print` + 빨간 배너 | `@media print` |

---

**발행**: 2026-04-29 · 빅터(05) · C 카테고리
**Phase 2 A·B·C 완료** — Phase 2 잔여 D·E·G·H·I·J + Phase 3 F·에러·로딩·모바일
