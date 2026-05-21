@echo off
REM ============================================================
REM   KNK HAIST WORKS - Claude(AI) API Key Register
REM   v5H226z108n18 (2026-05-21)
REM   ASCII-only content (avoids Korean codepage corruption).
REM   The key is NOT stored in any file - only as Windows
REM   user environment variable ANTHROPIC_API_KEY.
REM ============================================================
title KNK AI API Key Register

echo.
echo  ============================================================
echo    Claude(AI) API Key Registration
echo  ============================================================
echo.
echo   - Get your key at: https://console.anthropic.com  (menu: API Keys)
echo   - Key format example: sk-ant-api03-XXXXXXXX...
echo   - The key is NOT saved to any file. It is stored only as a
echo     Windows user environment variable (ANTHROPIC_API_KEY).
echo.

powershell -NoProfile -Command "$k = Read-Host -AsSecureString 'Paste API key here (hidden while typing), then Enter'; $p = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($k)); if ([string]::IsNullOrWhiteSpace($p)) { Write-Host '[Cancelled] empty - not registered.'; exit 1 }; if (-not $p.StartsWith('sk-')) { Write-Host '[Warn] does not start with sk- (registering anyway).' }; [Environment]::SetEnvironmentVariable('ANTHROPIC_API_KEY', $p, 'User'); Write-Host ('[OK] Registered: ' + $p.Substring(0,7) + '...' + $p.Substring($p.Length-4))"

if errorlevel 1 (
    echo.
    echo  Registration cancelled or failed.
    echo.
    pause
    exit /b 1
)

echo.
echo  ============================================================
echo   NEXT STEPS
echo    1) Close the running KNK server window (or run KNK stop bat)
echo    2) Start the server again (KNK start bat)
echo    3) In the startup log, look for:  [AI] Claude ...
echo  ============================================================
echo.
echo   Note: the new key applies to newly opened windows only.
echo.
pause
