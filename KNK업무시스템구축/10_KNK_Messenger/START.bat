@echo off
REM === KNK Messenger Launcher (LAN/VPN test deployment) ===
REM LAST UPDATE: 2026-05-06 - Auto secret + LAN IP display + auto-open browser
cd /d "%~dp0"
cls
echo.
echo  ============================================
echo    KNK Messenger - Internal Test Server
echo  ============================================
echo.
echo    A browser will open in 3 seconds (this PC).
echo    Other employees use the URL printed below
echo    after the server is ready.
echo.
echo    Accounts (password: knk1234)
echo      - CEO  : kjr
echo      - Beta : lhr / lh / okh / bsj / ajy / lsr
echo.
echo    To stop: close this window or Ctrl+C
echo  ============================================
echo.

REM Background task: wait 3s then open local browser
start "" /B cmd /c "ping 127.0.0.1 -n 4 -w 1000 > nul & start http://localhost:5050"

REM Foreground: run server (will print employee URLs)
py app.py

echo.
echo  Server stopped. Press any key to close.
pause >nul
