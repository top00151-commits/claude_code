# 📋 실무팀2 → 빅터(01) 핸드오프 v11 — 그룹 H 수출입 + FTA 사이클

> **발신**: 실무팀2 (매출영업센터)
> **수신**: 빅터 (01 통합실무팀)
> **결재 기준**: 김정락 대표이사 — "빅터 권장안 진행" (그룹 H, 2026-05-10)
> **작성일**: 2026-05-10
> **버전**: v5H226z63 → **v5H226z70**

---

## 1. 🎯 본 사이클 결과 — 8 페이지 v1+v2 완료

| 그룹 | 페이지 | z 번호 | 커밋 | 변경 |
|---|---|---|---|---|
| **H 수출 (베트남 P11)** | export_home.html | z63 | c3accdf | 토큰 + .mgmt-pill (수출번호) + 1100px (5→3col) + data-dn |
| **H** | export_order_detail.html | z64 | e930414 | 토큰 + .mgmt-pill lg (헤더) + data-dn |
| **H** | export_order_form.html | z65 | ae861c3 | 토큰 + 1100px (frow 2→1col) + data-dn |
| **H** | export_ci.html | z66 | 4b56d8b | 토큰 + 1100px + data-dn (Commercial Invoice) |
| **H** | export_pl.html | z67 | 407893f | 토큰 + 1100px (frow 3→1col) + data-dn (Packing List) |
| **H** | export_bl_customs.html | z68 | a9e41eb | 토큰 + 1100px + data-dn (B/L 통관) |
| **H FTA** | fta_list.html | z69 | f3c4966 | 토큰 + .mgmt-pill (인증번호) + data-dn |
| **H FTA** | fta_form.html | z70 | 7b8e9e7 | 토큰 + 1100px + data-dn |

**누적 매출영업 진행률: 27 페이지 / 30+ = 약 90%**

---

## 2. ✅ 자체 검증 결과 (대표 지시: "완료 후 한번 더 검증 필수")

### 검증 A — 토큰 / 1100px / data-dn 부착 (Grep 자동검증)
- `--qv-surface:#ffffff` 토큰: **8/8 통과**
- `@media (max-width:1100px)` 반응형: **8/8 통과**
- `data-dn="main"` 부착: **8/8 통과**

### 검증 B — 메인 폴더 동기화 (옵션 A)
- `diff -q` 워크트리 ↔ 메인: **8/8 일치** (출력 0줄)

### 검증 C — git push 상태
- 8 commits (z63~z70) 모두 origin/claude/charming-yonath-a72046 push 완료

### 검증 D — REPLY v2 룰 준수
| 룰 | 결과 |
|---|---|
| 메인 BAT (KNK_시작.bat / START.bat) 미수정 | ✅ |
| `_v5_partials/` 미접촉 | ✅ |
| DB 스키마 / `main.py` 라우트 미접촉 | ✅ |
| PARTS 28컬럼 백엔드 미접촉 | ✅ |
| 외부 자산 0건 | ✅ |
| 외부 상표권·라이선스 비침해 | ✅ |
| 워크트리 → 메인 폴더 동기화 | ✅ 8회 |

---

## 3. 🎨 페이지 간 일관성 — 누적 통계 (z70 기준)

### `.mgmt-pill` 적용 페이지 (15곳)
project_detail / sales_orders / sales_home / customer_detail / sales_order_detail / sales_quote_detail / sales_quotations / projects / sales_shipments_receipts / sales_production / **export_home (수출번호) / export_order_detail (헤더 lg) / fta_list (인증번호)** + 컴포넌트 등록 (customers_list / form 4종)

### 시안1 토큰 도입 페이지 (26곳)
project_detail / sales_orders / sales_home / customer_detail / sales_order_detail / sales_quote_detail / sales_quotations / projects / customers_list / sales_quote_form / project_form / customer_form / sales_shipments_receipts / sales_outstanding / sales_aging / sales_dashboard / sales_forecast / sales_production / **export_home / export_order_detail / export_order_form / export_ci / export_pl / export_bl_customs / fta_list / fta_form**

### data-dn 부착 페이지 (26곳)
모든 페이지 main / page-head / 주요 영역에 부착

### 1100px 반응형 분기 (26곳)
모든 페이지에 추가

---

## 4. 📂 본 사이클 8 커밋

```
c3accdf v5H226z63 — export_home v1+v2
e930414 v5H226z64 — export_order_detail v1+v2 (헤더 .mgmt-pill lg)
ae861c3 v5H226z65 — export_order_form v1+v2
4b56d8b v5H226z66 — export_ci v1+v2
407893f v5H226z67 — export_pl v1+v2
a9e41eb v5H226z68 — export_bl_customs v1+v2
f3c4966 v5H226z69 — fta_list v1+v2 (.mgmt-pill 인증번호)
7b8e9e7 v5H226z70 — fta_form v1+v2
```

---

## 5. ⚠️ 미진행 페이지 (남은 4~6 페이지)

| 우선순위 | 페이지 | 비고 |
|---|---|---|
| 보류 (현 사이클) | export_ci_print.html | A4 인쇄 전용, chrome 없음 |
| 보류 | export_pl_print.html | A4 인쇄 전용 |
| 보류 | export_bl_print.html | A4 인쇄 전용 |
| 보류 | fta_print.html | A4 인쇄 전용 |
| 다음 사이클 | consumables.html × 3 | 그룹 G 소모품 |
| 옵션 | project_new_chooser.html | 4 카드 단순 |
| 옵션 | quotation_print.html | A4 PDF |
| 옵션 | 빨강 다이어트 v3 일괄 적용 | 미적용 페이지 다수 |

**print 4개 보류 사유**: 인쇄 전용 페이지는 chrome (header/sidebar) 없이 단독 렌더링 → 시안1 토큰·data-dn 적용 효과 미미. 빅터 판단으로 본 사이클 보류, 별도 사이클에서 인쇄 양식 통일 작업 권장.

---

## 6. 🛑 대표님 결재 대기 사항

### 결재 A — 본 사이클 8 페이지 검수
- 27 페이지 누적 (63% → 약 90% 진척)
- preview panel 또는 브라우저 직접 확인

### 결재 B — 다음 사이클 진입 옵션
- 옵션 (1) **그룹 G 소모품** (3 페이지) — 짧고 빠른 마감
- 옵션 (2) **print 4개 일괄** — 인쇄 양식 별도 디자인 토큰 (페이지 셋업 + A4 사이즈 + black on white)
- 옵션 (3) **빨강 다이어트 v3 일괄** — 남은 24+ 페이지 빨강 사용량 점검
- 옵션 (4) **project_new_chooser + quotation_print 마무리** — 단순 페이지 일괄
- 옵션 (5) **대표 직접 지정**

빅터 권장: **(1) 그룹 G** — 단기 빠른 100% 도달 가능. 또는 **(3) 빨강 다이어트** — 페이지 간 디자인 일관성 점검.

---

## 7. 🙇 빅터 메모

- 본 사이클 블로커 0회 (z62 권한 추가 후 commit 차단 없음)
- 베트남 수출 P11 페르소나 핵심 페이지 (export_home, export_order_detail) 시안1 적용 완료
- 인코텀즈·HS 코드·B/L·CI·PL·통관 단계 모든 폼 페이지 일관된 토큰
- z70 까지 누적 commit 30+개 (자율 7시간 14 + 그룹 F·A 6 + 그룹 H·FTA 8 + HANDOFF 보고)

---

**문의**: `_ORDERS/` 발주서 v2 / `99_DISPATCH/` 채널
**확인 도구**: `01B_매출영업_상태확인.bat` 더블클릭
