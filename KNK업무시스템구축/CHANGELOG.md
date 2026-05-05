# KNK HAIST WORKS — 변경 이력

> 본 파일은 BAT 파일에 누적되던 LAST UPDATE 라인을 분리·보존한 것입니다. (Windows CMD 8191자 라인 한계로 BAT 실행 실패 → 2026-05-05 분리)

---

## v5H129 (2026-05-04) — 자재 등록 사진/도면 첨부 + 자동 용량 최소화
- 대표 직접 요청
- DB: `part_attachments` 테이블 신설 (part_id FK CASCADE + idx)
- main.py: `POST /parts/{pid}/attach`, `GET /parts/{pid}/attachments/{aid}`, `POST .../delete` 3개 라우트
- part_form.html: Canvas API 클라이언트 압축 (긴 변 1600px + JPEG 0.8) — 보통 90%+ 절감, 라이브 표시
- 보안: path traversal 2중 검증, 확장자/크기 cap, can_use_logistics 가드

## v5H128 — admin 라우트 권한 가드 전수 점검 + ship_over_warn UI 노출
- admin/* 35+개 모두 require(['admin','ceo']) PASS
- sales_order_detail에 ⚠ 정정 카드

## v5H127 — export_order_detail CI/PL/BL/통관 카드 결함 수정 + quotation 자가치유
- 라우트 list 전달인데 템플릿이 단일 dict로 접근하던 결함, 컬럼명 정합
- B/L 카드, 통관 카드 신설
- quotations.total_amount vs SUM 자가치유

## v5H126 — 통화 일관성 4종
- SO 상세 다통화 수금 분리 표시
- _get_active_fx_rate 헬퍼 + receipts FX 자동 채움
- sales_dashboard 통화별 미수금 위젯
- export CI ↔ 수주 통화 환산표

## v5H125 — 도메인 심화 감사
- part_prices 활성기간 겹침 검증
- parts_detail 진입 시 stock 자가치유
- SO 상세 다통화 수금 분리

## v5H124 — 통화 일관성 확장
- receipts_payment ALTER currency/fx_rate
- 수금 통화 화이트리스트
- sales_dashboard 통화별 수주 분포
- project_detail 다통화 SO 경고

## v5H123 — 매출 대시보드 통화 혼합 집계 결함 (HIGH)
- KRW + USD + VND 단순 합산 → KRW 단독 필터 + by_currency 분포

## v5H122 — Task 서브 API 페이로드 검증
- /api/task/*/comment, /reaction, /delegate 검증

## v5H121 — 미점검 도메인 감사 + PO 자가치유 UI
- tasks API 검증, PO ⚠ 자동보정 배지

## v5H120 — history_card.html 공통 partial
- 5종 변경이력 카드 통합

## v5H119 — _safe_delete_with_cascade 공통 헬퍼
- 7개 delete 함수 리팩토링

## v5H118 — PO 자가치유 + CAPA 라이프사이클 가드
- /po/{id} 진입 시 SUM 자가치유
- CAPA 역행 차단

## v5H117 — 수출입 CI/PL/BL/관세 정합성
- FTA H1 패턴 4개 도메인 일괄

## v5H116 — 미점검 도메인 감사 + 코드품질
- FTA·QC·WO 발급/발행 강화
- doc_audit_log 통합 테이블
- /api/parts/{pid}/active-price API
- CURRENCY_OPTIONS 단일 진실 소스

## v5H115 — 협업 도메인 감사 결함 8건
- issue/ticket/board/change cascade 안전망 + 검증

## v5H114 — 변경이력 UI 3종 + PO 폼 정식 마이그레이션
- user/team/quotation 변경이력 카드
- PO 폼 datalist + line_part_id

## v5H113 — 잠재 결함 + LOW 9건 자율 처리
- PO 폼 정합 (_parse_po_lines_from_form 폴백)
- customer_history UI
- LOW 9건 (part_prices/stock_adjust/users/teams/suppliers/parts/quotations 검증)

## v5H112 — 자재구매·영업 도메인 결함 12건
- HIGH 8 + MED 4
- po_update id 기준 UPSERT, cascade 안전망 4종, 정합성 검증, SO SSOT lock, 음수 차단, 고객사명 동기화

## v5H101 — SO 기준 자가치유 + 프로젝트 변경 이력 테이블
- order_amount/due_date/order_date 자가치유
- project_history 테이블 + log_project_change

## v5H100 — 호기 수정/삭제 이력화

## v5H99 — 프로젝트 리스트 단계 컬럼/필터 제거

## v5H98 — 프로젝트 삭제 HTTP 500 수정 (cascade 동적 안전망)

## v5H97 — 등록폼 4가지 개선 + 상태 인라인 변경

## v5H96 — SO 상세에 관리코드 + 호기 정보

## v5H95 — 통화 옵션 KRW/USD/VND 통일

## v5H94 — 수주액 KPI 단일진실소스 (자가치유 첫 도입)

## v5H93 — 수주내역 카드형 레이아웃

## v5H92 — 라벨 변경 + 통화 선택

## v5H91 — 호기수/금액 정합성 검증

## v5H90 — 동일 SO 안에 단가 다른 호기 추가

## v5H89 — 수주관리 리스트 정보 확장 + 고객사 표기 수정

## v5H88 — SO 접미 채번 (-1 누락 수정)

## v5H87 — 진행중 상태 등록 시 SO 자동 발행

## v5H86 — 진행중/납품완료 시 자동 관리코드 발급

## v5H85 — SO 안 호기 단가 분해 표기

---

> 신규 변경은 본 파일 최상단에 추가하고, BAT 의 LAST UPDATE 라인은 한 줄 요약(80자 이내)으로 유지할 것.
