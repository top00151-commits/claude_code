@echo off
REM ============================================================
REM   v5H57 (2026-05-03) - 사업자등록증 OCR 설치 안내
REM   PDF 자동 인식은 별도 설치 없이 즉시 사용 가능
REM   이미지 / 스캔본 OCR 만 추가 설치 필요
REM ============================================================
chcp 65001 > nul
title KNK HAIST WORKS - OCR 설치 안내

cls
echo.
echo  ============================================================
echo    KNK HAIST WORKS  ^|  사업자등록증 OCR 설치 안내
echo  ============================================================
echo.
echo  [현재 상태]
where tesseract >nul 2>nul
if errorlevel 1 (
    echo    Tesseract OCR : 미설치
) else (
    echo    Tesseract OCR : 설치 완료
)
if exist "C:\Program Files\Tesseract-OCR\tesseract.exe" (
    echo    표준 경로     : C:\Program Files\Tesseract-OCR\tesseract.exe
)
echo.
echo  [기능별 의존성]
echo.
echo    PDF 자동 인식 (홈택스/정부24)    : 즉시 사용 가능 ^(추가 설치 불필요^)
echo    스캔본 PDF / JPG / PNG OCR       : Tesseract 설치 필요
echo.
echo  ============================================================
echo  [Tesseract 설치 방법 (한 번만)]
echo  ============================================================
echo.
echo    1. 다운로드 페이지 열기:
echo       https://github.com/UB-Mannheim/tesseract/wiki
echo.
echo    2. tesseract-ocr-w64-setup-v5.x.x.exe 다운로드
echo.
echo    3. 설치 시 ★중요★:
echo       "Additional language data" 항목에서
echo       "Korean" 반드시 체크 (한국어 인식)
echo.
echo    4. 설치 경로: C:\Program Files\Tesseract-OCR\
echo       (HAIST WORKS 가 자동 감지 - PATH 설정 불필요)
echo.
echo  ============================================================
echo  [추가 - 스캔 PDF 지원 시 Poppler 설치]
echo  ============================================================
echo.
echo    스캔된 PDF 도 인식하려면 Poppler 설치 (이미지 변환용):
echo    https://github.com/oschwartz10612/poppler-windows/releases
echo    bin 폴더를 PATH 에 추가
echo.
echo  ============================================================
echo  [정책]
echo  ============================================================
echo.
echo    * 외부 API 0건 (모든 OCR 로컬 실행)
echo    * 데이터 외부 송신 0건
echo    * 오픈소스 (Apache 2.0)
echo.
echo  ------------------------------------------------------------
echo  [브라우저로 다운로드 페이지 열기]
echo  ------------------------------------------------------------
echo.
choice /C YN /M "지금 Tesseract 다운로드 페이지를 여시겠습니까"
if errorlevel 2 goto :end
if errorlevel 1 start https://github.com/UB-Mannheim/tesseract/wiki

:end
echo.
pause
