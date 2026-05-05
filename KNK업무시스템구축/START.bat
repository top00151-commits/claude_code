@echo off
REM ============================================================
REM   LAST UPDATE: 2026-05-05 v5H142 소모품 발주 전용 도메인 신설 — consumable_orders/items 테이블 + 엑셀 일괄 import + 이미지 자동 압축(1920px JPEG q85, 평균 88% 절감) + 자재/관리번호 자동매칭 + /consumables 라우트 8건 + 3개 신규 템플릿. 관리번호 발급/자동 SO 모두 NEW_EQUIP만 트리거(소모품·수리·기타 차단). 프로젝트 상세에 "📦 소모품 발주 이력" 카드 추가.
REM   (full changelog: ../CHANGELOG.md)
REM   Rule: 01 session updates this single-line summary on each code change
REM ============================================================
cd /d "%~dp001_HAIST_WORKS"
title KNK HAIST WORKS - HAIST Innovation [v5H142]

echo.
echo ============================================================
echo    HAIST WORKS  ^|  KNK Integrated Work Platform
echo    Human ^& AI create the Best
echo    [v5H142  2026-05-05]
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
