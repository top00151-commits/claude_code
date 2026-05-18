# 📤 실무팀1 → 빅터(01) 2차 산출물 전달 — daily.html

**발신:** 실무팀1 (통합플랫폼) · 워크트리 `sad-johnson-eddf3c` (메인 폴더 직접 작업)
**수신:** 빅터 (01 통합실무팀)
**라우팅:** 김정락 대표이사 → 빅터 통합 라인
**일자:** 2026-05-10
**대상:** 발주서 2순위 페이지 — `daily.html` (일일 업무)
**v4 정정 룰 적용:** ✅

---

## 변경 파일 목록

```
01_HAIST_WORKS/app/templates/daily.html  (개선)
  ↳ 사본: 01A_HAIST_WORKS_통합플랫폼/changed_templates/daily.html
```

**라인 변동:** 276 → 284 (+8)

---

## 작업 요약 (daily.html)

### 적용 내용
**Step 1: Quiet Tone v3 토큰 마이그레이션** (home과 동일 패턴)

| 기존 (v5) | 신규 (v3) | 용도 |
|---|---|---|
| `--paper-3` | `--qv-surface` | task-card / qa-bar 흰 배경 |
| `--paper-2` | `--qv-surface-3` | task-notes 옅은 회색 배경 |
| `--paper` | `--qv-surface-2` | input focus 배경 |
| `--ink` | `--qv-ink` | 제목/본문 |
| `--mute` | `--qv-ink-3` | task-meta 회색 |
| `--line` | `--qv-line` | 보더 |
| `--amber-glow` | `--qv-surface-2` | qa-bar 아이콘 배경 |
| `--amber-deep` | `--qv-ink-2` | date-nav 강조 링크 |
| `--amber` | `--qv-line-3` | task-card hover 보더 |

**Step 2: 컴포넌트 표준화** — 기존 `.bento`/`.kpi-card`/`.kpi-label`/`.kpi-num`/`.kpi-trend`/`.task-card`/`.qa-bar`/`.pill` 그대로 (이미 v3 partial이 `!important`로 오버라이드)

**Step 3: data-dn 디버그 라벨 부착 (7개)**

```
daily-main / daily-pagehead
daily-kpi-bento / daily-quickadd
daily-pending-yday (pending_yday 시) / daily-tasks
daily-weekstats (week_stats 시)
```

**Step 4: 빨강 톤** — 위험/강조 의미 4건 보존
- `.task-card.delay` 좌측 보더 4px (지연)
- `input#newTitle:focus` box-shadow + `.qa-bar select/number/list:focus` border (사용자 input 응답)
- `.pill pill-danger` 🔴 대표 요청 (의미 위험)

**Step 5: 상단 주석** — Quiet Tone v3 마이그레이션 + 부록 B 후속 보류 명시 (v4 룰: 주석 자유 사용 가능)

### 데이터 의존성
- 기존 Jinja 변수 100% 보존: `tasks`, `pending_yday`, `week_stats`, `week_range`, `sel_date`, `prev_date`, `next_date`, `projects`, `customers`, `t.project_name`/`t.project_label`/`t.customer_name`/`t.customer_label`/`t.has_ceo_req`/`t.comment_count` 등
- API 엔드포인트 (`/api/task` POST/PATCH, `/api/carry-forward`) 그대로
- chrome partial include 그대로

---

## 위험 / 주의사항

1. **input focus 빨강** — quiet tone 정신상 잉크가 더 적합할 수 있으나, **사용자 입력 응답의 의미적 빨강**으로 해석하여 보존. home.html과 일관성 유지. v3+ 차수에서 일괄 정리 검토 가능.

2. **focusNewTask JS 함수**의 일시 box-shadow 빨강 — 사용자가 "+새 업무" 클릭 시 0.8초간 강조. 빨강 잔재. 잉크로 변경 권장 (후속).

3. **부록 B specs 미적용 항목** (v3+ 차수로 보류):
   - 시간대별 카드 (오전/오후/야간) — 현재는 통합 task-card 리스트
   - 사진 드래그앤드롭 + 클립보드 paste — JS 신규 구현 필요
   - 자동 저장 디바운스 — 현재는 Enter 즉시 등록
   - 이는 백엔드 로직·JS 신규 작업으로 발주서 룰 ("백엔드 로직 X")과 정합성 검토 필요

---

## 미완료 / 추가 작업 제안

- 22 페이지 중 **2/22 완료** (home, daily). v4 룰 4 (단계 분할) 기준 v2 차수 통과
- 다음 작업: `weekly.html` (3순위) — 자동 취합 + 메일/엑셀 출력
- 부록 B specs 충족은 v3+ 차수에서 통합 진행

---

## 검증 결과

- [x] Quiet Tone v3 토큰만 사용 (잔존 v5 grep 0건)
- [x] data-dn 라벨 7개 부착
- [x] 빨강 사용 — 위험/강조 의미만 (지연 보더 + focus + pill-danger)
- [x] Jinja 변수 / 권한 분기 / 라우트 / API 변경 0건
- [x] `_v5_partials/` / `main.py` / DB / 메인 BAT 미수정
- [x] 외부 라이브러리 추가 없음
- [ ] **?debug=1 라이브 검증** — 서버 가동 후 영역 라벨 7개 확인 필요
- [ ] **1100px 이하 반응형** — 라이브 검증 필요

---

## 동기화 상태 (v4 룰 3 — 옵션 A)

본 워크트리는 메인 폴더 직접 작업 환경 → **자동 동기화 충족**.

- 변경 HTML: `01_HAIST_WORKS/app/templates/daily.html` ✅ 메인 위치
- HANDOFF / PROGRESS / CHANGES_LOG: `01A_HAIST_WORKS_통합플랫폼/output/`, `PROGRESS.md` ✅ 메인 위치

**chat 출력:** "01A v1+v2 차수 메인 폴더 동기화 완료 — daily.html 추가 (누적 2/22)"

---

**다음 산출물 도착 예정:** `weekly.html` (3순위)

**문의:** 추가 사항 있으면 `output/INQUIRY_TO_01_v2.md`
