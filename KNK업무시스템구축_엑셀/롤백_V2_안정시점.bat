@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo ================================================================
echo   !!  V2 -> 안정 시점(v2026.04g_20260502) 롤백  !!
echo ================================================================
echo.
echo   동작:
echo     1. 현재 V2 -> V2_롤백전백업_{타임스탬프} 로 자동 백업
echo     2. V2_안정_v2026.04g_20260502 -> V2 로 복구
echo.
echo   복구 시점: 2026-05-02 (v2026.04g)
echo     - .bat BEL 0x07 패치 완료
echo     - 매출 사이클 8_매출마감 dry-run 검증
echo     - 6/7대장 최신순 정렬
echo     - 관리코드 채번 버그 수정 (영업단계 빈 칸 시 X)
echo     - 신규 입력 영역 셀 서식 (buffer 30)
echo     - column-level protection (빈 행 입력 가능)
echo     - 관리코드 일관성 검증 + 노랑/파랑 + 9_불일치 시트
echo     - 데이터초기화.bat 3개 (knk1234)
echo.
echo ----------------------------------------------------------------
echo.
set /p pwd="비밀번호 입력: "
if not "!pwd!"=="knk1234" (
    echo.
    echo   [X] 비밀번호 오류. 작업 취소.
    pause
    exit /b 1
)

echo.
echo   ! 마지막 확인 ! 정말 롤백하시겠습니까?
echo.
echo   주의: 현 V2 작업 내용은 V2_롤백전백업_{타임스탬프} 폴더에 보존됩니다.
echo.
set /p confirm="   롤백 진행: Y 입력 후 Enter (취소: 다른 키): "
if /i not "!confirm!"=="Y" (
    echo.
    echo   취소되었습니다.
    pause
    exit /b 1
)

rem 타임스탬프 생성 (YYYYMMDD_HHMMSS)
for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /value') do set datetime=%%I
set TS=!datetime:~0,8!_!datetime:~8,6!
set BACKUP_NAME=V2_롤백전백업_!TS!

echo.
echo [1/2] 현 V2 -> !BACKUP_NAME! 백업 중...
echo ----------------------------------------------------------------
if not exist "V2" (
    echo   [X] V2 폴더가 없습니다.
    pause
    exit /b 1
)
xcopy "V2" "!BACKUP_NAME!\" /E /I /Q /Y >nul
if errorlevel 1 (
    echo   [X] 백업 실패.
    pause
    exit /b 1
)
echo   [OK] 백업 완료: !BACKUP_NAME!

echo.
echo [2/2] 안정 시점 -> V2 복구 중...
echo ----------------------------------------------------------------
if not exist "V2_안정_v2026.04g_20260502" (
    echo   [X] 안정 스냅샷 폴더가 없습니다: V2_안정_v2026.04g_20260502
    echo       빅터에게 알려주세요.
    pause
    exit /b 1
)
rmdir /S /Q "V2" 2>nul
xcopy "V2_안정_v2026.04g_20260502" "V2\" /E /I /Q /Y >nul
if errorlevel 1 (
    echo   [X] 복구 실패. 백업(!BACKUP_NAME!)에서 수동 복원 필요.
    pause
    exit /b 1
)
echo   [OK] 복구 완료

echo.
echo ================================================================
echo   [OK] 롤백 완료
echo.
echo   현재 V2 = V2_안정_v2026.04g_20260502 시점
echo   롤백 전 작업물: !BACKUP_NAME!/ 에 보존됨 (필요 시 복원 가능)
echo ================================================================
timeout /t 8 >nul
exit /b 0
