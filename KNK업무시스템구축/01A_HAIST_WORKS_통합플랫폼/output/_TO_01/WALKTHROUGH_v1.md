# 🚶 페르소나 Walkthrough v1 — 22 페이지 시뮬레이션

**작성:** 실무팀1 (코드 정독 기반 시뮬레이션 / 라이브 검증 X)
**일자:** 2026-05-10
**목적:** 빅터 통합 검수 + 04 운영테스트팀 회귀 자료 + 05 디자인팀 시각 점검 자료
**주의:** 이 문서는 **코드 정독 기반 시뮬레이션**입니다. 라이브 환경 검증은 별도 필요.

---

## 페르소나 1 — 김대표 (CEO, 매일 아침 9시 통합 홈 진입)

### 진입: `/home` (통합 홈)

**시각 첫 인상 (예측):**
- 잉크 검정 hero KPI 카드 좌측 (전 amber 그라디언트 → 잉크 단색) — 차분한 권위
- 7개 KPI 벤토 그리드 (clickable) — 흰 배경 + 회색 보더, 호버 시 잉크 보더
- 경영진 KPI 영역(executive) — 자물쇠 라벨이 회색(잉크 톤)으로 표시 (전 빨강 → 정정됨)
- 빠른 액션 4개 — 회색 배경 아이콘 + 잉크 텍스트
- 우측 알림 뱃지(`unread`) — 빨강 (의미적 보존, 카운트 표시)

**예상 페인 포인트:**
- `.scope-tab.active` 잉크 검정 배경 + 흰 글자 — 시각 액센트가 amber 시절 대비 약화. 클릭한 탭 식별이 살짝 어렵게 느껴질 수 있음.
- "지연 카드" 빨강 경고 동작 정상 (delay_my>0 시)
- "어제 미완료" `--warn` 보더 (호박색 → 변경 안 됨, 의미적 위험 보존)

**문제 가능성:**
- ⚠ `style="border-color:var(--warn);"` (라인 292) — `--warn`이 v5 `#f59e0b` 호박색 그대로. quiet tone에서 "위험 의미"는 잉크/회색이 더 일관적일 수 있음. v3+ 검토 후보.

### 다음 진입: `/cockpit` (팀장 코크핏)
- 4 KPI: 팀원 / 정체 업무(노랑) / 미작성 일일(빨강) / 병목
- "정체 업무" tbl-sticky 정상
- 미작성 일일 명단

**예상 페인:** 표시 OK. 데이터 적을 때 빈 영역.

---

## 페르소나 2 — 박PM (프로젝트 매니저, /home → /daily → /weekly 순환)

### `/daily` 일일 업무

**시각:**
- task-card 목록, 지연 카드는 좌측 빨강 보더 4px
- qa-bar 빠른 입력 — focus 시 빨강 box-shadow (사용자 입력 응답)
- 어제 미완료 카드 (warn 보더 4px)

**예상 사용:**
- 매일 16:30 마감 전 빠른 입력 → Enter
- 입력란에 placeholder "지금 무슨 업무를 하고 계신가요?" — quiet 톤

**잠재 이슈:**
- 시간대별 카드(부록 B specs)가 적용되지 않음 → 모든 task가 통합 리스트
- 사진 첨부도 없음 (v3+ 차수)
- 경험상 큰 차이는 없으나 부록 B 명세 미충족 표시

### `/weekly` 주간 보고
- victor-insight 카드 — 잉크→#4A2F1F 그라디언트 (warm 잉크 톤). amber-glow 라벨도 현재 v3 토큰 적용.
- 4 KPI: 전체/완료/공수/지연
- 부서별 현황 (팀장+) — `--warn` 보더 (50% 미만 시) — 의미적 보존
- 인쇄 버튼 (window.print()) — `@media print` 적용 → A4 출력 가능

**잠재 이슈:**
- victor-insight `var(--qv-ink) → #4A2F1F` 그라디언트는 그대로 — 부드러운 잉크 그라디언트. quiet 톤에서 OK.

---

## 페르소나 3 — 이매니저 (영업, /tickets 발행 → /changes 작성)

### `/tickets` (티켓 목록)
- 필터바: 검색 + 상태 + 긴급도 selects (v3 토큰)
- 표 zebra (v3 partial 자동 적용)
- 티켓 ID `#123` 잉크 톤(전 amber-deep → qv-ink-2)
- 긴급/심각 pill — 빨강 (의미적)
- 기한 초과 pill — 빨강 (조건부)

**예상 OK.**

### `/tickets/new` (티켓 작성)
- 폼 카드 (form-card) 흰 배경
- 필수(*) 별표 빨강 — UX 관습 보존
- input focus border 잉크 (전 amber → qv-ink)
- focus shadow `var(--qv-surface-2)` — 옅은 회색 후광

**예상 OK.**

### `/changes/new` (변경 공지 작성) — 동일 패턴

---

## 페르소나 4 — 정대리 (구매·QC, /issues 등록)

### `/issues` (이슈·AS 목록)
- 4 KPI: 전체 / 미해결(빨강) / 심각(빨강) / 완료(녹색)
- 표 zebra
- ID `#123` amber-deep → qv-ink-2 잉크 톤

### `/issues/{id}` (이슈 상세)
- detail-grid 1+320px (v3 partial 적용)
- section-card h3::before 빨강 막대 — **이슈 페이지 위험 의미**, 보존이 의미적 정확
- ID `#123` 빨강 (의미적 위험)
- SLA 초과 ⚠ 빨강 (의미적)

**예상 OK.** 이슈 페이지의 빨강은 의미적으로 적합.

---

## 페르소나 5 — 김사원 (일반 직원, /notifications · /board)

### `/notifications`
- notif-item 카드 — 미읽음은 좌측 빨강 보더 4px + 옅은 회색 배경
- NEW pill-danger 빨강
- 시간 표시 — 잉크-2

**예상 OK.**

### `/board/{name}` (게시판)
- 표 zebra
- 고정글 핀 pill-danger 빨강 (의미적)
- 카테고리 pill-muted 잉크 톤

### `/board/{name}/new` (글 작성)
- form-card 표준 폼

**예상 OK.**

---

## 페르소나 6 — 자기 (모든 직원, /profile)

### `/profile`
- profile-hero 잉크 단색 카드 (전 amber 그라디언트 → 잉크) — 차분
- avatar-lg 흰 원 + 잉크 글자 (전 빨강 → 정정됨, v3 보강)
- KPI 4: 30일 업무 / 진행중 / 댓글 / 미읽음 알림(조건부 빨강)
- 기본 정보 수정 폼 — 잉크 보더 액센트 (전 amber → qv-line-3)
- 권한 매트릭스 — 잉크 막대 (전 빨강 → 정정됨)
- 위임받은 권한 태그 — 회색 배경 + 잉크 글자 (전 빨강 rgba → 정정됨)

**예상 OK.** 권한 표시가 위험 의미 아닌 것 정정 완료.

---

## 종합 페인 포인트 매트릭스

| 우선순위 | 항목 | 페이지 | 근거 |
|---|---|---|---|
| 🟡 중 | `--warn` 호박색 잔존 (지연·warning 보더) | home, daily, weekly | quiet 톤에서 잉크/회색이 더 일관적일 수 있음. v3+ 검토 |
| 🟡 중 | victor-insight `#4A2F1F` 잉크 그라디언트 | weekly | 시각 OK이나 잉크 단색이 더 quiet |
| 🟢 약 | scope-tab.active 잉크 배경 액센트 약화 | home | 호박 → 잉크 변경. 클릭 식별 약간 약화 |
| 🟢 약 | ticket_detail 빅터 박스 강조 약화 | ticket_detail | amber-glow 배경 → qv-surface-2. 일반 카드와 시각 차별 약화 |
| 🟢 약 | input focus 빨강 보존 | daily, ticket_form 등 | UX 의미 보존이지만 quiet 톤 정책 결정 필요 |

**모든 페인은 v3+ 차수 검토 후보**이며, **v1+v2 차수 통과에는 영향 없음**.

---

## 결론

- 22 페이지 시각 첫 인상 모두 quiet 톤 부합 (잉크 + 회색 + 흰색 중심)
- 빨강은 의미적 위치(CTA / 위험 / 카운트 / 필수 별표)에만 유지
- 잉크 단색 그라디언트로 hero/탭/dock-head/profile-hero 정정 완료
- 부록 B specs 백엔드 의존 항목은 v3+ 보류 (룰 위반 회피)

**빅터 통합 후 라이브 검증 필요 (?debug=1 + 1100px 반응형).**
