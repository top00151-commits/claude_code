@echo off
REM ============================================================
REM   LAST UPDATE: 2026-05-03 v5H98 project delete HTTP 500 fix — CEO: '011T2604 delete fails with HTTP 500'. Cause: a child table FK not in cascade list. Fixes: (1) projects_delete_logi adds dynamic safety net — query sqlite_master for all tables, if has project_id col → SET NULL first (preserve history), DELETE if NULL not allowed (2) route wraps in try/except → returns JSON with sqlite/FK error detail (visible in modal) (3) projects.html delete JS parses JSON for user-friendly error message. v5H97 form 4 improvements + inline status — CEO: 'currency display, export/domestic, status location, SO issuance method'. (1) ① basic info adds 거래구분(내수/수출) radio, projects ALTER is_export (2) ③ amount adds 통화(KRW/USD/VND) select + label simplified (3) status labeled 'initial only - editable later in detail' + default 초기협의 (4) project_detail sidebar status becomes inline select → onchange POST /projects/{pid}/quick-status saves immediately (5) 거래구분 pill display (export blue/domestic orange) (6) order amount display with currency suffix. v5H96 SO detail shows mgmt code + unit info — CEO: 'lines show None/None part no/name, no mgmt code visible'. Cause: unit lines have no part_id (so LEFT JOIN parts → None) / route didn't join projects. Fixes: (1) sales_order_detail route joins projects (mgmt_code/project_name/biz_div/model_name) (2) items normalize: part_name falls back to unit_label (3) header shows mgmt code (link to project) / project name / biz / model / ship_to / currency / status (4) line table columns: 호기/품번 - 품명/사양 - 수량 - 단가(currency) - 금액(currency) - 비고. v5H95 currency options KRW/USD/VND + symbols removed — CEO: 'use only KRW, USD, VND, no symbols'. (1) all select options: KRW/USD/VND only, no ₩/$ prefix (2) all displays show 'amount CODE' format (e.g. 5,000,000 KRW) (3) server validation adds VND. v5H94 order amount KPI single source of truth — CEO: 'qty 1 but order amount shows 2 units worth'. Cause: form value 10M → auto SO at 10M with 1 line → user inline edited line to 5M → SO/items synced but projects.order_amount stuck at 10M (form value). Fix: (1) project_detail route auto-heals: compare SUM(orders) vs projects.order_amount on page load → UPDATE if differ (2) KPI + sidebar amount displayed from SO sum (single source of truth) (3) ⚠ shown when mismatch detected. v5H93 SO list redesigned as cards — CEO: 'too hard to read, simplify'. 11-col cramped table → 1 SO = 1 card. (1) Card header: big SO no + status pill + meta (order/due/ship/currency) + actions (＋ unit/🗑) (2) Body: unit lines table (label/price/note/save·×) always visible, inline editable per row (3) Footer: qty N · total ₩X · ⚠ integrity warnings (4) ＋ unit inline panel (label/currency/price/note) (5) Below all cards: 'grand total' box (6) New APIs: POST /sales/orders/items/{iid}/edit · /delete (per-unit edit/delete with auto SO + project total recalc). v5H92 label rename + currency selector — CEO: '납품지→납품처, 호기수→수량, 금액→단가/금액 split, ₩/$ selectable on input'. (1) all template label renames (2) project_detail SO table 11 columns: SO no/order date/due/납품처/수량/단가(₩|$)/금액/통화/status/note/action (3) 단가 cell: uniform shows price, mixed shows '여러 단가 ▾' (4) currency column: editable shows ₩KRW/$USD select, else text (5) ALTER orders ADD currency, get_project_orders + sales_orders SELECT include it (6) form units row gets currency select column + 단가 label (7) confirm_order_multi groups by (due,ship,currency); INSERT includes currency (with fallback) (8) add-unit/quick-edit accept currency. v5H91 unit/amount integrity validation — CEO: '3 units but only 2 prices entered, no error appeared, should warn'. (1) get_project_orders computes mismatch_qty/mismatch_sum flags (2) project_detail unit cell ⚠ '호기 N/M' warning + amount cell ⚠ '합계 불일치 Δamount' (3) quick-edit server validation: when order_items exist, reject unit_qty change unless equals item count, reject total_amount change unless equals sum (with friendly guidance). v5H90 add unit with different price to same SO — CEO: 'in same SO, when extra unit comes with different price, reflect that too'. project_detail SO row gets ➕ 호기 button + inline form (label/amount/note). POST /sales/orders/{oid}/add-unit: order_items INSERT + orders.unit_qty++/total_amount += amount + unit_label appended + project sum sync + history. Rejects SHIPPED/INVOICED/PAID/CANCELLED. v5H89c row click 404 fix. v5H89b customer not visible — data linkage fix — CEO: 'looks like data not linked, customer not showing'. Root cause: projects stored customer_name(text) but left customer_id(FK) NULL → orders inherited NULL → JOIN failed. Fixes: (1) projects_create_logi/update_logi auto-map customer_name → customer_id (2) confirm_order_multi also looks up at SO creation (3) sales_orders SELECT triple-fallback cu.name → p.customer_name → pcu.name (4) Startup migration backfill: fill NULL projects.customer_id and orders.customer_id from project. Existing data auto-heals on next start. v5H89 sales orders list expanded — CEO: 'too few info columns; mgmt code, model, customer, etc not visible'. Route adds projects join (mgmt_code/project_name/biz_div/model_name/po_type) + dynamic SELECT for new orders columns (ship_to/unit_qty/unit_label) via PRAGMA. Template now 11 columns: SO no / mgmt code (project link) / project·model / biz pill (T/M color) / customer / units+labels / ship_to / amount / status / order date / due date. v5H88 SO suffix — CEO: 'why does T-260505 jump to -2, where's -1?'. v5H69 logic counted bare base as N=1 → next was -2 (skipping -1). Fix: bare base excluded from N count → 1st = base, 2nd = base-1, 3rd = base-2. v5H87 진행중 status also auto-issues SO — CEO: 'progress=진행중 means under production, but no SO means not in 수주관리 aggregation — contradiction'. v5H86 only issued mgmt code. Fix: POST /projects/new + /projects/{pid}/edit when status in WON_STATUSES AND no SO yet → confirm_order_multi with single unit (label='1호기', amount=order_amount, due_date=project.due) auto-issues SO. Hint updated to 'mgmt + SO together'. v5H86 status auto-issues mgmt code — CEO: 'selected 진행중 but mgmt code not issued'. Before: only stage in (수주확정,납품) triggered. Added: WON_STATUSES = (진행중,납품완료) also triggers → projects_create_logi/update_logi check status, auto-promote stage to 수주확정. Form hint updated. v5H85 per-unit price breakdown when units within an SO differ — CEO: 'when SO is the same but unit prices differ, how do we display?'. get_project_orders now fetches order_items per SO + computes unit_price_uniform flag. project_detail amount cell shows (1) all-same: 'N units × price' subtitle (2) mixed: '호기별 단가 ▾' collapsible details with each unit label + amount. Single-unit SO: no breakdown. — CEO suggestion: 'if we can edit the order quantity, it'll be easier'. project_detail SO list now shows unit_qty (number input) and total_amount (text + commas) inline; on change a 💾 button appears → POST /sales/orders/{oid}/quick-edit. Validation: qty>=1, amt>=0; rejects SHIPPED/INVOICED/PAID/CANCELLED SOs. Updates project.order_amount sum + writes history note. Requires can_use_sales. Direct quantity adjustment as simpler alternative to multi-SO grouping flow.
REM   Rule: 01 session bumps this line every time code is modified
REM ============================================================
cd /d "%~dp001_HAIST_WORKS"
title KNK HAIST WORKS - HAIST Innovation [Updated 2026-05-03 v5H98 project delete HTTP 500 fix (dynamic cascade)]

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
