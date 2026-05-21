@echo off
cd /d "%~dp0"
echo.
echo =====================================================
echo   KNK Messenger Load Test Phase 3
echo =====================================================
echo.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "run_loadtest.ps1"
echo.
echo =====================================================
echo   Done. Press any key to close.
echo =====================================================
pause >nul
