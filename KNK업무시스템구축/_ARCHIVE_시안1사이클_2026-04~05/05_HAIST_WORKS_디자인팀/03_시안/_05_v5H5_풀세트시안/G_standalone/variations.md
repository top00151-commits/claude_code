# G. Standalone 카테고리 — 변형 가이드

> 마스터 3종:
> - `master_G_login_v5H5.html` (로그인)
> - `master_G_error_v5H5.html` (404·500·로딩)
> - `master_G_print_v5H5.html` (인쇄 6종 표준)
>
> 12종 standalone 페이지 변형 명세 — base 미상속

---

## 적용 대상 12 페이지

| # | 페이지 | 라우트 | 우선순위 | 마스터 | 비고 |
|---|---|---|---|---|---|
| 1 | **로그인** | `/login` | **P0** | login 마스터 | 좌 그라데이션 + 우 폼 |
| 2 | **사용가이드** | `/guide` | **P0** | (이미 PREVIEW에 있음) | `02_guide_v5_H5.html` 참조 |
| 3 | 견적서 인쇄 | `/sales/quotations/{id}/print` | P1 | print 마스터 | 회사정보 미입력 시 빨간 배너 |
| 4 | CI 인쇄 | `/export/ci/{id}/print` | P1 | print 마스터 | 통화·Incoterms 추가 |
| 5 | PL 인쇄 | `/export/pl/{id}/print` | P1 | print 마스터 | 포장 단위·무게 |
| 6 | B/L 인쇄 | `/export/bl/{id}/print` | P1 | print 마스터 | 운송·통관 |
| 7 | FTA 인쇄 | `/export/fta/{id}/print` | P1 | print 마스터 | HSK·원산지 |
| 8 | QC 검사보고서 인쇄 | `/qc/inspection-reports/{id}/print` | P2 | print 마스터 | 항목별 OK/NG 표 |
| 9 | 작업지시서 인쇄 | `/production/work-orders/{id}/print` | P2 | print 마스터 | BOM 트리 |
| 10 | **404 에러** | (FastAPI 기본) | P1 | error 마스터 | 자주 찾는 페이지 4종 |
| 11 | **500 에러** | (FastAPI 기본) | P1 | error 마스터 | 빅터 자동 알림 |
| 12 | **로딩 인디케이터** | (전역) | P2 | error 마스터 | 진척 막대 + 빅터 팁 |

---

## 마스터별 핵심 컴포넌트

### login 마스터 (`master_G_login_v5H5.html`)
- 좌측 앰버 그라데이션 환영 패널 + 통계 3종 미리보기
- 우측 흰 폼 (사번/이메일·비밀번호·체크·SSO)
- 로고는 흰 카드 위 (원본색 보존)
- 모서리 28px (가장 둥근)

### error 마스터 (`master_G_error_v5H5.html`)
- 큰 코드 (404/500) — 그라데이션 텍스트
- 이모지 56px
- 자주 찾는 페이지 4-6 링크
- 빅터 도움말 카드 (검정 배경)
- 로딩: 스피너 + 진척 막대 + 빅터 팁 ("DID YOU KNOW?")

### print 마스터 (`master_G_print_v5H5.html`)
- **회사정보 미입력 빨간 배너** (조건부 — 01 응답서 §3-G 인계)
- 헤더 3-단 (로고 + 회사정보 + 문서종류)
- 메타 2-블록 (거래처 / 발주정보)
- 라인 표 (검정 보더)
- 합계 (총액 그라데이션)
- 서명 + 도장
- 푸터
- **`@media print` 미디어 쿼리** — 인쇄 시 그라데이션 → 검정 단색 자동 변환

---

## 변형 키 (인쇄 6종)

### 견적서 인쇄
- `doc-type`: "견적서" (영문 "Quotation")
- 추가: 견적 유효기간 (필수)
- 합계: 견적 단가 별도 표시 옵션

### CI (Commercial Invoice)
- `doc-type`: "Commercial Invoice"
- 통화 + Incoterms (FOB·CIF·EXW...)
- 영문 표기 우선

### PL (Packing List)
- `doc-type`: "Packing List"
- 추가: 포장 단위 (Box / Pallet) + 무게 (Net / Gross) + 부피 (CBM)

### B/L 인쇄
- `doc-type`: "Bill of Lading"
- 추가: Vessel·Voyage·Port of Loading·Discharge

### FTA 원산지
- `doc-type`: "Certificate of Origin"
- HSK 코드 컬럼
- 원산지 판정 결과
- 발급 기관 도장 영역

### QC 검사보고서
- `doc-type`: "Inspection Report"
- 항목별 OK/NG 매트릭스 표
- 사진 첨부 영역 (4-6 grid)
- 검사자 서명

### 작업지시서
- `doc-type`: "Work Order"
- BOM 트리 (들여쓰기)
- 라인별 수량·재료·작업시간

---

## 공통 표준 (모든 인쇄)

1. **회사정보 미입력 시 빨간 배너** (조건부 표시)
2. **`@media print`**: 그라데이션 → 검정 단색 자동 변환 / 도구바 숨김 / page-break-after 적용
3. **로고 + 회사정보** 좌측 헤더 표준
4. **문서번호** 우상단 그라데이션
5. **검정 보더 표** (인쇄 시 기본)
6. **서명·도장** 영역 표준 (2-2 그리드)
7. **푸터**: 시스템 자동 생성 + 문서번호 (감사 추적)

---

## 빈 상태 (Empty State) — N-3 보강 완료

마스터 시안 발행: **`master_G_empty_v5H5.html`** (4종 표준)

| 코드 | 용도 | 트리거 페이지 |
|---|---|---|
| **E-01** | 견적 0건 (영업 첫날) | `/sales/quotations` |
| **E-02** | 고객사 0건 (신규 사용자) | `/customers` |
| **E-03** | 재고 임계 미만 0건 (양호) | `/stock/balances` |
| **E-04** | 검색·필터 결과 없음 | 전 리스트 페이지 공통 |

### 4종 표준 구조 (모든 빈 상태)
1. **큰 이모지** (64px) — 감정 전달
2. **헤드라인** + 부 본문
3. **다음 액션 2 버튼** (보조·CTA)
4. **빅터 도움말** (검정 카드, optional)

→ D 리스트 카테고리 24 페이지 모두 본 4종 중 적합한 패턴 적용.

---

**발행**: 2026-04-29 · 빅터(05) · G 카테고리
