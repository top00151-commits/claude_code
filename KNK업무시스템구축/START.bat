@echo off
REM ============================================================
REM   LAST UPDATE: 2026-05-07 v5H203 프로젝트 등록·상세 날짜 input 도 공휴일 표시 데이트픽커로 통일 — 신규 partial _v5_partials/knk_datepicker.html (popup 캘린더, K/V 배지, 일·공휴일 적색, 토요일 청색, 대체공휴일 점선 테두리, 오늘로/지우기/닫기). 자동 부착(.knk-cal) + 동적 추가 input MutationObserver 대응. 적용 input: 발주일·납기·제안서일정·견적서일정·호기 납기(등록 폼), SO 발주일·납기·호기 발주일·납기·추가발주 모달(상세 페이지). HOLIDAYS_KR/HOLIDAYS_VN Jinja 전역(get_holidays) 노출. v5H202 전체 캘린더 통일 — 한국·베트남 공휴일·대체공휴일 표시(K/V 배지 + 일/공휴일 적색 + 토요일 청색). v5H201 등록 필수 검증 + 수정 비번 잠금 — (1)/projects/new POST 에 고객사/PO유형/발주일/납기/단가 필수 검증 + 외화 시 기준환율 필수, 빈 항목 시 'X 를 입력해주세요' 안내, (2)/projects/{pid}/edit 수정 폼은 기본 잠금 → '🔓 수정 잠금 해제' 버튼으로 비밀번호 인증 후 편집 가능 (Tier 1 영구 잠금 필드 제외), (3)/projects/{pid}/edit POST 가 unlock_verified+password 재검증, (4)password_confirm partial 이 검증된 비밀번호를 onConfirm 인자로 전달. v5H191 우측 패널 상태 read-only pill 화 — 정보 확인 전용. v5H190 프로젝트 레벨 편집 툴바([⇄ 거래구분][✏️ 통화/환율][✏️ 비고]) 제거 — 호기별 인라인 편집이 대체. v5H189 호기별 통화 인라인 (KRW/USD/VND/JPY/CNY/EUR) — 5대 국내 KRW · 5대 해외 USD 같은 시나리오 지원. 표시도 행별 통화로 (◆ override 표식). /sales/orders/items/{iid}/edit 가 currency 폼값 받음, SO 부모와 동일하면 NULL 상속/다르면 override 저장. 변경 이력에 '통화 KRW → USD' 자동 기록. v5H188 호기 라인 항상 편집 가능 — '편집 모드 토글' 폐기. 단가/발주일/납기/납품처/비고 input 항상 노출(편집 가능 SO 한정), 비편집 SO(완료/취소) 는 텍스트만. 토글 버튼 → '💾 변경사항 저장' (항상 일괄 저장 동작). v5H187 통화 인라인 편집 시 즉시 cascade — header-edit endpoint 가 currency 변경되면 같은 트랜잭션에서 (1)orders.currency (수금이력 없는 SO 만), (2)order_items.currency 모두 동기화. 이력에 'SO N건 + 호기 M건 통화 동기화' 자동 기록. 이전엔 startup 백필에만 의존해서 즉시 반영 안되던 결함. v5H186 호기별 상태 신설 + 편집 버그 수정 — (1)order_items.unit_status 컬럼 신설(DEFAULT '진행중'), (2)호기 행마다 상태 select(컬러 배지) 즉시 변경, (3)호기 일괄 상태 적용 툴바('이 SO 전체'/'프로젝트 전체'), (4)/sales/orders/items/{iid}/status + /projects/{pid}/units/bulk-status endpoint, (5)거래구분 토글 후 풀 reload(이전엔 우측 패널만 갱신되어 다른 표시 영역이 stale), (6)통화/환율 편집 시 fx 부분 실패해도 reload(KRW 선택 시 fx 빈값 처리 안되어 reload 안되던 버그 수정), (7)이력 자동 기록 ('호기 상태(1호기)' / '호기 상태 일괄 변경'). v5H185 프로젝트 상세 편집 위치 재배치 — (1)우측 '프로젝트 정보' 패널은 정보 확인만(✏️ 모두 제거), (2)타이틀 '프로젝트명' 옆에 ✏️ 추가 (프로젝트명 인라인 편집 + 우측 패널 동기화), (3)수주 내역 헤더에 [⇄ 거래구분] [✏️ 통화/환율] [✏️ 비고] 툴바 추가. v5H184 UX 라벨 친화 — '1대 단가 (SO 발행됨 — 변경 시 자가치유 위험)' → '이미 수주 발행됨 — 호기별 단가는 [상세 화면]에서 편집' (tooltip 으로 자세한 설명). 안내 문구에 'SO = Sales Order (수주번호)' 풀이 추가. v5H183 프로젝트 변경 이력 상세 기록 강화 — (1)신규 등록 시 모든 초기값(사업부/유형/PO유형/고객사/모델/거래구분/통화/기준환율/수량/단가/수주액/발주일/납기/초기상태/PM/영업/비고) 각각 별도 행으로 로깅, (2)자동 SO 발행 시 통화·납기·라벨 풀 디테일 + 호기별 개별 추가 행 로깅, (3)호기 라인 수정 시 단가/발주일/납기/납품처/비고/라벨 모든 변경을 project_history 에 SO번호와 함께 기록 (이전엔 order_status_history 만 기록되어 프로젝트 이력 페이지에 안 보였음). v5H182 호기 인라인 편집 일괄 저장 — 행별 저장(💾) + 메타 저장 버튼 숨김 후 '편집 완료' 클릭 시 dirty 행 모두 sequential POST. 진행 중 'X호기 1행만 저장되고 다른 행 미저장 후 편집모드 종료' 버그 해결. v5H181 고객사 일괄 등록 후 리스트 표시 누락 버그 수정 — (1)customers list SELECT 에 manager_name/phone/email/address/is_active 추가, (2)템플릿 컬럼명 수정 (business_no→biz_no, contact_person→manager_name), (3)import-confirm 신규 default tier '신규'→'일반', (4)startup 시 customers.tier='신규' → '일반' 정리(30건). v5H180 고객사 다건 일괄 삭제 — 체크박스+sticky 툴바+비번 재인증, FK 안전(프로젝트/수주 연결된 고객사는 차단), 담당자(customer_contacts) cascade 삭제, 최대 200건/회. v5H179 프로젝트 다건 일괄 삭제 — 행별 체크박스 + 헤더 전체선택(indeterminate 지원) + 선택건수 실시간 표시 sticky 툴바 + 비밀번호 재인증 후 /projects/bulk-delete (최대 200건, FK 실패 건은 집계만 보고 계속) v5H178b (1)HTML 응답에 Cache-Control: no-store 추가(인라인 편집 후 stale 화면 방지), (2)startup 시 호기 라벨 중복 자동 정리(같은 SO 내 동일 unit_label 다수 → 첫 라벨 시작숫자 추출 후 순차 재번호 + orders.unit_qty/total_amount 동기화), (3)order_items.currency 부모 SO 와 mismatch 시 sync(NULL 만이 아니라 mismatch 도). v5H178 추가 발주 모달에 통화 select(KRW/USD/VND/JPY/CNY/EUR, default = 프로젝트 헤더 통화) + 납품처 input 추가. add_followup_order(currency, ship_to) 인자 추가, orders.currency/ship_to + order_items.currency 명시 저장(스키마 동적 감지). v5H177 (Phase 1+2 통합) 호기별 발주일/납기/납품처 override + 프로젝트 헤더 인라인 편집 — (1)order_items 에 order_date/due_date/ship_to/currency 컬럼 추가, NULL 시 SO 부모값 상속, 다르면 ◆ 표시, (2)호기 인라인 편집 행에 발주일/납기/납품처 input 추가, (3)/sales/orders/items/{iid}/edit 가 override 받음, (4)project_form.html 수정모드 진입 시 모든 필드 readonly + 상세 페이지 안내 배너, (5)/projects/{pid}/header-edit 신규 endpoint (name/customer_id/currency/fx_rate/is_export/note/order_date/due_date 단건 PATCH, mgmt_code/biz_div/project_type/po_type/created_* Tier 1 영구 잠금), (6)프로젝트 상세 우측 패널 ✏️ 인라인 편집 (이름/비고/통화·환율/거래구분 토글). v5H176 SO 합계 통화 표기 하드코딩 KRW → p.currency 동적. 외화 + fx_rate 있으면 KRW 환산 병기. v5H175 전역 '← 이전 페이지' 플로팅 버튼 추가 — 모든 페이지 좌하단(사이드바 옆) 항상 노출. history.back() 우선 + same-origin referrer fallback + 허브 홈 fallback. 홈/탑탭 메인(/home, /sales, /logistics, /login)에서는 자동 숨김. v5H174 프로젝트 등록/수정 폼 우측 상단에 '등록자 / 등록일시' (수정 시 최근 수정 일시 추가) 항상 표시. 신규 등록 시는 현재 로그인 사용자 + 실시간 시계. 수정 시는 created_by → users.name lookup. v5H173 외화 원화 환산 — (1)project_form 페이지 로드 시 fx_rate 가 있으면 원화 환산 자동 재계산(빈 0 으로 보이던 문제 해결), (2)저장된 amount_krw 가 있으면 그 값으로 초기화, (3)project_detail 우측 패널 수주액 아래 '≈ X KRW (환율 1 USD = 1450 KRW)' 표기 추가. v5H172 통화 표시 일관성 + 데이터 백필 + 인라인 편집 즉시 반영 — (1)startup 시 orders.currency 자동 백필(수금이력 없는 SO 만 프로젝트 헤더 통화로 sync), (2)project_detail KPI/SO 카드 통화 표기를 p.currency 우선으로 변경(legacy NULL/'KRW' 데이터 fallback), (3)호기 라인 currency select 6종 확장, (4)인라인 편집 저장 후 캐시버스터 강제 reload(_t=Date.now()). v5H171 통화 데이터 end-to-end 연결 수정 — (1)main.py:8262 VND 묵음 손실 버그 수정(KRW/USD/VND/JPY/CNY/EUR 모두 허용·헤더 통화 default), (2)main.py:8228/9070 fx_rate·amount_krw 폼값을 프로젝트 INSERT/UPDATE 에 전달, (3)project_workflow.confirm_order() 단일 SO 발행 시 프로젝트 헤더 통화 상속(NULL 누락 버그 수정), (4)project_form.html 헤더 통화 6종(KRW/USD/VND/JPY/CNY/EUR) 확장 + 헤더 변경 시 호기 라인 unit_currency[] 자동 동기화 + 새 호기 라인 추가 시 헤더 default 적용. 수주관리 '+새 수주' 버튼 제거(SO는 프로젝트 진행중 전환 시 자동 발행 구조라 수동 생성 불필요). 임박납기 박스 높이를 달력 그리드 실제 높이에 정확히 맞춤(JS sync). 달력은 자연 높이 유지, 리스트는 내부 스크롤. v5H168 한달이동(±1개월) + 60건 확장 유지. 수주관리 페이지 전면 재설계 — 4탭(T 검사기/M 자동화/K 기타/소모품) + KPI 6카드 + 상태 파이프라인(수평 칸반) + 출하 캘린더(이번달+다음달) + 강화 목록표(D-day 뱃지·진행률 바·납기색상행). /sales/orders 라우트 매개변수 추가(tab/status/period/currency/q/sort/due_date). 소모품 탭은 consumable_orders 테이블 별도 조회. 신규 partial 2종(_v5_partials/so_pipeline.html, so_calendar.html). 백워드 호환 PRAGMA 컬럼 동적 감지 유지. 정렬 기본 = 납기 임박순. 권한: can_use_sales.
REM   PREV: 2026-05-05 v5H154 고객사 엑셀 일괄 등록 신설. /customers/import-template (양식 다운로드) + /customers/import-xlsx (파싱·검증·미리보기 JSON) + /customers/import-confirm (UPSERT) 3개 라우트 신설. '고객사' 시트 row7+ 파싱, 10컬럼 매핑(고객사명/사업자번호/대표/담당자/전화/이메일/주소/등급/활성/비고), 검증(사업자번호 10자리·이메일 형식·등급 A/B/C/VIP·활성 1/0). 동일 이름 존재 시 빈 칸 아닌 필드만 UPDATE(기존 데이터 보호) / 신규 INSERT, 사업자번호 중복(다른 이름)은 경고만. customers_list.html 상단에 [📥 양식 다운로드][📤 엑셀 일괄 업로드] 버튼 + 미리보기 모달(신규/업데이트 카운트·동작 pill·검증결과). 권한: can_use_sales.
REM   (full changelog: ../CHANGELOG.md)
REM   Rule: 01 session updates this single-line summary on each code change
REM ============================================================
cd /d "%~dp001_HAIST_WORKS"
title KNK HAIST WORKS - HAIST Innovation [v5H178]

echo.
echo ============================================================
echo    HAIST WORKS  ^|  KNK Integrated Work Platform
echo    Human ^& AI create the Best
echo    [v5H178  2026-05-06]
echo ============================================================
echo.

REM -- Check Python --
where python >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python is not installed.
    echo         Install Python 3.10+ from https://www.python.org/downloads/
    echo         Make sure to check "Add Python to PATH" during install.
    pause
    exit /b 1
)

REM -- Auto-install required packages on first run --
python -c "import fastapi, uvicorn, jinja2" >nul 2>nul
if errorlevel 1 (
    echo [First Run] Installing required packages, please wait...
    echo.
    python -m pip install --upgrade pip
    python -m pip install -r requirements.txt
    if errorlevel 1 (
        echo.
        echo [ERROR] Package installation failed.
        echo         Check your internet connection and try again.
        pause
        exit /b 1
    )
    echo.
    echo [OK] Installation complete.
    echo.
)

REM -- Open browser after 4 seconds --
start "" /b cmd /c "timeout /t 4 /nobreak >nul && start http://localhost:8081"

REM -- Run server --
echo Starting server on http://localhost:8081 ...
echo Press Ctrl+C to stop.
echo.
python run.py

echo.
echo Server stopped. Press any key to close.
pause >nul
