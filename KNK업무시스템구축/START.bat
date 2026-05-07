@echo off
REM ============================================================
REM   LAST UPDATE: 2026-05-08 v5H226i (수주 라인 엑셀 다운로드 기능 추가)
REM   - BAT line-length 8192 limit fix (REM truncated, full log -> CHANGELOG.md)
REM   - v5H226c consumable Excel upload: image extract + header auto-mapping
REM   - v5H226b INSERT column-name bug fix (qty/unit_price/amount)
REM   - v5H226 consumable line-input feature (+ excel modal + paste image preview)
REM   Full changelog: ./CHANGELOG.md
REM   Rule: 01 session updates this short summary on each code change
REM ============================================================
cd /d "%~dp001_HAIST_WORKS"
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
title KNK HAIST WORKS - HAIST Innovation [v5H226i]

echo.
echo ============================================================
echo    HAIST WORKS  ^|  KNK Integrated Work Platform
echo    Human ^& AI create the Best
echo    [v5H226i  2026-05-08]
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
