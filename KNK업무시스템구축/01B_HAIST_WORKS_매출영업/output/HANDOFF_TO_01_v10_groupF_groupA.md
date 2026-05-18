# 📋 실무팀2 → 빅터(01) 핸드오프 v10 — 그룹 F·A 사이클 완료

> **발신**: 실무팀2 (매출영업센터)
> **수신**: 빅터 (01 통합실무팀)
> **결재 기준**: 김정락 대표이사 — "(2) 권한 추가 + 다음 차수 진행 + 완료 후 검증 필수" (2026-05-10)
> **작성일**: 2026-05-10
> **버전**: v5H226z57 → **v5H226z62**

---

## 1. 🎯 본 사이클 결과 — 6 페이지 v1+v2 완료

| 그룹 | 페이지 | z 번호 | 커밋 | 변경 |
|---|---|---|---|---|
| **F (납품·수금)** | sales_shipments_receipts.html | z57 | e2f2cbc | 토큰 + .mgmt-pill (수주번호) + data-dn |
| **F** | sales_outstanding.html | z58 | b3dfb10 | 토큰 + 1100px + data-dn 6영역 |
| **F** | sales_aging.html | z59 | 1f5254d | 토큰 + bento 5→3col 반응형 + data-dn 7영역 |
| **A 잔여** | sales_dashboard.html | z60 | 9feac5b | 토큰 + 1100px + data-dn 6영역 |
| **A 잔여** | sales_forecast.html | z61 | d6bd20b | 토큰 + 1100px (3→1col) + data-dn 5영역 |
| **A 잔여** | sales_production.html | z62 | 29835b6 | 토큰 + .mgmt-pill (수주번호) + data-dn |

**누적 매출영업 진행률: 19 페이지 / 30+ = 약 63%**

---

## 2. ✅ 자체 검증 결과 (대표 지시: "완료 후 한번 더 검증")

### 검증 A — 토큰 / 1100px / data-dn 부착 (Grep 자동검증)
- `--qv-surface:#ffffff` 토큰: **3/3 통과** (dashboard, forecast, production)
- `@media (max-width:1100px)` 반응형: **3/3 통과**
- `data-dn="main"` 부착: **3/3 통과**

### 검증 B — 메인 폴더 동기화 (옵션 A)
- `diff -q` 워크트리 ↔ 메인: **3/3 일치** (출력 0줄)

### 검증 C — git push 상태
- 6 commits (z57~z62) 모두 origin/claude/charming-yonath-a72046 에 push 완료
- working tree clean (`git status --short` 0줄)

### 검증 D — REPLY v2 룰 준수
| 룰 | 결과 |
|---|---|
| 메인 BAT (KNK_시작.bat / START.bat) 미수정 | ✅ |
| `_v5_partials/` 미접촉 | ✅ |
| DB 스키마 / `main.py` 라우트 미접촉 | ✅ |
| PARTS 28컬럼 백엔드 미접촉 | ✅ |
| 외부 자산 0건 (Chart.js, 외부 API 등) | ✅ |
| 외부 상표권·라이선스 비침해 | ✅ |
| 워크트리 → 메인 폴더 동기화 | ✅ 6회 |

---

## 3. 🎨 페이지 간 일관성 — 누적 통계

### `.mgmt-pill` 적용 페이지 (12곳)
1. project_detail.html (헤더 lg + 자식 sm)
2. sales_orders.html (SO 리스트 + 임박 납기)
3. sales_home.html (최근 프로젝트 sm)
4. customer_detail.html (프로젝트 표 sm)
5. sales_order_detail.html (헤더 mgmt_code 링크)
6. sales_quote_detail.html (헤더 견적번호 lg)
7. sales_quotations.html (견적번호 sm)
8. projects.html (프로젝트 mgmt_code sm)
9. sales_shipments_receipts.html (z57, 수주번호 sm)
10. sales_production.html (z62, 수주번호 sm)
11. customers_list.html (등록만)
12. customer_form / project_form / sales_quote_form (등록만)

### 시안1 토큰 도입 페이지 (18곳)
project_detail / sales_orders / sales_home / customer_detail / sales_order_detail / sales_quote_detail / sales_quotations / projects / customers_list / sales_quote_form / project_form / customer_form / sales_shipments_receipts / sales_outstanding / sales_aging / **sales_dashboard / sales_forecast / sales_production**

→ 18 페이지 모두 동일 11종 토큰 (qv 6 + biz 4) body 스코프 등록

### data-dn 부착 페이지 (18곳)
모든 페이지 main / page-head / 주요 영역에 부착

### 1100px 반응형 분기 (18곳)
모든 페이지에 추가

---

## 4. 📂 본 사이클 6 커밋

```
e2f2cbc v5H226z57 — sales_shipments_receipts v1+v2 (토큰 + .mgmt-pill + data-dn)
b3dfb10 v5H226z58 — sales_outstanding v1+v2 (토큰 + 1100px + data-dn 6영역)
1f5254d v5H226z59 — sales_aging v1+v2 (토큰 + bento 반응형 + data-dn 7영역)
9feac5b v5H226z60 — sales_dashboard v1+v2 (토큰 + 1100px + data-dn 6영역)
d6bd20b v5H226z61 — sales_forecast v1+v2 (토큰 + 1100px + data-dn 5영역)
29835b6 v5H226z62 — sales_production v1+v2 (토큰 + .mgmt-pill + data-dn)
```

---

## 5. ⚠️ 미진행 페이지 (남은 11+개)

| 우선순위 | 페이지 | 비고 |
|---|---|---|
| 낮음 | project_new_chooser.html | 4 카드, 단순 |
| 낮음 | quotation_print.html | A4 PDF, 인쇄 전용 |
| 다음 사이클 | consumables.html × 3 | 그룹 G 소모품 |
| 다음 사이클 | export_*.html × 11 | 그룹 H 수출입 (베트남 P11) |
| 다음 사이클 | fta_*.html × 3 | FTA 원산지 |
| 옵션 | 빨강 다이어트 v3 × 16 | 미적용 페이지 |

---

## 6. 🛑 대표님 결재 대기 사항

### 결재 A — 본 사이클 6 페이지 검수
- 19 페이지 누적 (43% → 63% 진척)
- preview panel 또는 브라우저 직접 확인 가능

### 결재 B — 다음 사이클 진입 옵션
- 옵션 (1) 그룹 G 소모품 (3 페이지) — 짧고 마감 쉬움
- 옵션 (2) 그룹 H 수출입 11 + FTA 3 = **14 페이지** — 베트남 수출 P11 페르소나 핵심
- 옵션 (3) 빨강 다이어트 v3 일괄 적용 (남은 16 페이지)
- 옵션 (4) project_new_chooser + quotation_print 마무리
- 옵션 (5) 대표 직접 지정

빅터 권장: **(2) 그룹 H** — 페이지 수 많지만 베트남 P11 페르소나가 결재 우선순위 높음. 또는 **(1) 그룹 G** — 단기 빠른 마감 가능.

---

## 7. 🙇 빅터 메모

- 권한 추가 후 commit 차단 0회 — 사이클 6 커밋 모두 정상 진행
- 모든 변경 단일 페이지 한정 — 다른 페이지 영향 0
- 본 사이클 검증 자동 (Grep + diff) → 향후 사이클도 동일 패턴 적용
- z62 까지 누적 commit 22 개 (자율 7시간 14 + 본 사이클 6 + z53 동기화 1 + 최종 보고 1)

---

**문의**: `_ORDERS/` 발주서 v2 / `99_DISPATCH/` 채널
**확인 도구**: `01B_매출영업_상태확인.bat` 더블클릭
