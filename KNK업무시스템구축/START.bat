@echo off
REM ============================================================
REM   LAST UPDATE: 2026-05-05 v5H146 소모품 발주 등록 흐름 강화 + 관련부서 통보. 엑셀 업로드 확정 후 큰 성공 카드(라인검토/통보발송/추가등록 3버튼) + 3.5초 자동 redirect. POST /consumables/{co_id}/notify 신설(자재구매·admin 일괄 알림 INSERT). consumable_detail.html 에 [📤 관련부서 통보] 버튼. 메뉴 위치는 v5H143 에서 이미 M-01 이동 완료.
REM   (full changelog: ../CHANGELOG.md)
REM   Rule: 01 session updates this single-line summary on each code change
REM ============================================================
cd /d "%~dp001_HAIST_WORKS"
title KNK HAIST WORKS - HAIST Innovation [v5H144]

echo.
echo ============================================================
echo    HAIST WORKS  ^|  KNK Integrated Work Platform
echo    Human ^& AI create the Best
echo    [v5H144  2026-05-05]
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
