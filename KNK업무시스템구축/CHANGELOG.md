# KNK HAIST WORKS — 변경 이력

> 본 파일은 BAT 파일에 누적되던 LAST UPDATE 라인을 분리·보존한 것입니다. (Windows CMD 8191자 라인 한계로 BAT 실행 실패 → 2026-05-05 분리)

---

## v5H140 (2026-05-05) — 연관 관리번호 선택 시 고객사/사업부/모델 자동 채움
- /api/projects/search 응답에 customer_id / biz_div / model_name / po_type / is_export 추가
- project_form.html JS: 부모 프로젝트 선택 시 위 5필드 자동 입력 (빈 칸일 때만, 사용자 입력 보존)
- 안내 토스트 "✓ 연관 프로젝트 정보로 자동 채움됨 (필요 시 수정 가능)"
- 백워드 호환: 부모 프로젝트 정보 누락 시 silent 폴백

## v5H139 (2026-05-05) — 프로젝트 유형 라디오 라벨 2줄(영문+한글) 표기
- project_form.html 라디오 라벨이 PROJECT_TYPE_LABELS 컨텍스트 미전달로 영문만 노출되는 결함 수정
- 인라인 dict으로 한글 매핑 하드코딩 + 라벨을 카드형으로 변경 (선택시 애버 배경)
- v5H138 partial 패턴과 동일한 영문(응고릴)+한글(이모지+라벨) 2줄 표기

## v5H138 (2026-05-05) — 프로젝트 유형 pill 영문+한글 2줄 표기 (대표 직접 요청, so-pill 패턴 통일)
- **요청 배경**: v5H135 SO 상태 pill 처럼 프로젝트 유형도 영문 enum + 한글 의미를 2줄로 (NEW_EQUIP / 🔧 신규 장비 등). 영문은 시스템 enum 가시화, 한글은 직관성.
- **partial 신설 — `app/templates/_v5_partials/project_type_pill.html`**: 4종 매핑 (NEW_EQUIP→🔧 신규 장비 / CONSUMABLE→📦 소모품·부품 / SERVICE→🔨 수리·유지보수 / OTHER→🌐 기타). `<span class="pt-pill pt-pill-{code}">` + `.en` (monospace 영문) + `.kr` (이모지+한글) 2줄 inline-flex column. `size='sm'` 인자로 작은 크기 (목록 표 셀용). 4색 분기: NEW_EQUIP 주황(#ffedd5/#9a3412) · CONSUMABLE 녹색(#d1fae5/#065f46) · SERVICE 파랑(#dbeafe/#1e3a8a) · OTHER 회색(#e5e7eb/#374151). 매핑에 없는 enum 은 영문만 표시 — backward compatible.
- **적용 — `project_detail.html`**: 헤더 H1 의 stage pill 옆 단일 라벨 pill → partial (full size). 사이드 패널 "프로젝트 정보" `<dt>유형</dt>` → partial (size='sm').
- **적용 — `projects.html`**: 목록 표 "유형" 컬럼 셀 → partial (size='sm'). 검색 폼 셀렉트 옵션은 그대로 유지 (드롭다운은 단일 라인이 자연).
- **유지 (변경 없음)**: `project_form.html` 라디오 라벨 텍스트 (대표 지시 — "라디오는 그대로 두고 pill 만"). 백엔드 enum/상수/라우트 무변경.
- **검증**: Jinja parse PASS (project_type_pill / project_detail / projects / project_form 4종). v5H137 기능(자동 SO 라벨 토글, 연관 관리번호 자동완성, 안내 배너) 무영향.

## v5H137 (2026-05-05) — 프로젝트 유형 분류 신설 (대표 직접 요청)
- **요청 배경**: 등록할 때부터 소모품인지 기타인지 구분해서 등록해야 함. 소모품 등록 시 연관 관리번호 연결 가능, 없으면 단독 진행. SO 자동 라벨도 유형에 맞게 (검사기는 호기, 소모품은 회차, 수리는 차, 기타는 건).
- **DB 마이그 — `app/database.py`**: `projects` 테이블에 `project_type TEXT DEFAULT 'NEW_EQUIP'` + `parent_project_id INTEGER` 2개 컬럼 ALTER (PRAGMA 가드 + try/except 폴백). `idx_projects_parent` 인덱스 추가 (소모품 → 부모 장비 역조회 가속). 기존 행은 NULL → DEFAULT 'NEW_EQUIP' 으로 동작 (백워드 호환).
- **상수 4종 — `app/database.py`**: `PROJECT_TYPES` 튜플 (NEW_EQUIP/CONSUMABLE/SERVICE/OTHER) + `PROJECT_TYPE_LABELS` (이모지+한글) + `PROJECT_TYPE_UNIT_LABEL` 라벨 패턴 dict + `project_unit_label(ptype, n)` 헬퍼 (NEW_EQUIP→'1호기', CONSUMABLE→'1회차', SERVICE→'1차', OTHER→'1건'; NULL/미지원 → NEW_EQUIP 폴백).
- **헬퍼 확장**: `_project_insert_or_update_values()` 에 project_type/parent_project_id 정규화. `projects_create_logi()` INSERT + `projects_update_logi()` UPDATE 양쪽에 두 컬럼 반영. `projects_list_logi(project_type=)` 필터 인자 추가. `projects_update_logi` 변경 이력 diff 키에 두 컬럼 추가.
- **자동 SO 호기 라벨 토글 — `app/main.py`**: `/projects/new` POST + `/projects/{pid}/edit` POST + `/projects/{pid}/quick-status` POST + `project_detail` v5H130 자가치유 진입 시 SO 발행 코드 4곳 모두 하드코딩 `f"{i+1}호기"` → `_logi.project_unit_label(_ptype, i+1)` 로 교체. confirm_order_multi 호출 시 폼의 `unit_label[]` 빈 칸 폴백도 project_type 기준. 백워드 호환 — 기존 NEW_EQUIP 프로젝트는 정확히 동일하게 '1호기/2호기...' 로 동작.
- **`app/project_workflow.py`**: `add_followup_order(unit_label_pattern=None)` 인자 추가 — 미전달 시 프로젝트 row 의 `project_type` 으로 PROJECT_TYPE_UNIT_LABEL 자동 조회. 기존 호출부(qty 인자만) 영향 없음.
- **폼 UI — `app/templates/project_form.html`**: 사업부/PO유형 그리드 다음 줄에 "프로젝트 유형" 라디오 4종 (이모지+한글) + 토글 JS (`pfTogglePtype()`). CONSUMABLE/SERVICE 선택 시 "🔗 연관 관리번호 (선택)" 입력칸 노출 — `/api/projects/search` (v5H136) 재사용한 자동완성 (200ms debounce, mgmt_code+이름+고객사 표시, 클릭 시 hidden parent_project_id 채움). 다른 유형으로 바꾸면 hidden 자동 초기화.
- **상세 UI — `app/templates/project_detail.html`**: 헤더 H1 에 stage pill 옆에 프로젝트 유형 pill 추가. 사이드패널 "프로젝트 정보" 에 "유형" + (있을 때) "연관 관리번호" 링크 표시. CONSUMABLE/SERVICE + parent_project 있으면 소모품 카드 위에 amber 안내 배너 ("📦 이 프로젝트는 [009T2605 …] 의 소모품/부품 발주 건입니다"). `project_detail` 라우트 ctx 에 `parent_project` 단건 조회 + PROJECT_TYPES/LABELS 전달.
- **목록 UI — `app/templates/projects.html`**: 검색 폼에 "유형 전체" 셀렉트 추가. 표 헤더에 "유형" 컬럼 + 행마다 PROJECT_TYPE_LABELS pill. 초기화 버튼 조건에 project_type 추가.
- **검증**: `py_compile` (database.py + main.py + project_workflow.py) PASS. Jinja parse (project_form/project_detail/projects) PASS. `init_db()` 후 `PRAGMA table_info(projects)` 에서 두 컬럼 + 인덱스 존재 확인. 라벨 헬퍼 6개 케이스 (NEW_EQUIP/CONSUMABLE/SERVICE/OTHER/NULL/미지원 폴백) PASS.
- **백워드 호환**: 기존 프로젝트는 project_type NULL → DEFAULT 'NEW_EQUIP' 으로 동작, 자동 SO 라벨도 기존 그대로 '1호기/2호기...'. parent_project_id NULL → 단독 진행 (정상). v5H136 소모품 카드 + v5H132 단가×수량 + v5H81 호기 그룹화 SO 발행 모두 무영향.

## v5H136 (2026-05-05) — PO 라인 ↔ 프로젝트 다대다 연결 (대표 직접 요청, 장비 소모품/수리이력 추적)
- **요청 배경**: 검사기/장비에 소모품 발주 요청이 오면 해당 장비 관리번호와 PO 라인을 연결해 ① 자주 나가는 소모품 식별 ② 수리 이력 누적 ③ 장비별 운영비(TCO) 추적이 가능하도록. 공통 부품(공구·범용 소모품)은 연결하지 않아도 자연 폴백.
- **DB 스키마 — `app/database.py` SCHEMA**: `po_item_project_links` 신규 테이블 (id / po_item_id FK CASCADE / project_id FK CASCADE / allocated_qty / allocation_pct / note / created_at / created_by) + 2 인덱스. ALTER 없이 `IF NOT EXISTS` 신규 테이블이라 기존 PO 데이터 무영향.
- **헬퍼 5종 — `app/database.py` 말미**: `po_item_link_project()` (중복 거부 후 lastrowid 반환), `po_item_unlink_project()`, `get_po_item_links(po_item_id)` (mgmt_code/project_name/equip_type 조인), `get_project_consumables(project_id)` (PO·자재·공급사 풀 조인 + 분배수량/% 우선순위 계산 + 합계), `get_part_project_usage(part_id)` (자재별 프로젝트 누적 GROUP BY, 수량 내림차순).
- **라우트 3종 — `app/main.py` 말미**: `POST /po/{po_id}/items/{iid}/link-project` (form: project_id 필수 + allocated_qty/allocation_pct/note 선택), `POST /po/links/{link_id}/delete` (link → po_item → po 역추적 후 PO 상세로 리다이렉트), `GET /api/projects/search?q=` (mgmt_code OR name LIKE, mgmt_code 있는 활성 프로젝트만 30건). 3종 모두 `can_use_logistics` 가드.
- **기존 라우트 ctx 보강**: `po_detail` → 각 라인에 `links` 어태치 + `link_projects` 선택지 추가. `project_detail` → `consumables` (rows/total_amount/total_qty/count) 추가. `parts_detail_page` → `project_usage` 추가. 모두 try/except 폴백.
- **UI 카드 3종**:
  - `app/templates/po_detail.html`: 라인 행 우측 [🔗 연결] 버튼 + 인라인 폼 (프로젝트 select / 분배수량 / % / 비고). 연결된 프로젝트는 라인 아래 칩(관리번호 + 프로젝트명 + 분배 + ×)으로 표시. 합계 colspan 5→6 자동 조정.
  - `app/templates/project_detail.html`: "🔧 소모품·부품 사용 이력" 카드 신설 (발주일/자재코드/자재명/수량(분배 표기)/단가/금액/PO/공급사/비고 + 합계 행). 빈 상태 안내.
  - `app/templates/part_detail.html`: "📊 프로젝트별 사용 현황" 카드 신설 (관리번호/프로젝트명/누적수량/누적금액/마지막발주일/연결수). 빈 상태에는 "🌐 공통 부품" 칩 + 안전재고 후보 안내.
- **테스트 방법**: ① /po/{id} 진입 → 라인 [🔗 연결] → 프로젝트 선택 → 칩 등장 확인 → 칩 × 클릭 시 해제 ② /project/{id} 진입 → 소모품 카드에 방금 연결한 라인 표시 + 합계 행 ③ /parts/{id} 진입 → 프로젝트별 사용 현황 카드 ④ 0건 자재는 "공통 부품" 안내 표시.
- **검증**: py_compile (database.py + main.py) PASS. Jinja parse (po_detail/project_detail/part_detail) PASS. 백워드 호환 — 기존 PO/프로젝트/자재 데이터에 연결 0건이면 모든 카드가 빈 상태 안내로 안전하게 폴백. 모든 신규 fetch 는 try/except 로 감싸 회귀 차단.

## v5H135 (2026-05-05) — SO 상태 pill 영문+한글 2줄 표기 통일 (대표 직접 요청)
- **요청 배경**: SO 상태가 영문 enum (CONFIRMED/SHIPPED 등) 만 표시되어 비영어 사용자 직관성 저하. 영문(원본 enum) + 한글 의미를 한 pill 안에 2줄로 함께 표기하여 가독성·검색성·국제화 동시 확보
- **partial 신설 — `app/templates/_v5_partials/so_status_pill.html`**: 매핑 dict (DRAFT→임시 / CONFIRMED→수주확정 / SHIPPED→출하 / INVOICED→송장발행 / PAID→수금완료 / CANCELLED→취소) + flex-column 2줄 레이아웃 + 상태별 6색 (amber/gray/blue/violet/green/red). 매핑에 없는 상태는 영문만 표시 (backward compatible)
- **적용 위치 3곳 일괄 통일**:
  - `project_detail.html:296` — 프로젝트 상세 SO 카드 헤더
  - `sales_order_detail.html:22` — SO 상세 헤더
  - `sales_orders.html:71` — SO 목록 상태 컬럼
- **호출 방식**: `{% with status=so.status %}{% include '_v5_partials/so_status_pill.html' %}{% endwith %}` — 호출부 변수명(so/order/o) 무관하게 `status` 키로 통일
- **검증**: Jinja parse 4파일 PASS. PO/quotation 상태는 별도 enum 이라 이번 작업 범위 외 (요청 시 후속)

## v5H134 (2026-05-05) — SO 카드 호기 라인 내림차순 강제 (v5H133 미반영 핫픽스)
- **요청 배경**: v5H133 배포 후 대표 스크린샷에서 SO 카드 호기 라인이 여전히 오름차순(3→12호기, 1→2호기)으로 표시. 백엔드 `get_project_orders` 의 in-Python sort 가 적용되었음에도 화면 미반영 의심
- **백엔드 보강 — `app/project_workflow.py` `get_project_orders`**: 각 unit dict 에 정렬 키 `_sort_n` (unit_label 의 숫자 prefix, 미매칭 9999) 을 미리 계산해 내장. 정렬 함수도 이 키 사용. 데이터 자체에 키가 박혀 있어 다운스트림(템플릿/JSON 직렬화) 어디서든 재정렬 가능
- **템플릿 보강 — `app/templates/project_detail.html` SO 카드**: `{% for u in so.units %}` → `{% set _units_desc = so.units|sort(attribute='_sort_n', reverse=true) %}` + `{% for u in _units_desc %}`. 백엔드 정렬이 어떤 이유로든 누락되어도 화면단에서 재정렬되는 이중 안전망
- **데이터 흐름 추적 결과**: SO 카드는 `so.units` (= `get_project_orders` 반환의 units 키) 만 사용. 다른 데이터 소스(order_items, items) 우회 경로 없음 확인. 정렬 누락 원인은 서버 재시작 미수행 또는 캐시로 추정 — 데이터에 키 내장으로 향후 동일 증상 재발 차단

## v5H133 (2026-05-05) — 호기 표시 순서 반전 (최근 호기 → 1호기, 대표 직접 요청)
- **요청 배경**: 호기 라인이 1호기 → N호기 (오름차순) 으로 표시되어 신규 호기 확인 시 스크롤 필요. 가장 최근 발주된 호기를 맨 위에 배치하기 위해 내림차순으로 반전
- **`app/main.py` `/project/{pid}` (`all_units_sorted`)**: `sorted(_flat, key=_sort_key)` → `sorted(_flat, key=_sort_key, reverse=True)`. 사이드패널 호기 분해 라인이 N → 1 순으로 표시
- **`app/main.py` `/sales/orders/{oid}` (`sales_order_detail`)**: SQL `ORDER BY oi.id` 결과를 in-Python 으로 `unit_label` 숫자 prefix 기준 reverse=True 재정렬. SO 상세의 "수주 라인" 테이블이 N → 1 순
- **`app/project_workflow.py` `get_project_orders.units`**: SQL `ORDER BY id ASC` 후 in-Python 으로 `unit_label` 숫자 prefix 기준 reverse=True 재정렬. project_detail SO 카드의 호기 라인이 N → 1 순 (`so.units` 소비처 동시 영향)
- **백워드 호환**: 데이터 구조/컬럼/스키마 변경 없음. 정렬 순서만 표시단에서 반전. 라벨 숫자 추출 실패 라인은 `9999` 키로 정렬 후 reverse → 무라벨 라인이 항상 최상단(또는 라벨 라인보다 위)에 위치 (기존도 9999 → 최하단이었던 것을 의도적으로 뒤집음)
- **영향 없음**: sales_orders.html 목록(SO 1줄당 unit_label 단일 칩 표시), 엑셀 export, biz_doc 생성, stock 자가치유 — 모두 단일 라인 표시 또는 불변 데이터 흐름

## v5H132 (2026-05-05) — 프로젝트 등록/수정 폼 단가·수량·금액 3-필드 (대표 후속 요청)
- **요청 배경**: v5H131 은 추가 발주만 처리. 초기 등록 시점에도 수량 조정 필드가 없어 진행 중 1대 SO 만 발행되던 결함. "단가, 수량, 금액으로 표현" 요청
- **schema** (`database.py`): `projects` 에 `unit_qty INTEGER DEFAULT 1`, `unit_price REAL` 컬럼 ALTER (PRAGMA 가드 idempotent). 기존 row 는 NULL/1 폴백
- **UI** (`templates/project_form.html` ③ 금액 섹션): "수주액" 단일 → **단가 / 수량 / 금액(자동·readonly)** 3-필드 그리드. 단가 또는 수량 변경 시 JS 가 `금액 = 단가 × 수량` 라이브 계산, hidden `order_amount` 동기화. 통화는 별도 행. 안내문 "수량 N대 → N개 호기 라인 SO 자동 발행" 명시. SO 발행됨 상태에서는 단가/수량 readonly
- **수정폼**: 동일 폼이 project edit 도 사용 — `project.unit_qty`, `project.unit_price` 폴백 (NULL 이면 `_p_qty=1`, `_p_price=order_amount/qty`)
- **라우트** (`main.py`):
  - `POST /projects/new`: `unit_price`, `unit_qty` 폼 파싱(1~100 클램프) → `order_amount = unit_price × unit_qty` 서버 재계산. v5H87 자동 SO 분기에서 1호기 단건 → **N개 호기 라인** (각 단가=unit_price) `confirm_order_multi` 호출
  - `POST /projects/{pid}/edit`: 동일 처리 + `projects_update_logi` 에 `unit_qty`/`unit_price` 전달
  - `POST /projects/{pid}/quick-status` (v5H130): `projects` 에서 `unit_qty`, `unit_price` 함께 SELECT → WON 진입 자동 SO 발행 시 N개 호기 라인 생성. 이력 메시지 "단가 X × N대 = TOTAL"
- **DB 헬퍼** (`database.py`): `_project_insert_or_update_values` 에 `unit_qty`(1~100 클램프), `unit_price`(빈/0 → None) 추가. INSERT/UPDATE SQL 양쪽에 컬럼 추가
- **UI 보강** (`templates/project_detail.html` 사이드패널): 수주액 dd 에 `단가 X × N대 = TOTAL CUR` 라인 추가 (unit_qty/unit_price NULL 시 폴백 계산)
- **백워드 호환**: 기존 프로젝트 (unit_qty/unit_price NULL) 는 quick-status·edit 폴백으로 1호기 단건 처리됨. 추가 발주 (v5H131) 모달은 변경 없음 — 이미 일관성 있음

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
