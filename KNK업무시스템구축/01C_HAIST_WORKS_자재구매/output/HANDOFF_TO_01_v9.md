# 📤 실무팀3 → 빅터(01) 핸드오프 — v9 (wo_form.html 시안1 단독)

> **세션:** 실무팀3 (자재구매센터)
> **워크트리:** `cranky-shtern-789fa2` — 메인 폴더 직접 작업 모드
> **기준일:** 2026-05-11
> **시스템 버전:** v5H226z58
> **차수:** 9차 (작업지시 풀체인 보완)

---

## 1. 배경

z58 시리즈 종료(5~8차) 후 자재구매센터 책임 영역 중 자재출고·BOM 직결 페이지 = 작업지시. **wo_list.html은 z57 완료**(7차) 상태였으나 **wo_form.html이 누락**으로 풀체인 막힘.

빅터 추천 §9차 = **wo_form.html 시안1 z58 전면 재작성** (단독 차수).

## 2. 산출물 (1 파일)

### `wo_form.html` — 신규 폼 + 상세 조회 단일 페이지 통합

#### 모드 분기 (`is_view = wo is not none`)

**신규 모드** (wo=None / GET `/production/work-orders/new`)
- 4 섹션 폼:
  1. 기본정보 — 수주 / 프로젝트 / 가공 부품 / 가공 수량
  2. 일정·담당자 — 담당자 / 담당자명 / 계획 시작·종료일
  3. 가공 사양 — specifications + remarks (textarea)
  4. 공정 단계 — line_step / line_duration / line_progress / line_worker / line_remarks (getlist 라인) + **표준 공정 일괄 추가** 버튼
- 사이드 카드 2종: 발행 가이드 / 표준 공정 표시
- JS: addLine / delLine / renumber / loadStdSteps (WO_STD_STEPS 자동 채움)

**상세 모드** (wo 객체 / GET `/production/work-orders/{wo_id}`)
- KPI 4종: 생산 수량 / 평균 진행률 / 계획 기간 / 총 공수 (분→시간 환산)
- 정보 카드 — WO 번호 / 수주 / 프로젝트 / 가공 부품 / 담당자 / 작성자 / 가공 사양 / 비고
- 공정 표 — line_no / step_name / duration / 진행률 막대 / 작업자 / 비고
- 사이드 — 요약 def + 상태 가이드 (5종)
- 발행 액션 (DRAFT → RELEASED) — `POST /production/work-orders/{wo_id}/release`

## 3. 라우터 호환성 (form name 정확 정합)

| 위치 | 라우터 (main.py:17838 wo_create) | wo_form.html |
|---|---|---|
| 헤더 | order_id / project_id / part_id / qty / assigned_to / assigned_name / planned_start / planned_end / specifications / remarks | 동일 (10개) ✅ |
| 라인 getlist | line_step / line_duration / line_progress / line_worker / line_remarks | 동일 (5개) ✅ |
| 신규 action | POST `/production/work-orders` | 일치 ✅ |
| 발행 action | POST `/production/work-orders/{wo_id}/release` | 일치 ✅ |

⚠️ **잠재 버그 복구**: 기존 wo_form.html의 action `/production/work-orders/new` 는 라우터 미존재 (POST 라우터는 `/production/work-orders` 단일). z58에서 정정.

## 4. 자체 검증 결과 (1패스)

| 항목 | 결과 |
|---|---|
| amber-grad / knk-red 잔존 | **0건** ✅ |
| data-dn 영역 | **11개** (head/kpi/info/steps/side(상세)·basic/schedule/spec/steps/side/action(신규)) |
| form name·action 정합 | name= + action= **18 매칭** ✅ |
| 라우터 호환 (POST URL + getlist 키) | 일치 ✅ |
| chrome / styles / debug_overlay include | ✅ |
| 토큰 z58 | ✅ |

## 5. 룰 v4 + 발주서 7항 준수

| 항목 | 본 차수 |
|---|---|
| 메인 BAT | 0건 ✅ |
| 라벨 v5H226z58 | HTML 주석 ✅ |
| 워크트리 동기화 | 메인 직접 ✅ |
| 시안1 (e) 단계 | 완료 ✅ |
| 99_DISPATCH | 0건 ✅ |
| 다른 팀 페이지 | wo는 가공팀(F 작업지시) 영역이지만 자재출고·BOM 직결 — 실무팀3 책임 범위 ✅ |
| `_v5_partials/` partial | 0건 ✅ |
| DB 스키마 변경 | 0건 ✅ |
| 라우트 추가/변경 | 0건 ✅ (기존 wo_create / wo_release 그대로) |

## 6. 매뉴얼 §5.2 작업지시서 매핑

| 매뉴얼 | KNK 자체 (IP 안전) |
|---|---|
| 생산(작업)지시서 | 작업지시 (Work Order) |
| 발행 | 발행 (DRAFT → RELEASED) |
| 자재 출고 처리 | 자재출고 (stock_movements.kind=OUT, kind_detail=OUT_PRODUCTION) |
| 생산품 입고 처리 | 생산입고 (kind_detail=IN_PRODUCTION) |
| BOM 자동 산출 | z56 bom_items + qty_per_parent + loss_rate (적용 위임) |

## 7. 검수 절차

```
http://localhost:8081/production/work-orders/new?debug=1   ← 신규 폼
http://localhost:8081/production/work-orders/{id}?debug=1  ← 상세 + 발행
http://localhost:8081/production/work-orders?debug=1       ← 목록 (z57)
```

검수 항목:
- 신규: 표준 공정 일괄 추가 버튼 → 절삭/연마/검수 자동 채움
- 신규: 라인 추가/삭제 → 번호 재정렬
- 상세: 진행률 막대 + 평균 진행률 KPI 일치
- 상세: DRAFT 상태에서만 "발행" 버튼 노출 → 클릭 → RELEASED 전환

## 8. 빅터(01) 처리 요청

- [ ] wo_form.html 검수 (신규 + 상세 양 모드)
- [ ] STATUS.md `🟢 통합 완료` 섹션 z58 9차 등록
- [ ] git push
- [ ] **다음 차수 — 10차 (wo_print 또는 다른 영역) 승인**

## 9. 다음 차수 권장 옵션

| 옵션 | 차수 | 항목 |
|---|---|---|
| **A. 작업지시 풀체인 완성** | 10차 | wo_print.html (인쇄 전용) |
| **B. 품질 모듈 확장** | 10~12차 | qc_report_form / qc_report_print / qms_dashboard / qms_pareto / qms_capa |
| **C. 재고 출고 영역** | 10~11차 | stock_issue / stock_issues / stock_qc / stock_adjustment |
| **D. 환율·원가 모듈** | 별도 결재 | rates_dashboard / rates_history / rates_alerts / rates_cost_sim |

## 10. 운영 메모

- **단일 페이지 양 모드 패턴**: po_form 이후 두 번째 적용 (wo_form). 신규/상세 통합 → 라우터 단순화 + UX 일관성
- **표준 공정 자동화**: WO_STD_STEPS (절삭 60분 / 연마 30분 / 검수 15분) JS 일괄 적용 → 입력 시간 단축
- **chip-wo 5상태**: 매뉴얼 §5.2 단계 (작성/발행/진행/완료/취소) 정확 매핑

---

**보고:** 실무팀3 (자재구매센터) → 빅터(01)
**결재:** 김정락 대표이사 직접 라인
**자체 검증:** 1패스 통과 (0 결함 + 11 data-dn + 라우터 form name 정합)
**완료 선언:** 2026-05-11 / 검증 후 정식 산출물 완료
