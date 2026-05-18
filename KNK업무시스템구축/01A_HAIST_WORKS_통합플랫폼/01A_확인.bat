@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"
title Team1 Platform - Quick Tool

:MENU
cls
echo.
echo ============================================================
echo    HAIST WORKS - Team1 (Platform) Quick Tool
echo    Worktree: sad-johnson-eddf3c    Pages: 22
echo ============================================================
echo.
echo  [Work Tracking]
echo    1. PROGRESS.md         (22 pages status)
echo    2. CHANGES_LOG.md      (changes log)
echo    3. changed_templates   (folder)
echo    4. Progress count      (done/pending)
echo.
echo  [Victor Communication]
echo    5. INQUIRY             (sent inquiry, _TO_01)
echo    6. REPLY               (received reply, output)
echo    7. HANDOFF v4          (v3+ latest, _TO_01)
echo    V. VERIFY v2           (v3+ verify, _TO_01)
echo    W. WALKTHROUGH         (persona, _TO_01)
echo    H. HOTFIX issues route (1-token patch req, _TO_01)
echo    X. v1+v2 archive       (HANDOFF v3 / VERIFY v1)
echo    8. notes folder
echo    T. _TO_01 folder       (Victor INBOX)
echo.
echo  [Browser Test - server 8081]
echo    9. Home page
echo    A. Top 5 pages         (home/daily/weekly/notif/cal)
echo    B. All 22 pages        (CAUTION: 22 tabs)
echo    C. Custom URL
echo.
echo  [Misc]
echo    S. Server status check (port 8081)
echo    R. Server start        (..\START.bat)
echo    F. INSTRUCTIONS.md
echo    Q. Quit
echo.
set /p choice=Select:

if /i "%choice%"=="1" start "" notepad "%~dp0PROGRESS.md"
if /i "%choice%"=="2" call :OPEN_CHANGES
if /i "%choice%"=="3" start "" "%~dp0changed_templates"
if /i "%choice%"=="4" call :SHOW_SUMMARY
if /i "%choice%"=="5" start "" notepad "%~dp0output\_TO_01\INQUIRY_TO_01_2026-05-10.md"
if /i "%choice%"=="6" start "" notepad "%~dp0output\REPLY_FROM_01_2026-05-10.md"
if /i "%choice%"=="7" call :OPEN_HANDOFF
if /i "%choice%"=="V" start "" notepad "%~dp0output\_TO_01\VERIFICATION_REPORT_v2.md"
if /i "%choice%"=="W" start "" notepad "%~dp0output\_TO_01\WALKTHROUGH_v1.md"
if /i "%choice%"=="H" start "" notepad "%~dp0output\_TO_01\HOTFIX_REQUEST_2026-05-10_issues_route.md"
if /i "%choice%"=="X" call :OPEN_ARCHIVE
if /i "%choice%"=="8" start "" "%~dp0notes"
if /i "%choice%"=="T" start "" "%~dp0output\_TO_01"
if /i "%choice%"=="9" start http://localhost:8081/home
if /i "%choice%"=="A" call :OPEN_TOP5
if /i "%choice%"=="B" call :OPEN_ALL22
if /i "%choice%"=="C" call :OPEN_CUSTOM
if /i "%choice%"=="S" call :CHECK_SERVER
if /i "%choice%"=="R" start "" "%~dp0..\START.bat"
if /i "%choice%"=="F" start "" notepad "%~dp0INSTRUCTIONS.md"
if /i "%choice%"=="Q" goto :EOF
goto MENU


REM -------- subroutines --------

:OPEN_CHANGES
if exist "%~dp0output\CHANGES_LOG.md" (
    start "" notepad "%~dp0output\CHANGES_LOG.md"
) else (
    echo CHANGES_LOG.md not found.
    pause
)
exit /b

:OPEN_HANDOFF
if exist "%~dp0output\_TO_01\HANDOFF_TO_01_v4.md" (
    start "" notepad "%~dp0output\_TO_01\HANDOFF_TO_01_v4.md"
) else if exist "%~dp0output\_TO_01\HANDOFF_TO_01_v3.md" (
    start "" notepad "%~dp0output\_TO_01\HANDOFF_TO_01_v3.md"
) else if exist "%~dp0output\_TO_01\HANDOFF_TO_01_v2.md" (
    start "" notepad "%~dp0output\_TO_01\HANDOFF_TO_01_v2.md"
) else if exist "%~dp0output\_TO_01\HANDOFF_TO_01_v1.md" (
    start "" notepad "%~dp0output\_TO_01\HANDOFF_TO_01_v1.md"
) else (
    echo HANDOFF file not found yet.
    pause
)
exit /b

:OPEN_ARCHIVE
echo.
echo --- v1+v2 archive (older docs) ---
if exist "%~dp0output\_TO_01\HANDOFF_TO_01_v3.md" start "" notepad "%~dp0output\_TO_01\HANDOFF_TO_01_v3.md"
if exist "%~dp0output\_TO_01\VERIFICATION_REPORT_v1.md" start "" notepad "%~dp0output\_TO_01\VERIFICATION_REPORT_v1.md"
exit /b

:SHOW_SUMMARY
echo.
echo ============================================================
echo    22 pages progress (changed_templates basis)
echo ============================================================
set DONE=0
for %%P in (home daily weekly now team cockpit notifications calendar search tickets_list ticket_detail ticket_form changes_list change_detail change_form issues_list issue_detail issue_form board_list board_detail board_form board_teams profile) do (
    if exist "%~dp0changed_templates\%%P.html" (
        echo   [DONE] %%P.html
        set /a DONE=!DONE!+1
    ) else (
        echo   [....] %%P.html
    )
)
echo.
echo   Done: !DONE! / 22
echo.
pause
exit /b

:OPEN_TOP5
echo Opening top 5 pages...
start http://localhost:8081/home
timeout /t 1 /nobreak >nul
start http://localhost:8081/daily
timeout /t 1 /nobreak >nul
start http://localhost:8081/weekly
timeout /t 1 /nobreak >nul
start http://localhost:8081/notifications
timeout /t 1 /nobreak >nul
start http://localhost:8081/calendar
exit /b

:OPEN_ALL22
echo Opening all 22 pages as new tabs.
echo Starts in 5 sec (Ctrl+C to cancel)...
timeout /t 5 >nul
start http://localhost:8081/home
start http://localhost:8081/daily
start http://localhost:8081/weekly
start http://localhost:8081/now
start http://localhost:8081/team
start http://localhost:8081/cockpit
start http://localhost:8081/notifications
start http://localhost:8081/calendar
start http://localhost:8081/search
start http://localhost:8081/tickets
start http://localhost:8081/tickets/1
start http://localhost:8081/tickets/new
start http://localhost:8081/changes
start http://localhost:8081/changes/1
start http://localhost:8081/changes/new
start http://localhost:8081/issues
start http://localhost:8081/issues/1
start http://localhost:8081/issues/new
start http://localhost:8081/board/general
start http://localhost:8081/board/general/1
start http://localhost:8081/board/general/new
start http://localhost:8081/board/teams
start http://localhost:8081/profile
echo 22 pages opened.
pause
exit /b

:OPEN_CUSTOM
set /p urlpath=URL path (e.g. /home or /daily?debug=1):
start http://localhost:8081%urlpath%
exit /b

:CHECK_SERVER
echo.
echo Checking server response... (http://localhost:8081/)
curl -s -o nul -w "HTTP %%{http_code}  -  %%{time_total}s\n" --max-time 3 http://localhost:8081/ 2>nul
if errorlevel 1 (
    echo.
    echo [SERVER DOWN] No response on port 8081. Use menu R to start.
)
echo.
pause
exit /b
