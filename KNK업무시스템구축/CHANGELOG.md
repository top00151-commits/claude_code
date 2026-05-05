# KNK HAIST WORKS — 변경 이력

> 본 파일은 BAT 파일에 누적되던 LAST UPDATE 라인을 분리·보존한 것입니다. (Windows CMD 8191자 라인 한계로 BAT 실행 실패 → 2026-05-05 분리)

---

## v5H131 (2026-05-05) — "+ 추가 발주" 모달 수량 필드 추가 (대표 직접 요청)
- **요청 배경**: 추가 발주가 여러 대일 수 있는데 수량 조정 필드 부재. 4호기 4.9M씩 4대 = 19.6M 일괄 입력 시나리오
- **의미 결정**: `total_amount` 필드 = **1대 단가** (옵션 A 채택). 사용자는 단가만 알면 되므로 더 직관적
- **UI** (`templates/project_detail.html`):
  - "수주액 (원)" → "1대 단가 (원)"
  - "수량 (대)" 신설 (number, min=1 max=100 value=1)
  - 단가/수량 입력 시 **라이브 합계** 표시: `SO 총액 (단가 × 수량) = N KRW`
  - 안내문: "수량 N대 입력 → N개 호기 라인 자동 생성 (예: 3호기·4호기·5호기·6호기)"
- **JS**: `submitFollowupOrder()` 에 `qty` form 필드 + 검증 (단가 > 0, qty 1~100). 응답 alert 에 다대 등록 시 단가/총액 표시
- **라우트** (`main.py:5409 /projects/{pid}/add-followup-order`): `qty` form 파싱 + 검증, `add_followup_order(..., qty=qty)` 전달
- **워크플로우** (`project_workflow.py:add_followup_order`): qty 파라미터 추가 (백워드 호환 default=1).
  - `unit_price = total_amount` (입력값 = 1대 단가), `so_total = unit_price × qty`
  - `orders.unit_qty = qty`, `orders.total_amount = so_total`, `orders.unit_label`은 단일 시 "3호기" / 다대 시 "3호기~6호기"
  - `order_items` N개 INSERT — 각 라인 `qty=1, unit_price=단가, unit_label="N호기"` (프로젝트 전체 연속번호, v5H110 add-unit 패턴 동일)
  - 상태 이력 메시지에 "qty대 × 단가 X = 총액 Y" 명시
- **백워드 호환**: qty 미전달/1 전달 시 v5H130 동작과 동일 (기존 호출부 영향 없음)
- py_compile PASS (main.py / project_workflow.py)
- **테스트 방법**: 프로젝트 상세 → "+ 추가 발주" → 단가 4,900,000 + 수량 4 입력 → 라이브 합계 19,600,000 KRW 확인 → 발행 → SO 카드에 4개 호기 라인(3~6호기, 각 4.9M) 생성 확인

## v5H130 (2026-05-05) — 자동 SO 발행 누락 결함 3중 차단 (대표 직접 보고)
- **재현 케이스**: 009T2605 김성준1 검사기 — 인라인 "초기협의 → 진행중" 클릭 후 SO 0건, 사용자가 "추가 발주" 누름 → 1호기가 4.9M으로 기록되며 초기 5M 흔적 소실
- **근본 원인**: `POST /projects/{pid}/quick-status` 라우트(main.py:4862)에 v5H87 자동 SO 발행 로직이 누락. form-POST 경로(`/projects/new`, `/projects/{pid}/edit`)에는 있으나 인라인 상태변경 경로에는 없었음
- **수정 1 (HIGH)**: quick-status 라우트가 WON_STATUSES 진입 시 + SO 0건 + order_amount > 0 → `confirm_order_multi`로 1호기 자동 발행. 이력에 "수주발행(자동) v5H130 자동" 기록
- **수정 2 (HIGH 백업 안전망)**: `GET /project/{pid}` 진입 시 동일 조건이면 자동 1호기 발행 — 어떤 경로로 들어왔든 상세 페이지 한 번 열면 자가치유. 또한 `order_amount` 자가치유 시 `log_project_change`로 변경 이력 기록 (이전엔 무로그 덮어쓰기였음)
- **수정 3 (MED UX 가드)**: `openFollowupOrder()` JS — 기존 SO 0건이면 confirm 모달로 경고 ("이 발주가 1호기로 기록됨, 새로고침하면 자가치유"). 사용자 의도가 "추가"인데 실제는 "초기"가 되는 함정 차단
- 부수 수정: quick-status의 `generate_mgmt_code(biz_div)` 호출은 database.py 시그니처(1-arg) 그대로 유지 (project_workflow.py 의 3-arg 변종과 혼동 방지)
- 백워드 호환: 기존 라우트 응답 스키마 유지 + try/except로 모든 자동 발행 swallow (실패해도 상태 변경은 성공). JSON 응답에 `auto_so_issued`, `auto_so_no` 필드만 추가
- py_compile PASS (main.py / database.py / project_workflow.py)

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
