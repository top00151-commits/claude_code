# 📤 실무팀3 → 빅터(01) 핸드오프 — v10 (qc_report_form.html 시안1)

> **세션:** 실무팀3 (자재구매센터)
> **워크트리:** `cranky-shtern-789fa2` — 메인 폴더 직접 작업 모드
> **기준일:** 2026-05-11
> **시스템 버전:** v5H226z58
> **차수:** 10차 (품질 모듈 시작 — qc_report_list 풀체인 보완)

---

## 1. 배경

빅터 추천 §10차 = **B 품질 모듈** 시작. qc_report_list (z57 완료, 7차) 다음 누락이었던 **qc_report_form.html** 을 시안1 z58로 전면 재작성. wo_form 패턴 차용 — 신규/상세 단일 페이지 통합.

## 2. 산출물 (1 파일)

### `qc_report_form.html` — 신규 폼 + 상세 조회 통합

#### 신규 모드 (report=None)
- 3 섹션:
  1. **기본 정보** — 고객사 / 수주 / 검사부품 / 검사일 / 모델 / 시리얼번호
  2. **판정·담당** — 종합 판정 (PASS/CONDITIONAL_PASS/FAIL) / QA 매니저 / 비고
  3. **검사 항목** — line_item_name / line_spec / line_measured / line_judgment / line_remarks (getlist 라인) + **표준 6항목 일괄 추가**
- 사이드 2 카드: 발급 가이드 / 표준 6항목 표시
- JS: `loadStdItems()` 표준 6항목 자동 채움 / `updateJudgmentStyle()` 판정 색상 동적 변경

#### 상세 모드 (report 객체)
- KPI 4종: 종합 판정 / PASS 수·비율 / FAIL 수·비율 / NA 수
- 검사 정보 카드 (보고서 번호/고객사/수주/검사부품/모델/시리얼/검사일/검사자/QA매니저)
- 검사 항목 표 (#/항목명/Spec/측정값/판정chip/비고)
- 발급 액션 (DRAFT → ISSUED) — 빨간 확인 다이얼로그

## 3. 라우터 호환성 정합

| 위치 | 라우터 (main.py:17591 qc_report_create) | qc_report_form.html |
|---|---|---|
| 신규 action | POST `/qc/inspection-reports` | 일치 ✅ |
| 발급 action | POST `/qc/inspection-reports/{id}/issue` | 일치 ✅ |
| 헤더 필드 12개 | customer_id / customer_name / order_id / order_no / part_id / machine_model / machine_serial / inspection_date / overall / qa_manager_id / qa_manager_name / remarks | 동일 ✅ |
| 라인 getlist 5개 | line_item_name / line_spec / line_measured / line_judgment / line_remarks | 동일 ✅ |

⚠️ **잠재 버그 복구**: 기존 폼 action `/qc/reports/new` (POST) — 라우터 없음. z58에서 정확한 `/qc/inspection-reports` (POST)로 정정.

## 4. 자체 검증 결과 (1패스)

| 항목 | 결과 |
|---|---|
| amber-grad / knk-red 잔존 | **0건** ✅ |
| data-dn 영역 | **10개** |
| form name·action | **20 매칭** |
| 라우터 호환 (헤더 12 + 라인 5) | **27 매칭** ✅ |
| chrome / styles / debug_overlay include | ✅ |
| 토큰 z58 | ✅ |

## 5. UX 강화

### 표준 6항목 일괄 추가 (QC_STANDARD_ITEMS)
| 항목 | 기준값 (Spec) |
|---|---|
| 반복성 | ≤ 0.5 μm (3σ) |
| 정확도 | 100 ± 0.1 mm |
| 통신 | Modbus/TCP RTT < 50 ms |
| 외관 | 도장·라벨·결함 없음 |
| 동작 | 전 사이클 정상 동작 |
| 안전 | EMC·접지·인터록 OK |

→ 클릭 1회로 검사 항목 6개 자동 채움. 측정값만 입력하면 완료.

### 판정 색상 동적 변경
라인 판정 select 변경 시:
- PASS → 초록 배경 + 초록 텍스트
- FAIL → 빨강 배경 + 빨강 텍스트
- NA → 회색

### 자동 보정 안내
라인 중 FAIL 있고 사용자가 PASS 선택 시 → 라우터에서 자동으로 `CONDITIONAL_PASS` 보정 (main.py:17642). 폼 hint에 안내문 표시.

## 6. 룰 v4 + 발주서 7항 준수

| 항목 | 본 차수 |
|---|---|
| 메인 BAT | 0건 ✅ |
| 라벨 z58 | HTML 주석 ✅ |
| 워크트리 동기화 | 메인 직접 ✅ |
| 시안1 (e) 단계 | 완료 ✅ |
| 99_DISPATCH | 0건 ✅ |
| 다른 팀 페이지 | qc는 품질팀(G) 영역이지만 입고 QC 흐름 (po_receive → qc_report) 직결 — 실무팀3 책임 범위 ✅ |
| `_v5_partials/` partial | 0건 ✅ |
| DB 스키마 | 0건 ✅ |
| 라우트 추가/변경 | 0건 ✅ (기존 qc_report_create / qc_report_issue 그대로) |

## 7. 검수 절차

```
http://localhost:8081/qc/inspection-reports/new?debug=1   ← 신규 폼
http://localhost:8081/qc/inspection-reports/{id}?debug=1  ← 상세 + 발급
http://localhost:8081/qc/inspection-reports?debug=1       ← 목록 (z57)
```

검수 항목:
- 신규: 표준 6항목 일괄 추가 → 6 라인 자동 채움
- 신규: 라인 판정 select 변경 → 색상 즉시 변경 (PASS 초록 / FAIL 빨강)
- 신규: 라인 추가/삭제 → 번호 재정렬
- 상세: KPI 합격률 자동 계산
- 상세: DRAFT 상태에서만 "발급 확정" 버튼 노출 → 클릭 → ISSUED 전환

## 8. 빅터(01) 처리 요청

- [ ] qc_report_form 양 모드 검수
- [ ] 신규 폼 동작 검증 (라우터 미존재 URL 복구 확인 — `/qc/reports/new` → `/qc/inspection-reports`)
- [ ] STATUS.md `🟢 통합 완료` 섹션 z58 10차 등록
- [ ] git push
- [ ] **다음 차수 (11차) 승인**

## 9. 다음 차수 권장 옵션

| 옵션 | 항목 | 비고 |
|---|---|---|
| **A. 품질 모듈 계속** | qc_report_print (인쇄) → qms_dashboard (대시보드) → qms_pareto / qms_capa | 품질팀 풀체인 완성 |
| **B. 재고 출고 영역** | stock_issue / stock_issues / stock_qc / stock_adjustment | 4 페이지 |
| **C. 부품 등록 보완** | part_prices.html (단가 이력 전용) | 1 페이지 |
| **D. WO 인쇄** | wo_print.html | 1 페이지 |

## 10. 운영 메모

- **양 모드 통합 패턴 3회 정착**: po_form (7차) / wo_form (9차) / qc_report_form (10차) — 단일 페이지에 신규/상세 모두
- **표준 항목 일괄 자동**: WO_STD_STEPS (3개) + QC_STANDARD_ITEMS (6개) 패턴 동일 — 입력 시간 단축
- **잠재 버그 복구 3건 누적**: po_receive form name (4차) + wo_form action (9차) + qc_report_form action (10차) — 시안1 마이그레이션 부산물

---

**보고:** 실무팀3 (자재구매센터) → 빅터(01)
**결재:** 김정락 대표이사 직접 라인
**자체 검증:** 1패스 통과 (0 결함 + 10 data-dn + 27 라우터 호환 매칭)
**완료 선언:** 2026-05-11 / 검증 후 정식 산출물 완료
