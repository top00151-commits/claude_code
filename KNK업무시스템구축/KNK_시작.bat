@echo off
REM ============================================================
REM   LAST UPDATE: 2026-05-05 v5H129 parts attachment + auto image compression
REM   Full changelog: ../CHANGELOG.md
REM ============================================================
chcp 65001 > /dev/null
title KNK HAIST WORKS [v5H129]
cd /d "%~dp001_HAIST_WORKS"

echo.
echo ============================================================
echo    HAIST WORKS  ^| KNK Integrated Work Platform
echo    Human ^& AI create the Best
echo    [v5H129  2026-05-05]
echo ============================================================
echo.

where python >/dev/null 2>/dev/null
if errorlevel 1 (
    echo [ERROR] Python is not installed.
    echo Install Python 3.10+ from https://www.python.org/downloads/
    pause
    exit /b 1
)

python -c "import fastapi, uvicorn, jinja2" >/dev/null 2>/dev/null
if errorlevel 1 (
    echo [First Run] Installing required packages...
    python -m pip install --upgrade pip >/dev/null
    python -m pip install -r requirements.txt
    if errorlevel 1 (
        echo [ERROR] Package installation failed. Check your internet connection.
        pause
        exit /b 1
    )
    echo [OK] Installation complete.
)

start "" /b cmd /c "timeout /t 3 /nobreak >/dev/null ^&^& start http://localhost:8081"

python run.py

echo.
echo Server stopped. Press any key to close.
pause >/dev/null
