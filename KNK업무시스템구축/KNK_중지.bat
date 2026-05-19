@echo off
REM ============================================================
REM   KNK HAIST WORKS - 서버 중지 / 좀비 청소
REM   v5H226z108n12 (2026-05-18)
REM ============================================================
chcp 65001 >nul
title KNK HAIST WORKS - Stop Server

echo.
echo ============================================================
echo    KNK HAIST WORKS  ^|  Server Stop / Zombie Cleanup
echo ============================================================
echo.

echo [1/2] 8081 포트 점유 프로세스 종료 ...
powershell -NoProfile -Command "$p = Get-NetTCPConnection -LocalPort 8081 -State Listen -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique; if ($p) { foreach ($i in $p) { Write-Host '  killed pid' $i; Stop-Process -Id $i -Force -ErrorAction SilentlyContinue } } else { Write-Host '  (없음)' }"

echo.
echo [2/2] 부모 죽은 uvicorn 좀비 워커 청소 ...
powershell -NoProfile -Command "$orphan = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -match 'spawn_main.*parent_pid' -and -not (Get-Process -Id $_.ParentProcessId -ErrorAction SilentlyContinue) }; if ($orphan) { foreach ($o in $orphan) { Write-Host '  killed orphan pid' $o.ProcessId; Stop-Process -Id $o.ProcessId -Force -ErrorAction SilentlyContinue } } else { Write-Host '  (없음)' }"

echo.
echo 완료. 이제 KNK_시작.bat 으로 깨끗하게 재시작 가능합니다.
echo.
pause
