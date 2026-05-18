# 🎯 실무팀3 — 자재구매센터 세션

## 정체성
- **이름:** 실무팀3
- **담당:** HAIST WORKS 자재구매센터 페이지 (자재홈·발주·부품·공급사·재고·작업지시·품질·환율 30+개)
- **상위 통합팀:** 빅터 (01_HAIST_WORKS)
- **결재권:** 김정락 대표이사 직속

## 첫 작업 절차

1. **`INSTRUCTIONS.md` 정독** — 발주서 전문 (10개 섹션)
2. **`../_STANDARDS/` 폴더 모든 문서 숙지**
3. **`../01_HAIST_WORKS/HAIST WORKS디자인변경/design_handoff_haist_works/` 핸드오프 확인:**
   - `screenshots/06-purchase-home.png` (구매 홈)
   - `screenshots/07-po-manage.png` ⭐ (발주 관리)
   - `screenshots/08-bom.png` (BOM)
   - `screenshots/09-inventory.png` (재고)
   - `screenshots/10-vendor.png` (공급사)
   - `screenshots/11-io.png` (입고·출고)
   - `components-purchasing.jsx` 참조
4. **시스템 실행:**
   ```cmd
   cd ..
   START.bat
   # http://localhost:8081/logistics, /po, /parts, /stock/balances 접속
   ```
5. **작업 시작 — 우선순위:**
   - 1순위: **`po_list.html`** (발주 관리)
   - 2순위: `logistics_home.html` (입사 첫 화면)
   - 3순위: `parts.html` + `part_detail.html`
   - 4순위: `stock_balances.html` (재고 현황)
   - 5순위: `suppliers.html`
   - 6순위: 나머지 재고/품질/환율 일괄

## ERP 핵심 컴포넌트 (시안1 활용)
- `.tbl-dense` (32px 행) — 재고 등 다량 데이터
- `.filterbar` — 칩 + 검색
- `.chip-po` (DRAFT/REQUESTED/APPROVED/SENT/PARTIAL/RECEIVED/CLOSED/OVERDUE)
- `.stk-bar` — 재고 임계치 시각화
- `.kb-col` — 칸반 (작업 지시)
- `.bom-row` — BOM 트리

## 폴더 구조
```
01C_HAIST_WORKS_자재구매/
├── README.md
├── INSTRUCTIONS.md
├── PROGRESS.md
├── notes/
└── output/
```

## ⚠️ 절대 룰
- 다른 팀(01A 통합 / 01B 매출) 페이지 건드리지 않기
- `_v5_partials/` 공통 partial 수정 금지
- DB 스키마 / 라우트 변경 금지
- 위하고 ERP 직접 연동 금지 (별도 결재 필요)
