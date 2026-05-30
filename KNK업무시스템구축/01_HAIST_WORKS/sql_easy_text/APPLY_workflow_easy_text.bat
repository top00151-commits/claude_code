@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

REM ============================================================
REM   workflow_template 5개 시나리오 텍스트 쉬운 표현 적용 도구
REM   대표 직접 지시 (2026-05-12) 즉시 실행용
REM ============================================================

set DB="%~dp0..\..\01_HAIST_WORKS\data\haist_works.db"
set SQL="%~dp0workflow_scenarios_excel_corrected.sql"
set BAK_DIR="%~dp0..\..\01_HAIST_WORKS\data\backup"
set BAK_TIME=%date:~0,4%%date:~5,2%%date:~8,2%_%time:~0,2%%time:~3,2%
set BAK_TIME=%BAK_TIME: =0%
set BAK_FILE="%~dp0..\..\01_HAIST_WORKS\data\backup\haist_works_pre_easy_text_%BAK_TIME%.db"

echo.
echo ============================================================
echo  workflow_template 5 scenarios easy-text UPDATE
echo ============================================================
echo.
echo  DB :  %DB%
echo  SQL:  %SQL%
echo.

if not exist %DB% (
    echo [ERROR] DB file not found: %DB%
    pause
    exit /b 1
)

if not exist "%~dp0..\..\01_HAIST_WORKS\data\backup" mkdir "%~dp0..\..\01_HAIST_WORKS\data\backup"

echo [Step 1] Backing up DB...
copy %DB% %BAK_FILE% >nul
if errorlevel 1 (
    echo [ERROR] Backup failed.
    pause
    exit /b 1
)
echo   Backup OK -^> %BAK_FILE%
echo.

echo [Step 2] Checking sqlite3 ...
where sqlite3 >nul 2>&1
if errorlevel 1 (
    echo [WARN] sqlite3 CLI not found on PATH.
    echo        Please install sqlite3 or run the SQL via DB Browser for SQLite.
    echo        SQL file location: %SQL%
    pause
    exit /b 2
)

echo [Step 3] Applying SQL...
sqlite3 %DB% < %SQL%
if errorlevel 1 (
    echo [ERROR] SQL apply failed. DB backup is at: %BAK_FILE%
    pause
    exit /b 3
)
echo   SQL applied OK.
echo.

echo [Step 4] Verification (5 rows shown below):
sqlite3 %DB% "SELECT code, title_ko FROM workflow_template ORDER BY 'order';"
echo.

echo [DONE] Workflow scenarios easy-text applied.
echo  Please refresh /workflow page (Ctrl+F5) and verify.
echo.
pause
