@echo off
REM ============================================================
REM   LAST UPDATE: 2026-05-08 v5H216 소모품 발주 묶음 관리코드 도입 — 'S' prefix 신설(예: 001S2605). consumable_orders.mgmt_code 컬럼 추가, generate_mgmt_code 가 S 도 지원(consumable_orders 에서 검색), co_create() 가 자동 발급, startup 시 기존 묶음 백필(YYMM 별 sequence 추적). UI: 유형 선택 화면·소모품 목록·상세 모두 관리코드 표시. 라인별 장비 매칭은 그대로(linked_project_id). v5H215 stage 매핑 단순화 — stage = status 그대로 사용. 검사기(T) '제안서 해당없음'인데 단계 = '제안작성' 표기 의미 충돌 해결. 사용자가 선택한 세부 상태(초기협의/제안서전달/견적발행/수주예정/진행중/납품완료/취소/보류/기타)가 단계에도 그대로 반영. 수주확정(mgmt_code 발급) 시점만 stage='수주확정' 별도 마킹 유지. v5H214 status → stage 자동 매핑 + 상태 pill fallback 수정 — stage 는 사용자 선택 status 에서 자동 도출(초기협의/제안서전달/견적발행/수주예정/보류/기타→제안작성, 진행중→진행중, 납품완료→납품완료, 취소→취소). 상태 pill 의 fallback(호기 0건 시)도 stage→status 우선으로 변경 — 사용자가 '수주예정' 선택해도 상태가 '제안작성' 으로 보이던 버그 수정. /projects/new POST + /edit POST + quick-status 모두 일관 적용. v5H213 수주 전 내역 UX 개선 — (1)즉시 저장 → 수정/저장 패턴(SO 카드와 동일), (2)체크박스+제출완료 라벨 가로 배치(min-width 100px 줄바꿈 방지), (3)메모 placeholder 안내문 제거(빈 입력칸은 빈 칸), (4)프로젝트 정보 우측 패널 거래구분 이모지 🏠/✈ 모두 제거. v5H212 수주 전 내역 섹션 신설 — 수주내역 위에 제안서·견적서 진행 추적. 컬럼 4개(proposal_submitted/proposal_memo/quotation_submitted/quotation_memo) 추가, /projects/{pid}/presales-edit 단건 PATCH 라우트, 인라인 체크박스+메모 입력(blur 시 자동 저장 ✓ 표시), '해당없음'(date 빈 값) 줄 자동 숨김, 수주확정 후 기본 접힘 + localStorage 사용자 토글 기억, 변경 이력 자동 기록. v5H211 단계별 차등 검증 — 초기협의/제안서전달/견적발행/수주예정/보류 단계는 단가·발주일·납기·환율 옵션(추상적 견적), 진행중/납품완료 또는 '수주확정 동시발급' 체크 시에만 strict 검증. 거래구분 라벨 이모지(🏠/✈) 제거(물류 운송수단 오해 방지). 상태 select 아래 동적 안내 박스(strict 시 노란색 ⚠, 그 외 회색 ⓘ). v5H210 공휴일 자동 계산 (holidays 라이브러리 도입) — 매년 수동 갱신 불필요. holidays>=0.96 패키지가 음력 환산·대체공휴일 규칙·nghỉ bù 모두 자동 처리. 7년 슬라이딩 윈도우(작년~5년 후) 서버 시작 시 자동 생성. KR 근로자의날(5/1) 수동 추가, 제헌절(7/17) 제외(2008년 공휴일 폐지). 진단 /_debug/holidays. v5H208 공휴일 데이터 context 이중 안전망 — Jinja globals 외에 ctx() 함수에서도 KNK_HOLIDAYS_KR/VN 직접 주입(globals 미적용 환경 대비), partial 에 default({}, true) 필터 적용, 빈 데이터 시 콘솔 ⚠️ 서버 재시작 안내. v5H207 데이트픽커 (1)공휴일 데이터 정의 가드 — KNK_HOLIDAYS_KR/VN is defined 체크 + 콘솔 진단 로그(키 개수 표시), (2)스마트 위치 — popup 실제 사이즈 측정 후 아래 공간 부족 시 input 위쪽에 표시, 좌우 화면 경계 보정. 화면 하단 input 클릭 시 잘리던 문제 해결. v5H206 데이트픽커 셀·배지 확대 — popup 280→340px, 셀 32→42px, K/V 배지 11→16px (수주관리와 동일). 선택일은 amber 배경+적색 테두리. v5H205 공휴일 적색 표시 수주관리 패턴 통일 — knk_datepicker + calendar.html 모두 .d.sun/.d.hol/.d.sat !important 적용 (수주관리 sales_orders.html 동일). v5H204 공휴일 데이터 보강 — 한국: 근로자의날 추가 + 2025/2028 풀 커버 + 대체공휴일 부처님오신날·성탄절 적용. 베트남: Tết 5일 풀(29~Mùng4) + nghỉ bù 정확화 + 2025/2028 추가. 총 한국 4년치 50건+, 베트남 4년치 35건+. v5H203 프로젝트 등록·상세 날짜 input 도 공휴일 표시 데이트픽커로 통일 — 신규 partial knk_datepicker.html (popup 캘린더, K/V 배지, 일·공휴일 적색, 토요일 청색, 대체공휴일 점선, 오늘로/지우기/닫기). 적용 input: 발주일·납기·제안서·견적서·호기 납기(등록), SO 발주일·납기·호기 발주일·납기·추가발주(상세). HOLIDAYS_KR/VN Jinja 전역 노출. v5H202 전체 캘린더 통일 — 한국·베트남 공휴일·대체공휴일 표시(K/V 배지 + 일/공휴일 적색 + 토요일 청색). v5H201 우측 패널 상태 read-only. v5H190 프로젝트 레벨 편집 툴바 제거. v5H189 호기별 통화 인라인 select (KRW/USD/VND/JPY/CNY/EUR) — 일부 호기는 USD 결제 같은 시나리오 지원. v5H188 호기 라인 항상 편집 가능 (편집 모드 토글 폐기) + '💾 변경사항 저장'. v5H187 프로젝트 통화 변경 시 호기까지 즉시 cascade. v5H186 호기별 상태(진행중/납품완료/취소/보류) + 일괄 적용 + 거래구분/통화 편집 버그 수정. v5H185 프로젝트 상세 편집 위치 재배치 (우측 패널=read-only, 타이틀 옆 ✏️ + 수주내역 툴바). v5H184 등록 폼 자가치유 라벨을 친화적으로 수정 + SO=수주번호 풀이 안내. v5H183 프로젝트 변경 이력 상세 기록(등록 초기값 16종 + 자동 SO 호기별 + 호기 수정 단가/발주일/납기/납품처 모두 project_history 에 기록). v5H182 호기 인라인 편집 '편집 완료' 일괄 저장(행별 💾 버튼 숨김). v5H181 고객사 리스트 SELECT/템플릿 컬럼명 수정 + tier '신규'→'일반' 정리. v5H180 고객사 다건 일괄 삭제 (FK 연결 시 차단). v5H179 프로젝트 다건 일괄 삭제(체크박스+sticky 툴바+비번 재인증). v5H178b HTML 응답 no-cache + 호기 중복 라벨 자동 재번호 + order_items.currency 부모 sync. v5H178 추가 발주 모달에 통화·납품처 추가 (default = 프로젝트 헤더 통화). v5H177 호기별 발주일/납기/납품처 override + 프로젝트 헤더 인라인 편집(이름/비고/통화·환율/거래구분) + 수정 폼 readonly. Tier 1(관리코드/사업부/유형/PO유형) 영구 잠금. v5H176 SO 합계 통화 표기를 p.currency 동적 + 외화 시 KRW 환산 병기. v5H175 전역 '← 이전 페이지' 플로팅 버튼 (모든 페이지 좌하단, 홈/탑탭 메인 제외) + history.back/referrer/허브 홈 fallback. v5H174 프로젝트 폼 우측 상단 '등록자/등록일시' 항상 표시 (수정 시 최근수정 추가). v5H173 외화 원화 환산 자동 — 폼 로드 시 fx_rate 있으면 원화 환산 자동 재계산·표시, 저장된 amount_krw 보존, 프로젝트 상세 우측 패널 환산값 표기. v5H172 통화 표시·백필·즉시반영 — (1)startup orders.currency 자동 백필, (2)KPI/SO 통화 표기 p.currency 우선, (3)인라인 편집 후 캐시버스터 강제 reload. v5H171 통화 데이터 연결 — (1)VND 묵음 손실 버그 fix, (2)fx_rate·amount_krw 프로젝트 저장 누락 fix, (3)confirm_order() 단일 SO 통화 상속 누락 fix, (4)project_form 헤더 통화 6종 확장 + 호기 라인 자동 동기화. 수주관리 '+새 수주' 버튼 제거(SO는 프로젝트 진행중 전환 시 자동 발행 구조라 수동 생성 불필요). 임박납기 박스 높이를 달력 그리드 실제 높이에 정확히 맞춤(JS sync). 달력은 자연 높이 유지(과대 stretch 제거), 리스트는 내부 스크롤. v5H168 한달이동(±1개월) + 60건 확장 유지. 수주관리 페이지 전면 재설계 — 4탭(T 검사기/M 자동화/K 기타/소모품) + KPI 6카드 + 상태 파이프라인(수평 칸반) + 출하 캘린더(이번달+다음달) + 강화 목록표(D-day 뱃지·진행률 바·납기색상행). /sales/orders 라우트 매개변수 추가(tab/status/period/currency/q/sort/due_date). 소모품 탭은 consumable_orders 테이블 별도 조회. 신규 partial 2종(_v5_partials/so_pipeline.html, so_calendar.html). 백워드 호환 PRAGMA 컬럼 동적 감지 유지. 정렬 기본 = 납기 임박순(오버듀→임박→여유). 캘린더 색상: 오버듀 적색/D-3 주황/D-7 노랑/여유 녹색. 권한: can_use_sales (_s1_guard).
REM   PREV: 2026-05-05 v5H154 고객사 엑셀 일괄 등록 신설. /customers/import-template (양식 다운로드) + /customers/import-xlsx (파싱·검증·미리보기 JSON) + /customers/import-confirm (UPSERT) 3개 라우트 신설. '고객사' 시트 row7+ 파싱, 10컬럼 매핑(고객사명/사업자번호/대표/담당자/전화/이메일/주소/등급/활성/비고), 검증(사업자번호 10자리·이메일 형식·등급 A/B/C/VIP·활성 1/0). 동일 이름 존재 시 빈 칸 아닌 필드만 UPDATE(기존 데이터 보호) / 신규 INSERT, 사업자번호 중복(다른 이름)은 경고만. customers_list.html 상단에 [📥 양식 다운로드][📤 엑셀 일괄 업로드] 버튼 + 미리보기 모달(신규/업데이트 카운트·동작 pill·검증결과). 권한: can_use_sales.
REM   Full changelog: ../CHANGELOG.md
REM ============================================================
chcp 65001 >nul
title KNK HAIST WORKS [v5H178]
cd /d "%~dp001_HAIST_WORKS"

echo.
echo ============================================================
echo    HAIST WORKS  ^| KNK Integrated Work Platform
echo    Human ^& AI create the Best
echo    [v5H178  2026-05-06]
echo ============================================================
echo.

where python >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python is not installed.
    echo Install Python 3.10+ from https://www.python.org/downloads/
    pause
    exit /b 1
)

python -c "import fastapi, uvicorn, jinja2" >nul 2>nul
if errorlevel 1 (
    echo [First Run] Installing required packages...
    python -m pip install --upgrade pip >nul
    python -m pip install -r requirements.txt
    if errorlevel 1 (
        echo [ERROR] Package installation failed.
        pause
        exit /b 1
    )
    echo [OK] Installation complete.
)

start "" /b cmd /c "timeout /t 3 /nobreak >nul && start http://localhost:8081"

python run.py

echo.
echo Server stopped. Press any key to close.
pause >nul
