@echo off
chcp 65001 > nul
title KNK 물류허브 - 바탕화면 바로가기 만들기
cd /d "%~dp0"

echo.
echo ============================================================
echo    KNK 물류허브 - 바탕화면 바로가기 만들기
echo ============================================================
echo.
echo 바탕화면에 'KNK 물류허브' 바로가기를 만듭니다 ...
echo.

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$ws = New-Object -ComObject WScript.Shell;" ^
  "$desktop = [Environment]::GetFolderPath('Desktop');" ^
  "$lnk = Join-Path $desktop 'KNK 물류허브.lnk';" ^
  "$sc = $ws.CreateShortcut($lnk);" ^
  "$sc.TargetPath = '%~dp0KNK_시작.bat';" ^
  "$sc.WorkingDirectory = '%~dp0';" ^
  "$sc.IconLocation = 'imageres.dll,108';" ^
  "$sc.Description = 'KNK 물류허브 - HAIST Innovation';" ^
  "$sc.Save();" ^
  "Write-Host '   [성공] 바탕화면에 바로가기가 생성되었습니다.' -ForegroundColor Green"

echo.
echo 이제 바탕화면의 'KNK 물류허브' 아이콘을 더블클릭하면 바로 실행됩니다.
echo.
pause
