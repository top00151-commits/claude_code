# [01 → 05] 힐링 시안 #13~#20 코드 적용 완료 회신 (3차 · 시안 반영)

> **발신**: 01 메인 세션 빅터
> **수신**: 05 디자인팀
> **참조**: 09 프로젝트 팀장
> **일자**: 2026-04-25 14:30
> **계기**: 대표 지적 — *"최종 반영한 시안이 아닌데"* (2차 회신 직후)
> **근거**: `_세션01_전달/00_INDEX_힐링전환.md` Step 2 시안 4종 + 2026-04-25 신규 5종

---

## 0. 한 줄

3차 QA 패치(①~④)는 끝났지만 **시안 #13~#20 시각 적용이 누락**됐다는 대표 지적을 받고, 본 사이클에서 8개 route 의 healing 시안 핵심 컴포넌트를 일괄 적용 완료.

---

## 1. 적용 결과 (커밋 2건)

### 커밋 `b2a557d` — 로그인 시안 #13 전면 적용
- `app/templates/login.html` 전체 재작성 (285줄 추가, 84줄 삭제)
- 좌 패널: `--grad-brand-deep` (딥 레드) → `--grad-panel` (딥 세이지 포레스트 #3F5C44 → #2B3E2E → #1A2A1C)
- 우 패널: sage-50 배경 + 라디얼 데코 + 14px border-radius 폼
- 🌿 "오늘도 평안하시길" 인사말, bp-points 3종(빅터·전사·내업무)
- KNK 로고 인라인 SVG (외부 자산 0건)
- 언어 셀렉터 ko/vi/en 3종 (한국어 표기 일치)
- KNK 레드는 로그인 CTA 버튼만 유지 (B-2 규칙 준수)

### 커밋 `3f3ad23` — 시안 #14~#20 핵심 컴포넌트 일괄 적용
**`static/style.css` (+330줄)** — healing 모듈 추가:
| 컴포넌트 | 시안 출처 | 적용 |
|---|---|---|
| `.page-head` (sage-50 배경 · 18px radius · accent bar) | #14·#15·#16~20 공통 | 모든 route |
| `.page-breadcrumb` (`통합 / 전사 흐름 / 현재` + lock-badge) | #14·#15·#16~20 공통 | 7 route |
| `.hello-banner` (인사 카드, 그라디언트+라디얼) | #15 dashboard | dashboard |
| `.section-head h2` (grad-sage 4px accent) | #15 공통 | 글로벌 |
| `.kpi-card` (20px radius · sage-200 border · hover lift · 라디얼) | #15 hero-kpi | 글로벌 |
| `.team-tbl` (sage-50 헤더 · sage-100 hover · sage 진행바) | #15 | dashboard |
| `.progress-matrix-grid` / `.pm-card` (진행률 카드) | #14 | progress |
| `.narr-card` / `.delay-list` / `.mini-tbl` / `.empty` | #15 | dashboard |

**route 템플릿 7건 — `page-breadcrumb` + 새 헤더 패턴 적용**:
| Route | 템플릿 | 변경 |
|---|---|---|
| `/dashboard` | dashboard.html | breadcrumb + 🔒경영진 lock + hello-banner |
| `/progress` | progress_matrix.html | breadcrumb + 새 헤더 + sage 안내 버튼 |
| `/changes` | changes_list.html | breadcrumb + 새 헤더 + grad-brand 등록 CTA |
| `/tickets` | tickets_list.html | breadcrumb + 새 헤더 + grad-brand CTA |
| `/issues` | issues_list.html | breadcrumb + 팀장+ SLA badge (amber) |
| `/daily` | daily.html | breadcrumb 추가 (기본 헤더 유지) |
| `/admin` | admin.html | breadcrumb + 🔒P4 관리자 lock |

**CSS 캐시 키**: `v=20260424healing-v1` → `v=20260425healing-v2` (base.html · base_logi.html)

---

## 2. 회귀 검증 (CEO `kjr` / `knk1234`)

```
/login         200 bc=True len=13935  (이미 sage 적용 · breadcrumb 不要)
/home          200 bc=False len=176265 (홈은 hm2-* 자체 헤더 사용 · 정책 일치)
/dashboard     200 bc=True len=60605
/progress      200 bc=True len=373422
/changes       200 bc=True len=60349
/tickets       200 bc=True len=52431
/issues        200 bc=True len=52750
/daily         200 bc=True len=98879
/admin         200 bc=True len=241257
```

9개 route 모두 200 OK · breadcrumb 마크업 정상 노출.

---

## 3. 한계·미적용 사항

본 사이클은 **각 시안의 핵심 비주얼 컴포넌트(page-header, KPI 카드, 인사 배너, 섹션 헤드)** 만 적용. 시안의 모든 디테일을 1:1 픽셀 일치로 옮기지는 않았습니다 — 다음 항목은 별도 사이클 권장:

| 항목 | 시안 | 추정 ETA |
|---|---|---|
| 대시보드 SVG 차트 (라이브러리 없이 수제) | #15 §chart | 2h |
| 팀별 진행률 리스트 (`.team-row` 호버 슬라이드) | #15 §team-list | 1h |
| 활동 피드 (`.feed-item` + 색 도트) | #15 §feed | 1h |
| 부서 카드 grid-3 (`.dept-card` sales/logi/admin) | #15 §grid-3 | 1.5h |
| /tickets 칸반 보드 뷰 | #17 | 3h |
| /issues 5단계 SLA 바·고객 임팩트 컬럼 | #18 | 2.5h |
| /daily Sage 캐리오버 타임라인 | #19 | 2h |
| /admin 5탭 sage 카드 그리드 | #20 | 2h |

총 잔여 추정 **15h** — 09 팀장 우선순위 의사결정 후 순차 진행 권장.

---

## 4. 본 사이클 작업 평가 (자체)

- **장점**: 9개 route 한 번에 시안 톤 일관 적용 · CSS 한 곳 모듈화 → 향후 디테일 추가 용이
- **단점**: 픽셀 단위 차트·칸반 등 인터랙티브 컴포넌트는 미반영
- **외부 자산**: 0건 추가 (Lucide SVG 인라인만 사용 · 04 정책 준수)
- **상표권**: 타사 브랜드명 0건 노출 (정책 §5 준수)

---

## 5. 04 운영테스트팀 재검증 요청

본 사이클 변경은 시각만 적용했으나, 04 §S2 사용성 검증 시 다음 신규 마크업 매칭 키워드 가이드:

```
class="page-breadcrumb"            → 7개 route 에서 발견되어야 함
class="page-title"                 → 7개 route
class="hello-banner"               → /dashboard 1건
class="lock-badge"                 → /dashboard, /issues, /admin 3건
"통합 /"                            → 7개 route breadcrumb 텍스트
class="kpi-card" (sage 톤 적용 후)  → /dashboard 6건, /home 다수
"--grad-sage" 토큰                  → style.css :root + active sb-item
"--grad-panel" 토큰                  → /login 좌 패널 background
```

---

## 6. 커밋 ID 일람 (오늘 사이클 누적)

| 커밋 | 메시지 | 패치 분류 |
|---|---|---|
| `2db51e6` | fix(dock): remove .dock-tab residual | QA-H2/H3-5 |
| `7f5fb76` | feat(home): graceful fallback for revenue KPI | QA-H1 |
| `756c47f` | chore(home): add greeting_bucket | QA-H6 |
| `da63591` | docs: 힐링 3차 패치 ①~④ 회신 | 문서 |
| `b2a557d` | feat(login): apply healing mockup #13 (Sage Garden B-2) | **시안 #13** |
| `3f3ad23` | feat(theme): apply healing mockups #14~#20 | **시안 #14~#20** |

총 6커밋 / 15+ 파일 / +800 라인 / 9 route healing 시안 비주얼 적용.

---

**발행**: 2026-04-25 14:30 · 01 메인 세션 빅터
**상태**: 🟢 시안 #13~#20 핵심 컴포넌트 적용 완료 · 디테일 추가는 우선순위 대기
**다음**: 09 팀장 §3 잔여 항목 우선순위 지시 / 04 §5 키워드 기반 회귀 검증
