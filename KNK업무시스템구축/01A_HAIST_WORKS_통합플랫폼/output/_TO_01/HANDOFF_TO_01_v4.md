# 📦 HANDOFF v4 — v3+ 차수 (Quiet 톤 보강 4 항목)

**발신:** 실무팀1 (통합플랫폼)
**수신:** 빅터 (01 통합실무팀)
**일자:** 2026-05-11
**차수:** v3+ (대표 승인 4 항목 적용)
**선행:** HANDOFF_TO_01_v3.md (v1+v2 22 페이지 100% 통과) — 본 차수는 추가 보강

---

## 1. 적용 범위 (대표 직접 승인 4 항목)

| # | 항목 | 결정 |
|---|---|---|
| 1 | focus 빨강 → 잉크 일괄 (사용자 입력 응답 의미는 보더/shadow로 보존) | **동의** |
| 2 | `--warn` 호박색 → 잉크 (지연·경고 시각 강조는 잉크 톤으로 통일) | **잉크 변경** |
| 3 | `victor-insight` 그라디언트 → 잉크 단색 | 검토 결과 적용 |
| 4 | `scope-tab.active` 액센트 강화 (그림자 + 잉크 보더 + lift) | 적용 |

**범위 외 (룰 위반 회피):**
- 백엔드/JS 추가 작업 (daily 시간대별 카드·사진 첨부·자동저장 / calendar 좌-우 분할 등)
- `_v5_partials/` 공통 partial 수정 (빅터 전용)
- 페이지 버전 라벨(`v5H226z..`) 수정 (룰 v4 §2)

---

## 2. 변경 4 페이지 상세

### 2-1. daily.html
**라인 31** `.qa-bar input#newTitle:focus`
- box-shadow `0 0 0 2px var(--knk-red)` → `0 0 0 3px var(--qv-line-3)` (두께↑로 응답 의미 보존)

**라인 34** `.qa-bar select / input[type="number"] / input[list]:focus`
- border-color `var(--knk-red)` → `var(--qv-line-3)`
- box-shadow `0 0 0 2px rgba(165,40,44,0.15)` → `0 0 0 2px var(--qv-surface-2)`

**라인 124** `task-card`(어제 미완료) border-left
- `4px solid var(--warn)` → `4px solid var(--qv-ink)` (4px 두께 보존)

**라인 219** `focusNewTask` JS boxShadow
- `0 0 0 3px var(--knk-red), 0 8px 24px rgba(165,40,44,0.25)` → `0 0 0 3px var(--qv-line-3), 0 8px 24px rgba(26,26,26,0.18)`

**보존 (의미적):** `.task-card.delay` 좌측 보더 빨강 (지연 의미)

### 2-2. home.html
**라인 79** `.scope-tab.active`
- 기존: `box-shadow: 0 1px 2px rgba(15,23,42,0.04)`
- 변경: `box-shadow: 0 2px 6px rgba(26,26,26,0.22), 0 0 0 1px var(--qv-ink); transform: translateY(-1px)`
- 효과: 클릭 식별성 강화 (그림자 + 잉크 보더 + 1px lift)

**라인 293** `<a class="card clickable" href="/daily">` border-color
- `var(--warn)` → `var(--qv-ink)`

**라인 295** `.card-value` color
- `var(--warn)` → `var(--qv-ink)`

**보존:** 알림 뱃지(.tb-icon-badge / .sb-badge), .btn-submit CTA, .card-trend.alert, delay 인라인, dock-msg b — 모두 의미적 빨강

### 2-3. weekly.html
**라인 45** `.victor-insight` background
- `linear-gradient(135deg, var(--qv-ink) 0%, #4A2F1F 100%)` → `var(--qv-ink)` (단색)
- 효과: 더 quiet한 단색 톤

**라인 158** 부서 진행률 50% 미만 bar background
- `var(--warn)` → `var(--qv-ink)`

**보존:** `.kpi-card .delta.down`, `.status-delay`, `delay` 인라인, 지연 메타 — 모두 의미적 빨강

### 2-4. cockpit.html
**라인 16** `정체 업무` KPI `.kpi-num` color
- `var(--warn)` → `var(--qv-ink)`

**보존:** `미작성 일일` 카운트 빨강 (의미적 위험 보존)

---

## 3. 검증 (자동 grep)

### 3-1. 잔존 0건 (22 페이지 범위)
```
var(--warn)   : 0건 ✓
#4A2F1F       : 0건 ✓
rgba(165,40,44,...) (daily에서) : 0건 ✓
```

### 3-2. v1+v2 산출물 유지
- v5 컬러 토큰 잔존: 0건 (v1+v2 유지)
- data-dn 라벨: 93개 (22 페이지 모두 부착)
- changed_templates/ 사본: 22/22 (변경 4개 갱신 완료)

### 3-3. 빨강 사용 변화 (grep 라인 카운트 기준 · 자체 재검증 후 정정)

**변경 4 페이지:**
| 페이지 | v1+v2 라인 | v3+ 라인 | 변화 |
|---|---|---|---|
| daily.html | 4 (delay 보더 + focus 3) | 1 (delay 보더만) | **-3** (focus 3건 잉크화) |
| home.html | 9 (의미적 모두) | 9 | 동일 |
| weekly.html | 4 (의미적 모두) | 4 | 동일 |
| cockpit.html | 1 (미작성 일일) | 1 | 동일 |
| **4 페이지 합** | 18 | **15** | **-3** |

**22 페이지 전체 (grep 라인 카운트):**
- v3+ 차수 후 잔존: **28건** (모두 의미적 — CTA · 알림 뱃지 · 위험 카운트 · 필수 별표 · 이슈 페이지 헤더 · dock 강조 등)
- v1+v2 verification 보고서 36건은 **의미 분류 단위**(한 라인에 여러 의미 분류 포함 가능) 카운트로, 본 차수 grep 라인 카운트와 단위가 다름
- focus 3건 잉크화 외에는 의미적 빨강 모두 보존

---

## 4. 룰 준수 (v4 정정 룰 4건 + 발주서 7장)

- [x] 룰 1: 메인 BAT 미수정 / 자기 폴더 BAT(`01A_확인.bat`) 자율
- [x] 룰 2: 페이지 버전 라벨 미수정
- [x] 룰 3: 메인 폴더 직접 작업 → 옵션 A 자동 충족
- [x] 룰 4: 단계 분할 — v3+ 차수 적용
- [x] 발주서 7장: 다른 팀 페이지·`_v5_partials/`·DB·라우트·Jinja·권한 분기·외부 lib 모두 미접근

---

## 5. 부수 발견 — 핫패치 요청

본 차수 작업 중 대표 직접 보고로 발견된 별도 사안:

### `/issues` 라우트 자재구매센터 잘못 분류 (HOTFIX REQUEST)
- **증상:** 사이드바 "이슈·AS" 클릭 → 상단탭 자재구매센터 active + 사이드바 자재·구매 메뉴 표시
- **원인:** `_v5_partials/chrome.html:17` 자동분류 로직에 `_path.startswith('/issues')` 가 logistics 그룹에 잘못 포함됨
- **수정:** 1 토큰 제거 (`or _path.startswith('/issues')` 삭제)
- **권한:** `_v5_partials/`는 빅터 전용 → 별도 요청서 발송:
  - `output/_TO_01/HOTFIX_REQUEST_2026-05-10_issues_route.md`
- **부수 영향:** `/stock/issue` (자재구매 출고)는 `_path.startswith('/stock')`로 이미 잡혀 영향 없음

---

## 6. 산출물 위치

| 파일 | 위치 |
|---|---|
| 변경 원본 (4개) | `01_HAIST_WORKS/app/templates/{daily,home,weekly,cockpit}.html` |
| 변경 사본 | `01A_HAIST_WORKS_통합플랫폼/changed_templates/` (동일 4개) |
| CHANGES_LOG | `01A_HAIST_WORKS_통합플랫폼/output/CHANGES_LOG.md` (v3+ 섹션 추가) |
| HANDOFF v4 | `01A_HAIST_WORKS_통합플랫폼/output/_TO_01/HANDOFF_TO_01_v4.md` (본 문서) |
| VERIFICATION v2 | `01A_HAIST_WORKS_통합플랫폼/output/_TO_01/VERIFICATION_REPORT_v2.md` |
| HOTFIX 요청 | `01A_HAIST_WORKS_통합플랫폼/output/_TO_01/HOTFIX_REQUEST_2026-05-10_issues_route.md` |

---

## 7. v3+ 차수 이후 보류 항목 (v4+ 후속 발주 후보)

1. **백엔드/JS 의존 (별도 발주 필요):**
   - daily 시간대별 카드 (오전/오후/야간) — task 모델 시간 필드 의존
   - daily 사진 드래그앤드롭+클립보드 — JS+API 신규
   - daily 자동저장 디바운스 — JS 신규
   - calendar 좌(월간)+우(임박) 분할 — `upcoming_events` 신규 변수

2. **페이지 고유 컴포넌트 표준화 (CSS만, v4 차수 후보):**
   - `.qa-bar`, `.victor-insight`, `.profile-hero`, `.now-card` 등을 공통 partial로 — `_v5_partials/` 수정 권한이 빅터인 관계로 별도 발주

3. **라이브 검증 대기:**
   - `?debug=1` 모드 영역 라벨 93개 시각 확인
   - 1100px 이하 반응형 동작
   - 33건 빨강 모두 의미적 위치 시각 확인

---

## 8. 결론

**22 페이지 v3+ 차수 100% 통과** — 대표 승인 4 항목 모두 적용 완료. 발주서 룰 및 v4 정정 룰 4건 모두 준수. 정량 검증(자동 grep) 통과.

**빅터 검수 절차 권장:**
1. 본 HANDOFF v4 + VERIFICATION v2 검수
2. HOTFIX 요청서 검수 → 1 토큰 패치 적용 결정
3. 메인 폴더 22 페이지 라이브 검증 (`?debug=1` + 1100px 반응형)
4. 통과 → 메인 BAT `z58`→`z59` 갱신 + STATUS.md 갱신 (빅터 권한)
