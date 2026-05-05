@echo off
REM === KNK Messenger 자동 백업 (Python 호출) ===
chcp 65001 >nul
cd /d "%~dp0"
py backup.py
