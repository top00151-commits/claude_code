@echo off
REM ============================================================
REM   KNK HAIST WORKS - AI API Key Register (Claude / OpenAI)
REM   v5H226z108n19 (2026-05-21)
REM   ASCII-only content (avoids Korean codepage corruption).
REM   Key is NOT stored in any file - only as Windows user
REM   environment variable.
REM ============================================================
title KNK AI API Key Register
setlocal

echo.
echo  ============================================================
echo    AI API Key Registration  (choose provider)
echo  ============================================================
echo.
echo    1) Claude  (Anthropic)   key var: ANTHROPIC_API_KEY
echo    2) OpenAI                 key var: OPENAI_API_KEY
echo.
set "CHOICE="
set /p CHOICE=Select provider [1=Claude / 2=OpenAI]:

if "%CHOICE%"=="1" ( set "PROVIDER=claude" & set "KEYVAR=ANTHROPIC_API_KEY" & set "HINT=sk-ant-api03-..." )
if "%CHOICE%"=="2" ( set "PROVIDER=openai" & set "KEYVAR=OPENAI_API_KEY"    & set "HINT=sk-..." )

if not defined PROVIDER (
    echo.
    echo  [Cancelled] invalid choice ^(type 1 or 2^).
    echo.
    pause
    exit /b 1
)

echo.
echo   Provider : %PROVIDER%
echo   Key var  : %KEYVAR%
echo   Key form : %HINT%
echo   ^(Get key: Claude=console.anthropic.com / OpenAI=platform.openai.com^)
echo.

REM Secure input (hidden), set both the key var and KNK_AI_PROVIDER. Key never saved to file.
powershell -NoProfile -Command "$k = Read-Host -AsSecureString 'Paste API key (hidden), then Enter'; $p = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($k)); if ([string]::IsNullOrWhiteSpace($p)) { Write-Host '[Cancelled] empty - not registered.'; exit 1 }; [Environment]::SetEnvironmentVariable('%KEYVAR%', $p, 'User'); [Environment]::SetEnvironmentVariable('KNK_AI_PROVIDER', '%PROVIDER%', 'User'); Write-Host ('[OK] Registered ' + '%KEYVAR%' + ' = ' + $p.Substring(0,[Math]::Min(7,$p.Length)) + '...' + $p.Substring([Math]::Max(0,$p.Length-4))); Write-Host ('[OK] KNK_AI_PROVIDER = %PROVIDER%')"

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
echo    1) Close the running KNK server window (or KNK stop bat)
echo    2) Start the server again (KNK start bat)
echo    3) In the startup log, look for:  [AI] ... active
echo  ============================================================
echo.
echo   Note: applies to newly opened windows only.
echo   To switch provider later, just run this again.
echo.
pause
endlocal
