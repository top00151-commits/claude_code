@echo off
REM ============================================================
REM   LAST UPDATE: 2026-05-05 v5H141 부모 프로젝트 상세에 "연결된 자식 프로젝트(소모품·수리)" 카드 신설 — get_child_projects 헬퍼 + /project/{pid} ctx + project_detail.html 신규 섹션 (관리번호/유형pill/상태/최근SO/합계). 부모↔자식 가시화 결함 수정 (자식 0건이면 카드 미노출)
REM   (full changelog: ../CHANGELOG.md)
REM   Rule: 01 session updates this single-line summary on each code change
REM ============================================================
cd /d "%~dp001_HAIST_WORKS"
title KNK HAIST WORKS - HAIST Innovation [v5H140]

echo.
echo ============================================================
echo    HAIST WORKS  ^|  KNK Integrated Work Platform
echo    Human ^& AI create the Best
echo    [v5H140  2026-05-05]
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
