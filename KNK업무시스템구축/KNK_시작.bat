@echo off
REM ============================================================
REM   LAST UPDATE: 2026-05-03 v5H89b 고객사 표기 안 됨 — 데이터 연결 수정 — 대표 보고: '정보 다 연결 안된것 같은데, 고객사 안 보임'. 원인: projects 가 customer_name(text) 만 저장하고 customer_id(FK) 비워둠 → orders 도 customer_id NULL → JOIN 실패. 수정 (1) projects_create_logi/update_logi 가 customer_name → customer_id 자동 매핑 (2) confirm_order_multi 도 SO 발행 직전 lookup 으로 채움 (3) sales_orders SELECT 가 cu.name → p.customer_name → pcu.name (project FK) 3중 폴백 (4) DB 마이그레이션 backfill: NULL projects.customer_id 채움 + NULL orders.customer_id 를 project.customer_id 로 채움 (기존 데이터 자동 회복). v5H89 수주관리 리스트 정보 확장 — 대표 보고: '수주관리 데이터 항목 너무 작아 관리번호/품명/모델/고객사 보이지 않음'. sales_orders 라우트에 projects 조인 추가 (mgmt_code/project_name/biz_div/model_name/po_type) + orders 신규 컬럼 PRAGMA 동적 SELECT (ship_to/unit_qty/unit_label). 템플릿 컬럼 11개로 확장: 수주번호 / 관리번호(프로젝트 링크) / 프로젝트·모델 / 사업부(T·M 컬러 pill) / 고객사 / 호기수+라벨 / 납품지 / 금액 / 상태 / 수주일 / 납기. v5H88 SO 접미 채번 — 대표 지적: 'T-260505 다음이 왜 -2 인가, -1 이 없네'. v5H69 로직이 base 단독을 N=1로 카운트해 다음을 -2 로 부여 → -1 누락. 수정: base 단독은 N 카운트 제외 → 첫 건 base, 두 번째 base-1, 세 번째 base-2 순서 보장. v5H87 진행중 상태 등록 시 SO 도 자동 발행 — 대표 보고: '진행중인데 수주번호가 없으니 수주관리에 집계 안 되고, 진행중 정의(제작 중)와도 모순'. v5H86 은 관리코드만 발급 → SO 누락. 수정: POST /projects/new + /projects/{pid}/edit 모두 status in WON_STATUSES + (SO 없음) 이면 confirm_order_multi 로 1호기 SO 자동 발행 (label='1호기', amount=order_amount, due_date=project.due). 폼 hint 도 '관리코드+SO 동시 발급' 으로 명확화. v5H86 상태 '진행중'/'납품완료' 시 자동 관리코드 발급 — 대표 보고: '진행중 선택했는데 관리코드 부여 안 됨'. 기존: stage in (수주확정,납품) 만 트리거. 추가: WON_STATUSES = (진행중,납품완료) 도 트리거 → projects_create_logi/update_logi 양쪽 status 검사 추가, 자동 stage='수주확정' 승격. 폼 hint 갱신. v5H85 SO 안 호기 단가 다를 때 분해 표기 — 대표 질문 '수주번호는 같은데 호기 금액이 다를 때는 어떻게 표기를 해?'. get_project_orders 가 order_items 동시 fetch + unit_price_uniform 판정. project_detail 금액 셀 아래에 (1) 단가 모두 동일 → 'N대 × 단가' (2) 단가 다름 → '호기별 단가 ▾' 펼치기 (각 호기 라벨 + 금액). 호기 1개면 표기 생략 (합계만) — 대표 제안 '발주 수량을 수정할 수 있게 하면 쉽게 될 것 같은데'. project_detail 수주 내역 테이블에서 호기수(number input)/금액(text input + 콤마) 즉시 편집 → 변경 감지 시 💾 저장 버튼 노출 → 클릭 시 POST /sales/orders/{oid}/quick-edit. 호기수 1+ / 금액 0+ 검증, 출하/송장/취소 SO 는 거부. 저장 시 프로젝트 order_amount 동기화 + history 기록. 권한: can_use_sales 필요. 신규 발주 워크플로우 대신 직접 수량 조정으로 단순화 가능
REM   업데이트 규칙: 01 세션이 코드 수정/작업할 때마다 본 라인 갱신
REM ============================================================
chcp 65001 > nul
title KNK HAIST WORKS - HAIST Innovation [Updated 2026-05-03 v5H89b 고객사·관리번호 데이터 연결 + 기존 NULL 백필]
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
