@echo off
REM === 바탕화면에 KNK 메신저 바로가기(.lnk) 생성 ===
REM LAST UPDATE: 2026-05-11
chcp 65001 >nul
cd /d "%~dp0"
py make_desktop_shortcut.py %1
echo.
pause
