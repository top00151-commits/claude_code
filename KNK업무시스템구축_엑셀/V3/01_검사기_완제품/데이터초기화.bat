@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo ================================================================
echo   !!  KNK 검사기 PMS - 데이터 전체 초기화  !!
echo ================================================================
echo.
echo   대상: 01_검사기_완제품 폴더의 모든 .xlsx 파일
echo   삭제: R5+ 모든 데이터 (제목·헤더·서식·드롭다운은 보존)
echo   백업: _참고용_원본데이터/{타임스탬프}/ 자동 보존
echo.
echo ----------------------------------------------------------------
echo.
set /p pwd="비밀번호 입력: "
if not "!pwd!"=="knk1234" (
    echo.
    echo   [X] 비밀번호가 틀렸습니다. 작업 취소.
    echo.
    pause
    exit /b 1
)

echo.
echo   ! 마지막 확인 ! 정말 모든 데이터를 삭제하시겠습니까?
echo     (백업은 자동으로 보존되지만 신중하게 결정해주세요)
echo.
set /p confirm="   삭제 진행: Y 입력 후 Enter (취소: 다른 키): "
if /i not "!confirm!"=="Y" (
    echo.
    echo   취소되었습니다.
    echo.
    pause
    exit /b 1
)

echo.
echo [1/3] 데이터 삭제 + 자동 백업...
echo ----------------------------------------------------------------
python -X utf8 scripts\reset_to_empty.py
if errorlevel 1 goto :ERROR

echo.
echo [2/3] sync.py 실행 (빈 상태 정리)...
echo ----------------------------------------------------------------
python -X utf8 scripts\sync.py
if errorlevel 1 goto :ERROR

echo.
echo [3/3] apply_standard.py 실행 (스펙 정규화)...
echo ----------------------------------------------------------------
python -X utf8 scripts\apply_standard.py
if errorlevel 1 goto :ERROR

echo.
echo ================================================================
echo   [OK] 초기화 완료. 5초 후 자동 종료.
echo ================================================================
timeout /t 5 >nul
exit /b 0

:ERROR
echo.
echo ================================================================
echo   [오류] 위 메시지 확인 후 Enter 누르면 창이 닫힙니다.
echo ================================================================
pause
exit /b 1
