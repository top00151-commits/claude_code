@echo off
REM ============================================================
REM   LAST UPDATE: 2026-05-03 v5H52 매출영업센터 폼 흐름 전면 정합 (대표 사용 중 발견 3대 결함 일괄 수정) — (1) /projects/new POST 'project_name' 필수 검증 실패 → 템플릿 실제 필드명(name/customer_name) 호환 + 콤마 자동 제거 (2) /customers/new 별칭만 있고 실제 폼 없음 → customer_form.html 신규(8필드) + customers ALTER 8컬럼(biz_no/ceo_name/manager_name/phone/email/address/is_active) + POST/edit 핸들러 신규 (3) /sales/quotes/new 별칭만 있음 → sales_quote_form.html 신규(라인 동적 추가/실시간 합계) + sales_quote_detail.html 신규 + POST 신규 (4) KRW 입력 실시간 천단위 콤마 공통 JS (knk_inputs.html) — chrome.html 자동 포함, 모든 amount/price/금액 input 자동 적용 (5) tbl-sticky CSS — 13개 list 템플릿(고객사/부품/공급사/PO/수주/견적/이슈/티켓/변경/수불/잔고/QC/작업지시) 헤더 고정 스크롤
REM   업데이트 규칙: 01 세션이 코드 수정/작업할 때마다 본 라인 갱신
REM ============================================================
chcp 65001 > nul
title KNK HAIST WORKS - HAIST Innovation [Updated 2026-05-03 v5H57 사업자등록증 PDF/이미지 자동 인식]
cd /d "%~dp001_HAIST_WORKS"

echo.
echo ============================================================
echo    HAIST WORKS  ^|  KNK 통합 업무 플랫폼
echo    Human ^& AI create the Best
echo    [Last Update: 2026-04-29 G25_v4_CX23c_마스트헤드제거 (대표결재: 나)제거안) 3 base (통합/매출/자재) 상단 매거진 마스트헤드(VOL.NO + EDITION) 라인 일괄제거 → 일반 사무실 시스템 톤 + topbar-h 125→80px + dock top 80px 정합]
echo ============================================================
echo.

REM ── Python 설치 확인 ────────────────────────────────────────
where python >nul 2>nul
if errorlevel 1 (
    echo [오류] Python이 설치되어 있지 않습니다.
    echo.
    echo    https://www.python.org/downloads/  에서 Python 3.10 이상을 설치한 뒤
    echo    다시 이 파일을 더블클릭해주세요.
    echo.
    pause
    exit /b 1
)

REM ── 필수 패키지 자동 설치 (최초 1회) ────────────────────────
python -c "import fastapi, uvicorn, jinja2" >nul 2>nul
if errorlevel 1 (
    echo [최초 실행] 필요한 패키지를 설치합니다. 잠시 기다려주세요 ...
    echo.
    python -m pip install --upgrade pip >nul
    python -m pip install -r requirements.txt
    if errorlevel 1 (
        echo.
        echo [오류] 패키지 설치에 실패했습니다.
        echo        인터넷 연결을 확인한 뒤 다시 시도해주세요.
        pause
        exit /b 1
    )
    echo.
    echo [완료] 설치가 끝났습니다.
    echo.
)

REM ── 서버 시작 후 3초 뒤 브라우저 자동 열기 ──────────────────
start "" /b cmd /c "timeout /t 3 /nobreak >nul && start http://localhost:8081"

REM ── 서버 실행 ──────────────────────────────────────────────
python run.py

echo.
echo 서버가 종료되었습니다. 창을 닫으려면 아무 키나 누르세요.
pause >nul
