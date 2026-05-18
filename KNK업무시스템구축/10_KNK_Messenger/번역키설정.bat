@echo off
REM === Anthropic API 키 등록 (1회 설정) ===
REM LAST UPDATE: 2026-05-11 - 신규 작성, .env 파일 자동 작성
chcp 65001 > nul
setlocal
cd /d "%~dp0"

echo.
echo ===============================================
echo   KNK 메신저 - 번역 기능 활성화 (1회 설정)
echo ===============================================
echo.
echo  Claude AI 번역을 사용하려면 Anthropic API 키가 필요합니다.
echo.
echo  1) 키 발급:  https://console.anthropic.com
echo                -^> API Keys -^> Create Key
echo                -^> 키 복사 (sk-ant-api03-... 로 시작)
echo.
echo  2) 아래에 키를 붙여넣고 Enter
echo     (붙여넣기: 마우스 우클릭 또는 Ctrl+V)
echo.

set /p APIKEY="    ANTHROPIC_API_KEY = "

if "%APIKEY%"=="" (
  echo.
  echo  [취소] 키가 입력되지 않았습니다.
  pause
  exit /b 1
)

REM 형식 가벼운 검증
echo %APIKEY% | findstr /B "sk-ant-" > nul
if errorlevel 1 (
  echo.
  echo  [경고] 키가 'sk-ant-' 로 시작하지 않습니다. 정말 맞으십니까?
  set /p YN="    그래도 저장할까요? (Y/N): "
  if /I not "%YN%"=="Y" exit /b 1
)

REM .env 파일 작성 (기존 ANTHROPIC_API_KEY 줄은 제거하고 새로 추가)
if exist ".env" (
  REM 기존 ANTHROPIC_API_KEY 라인 제거
  findstr /V /B /C:"ANTHROPIC_API_KEY=" ".env" > ".env.tmp"
  move /Y ".env.tmp" ".env" > nul
)

echo ANTHROPIC_API_KEY=%APIKEY%>> ".env"

echo.
echo ===============================================
echo   저장 완료: .env 파일에 키 등록됨
echo ===============================================
echo.
echo  다음 단계:
echo   1) 메신저START.bat 가 켜져 있으면 Ctrl+C 로 종료
echo   2) 메신저START.bat 다시 더블클릭
echo   3) 채팅방에서 [VN 베트남어] 토글 ON 후 메시지 입력 -^> 전송
echo.
echo  Tip: .env 파일은 텍스트 편집기로 직접 열어 수정 가능.
echo       파일 권한: 본인만 읽도록 보관 (절대 외부 공유 금지).
echo.
pause
