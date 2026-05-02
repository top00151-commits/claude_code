@echo off
REM ============================================================
REM   LAST UPDATE: 2026-05-02 v5H36 task_detail 삭제 + 반응 표시 버그 수정 (대표 지적) — (1) DELETE /api/task API: 권한 미검증 후 항상 ok:True 반환 → SELECT user_id 먼저 조회·작성자 또는 ceo/admin 검증·404/403 정확 반환 (조용한 실패 제거), (2) 프론트 deleteTask: 'r.ok' 단순 체크 → r.ok && j.ok 검사 + 실제 서버 에러 메시지 alert 표시 + credentials:'same-origin' 명시, (3) 사이드바 반응 카드: get_reactions가 list가 아닌 dict ('ack/question/risk/ok' 키) 반환 → for r in reactions가 str key 순회로 r.count=str.count 메서드 출력 버그 → reactions.ack|length 등 명시적 키 접근으로 수정 (👀확인/👍좋아요/❓질문/⚠위험 4종 분리 표시) / 154/154 PASS
REM   업데이트 규칙: 01 세션이 코드 수정/작업할 때마다 본 라인 갱신
REM ============================================================
chcp 65001 > nul
title KNK HAIST WORKS - HAIST Innovation [Updated 2026-05-02 v5H36 삭제 권한 검증 + 반응 dict 표시 버그 수정]
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
