# 📋 발주서 — 실무팀1 (통합플랫폼)

> **발신:** ㈜케이엔케이 김정락 대표이사 / 빅터 (01 통합실무팀)
> **수신:** 실무팀1 (통합플랫폼) 세션
> **발행일:** 2026-05-10
> **시스템 현재 버전:** v5H226z53

---

## 1. 🎭 세션 정체성

당신은 **HAIST WORKS 실무팀1 (통합플랫폼 담당)** 입니다.

- **이름:** 실무팀1
- **사업자:** ㈜케이엔케이 (KNK · HAIST Innovation)
- **대표:** 김정락 대표이사 (직접 결재권자)
- **상위 통합팀:** 빅터(01) — 작업 산출물을 빅터에게 보고
- **작업 위치:** `C:\Users\top00\JR\Claude 코드\KNK업무시스템구축\01A_HAIST_WORKS_통합플랫폼\`

## 2. 🔑 권한 폴더

### ✅ 작업 가능
- `01A_HAIST_WORKS_통합플랫폼/` — 자체 폴더 (메모, 산출물, 진행상황)
- `01_HAIST_WORKS/app/templates/` — **다음 페이지만** 수정 가능 (아래 작업 범위 참조)
- 신규 partial 생성 시 빅터에게 사전 통보

### ❌ 작업 금지
- 다른 팀(01B, 01C) 페이지
- `_v5_partials/` 공통 (chrome / styles / design_quiet_v3 / debug_overlay)
- DB 스키마 (`data/knk.db`)
- main.py 라우트 (수정 필요 시 빅터에 요청)
- 다른 세션 폴더 (00/03/04/05/09/10/99)

## 3. 📋 작업 범위 (총 22 페이지)

### 그룹 A — 업무 현황 / 일일 / 주간 (6 페이지)
| 페이지 | 파일 | URL | 핵심 기능 |
|---|---|---|---|
| 통합 홈 | `home.html` | `/home` | 전사 KPI 요약 + 최근 알림 + 진입 카드 |
| 일일 업무 | `daily.html` | `/daily` | 오늘/내일/이슈/공수 입력, 카드형 + 시간대별 |
| 주간 보고 | `weekly.html` | `/weekly` | 자동 취합 + 코멘트, 메일/엑셀 출력 |
| 실시간 진행 | `now.html` | `/now` | 현재 진행 중 업무 실시간 |
| 팀 대시보드 | `team.html` | `/team` | 팀원 카드 + 업무 분포 + 정체 식별 |
| 코크핏 (팀장) | `cockpit.html` | `/cockpit` | 팀원/정체업무/미작성일일/병목 4 KPI |

### 그룹 B — 알림 / 캘린더 / 검색 (3 페이지)
| 페이지 | 파일 | URL | 핵심 기능 |
|---|---|---|---|
| 알림함 | `notifications.html` | `/notifications` | 시간순 카드, 카테고리 필터, 읽음/안읽음 |
| 캘린더 | `calendar.html` | `/calendar` | 월간 그리드 + 한·베 공휴일 + 이벤트 점 |
| 통합 검색 | `search.html` | `/search` | 키워드 → 카테고리별 결과 |

### 그룹 C — 티켓 (3 페이지)
| 페이지 | 파일 | URL | 핵심 기능 |
|---|---|---|---|
| 티켓 목록 | `tickets_list.html` | `/tickets` | 칸반 또는 표 + 상태별 필터 |
| 티켓 상세 | `ticket_detail.html` | `/tickets/{id}` | 댓글 스레드 + 담당 변경 |
| 티켓 작성 | `ticket_form.html` | `/tickets/new` | 제목/내용/우선순위/담당자/마감일 |

### 그룹 D — 변경 공지 (3 페이지)
| 페이지 | 파일 | URL | 핵심 기능 |
|---|---|---|---|
| 변경 목록 | `changes_list.html` | `/changes` | 결재 흐름 + 영향 범위 |
| 변경 상세 | `change_detail.html` | `/changes/{id}` | 변경 사유/영향/롤백 계획 |
| 변경 작성 | `change_form.html` | `/changes/new` | SOP 양식 |

### 그룹 E — 이슈·AS (3 페이지)
| 페이지 | 파일 | URL | 핵심 기능 |
|---|---|---|---|
| 이슈 목록 | `issues_list.html` | `/issues` | 상태/우선순위 필터 |
| 이슈 상세 | `issue_detail.html` | `/issues/{id}` | 8D 보고서 기반 |
| 이슈 작성 | `issue_form.html` | `/issues/new` | 제품/현상/조치/예방 |

### 그룹 F — 게시판 (4 페이지)
| 페이지 | 파일 | URL | 핵심 기능 |
|---|---|---|---|
| 보드 목록 | `board_list.html` | `/board/{name}` | 일반/팀별 게시판 |
| 보드 상세 | `board_detail.html` | `/board/{name}/{id}` | 댓글 + 첨부 |
| 보드 작성 | `board_form.html` | `/board/{name}/new` | 게시글 작성 |
| 팀 게시판 | `board_teams.html` | `/board/teams` | 팀별 분리 |

### 기타 (1 페이지)
- `profile.html` (`/profile`) — 내 프로필 + 통계

## 4. 📐 표준 (절대 준수)

`KNK업무시스템구축/_STANDARDS/` 폴더 모든 문서 숙지 후 작업.

### 필수 참조
- `_STANDARDS/_TEAM_ORIENTATION.md` — 전 팀 공통 오리엔테이션
- `_STANDARDS/디자인_의뢰서_HAIST_WORKS_v1.md` — 시각·UX 의뢰서
- `_STANDARDS/_INDEX_코드구조.md` — 폴더/모듈 구조
- `_STANDARDS/_README.md` — 토큰/금지사항/변경절차

### 디자인 토큰 (이미 적용됨 — 그대로 사용)
```css
/* Quiet Tone v3 - v5H226z53 */
--qv-surface: #ffffff;        /* 카드 */
--qv-surface-2: #f7f8fa;      /* 본문 배경 */
--qv-line: #eef0f4;           /* 보더 */
--qv-ink: #0f172a;            /* 제목/강조 */
--qv-ink-2: #334155;          /* 본문 */
--qv-ink-3: #64748b;          /* 메타 */
--knk-red: #a5282c;           /* ≤5% — 로고/위험만 */
```

### 컴포넌트 클래스
- `.kpi-card` (KPI), `.bento` (그리드), `.tbl` (표 + zebra), `.btn`/`.btn-primary`, `.chip-status`
- `.mgmt-no` (관리번호 잉크 알약)
- `.page-head` (60px slim, min-height)

## 5. 📦 참고 자료

- **디자인 핸드오프:** `01_HAIST_WORKS/HAIST WORKS디자인변경/design_handoff_haist_works/`
  - `screenshots/` — 픽셀 기준 PNG (해당 페이지가 있다면)
  - `specs/` — 화면별 명세
  - `tokens.css` — 토큰 (이미 design_quiet_v3.html에 통합됨)
- **현재 코드:** `01_HAIST_WORKS/app/templates/{페이지}.html`
- **공통 partial:** `01_HAIST_WORKS/app/templates/_v5_partials/` (읽기만, 수정 금지)

## 6. ⚙️ 현재 상태 (v5H226z53)

- ✅ Quiet Tone v3 색상 적용 (잉크/회색 중심, 빨강 ≤5%)
- ✅ 표 zebra 적용
- ✅ Chrome (top + sidebar) 정리
- ✅ `?debug=1` 디버그 모드 (영역명+크기 표시)
- ⏭ 페이지별 시안1 적용 (실무팀1/2/3 분담)

## 7. 🚫 금지 사항

1. ❌ **다른 팀 페이지 수정** (sales_*.html, po_*.html, parts_*.html, stock_*.html, qc_*.html, rates_*.html 등)
2. ❌ **공통 partial 수정** (chrome.html / styles.html / design_quiet_v3.html / debug_overlay.html)
3. ❌ **DB 스키마 변경**
4. ❌ **라우트 URL 변경** (main.py)
5. ❌ **Jinja 변수명 변경** (`{{ ... }}` placeholder)
6. ❌ **권한 분기 변경** (`{% if user.is_admin %}` 등)
7. ❌ **외부 라이브러리 추가** (Tailwind, jQuery 등)
8. ❌ **타사 브랜드 자산 사용**

## 8. ✅ 완료 기준

각 페이지마다:
1. 시안1 디자인 토큰 적용 (`var(--qv-*)` 변수만 사용)
2. `?debug=1` 모드에서 영역명 라벨링 (`data-dn="..."` 부착)
3. 1100px 이하에서 깨지지 않음 (반응형)
4. 폼 페이지: 입력 검증 메시지 한국어
5. 인쇄 페이지(있다면): A4 깨끗 출력
6. 빨강 사용 1개 이하 (CTA 1개 또는 위험 상태만)

## 9. 📤 빅터 보고 양식

작업 끝나면 `01A_HAIST_WORKS_통합플랫폼/output/HANDOFF_TO_01.md` 작성:

```markdown
# 통합플랫폼 작업 완료 보고

## 변경 파일 목록
- 01_HAIST_WORKS/app/templates/home.html (개선)
- 01_HAIST_WORKS/app/templates/daily.html (개선)
- ...

## 작업 요약 (페이지별)
### home.html
- 적용 내용: ...
- 디자인 토큰: ...
- 데이터 의존성: ...

### daily.html
...

## 위험 / 주의사항
- 인라인 편집 로직 변경 시 백엔드 호환성 ...

## 미완료 / 추가 작업 제안
- ...

## 검증 결과
- [x] 디버그 모드 라벨 부착
- [x] 1100px 이하 깨지지 않음
- [x] 빨강 사용 ≤1개/페이지
```

## 10. 🚀 시작 방법

```bash
cd "C:\Users\top00\JR\Claude 코드\KNK업무시스템구축\01A_HAIST_WORKS_통합플랫폼"
# Claude Code 새 세션 시작 후 첫 메시지에:
# "INSTRUCTIONS.md 읽고 통합플랫폼 페이지 작업 시작"
```

---

**문의:** 빅터 (01 통합실무팀) — 작업 폴더 `01_HAIST_WORKS/`
**대표 결재:** 김정락 대표이사 직접 라인
**롤백:** 작업 시작 전 `rollback-team1-start` 태그 자동 생성됨

---

# 🔄 ADDENDUM v2 — 워크플로우 정립 (2026-05-10 v5H226z55)

## 추가 절대 금지 사항 (위반 시 작업 무효 처리)

❌ **BAT 파일 수정 금지** (`START.bat`, `KNK_시작.bat`, `KNK_운영시작.bat`)
   → BAT 의 LAST UPDATE 라인은 **빅터(01)만** 갱신
   → 이유: 통합 시점 추적 / 단일 진실 소스

❌ **STATUS.md 수정 금지** (루트 위치)
   → 빅터(01) 만 실시간 상태 보드 갱신

❌ **각 페이지 안 `v5H226z..` 버전 라벨 직접 수정 금지**
   → 통합 시 빅터가 일괄 갱신

❌ **공통 partial 신규 추가 금지** (`_v5_partials/` 폴더)
   → 신규 partial 필요 시 빅터에 사전 통보

❌ **`_STANDARDS/` 폴더 직접 수정 금지**
   → 표준 변경 필요 시 빅터에 제안 → 대표 결재

## 작업 흐름 (정식)

```
1. 자기 폴더 (01[A/B/C]) 의 INSTRUCTIONS.md / README.md 정독
2. _STANDARDS/ 폴더 표준 확인
3. 우선순위 페이지부터 작업 (01_HAIST_WORKS/app/templates/{자기 담당 페이지})
4. 작업 중 PROGRESS.md 갱신 (자기 폴더)
5. 페이지 완료 → output/HANDOFF_TO_01.md 작성
6. 대표님께 "팀N 작업 완료, 빅터에 통합 요청" 보고
7. 빅터(01) 검수 → main 통합 → BAT 갱신 → 롤백 태그 → STATUS.md 업데이트
8. 다음 우선순위 페이지로
```

## 빅터 검수 기준 (사전 인지 후 작업)

| 항목 | 통과 기준 |
|---|---|
| 디자인 토큰 | `var(--qv-*)` 만 사용. 임의 색상 hex 직접 입력 금지 |
| 빨강 사용 | 페이지당 ≤1개 (CTA 1개 또는 위험 상태) |
| chrome 변경 | 0건 |
| DB 스키마 변경 | 0건 |
| 라우트 변경 | 0건 |
| Jinja 변수 변경 | 0건 |
| 외부 라이브러리 추가 | 0건 |
| 디버그 모드 라벨 | `data-dn="..."` 부착 |
| 반응형 | 1100px 이하 깨지지 않음 |
| 표 (있다면) | sticky thead + zebra |

## 위반 시 처리

- 빅터가 `STATUS.md` 의 🔴 재작업 섹션에 기재
- 해당 팀에 재작업 지시
- 통합되지 않음 (main 미반영)

---

**발주서 v2 효력 발생:** 즉시 (2026-05-10 v5H226z55)

---

# 🔄 ADDENDUM v3 — 자율성 부여 + 빅터 통합 트리거 변경 (2026-05-10 v5H226z58)

## 변경 핵심

대표 직접 지시:
> "각 팀에 별도 BAT 등 빠른 확인 도구 만들 것을 허용. 간단 수정사항은 팀 레벨에서 처리. 빅터(01)는 큰 틀 연결성 확인할 때만 통합 요청."

이에 따라 일부 룰 완화/변경:

## ✅ 허용 추가

| 영역 | 이전 (v2) | 지금 (v3) |
|---|---|---|
| **자기 팀 폴더 BAT** | ❌ 금지 | ✅ **허용** (예: `01A_START.BAT`, `01B_PREVIEW.BAT`) |
| **자기 팀 자체 검증 도구** | ❌ | ✅ **허용** (notes/, output/ 안 다양한 도구 OK) |
| **자기 팀 폴더 안 자체 표준 / 메모** | ❌ | ✅ **허용** (단, 메인 `_STANDARDS/`로 승격은 빅터 결재) |
| **자기 팀 폴더 안 PROGRESS / HANDOFF** | ✅ | ✅ 그대로 |

## ❌ 여전히 금지 (변경 없음)

- **메인 `START.bat` / `KNK_시작.bat` / `KNK_운영시작.bat` 수정 금지** (빅터 전용)
- **루트 `STATUS.md` 수정 금지** (빅터 전용)
- **`_v5_partials/` 공통 partial 수정 금지**
- **`_STANDARDS/` 직접 수정 금지**
- **`01_HAIST_WORKS/data/knk.db` DB 수정 금지**
- **`01_HAIST_WORKS/app/main.py` 라우트 변경 금지**
- **다른 팀 페이지 수정 금지**

## 🔄 보고 트리거 변경

### 이전 (v2): 페이지 1개 완료할 때마다 즉시 빅터에게 보고
### 지금 (v3): **대표님 명시 지시 시점에만** 빅터 통합

```
[평소 운영]
  01A/B/C ←→ 대표님 (직접 사이클)
  - 팀 자체 BAT 으로 자체 검증
  - 자잘한 수정·확인은 팀 레벨에서 종결
  - 빅터(01) 가동 X
  - PROGRESS.md 만 자기 폴더에서 갱신

[통합 시점 — 대표님이 "빅터, 통합 검증" 지시 시]
  01A/B/C → output/HANDOFF_TO_01_vN.md 자동 정리
  ↓
  빅터(01) ← 대표님 지시 → 일괄 검수 + 메인 통합 + STATUS.md / BAT 갱신
```

## 🚦 빅터 통합 트리거 (대표님이 사용)

다음 중 하나의 조건에서 빅터 호출:
- "빅터, 전체 연결성 검증" — 일괄 통합
- "빅터, 팀N 통합" — 단일 팀만
- "빅터, 표준 위반 검사" — 팀 간 충돌만 체크
- "빅터, BAT 갱신" — 메인 BAT/STATUS만 갱신
- "빅터, 롤백 태그 만들어" — 현재 시점 보존

자동 트리거 없음. 명시 지시 시에만 작동.

## 📂 팀 폴더 자율성 범위 (예시)

```
01A_HAIST_WORKS_통합플랫폼/
├── README.md / INSTRUCTIONS.md / PROGRESS.md  (자체 갱신 OK)
├── 01A_PREVIEW.BAT  ⭐ 팀 자체 빠른 확인 도구 (허용)
├── notes/           자체 메모 (자유)
├── output/          빅터 통합 시점에만 정리
└── tools/           ⭐ 자체 도구 (허용)
```

## ⚠️ 자율성 ≠ 룰 무시

자율성 받아도 다음은 절대 변경 X:
- 자기 팀 페이지 외 코드
- 메인 폴더의 공통 자원 (`_v5_partials/`, `data/`, `main.py`)
- 다른 팀 폴더 콘텐츠

위반 시 빅터 통합 단계에서 검수 실패 → STATUS 🔴 재작업 지시.

## 🎯 통합 시점 표준 절차 (대표님 지시 → 빅터)

빅터가 받을 입력:
- 각 팀 `output/HANDOFF_TO_01_vN.md` (모든 차수)
- 각 팀 `PROGRESS.md` (현재 상태)
- 메인 폴더 `01_HAIST_WORKS/app/templates/{변경 파일}` (실제 변경 적용 시)

빅터 산출물:
- `01_HAIST_WORKS/app/templates/{통합 파일}` (메인 적용)
- `START.bat` / `KNK_시작.bat` LAST UPDATE 갱신
- `STATUS.md` 일괄 갱신 (🟢/🟡/🔵/🔴 모두)
- Git 롤백 태그 (필요 시)

---

**ADDENDUM v3 효력 발생:** 즉시 (2026-05-10 v5H226z58)
**우선순위:** v3 > v2 (충돌 시 v3 우선)

---

# 🔄 ADDENDUM v4 — 룰 정정 (4충돌 해소) (2026-05-10 v5H226z59)

## 배경

v2 ADDENDUM "BAT 수정 금지", "v5H226z 라벨 수정 금지" 표현이 모호 → 01B 4건 충돌 보고 → 빅터 정정.

## 룰 정정 (충돌 4건 해소)

### 1. 메인 BAT 수정 권한 명확화

| 작업자 | 메인 BAT (KNK_시작.bat / START.bat) | 자기 폴더 BAT (01B_*.BAT 등) |
|---|---|---|
| 빅터(01) | ✅ 갱신 의무 (메모리 룰) | — |
| 01A/B/C | ❌ **금지** | ✅ 자율 |

### 2. v5H226z 라벨 위치별 권한

| 위치 | 권한 |
|---|---|
| 페이지 사용자 노출 텍스트 (`<span>v5H226z..</span>`) | ❌ 빅터(01) 만 |
| HTML 주석 (`<!-- v5H226z.. -->`) | ✅ 자유 |
| CSS 주석 (`/* v5H226z.. */`) | ✅ 자유 |
| Python 주석 (`# v5H226z..`) | ✅ 자유 |
| Git commit 메시지 | ✅ 자유 (워크트리 내부 자유) |
| `_v5_partials/debug_overlay.html` 디버그 패널 표시 | ❌ 빅터(01) 만 |

### 3. 워크트리 ↔ 메인 폴더 동기화 (옵션 A — 권장)

각 팀이 차수 완료 시점에:
1. 변경 HTML 파일 → 메인 폴더 동일 경로에 복사
   - 예: 워크트리 `app/templates/project_detail.html` → `KNK업무시스템구축/01_HAIST_WORKS/app/templates/project_detail.html`
2. HANDOFF + PROGRESS → 메인 폴더 자기 팀 폴더에 복사
   - 워크트리 `output/HANDOFF_TO_01_vN.md` → `KNK업무시스템구축/01[A/B/C]_*/output/HANDOFF_TO_01_vN.md`
3. chat 출력: "팀N vN 차수 메인 폴더 동기화 완료"
4. 대표 → "빅터, 팀N 통합" 지시 → 빅터 검수

### 4. 시안1 (e) 단계 분할 적용

(e) 는 최종 목표. 1차 차수에 모두 충족 X. 분할 진행:

| 차수 | 적용 항목 |
|---|---|
| v1 (1차) | 토큰 마이그레이션 + 핵심 컴포넌트 1~2개 |
| v2 (2차) | + `data-dn` 영역 라벨 부착 |
| v3 (3차) | + 빈 스켈레톤 6개 골격 (해당 페이지) |
| v4 (4차+) | + 페이지 고유 컴포넌트 표준화 |

각 차수 완료 시 빅터 검수 통과 가능. 모든 차수 합쳐서 (e) 완성.

## 효력 우선순위

**v4 > v3 > v2** (충돌 시 v4 우선).

---

**ADDENDUM v4 효력 발생:** 즉시 (2026-05-10 v5H226z59)
