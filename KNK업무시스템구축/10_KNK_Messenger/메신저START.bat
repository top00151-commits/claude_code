@echo off
REM === KNK Messenger Launcher (auto-opens app window) ===
REM LAST UPDATE: 2026-05-11 - Auto-load .env (ANTHROPIC_API_KEY 등 자동 설정)
cd /d "%~dp0"
cls
echo.
echo  ============================================
echo    KNK Messenger - Internal Test Server
echo  ============================================
echo.
echo    Starting server... a separate app window
echo    will open automatically in 4 seconds.
echo.
echo    Accounts (password: knk1234)
echo      - CEO  : kjr
echo      - Beta : lhr / lh / okh / bsj / ajy / lsr
echo.
echo    To stop: close this window or Ctrl+C
echo  ============================================
echo.

REM === .env 파일 자동 로드 (ANTHROPIC_API_KEY 등 환경변수) ===
REM .env 파일이 있으면 KEY=VALUE 라인을 환경변수로 설정한다.
REM 주석(#) 과 빈 줄은 건너뜀.
if exist ".env" (
  echo  [info] .env loaded
  for /f "usebackq tokens=1,* delims==" %%a in (".env") do (
    if not "%%a"=="" if not "%%a:~0,1%"=="#" set "%%a=%%b"
  )
)
if defined ANTHROPIC_API_KEY (
  echo  [info] AI translation: ENABLED
) else (
  echo  [info] AI translation: OFF (.env 에 ANTHROPIC_API_KEY 추가 시 활성)
)
echo.

REM Find Chrome or Edge
set "BROWSER="
if exist "C:\Program Files\Google\Chrome\Application\chrome.exe" set "BROWSER=C:\Program Files\Google\Chrome\Application\chrome.exe"
if "%BROWSER%"=="" if exist "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe" set "BROWSER=C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
if "%BROWSER%"=="" if exist "%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe" set "BROWSER=%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"
if "%BROWSER%"=="" if exist "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" set "BROWSER=C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
if "%BROWSER%"=="" if exist "C:\Program Files\Microsoft\Edge\Application\msedge.exe" set "BROWSER=C:\Program Files\Microsoft\Edge\Application\msedge.exe"

REM Background: wait 4 seconds, then open Chrome/Edge in app mode (separate window)
if not "%BROWSER%"=="" (
  start "" /B cmd /c "ping 127.0.0.1 -n 5 -w 1000 > nul & start "" "%BROWSER%" --app=http://localhost:5050 --window-size=1200,800"
) else (
  REM Fallback: just open default browser
  start "" /B cmd /c "ping 127.0.0.1 -n 5 -w 1000 > nul & start http://localhost:5050"
)

REM Foreground: server (blocking)
py app.py

echo.
echo  Server stopped. Press any key to close.
pause >nul
