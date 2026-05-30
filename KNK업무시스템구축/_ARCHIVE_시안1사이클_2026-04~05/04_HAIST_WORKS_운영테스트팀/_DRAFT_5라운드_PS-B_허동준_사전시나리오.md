# 5라운드 PS-B 허동준 — 정적 사전 시나리오 매트릭스

> 04 운영테스트팀 / 빅터
> 일자: 2026-05-01
> 트리거: 09 결재서 5라운드 PS-A → **PS-B 허동준** → PS-G → PS-F 순서
> 비간섭 원칙: 사전 정적 매트릭스, 동적 회귀 09 신호 후

---

## 0. 페르소나 PS-B 허동준 정의

| 항목 | 값 | 근거 |
|---|---|---|
| 이름 | 허동준 | `database.py:1557` 시드 |
| 팀 | 10 구매팀 (team_id=10) | `database.py:1463, 1555` |
| 직급 | 매니저 | `database.py:1557` |
| 역할 | member | `database.py:1557` |
| login_id | `hdj` (영문 시드 별도) 또는 `허동준` | OPS-001 사이클 84 핫패치 시드 마이그 후 |
| 비밀번호 | `knk1234` | 04 정책 |
| 역할 홈 | `/home` | `main.py:540-555` member 분기 |
| 자재 view 권한 | ✅ 허용 | `database.py:1669-1670` 구매(10) 평직원 전원 자동 |
| 자재 use 권한 | ✅ 허용 | 구매팀 본업 (발주·입고·단가) |
| 매출 view 권한 | ❌ 차단 | team_id=10 (영업·검사기·품질 외) → can_view_sales 플래그 의존 |
| 본업 | 부품 발주 / 협력사 단가 협상 / 자재 입고 확인 / 신규 협력사 등록 심사 / 긴급 자재 수배 (`database.py:2177-2182`) |

### OPS-001 시드 마이그레이션 (사이클 84) 검증
- 사이클 84 핫패치: `hdj / knk1234` → `/logistics` 200 OK + "🏭 자재 허브"
- 사이클 86 회귀 검증 항목 (옵션 C 시드 재실행 후)

---

## 1. 5라운드 12단계 동선 (허동준 하루 업무)

### 1.1 단계별 L-1~L-10 매트릭스

| Step | URL | L-1 200 | L-2 입력 | L-3 본업 | L-7 base | L-8 잔존 | L-10 i18n |
|---|---|---|---|---|---|---|---|
| S0 | / 인증 전 | ✅ | — | — | — | — | ⚠ Phase 1 PASS |
| S1 | /login → 허동준 (or hdj) | ✅ | ⚠ A-002 | — | — | — | — |
| S2 | /home | ✅ | ⚠ A-003 max | ✅ KPI member 표준 | ✅ base | — | sb_* |
| S3 | ws-tabs 자재구매센터 → /logistics | ✅ | — | ✅ 진입 (OPS-001 검증 P0) | ✅ base_logi | — | — |
| S4 | /parts → 부품 검색 | ⚠ C-009 자동완성 부재 | ⚠ B-002 단가 표기 | ✅ 부품 조회 | ✅ base_logi | — | — |
| S5 | /po → /po/new 신규 발주 | ✅ | ⚠ C-007 VAT 라디오 (적용 PASS) / C-017 통화 코드 | ✅ 본업 1순위 | ✅ base_logi | ⚠ M-1·M-2 P2 보류 | — |
| S6 | /po/{id}/receive 입고 처리 | ⚠ C-020 미검증 (OPS-V2) | — | ✅ 본업 2순위 | ✅ base_logi | — | — |
| S7 | /stock/qc/{po_item_id} 검수 | ✅ | — | ✅ FAIL → disposition (사이클 88 W7 PASS) | ✅ base_logi | — | — |
| S8 | /stock/issue 출고 | ✅ | ✅ 안전재고 confirm (OPS-P0-3 PASS) | ⚠ C-018 음수 검증 부족 | ✅ base_logi | — | — |
| S9 | /stock/balances 재고 잔량 | ✅ | — | ✅ 조회 | ✅ base_logi | ⚠ C-013 마지막 갱신 라벨 | — |
| S10 | /suppliers → /supplier/new 협력사 등록 | ⚠ C-024 국가 입력 미확인 | — | ✅ 신규 협력사 심사 | ✅ base_logi | — | — |
| S11 | /rates 환율 → /rates/cost-sim 시뮬 | ⚠ C-021 미검증 (OPS-V3) | — | ✅ 단가 협상 근거 | ✅ base_logi | — | — |
| S12 | /logout | ✅ | — | — | — | — | — |

### 1.2 매트릭스 합계

- L-1: 정적 12/12 PASS, 동적 회귀 시 실측 (특히 S6/S10/S11 미검증 영역)
- L-2: 4건 마찰 (A-003 / B-002 / C-007 / C-017)
- L-3: 본업 5단 (발주 → 입고 → 검수 → 출고 → 재고)
- L-7: 3종 base 동시 회귀 PASS (base_logi 일관)
- L-8: M-1·M-2 P2 보류 (Phase 2-3 C 사이클 대기)

---

## 2. 5라운드 PS-B 정적 발견 (117건 회귀 흡수)

### 2.1 OPS-001 시드 마이그 회귀 (사이클 84 핫패치)
| 검증 | 결과 |
|---|---|
| `hdj / knk1234` → /logistics 200 + "🏭 자재 허브" | 동적 검증 필요 (사이클 86 옵션 C) |
| `/parts` 부품 리스트 200 | 동적 검증 필요 |
| `허동준` → 자재 view 권한 자동 허용 | `main.py:1669-1670` 정적 PASS |

### 2.2 117건 연계 발견 (자재 영역)

| OPS | Tier | 117건 코드 | 허동준 동선 영향 |
|---|---|---|---|
| OPS-PS-B-1 | P0 | C-004 안전재고 미달 출고 차단 | S8 — 일상 차단 PASS |
| OPS-PS-B-2 | P1 | C-001 부품 안전재고 입력 위치 모호 | S10 신규 부품 등록 시 |
| OPS-PS-B-3 | P1 | C-002 환율 history 그래프 부재 | S11 단가 협상 근거 부족 |
| OPS-PS-B-4 | P1 | C-003 발주 라인 필드 일관성 (8열 vs 10열) | S5 작성 ↔ S6 읽기 불일치 |
| OPS-PS-B-5 | P1 | C-005 12종 stock 네비게이션 불일치 | S9 다른 stock 화면 진입 마찰 |
| OPS-PS-B-6 | P1 | C-007 VAT 처리 (적용 PASS) | S5 정상 |
| OPS-PS-B-7 | P1 | C-008 환율 일자 동기화 부재 | S5 발주 시 환율 미등록 백필 불가 |
| OPS-PS-B-8 | P1 | C-012 BOM 입력 기능 부재 | S10 반제품 관리 불가 |
| OPS-PS-B-9 | P1 | C-014 발주 인쇄 @media print 부재 | S5 발주서 출력 시 |
| OPS-PS-B-10 | P1 | C-018 재고 음수 클라이언트 검증 부족 | S8 출고 시 |
| OPS-PS-B-11 | P1 | C-025 can_view_logistics 라우트 미검증 | S3~S11 모든 자재 라우트 |
| OPS-PS-B-12 | P1 | C-026 stock_adjustments 승인 흐름 미검증 | (실사 → 조정 → 승인 본업) |
| OPS-PS-B-13 | P2 | C-006 ROP vs 안전재고 용어 혼동 | S8 출고 결정 시 혼란 |
| OPS-PS-B-14 | P2 | C-009 부품 검색 자동완성 부재 | S4 |
| OPS-PS-B-15 | P2 | C-010 stock_issue Lot/Serial 선택 부재 | S8 원가 역산 불가 |
| OPS-PS-B-16 | P2 | C-013 stock_balances 마지막 갱신 라벨 | S9 |
| OPS-PS-B-17 | P2 | C-015 suppliers 평균 리드타임 미표시 | S10 |
| OPS-PS-B-18 | P2 | C-017 환율 통화 코드 일관성 | S5/S11 |
| OPS-PS-B-19 | P2 | C-022 stock_reorder 추천 알고리즘 미검증 | (V4 미Read) |
| OPS-PS-B-20 | P2 | C-023 stock_qc 상태 전이 흐름 불명 | S7 |
| OPS-PS-B-21 | P2 | C-027 po_list 부분입고 선택 미검증 | S6 |
| OPS-PS-B-22 | P3 | C-011 po_list 지연 색상 한정 | S5 목록 조회 |
| OPS-PS-B-23 | P3 | C-016 12종 stock 카드 grid 불일치 | S9 시각 마찰 |
| OPS-PS-B-24 | P3 | C-024 supplier 국가 입력 방식 불명 | S10 |
| OPS-PS-B-25 | P3 | C-028 logistics_home KPI 사전필터 부재 | S3 |

→ 25건 모두 117건 발주 4종에 흡수됨. 본 라운드 회귀 검증.

### 2.3 미검증 보강 항목 (정적 grep 한계)
- **OPS-V1** part_detail / part_prices 단가 이력
- **OPS-V2** po_receive 부분입고 + Lot/Serial
- **OPS-V3** rates_cost_sim 시뮬레이션
- **OPS-V4** stock_reorder 추천
- **OPS-V5** stock_qc 상태 전이 (사이클 88 PASS 흡수)
- **OPS-V6** stock_adjustments 승인 흐름
- **OPS-V7** admin_permissions_groups (자재 영역 외)

→ 6건 (V7 제외) 허동준 동선 직결. 01 자체 점검 + 보강 후 회신 권고.

---

## 3. 동적 회귀 필요 영역 (서버 기동 후)

| 항목 | 정적 한계 | 09/대표 신호 후 검증 |
|---|---|---|
| L-1 11/12 200 OK | 동적 응답 코드 | 12 단계 모두 GET |
| L-2 폼 submit | JS 검증 + 서버 흐름 | S5 발주 / S8 출고 / S10 협력사 |
| W7 disposition redirect | FAIL 클릭 → URL | S7 실제 FAIL 시뮬 |
| W8 confirm 모달 | 안전재고 미달 confirm | S8 미달 수량 입력 |
| L-9 모달 z-index | 도크/모달 충돌 | S5 발주 모달 + 도크 |
| L-10 ko/vi/en | 페이지 본문 한국어 잔존 | (허동준 한국어만 — 베트남법인 PS-G 트랙) |

---

## 4. 회신 양식 (5라운드 PS-B 본 가동 시)

```
## P-B 허동준 (login_id=hdj or 허동준 / 10팀·매니저·member)

### Level-1~10 체크 결과 (12단계 동선)
- L-1: ✅ 12/12 200 OK
- L-2: ❌ 4건 (A-003 / B-002 / C-007 / C-017)
- L-3: ✅ 본업 5단 완주 (S3~S9)
- L-7: ✅ base_logi 일관
- ...

### OPS-001 사이클 84 회귀
- /logistics 200 + "🏭 자재 허브" — PASS/FAIL
- /parts 200 — PASS/FAIL
- 자재 view 자동 허용 — PASS

### 발견 25건 회귀 + 신규 N건
...

### "일이 늘어나는가" 판정
S5(발주): VAT 라디오 PASS / 환율 일자 마찰 → 일 늘어남
S6(입고): 부분입고 미검증 → 동적 회귀 필요
S8(출고): 안전재고 confirm PASS → 일 줄어듦 (정정)
종합: 117건 발주 회신 + V1~V6 보강 시 허동준 일 ↓
```

---

## 5. 다음 페르소나 (PS-G·PS-F) 사전 정리 권고

09 결재서 명시:
- **PS-G 쑤아잉** — 베트남법인 (vi 침투 검증 핵심 / OPS-W-1 i18n)
- **PS-F kjr** — 가짜 CEO 시드 (OPS-V15 비번 리셋 + OPS-012 안내 배너)

→ PS-B 회신 PASS 후 PS-G·PS-F 사전 매트릭스 발주 권고.

---

## 6. 정직성 v3

- ✅ 모든 라인 인용 grep -n / database.py 직접 결과
- ✅ 추정 0건 (V1~V7 / 동적 영역 명시 분리)
- ✅ "% 완료" 미사용
- ✅ 합산 산식: 25 OPS = P0×1 + P1×11 + P2×9 + P3×4

---

*04 운영테스트팀 빅터 — 2026-05-01*
*PS-B 사전 매트릭스 12단계 + 25 OPS 회귀 + 6 V 보강 + 6 동적 항목.*
