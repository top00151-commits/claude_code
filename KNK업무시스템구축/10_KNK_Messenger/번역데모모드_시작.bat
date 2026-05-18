@echo off
REM === 번역 데모 모드 (Mock) ===
REM LAST UPDATE: 2026-05-11 - app.py 가 dev 모드 + 키 없으면 자동 mock 활성하므로 이 파일은 폴백/명시용
chcp 65001 > nul
setlocal
cd /d "%~dp0"

echo.
echo ===============================================
echo   KNK 메신저 - 번역 데모 모드로 시작
echo ===============================================
echo.
echo  Anthropic API 키 없이 UI 흐름만 테스트합니다.
echo  - 가짜 번역 (KNK 핵심 용어만 실제 변환)
echo  - 비용 0원, 즉시 응답
echo  - 실제 번역 품질은 알 수 없음
echo.
echo  실제 번역을 원하시면:
echo    1) 종료 후 번역키설정.bat 실행
echo    2) 일반 메신저START.bat 실행
echo ===============================================
echo.

set "KNK_MSG_TRANSLATE_MOCK=1"

REM === .env 파일 자동 로드 ===
if exist ".env" (
  echo  [info] .env loaded
  for /f "usebackq tokens=1,* delims==" %%a in (".env") do (
    if not "%%a"=="" if not "%%a:~0,1%"=="#" set "%%a=%%b"
  )
)

REM 데모 모드는 .env 의 ANTHROPIC_API_KEY 를 무시
set "KNK_MSG_TRANSLATE_MOCK=1"

echo  [DEMO MODE] 번역 가짜 실행, 비용 0
echo.

REM Find Chrome or Edge
set "BROWSER="
if exist "C:\Program Files\Google\Chrome\Application\chrome.exe" set "BROWSER=C:\Program Files\Google\Chrome\Application\chrome.exe"
if "%BROWSER%"=="" if exist "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe" set "BROWSER=C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
if "%BROWSER%"=="" if exist "%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe" set "BROWSER=%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"
if "%BROWSER%"=="" if exist "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" set "BROWSER=C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
if "%BROWSER%"=="" if exist "C:\Program Files\Microsoft\Edge\Application\msedge.exe" set "BROWSER=C:\Program Files\Microsoft\Edge\Application\msedge.exe"

if not "%BROWSER%"=="" (
  start "" /B cmd /c "ping 127.0.0.1 -n 5 -w 1000 > nul & start "" "%BROWSER%" --app=http://localhost:5050 --window-size=1200,800"
) else (
  start "" /B cmd /c "ping 127.0.0.1 -n 5 -w 1000 > nul & start http://localhost:5050"
)

py app.py

echo.
echo  Server stopped. Press any key to close.
pause >nul
