@echo off
REM === KNK Messenger Launcher (auto-opens browser) ===
REM LAST UPDATE: 2026-05-06 - Auto-open browser after 3s
cd /d "%~dp0"
cls
echo.
echo  ============================================
echo    KNK Messenger  (10_KNK_Messenger)
echo  ============================================
echo.
echo    A browser tab will open in 3 seconds.
echo    If not, manually visit: http://localhost:5050
echo.
echo    Mobile: http://[this-PC-IP]:5050
echo.
echo    Accounts (password: knk1234)
echo      - CEO  : kjr
echo      - Beta : lhr / lh / okh / bsj / ajy / lsr
echo.
echo    To stop the server: close this window or Ctrl+C
echo  ============================================
echo.

REM Background task: wait 3s then open browser
start "" /B cmd /c "ping 127.0.0.1 -n 4 -w 1000 > nul & start http://localhost:5050"

REM Foreground: run server (blocking)
py app.py

echo.
echo  Server stopped. Press any key to close.
pause >nul
