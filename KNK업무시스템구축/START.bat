@echo off
REM ============================================================
REM   LAST UPDATE: 2026-05-05 v5H152 프로젝트 엑셀 일괄 등록 신설. /projects/import-template (양식 .xlsx 다운로드) + /projects/import-xlsx (업로드·파싱·검증·미리보기 JSON) + /projects/import-confirm (확정 INSERT) 3개 라우트 신설. T_검사기/M_자동화 시트 row5+ 파싱, 16컬럼 매핑, 검증(통화 KRW/USD/VND·상태 화이트리스트·수량 1-100·단가≥0·날짜 YYYY-MM-DD), 미등록 고객사는 경고만. chooser 페이지에 [📥 양식 다운로드][📤 엑셀 업로드] 버튼 + 미리보기 모달(표·검증결과·정상건수 카운트·등록확정).
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
