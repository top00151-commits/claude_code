# 01 회신 자동 발사 매트릭스 — 8 발주서 회귀 grep 명령

> 04 운영테스트팀 빅터 — 본 세션 직접 정리
> 일자: 2026-05-01
> 목적: 01 회신 도착 즉시 04가 grep 자체 검증 자동 발사 + walkthrough 매트릭스 즉시 발행

---

## 0. 한 줄

01에 발주된 8 발주서 (P0 4 + P1 권한가드 9 + P1 자동화 8 + P1 데이터정확성 35 + OPS-W 2 + OPS-PS-G-7 1) — 회신 도착 시 즉시 발사할 grep 명령 + walkthrough 매트릭스.

---

## 1. 발주 8종 회신 트리거 매트릭스

| 발주 | 회신 파일 | 04 자동 발사 grep | 회귀 walkthrough |
|---|---|---|---|
| P0 4건 | `_FROM_01_2026-04-29_OPS_P0_4건_핫패치_응답.md` | §2 | W1·W7·W8·W10 |
| P1 권한가드 9건 | `_FROM_01_2026-04-29_OPS_P1_권한가드_9건_응답.md` | §3 | W2·W4·W10 |
| P1 자동화 8건 | `_FROM_01_2026-04-29_OPS_P1_자동화_8건_응답.md` | §4 | (백그라운드) |
| P1 데이터정확 35건 | `_FROM_01_2026-04-29_OPS_P1_데이터정확성_35건_응답.md` | §5 | W3·W5·W12 |
| OPS-W-1+W-3 | `_FROM_01_2026-05-01_OPS_W1_W3_분리응답.md` | §6 | W9 |
| OPS-PS-G-7 | `_FROM_01_2026-05-01_OPS_PS-G-7_error_lang_응답.md` | §7 | (베트남법인 PS-G) |
| Phase 2-1~8 | `_FROM_01_2026-04-30_v5H5_Phase2-N_X_완료.md` | §8 | (별도 매트릭스 8건 사전 정리) |

---

## 2. P0 4건 회귀 grep 명령

```bash
# OPS-P0-1 [A-003] /home 공수 max
grep -n 'id="newHours"' app/templates/home.html
# 기대: max="24" 또는 max="48" 포함

# OPS-P0-2 [A-013] /login 비번 토글 44px
grep -n '\.toggle' app/templates/login.html static/css/v5_login.css static/style.css
# 기대: width:44px;height:44px

# OPS-P0-3 [C-004] /stock/issue 안전재고 confirm
grep -n 'checkSafetyStock\|onsubmit=.*checkSafetyStock' app/templates/stock_issue.html
# 기대: 2매치 (정의 + 호출) — 현재 PASS 확인됨

# OPS-P0-4 [E-007] /admin/company-info ?saved=1
grep -n 'admin/company-info?saved' app/main.py
grep -n 'saved=saved\|saved: int' app/main.py
# 기대: 1매치 + 1매치 — 현재 PASS 확인됨
```

→ P0 4건 중 P0-3 / P0-4 이미 PASS 확인 (사이클 88 + E 영역 보강).

---

## 3. P1 권한가드 9건 회귀 grep

```bash
# G1 [A-008] /dashboard 폴백
grep -n '?no_perm=dashboard' app/main.py app/templates/home.html
# 기대: main.py 1매치 + home.html 1매치 (PASS 확인됨)

# G2 [D-006] /board 승인 권한
grep -n "approve.*post" app/main.py
grep -n "is_leader\|role.*leader.*admin" app/main.py
# 기대: leader/admin 가드 부분에 매치

# G3 [D-009] /calendar scope=team 가드
grep -nE "scope.*=.*'team'\|scope == 'team'" app/main.py
# 기대: leader 재가드 추가

# G4 [E-001] /admin 진입 통일 (09 결재 옵션 A or B)
grep -nE "@app\.(get|post).*admin/permissions/grant" app/main.py
# 기대: require admin/ceo 적용 (옵션 A) 또는 leader 분기 (옵션 B)

# G5 [E-023] /team/{id}/permissions 소유권
grep -n "/team/{team_id" app/main.py
# 기대: u['team_id'] == team_id 가드

# G6 [B-004] /sales/production/start 권한
grep -n 'sales/production/start' app/main.py
# 기대: 생산팀 leader 가드

# G7 [B-005] 세금계산서 권한
grep -n 'tax_invoice\|세금계산서' app/templates/sales_orders.html app/main.py
# 기대: invoice_issue 권한 분기

# G8 [C-025] can_view_logistics 라우트 적용
grep -n 'can_view_logistics\|require.*logistics' app/main.py
# 기대: 자재 라우트별 가드

# G9 [C-026] stock_adjustments 승인 분리
grep -n 'can_approve\|approve.*adjustment' app/main.py
# 기대: leader/admin 분리 가드
```

---

## 4. P1 자동화 8건 회귀 grep

```bash
# A1 [D-003] 티켓 자동 라우팅
grep -n 'TICKET_CATEGORIES\|recipient_team_id' app/main.py
# 기대: 카테고리별 default 매핑

# A2 [D-008] 미작성자 자동 알림 (B2 안 채택 — main.py:188 _start_daily_reminder_scheduler 확인)
grep -n '_start_daily_reminder_scheduler\|notifications.*INSERT' app/main.py
# 기대: 1매치 (PASS 확인됨 — main.py:188)

# A3 [D-018] 티켓 댓글 알림
grep -n 'notify_comment\|comment.*notify' app/main.py
# 기대: 댓글 후 알림 호출

# A4 [B-007] 수금 잔액 자동
grep -n 'data-outstanding\|placeholder.*미수금' app/templates/sales_shipments_receipts.html
# 기대: 동적 placeholder

# A5 [A-005] 배너 8초 + 닫기 버튼
grep -nE 'setTimeout.*8000\|setTimeout.*5000' app/templates/daily.html app/templates/home.html
# 기대: 8000 ms 또는 5000+ms 변경

# A6 [A-011] /now 폴링 에러 배너
grep -n 'catch.*\[배너\|폴링.*실패' app/templates/now.html
# 기대: catch 블록에 사용자 피드백

# A7 [D-017] /weekly/refresh 캐시 무효화
grep -n "Cache-Control" app/main.py
# 기대: no-cache 헤더

# A8 [E-013] /guide 검색 JS
grep -n 'guideSearch\|search.*input' app/templates/guide.html
# 기대: JS 함수 정의 (또는 disabled 안내)
```

---

## 5. P1 데이터정확성 35건 회귀 grep (대표 5건)

```bash
# D3 [D-014] /projects mgmt_code 유일성
grep -n 'mgmt_code.*COUNT\|UNIQUE.*mgmt_code' app/main.py app/database.py
# 기대: SELECT COUNT 검증 또는 UNIQUE 제약

# I1 [B-015] 견적서 통화 변수화
grep -n 'qp_currency\|header\.currency' app/templates/quotation_print.html
# 기대: 동적 통화 변수

# L1 [B-001] sales_home 링크 수정
grep -n '/sales/dashboard\|href="/admin"' app/templates/sales_home.html
# 기대: KPI 카드 → /sales/dashboard

# L5 [B-020] base_sales 사이드바 4개 추가
grep -n '/sales/forecast\|/sales/aging\|/sales/outstanding' app/templates/base_sales.html
# 기대: 3개 매치

# M1 [D-001] 변경공지 분모 수정
grep -nE 'ack_count.*impact_count.*\* 5\|change_reads' app/templates/changes_list.html app/main.py
# 기대: × 5 제거, change_reads 행 수 사용
```

→ 35건 중 5건 대표. 회신 시 영역별 grep 35종 일괄 발사.

---

## 6. OPS-W 분리 발주 회귀 grep

```bash
# OPS-W-1 v5_tokens.css 라인수
wc -l app/static/css/v5_tokens.css
# 기대: 426 (또는 회신 시 명시 라인수와 일치)

# OPS-W-3 weekly @media print
grep -n '@media print' app/templates/weekly.html
# 기대: 1매치 이상 + 사이드바·도크 숨김 룰
grep -n 'sidebar.*display:\s*none' app/templates/weekly.html
# 기대: 1매치
```

---

## 7. OPS-PS-G-7 회귀 grep

```bash
# error.html lang 하드코딩 정정
grep -n '"lang":\s*"ko"' app/main.py
# 기대: 0매치 (수정 후)
grep -n 'request\.session\.get."lang"' app/main.py
# 기대: 1매치 이상 (수정 추가)
```

---

## 8. Phase 2 8 발주 회귀 grep (요약 — 상세는 별도 _DRAFT_Phase2 매트릭스)

| Phase | 핵심 grep |
|---|---|
| 2-1 A 대시보드 | `class="bento"` ≥3 / `var(--sage-` = 0 / `--amber\|--paper\|--knk-red` ≥3 |
| 2-2 B 매트릭스 | `metric-tabs\|sales-period-tab` ≥1 / `kpi-card v5` 5종 동일 |
| 2-3 C 폼 | `form-stepper` ≥1 / `form-section` ≥1 + `vat_mode` 보존 |
| 2-4 D 리스트 | `bulk-action-bar` ≥1 / `filter-chips` ≥1 |
| 2-5 E 상세 | `workflow-stepper` (po·change·issue·ticket 4종) / customer·board·part 0 |
| 2-6 H 관리자 | `admin_team_perms.html` sage 0 / `atab` ≥1 |
| 2-7 I 보고서 | `weekly-insight\|victor-insight` ≥1 / `@media print` weekly |
| 2-8 J 빅터 AI | `data-mode="victor"\|data-mode="search"` 보존 / `search-results` ≥1 |

---

## 9. 자동 발사 흐름 (회신 도착 → 04 응답)

```
01 회신 도착
  ↓
04: §N grep 명령 일괄 실행 (Bash 또는 Grep tool)
  ↓
PASS/FAIL 매트릭스 생성 (정직성 v3 — 매치 수 직접 인용)
  ↓
FAIL 발견 시 OPS-N 코드 + 즉시 재 발주
  ↓
PASS 시 walkthrough W1~W12 매트릭스 갱신
  ↓
회신 파일 발행: _TO_01_2026-MM-DD_OPSXX_회귀결과.md
  ↓
09 통보 (FYI) → 다음 사이클 가동
```

---

## 10. 정직성 v3 의무

- ✅ 모든 grep 명령은 정확한 파일 경로 + 패턴
- ✅ "% 완료" 표현 미사용 (PASS/FAIL 매트릭스만)
- ✅ 합산 산식: 4 + 9 + 8 + 35 + 2 + 1 + 8 = 67 (P0~OPS-W~OPS-PS-G + Phase 2 8 합산)
- ✅ 회귀 시 BAT grep 4/4 라인 직접 인용 의무

---

*04 운영테스트팀 빅터 — 2026-05-01*
*8 발주 회귀 grep 자동 발사 매트릭스 — 회신 도착 시 즉시 가동 가능 상태.*
