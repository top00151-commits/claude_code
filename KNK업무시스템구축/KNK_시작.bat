@echo off
REM ============================================================
REM   LAST UPDATE: 2026-05-05 v5H142 소모품 발주 전용 도메인 신설 — consumable_orders/items 테이블 + 엑셀 일괄 import + 이미지 자동 압축(1920px JPEG q85, 평균 88% 절감) + 자재/관리번호 자동매칭 + /consumables 라우트 8건 + 3개 신규 템플릿. 관리번호 발급/자동 SO 모두 NEW_EQUIP만 트리거(소모품·수리·기타 차단). 프로젝트 상세에 "📦 소모품 발주 이력" 카드 추가.
REM   Full changelog: ../CHANGELOG.md
REM ============================================================
chcp 65001 >nul
title KNK HAIST WORKS [v5H142]
cd /d "%~dp001_HAIST_WORKS"

echo.
echo ============================================================
echo    HAIST WORKS  ^| KNK Integrated Work Platform
echo    Human ^& AI create the Best
echo    [v5H142  2026-05-05]
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
