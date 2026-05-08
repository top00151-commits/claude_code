@echo off
REM ============================================================
REM   LAST UPDATE: 2026-05-08 v5H226p (수주관리 달력·임박납기 접기 토글 + 네비 4버튼 고정)
REM   - BAT line-length 8192 limit fix (REM truncated, full log -> CHANGELOG.md)
REM   - v5H226c soconsumable Excel upload: image extract + header auto-mapping
REM   - v5H226b INSERT column-name bug fix (qty/unit_price/amount)
REM   - v5H226 consumable line-input feature (+ excel modal + paste image preview)
REM   Full changelog: ./CHANGELOG.md
REM ============================================================
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
title KNK HAIST WORKS [v5H226p]
cd /d "%~dp001_HAIST_WORKS"

echo.
echo ============================================================
echo    HAIST WORKS  ^| KNK Integrated Work Platform
echo    Human ^& AI create the Best
echo    [v5H226p  2026-05-08]
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
