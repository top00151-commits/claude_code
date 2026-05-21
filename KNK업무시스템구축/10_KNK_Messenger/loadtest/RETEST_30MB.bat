@echo off
cd /d "%~dp0"
echo.
echo =====================================================
echo   KNK Messenger - Retest 30MB x 75
echo =====================================================
echo.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "retest_30mb.ps1"
pause >nul
