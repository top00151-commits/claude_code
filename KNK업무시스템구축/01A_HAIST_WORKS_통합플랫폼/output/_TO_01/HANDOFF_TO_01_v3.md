# 📤 실무팀1 → 빅터(01) 3차 산출물 — 22 페이지 v1+v2 일괄 완료

**발신:** 실무팀1 (통합플랫폼) · 워크트리 `sad-johnson-eddf3c` (메인 폴더 직접 작업)
**수신:** 빅터 (01 통합실무팀)
**라우팅:** 김정락 대표이사 → 빅터 통합 라인
**일자:** 2026-05-10
**대상:** 발주서 22 페이지 **전체** — Quiet Tone v3 토큰 마이그레이션 + data-dn 라벨
**v4 정정 룰 적용:** ✅ (단계 분할 v2 통과)
**작업 시간:** ~7시간 자율 작업 (대표 위임)

---

## 🎯 한 줄 요약

> **22 페이지 v1+v2 차수 100% 완료. 잔존 v5 컬러 토큰 0건 / data-dn 라벨 93개 부착. 메인 폴더 직접 적용 완료(옵션 A 자동 충족), 빅터 통합 즉시 가능.**

---

## 변경 파일 목록 (23개)

### 그룹 A — 업무 현황 / 일일 / 주간 (6)
- `01_HAIST_WORKS/app/templates/home.html` (473→478, +5)
- `01_HAIST_WORKS/app/templates/daily.html` (276→284, +8)
- `01_HAIST_WORKS/app/templates/weekly.html` (208→211, +3)
- `01_HAIST_WORKS/app/templates/now.html` (40→43, +3)
- `01_HAIST_WORKS/app/templates/team.html` (115→119, +4)
- `01_HAIST_WORKS/app/templates/cockpit.html` (47→51, +4)

### 그룹 B — 알림 / 캘린더 / 검색 (3)
- `01_HAIST_WORKS/app/templates/notifications.html` (59→64, +5)
- `01_HAIST_WORKS/app/templates/calendar.html` (101→106, +5)
- `01_HAIST_WORKS/app/templates/search.html` (77→81, +4)

### 그룹 C — 티켓 (3)
- `01_HAIST_WORKS/app/templates/tickets_list.html` (51→54, +3)
- `01_HAIST_WORKS/app/templates/ticket_detail.html` (86→89, +3)
- `01_HAIST_WORKS/app/templates/ticket_form.html` (74→77, +3)

### 그룹 D — 변경 공지 (3)
- `01_HAIST_WORKS/app/templates/changes_list.html` (39→42, +3)
- `01_HAIST_WORKS/app/templates/change_detail.html` (72→75, +3)
- `01_HAIST_WORKS/app/templates/change_form.html` (47→50, +3)

### 그룹 E — 이슈·AS (3)
- `01_HAIST_WORKS/app/templates/issues_list.html` (51→54, +3)
- `01_HAIST_WORKS/app/templates/issue_detail.html` (66→69, +3)
- `01_HAIST_WORKS/app/templates/issue_form.html` (47→50, +3)

### 그룹 F — 게시판 (4)
- `01_HAIST_WORKS/app/templates/board_list.html` (36→39, +3)
- `01_HAIST_WORKS/app/templates/board_detail.html` (53→56, +3)
- `01_HAIST_WORKS/app/templates/board_form.html` (39→42, +3)
- `01_HAIST_WORKS/app/templates/board_teams.html` (25→28, +3)

### 기타 (1)
- `01_HAIST_WORKS/app/templates/profile.html` (153→156, +3)

→ **사본: `01A_HAIST_WORKS_통합플랫폼/changed_templates/{동일 파일명}` 22개**

**총 라인 변동: +83줄 (상단 주석 + data-dn 부속)**

---

## 적용 내용 (22 페이지 공통)

### Step 1: Quiet Tone v3 토큰 마이그레이션 (14종 매핑)

| 기존 (v5) | 신규 (v3) | 용도 |
|---|---|---|
| `--paper-3` | `--qv-surface` | 카드/사이드바/벤토 흰 배경 |
| `--paper-2` | `--qv-surface-3` | 옅은 회색 보조 |
| `--paper` | `--qv-surface-2` | 본문 배경, input focus |
| `--ink` | `--qv-ink` | 제목/본문 잉크 |
| `--mute` | `--qv-ink-3` | 메타·라벨 회색 |
| `--line` | `--qv-line` | 보더 |
| `--amber-glow` | `--qv-surface-2` | 아이콘 배경, focus shadow |
| `--amber-deep` | `--qv-ink-2` | 강조 텍스트·링크 |
| `--amber-light` | `--qv-line-2` | 옅은 보더 |
| `--amber` | `--qv-line-3` 또는 `--qv-ink` | 보더 액센트 / focus border |
| `--grad-amber` | `--qv-ink` | 그라디언트 → 잉크 단색 |
| `--grad-knk-red` | `--qv-ink` | 그라디언트 → 잉크 단색 |
| `--shadow-amber` | `0 1px 2px rgba(15,23,42,0.04)` | 미세 그림자 |
| `--glow-amber-radial` | `transparent` | radial glow 제거 |

### Step 2: 컴포넌트 표준화
- 기존 공통 컴포넌트 클래스 그대로 사용 (`.bento` / `.kpi-card` / `.tbl` / `.pill` / `.page-head` / `.btn-primary` / `.btn-secondary` 등 — 이미 v3 partial이 `!important`로 오버라이드)

### Step 3: data-dn 디버그 라벨 부착 (총 93개)

| 영역 명명 규칙 | 예시 |
|---|---|
| `{page}-main` | `home-main`, `daily-main`, `tickets-main` 등 22개 |
| `{page}-pagehead` | `home-pagehead`, `weekly-pagehead` 등 22개 |
| `{page}-{section}` | `home-kpi-bento`, `home-quickactions`, `cal-grid`, `daily-quickadd`, `tickets-filterbar`, `profile-hero` 등 49개 |

### Step 4: 빨강 톤 정리
- CTA 1개 + 의미적 위험/경고만 보존:
  - `.btn-submit` / `.btn-primary` (등록 버튼)
  - `.task-card.delay`, `.notif-item.unread` (지연·미읽음 보더)
  - `.pill-danger` (대표 요청·심각·긴급 표시)
  - `.input:focus` shadow (사용자 입력 응답 의미)
  - `.tb-icon-badge`, `.sb-badge` (알림 카운트 — chrome partial 영역)
  - `card-trend.alert`, 인라인 동적 `style="color:var(--knk-red)"` (조건부 위험)
- **잉크 단색 변경**: `.card.hero`(home), `.scope-tab.active`(home), `.dock-head`(home), `.page-title em`(home/weekly/daily), `.profile-hero`(profile) — 호박 그라디언트/빨강 그라디언트 → 잉크 검정 단색
- **잉크 톤 변경**: 경영진 자물쇠 라벨(home, 권한 표시는 위험 의미 아님)

### Step 5: 상단 주석 (페이지 버전 라벨 미수정)
- 22 페이지 모두 `2026-05-10 실무팀1: Quiet Tone v3 토큰 + data-dn (v1+v2 차수)` 메모 추가
- 페이지 버전 라벨(`v5H226z..`) 직접 수정 0건 — 빅터 v4 룰 2 보수적 준수

---

## 정량 검증 (자동 grep)

```
잔존 v5 컬러 토큰 (paper/ink/mute/line/amber/grad-amber/grad-knk-red/shadow-amber/glow-amber):
  → 0 건 (22 / 22 페이지 클린)

data-dn 라벨 부착:
  → 93 개 (22 / 22 페이지 모두 부착, 평균 4.2개/페이지)

변경 사본 생성:
  → 22 / 22 (100%)
```

---

## 데이터 의존성 (모두 보존)

- Jinja 변수 100% 그대로 (`{{ }}`/`{% %}` placeholder 변경 없음)
- 권한 분기 그대로 (`{% if user.is_admin %}` / `{% if role in ('ceo',...) %}` / `{% if is_executive %}`)
- API 엔드포인트 그대로 (`/api/task`, `/api/carry-forward`, `/tickets`, `/changes`, `/issues`, `/board/...`, `/me`, `/notifications/read-all` 등)
- chrome partial include 그대로
- 라우트 URL 변경 0건
- DB 스키마·main.py 미수정

---

## 위험 / 주의사항

1. **input focus 빨강 보존** — quiet tone 정신상 잉크가 더 적합할 수 있으나, **사용자 입력 응답의 의미적 빨강**으로 해석하여 22 페이지 일관 유지. v3+ 차수에서 일괄 정리 검토 가능.

2. **box-shadow 토큰** — `--shadow-md`/`--shadow-lg` (v5_tokens.css 정의)는 그대로 사용. v3 partial이 별도 그림자 토큰 정의 안 함. 시각적 OK.

3. **부록 B specs 미적용 항목** (v3+ 차수 보류 — 백엔드/JS 추가 작업 필요):
   - daily.html: 시간대별 카드(오전/오후/야간), 사진 드래그앤드롭+클립보드, 자동저장 디바운스
   - calendar.html: 좌(월간 그리드 1280×600) + 우(임박 일정 320px) 분할 레이아웃 (현재 단일 컬럼)
   - 발주서 룰 "백엔드 로직 X"와 정합성 검토 필요

4. **scope-tab.active 시각 어필 약화** (home.html) — 호박 그라디언트→잉크 검정. 시안1 톤 일치하나 액센트 약화. 대표 확인 권장.

5. **ticket_detail 빅터 박스** — 기존 `--amber-glow` 배경+`--amber` 보더가 `--qv-surface-2` 배경+`--qv-line-3` 보더로 변경됨. 강조 약화. `.section-card` 일반과 시각 차별성 줄어듬. v3+ 차수에서 배경 톤 조정 가능.

---

## 미완료 / 추가 작업 제안 (v3+ 차수)

- 부록 B specs 풀 적용 (시간대별/캘린더 좌우/사진 업로드)
- 페이지 고유 컴포넌트 표준화 (.qa-bar, .victor-insight, .profile-hero, .now-card 등 → 공통화)
- input focus 빨강 → 잉크 톤 일괄 정리
- 1100px 이하 반응형 라이브 검증
- ?debug=1 모드 라이브 검증 — 영역 라벨 93개 모두 보이는지

---

## 검증 결과 (자동/수동)

자동 grep ✅:
- [x] var(--qv-*) 토큰 사용 (잔존 v5 컬러 grep 0건)
- [x] data-dn 라벨 93개 부착 (22 페이지 모두)
- [x] 변경 사본 22개 생성

룰 준수 ✅:
- [x] Jinja 변수 / 권한 분기 / 라우트 / API 변경 0건
- [x] `_v5_partials/` / `main.py` / DB / 메인 BAT 미수정
- [x] 외부 라이브러리 추가 없음
- [x] 자기 폴더 BAT(`01A_확인.bat`) 자율 사용 — v4 룰 1 부합
- [x] 페이지 버전 라벨 직접 수정 0건 — v4 룰 2 보수적 준수
- [x] 옵션 A 동기화 자동 충족 — v4 룰 3
- [x] (e) 단계 분할 v2 통과 — v4 룰 4

라이브 검증 (서버 가동 후 대표·빅터 측 필요) ⏳:
- [ ] ?debug=1 모드에서 data-dn 라벨 93개 모두 표시
- [ ] 1100px 이하 반응형 깨지지 않음
- [ ] 폼 한국어 검증 메시지 동작
- [ ] 빨강 사용 ≤1개/페이지 시각 확인

---

## 동기화 상태 (v4 룰 3 — 옵션 A)

본 워크트리는 메인 폴더 직접 작업 환경 → **자동 동기화 충족**.

- 변경 HTML: `01_HAIST_WORKS/app/templates/{22 페이지}.html` ✅ 메인 위치
- HANDOFF v1·v2·v3: `01A_HAIST_WORKS_통합플랫폼/output/_TO_01/` ✅ 메인 위치
- PROGRESS / CHANGES_LOG: `01A_HAIST_WORKS_통합플랫폼/PROGRESS.md`, `output/CHANGES_LOG.md` ✅ 메인 위치
- 사본: `01A_HAIST_WORKS_통합플랫폼/changed_templates/` 22개 ✅

**chat 출력:** "01A v1+v2 차수 22 페이지 일괄 메인 폴더 동기화 완료 (누적 22/22 = 100%)"

---

## 빅터 통합 절차 제안

1. 본 HANDOFF + 22 변경 파일 검수
2. ?debug=1 모드로 영역 라벨 93개 확인
3. 1100px 이하 반응형 동작 확인
4. 통합 commit + STATUS.md 갱신 + 메인 BAT z58 → z59 갱신 (빅터 권한)
5. v3+ 차수 추가 발주 받으면 다음 차수 진행

---

**다음 가능 작업 (대표 지시 필요):**
- v3 차수: 부록 B specs 적용 (daily/calendar 백엔드 협의 필요)
- v4 차수: 페이지 고유 컴포넌트 표준화
- 또는: 다른 우선순위 작업

**문의:** `output/INQUIRY_TO_01_v2.md` (다음 차수)
