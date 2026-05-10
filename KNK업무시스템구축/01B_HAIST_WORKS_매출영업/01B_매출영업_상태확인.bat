@echo off
REM ============================================================
REM   01B 매출영업 작업 상태 확인 도구
REM   더블클릭 → PROGRESS / 최근 HANDOFF / git log 매출영업만 한눈에
REM   LAST UPDATE: 2026-05-10 v5H226z41
REM ============================================================
chcp 65001 >nul
title 01B 매출영업 상태 확인
cd /d "%~dp0"

cls
echo.
echo ============================================================
echo    📊 매출영업 (01B) 작업 상태 확인
echo    %DATE% %TIME:~0,8%
echo ============================================================
echo.

REM ---- 섹션 1: 현재 시스템 버전 (양파일 LAST UPDATE) ----
echo [1] 현재 시스템 버전
echo ------------------------------------------------------------
findstr /B "REM   LAST UPDATE" "%~dp0..\KNK_시작.bat"
findstr /B "REM   LAST UPDATE" "%~dp0..\START.bat"
echo.

REM ---- 섹션 2: PROGRESS.md (진행 표) ----
echo [2] 진행 현황 (PROGRESS.md)
echo ------------------------------------------------------------
type "%~dp0PROGRESS.md"
echo.

REM ---- 섹션 3: HANDOFF 보고서 목록 (최신순) ----
echo [3] 빅터 → 대표 보고서 (최신순)
echo ------------------------------------------------------------
dir /b /o-d "%~dp0output\HANDOFF_TO_01_*.md" 2>nul
echo.

REM ---- 섹션 4: git log 매출영업 관련 ----
echo [4] git log — 매출영업 관련 커밋 (최근 10건)
echo ------------------------------------------------------------
pushd "%~dp0..\..\" >nul 2>&1
git log --oneline -10 -- ^
  "KNK업무시스템구축/01_HAIST_WORKS/app/templates/project_detail.html" ^
  "KNK업무시스템구축/01_HAIST_WORKS/app/templates/projects.html" ^
  "KNK업무시스템구축/01_HAIST_WORKS/app/templates/project_form.html" ^
  "KNK업무시스템구축/01_HAIST_WORKS/app/templates/project_new_chooser.html" ^
  "KNK업무시스템구축/01_HAIST_WORKS/app/templates/sales_home.html" ^
  "KNK업무시스템구축/01_HAIST_WORKS/app/templates/sales_dashboard.html" ^
  "KNK업무시스템구축/01_HAIST_WORKS/app/templates/sales_forecast.html" ^
  "KNK업무시스템구축/01_HAIST_WORKS/app/templates/sales_production.html" ^
  "KNK업무시스템구축/01_HAIST_WORKS/app/templates/sales_orders.html" ^
  "KNK업무시스템구축/01_HAIST_WORKS/app/templates/sales_order_detail.html" ^
  "KNK업무시스템구축/01_HAIST_WORKS/app/templates/sales_quotations.html" ^
  "KNK업무시스템구축/01_HAIST_WORKS/app/templates/sales_quote_detail.html" ^
  "KNK업무시스템구축/01_HAIST_WORKS/app/templates/sales_quote_form.html" ^
  "KNK업무시스템구축/01_HAIST_WORKS/app/templates/quotation_print.html" ^
  "KNK업무시스템구축/01_HAIST_WORKS/app/templates/sales_shipments_receipts.html" ^
  "KNK업무시스템구축/01_HAIST_WORKS/app/templates/sales_outstanding.html" ^
  "KNK업무시스템구축/01_HAIST_WORKS/app/templates/sales_aging.html" ^
  "KNK업무시스템구축/01_HAIST_WORKS/app/templates/customers_list.html" ^
  "KNK업무시스템구축/01_HAIST_WORKS/app/templates/customer_detail.html" ^
  "KNK업무시스템구축/01_HAIST_WORKS/app/templates/customer_form.html" ^
  "KNK업무시스템구축/01_HAIST_WORKS/app/templates/consumables.html" ^
  "KNK업무시스템구축/01_HAIST_WORKS/app/templates/consumable_detail.html" ^
  "KNK업무시스템구축/01_HAIST_WORKS/app/templates/consumable_form_upload.html" ^
  "KNK업무시스템구축/01_HAIST_WORKS/app/templates/export_*.html" ^
  "KNK업무시스템구축/01_HAIST_WORKS/app/templates/fta_*.html" ^
  "KNK업무시스템구축/01B_HAIST_WORKS_매출영업/" 2>nul
popd >nul 2>&1
echo.

REM ---- 섹션 5: git status (워크트리 변경) ----
echo [5] 미커밋 변경 (작업 중)
echo ------------------------------------------------------------
pushd "%~dp0..\..\" >nul 2>&1
git status -s -- "KNK업무시스템구축/01_HAIST_WORKS/app/templates/" "KNK업무시스템구축/01B_HAIST_WORKS_매출영업/" 2>nul
popd >nul 2>&1
echo.

REM ---- 섹션 6: 옵션 메뉴 ----
echo ============================================================
echo    더 자세히 보기:
echo      P) PROGRESS.md 메모장 열기
echo      L) 최신 HANDOFF 메모장 열기
echo      O) output 폴더 탐색기 열기
echo      G) GitHub 브랜치 페이지 열기
echo      Q) 종료
echo ============================================================
echo.
choice /c PLOGQ /n /m "선택 (P/L/O/G/Q): "
if errorlevel 5 goto :end
if errorlevel 4 (
    start "" "https://github.com/top00151-commits/claude_code/tree/claude/charming-yonath-a72046/KNK업무시스템구축/01B_HAIST_WORKS_매출영업"
    goto :end
)
if errorlevel 3 (
    explorer "%~dp0output"
    goto :end
)
if errorlevel 2 (
    for /f "delims=" %%f in ('dir /b /o-d "%~dp0output\HANDOFF_TO_01_*.md"') do (
        notepad "%~dp0output\%%f"
        goto :end
    )
)
if errorlevel 1 (
    notepad "%~dp0PROGRESS.md"
    goto :end
)

:end
exit /b 0
