@echo off
REM ============================================================
REM   LAST UPDATE: 2026-05-06 v5H185 프로젝트 상세 편집 위치 재배치 (우측 패널=read-only, 타이틀 옆 ✏️ + 수주내역 툴바). v5H184 등록 폼 자가치유 라벨을 친화적으로 수정 + SO=수주번호 풀이 안내. v5H183 프로젝트 변경 이력 상세 기록(등록 초기값 16종 + 자동 SO 호기별 + 호기 수정 단가/발주일/납기/납품처 모두 project_history 에 기록). v5H182 호기 인라인 편집 '편집 완료' 일괄 저장(행별 💾 버튼 숨김). v5H181 고객사 리스트 SELECT/템플릿 컬럼명 수정 + tier '신규'→'일반' 정리. v5H180 고객사 다건 일괄 삭제 (FK 연결 시 차단). v5H179 프로젝트 다건 일괄 삭제(체크박스+sticky 툴바+비번 재인증). v5H178b HTML 응답 no-cache + 호기 중복 라벨 자동 재번호 + order_items.currency 부모 sync. v5H178 추가 발주 모달에 통화·납품처 추가 (default = 프로젝트 헤더 통화). v5H177 호기별 발주일/납기/납품처 override + 프로젝트 헤더 인라인 편집(이름/비고/통화·환율/거래구분) + 수정 폼 readonly. Tier 1(관리코드/사업부/유형/PO유형) 영구 잠금. v5H176 SO 합계 통화 표기를 p.currency 동적 + 외화 시 KRW 환산 병기. v5H175 전역 '← 이전 페이지' 플로팅 버튼 (모든 페이지 좌하단, 홈/탑탭 메인 제외) + history.back/referrer/허브 홈 fallback. v5H174 프로젝트 폼 우측 상단 '등록자/등록일시' 항상 표시 (수정 시 최근수정 추가). v5H173 외화 원화 환산 자동 — 폼 로드 시 fx_rate 있으면 원화 환산 자동 재계산·표시, 저장된 amount_krw 보존, 프로젝트 상세 우측 패널 환산값 표기. v5H172 통화 표시·백필·즉시반영 — (1)startup orders.currency 자동 백필, (2)KPI/SO 통화 표기 p.currency 우선, (3)인라인 편집 후 캐시버스터 강제 reload. v5H171 통화 데이터 연결 — (1)VND 묵음 손실 버그 fix, (2)fx_rate·amount_krw 프로젝트 저장 누락 fix, (3)confirm_order() 단일 SO 통화 상속 누락 fix, (4)project_form 헤더 통화 6종 확장 + 호기 라인 자동 동기화. 수주관리 '+새 수주' 버튼 제거(SO는 프로젝트 진행중 전환 시 자동 발행 구조라 수동 생성 불필요). 임박납기 박스 높이를 달력 그리드 실제 높이에 정확히 맞춤(JS sync). 달력은 자연 높이 유지(과대 stretch 제거), 리스트는 내부 스크롤. v5H168 한달이동(±1개월) + 60건 확장 유지. 수주관리 페이지 전면 재설계 — 4탭(T 검사기/M 자동화/K 기타/소모품) + KPI 6카드 + 상태 파이프라인(수평 칸반) + 출하 캘린더(이번달+다음달) + 강화 목록표(D-day 뱃지·진행률 바·납기색상행). /sales/orders 라우트 매개변수 추가(tab/status/period/currency/q/sort/due_date). 소모품 탭은 consumable_orders 테이블 별도 조회. 신규 partial 2종(_v5_partials/so_pipeline.html, so_calendar.html). 백워드 호환 PRAGMA 컬럼 동적 감지 유지. 정렬 기본 = 납기 임박순(오버듀→임박→여유). 캘린더 색상: 오버듀 적색/D-3 주황/D-7 노랑/여유 녹색. 권한: can_use_sales (_s1_guard).
REM   PREV: 2026-05-05 v5H154 고객사 엑셀 일괄 등록 신설. /customers/import-template (양식 다운로드) + /customers/import-xlsx (파싱·검증·미리보기 JSON) + /customers/import-confirm (UPSERT) 3개 라우트 신설. '고객사' 시트 row7+ 파싱, 10컬럼 매핑(고객사명/사업자번호/대표/담당자/전화/이메일/주소/등급/활성/비고), 검증(사업자번호 10자리·이메일 형식·등급 A/B/C/VIP·활성 1/0). 동일 이름 존재 시 빈 칸 아닌 필드만 UPDATE(기존 데이터 보호) / 신규 INSERT, 사업자번호 중복(다른 이름)은 경고만. customers_list.html 상단에 [📥 양식 다운로드][📤 엑셀 일괄 업로드] 버튼 + 미리보기 모달(신규/업데이트 카운트·동작 pill·검증결과). 권한: can_use_sales.
REM   Full changelog: ../CHANGELOG.md
REM ============================================================
chcp 65001 >nul
title KNK HAIST WORKS [v5H178]
cd /d "%~dp001_HAIST_WORKS"

echo.
echo ============================================================
echo    HAIST WORKS  ^| KNK Integrated Work Platform
echo    Human ^& AI create the Best
echo    [v5H178  2026-05-06]
echo ============================================================
echo.

where python >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python is not installed.
    echo Install Python 3.10+ from https://www.python.org/downloads/
    pause
    exit /b 1
)

python -c "import fastapi, uvicorn, jinja2" >nul 2>nul
if errorlevel 1 (
    echo [First Run] Installing required packages...
    python -m pip install --upgrade pip >nul
    python -m pip install -r requirements.txt
    if errorlevel 1 (
        echo [ERROR] Package installation failed.
        pause
        exit /b 1
    )
    echo [OK] Installation complete.
)

start "" /b cmd /c "timeout /t 3 /nobreak >nul && start http://localhost:8081"

python run.py

echo.
echo Server stopped. Press any key to close.
pause >nul
