@echo off
REM ============================================================
REM   LAST UPDATE: 2026-05-03 v5H85 per-unit price breakdown when units within an SO differ — CEO: 'when SO is the same but unit prices differ, how do we display?'. get_project_orders now fetches order_items per SO + computes unit_price_uniform flag. project_detail amount cell shows (1) all-same: 'N units × price' subtitle (2) mixed: '호기별 단가 ▾' collapsible details with each unit label + amount. Single-unit SO: no breakdown. — CEO suggestion: 'if we can edit the order quantity, it'll be easier'. project_detail SO list now shows unit_qty (number input) and total_amount (text + commas) inline; on change a 💾 button appears → POST /sales/orders/{oid}/quick-edit. Validation: qty>=1, amt>=0; rejects SHIPPED/INVOICED/PAID/CANCELLED SOs. Updates project.order_amount sum + writes history note. Requires can_use_sales. Direct quantity adjustment as simpler alternative to multi-SO grouping flow.
REM   Rule: 01 session bumps this line every time code is modified
REM ============================================================
cd /d "%~dp001_HAIST_WORKS"
title KNK HAIST WORKS - HAIST Innovation [Updated 2026-05-03 v5H85b per-unit breakdown fallback (avg if no items)]

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
