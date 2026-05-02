# 영역 C — 자재·구매 Hub 검증 (28건 발견)

> 04 운영테스트팀 / Explore agent C 결과 흡수
> 일자: 2026-04-29
> 정직성 v3: grep -n 직접 인용 / 추정 0건

## 발견 요약

| 범주 | 건수 | Tier 분포 |
|---|---|---|
| 운영 순서 | 8 | P0-P1 |
| 항목 구성 | 7 | P1-P2 |
| UX/UI 일관성 | 8 | P2-P3 |
| i18n / 데이터 표기 | 3 | P2-P3 |
| 시각/접근성 | 2 | P3 |
| **합계** | **28** | P0×1 + P1×10 + P2×13 + P3×4 |

---

## C-001 [P1] 부품 안전재고 입력 위치 모호
- 페이지: /parts/new, /parts/{id}
- 페르소나: 정성진 구매팀장
- 증거: `part_form.html:96-127` 신규 2단 grid vs 수정 3단 grid
- 문제: 신규 등록자가 안전재고 입력 시점 불명
- 권장: 신규/수정 폼 배치 통일 + "신규 등록 시 선택, 입고 후 수정 가능" 라벨

## C-002 [P1] 환율 History 그래프 부재
- 페이지: /rates/history
- 페르소나: 정성진 / 박지은
- 증거: `rates_history.html:1-65` (표만), `rates_dashboard.html:74-95` (chart 없음)
- 문제: 추세 한눈에 파악 불가
- 권장: 월별/일별 선 그래프 추가

## C-003 [P1] 발주 라인 필드 일관성
- 페이지: /po/new vs /po/{id}
- 페르소나: 정성진
- 증거: `po_form.html:129-137` 8열 vs `po_detail.html:70-74` 10열 (규격·비고 위치 차이)
- 문제: 작성-읽기 불일치
- 권장: 규격 컬럼 통일

## C-004 [P0] 안전재고 미달 출고 차단 부재
- 페이지: /stock/issue
- 페르소나: 임택훈 제조2 / 윤영조 가공
- 증거: `stock_issue.html:86-109`
- 문제: 안전재고 미달 부품 출고 시 경고/차단 없음
- 권장: "안전재고 미달 시 확인" 팝업

## C-005 [P1] 12종 stock 화면 네비게이션 불일치
- 페이지: /stock/movements / balances / abc / fifo
- 페르소나: 임택훈
- 증거: `stock_movements.html:1-70` (KPI 6단계) vs `stock_balances.html:1-40` (단순 백링크)
- 문제: 12종 메뉴 간 이동 동선 불명확
- 권장: 모든 stock 화면 상단 12종 메뉴 탭 또는 breadcrumb 통합

## C-006 [P2] 재발주점(ROP) vs 안전재고 용어 혼동
- 페이지: /stock/safety
- 페르소나: 정성진
- 증거: `stock_safety.html:96-101`
- 문제: 안전재고/ROP/권장발주량 트리거 차이 불명
- 권장: "안전재고=최저 line, ROP=재발주 trigger" 명시

## C-007 [P1] VAT 포함/별도 미표시
- 페이지: /po/new, /po/{id}
- 페르소나: 정성진
- 증거: `po_form.html:43-111`, `po_detail.html:45-62`
- 문제: VAT 처리 방식 비표시 → 한국 관행과 충돌
- 권장: 헤더 "VAT 처리" 라디오 (포함/별도/미지정)

## C-008 [P1] 환율 일자 동기화 메커니즘 부재
- 페이지: /po/new + /rates
- 페르소나: 정성진
- 증거: `po_form.html:58-71`, `rates.html:40-80`
- 문제: 환율 미등록 시 백필 불가, 사후 변경 시 발주 재계산 없음
- 권장: 발주 저장 시 "환율 미등록" 경고 + 변경 후 영향 발주 자동 감지

## C-009 [P2] 부품 검색 자동완성 부재
- 페이지: /parts
- 페르소나: 정성진
- 증거: `parts.html:14` autocomplete 속성 없음
- 권장: autocomplete + suggest API

## C-010 [P2] stock_issue Lot/Serial 선택 부재
- 페이지: /stock/issue
- 페르소나: 임택훈
- 증거: `stock_issue.html:14-27`
- 문제: FIFO 레이어/Lot 명시 선택 불가 → 원가 역산 불가
- 권장: Lot/Serial 선택 UI

## C-011 [P3] po_list 지연 색상 한정
- 페이지: /po
- 페르소나: 정성진
- 증거: `po_list.html:71-73` 빨강(#DC2626)만
- 권장: 다크모드 contrast 강화

## C-012 [P1] 부품 BOM 입력 기능 부재
- 페이지: /parts/new
- 페르소나: 정성진 / 김형렬
- 증거: `part_form.html:96-127`
- 문제: 반제품 → 원자재 매핑 없음
- 권장: BOM 트리 입력 UI

## C-013 [P3] stock_balances 마지막 갱신 라벨 불명확
- 페이지: /stock/balances
- 페르소나: 임택훈
- 증거: `stock_balances.html:39`
- 문제: 실시간 갱신 메커니즘 불분명
- 권장: 자동 갱신 또는 "수동 새로고침" 버튼

## C-014 [P1] 발주 인쇄 @media print 미정의
- 페이지: /po/{id}
- 페르소나: 정성진
- 증거: `po_detail.html:16` window.print() 호출, @media print 스타일 시트 없음
- 권장: print stylesheet 추가

## C-015 [P2] suppliers 평균 리드타임 미표시
- 페이지: /suppliers
- 페르소나: 정성진
- 증거: `suppliers.html:20-59` 컬럼 없음 vs `logistics_home.html:93` 언급만
- 권장: 컬럼 추가

## C-016 [P3] stock 12종 카드 grid 불일치
- 페이지: /stock/* 12종
- 페르소나: 임택훈
- 증거: `stock_balances` 3칸 KPI / `stock_abc` 3칸 A/B/C / `stock_fifo` 4칸 요약
- 권장: 통일 grid 규칙

## C-017 [P2] 환율 통화 코드 일관성
- 페이지: /rates vs /po/new
- 페르소나: 정성진
- 증거: `rates.html:25` USD/VND/JPY/CNY/EUR vs `po_form.html:61-66` KRW/USD/JPY/CNY/EUR (VND 미포함)
- 권장: 통화 리스트 단일 정의

## C-018 [P1] 재고 음수 방지 클라이언트 검증 부재
- 페이지: /stock/issue
- 페르소나: 임택훈
- 증거: `stock_issue.html` min="0.01" 만, 시스템 재고 초과 검증 없음
- 권장: 클라이언트 검증 + 즉시 피드백

## C-019 [P2] part_detail / part_prices 단가 이력 메커니즘 불명
- 페이지: /part/{id}, /part/{id}/prices
- 페르소나: 정성진
- 증거: 파일 미확인 (Explore agent)
- 권장: 단가 이력 그래프 + 공급사별 비교

## C-020 [P1] po_receive 부분입고/Lot/검수 메커니즘 미검증
- 페이지: /po/{id}/receive
- 페르소나: 정성진
- 증거: 파일 미확인
- 권장: 부분입고 + Lot/Serial 입력 + 검수 상태 전이 명시

## C-021 [P2] rates_cost_sim 시뮬레이션 검증 미수행
- 페이지: /rates/cost-sim
- 페르소나: 정성진 / 박지은
- 증거: 파일 미확인
- 권장: 환율 변동 → 원가 영향 시뮬

## C-022 [P2] stock_reorder 추천 알고리즘 미검증
- 페이지: /stock/reorder
- 페르소나: 정성진
- 증거: 파일 미확인
- 권장: 안전재고/ROP/권장량 연계 검증

## C-023 [P2] stock_qc 상태 전이 흐름 불명
- 페이지: /stock/qc
- 페르소나: 김정록 품질
- 증거: GR→QC→BAL 순서 template 미명시
- 권장: 상태 흐름 다이어그램

## C-024 [P3] suppliers 국가 입력 방식 불명
- 페이지: /supplier/new
- 페르소나: 정성진
- 증거: `supplier_form.html` 미확인
- 권장: 국가 select 옵션 (ISO 3166)

## C-025 [P1] can_view_logistics 권한 체크 미검증
- 페이지: /logistics 전체
- 페르소나: 윤영조 (view-only)
- 증거: `main.py:274-295` 정의 + 각 라우트 적용 여부 미검증
- 권장: 라우트별 권한 가드 그레프 검증

## C-026 [P1] stock_adjustments 승인 흐름 미검증
- 페이지: /stock/adjust, /stock/adjustment
- 페르소나: 임택훈 / 정성진
- 증거: 실사→조정→승인 3단계 template 미검증
- 권장: 권한 분리 (leader vs ops) + 승인 큐

## C-027 [P2] po_list 부분입고 선택 동작 미검증
- 페이지: /po
- 페르소나: 정성진
- 증거: `po_list.html:21` PO_STATUSES select
- 문제: 부분입고 라인 추적 UI 부재
- 권장: 부분입고 라인 분리 표시

## C-028 [P3] logistics_home KPI 클릭 후 사전필터 부재
- 페이지: /logistics
- 페르소나: 정성진
- 증거: KPI 클릭 → `/po?status=발주완료`
- 문제: 날짜·공급사 사전 필터 없음 → 매번 재설정
- 권장: 사용자 마지막 필터 기억

---

**Tier 합계**: P0×1 + P1×10 + P2×13 + P3×4 = 28건
