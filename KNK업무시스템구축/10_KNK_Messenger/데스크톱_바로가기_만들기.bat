@echo off
chcp 65001 >nul
cd /d "%~dp0"
py make_desktop_shortcut.py %1
echo.
pause
