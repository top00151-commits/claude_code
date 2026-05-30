@echo off
REM ============================================================
REM   KNK HAIST WORKS - 운영 모드 시작 스크립트 (v5H226f-2)
REM   - reload off, workers 2, host 127.0.0.1 (역방향 프록시 뒤 가정)
REM   - 운영 SECRET_KEY 미설정 시 시작 거부
REM   인터넷 노출 전 체크리스트:
REM     1) HTTPS 역방향 프록시 (Nginx/Caddy) 앞단 배치
REM     2) 방화벽 8081 외부 차단, 프록시만 접근
REM     3) KNK_SECRET_KEY 환경변수 설정 (32+ 문자열)
REM     4) 백업 자동화 (data/knk.db, uploads/)
REM   Full changelog: ./CHANGELOG.md
REM ============================================================
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
set KNK_MODE=prod
title KNK HAIST WORKS [PRODUCTION]
cd /d "%~dp001_HAIST_WORKS"

REM -- SECRET_KEY 검증 (운영 시 필수) --
if "%KNK_SECRET_KEY%"=="" (
    echo.
    echo [ERROR] 운영 모드에서는 KNK_SECRET_KEY 환경변수 필수입니다.
    echo         예: setx KNK_SECRET_KEY "your-32-char-random-string"
    echo         설정 후 새 콘솔에서 다시 실행하세요.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo    HAIST WORKS  ^| PRODUCTION MODE
echo    [v5H226f-2  2026-05-08]
echo ============================================================
echo.

where python >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python is not installed.
    pause
    exit /b 1
)

python -c "import fastapi, uvicorn, jinja2" >nul 2>nul
if errorlevel 1 (
    echo [ERROR] 필수 패키지 누락. KNK_시작.bat 으로 먼저 설치하세요.
    pause
    exit /b 1
)

echo Starting in PRODUCTION mode (reload off, workers 2)...
echo Press Ctrl+C to stop.
echo.
python run.py

echo.
echo Server stopped. Press any key to close.
pause >nul
