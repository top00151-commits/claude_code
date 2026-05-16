@echo off
REM ============================================================
REM   LAST UPDATE: 2026-05-16 v5H226z108 (워크플로우 단순화 — /home 단일 진입점 + [✓끝] 원샷 자동화(체크포인트+task+노드+알림) + 사이드바 다이어트(일반직원 워크플로우 메뉴 숨김))
REM   - BAT line-length 8192 limit fix (REM truncated, full log -> CHANGELOG.md)
REM   - v5H226c soconsumable Excel upload: image extract + header auto-mapping
REM   - v5H226b INSERT column-name bug fix (qty/unit_price/amount)
REM   - v5H226 consumable line-input feature (+ excel modal + paste image preview)
REM   Full changelog: ./CHANGELOG.md
REM ============================================================
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
title KNK HAIST WORKS [v5H226z108]
cd /d "%~dp001_HAIST_WORKS"

echo.
echo ============================================================
echo    HAIST WORKS  ^| KNK Integrated Work Platform
echo    Human ^& AI create the Best
echo    [v5H226z108  2026-05-16]
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
