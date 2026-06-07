@echo off
REM === 메신저 OpenAI 키 설정 (NAS 서버) ===
REM LAST UPDATE: 2026-05-31 - 대표님이 키 입력 -> NAS /opt/knk_messenger/.env 갱신 + 메신저 재시작
REM   (로컬용 OpenAI키설정.bat 와 다름. 이건 운영 서버(NAS)에 키를 넣는 용도)
chcp 65001 >nul
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File ".\deploy\set_nas_openai_key.ps1"
echo.
pause
