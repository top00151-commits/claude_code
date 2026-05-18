# 📤 실무팀3 → 빅터(01) 핸드오프 — v2

> **세션:** 실무팀3 (자재구매센터)
> **기준일:** 2026-05-10
> **시스템 버전:** v5H226z56 (z55 빅터 통합 후 +1)
> **차수:** 2차

---

## 1. 이번 차수 요약

**완료 1건:** 우선순위 2번 `logistics_home.html` (자재구매 홈) — Quiet Ops + 시안1 적용.

| 항목 | 결과 |
|---|---|
| Quiet Ops 톤 전환 | ✅ amber-grad 잔존 0건 (완전 잉크/회색) |
| KPI 6장 (12-col 그리드) | ✅ 가용 데이터 100% (parts_count + stock_kpi) |
| 발주 흐름 5단계 시각화 | ✅ DB PO_STATUSES 매핑 |
| 사업부별 자재 분포 | ✅ parts_stats.by_div + biz 색 토큰 |
| Quick Actions 4종 | ✅ 신규 발주/입고/출고/자재 등록 |
| ?debug=1 영역 라벨 | ✅ 11개 부착 (head, kpi-1~6, flow, biz, near-receipt, low-stock-detail, quick-actions) |
| 빨강 사용 ≤1개/페이지 | ✅ 안전재고 미달 KPI alert만 (조건부) |
| chrome / DB / 라우트 변경 | ✅ 0건 (빅터 회신 §3 보류 사항 준수) |

## 2. 변경 파일

```
01_HAIST_WORKS/app/templates/logistics_home.html  (전면 재작성)
01C_HAIST_WORKS_자재구매/PROGRESS.md              (진행 갱신)
01C_HAIST_WORKS_자재구매/output/HANDOFF_TO_01_v2.md  (본 파일)
01C_HAIST_WORKS_자재구매/output/_TO_01/2026-05-10_..._DONE_logistics_home.md  (INBOX)
99_DISPATCH/2026-05-10_..._FYI_실무팀3_logistics_home_v1.md  (FYI)
```

**라우트·DB 스키마·_v5_partials 변경 없음** (REPLY_FROM_01 §3 보류 정책 준수).

**BAT 갱신 없음** (z55 도입 룰 — 빅터01만 갱신).

## 3. 적용한 시안1 컴포넌트

- **PageHead:** `자재구매센터 > 자재구매 홈` + 메타 (총 자재 / 활성 / 진행 발주 / 안전재고 미달 조건부)
- **KPI 6장:**
  1. 총 자재 종수 (활성/비활성)
  2. 진행 발주 (작성중+발주완료+부분입고)
  3. 30일 입고 (단위 합)
  4. 30일 출고 (단위 합)
  5. 안전재고 미달 (alert 톤, 조건부 빨강)
  6. 총 재고가치 (FIFO 실단가 / 억·만원 자동)
- **발주 흐름:** 5단계 막대 (작성중/발주완료/부분입고/입고완료/취소). 색상 시안1 토큰. 단계별 분포는 라우트 확장 후 활성화 예정 (현재 합계만 표시).
- **사업부별 자재 분포:** 4사업부 (T/M/E/C) + 미지정. 막대 너비 = 비중. biz 색 토큰 (--biz-t/m/e/c) 사용.
- **Placeholder 카드 2종:** "입고 임박 (D-3)" + "안전재고 미달 상세" — 라우트 확장 결재 대기 표시 (대시 점선 + 위임 안내).
- **Quick Actions 4종:** 신규 발주 / 입고 처리 / 출고 등록 / 자재 등록.

## 4. 데이터 호환성 — 시안1 사양 vs 가용

| # | 시안1 사양 | 가용 데이터 | 본 차수 처리 |
|---|---|---|---|
| 1 | 이달 발주액 (3.62억) | sum(po.total_amount) by month — **미가용** | KPI 슬롯 → 30일 입고로 대체 |
| 2 | 진행 발주 (18건) | sk.po_pending ✅ | 가용 그대로 |
| 3 | 이번 주 입고 7건 | 별도 쿼리 필요 — **미가용** | 30일 입고로 대체 |
| 4 | 납기 지연 2건 | 별도 쿼리 (expected_date < today) — **미가용** | 안전재고 미달 alert로 대체 |
| 5 | 안전재고 미달 3 | sk.low_stock ✅ | 가용 그대로 |
| 6 | 공급사 OTD 94.2% | 별도 계산 — **미가용** | 총 재고가치로 대체 |
| 7 | 발주 흐름 7단계 | DB enum 5단계 | 5단계만 (REPLY §2 동의) |
| 8 | 사업부 비교 (구매×매출) | 매출 데이터 도메인 분리 — **미가용** | 자재 분포만 표시 |
| 9 | 입고 임박 (D-3) 7행 | 라우트 미제공 | placeholder 카드 |
| 10 | 안전재고 미달 3건 상세 | 라우트 미제공 | placeholder 카드 |

**결론:** 가용 6 KPI + 발주흐름 + 사업부분포 + Quick Actions 는 시안1 톤 100% 적용. 미가용 2영역(입고임박·안전재고상세)은 placeholder + 라우트 확장 후 활성화 명시.

## 5. 화면 동작 검증 (?debug=1)

브라우저 `http://localhost:8081/logistics?debug=1` 접속 시 11개 라벨 표시:
- `lh:head` (PageHead)
- `lh:kpi-1` ~ `lh:kpi-6` (KPI 6장)
- `lh:flow` (발주 흐름)
- `lh:biz` (사업부 분포)
- `lh:near-receipt` (입고 임박 placeholder)
- `lh:low-stock-detail` (안전재고 placeholder)
- `lh:quick-actions` (Quick Actions)

## 6. 다음 차수 계획

**3순위 `parts.html` + `part_detail.html`** (부품 마스터) 착수 예정.

작업 전 정독:
- `01_HAIST_WORKS/HAIST WORKS디자인변경/design_handoff_haist_works/specs/09-inventory.md` (재고 패턴 참조)
- `components-purchasing.jsx`의 `Inventory` / 시안1 부품 카드 그리드 부분
- 위하고_자료 `품목등록.xlsx` 33컬럼 매핑 (익명화 어휘로 구현)

가용 데이터 점검:
- `_logi.parts_list()` 어떤 필드 반환하는지 확인 후 컬럼 결정
- 마이그레이션 v5H226z56 적용 후 `code_v2` / `safety_stock` / `default_warehouse` 활용 가능

## 7. 빅터(01) 검토 요청 사항

- [ ] logistics_home.html 1차 결과 점검 (Quiet Ops 톤 / KPI 6 / 발주흐름 / 사업부 / placeholder)
- [ ] **마이그레이션 SQL `v5H226z56_자재모듈표준v1.sql` 적용 의사** — 대표 5건 결재 통과 후 작성. 빅터(01) 또는 대표 직접 라인에서 실행 권장. 본 세션은 적용 안 함 (안전).
- [ ] 라우트 확장 결재 진행 의향 (입고 임박 / 안전재고 상세 / 사업부 매출 비중) → 현재 placeholder 상태 활성화
- [ ] 3순위 `parts.html` 착수 승인

## 8. 파생 결재 요청 사항 (대표 라인)

마이그레이션 SQL 적용 시점에서:
- DB 백업 → 적용 → 검증 → 운영 재개 가이드는 SQL 파일 헤더 §VERIFY / §ROLLBACK 참조
- 적용은 빅터(01) 단독 또는 대표 직접 실행. 실무팀3 권한 외.

---

**보고:** 실무팀3 (자재구매센터) → 빅터(01)
**결재:** 김정락 대표이사 직접 라인
