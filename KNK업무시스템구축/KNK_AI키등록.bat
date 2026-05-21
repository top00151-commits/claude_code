@echo off
REM ============================================================
REM   KNK HAIST WORKS — Claude(AI) API 키 등록 도우미
REM   v5H226z108n17 (2026-05-21)
REM   - 키를 이 파일이나 어떤 파일에도 저장하지 않음 (보안)
REM   - 입력한 키를 Windows 사용자 환경변수 ANTHROPIC_API_KEY 로 영구 등록
REM   - 등록 후 서버(KNK_시작.bat) 재시작하면 AI 기능 활성화
REM ============================================================
chcp 65001 >nul
title KNK AI API 키 등록

echo.
echo ============================================================
echo    Claude(AI) API 키 등록
echo ============================================================
echo.
echo  - 키는 화면·파일에 저장되지 않고 OS 환경변수로만 등록됩니다.
echo  - 키는 https://console.anthropic.com 의 API Keys 에서 발급.
echo  - 형식 예: sk-ant-api03-XXXXXXXX...
echo.

REM 현재 등록 상태 표시 (값은 마스킹)
if defined ANTHROPIC_API_KEY (
    echo  [현재] 이미 등록된 키가 있습니다. 새로 입력하면 덮어씁니다.
) else (
    echo  [현재] 등록된 키 없음.
)
echo.

REM PowerShell 보안 입력(화면에 안 보임) → setx 로 영구 등록. 키는 파일에 안 남음.
powershell -NoProfile -Command ^
  "$k = Read-Host -AsSecureString '여기에 API 키 붙여넣기 (입력 시 화면에 안 보임)';" ^
  "$p = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($k));" ^
  "if ([string]::IsNullOrWhiteSpace($p)) { Write-Host '[취소] 빈 값 — 등록 안 함.'; exit 1 }" ^
  "if (-not $p.StartsWith('sk-')) { Write-Host '[경고] sk- 로 시작하지 않습니다. 그래도 등록합니다.' }" ^
  "[Environment]::SetEnvironmentVariable('ANTHROPIC_API_KEY', $p, 'User');" ^
  "Write-Host ('[완료] 등록됨: ' + $p.Substring(0,7) + 'xxxx...' + $p.Substring($p.Length-4))"

if errorlevel 1 (
    echo.
    echo 등록이 취소되었거나 실패했습니다.
    echo.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo  [다음 단계]
echo   1) 열려있는 KNK 서버 창을 닫고 (또는 KNK_중지.bat)
echo   2) KNK_시작.bat 을 다시 실행하세요.
echo   3) 서버 시작 로그에 [AI] Claude 연동 활성 가 보이면 완료.
echo ============================================================
echo.
echo  ※ 방금 등록한 키는 새로 여는 창부터 적용됩니다 (현재 창에는 미적용).
echo.
pause
