@echo off
REM ============================================================
REM   01B 매출영업 작업 상태 확인 도구 (v3 ? 인코딩 혼합 처리)
REM   BAT 자체: CP949  /  외부 파일(UTF-8): 출력 시 65001 전환
REM   LAST UPDATE: 2026-05-10 v5H226z71
REM ============================================================
chcp 949 >nul
title 01B 매출영업 상태 확인
cd /d "%~dp0"

cls
echo.
echo ============================================================
echo    [01B] 매출영업 작업 상태 확인
echo    %DATE% %TIME:~0,8%
echo ============================================================
echo.

echo [1] 현재 시스템 버전
echo ------------------------------------------------------------
REM UTF-8 파일은 PowerShell로 -- findstr는 65001에서 "쓰기 오류" 버그
if exist "%~dp0..\KNK_시작.bat" powershell -NoProfile -Command "Get-Content -LiteralPath '%~dp0..\KNK_시작.bat' -Encoding UTF8 | Select-String '^REM   LAST UPDATE'"
if exist "%~dp0..\START.bat" powershell -NoProfile -Command "Get-Content -LiteralPath '%~dp0..\START.bat' -Encoding UTF8 | Select-String '^REM   LAST UPDATE'"
echo.

echo [2] 진행 현황 (PROGRESS.md)
echo ------------------------------------------------------------
chcp 65001 >nul
if exist "%~dp0PROGRESS.md" (type "%~dp0PROGRESS.md") else (echo PROGRESS.md 없음)
chcp 949 >nul
echo.

echo [3] 빅터 -^> 대표 보고서 (최신순)
echo ------------------------------------------------------------
if exist "%~dp0output" (dir /b /o-d "%~dp0output\HANDOFF_TO_01_*.md" 2>nul) else (echo output 폴더 없음)
echo.

echo [4] git log - 매출영업 관련 (최근 15건)
echo ------------------------------------------------------------
pushd "%~dp0..\..\" >nul 2>&1
chcp 65001 >nul
git log --oneline -15 -- "KNK업무시스템구축/01_HAIST_WORKS/app/templates/" "KNK업무시스템구축/01B_HAIST_WORKS_매출영업/" 2>nul
chcp 949 >nul
popd >nul 2>&1
echo.

echo [5] 미커밋 변경 (작업 중)
echo ------------------------------------------------------------
pushd "%~dp0..\..\" >nul 2>&1
chcp 65001 >nul
git -c core.quotepath=false status -s -- "KNK업무시스템구축/01_HAIST_WORKS/app/templates/" "KNK업무시스템구축/01B_HAIST_WORKS_매출영업/" 2>nul
chcp 949 >nul
popd >nul 2>&1
echo.

echo ============================================================
echo    더 자세히 보기:
echo      P) PROGRESS.md 메모장 열기
echo      L) 최신 HANDOFF 메모장 열기
echo      O) output 폴더 탐색기 열기
echo      G) GitHub 브랜치 페이지 열기
echo      Q) 종료
echo ============================================================
echo.
choice /c PLOGQ /n /m "선택 (P/L/O/G/Q): "
if errorlevel 5 goto :end
if errorlevel 4 (
    start "" "https://github.com/top00151-commits/claude_code/tree/claude/charming-yonath-a72046/KNK업무시스템구축/01B_HAIST_WORKS_매출영업"
    goto :end
)
if errorlevel 3 (
    start "" explorer "%~dp0output"
    goto :end
)
if errorlevel 2 (
    for /f "delims=" %%f in ('dir /b /o-d "%~dp0output\HANDOFF_TO_01_*.md" 2^>nul') do (
        start "" notepad "%~dp0output\%%f"
        goto :end
    )
)
if errorlevel 1 (
    start "" notepad "%~dp0PROGRESS.md"
    goto :end
)

:end
echo.
echo 종료. (창을 닫으려면 아무 키나 누르세요)
pause >nul
exit /b 0
