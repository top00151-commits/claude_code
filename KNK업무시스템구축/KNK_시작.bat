@echo off
REM ============================================================
REM   LAST UPDATE: 2026-05-02 v5H32 공수 입력 UX 명확화 (대표 지시 — 며칠/몇주 걸리는 업무 시간 표현 혼란) — (1) 라벨 '공수(시간)' → '⏱ 오늘 작업 시간 (h)' + 안내 '오늘({work_date}) 이 업무에 들인 시간만 입력. 다음 날에도 이어서 하면 일일업무에서 새 카드 작성', (2) 빠른 입력 프리셋 5개 (0.5/1h/2h/4h/8h하루) 클릭 한 번에 입력, (3) 마감일 라벨 '📅 마감일 (전체 업무 종료 예정)' + '며칠/몇주/몇달 걸려도 OK' 안내, (4) 사이드바 '📊 이 프로젝트 누적 공수' 카드 신규 (동일 project_id 또는 project_label의 모든 카드 SUM/COUNT, 기간 first~last) — 며칠 이어진 업무 자동 집계 / 154/154 PASS
REM   업데이트 규칙: 01 세션이 코드 수정/작업할 때마다 본 라인 갱신
REM ============================================================
chcp 65001 > nul
title KNK HAIST WORKS - HAIST Innovation [Updated 2026-05-02 v5H32 공수 입력 명확화 + 누적 공수 자동 집계]
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
