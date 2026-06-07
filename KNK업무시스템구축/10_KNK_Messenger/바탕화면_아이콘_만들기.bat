@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo.
echo   KNK 메신저 - 바탕화면 실행 아이콘 만들기
echo   =========================================
echo.
powershell -NoProfile -Command "$here=(Get-Location).Path; $bat=(Get-ChildItem -LiteralPath $here -Filter '*START.bat' | Where-Object { $_.Name -ne (Split-Path -Leaf $PSCommandPath) } | Select-Object -First 1).FullName; $ico=Join-Path $here 'KNK.ico'; $desk=[Environment]::GetFolderPath('Desktop'); $lnk=Join-Path $desk 'KNK 메신저.lnk'; $w=New-Object -ComObject WScript.Shell; $s=$w.CreateShortcut($lnk); $s.TargetPath=$bat; $s.WorkingDirectory=$here; $s.IconLocation=$ico; $s.Save(); Write-Host ('   생성 완료: ' + $lnk)"
echo.
echo   바탕화면에 'KNK 메신저' 아이콘(KNK 로고)이 생겼습니다.
echo   그 아이콘을 더블클릭하면 메신저가 실행됩니다.
echo.
pause
