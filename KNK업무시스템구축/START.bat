@echo off
REM ============================================================
REM   LAST UPDATE: 2026-05-05 v5H143 quick-status NameError(_cur_ptype) 핫픽스 — v5H142에서 NEW_EQUIP 분기 추가 시 _cur_ptype 정의가 사용 뒤로 밀려 CONSUMABLE 프로젝트 상태 변경 시 HTTP 500 발생. _cur_ptype 정의를 분기 직전으로 이동 + 외곽 try/except로 모든 예외를 친절 JSON 응답. 사이드바 매출·영업 그룹에 "📦 소모품 발주 (M-01-14)" 노출.
REM   (full changelog: ../CHANGELOG.md)
REM   Rule: 01 session updates this single-line summary on each code change
REM ============================================================
cd /d "%~dp001_HAIST_WORKS"
title KNK HAIST WORKS - HAIST Innovation [v5H143]

echo.
echo ============================================================
echo    HAIST WORKS  ^|  KNK Integrated Work Platform
echo    Human ^& AI create the Best
echo    [v5H143  2026-05-05]
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
