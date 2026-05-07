@echo off
REM ============================================================
REM   LAST UPDATE: 2026-05-06 v5H173 외화 원화 환산 자동 계산·표시·보존 — (1)project_form 페이지 로드 시 fx_rate 가 있으면 원화 환산 자동 재계산(빈 0 으로 보이던 문제 해결), (2)저장된 amount_krw 가 있으면 그 값으로 초기화, (3)project_detail 우측 패널 수주액 아래 '≈ X KRW (환율 1 USD = 1450 KRW)' 표기 추가. v5H172 통화 표시 일관성 + 데이터 백필 + 인라인 편집 즉시 반영 — (1)startup 시 orders.currency 자동 백필(수금이력 없는 SO 만 프로젝트 헤더 통화로 sync), (2)project_detail KPI/SO 카드 통화 표기를 p.currency 우선으로 변경(legacy NULL/'KRW' 데이터 fallback), (3)호기 라인 currency select 6종 확장, (4)인라인 편집 저장 후 캐시버스터 강제 reload(_t=Date.now()). v5H171 통화 데이터 end-to-end 연결 수정 — (1)main.py:8262 VND 묵음 손실 버그 수정(KRW/USD/VND/JPY/CNY/EUR 모두 허용·헤더 통화 default), (2)main.py:8228/9070 fx_rate·amount_krw 폼값을 프로젝트 INSERT/UPDATE 에 전달, (3)project_workflow.confirm_order() 단일 SO 발행 시 프로젝트 헤더 통화 상속(NULL 누락 버그 수정), (4)project_form.html 헤더 통화 6종(KRW/USD/VND/JPY/CNY/EUR) 확장 + 헤더 변경 시 호기 라인 unit_currency[] 자동 동기화 + 새 호기 라인 추가 시 헤더 default 적용. 수주관리 '+새 수주' 버튼 제거(SO는 프로젝트 진행중 전환 시 자동 발행 구조라 수동 생성 불필요). 임박납기 박스 높이를 달력 그리드 실제 높이에 정확히 맞춤(JS sync). 달력은 자연 높이 유지, 리스트는 내부 스크롤. v5H168 한달이동(±1개월) + 60건 확장 유지. 수주관리 페이지 전면 재설계 — 4탭(T 검사기/M 자동화/K 기타/소모품) + KPI 6카드 + 상태 파이프라인(수평 칸반) + 출하 캘린더(이번달+다음달) + 강화 목록표(D-day 뱃지·진행률 바·납기색상행). /sales/orders 라우트 매개변수 추가(tab/status/period/currency/q/sort/due_date). 소모품 탭은 consumable_orders 테이블 별도 조회. 신규 partial 2종(_v5_partials/so_pipeline.html, so_calendar.html). 백워드 호환 PRAGMA 컬럼 동적 감지 유지. 정렬 기본 = 납기 임박순. 권한: can_use_sales.
REM   PREV: 2026-05-05 v5H154 고객사 엑셀 일괄 등록 신설. /customers/import-template (양식 다운로드) + /customers/import-xlsx (파싱·검증·미리보기 JSON) + /customers/import-confirm (UPSERT) 3개 라우트 신설. '고객사' 시트 row7+ 파싱, 10컬럼 매핑(고객사명/사업자번호/대표/담당자/전화/이메일/주소/등급/활성/비고), 검증(사업자번호 10자리·이메일 형식·등급 A/B/C/VIP·활성 1/0). 동일 이름 존재 시 빈 칸 아닌 필드만 UPDATE(기존 데이터 보호) / 신규 INSERT, 사업자번호 중복(다른 이름)은 경고만. customers_list.html 상단에 [📥 양식 다운로드][📤 엑셀 일괄 업로드] 버튼 + 미리보기 모달(신규/업데이트 카운트·동작 pill·검증결과). 권한: can_use_sales.
REM   (full changelog: ../CHANGELOG.md)
REM   Rule: 01 session updates this single-line summary on each code change
REM ============================================================
cd /d "%~dp001_HAIST_WORKS"
title KNK HAIST WORKS - HAIST Innovation [v5H173]

echo.
echo ============================================================
echo    HAIST WORKS  ^|  KNK Integrated Work Platform
echo    Human ^& AI create the Best
echo    [v5H173  2026-05-06]
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
