# 📤 실무팀3 → 빅터(01) 핸드오프 — v14 (stock_issue / E 재고 그룹 시작)

> **세션:** 실무팀3 (자재구매센터)
> **워크트리:** `cranky-shtern-789fa2` — 메인 폴더 직접 작업 모드
> **기준일:** 2026-05-11
> **시스템 버전:** v5H226z58
> **차수:** 14차 (재고 출고 등록 — E 그룹 시작)

---

## 1. 배경

빅터 추천 §14차 = **A. stock_issue** — po_receive(입고) 다음 자연 흐름. E 재고 그룹 시작 (출고·실사·조정 미완 6 페이지 중 첫 번째).

## 2. 산출물 (1 파일)

### `stock_issue.html` — 자재 출고 등록 폼

#### 3 섹션 폼
1. **자재 선택** — select + 자재 정보 카드 (자동 표시)
2. **출고 정보** — 수량 + 일자 + 출고 후 재고 미리보기 + 사유(6종) + 단가 + 위치/LOT
3. **귀속 (선택)** — 프로젝트(관리코드) + 고객사 + 비고

#### UX 핵심 — 자재 정보 자동 카드
자재 select 변경 → JS로 즉시 표시:
- **현재 재고** (안전재고 50% 미만 = 빨강 / 안전재고 미만 = 황 / 정상 = 검정)
- **안전 재고**
- **표준 단가** (단가 input에 자동 채움)
- 자재 카드 표시 (선택 전엔 숨김)

#### UX 핵심 — 출고 후 재고 미리보기
수량 입력 → JS로 즉시 계산:
- 현재 재고 - 출고 수량 = 예상 잔여 재고
- 초과 입력 시: 수량 input 빨간 강조 + 미리보기 카드 "재고 부족"
- 안전재고 미만 예상 시: 황색 경고
- 사이드 요약: 출고 금액 (수량 × 단가) 자동 계산

#### 출고 사유 6종 select
- 현장 출고 (기본)
- 생산 투입
- 외주 지급
- 수리/교체
- 시료/샘플
- 기타

## 3. 라우터 호환성

| 위치 | 라우터 (main.py:12127) | stock_issue.html |
|---|---|---|
| action | POST `/stock/issue` | 일치 ✅ |
| 필수 | part_id, quantity | 일치 (required) ✅ |
| 선택 | project_id, customer_id, unit_price, reason, location, occurred_at, note | 일치 ✅ |
| 라우터 fallback | qty ≤ 0 → `?error=qty` / 비유효 → `?error=invalid` | URL ?error= 배너 표시 ✅ |

## 4. 자체 검증 결과 (1패스)

| 항목 | 결과 |
|---|---|
| amber-grad / knk-red 잔존 | **0건** ✅ |
| data-dn / name / action 매칭 | **19 매칭** ✅ |
| parts 변수 7컬럼 활용 | id / part_no / part_name / unit / stock_qty / std_price / safety_stock |
| projects / customers / default_part_id 변수 | ✅ |
| JS 동작 (onPartChange / onQtyChange) | ✅ |
| 토큰 z58 | ✅ |

## 5. 룰 v4 + 발주서 7항 준수

| 항목 | 본 차수 |
|---|---|
| 메인 BAT | 0건 ✅ |
| 라벨 z58 | HTML 주석 ✅ |
| 워크트리 동기화 | 메인 직접 ✅ |
| 시안1 (e) 단계 | 완료 ✅ |
| 99_DISPATCH | 0건 ✅ |
| 다른 팀 페이지 | 0건 ✅ (재고 출고는 자재구매센터 영역) |
| `_v5_partials/` partial | 0건 ✅ |
| DB 스키마 | 0건 ✅ |
| 라우트 추가/변경 | 0건 ✅ |
| 위하고 직접 연동 | 0건 ✅ |

## 6. 검수 절차

```
http://localhost:8081/stock/issue?debug=1                       ← 신규 출고
http://localhost:8081/stock/issue?part_id={자재id}&debug=1      ← 자재 미리 선택
http://localhost:8081/stock/issue?error=qty&debug=1             ← 에러 배너 테스트
```

검수 항목:
- 자재 select 변경 → 자재 정보 카드 즉시 표시
- 안전재고 < 50% 자재 선택 → 현재 재고가 빨강으로 표시
- 수량 입력 → 출고 후 재고 미리보기 즉시 갱신
- 출고 수량 > 현재 재고 → 빨강 강조 + "재고 부족" 메시지
- 사이드 요약 (자재명·수량·금액·상태) 동기 갱신
- 출고 등록 후 `/stock/movements?success={이동번호}` 리디렉션

## 7. 빅터(01) 처리 요청

- [ ] stock_issue 검수 (자재 변경 + 수량 입력 동적 동작)
- [ ] 출고 등록 후 재고 차감 정합성 확인
- [ ] STATUS.md `🟢 통합 완료` z58 14차 등록
- [ ] git push
- [ ] **다음 차수 (15차) 승인**

## 8. E 재고 그룹 진행 현황

| 페이지 | 상태 | 차수 |
|---|---|---|
| stock_balances | 🟢 | z57 |
| stock_movements | 🟢 | z57 |
| stock_abc | 🟢 | z57 |
| stock_safety | 🟢 | z57 |
| stock_turnover | 🟢 | z57 |
| stock_reorder | 🟢 | z57 |
| stock_receipts | 🟢 | z57 |
| **stock_issue** | **🟢** | **z58 (14차)** |
| stock_issues (출고 이력) | 🔘 | 다음 차수 |
| stock_qc | 🔘 | |
| stock_adjustment | 🔘 | |
| stock_audit | 🔘 | |
| stock_fifo | 🔘 | |

→ E 그룹 13 페이지 중 **8 완료** (62%)

## 9. 다음 차수 권장 옵션

| 옵션 | 항목 | 분량 | 비고 |
|---|---|---|---|
| **A. stock_issues** | 출고 이력 (목록) | 1 페이지 | stock_issue 대칭 ⭐ |
| **B. stock_adjustment** | 재고 조정 | 1 페이지 | 실사 차이 보정 |
| **C. stock_audit** | 재고 실사 | 1 페이지 | 실사 입력 |
| **D. 품질 BI** | qms_dashboard | 1 페이지 | 다른 영역 |

빅터 추천: **A. stock_issues** (출고 이력 목록) — stock_receipts(입고 이력 z57)와 대칭. 1 페이지 단독.

## 10. 운영 메모

- **JS 동적 미리보기 패턴**: po_receive (수량 입력 자동 재계산), part_form (datalist), **stock_issue (자재 정보 + 출고 후 재고)** — 사용자 입력 직후 결과 즉시 표시
- **안전재고 색상 3단계**: 정상(검정) / 미만(황) / 50%미만(빨강) — 시각 우선순위 일관

---

**보고:** 실무팀3 (자재구매센터) → 빅터(01)
**결재:** 김정락 대표이사 직접 라인
**자체 검증:** 1패스 통과 (0 결함 + 19 매칭)
**완료 선언:** 2026-05-11 / 검증 후 정식 산출물 완료
**E 그룹 시작** — 14차 마감
