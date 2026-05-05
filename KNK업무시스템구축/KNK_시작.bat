@echo off
REM ============================================================
REM   LAST UPDATE: 2026-05-05 v5H145 소모품 발주 등록 흐름 강화 + 관련부서 통보. 엑셀 업로드 확정 후 큰 성공 카드(라인검토/통보발송/추가등록 3버튼) + 3.5초 자동 redirect. POST /consumables/{co_id}/notify 신설(자재구매·admin 일괄 알림 INSERT). consumable_detail.html 에 [📤 관련부서 통보] 버튼. 메뉴 위치는 v5H143 에서 이미 M-01 이동 완료.
REM   Full changelog: ../CHANGELOG.md
REM ============================================================
chcp 65001 >nul
title KNK HAIST WORKS [v5H144]
cd /d "%~dp001_HAIST_WORKS"

echo.
echo ============================================================
echo    HAIST WORKS  ^| KNK Integrated Work Platform
echo    Human ^& AI create the Best
echo    [v5H144  2026-05-05]
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
