@echo off
REM ============================================================
REM   LAST UPDATE: 2026-05-03 v5H83 같은 날 동일 (납기,납품지) 추가 발주 → 기존 SO 재사용 — 대표 지시: '같은 날에 추가가 나오면 미리 발행된 수주번호를 사용할 수 있게'. confirm_order_multi 가 그룹별로 (project_id, order_date, due_date, ship_to) 매칭되는 진행 가능 상태(DRAFT/QUOTED/CONFIRMED/IN_PRODUCTION/READY_TO_SHIP) 기존 SO 검색 → 발견 시 신규 발급 대신 기존 SO 의 total_amount/unit_qty/unit_label 누적 갱신 + order_items 신규 행 추가 + history '호기 추가' 기록. 완료/송장/취소 SO 는 추가 대상 제외 (새 SO 생성). 메시지 '신규 SO N건 · 기존 SO M건에 호기 추가' 형태로 분리 표시
REM   업데이트 규칙: 01 세션이 코드 수정/작업할 때마다 본 라인 갱신
REM ============================================================
chcp 65001 > nul
title KNK HAIST WORKS - HAIST Innovation [Updated 2026-05-03 v5H83 같은 날 동일 키 추가 발주 → 기존 SO 재사용]
cd /d "%~dp001_HAIST_WORKS"

echo.
echo ============================================================
echo    HAIST WORKS  ^|  KNK 통합 업무 플랫폼
echo    Human ^& AI create the Best
echo    [Last Update: 2026-04-29 G25_v4_CX23c_마스트헤드제거 (대표결재: 나)제거안) 3 base (통합/매출/자재) 상단 매거진 마스트헤드(VOL.NO + EDITION) 라인 일괄제거 → 일반 사무실 시스템 톤 + topbar-h 125→80px + dock top 80px 정합]
echo ============================================================
echo.

REM ── Python 설치 확인 ────────────────────────────────────────
where python >nul 2>nul
if errorlevel 1 (
    echo [오류] Python이 설치되어 있지 않습니다.
    echo.
    echo    https://www.python.org/downloads/  에서 Python 3.10 이상을 설치한 뒤
    echo    다시 이 파일을 더블클릭해주세요.
    echo.
    pause
    exit /b 1
)

REM ── 필수 패키지 자동 설치 (최초 1회) ────────────────────────
python -c "import fastapi, uvicorn, jinja2" >nul 2>nul
if errorlevel 1 (
    echo [최초 실행] 필요한 패키지를 설치합니다. 잠시 기다려주세요 ...
    echo.
    python -m pip install --upgrade pip >nul
    python -m pip install -r requirements.txt
    if errorlevel 1 (
        echo.
        echo [오류] 패키지 설치에 실패했습니다.
        echo        인터넷 연결을 확인한 뒤 다시 시도해주세요.
        pause
        exit /b 1
    )
    echo.
    echo [완료] 설치가 끝났습니다.
    echo.
)

REM ── 서버 시작 후 3초 뒤 브라우저 자동 열기 ──────────────────
start "" /b cmd /c "timeout /t 3 /nobreak >nul && start http://localhost:8081"

REM ── 서버 실행 ──────────────────────────────────────────────
python run.py

echo.
echo 서버가 종료되었습니다. 창을 닫으려면 아무 키나 누르세요.
pause >nul
