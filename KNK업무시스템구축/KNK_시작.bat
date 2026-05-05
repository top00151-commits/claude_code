@echo off
REM ============================================================
REM   LAST UPDATE: 2026-05-05 v5H132 프로젝트 등록/수정 폼에도 단가/수량/금액 3-필드 + 자동 SO N개 호기 라인 (등록 시 수량 N → N개 SO)
REM   Full changelog: ../CHANGELOG.md
REM ============================================================
chcp 65001 >nul
title KNK HAIST WORKS [v5H132]
cd /d "%~dp001_HAIST_WORKS"

echo.
echo ============================================================
echo    HAIST WORKS  ^| KNK Integrated Work Platform
echo    Human ^& AI create the Best
echo    [v5H132  2026-05-05]
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
