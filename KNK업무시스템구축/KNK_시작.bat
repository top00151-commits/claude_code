@echo off
REM ============================================================
REM   LAST UPDATE: 2026-05-05 v5H152 프로젝트 엑셀 일괄 등록 신설. /projects/import-template (양식 .xlsx 다운로드) + /projects/import-xlsx (업로드·파싱·검증·미리보기 JSON) + /projects/import-confirm (확정 INSERT) 3개 라우트 신설. T_검사기/M_자동화 시트 row5+ 파싱, 16컬럼 매핑, 검증(통화 KRW/USD/VND·상태 화이트리스트·수량 1-100·단가≥0·날짜 YYYY-MM-DD), 미등록 고객사는 경고만. chooser 페이지에 [📥 양식 다운로드][📤 엑셀 업로드] 버튼 + 미리보기 모달(표·검증결과·정상건수 카운트·등록확정).
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
