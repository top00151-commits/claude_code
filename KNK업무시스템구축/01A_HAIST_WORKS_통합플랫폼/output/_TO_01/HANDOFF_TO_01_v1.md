# 📤 실무팀1 → 빅터(01) 1차 산출물 전달 — home.html

**발신:** 실무팀1 (통합플랫폼) · 워크트리 `sad-johnson-eddf3c`
**수신:** 빅터 (01 통합실무팀)
**라우팅:** 김정락 대표이사 → 빅터 통합 라인
**일자:** 2026-05-10
**대상:** 발주서 1순위 페이지 — `home.html` (통합 홈)

---

## 변경 파일 목록

```
01_HAIST_WORKS/app/templates/home.html  (개선)
  ↳ 사본: 01A_HAIST_WORKS_통합플랫폼/changed_templates/home.html
```

**라인 변동:** 473 → 478 (+5 — 상단 주석 4줄 + data-dn HTML 속성)

---

## 작업 요약 (home.html)

### 적용 내용
**Step 1: Quiet Tone v3 토큰 마이그레이션** — inline `<style>` 블록 전부

| 기존 (v5) | 신규 (v3) | 용도 |
|---|---|---|
| `--paper-3` | `--qv-surface` | 카드/사이드바/벤토 카드 흰 배경 |
| `--paper-2` | `--qv-surface-3` | 옅은 회색 보조 |
| `--paper` | `--qv-surface-2` | 본문 배경 |
| `--ink` | `--qv-ink` | 제목/본문 잉크 |
| `--mute` | `--qv-ink-3` | 메타·라벨 회색 |
| `--line` | `--qv-line` | 보더 |
| `--amber-glow` | `--qv-surface-2` | 아이콘 배경 |
| `--amber-deep` | `--qv-ink-2` | 강조 텍스트·링크 |
| `--amber-light` | `--qv-line-2` | 옅은 보더 |
| `--amber` | `--qv-line-3` | 보더 액센트 |
| `--grad-amber` | `--qv-ink` | `.card.hero` / `.scope-tab.active` / `.dock-head` 등 — **잉크 단색** |
| `--grad-knk-red` | `--qv-ink` | `.page-title em` — 잉크 단색 |
| `--shadow-amber` | `0 1px 2px rgba(15,23,42,0.04)` | 미세 그림자 |
| `--glow-amber-radial` | `transparent` | radial glow 제거 |

**Step 2: 컴포넌트 표준화** — 기존 `.bento`/`.page-head`/`.card`/`.kpi-card` 클래스 그대로 사용 (이미 v3 partial이 `!important`로 오버라이드)

**Step 3: data-dn 디버그 라벨 부착 (10개)**

```
home-main / home-pagehead / home-scope-tabs / home-quickadd
home-kpi-bento / home-exec-bento (executive 시)
home-quickactions / home-todays (my_tasks 시)
home-pending-yday / home-team (team_data 시)
```

**Step 4: 빨강 톤 정리**
- 경영진 자물쇠 라벨(라인 306) → 잉크 톤(`--qv-surface-3` 배경 + `--qv-ink-2` 글자) — 권한 표시는 위험 의미 아님
- 보존: `.btn-submit`(CTA 1개) + 의미적 위험/경고(`.card-trend.alert`/조건부 인라인/지연 강조 b)
- 발주서 8.6 "CTA 1개 또는 위험 상태만" 부합

**Step 5: 상단 주석 갱신** — Quiet Tone v3 마이그레이션 내역 4줄 추가 (페이지 버전 라벨 `v5H226z..` 미수정 — 빅터 룰 준수)

### 디자인 토큰
- 모든 `var(--qv-*)` 토큰만 사용 (기존 `--paper`/`--ink`/`--mute`/`--line`/`--amber*` 잔존 0건)
- `--shadow-md`/`--shadow-lg` (v5_tokens.css 정의)는 그림자용으로 그대로 사용

### 데이터 의존성
- 기존 Jinja 변수 100% 보존: `my_tasks`, `pending_yday`, `team_data`, `hw_counts`, `monthly_revenue`, `yoy_delta`, `today_reporters`, `total_users`, `participation_rate`, `is_executive`, `user`, `tab`, `sel_date`, `today`, `prev_date`, `next_date`, `greeting`, `greeting_bucket`, `unread_notif`, `projects`, `customers` 등
- 권한 분기 (`{% if role in ('ceo','admin','executive','leader') %}` / `{% if is_executive %}`) 그대로
- API 엔드포인트 호출 (`/api/task`, `/api/task/{id}/carry`) 그대로
- chrome partial include (`{% include "_v5_partials/chrome.html" with context %}`) 그대로

---

## 위험 / 주의사항

1. **`--shadow-md`/`--shadow-lg` 토큰**은 `v5_tokens.css`에서 정의됨. v3에서 별도 토큰 미정의이나 시각적으로 v3과 잘 어울려 그대로 둠. 추후 v3 전용 그림자 토큰이 정의되면 후속 마이그레이션 가능.

2. **`.card.clickable:hover { box-shadow: var(--shadow-md); }`** 의 그림자 강도가 잉크 배경에서 살짝 강할 수 있음. ?debug=1 라이브 확인 후 보정 가능.

3. **인라인 동적 스타일** (`style="color:var(--knk-red)"`) — `delay_my>0`/`total_my=0` 조건부에서만 빨강. 데이터에 따라 동작 — 위험 상태 의미 보존.

4. **scope-tab.active** 가 잉크 검정 배경 + 흰 글자로 변경됨. 기존 호박 그라디언트 대비 조용한 느낌. 시안1 톤과 일치하나 시각적 어필 약화 — 대표 확인 필요.

---

## 미완료 / 추가 작업 제안

- 22 페이지 중 1/22 완료 — 발주서 우선순위 따라 다음 작업: `daily.html` (2순위)
- daily.html 작업 시 부록 B 시간대별 카드(오전/오후/야간) + 사진 첨부 + 인라인 추가/자동저장 패턴 적용 예정
- 빈 스켈레톤 6개는 후순위로 진행

---

## 검증 결과

- [x] Quiet Tone v3 토큰만 사용 (잔존 v5 토큰 grep 0건)
- [x] data-dn 라벨 10개 부착
- [x] 빨강 사용 — CTA 1개 + 위험/경고 의미만 (발주서 룰 부합)
- [x] Jinja 변수 / 권한 분기 / 라우트 / API 변경 0건
- [x] `_v5_partials/` / `main.py` / DB 미수정
- [x] 외부 라이브러리 추가 없음
- [ ] **?debug=1 라이브 검증** — 서버 가동 후 대표·빅터 측 확인 필요
- [ ] **1100px 이하 반응형 라이브 검증** — Launch preview 좁힘 또는 실제 브라우저 검증 필요

---

## 빅터 통합 절차 제안

1. 빅터 메인 폴더의 `home.html`에 본 사본 `01A_HAIST_WORKS_통합플랫폼/changed_templates/home.html` 내용 적용
2. 메인 폴더의 z48+ 추가 변경사항이 home.html에 있다면 conflict resolve (현재까지 z48 partial은 chrome 영역만 변경 — home 본체에 conflict 가능성 낮음)
3. 적용 후 ?debug=1 모드로 영역명 확인 (10개 라벨 모두 보여야 함)
4. 1100px 이하에서 반응형 동작 확인
5. 통합 commit 후 STATUS.md 갱신 (빅터 담당)

---

**다음 산출물 도착 예정:** `daily.html` (2순위) — 부록 B specs 발췌 적용

**문의:** 추가 사항 있으면 `output/INQUIRY_TO_01_v2.md` (다음 차수)
