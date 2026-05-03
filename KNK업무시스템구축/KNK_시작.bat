@echo off
REM ============================================================
REM   LAST UPDATE: 2026-05-03 v5H82 v5H81 등록 후 오류 수정 + 고객사 검증 강화 — (1) 오류 원인: get_project_orders 가 새 컬럼(ship_to/unit_qty/unit_label/unit_note) 미선택 → 템플릿 so.ship_to 접근 시 KeyError. PRAGMA 동적 감지로 존재하는 컬럼만 SELECT + None 안전 기본값 (2) 고객사 자유입력 차단 — POST /projects/new + /projects/{pid}/edit 가 customers.name 와 정확 일치 검증, 없으면 ?error=customer_not_registered 로 redirect (3) 폼 상단에 빨간 경고 배너 (등록 안 된 고객사 / 필수 항목 누락) (4) 고객사 라벨 '(등록된 고객사만 선택 가능)' 명시 (5) project_detail 합계 행 unit_qty 합산 안전 (None 가드)
REM   업데이트 규칙: 01 세션이 코드 수정/작업할 때마다 본 라인 갱신
REM ============================================================
chcp 65001 > nul
title KNK HAIST WORKS - HAIST Innovation [Updated 2026-05-03 v5H82 v5H81 후속 오류 수정 + 고객사 검증 강화]
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
