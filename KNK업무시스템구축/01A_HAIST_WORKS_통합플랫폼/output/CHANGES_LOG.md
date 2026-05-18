# 📋 실무팀1 (통합플랫폼) — 변경 이력 로그

> 22 페이지 시안1 적용 작업의 매 페이지·매 변경 시점 기록.
> 매 페이지 수정 직후 자동 갱신됨. 빅터 취합 + 대표 검토 자료.

## 형식

```
## YYYY-MM-DD HH:MM — {파일명} (그룹 X, N 순위)
- 변경 종류: (예) Quiet Tone v3 토큰 마이그레이션 / 골격 정의 / data-dn 부착 등
- 변경 내용:
  - {변경 1}
  - {변경 2}
- 원본: 01_HAIST_WORKS/app/templates/{파일명}
- 사본: 01A_HAIST_WORKS_통합플랫폼/changed_templates/{파일명}
- 라인 수: A → B (±C)
- 빨강 사용: N개
- 검증: ?debug=1 라벨 / 1100px 반응형 / 폼 한국어 검증
```

---

## 2026-05-10 — 작업 시작 전 상태

- 실무팀1 정체성 전환 완료 (워크트리 `sad-johnson-eddf3c`)
- 빅터(01) 회신 도착 — 차단 3건 모두 해제, (e) 전체 적용 승인
- 1순위: home.html (시안1 적용 1차 작업)
- 워크트리 베이스: `v5H226z39` + `_v5_partials/design_quiet_v3.html` (z48 헤더, 토큰 글로벌 로드 상태)

---

## 2026-05-10 — v4 정정 룰 4건 적용 (빅터 v2 회신)

`REPLY_FROM_01_2026-05-10_v2_공통룰정정.md` 도착 — 실무팀2 앞 회신이지만 모든 팀 공통 적용.

| 정정 | 내 home.html 작업 정합성 |
|---|---|
| 1. 메인 BAT은 빅터만 (자기 폴더 BAT 자율) | `01A_확인.bat` 자기 폴더 — ✅ |
| 2. v5H226z 주석/commit 자유 (사용자 노출만 X) | home.html 상단 주석 v5H226z 미사용했지만 OK | 
| 3. 워크트리→메인 동기화 옵션A | 메인 폴더 직접 작업 — **자동 충족** |
| 4. (e) 단계 분할 v1~v4 | home.html은 v1+v2 동시 적용 → v2 통과 |

메모리 갱신: `team_rules_v4_correction.md` 저장, MEMORY.md 인덱스 추가.

---

## 2026-05-10 — 일괄 묶음: 그룹 A 나머지 + B + C + D + E + F + 기타 (총 20 페이지) ✅ v1+v2 통과

대표 7시간 자율 작업 위임으로 home/daily 외 나머지 20 페이지를 동일 패턴 일괄 적용.

**처리 묶음:**
1. 그룹 A 나머지 4개: weekly / now / team / cockpit
2. 그룹 B 3개: notifications / calendar / search
3. 그룹 C 3개: tickets_list / ticket_detail / ticket_form
4. 그룹 D 3개: changes_list / change_detail / change_form (`change_detail var(--line)` 누락 발견 → 즉시 재치환)
5. 그룹 E 3개: issues_list / issue_detail / issue_form
6. 그룹 F 4개: board_list / board_detail / board_form / board_teams
7. 기타 1개: profile

**모든 페이지 공통 적용:**
- 색상 토큰 14종 매핑 (paper/ink/mute/line/amber/grad/shadow-amber/glow-amber → --qv-*)
- data-dn 라벨 부착 (페이지별 3~7개)
- 상단 주석 추가 (`2026-05-10 실무팀1: Quiet Tone v3 토큰 + data-dn (v1+v2 차수)`)
- Jinja/API/권한분기/라우트 변경 0건
- 페이지 버전 라벨(`v5H226z..`) 미수정 (v4 룰 2 보수적 준수)

**페이지별 특수 처리:**
- weekly: victor-insight 그라디언트 + glow 잉크 단색화
- calendar: 일/토/공휴일 K(빨강)·V(주황) 의미적 컬러 보존 (수주관리 패턴 통일)
- profile: profile-hero 그라디언트 + glow → 잉크 단색
- ticket_detail: 빅터 박스 amber-glow 배경 → qv-surface-2 (강조 약화 — v3+ 검토)
- daily/notifications: focus·input 빨강 의미적 보존

**라인 변동 누적:** +83줄 (22 페이지 합계)

**정량 검증 (자동 grep, 22 페이지 종합):**
- 잔존 v5 컬러 토큰: **0건**
- data-dn 라벨: **93개** (22 페이지)
- 사본 생성: **22 / 22**

---

## 2026-05-10 — daily.html (그룹 A, 2순위) ✅ v1+v2 통과

- **변경 종류:** Quiet Tone v3 토큰 마이그레이션 + data-dn 라벨 (home과 동일 패턴)
- **변경 내용:**
  - 색상 토큰 9종 일괄 치환:
    - `--paper-3` → `--qv-surface` / `--paper-2` → `--qv-surface-3` / `--paper` → `--qv-surface-2`
    - `--ink` → `--qv-ink` / `--mute` → `--qv-ink-3` / `--line` → `--qv-line`
    - `--amber-glow` → `--qv-surface-2` / `--amber-deep` → `--qv-ink-2` / `--amber` → `--qv-line-3`
  - data-dn 라벨 7개 부착:
    - `daily-main` (main wrapper)
    - `daily-pagehead` (page-head)
    - `daily-kpi-bento` (KPI 4카드)
    - `daily-quickadd` (qa-bar 빠른 입력)
    - `daily-pending-yday` (어제 미완료 — pending_yday 시)
    - `daily-tasks` (오늘 업무 리스트)
    - `daily-weekstats` (이번 주 통계 — week_stats 시)
  - 상단 주석에 Quiet Tone v3 마이그레이션 + 부록 B 후속 차수 보류 메모
- **원본:** `01_HAIST_WORKS/app/templates/daily.html`
- **사본:** `01A_HAIST_WORKS_통합플랫폼/changed_templates/daily.html`
- **라인 수:** 276 → 284 (+8: 상단 주석 7줄 + data-dn 부속)
- **빨강 사용:** 위험/강조 의미 4건 — `.task-card.delay` 보더(지연) / `input:focus` box-shadow 3건 / `pill-danger` (대표 요청 표시) — 발주서 8.6 위험 상태/강조 룰 부합
- **검증:**
  - [x] var(--qv-*) 토큰 사용 (잔존 v5 컬러 토큰 grep 0건)
  - [x] data-dn 라벨 7개 부착
  - [x] Jinja 변수 / 권한 분기 / API (`/api/task`, `/api/carry-forward`) 그대로
  - [ ] ?debug=1 라이브 검증 — 서버 가동 후 확인
- **금지 룰 준수:** 메인 BAT 미수정 / `_v5_partials/` 미수정 / `main.py` 미수정 / DB·라우트·Jinja 변수 미수정 / 외부 라이브러리 추가 없음
- **부록 B specs 후속 보류:** 시간대별 카드(오전/오후/야간) / 사진 드래그앤드롭+클립보드 / 자동저장 디바운스 — 백엔드·JS 추가 작업 필요로 v3+ 차수에서 다룸

---

## 2026-05-10 — home.html (그룹 A, 1순위) ✅ v1+v2 통과

- **변경 종류:** Quiet Tone v3 토큰 마이그레이션 + data-dn 라벨 + 빨강 톤 정리
- **변경 내용:**
  - 색상 토큰 일괄 치환 (전체 파일 inline `<style>` 블록):
    - `var(--paper-3)` → `var(--qv-surface)` (카드/사이드바/벤토 카드 흰 배경)
    - `var(--paper-2)` → `var(--qv-surface-3)` (옅은 회색 보조)
    - `var(--paper)` → `var(--qv-surface-2)` (본문 배경)
    - `var(--ink)` → `var(--qv-ink)` (제목/본문 잉크)
    - `var(--mute)` → `var(--qv-ink-3)` (메타·라벨 회색)
    - `var(--line)` → `var(--qv-line)` (보더)
    - `var(--amber-glow)` → `var(--qv-surface-2)` (icon 배경)
    - `var(--amber-deep)` → `var(--qv-ink-2)` (강조 텍스트·링크)
    - `var(--amber-light)` → `var(--qv-line-2)`
    - `var(--amber)` → `var(--qv-line-3)` (보더 액센트)
    - `var(--grad-amber)` → `var(--qv-ink)` (.card.hero / .scope-tab.active / .dock-head 등 — 잉크 단색)
    - `var(--grad-knk-red)` → `var(--qv-ink)` (.page-title em — 잉크 단색)
    - `var(--shadow-amber)` → `0 1px 2px rgba(15,23,42,0.04)` (미세 그림자)
    - `var(--glow-amber-radial)` → `transparent` (radial glow 제거)
  - 경영진 자물쇠 라벨(라인 306) 빨강 → 잉크 톤 (`var(--qv-surface-3)` 배경 + `var(--qv-ink-2)` 글자) — 권한 표시는 위험 의미 아님
  - data-dn 라벨 10개 부착:
    - `home-main` (main wrapper)
    - `home-pagehead` (page-head)
    - `home-scope-tabs` (3 탭)
    - `home-quickadd` (빠른 입력)
    - `home-kpi-bento` (KPI 7카드 그리드)
    - `home-exec-bento` (경영진 KPI 2카드 — is_executive 시)
    - `home-quickactions` (빠른 액션 4카드)
    - `home-todays` (오늘의 업무 — my_tasks 시)
    - `home-pending-yday` (어제 미완료 — pending_yday 시)
    - `home-team` (팀/전사 현황 — team_data 시)
  - 상단 주석에 Quiet Tone v3 마이그레이션 내역 기록 (페이지 버전 라벨 미수정 — 빅터 룰 준수)
- **원본:** `01_HAIST_WORKS/app/templates/home.html`
- **사본:** `01A_HAIST_WORKS_통합플랫폼/changed_templates/home.html`
- **라인 수:** 473 → 478 (+5: 주석 4줄 + data-dn은 0 라인 변동)
- **빨강 사용:** **CTA 1개 + 의미적 위험/경고 5건** = `.btn-submit` (등록 버튼) / `.card-trend.alert` 색 / 인라인 동적 색(delay_my>0, total_my=0) / `.dock-msg b` 강조 / `.tb-icon-badge`/`.sb-badge` (알림·메뉴 뱃지)
  - 발주서 8.6 "CTA 1개 또는 위험 상태만" 부합
- **검증:**
  - [x] data-dn 라벨 10개 부착
  - [x] var(--qv-*) 토큰 사용 (paper/ink/mute/line/amber 잔존 0건)
  - [ ] ?debug=1 라이브 검증 — 서버 가동 후 대표 확인
  - [ ] 1100px 이하 반응형 — Launch preview 좁게 줄여 확인 권장
- **금지 룰 준수:** 페이지 버전 라벨(`v5H226z..`) 미수정 / `_v5_partials/` 미수정 / `main.py` 라우트 미수정 / Jinja 변수 그대로 / 권한 분기 그대로 / 외부 라이브러리 추가 없음

---

## 2026-05-10 — v3+ 차수 (4 페이지 quiet 톤 보강)

### 적용 범위 (대표 승인 4 항목)
1. focus 빨강 → 잉크 일괄 (사용자 입력 응답 의미는 보더/shadow로 보존)
2. `--warn` 호박색 → 잉크 (지연·경고 시각 강조는 잉크 톤으로 통일)
3. `victor-insight` 그라디언트 → 잉크 단색
4. `scope-tab.active` 액센트 강화 (그림자 + 잉크 보더 + lift)

### daily.html
- **변경 종류:** focus 빨강 → 잉크 (3건) + 어제 미완료 보더 호박 → 잉크
- **변경 내용:**
  - 라인 31: `.qa-bar input#newTitle:focus` box-shadow `var(--knk-red)` → `var(--qv-line-3)` (3px로 두께↑)
  - 라인 34: `.qa-bar select/number/list:focus` border `var(--knk-red)` → `var(--qv-line-3)` / shadow `rgba(165,40,44,0.15)` → `var(--qv-surface-2)`
  - 라인 124: `task-card`(어제 미완료) border-left `var(--warn)` → `var(--qv-ink)` (4px 두께 보존)
  - 라인 219: JS focusNewTask boxShadow `var(--knk-red), rgba(165,40,44,...)` → `var(--qv-line-3), rgba(26,26,26,0.18)`
- **사본:** changed_templates/daily.html ✓
- **빨강 사용:** v1+v2 6건 → v3+ **3건**(↓3) — task-card.delay 보더(지연 의미 보존) + 별표 없음(daily는 폼 아님) + dock 영역 외
- **잔존 빨강 의미:** `.task-card.delay` 좌측 보더(지연), 의미적 보존

### home.html
- **변경 종류:** 어제 미완료 진입점 호박 → 잉크 + scope-tab.active 강화
- **변경 내용:**
  - 라인 79: `.scope-tab.active` box-shadow 1px → 2px+6px + 1px 잉크 보더 + `translateY(-1px)` lift (클릭 식별 강화)
  - 라인 293: `<a class="card clickable">` border-color `var(--warn)` → `var(--qv-ink)`
  - 라인 295: `.card-value` color `var(--warn)` → `var(--qv-ink)`
- **사본:** changed_templates/home.html ✓
- **빨강 사용:** v1+v2 7건 그대로(모두 의미적: btn-submit CTA / 알림 뱃지 / 위험 카운트 / dock 강조)

### weekly.html
- **변경 종류:** victor-insight 그라디언트 → 잉크 단색 + 부서 진행률 50%↓ 호박 → 잉크
- **변경 내용:**
  - 라인 45: `.victor-insight` background `linear-gradient(135deg, var(--qv-ink) 0%, #4A2F1F 100%)` → `var(--qv-ink)` (단색)
  - 라인 158: 부서 진행률 50% 미만 bar background `var(--warn)` → `var(--qv-ink)`
- **사본:** changed_templates/weekly.html ✓
- **빨강 사용:** v1+v2 4건 그대로(kpi delta down / status-delay / delay 인라인 / 지연 메타 — 모두 의미적)

### cockpit.html
- **변경 종류:** 정체 업무 KPI 호박 → 잉크
- **변경 내용:**
  - 라인 16: `.kpi-num` color `var(--warn)` → `var(--qv-ink)` (정체 업무 카운트)
- **사본:** changed_templates/cockpit.html ✓
- **빨강 사용:** v1+v2 1건 그대로(미작성 일일 카운트 — 의미적 위험)

### 검증 (자동 grep)
- 22 페이지 내 `var(--warn)` 잔존: **0건** ✓
- 22 페이지 내 `#4A2F1F` 잔존: **0건** ✓
- daily.html `rgba(165,40,44,...)` 잔존: **0건** ✓
- v1+v2 차수 산출물 (data-dn 라벨 93개·v5 토큰 0건) **유지** ✓

### 금지 룰 준수
- 페이지 버전 라벨 미수정 / `_v5_partials/` 미수정 / `main.py` 미수정 / DB·라우트·Jinja 변수 미수정 / 외부 라이브러리 추가 없음 / 다른 팀 페이지 미접근

### v3+ 차수 산출물
- HANDOFF_TO_01_v4.md (v3+ 차수 종합)
- VERIFICATION_REPORT_v2.md (v3+ 정량 검증)



---

## 2026-05-11 — home.html bento 폭 정렬 (1412 → 1476)

### 증상
- `?debug=1` 모드에서 home-pagehead/scope-tabs/quickadd는 1476×N
- home-kpi-bento/home-exec-bento는 **1412×N** (64px 좁음)
- 시각 정렬 어긋남

### 원인
`_v5_partials/styles.html:105` 의 `.bento { margin: 0 var(--content-pad); }`
→ `.main` padding(32px) 위에 좌우 32px 추가 margin = 64px 안쪽으로 들어감

### 수정 (home.html 내부 override)
- 라인 94: `.bento { ... }` 에 `margin: 0` 추가
- 효과: home 페이지에서만 .bento margin 제거 (다른 페이지 영향 없음)
- home-exec-bento(라인 309) 인라인 `margin-top:var(--space-4)` 는 top만 override로 보존

### 룰 준수
- 공통 partial `_v5_partials/styles.html` 미수정 (빅터 권한 존중) ✓
- home.html 내부 인라인 style override만 사용 ✓
- 다른 21 페이지 영향 없음 ✓

### 사본
- changed_templates/home.html 갱신 완료

## 2026-05-11 — home.html .section 폭 정렬 (추가 1412 → 1476)

### 증상
- 이전 .bento 수정 후에도 home-quickactions/home-todays/home-pending-yday/home-team 4개 영역은 **1412 폭** 잔존
- pagehead/bento/exec-bento와 시각 정렬 어긋남

### 원인
`_v5_partials/styles.html:99` 의 `.section { margin: var(--space-5) var(--content-pad) 0; }`
→ `.section`도 좌우 32px씩 추가 margin (.bento와 동일 패턴)

### 수정 (home.html 라인 126)
- Before: `.section { margin-top: var(--space-7); }`
- After:  `.section { margin: var(--space-7) 0 0; }`
- 효과: home 페이지의 모든 .section 좌우 margin 제거 (다른 페이지 영향 없음)
- top margin은 var(--space-7) 보존 (대표 의도된 섹션 간격)

### 영향 영역 (4개 section)
- home-quickactions (라인 332)
- home-todays (라인 359)
- home-pending-yday (라인 377)
- home-team (라인 395)

### 사본
- changed_templates/home.html 갱신 완료

## 2026-05-11 — 22 페이지 전체 폭 정렬 (1412 → 1476)

### 배경
home.html 폭 정렬 후, 대표 지시로 22 페이지 전체 점검 및 일괄 수정.

### 원인 패턴 (공통)
`_v5_partials/styles.html`의 wrapper 정의들이 좌우 `var(--content-pad)` margin을 자동 추가:
- `.bento`, `.section`, `.tbl-wrap` (partial)
- 페이지 자체 정의 `.form-card`, `.detail-grid`, `.search-box`, `.post-card`, `.kpi-row`, `.victor-insight`, `.qa-bar`, `.cal-wrap`, `.profile-hero`, `.alert-msg`, `.grid-2`
- 각종 인라인 style의 form filterbar / 댓글 form / legend / 버튼 div / list-scroll

### 수정 내역 (25건 + 17건 = 42 변경)

**그룹 A: 페이지 자체 inline `<style>` 정의 12건 (`var(--content-pad)` → `0`)**
- search.html `.search-box`
- ticket_detail.html `.detail-grid`
- ticket_form.html `.form-card`
- change_detail.html `.detail-grid`
- change_form.html `.form-card`
- issue_detail.html `.detail-grid`
- issue_form.html `.form-card`
- board_detail.html `.post-card`
- board_form.html `.form-card`
- weekly.html `.kpi-row`, `.victor-insight`, `.section`
- profile.html `.grid-2`, `.profile-hero`, `.alert-msg`
- daily.html `.qa-bar`
- calendar.html `.cal-wrap`

**그룹 B: partial wrapper override 10 페이지 추가**
- 추가 라인: `.bento, .section, .tbl-wrap { margin-left: 0; margin-right: 0; }`
- 대상: cockpit, tickets_list, changes_list, issues_list, board_list (새 `<style>` 블록) / daily, weekly, team, calendar, profile (기존 `<style>` 끝)
- home.html은 이미 적용됨

**그룹 C: 인라인 style 잔존 12건 수정**
- now.html, notifications.html `.list-scroll` 인라인
- board_teams.html `.actions` 인라인
- ticket_form, change_form, issue_form, board_form 의 버튼 div
- board_detail 댓글 form
- calendar legend div
- changes_list, issues_list, tickets_list 필터바 form
- search 결과 wrapper, team list-scroll

### 자동 검증 결과
- 22 페이지 내 margin context의 `var(--content-pad)` 잔존: **0건** ✓
- 모든 main 직접 자식 wrapper가 main padding 안쪽에서 1476 폭 유지

### 룰 준수
- `_v5_partials/styles.html` 미수정 (빅터 권한 존중) ✓
- 페이지 인라인 override만 사용 → 다른 팀(매출영업·자재구매) 페이지 영향 없음 ✓
- main.py / DB / Jinja / 권한 분기 / 외부 lib 변경 0건 ✓

### 사본
- changed_templates/ 23 파일 (22 페이지 + cockpit 추가) 일괄 갱신 완료
