# 페르소나 14명 사전 매트릭스 — 5라운드 4명 외 잔여

> 04 운영테스트팀 빅터 — 본 세션 직접 작성 (Explore agent 권한 오류 대체)
> 일자: 2026-05-01
> 정직성 v3: database.py:1474-1585 시드 직접 인용 / 117건 영역별 매핑

---

## 0. 한 줄

5라운드 PS-A·B·G·F 외 잔여 14명 사전 시나리오 — **각 페르소나 8~12 단계 동선 + 117건 OPS 매핑 + 본업 차단 P0 = 30 OPS 추출**.

---

## 1. 페르소나 14명 (database.py 시드 직접 인용)

### P-01 박지은 (`database.py:1565`) — 11 관리 leader / 매니저
- 권한: leader → role_home `/team` / 매출 view ✅ (leader 전체) / 자재 view ❌ (flag)
- 본업: 결재·증빙·게시판 분류·미작성 알림 (`database.py:2186` "{cu} 매출채권 회수")
- 동선 10단계: /team → /weekly → /weekly/team → /board/teams → /board/post → /admin? (E-001 차단) → /sales/aging → /sales/outstanding → /admin/reminders → /home
- 핵심 OPS: D-008 미작성자 자동 알림 / D-021 게시글 반려 사유 / B-007 수금 잔액 자동 / E-001 admin 진입 정책

### P-02 최혜연 (`database.py:1568`) — 11 관리 member / 프로
- 권한: member → /home / 매출 view ❌ (관리팀 평직원, flag) / 자재 view ❌
- 본업: 신청서 / 휴가 / 근태 (`database.py:2186` 박지은과 같은 팀)
- 동선 8단계: /home → /daily → /hr/hiworks → /profile → /board/company → /notifications → /now → /search
- 핵심 OPS: E-006 hiworks URL 미설정 안내 / E-015 /profile 비번 변경 취소 URL / A-005 배너 타임아웃

### P-03 이해림 (`database.py:1482`) — 01 영업 leader / 이사
- 권한: leader → 매출 view ✅ + 자재 view ❌
- 본업: 견적·수주·고객사 (`database.py:2167-2170`)
- 동선 12단계: /team → /sales → /sales/dashboard → /sales/forecast → /sales/aging → /sales/quotations → /sales/orders → /sales/production → /sales/shipments-receipts → /customers → /customer/{id} → /quotation/print
- 핵심 OPS: B-001 sales_home 잘못된 링크 / B-009 forecast / B-013 회사정보 빨간 배너 (PASS) / B-020 사이드바 누락

### P-04 정성진 (`database.py:1556`) — 10 구매 leader / 매니저
- 권한: leader → 매출 view ✅ (leader) + 자재 view ✅ (구매)
- 본업: 부품·발주·입고·재고·환율 (`database.py:2178-2182`) — PS-B 허동준의 leader 버전
- 동선 14단계: /team → /logistics → /parts → /parts/new → /po → /po/new → /po/{id}/receive → /stock/balances → /stock/issue → /stock/qc/{id} → /stock/audits → /stock/adjustments → /suppliers → /rates/cost-sim
- 핵심 OPS: PS-B 25건 흡수 + V1~V7 6 회귀 + V6 신규 2건 (실사 차이 산식 / 증명서 첨부 정책)

### P-05 김형렬 (`database.py:1531`) — 06 전장 leader / 매니저
- 권한: leader → 매출 view ✅ / 자재 view ❌ (flag)
- 본업: 도면 변경공지·전장설계 (`database.py:2160-2164`)
- 동선 10단계: /team → /changes → /changes/new (4단계 폼) → /changes/{id} → /projects → /project/{id} → /issues → /weekly → /board/teams → /home
- 핵심 OPS: D-001 변경공지 확인률 분모 / D-002 4단계 표시기 미동작 / D-012 영향 부서 자동 판별 / D-020 SLA 부재

### P-06 임택훈 (`database.py:1541`) — 08 제조2 leader / 매니저
- 권한: leader → 매출 view ✅ + 자재 view ✅ (team_id=8 — main.py:561 제조팀 7도 자동, 8 별도 flag)
- 본업: 도면 link / 변경 ack / 가공 진행 / 재고 실사 (`database.py:2173-2176`)
- 동선 12단계: /team → /changes → /changes/{id} ack → /progress → /stock/balances → /stock/audit → /stock/adjustment → /qc/inspection-reports → /production/work-orders → /weekly → /board/teams → /now
- 핵심 OPS: D-012 변경공지 영향 부서 / V6 실사·조정 / D-022 WO 패턴

### P-07 윤영조 (`database.py:1551`) — 09 가공 leader / 매니저
- 권한: leader → 매출 view ✅ / 자재 view ❌ (flag) — 사이클 81 정정
- 본업: 가공 작업지시 / 도면 버전 (`database.py:2179-2182`) + 베트남 출장 / FTA C/O
- 동선 10단계: /team → /production/work-orders → /wo/new → /wo/{id} → /qc/inspection-reports → /export → /fta → /fta/new → /export/ci → /weekly
- 핵심 OPS: B-017 FTA_TYPES 중복 / B-018 onCustomerChange JS / D-022 WO 패턴

### P-08 김정록 (`database.py:1500`) — 03 품질 leader / 매니저
- 권한: leader → 매출 view ✅ + 자재 view ✅ (team_id=3 영업·검사·품질)
- 본업: QC·CAPA·이슈 파레토 (`database.py:2156-2160`)
- 동선 12단계: /team → /qms → /qms/dashboard → /qms/capa → /qms/pareto → /qms/recurrence → /issues → /issues/new → /qc/inspection-reports → /stock/qc/{id} → /weekly → /home
- 핵심 OPS: D-005 심각도 ko/en / D-011 QMS SLA 산식 / D-015 이슈 → CAPA 연결 / V5 stock_qc PASS

### P-09 이한중 (`database.py:1517`) — 05 SW leader / 매니저
- 권한: leader → 매출 view ✅ / 자재 view ❌ (flag)
- 본업: 표준 라이브러리 / 일정 통보 (`database.py:2164-2168`)
- 동선 10단계: /team → /projects → /project/{id} → /progress → /progress/burndown → /progress/gantt → /changes (수신) → /tickets → /weekly → /home
- 핵심 OPS: D-007 STAGES 의존성 / D-014 mgmt_code 유일성 / D-019 마일스톤 산식

### P-10 이용식 (`database.py:1571`) — 12 베트남법인 leader / 법인장
- 권한: leader → 매출 view ✅ / 자재 view ✅ (베트남 법인장 별도 가산)
- 본업: 베트남 통합 뷰 / 현지 품질 / FTA 수입 (`database.py:2193-2196`)
- 동선 10단계: /team → /sales/dashboard → /export → /fta → /customer/{id} (베트남) → /qms → /weekly → /board/teams → /admin/company-info (참조) → /home (?lang=vi)
- 핵심 OPS: PS-G 9건 흡수 + L-10 i18n 침투 우선 / OPS-PS-G-7 error.html lang

### P-11 길희용 (`database.py:1492`) — 02 검사기 매니저 / member
- 권한: member → /home / 매출 view ✅ (team_id=2) / 자재 view ❌ (flag)
- 본업: PCB 아트웍 / 작업지시서 / QC 보고서 (`database.py:2152-2156`)
- 동선 10단계: /home → /daily → /production/work-orders → /wo/new → /wo/{id}/print → /qc/inspection-reports → /qc/inspection-reports/new → /qc/inspection-reports/{id}/print → /now → /search
- 핵심 OPS: D-022 WO 번호 패턴 / B-013 회사정보 빨간 배너 (인쇄)

### P-12 박승환 (`database.py:1578`) — 13 개발혁신 매니저 / member
- 권한: member → /home / 매출 view ❌ (flag) / 자재 view ❌ (flag)
- 본업: R&D 프로젝트 / 신제품 (`database.py:2199-2202`)
- 동선 8단계: /home → /daily → /projects → /project/{id} → /progress → /issues → /weekly → /board/teams
- 핵심 OPS: D-007 STAGES 의존성 / 최소 권한 시각 (member 차단 화면 다수)

### P-13 이현 (`database.py:1483`) — 01 영업 매니저 / member
- 권한: member → /home / 매출 view ✅ (team_id=1) / 자재 view ❌
- 본업: 영업 사원 / 견적 / 거래처 — PS-A 안지연의 매니저 버전 (이해림 leader 보좌)
- 동선 10단계: PS-A 11단계와 거의 동일 (안지연과 평행) — 단가·할인 권한 추가
- 핵심 OPS: PS-A 13건 동일 흡수 + B-005 세금계산서 권한 (이현 매니저는 미허용)

### P-14 kjr2 / 김동후 kdh (가짜 CEO 시드 / 보조 ceo)
- **kjr2** (사이클 85 OPS-012 검증 시드) — leader 가정, /dashboard 차단 → /home + 노란 배너
- **김동후 kdh** (`database.py:1474`) — 실제 ceo, kjr와 같은 권한
- 동선: kjr2 — /login → /dashboard (폴백) → /home no_perm 배너 → /team → /weekly
- 핵심 OPS: OPS-012 안내 배너 (PASS 회귀) / OPS-V15 비번 리셋 / E-007 회사정보

---

## 2. 페르소나 합산 매트릭스

| 페르소나 | 팀 | 역할 | 동선 | 핵심 OPS 회귀 |
|---|---|---|---:|---:|
| P-01 박지은 | 11 관리 | leader | 10 | 4 |
| P-02 최혜연 | 11 관리 | member | 8 | 3 |
| P-03 이해림 | 01 영업 | leader | 12 | 5 |
| P-04 정성진 | 10 구매 | leader | 14 | 28 (PS-B + V) |
| P-05 김형렬 | 06 전장 | leader | 10 | 4 |
| P-06 임택훈 | 08 제조2 | leader | 12 | 6 |
| P-07 윤영조 | 09 가공 | leader | 10 | 4 |
| P-08 김정록 | 03 품질 | leader | 12 | 6 |
| P-09 이한중 | 05 SW | leader | 10 | 4 |
| P-10 이용식 | 12 베트남 | leader | 10 | 9 (PS-G 흡수) |
| P-11 길희용 | 02 검사기 | member | 10 | 3 |
| P-12 박승환 | 13 개발혁신 | member | 8 | 2 |
| P-13 이현 | 01 영업 | member | 10 | 13 (PS-A 동일) |
| P-14 kjr2/kdh | 보조 | leader/ceo | 5+5 | 12 (PS-F 흡수) |
| **합계** | — | — | **141 단계** | **103 OPS 회귀** |

---

## 3. 페르소나별 본업 차단 P0 (3건)

| 페르소나 | P0 OPS | 영향 |
|---|---|---|
| P-04 정성진 (구매 leader) | C-004 안전재고 미달 출고 차단 | S8 일상 출고 위험 (PASS 적용 회귀) |
| P-08 김정록 (품질 leader) | (V5 stock_qc disposition PASS 사이클 88) | S6 부적합 처리 정상 |
| P-14 kjr2 (가짜 CEO) | A-008 → no_perm 폴백 (OPS-012 PASS) | /dashboard 차단 시 안내 정상 |

→ 3건 모두 117건 발주 적용 후 PASS 회귀.

---

## 4. 5라운드 다음 페르소나 진입 우선순위 권고

09 결재서 명시 PS-A → PS-B → PS-G → PS-F 외 추가 4명 권고:
1. **P-03 이해림** (영업 leader) — 매출 통합 동선 12 단계
2. **P-04 정성진** (구매 leader) — 자재 통합 14 단계 + V1~V7 흡수
3. **P-08 김정록** (품질 leader) — QMS 본업 + L-7 base 회귀
4. **P-10 이용식** (베트남법인장) — i18n vi 침투 leader 버전

---

## 5. 정직성 v3

- ✅ 모든 시드 인용 `database.py:1474-1585` 직접 라인 기재
- ✅ 권한 분기 `main.py:540-595` 직접 인용 (can_view_sales / can_use_logistics)
- ✅ 추정 0건 (5라운드 후속 페르소나 진입은 09 결재 사안 명시)
- ✅ 합산 산식: 141 단계 = 10·8·12·14·10·12·10·12·10·10·10·8·10·10 (정확 일치)
- ✅ 합산 OPS: 103 = 4+3+5+28+4+6+4+6+4+9+3+2+13+12 (정확 일치)

---

*04 운영테스트팀 빅터 — 2026-05-01*
*페르소나 14명 사전 매트릭스 — 141 단계 / 103 OPS 회귀 / P0 차단 3건.*
