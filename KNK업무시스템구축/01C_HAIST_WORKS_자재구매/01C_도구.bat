@echo off
chcp 65001 >nul 2>&1
title 01C 자재구매센터 - 도구
cd /d "%~dp0"

:menu
cls
echo.
echo ============================================================
echo  01C HAIST WORKS - 자재구매센터 (실무팀3)
echo  Worktree: cranky-shtern-789fa2  /  Mode: 메인 직접 작업
echo ============================================================
echo.
echo  [1] 서버 시작 (메인 KNK_시작.bat)
echo  [2] 자재구매 페이지 5종 브라우저 열기
echo  [3] PROGRESS.md 진행 현황
echo  [4] _TO_01 INBOX 통보 목록
echo  [5] _STANDARD_자재모듈기준_v1.md 표시
echo  [6] 위하고_자료 폴더 열기 (참조 ERP A 분석자료)
echo  [7] migrations/ 적용 가이드
echo  [8] DB 백업 (data/backup/)
echo  [9] git status (자재구매 영역 변경)
echo  [a] 디자인 핸드오프 폴더 열기
echo  [b] output 폴더 열기 (HANDOFF + INBOX)
echo  [c] 카운트 요약 (페이지/HANDOFF/INBOX/migrations)
echo.
echo  [0] 종료
echo.
set /p choice=Choice:

if "%choice%"=="1" goto serve
if "%choice%"=="2" goto open_pages
if "%choice%"=="3" goto show_progress
if "%choice%"=="4" goto show_inbox
if "%choice%"=="5" goto show_standard
if "%choice%"=="6" goto open_ref
if "%choice%"=="7" goto show_migration
if "%choice%"=="8" goto backup_db
if "%choice%"=="9" goto git_status
if "%choice%"=="a" goto open_design
if "%choice%"=="b" goto open_output
if "%choice%"=="c" goto count_summary
if "%choice%"=="0" goto end
echo [!] 잘못된 선택. 다시 입력.
timeout /t 1 >nul
goto menu

:serve
echo.
echo [+] 메인 서버 시작 (KNK_시작.bat 호출)
start "" "%~dp0..\KNK_시작.bat"
timeout /t 2 >nul
goto menu

:open_pages
echo.
echo [+] 자재구매 페이지 5종 브라우저로 열기...
start "" "http://localhost:8081/logistics?debug=1"
timeout /t 1 >nul
start "" "http://localhost:8081/po?debug=1"
timeout /t 1 >nul
start "" "http://localhost:8081/parts?debug=1"
timeout /t 1 >nul
start "" "http://localhost:8081/stock/balances?debug=1"
timeout /t 1 >nul
start "" "http://localhost:8081/suppliers?debug=1"
echo [+] 5개 탭 열기 완료
pause
goto menu

:show_progress
cls
echo.
echo ============================================================
echo  PROGRESS.md
echo ============================================================
type "%~dp0PROGRESS.md"
echo.
pause
goto menu

:show_inbox
cls
echo.
echo ============================================================
echo  output/_TO_01 INBOX 통보 목록
echo ============================================================
dir /b /o-n "%~dp0output\_TO_01\*.md" 2>nul
echo.
echo [참고] STD = 기준문서, DONE = 완료, BLOCKED = 차단, ASK = 질의, FYI = 참고
echo.
pause
goto menu

:show_standard
cls
echo.
echo ============================================================
echo  자재모듈 기준서 v1 (요약 — 처음 100줄)
echo ============================================================
powershell -NoLogo -NoProfile -Command "Get-Content '%~dp0_STANDARD_자재모듈기준_v1.md' -TotalCount 100 -Encoding UTF8"
echo.
echo [전체 보기] 파일을 직접 여시려면 다음 경로:
echo   %~dp0_STANDARD_자재모듈기준_v1.md
echo.
pause
goto menu

:open_ref
echo.
echo [+] 참조 ERP A 분석자료 폴더 열기 (위하고_자료)
start "" "%~dp0위하고_자료"
goto menu

:show_migration
cls
echo.
echo ============================================================
echo  migrations 폴더 — DB 마이그레이션 SQL
echo ============================================================
dir /b "%~dp0migrations\*.sql" 2>nul
echo.
echo [중요] 적용 권한: 빅터(01) 또는 대표 직접 라인. 본 세션 직접 적용 금지.
echo.
echo [적용 절차]
echo   1) DB 백업 (메뉴 [8])
echo   2) sqlite3 또는 DB Browser for SQLite에서 .read 실행
echo   3) 검증 쿼리 (SQL 파일 §VERIFY 섹션)
echo   4) 문제 시 백업 복구 (SQL 파일 §ROLLBACK)
echo.
pause
goto menu

:backup_db
echo.
set BAK_TIME=%date:~0,4%%date:~5,2%%date:~8,2%_%time:~0,2%%time:~3,2%
set BAK_TIME=%BAK_TIME: =0%
set BAK_DIR=%~dp0..\01_HAIST_WORKS\data\backup
if not exist "%BAK_DIR%" mkdir "%BAK_DIR%"
set BAK_FILE=%BAK_DIR%\haist_works_pre_z56_%BAK_TIME%.db
copy "%~dp0..\01_HAIST_WORKS\data\haist_works.db" "%BAK_FILE%" >nul 2>&1
if exist "%BAK_FILE%" (
    echo [+] DB 백업 완료
    echo     %BAK_FILE%
) else (
    echo [!] 백업 실패 - DB 파일 경로 확인 필요
    echo     기대: %~dp0..\01_HAIST_WORKS\data\haist_works.db
)
echo.
pause
goto menu

:git_status
cls
echo.
echo ============================================================
echo  git status - 자재구매 영역 변경
echo ============================================================
pushd "%~dp0.."
git status --short -- "01C_HAIST_WORKS_자재구매" "01_HAIST_WORKS/app/templates/po_*.html" "01_HAIST_WORKS/app/templates/parts*.html" "01_HAIST_WORKS/app/templates/part_*.html" "01_HAIST_WORKS/app/templates/stock_*.html" "01_HAIST_WORKS/app/templates/qc_*.html" "01_HAIST_WORKS/app/templates/qms_*.html" "01_HAIST_WORKS/app/templates/wo_*.html" "01_HAIST_WORKS/app/templates/rates*.html" "01_HAIST_WORKS/app/templates/fx_*.html" "01_HAIST_WORKS/app/templates/suppliers*.html" "01_HAIST_WORKS/app/templates/supplier_*.html" "01_HAIST_WORKS/app/templates/logistics_home.html" 2>nul
popd
echo.
pause
goto menu

:open_design
echo.
start "" "%~dp0..\01_HAIST_WORKS\HAIST WORKS디자인변경\design_handoff_haist_works"
goto menu

:open_output
echo.
start "" "%~dp0output"
goto menu

:count_summary
cls
echo.
echo ============================================================
echo  카운트 요약
echo ============================================================
echo.
echo [페이지 (자재구매 영역)]
dir /b "%~dp0..\01_HAIST_WORKS\app\templates\po_*.html" "%~dp0..\01_HAIST_WORKS\app\templates\parts*.html" "%~dp0..\01_HAIST_WORKS\app\templates\part_*.html" "%~dp0..\01_HAIST_WORKS\app\templates\stock_*.html" "%~dp0..\01_HAIST_WORKS\app\templates\qc_*.html" "%~dp0..\01_HAIST_WORKS\app\templates\qms_*.html" "%~dp0..\01_HAIST_WORKS\app\templates\wo_*.html" "%~dp0..\01_HAIST_WORKS\app\templates\rates*.html" "%~dp0..\01_HAIST_WORKS\app\templates\fx_*.html" "%~dp0..\01_HAIST_WORKS\app\templates\suppliers*.html" "%~dp0..\01_HAIST_WORKS\app\templates\supplier_*.html" "%~dp0..\01_HAIST_WORKS\app\templates\logistics_home.html" 2>nul | find /c /v ""
echo.
echo [HANDOFF 누적]
dir /b "%~dp0output\HANDOFF_*.md" 2>nul | find /c /v ""
echo.
echo [INBOX 통보]
dir /b "%~dp0output\_TO_01\*.md" 2>nul | find /c /v ""
echo.
echo [migrations]
dir /b "%~dp0migrations\*.sql" 2>nul | find /c /v ""
echo.
pause
goto menu

:end
echo.
echo Bye.
timeout /t 1 >nul
exit /b 0
