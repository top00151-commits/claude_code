@echo off
REM ============================================================
REM   LAST UPDATE: 2026-05-18 v5H226z108n12 (프로젝트 체크리스트 — 행 한줄 정렬 / 부서·담당자 인라인 / 행 높이 축소)
REM   - v5H226z108n12 마법사 우측 사이드 — 실시간 시나리오 미리보기 + 선택 요약 + 4가지 형태 안내
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
title KNK HAIST WORKS - HAIST Innovation [v5H226z108n12]

echo.
echo ============================================================
echo    HAIST WORKS  ^|  KNK Integrated Work Platform
echo    Human ^& AI create the Best
echo    [v5H226z108n12  2026-05-18]
echo ============================================================
echo.

REM z108n12: 8081 좀비 워커 자동 청소 (uvicorn reload Windows orphan 방지)
powershell -NoProfile -Command "$p = Get-NetTCPConnection -LocalPort 8081 -State Listen -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique; foreach ($i in $p) { Stop-Process -Id $i -Force -ErrorAction SilentlyContinue }; $orphan = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -match 'spawn_main.*parent_pid' -and -not (Get-Process -Id $_.ParentProcessId -ErrorAction SilentlyContinue) }; foreach ($o in $orphan) { Stop-Process -Id $o.ProcessId -Force -ErrorAction SilentlyContinue }" >nul 2>nul

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
