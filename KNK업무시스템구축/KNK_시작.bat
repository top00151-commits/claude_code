@echo off
REM ============================================================
REM   LAST UPDATE: 2026-05-03 v5H81 SO 채번 규칙 재정합 (대표 정의 명확화) — SO 는 호기/수량 구분이 아니라 진행 단위(납기/납품지/일자) 구분용. 수정 전: 호기마다 SO 1개씩 (T-260503/-2/-3) 잘못 발급. 수정 후: (납기, 납품지) 그룹화 → 같은 납기+같은 납품지면 호기 N대라도 SO 1개에 묶임, 다르면 그룹별 SO 분리. orders ALTER (ship_to, unit_qty), order_items ALTER (unit_label, line_note). confirm_order_multi 재작성 (그룹화 + order_items 적재). 폼 호기 테이블에 '납품지' 컬럼 추가 + SO 발행 예정 건수 라이브 hint. project_detail 수주내역 테이블에 납품지/호기 컬럼 추가
REM   업데이트 규칙: 01 세션이 코드 수정/작업할 때마다 본 라인 갱신
REM ============================================================
chcp 65001 > nul
title KNK HAIST WORKS - HAIST Innovation [Updated 2026-05-03 v5H81 SO 채번 규칙 재정합 (납기/납품지 그룹 = SO 1개)]
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
