# B. 매트릭스 카테고리 — 변형 가이드

> 마스터: `master_B_matrix_sales_dashboard_v5H5.html` (`/sales/dashboard`)
> 본 가이드: 같은 마스터로 처리할 12종 페이지의 변형 명세

---

## 적용 대상 12 페이지 (01 응답서 §3-B)

| # | 페이지 | 라우트 | 템플릿 | base | P | M-코드 | 변형 키 |
|---|---|---|---|---|---|---|---|
| 1 | **매출 분석** | `/sales/dashboard` | `sales_dashboard.html` | base_sales | **P0** | M-01-06 | 마스터 자체 |
| 2 | 매출 예측 | `/sales/forecast` | `sales_forecast.html` | base_sales | P1 | M-01-07 | A |
| 3 | 채권 노화 | `/sales/aging` | `sales_aging.html` | base_sales | P1 | M-01-08 | B |
| 4 | 미수금 현황 | `/sales/outstanding` | `sales_outstanding.html` | base_sales | **P0** | M-01-05 | C |
| 5 | 생산 진행 | `/sales/production` | `sales_production.html` | base_sales | P1 | — | D |
| 6 | 환율 KPI | `/rates/dashboard` | `rates_dashboard.html` | base_logi | P1 | — | E |
| 7 | QMS 대시 | `/qms` | `qms_dashboard.html` | base | P1 | — | F |
| 8 | QMS 파레토 | `/qms/pareto` | `qms_pareto.html` | base | P2 | — | G |
| 9 | QMS 재발률 | `/qms/recurrence` | `qms_recurrence.html` | base | P2 | — | H |
| 10 | ABC 분석 | `/stock/abc` | `stock_abc.html` | base_logi | P2 | — | I |
| 11 | 재고 회전율 | `/stock/turnover` | `stock_turnover.html` | base_logi | P2 | — | J |
| 12 | 병목 분석 | `/bottlenecks` | `bottlenecks.html` | base | P2 | — | K |

---

## 변형 키 — 페이지별 차이 spec

### 마스터 (`/sales/dashboard`) 핵심 컴포넌트
1. **매트릭스 5종 탭** (`.matrix-tabs`) — 대시·일별·월별·연간·고객별
2. **4 KPI 카드** (`.kpi-row`) — 첫 카드는 그라데이션 (featured)
3. **도구바** (`.toolbar`) — 필터 + 검색 + Excel 내보내기
4. **데이터 테이블** (`.table-wrap`) — 스파크라인 + 칩
5. **우측 인사이트 패널** (`.insights`) — 빅터 자동 분석 4 카드

### A. /sales/forecast (매출 예측)
- 5 탭 변경: `예측 1Q · 2Q · 3Q · 4Q · 연간`
- KPI 변경: 예측 매출 / 신뢰도 % / 리스크 / 기회
- 테이블 컬럼: 분기 / 예측액 / 실적 / 차이 / 확률
- 인사이트: "Q2 예상 +12% — 대성·삼강 발주 패턴"

### B. /sales/aging (채권 노화)
- 5 탭 변경: `0-30일 · 31-60 · 61-90 · 91-180 · 180+`
- KPI 변경: 총 미수 / 30일 이내 / 90+ 위험 / 평균 노화일수
- 테이블 컬럼: 고객 / 미수액 / 발생일 / 경과일수 / 위험도(색)
- 위험도 칩: `pill--ok`(0-30) / `pill--warn`(31-90) / `pill--low`(90+)

### C. /sales/outstanding (미수금)
- 5 탭 제거 — 단일 뷰
- 큰 KPI 4개 (전체·30일내·90일내·180+)
- 테이블 컬럼: 고객 / 미수액 / 발생 / 마지막 입금 / 담당
- 인사이트 빨강 강조

### D. /sales/production (생산 진행)
- 5 탭 변경: `진행률·일정·자재·검수·완료`
- KPI: 진행 PJT / 지연 / 검수 대기 / 완료
- 테이블: 프로젝트 / 진행률 (gauge) / 자재 도착 / 일정 D-N

### E. /rates/dashboard (환율)
- base 변경: base_logi
- 5 탭 변경: `KRW · USD · EUR · JPY · CNY`
- KPI: 현재 환율 / 24h 변동 / 7일 변동 / 30일 변동
- 차트: SVG 라인 차트 (히어로)

### F. /qms (QMS 대시)
- 5 탭 변경: `이슈·결함·시정·예방·재발`
- KPI: 신규 이슈 / 처리 / 평균 처리일 / 재발률

### G. /qms/pareto (파레토)
- 5 탭 제거
- 메인 영역: 파레토 차트 (큰 SVG 80% 화면)
- 우측 인사이트: 80/20 원인 분석

### H. /qms/recurrence (재발률)
- 5 탭 변경: `1주·1개월·분기·반기·연간`
- 매트릭스: 카테고리 × 기간 히트맵

### I. /stock/abc (ABC 분석)
- base_logi
- 3 탭만: `A · B · C`
- 테이블: SKU / 매출 점유율 / 누적 % / 분류

### J. /stock/turnover (회전율)
- 5 탭 변경: `전체·A급·B급·C급·이상치`
- KPI: 평균 회전율 / 정체 SKU / 부족 SKU / 적정 SKU

### K. /bottlenecks (병목)
- 5 탭 변경: `현재·예측·해소·재발·통계`
- 메인: 흐름도 시각화 (라인+노드)

---

## 공통 표준 (모든 변형 공통)

1. **5 탭 컴포넌트** (`.matrix-tabs`) — 항목명·숫자만 변경 (탭 수 5 유지 권장. 단일 뷰는 탭 제거 가능)
2. **4 KPI 패턴** — 첫 KPI는 항상 `featured` (그라데이션)
3. **도구바 필터** — 필터 5종 표준 (기간·등급·담당·등록일·상태) + Excel 버튼
4. **테이블 디자인** — `pill`·스파크라인·trend-up/down 표준 칩 사용
5. **인사이트 패널** — 4-5 카드 (그중 1개 highlight 강조 — 그라데이션 inkblock)

---

## 01팀 반영 체크리스트

| 변형 | 핵심 변경 | 검증 grep |
|---|---|---|
| sales_dashboard | 마스터 그대로 | `class="matrix-tabs"` |
| sales_forecast | 5 탭 변경 + 분기 컬럼 | `1Q·2Q·3Q·4Q` |
| sales_aging | 노화 5단계 + 위험도 칩 | `pill--low`·`pill--warn` |
| sales_outstanding | 5 탭 제거 + 큰 KPI 4 | (`.matrix-tabs` 없음) |
| qms_pareto | 5 탭 제거 + SVG 파레토 | `<svg.*pareto` |
| stock_abc | 3 탭만 | `repeat(3, 1fr)` |
| 환율 / 회전율 / 병목 | 차트·히트맵·흐름도 추가 | (페이지별) |

---

**발행**: 2026-04-29 · 빅터(05) · B 카테고리
**다음 카테고리**: C 폼
