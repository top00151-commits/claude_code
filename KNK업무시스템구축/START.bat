@echo off
REM ============================================================
REM   LAST UPDATE: 2026-05-05 v5H154 고객사 엑셀 일괄 등록 신설. /customers/import-template (양식 다운로드) + /customers/import-xlsx (파싱·검증·미리보기 JSON) + /customers/import-confirm (UPSERT) 3개 라우트 신설. '고객사' 시트 row7+ 파싱, 10컬럼 매핑(고객사명/사업자번호/대표/담당자/전화/이메일/주소/등급/활성/비고), 검증(사업자번호 10자리·이메일 형식·등급 A/B/C/VIP·활성 1/0). 동일 이름 존재 시 빈 칸 아닌 필드만 UPDATE(기존 데이터 보호) / 신규 INSERT, 사업자번호 중복(다른 이름)은 경고만. customers_list.html 상단에 [📥 양식 다운로드][📤 엑셀 일괄 업로드] 버튼 + 미리보기 모달(신규/업데이트 카운트·동작 pill·검증결과). 권한: can_use_sales.
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
