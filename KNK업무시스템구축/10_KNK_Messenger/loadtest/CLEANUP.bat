@echo off
cd /d "%~dp0"
echo.
echo =====================================================
echo   KNK Messenger Load Test - Cleanup Only
echo =====================================================
echo.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "cleanup_only.ps1"
echo.
pause >nul
