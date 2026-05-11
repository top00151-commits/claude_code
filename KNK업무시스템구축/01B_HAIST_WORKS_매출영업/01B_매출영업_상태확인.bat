@echo off
REM ============================================================
REM   01B 매출영업 상태 확인 + HTML 미리보기 (v4 ? 그룹별 8 단축키)
REM   더블클릭 -> 5섹션 정보 + 페이지 그룹 단축키 미리보기
REM   LAST UPDATE: 2026-05-10 v5H226z71
REM ============================================================
chcp 949 >nul
title 01B 매출영업 상태 + HTML 미리보기
cd /d "%~dp0"

cls
echo.
echo ============================================================
echo    [01B] 매출영업 작업 상태 + 페이지 미리보기
echo    %DATE% %TIME:~0,8%
echo ============================================================
echo.

echo [1] 현재 시스템 버전
echo ------------------------------------------------------------
if exist "%~dp0..\KNK_시작.bat" powershell -NoProfile -Command "Get-Content -LiteralPath '%~dp0..\KNK_시작.bat' -Encoding UTF8 | Select-String '^REM   LAST UPDATE'"
if exist "%~dp0..\START.bat" powershell -NoProfile -Command "Get-Content -LiteralPath '%~dp0..\START.bat' -Encoding UTF8 | Select-String '^REM   LAST UPDATE'"
echo.

echo [2] 진행 현황 (PROGRESS.md - 상위 30줄만)
echo ------------------------------------------------------------
chcp 65001 >nul
if exist "%~dp0PROGRESS.md" (powershell -NoProfile -Command "Get-Content -LiteralPath '%~dp0PROGRESS.md' -Encoding UTF8 -TotalCount 30") else (echo PROGRESS.md 없음)
chcp 949 >nul
echo.

echo [3] 빅터 -^> 대표 보고서 (최신순)
echo ------------------------------------------------------------
if exist "%~dp0output" (dir /b /o-d "%~dp0output\HANDOFF_TO_01_*.md" 2>nul) else (echo output 폴더 없음)
echo.

echo [4] git log - 매출영업 관련 (최근 10건)
echo ------------------------------------------------------------
pushd "%~dp0..\..\" >nul 2>&1
chcp 65001 >nul
git log --oneline -10 -- "KNK업무시스템구축/01_HAIST_WORKS/app/templates/" "KNK업무시스템구축/01B_HAIST_WORKS_매출영업/" 2>nul
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
echo    [HTML 미리보기] 그룹별 단축키 (서버 켜져있어야 함)
echo ------------------------------------------------------------
echo      S) 시스템 시작 + 매출영업 홈 (HAIST WORKS :8081)
echo      1) 프로젝트 (3p)         /projects
echo      2) 고객사 (3p)           /customers
echo      3) 견적 (3p)             /sales/quotations
echo      4) 수주 (2p)             /orders
echo      5) 납품/수금/미수/연체   /sales/shipments
echo      6) 대시/예측/생산        /sales/dashboard
echo      7) 수출 hub (6p)         /export
echo      8) FTA (2p)              /fta/certificates
echo ------------------------------------------------------------
echo    [메타 정보]
echo      P) PROGRESS.md 메모장 열기
echo      L) 최신 HANDOFF 메모장 열기
echo      O) output 폴더 탐색기
echo      G) GitHub 브랜치 페이지
echo      Q) 종료
echo ============================================================
echo.
choice /c 12345678SPLOGQ /n /m "선택: "

if errorlevel 14 goto :end
if errorlevel 13 (
    start "" "https://github.com/top00151-commits/claude_code/tree/claude/charming-yonath-a72046/KNK업무시스템구축/01B_HAIST_WORKS_매출영업"
    goto :end
)
if errorlevel 12 (
    start "" explorer "%~dp0output"
    goto :end
)
if errorlevel 11 (
    for /f "delims=" %%f in ('dir /b /o-d "%~dp0output\HANDOFF_TO_01_*.md" 2^>nul') do (
        start "" notepad "%~dp0output\%%f"
        goto :end
    )
    goto :end
)
if errorlevel 10 (
    start "" notepad "%~dp0PROGRESS.md"
    goto :end
)
if errorlevel 9 (
    echo.
    echo HAIST WORKS 시작 중...
    if exist "%~dp0..\KNK_시작.bat" (start "" "%~dp0..\KNK_시작.bat") else (echo KNK_시작.bat 없음. 메인 폴더에서 실행 필요.)
    timeout /t 5 /nobreak >nul
    start "" "http://localhost:8081/sales"
    goto :end
)
if errorlevel 8 (start "" "http://localhost:8081/fta/certificates" & goto :end)
if errorlevel 7 (start "" "http://localhost:8081/export" & goto :end)
if errorlevel 6 (start "" "http://localhost:8081/sales/dashboard" & goto :end)
if errorlevel 5 (start "" "http://localhost:8081/sales/shipments" & goto :end)
if errorlevel 4 (start "" "http://localhost:8081/orders" & goto :end)
if errorlevel 3 (start "" "http://localhost:8081/sales/quotations" & goto :end)
if errorlevel 2 (start "" "http://localhost:8081/customers" & goto :end)
if errorlevel 1 (start "" "http://localhost:8081/projects" & goto :end)

:end
echo.
echo 종료. (창을 닫으려면 아무 키나 누르세요)
pause >nul
exit /b 0
