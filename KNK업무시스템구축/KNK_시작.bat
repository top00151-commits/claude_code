@echo off
REM ============================================================
REM   LAST UPDATE: 2026-05-05 v5H148 프로젝트 등록 진입점 통합(대표 직접 지시). 사이드바 재편: 🆕 프로젝트 등록 / 📊 프로젝트 목록 / 📦 소모품 발주 목록. /projects/new GET 가 type 없으면 4-카드 chooser(T검사기·M자동화·기타·소모품)를 렌더, type 있으면 기존 폼 + biz_div/project_type 사전 선택 + "← 다른 유형으로 변경" 링크. project_new_chooser.html 신설(KNK 톤 카드 4종). 백워드 호환 유지.
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
