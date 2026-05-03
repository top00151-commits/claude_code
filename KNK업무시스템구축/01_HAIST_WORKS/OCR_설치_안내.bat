@echo off
REM ============================================================
REM   v5H59 (2026-05-03) - OCR install guide (English-only to avoid Korean cmd encoding issues)
REM   Korean detail: see http://localhost:8081/guide/ocr (after server start)
REM ============================================================
title KNK HAIST WORKS - OCR Install Guide

cls
echo.
echo  ============================================================
echo    KNK HAIST WORKS  ^|  OCR Install Guide
echo    (For business-license image / scan recognition)
echo  ============================================================
echo.
echo  [Current status]
where tesseract >nul 2>nul
if errorlevel 1 (
    echo    Tesseract OCR     : NOT installed
    set OCRSTATE=NOT
) else (
    echo    Tesseract OCR     : INSTALLED
    set OCRSTATE=OK
)
if exist "C:\Program Files\Tesseract-OCR\tesseract.exe" (
    echo    Standard path     : C:\Program Files\Tesseract-OCR\tesseract.exe
)
echo.
echo  [What works without install]
echo    PDF from Hometax / Gov24  : YES (text-PDF auto parsed)
echo.
echo  [What needs Tesseract install]
echo    JPG / PNG / scanned PDF  : Image OCR (Korean recognition)
echo.
echo  ============================================================
echo  [Install steps - one time only]
echo  ============================================================
echo.
echo    1. Download installer:
echo       https://github.com/UB-Mannheim/tesseract/wiki
echo       File: tesseract-ocr-w64-setup-v5.x.x.exe
echo.
echo    2. During install - IMPORTANT:
echo       In "Additional language data" section,
echo       CHECK "Korean" checkbox  (REQUIRED for Korean recognition)
echo.
echo    3. Default install path:
echo       C:\Program Files\Tesseract-OCR\
echo       (HAIST WORKS auto-detects - no PATH setup needed)
echo.
echo    4. Restart HAIST WORKS server (run START.bat again)
echo.
echo  ============================================================
echo  [Optional - scanned PDF support]
echo  ============================================================
echo    For scanned PDF (not just text PDF), also install Poppler:
echo      https://github.com/oschwartz10612/poppler-windows/releases
echo    Add bin folder to system PATH.
echo.
echo  ============================================================
echo  [Privacy / Policy]
echo  ============================================================
echo    * No external API calls (all OCR runs locally)
echo    * No data leaves the machine
echo    * Open source (Tesseract: Apache 2.0 license)
echo.
echo  ------------------------------------------------------------
echo.

if "%OCRSTATE%"=="OK" (
    echo  Tesseract is already installed - no action needed.
    echo  Image/PDF OCR is available in customer registration form.
    echo.
    pause
    exit /b 0
)

choice /C YN /M "Open Tesseract download page in browser now"
if errorlevel 2 goto :end
if errorlevel 1 start "" "https://github.com/UB-Mannheim/tesseract/wiki"

:end
echo.
pause
