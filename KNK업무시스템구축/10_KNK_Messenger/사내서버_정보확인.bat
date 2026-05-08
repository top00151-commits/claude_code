@echo off
chcp 65001 > nul
cd /d "%~dp0"
echo.
echo ===========================================
echo   KNK 메신저 - 사내 서버 정보 확인
echo ===========================================
echo.
PowerShell -NoProfile -ExecutionPolicy Bypass -File "%~dp0사내서버_정보확인.ps1"
pause
