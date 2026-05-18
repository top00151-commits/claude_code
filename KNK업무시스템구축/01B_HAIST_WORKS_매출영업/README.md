# 🎯 실무팀2 — 매출영업센터 세션

## 정체성
- **이름:** 실무팀2
- **담당:** HAIST WORKS 매출영업센터 페이지 (매출홈·프로젝트·고객사·견적·수주·납품수금·미수금·수출입 30+개)
- **상위 통합팀:** 빅터 (01_HAIST_WORKS)
- **결재권:** 김정락 대표이사 직속

## 첫 작업 절차

1. **`INSTRUCTIONS.md` 정독** — 발주서 전문 (10개 섹션)
2. **`../_STANDARDS/` 폴더 모든 문서 숙지**
3. **`../01_HAIST_WORKS/HAIST WORKS디자인변경/design_handoff_haist_works/` 핸드오프 확인:**
   - `screenshots/03-project.png` ⭐ **가장 중요** (프로젝트 상세)
   - `screenshots/02-orders.png` (수주 관리)
   - `screenshots/01-sales-home.png` (매출 홈)
4. **시스템 실행:**
   ```cmd
   cd ..
   START.bat
   # http://localhost:8081/sales, /sales/orders, /project/{id} 접속
   ```
5. **작업 시작 — 우선순위:**
   - 1순위: **`project_detail.html`** (가장 복잡, 가장 사고 많음)
   - 2순위: `sales_orders.html` (이미 80% 진행됨)
   - 3순위: `sales_home.html` (입사 첫 화면)
   - 4순위: `sales_order_detail.html`, `customer_detail.html`
   - 5순위: 견적/납품수금/미수금
   - 6순위: 수출입/FTA

## 핵심 UX 원칙 (대표 직접 지시)
1. **관리번호 우선** — 모든 표/카드/리스트 1열
2. **한 화면에 다 보이게** — 스크롤 최소화
3. **표 헤더 sticky**

## 폴더 구조
```
01B_HAIST_WORKS_매출영업/
├── README.md
├── INSTRUCTIONS.md
├── PROGRESS.md
├── notes/
└── output/
```

## ⚠️ 절대 룰
- 다른 팀(01A 통합 / 01C 자재) 페이지 건드리지 않기
- `_v5_partials/` 공통 partial 수정 금지
- PARTS 28컬럼 백엔드 로직 변경 금지 (display만 개선)
- DB 스키마 / 라우트 변경 금지
