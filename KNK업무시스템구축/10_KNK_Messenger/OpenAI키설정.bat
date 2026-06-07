@echo off
REM === OpenAI (ChatGPT) API key registration ===
REM LAST UPDATE: 2026-05-27 - PowerShell launcher (Korean encoding stable)
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File ".\OpenAI_setup.ps1"
if errorlevel 1 (
  echo.
  echo [ERROR] PowerShell script failed. Press any key to close.
  pause >nul
)
