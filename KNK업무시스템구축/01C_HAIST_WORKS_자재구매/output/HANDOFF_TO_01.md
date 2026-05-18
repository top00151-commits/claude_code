# 📤 실무팀3 → 빅터(01) 핸드오프 — v1

> **세션:** 실무팀3 (자재구매센터)
> **기준일:** 2026-05-10
> **시스템 버전:** v5H226z54 (이전 z53에서 +1)
> **차수:** 1차

---

## 1. 이번 차수 요약

**완료 1건:** 우선순위 1번 `po_list.html` (발주 관리) — 시안1 ERP 풀 적용.

| 항목 | 결과 |
|---|---|
| 시안1 디자인 토큰 | ✅ 적용 (Quiet Ops palette) |
| 32px dense 표 + sticky thead | ✅ |
| 필터바(.filterbar) 칩 | ✅ 5종 상태 칩 + 검색 + 결과 카운트 |
| chip-po 상태 5종 매핑 | ✅ 작성중/발주완료/부분입고/입고완료/취소 |
| ?debug=1 영역 라벨 | ✅ po:head / po:kpi / po:filter / po:table / po:empty |
| 빨강 사용 ≤1개/페이지 | ✅ KPI '취소' 셀의 mute 처리 외 빨강 액센트 없음 |

## 2. 변경 파일

```
01_HAIST_WORKS/app/templates/po_list.html   (전면 재작성)
KNK_시작.bat                                 (LAST UPDATE 라인)
START.bat                                    (LAST UPDATE 라인)
```

**라우트·DB 스키마·_v5_partials 변경 없음** (발주서 7항 금지사항 준수).

## 3. 적용한 시안1 컴포넌트

- **PageHead 메타 라인:** `전체 N건 · 진행 N · 완료 N · 취소 N` (라이브 카운트)
- **KPI Strip 8칸:** 전체 / 작성중 / 발주완료 / 부분입고 / 입고완료 / 취소 / 총 발주액 / 평균
  - 각 셀 클릭 시 status 필터 토글 (서버 라우터 그대로 사용)
  - 금액 단위 자동 스위칭 (억/만원/원)
- **FilterBar:** 6개 상태 칩 + 검색 입력 + 결과 카운트 + ↺ 필터 해제
- **Dense 표:** 8컬럼 (발주번호 / 발주일 / 공급사 / 프로젝트·관리코드 / 금액 / 예상입고 / 상태 / 담당)
  - 짝수 행 zebra
  - tfoot 합계 행 (sticky bottom, 평균 + 부분입고 잔량)
  - 행 클릭 시 `/po/{id}` 이동
- **chip-po:** 5상태 색상 시안1 토큰 사용
  - 작성중: 회색 / 발주완료: 보라 / 부분입고: 주황 warn / 입고완료: 잉크 검정 / 취소: 회색 + 취소선

## 4. 데이터 호환성 — ⚠️ 사양 vs 실제 갭

| 항목 | 시안1 사양 (07-po-manage.md) | 실제 라우트 제공 | 본 차수 처리 |
|---|---|---|---|
| 컬럼 수 | 14개 (체크 + 사업부 + 품명 + 수량 + 단가 + L/T 등) | 8개만 가용 | 가용 8컬럼만 표시 |
| 사업부(b)·품명·수량·단가·L/T | DB join 필요 | po_list 라우트 미제공 | 미표시 |
| 8 KPI mini-strip | 진행/이번달/평균단가/평균LT/OTD/긴급/승인대기/미입고잔액 | 일부만 산출 가능 | 6 status + 합계/평균 8칸 (집계 가능 항목만) |
| PO_STATUSES enum | tokens.css는 8종 (draft/req/app/sent/partial/recv/closed/overdue) | DB는 5종 | DB 기준 5종으로 매핑 |

**권고 (별도 결재 필요):**
- `database.py:po_list()` SELECT 확장으로 사업부 / 대표 품목명 / L/T 추가 시 시안1 14컬럼 풀 복원 가능
- 라우트 확장은 권한 밖이라 빅터(01) 또는 대표 결재 라인으로 요청

## 5. 화면 동작 검증 (?debug=1)

브라우저에서 `http://localhost:8081/po?debug=1` 접속 시 5개 영역 라벨이 우상단에 표시됨:
- `po:head` (PageHead)
- `po:kpi` (KPI Strip)
- `po:filter` (FilterBar)
- `po:table` (Dense table) — 데이터 있을 때
- `po:empty` (Empty state) — 데이터 없을 때

## 6. 다음 차수 계획

발주서 우선순위 → **2순위 `logistics_home.html`** (자재구매 입사 첫 화면) 착수 예정.

다만 디자인 핸드오프 `06-purchase-home.md` + `screenshots/06-purchase-home.png` 정독 후 시작.

## 7. 빅터(01) 검토 요청 사항

- [ ] po_list.html 1차 결과 화면 점검 (이전 amber-grad 톤 → Quiet Ops 톤 전환 인식 OK?)
- [ ] PO_STATUSES enum 5종 매핑 동의 (시안1 8종에서 현실 5종으로 축약)
- [ ] 라우트 확장(사업부·품명·L/T) 결재 라인 의향 — 풀 14컬럼 복원 여부
- [ ] 2순위 `logistics_home.html` 착수 승인

---

**보고:** 실무팀3 (자재구매센터) → 빅터(01)
**결재:** 김정락 대표이사 직접 라인
