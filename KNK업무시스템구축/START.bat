@echo off
REM ============================================================
REM   LAST UPDATE: 2026-05-02 v5H20 패턴 정밀화 + 적용 영역 대폭 확대 — PDF 원본 PNG 추출(SVG 폐기), 10개 영역 적용 (상단바·사이드바·page-head·card·KPI·btn·테이블·empty·login welcome·login bg) / 153/153 PASS
REM   Rule: 01 session bumps this line every time code is modified
REM ============================================================
cd /d "%~dp001_HAIST_WORKS"
title KNK HAIST WORKS - HAIST Innovation [Updated 2026-05-02 v5H20 PDF 원본 패턴 PNG 추출 + 10개 영역 적용]

echo.
echo ============================================================
echo    HAIST WORKS  ^|  KNK Integrated Work Platform
echo    Human ^& AI create the Best
echo    [Last Update: 2026-04-29 G25_v4_CX23c_마스트헤드제거 (대표결재: 나)제거안) 3 base (통합/매출/자재) 상단 매거진 마스트헤드(VOL.NO + EDITION) 라인 일괄제거 → 일반 사무실 시스템 톤 + topbar-h 125→80px + dock top 80px 정합]
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
