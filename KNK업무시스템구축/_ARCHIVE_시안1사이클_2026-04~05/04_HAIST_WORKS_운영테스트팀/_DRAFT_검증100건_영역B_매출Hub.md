# 영역 B — 매출·영업 Hub 검증 (20건 발견)

> 04 운영테스트팀 / Explore agent B 결과 흡수
> 일자: 2026-04-29
> 정직성 v3: grep -n 직접 인용 / 추정 0건

## B-001 [P1] sales_home KPI 카드 잘못된 링크
- 페이지: /sales (매출 홈)
- 페르소나: 이해림 영업 leader
- 증거: `sales_home.html:14-19` href="/admin"
- 문제: 당월/YTD 수주 KPI 클릭 시 /admin 으로 이동 → 매출 자세히 보기 동선 단절
- 권장: /sales/dashboard 로 변경

## B-002 [P2] 견적서 통화 컬럼 미표시
- 페이지: /sales/quotations
- 페르소나: 안지연 영업 사원
- 증거: `sales_quotations.html:46-65` 금액 컬럼만 존재
- 문제: 다통화 환경(VND/USD/KRW) 혼동
- 권장: "금액(원)" 또는 통화 칼럼 추가

## B-003 [P1] 견적 라인 추가 UX 불명
- 페이지: /sales/quotations
- 페르소나: 안지연
- 증거: `sales_quotations.html:70-71` 토글 폼
- 문제: 라인 추가 ↔ 인쇄 정합성 미검증
- 권장: 라인 목록과 신규 추가 UI 레이아웃 재정의

## B-004 [P2] 생산 시작 버튼 권한 미검증
- 페이지: /sales/orders
- 페르소나: 이해림 / 임택훈
- 증거: `sales_orders.html:63-66` /sales/production/start
- 문제: 핸들러 권한 검증 미상
- 권장: 생산팀 leader 만 허용

## B-005 [P1] 세금계산서 발행 권한 모호
- 페이지: /sales/orders
- 페르소나: 박지은 관리 leader
- 증거: `sales_orders.html:89` 외부 KNK 회계 시스템 명시
- 문제: 발행 버튼 표시 권한 기준 불명
- 권장: 회계권한자 필터 도입

## B-006 [P2] 출하 액션 조건 모호
- 페이지: /sales/production
- 페르소나: 이해림 / 임택훈
- 증거: `sales_production.html:54-62` status `READY_TO_SHIP` or `IN_PRODUCTION`
- 문제: 부분출하 동선 불명
- 권장: status별 출하 가능 조건 명시

## B-007 [P2] 수금 폼 잔액 기본값 부재
- 페이지: /sales/shipments-receipts
- 페르소나: 박지은
- 증거: `sales_shipments_receipts.html:43` input name="amount" placeholder 없음
- 문제: 수금 담당자 매번 잔액 수동 계산
- 권장: placeholder "미수금: XXXX원" 표시

## B-008 [P3] won() 매크로 일관성 부족
- 페이지: /sales/dashboard
- 페르소나: 김정락 CEO
- 증거: `sales_dashboard.html:8` vs `sales_forecast.html:7`
- 문제: 매출 예측은 "만" 포함, 강화 대시는 미포함
- 권장: 전사 규격 통일

## B-009 [P1] 예측 불가 안내 빈약
- 페이지: /sales/forecast
- 페르소나: 김정락 / 이해림
- 증거: `sales_forecast.html:101` "최소 2개월 이상 데이터"
- 문제: 현재 보유 월 수 미표시
- 권장: "현재 보유: 0개월 (최소 2개월 필요)" 식 안내

## B-010 [P2] aging 히트맵 정규화 모호
- 페이지: /sales/aging
- 페르소나: 박지은
- 증거: `sales_aging.html:93` "거래처별 max 기준"
- 문제: 여러 거래처 비교 시 상대 위험도 판단 어려움
- 권장: 전체 max 기준 옵션 추가

## B-011 [P1] 거래처 행 클릭 접근성
- 페이지: /customers
- 페르소나: 안지연
- 증거: `customers_list.html:40` onclick="location.href=..."
- 문제: 키보드 네비게이션 불가
- 권장: `<a href>` 재구조화

## B-012 [P3] customer_detail i18n 키 미전달
- 페이지: /customer/{id}
- 페르소나: 베트남법인 사용자
- 증거: `customer_detail.html:12-16` `{{ i.cd_* }}` vs `main.py:2610` i 객체 미포함
- 문제: i18n 컨텍스트 비주입
- 권장: 라우트에 i18n 컨텍스트 추가

## B-013 [P1] 견적서 인쇄 회사 정보 공란
- 페이지: /quotation/print
- 페르소나: 안지연
- 증거: `quotation_print.html:96-104` company_biz_no/address/tel/email
- 문제: 미입력 시 인쇄본 공란 → 제출 불가
- 권장: 필수 입력 폼 검증 강화

## B-014 [P2] 다국어 라디오 새로고침 스크롤 손실
- 페이지: /quotation/print
- 페르소나: 안지연
- 증거: `quotation_print.html:70-81` ?lang=...
- 문제: 페이지 reload 시 스크롤 위치 손실
- 권장: JS fetch + partial update

## B-015 [P1] 견적서 통화 하드코딩
- 페이지: /quotation/print
- 페르소나: 베트남법인 영업
- 증거: `quotation_print.html:163` `i.qp_currency_krw` 고정
- 문제: 수출 견적서(USD/VND) 미지원
- 권장: header.currency 변수화

## B-016 [P2] export_home empty state 모호
- 페이지: /export
- 페르소나: 이용식 베트남법인
- 증거: `export_home.html:23` + line 54 주석
- 문제: 본인이 진행할 사항 불명
- 권장: role 기반 메시지 분기

## B-017 [P1] FTA_TYPES 중복 전달
- 페이지: /fta
- 페르소나: 윤영조 (FTA C/O 발급)
- 증거: `fta_list.html:23-25` form select
- 문제: 검색 필터 UI ↔ 신규 발급 폼 중복 전달
- 권장: 라우트에서 단일 전달

## B-018 [P3] fta_form onCustomerChange JS 정의 미확인
- 페이지: /fta/new
- 페르소나: 윤영조
- 증거: `fta_form.html:100-103` onchange="onCustomerChange(this)"
- 문제: JS 함수 정의 미확인 → 동작 불명
- 권장: inline JS 제거 또는 스크립트 명시

## B-019 [P2] 매출 Hub 페이징 부재
- 페이지: 매출 Hub 5종
- 페르소나: 이해림 (대량 데이터)
- 증거: `sales_quotations.html`, `sales_orders.html`, `sales_production.html`, `sales_shipments_receipts.html` `{% if items|length > 0 %}` 무제한
- 문제: 1000건+ 성능 저하
- 권장: limit + offset 페이징

## B-020 [P1] 매출 사이드바 4개 페이지 누락
- 페이지: base_sales.html (사이드바)
- 페르소나: 이해림
- 증거: `base_sales.html:83-90` /projects, /sales/production 만 포함
- 문제: /sales/forecast, /sales/aging, /sales/outstanding 누락
- 권장: 4개 분석 페이지 사이드바 추가

---

**Tier 합계**: P0×0 + P1×11 + P2×7 + P3×2 = 20건
