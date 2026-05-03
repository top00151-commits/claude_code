@echo off
REM ============================================================
REM   LAST UPDATE: 2026-05-03 v5H88 SO suffix starts at -1 — CEO: 'why does T-260505 jump to -2, where's -1?'. v5H69 logic counted bare base as N=1 → next was -2 (skipping -1). Fix: bare base excluded from N count → 1st = base, 2nd = base-1, 3rd = base-2. v5H87 진행중 status also auto-issues SO — CEO: 'progress=진행중 means under production, but no SO means not in 수주관리 aggregation — contradiction'. v5H86 only issued mgmt code. Fix: POST /projects/new + /projects/{pid}/edit when status in WON_STATUSES AND no SO yet → confirm_order_multi with single unit (label='1호기', amount=order_amount, due_date=project.due) auto-issues SO. Hint updated to 'mgmt + SO together'. v5H86 status auto-issues mgmt code — CEO: 'selected 진행중 but mgmt code not issued'. Before: only stage in (수주확정,납품) triggered. Added: WON_STATUSES = (진행중,납품완료) also triggers → projects_create_logi/update_logi check status, auto-promote stage to 수주확정. Form hint updated. v5H85 per-unit price breakdown when units within an SO differ — CEO: 'when SO is the same but unit prices differ, how do we display?'. get_project_orders now fetches order_items per SO + computes unit_price_uniform flag. project_detail amount cell shows (1) all-same: 'N units × price' subtitle (2) mixed: '호기별 단가 ▾' collapsible details with each unit label + amount. Single-unit SO: no breakdown. — CEO suggestion: 'if we can edit the order quantity, it'll be easier'. project_detail SO list now shows unit_qty (number input) and total_amount (text + commas) inline; on change a 💾 button appears → POST /sales/orders/{oid}/quick-edit. Validation: qty>=1, amt>=0; rejects SHIPPED/INVOICED/PAID/CANCELLED SOs. Updates project.order_amount sum + writes history note. Requires can_use_sales. Direct quantity adjustment as simpler alternative to multi-SO grouping flow.
REM   Rule: 01 session bumps this line every time code is modified
REM ============================================================
cd /d "%~dp001_HAIST_WORKS"
title KNK HAIST WORKS - HAIST Innovation [Updated 2026-05-03 v5H88 SO suffix starts at -1 (T-260505 → -1 → -2)]

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
