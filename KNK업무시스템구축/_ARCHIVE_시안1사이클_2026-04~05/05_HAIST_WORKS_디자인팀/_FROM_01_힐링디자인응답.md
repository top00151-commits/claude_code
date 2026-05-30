# 01 메인 → 05 디자인팀 — 힐링 디자인 전환 응답 #12 (1차)

> **수신**: 05 디자인팀
> **원본**: `_세션01_전달/_TO_01_대표승인_힐링디자인전환_최종.md` + `_TO_01_디자인제안_12_힐링테마전환.md`
> **기준**: `01_디자인원칙_힐링v1.md` Sage Garden B-2
> **대표 승인**: 2026-04-24 "12B_healing_sage_garden.html 이걸로 선택할께 · B-2 (CTA만 KNK 레드)"

## 착수 현황

- [x] **착수 시작** 2026-04-24 · 전체 9커밋 중 1-3 + 5 + 7 **1차 완료**
- [ ] 커밋 6·8·9 (로그인·progress·dashboard) **후속 예정**

---

## 1차 완료 커밋 (5건 · 2커밋으로 통합)

### 커밋 `f61f06c` — 힐링 토큰 + 헤더 + 사이드바 (§1~§3)

**style.css `:root` 전면 교체**:
- 세이지 스케일 9단 (`--sage-50 ~ --sage-800`)
- 본문 잉크 (`--ink, --ink-2, --ink-3, --ink-4`) · 순수 검정 금지 ✓
- `--accent` = KNK 레드 (CTA 전용, B-2 규칙)
- `--grad-sage` · `--grad-header` · `--grad-brand`
- 자연 톤 상태색 (ok:sage-500, warn:amber, err:knk-red, info:mint)
- 유동 타이포 7단계 유지
- 힐링 그림자 (세이지 톤 rgba)
- **호환 별칭 유지** (`--r, --t, --g, --bg, --bd`) — 점진 마이그레이션

**body 힐링 기본값**:
- background `#FAFAFA` → `sage-100`
- color `#1A1A1A` → `ink` (이끼색)
- line-height `1.6` → `1.7` + letter-spacing `0.1px`

**헤더 (`.topbar`)**:
- 다크 그레이 `#0F172A` → `grad-header` (세이지 포레스트)
- `::before`/`::after` radial blob 장식
- 아바타 흰 배경 + 세이지 글자
- CTA(logout)만 KNK 레드 유지 (B-2)
- 라운드 10 → 12~14px

**사이드바 (`.sidebar, .sb-item`)**:
- 배경 `#fff` → `sage-50`
- 테두리 `sage-200`
- **활성 메뉴 레드 그라디언트 → `grad-sage`** ← 핵심 전환
- 호버 배경 → `sage-200`
- 아이콘 stroke 2 → 1.7 (정제)
- 라운드 10 → 14px

**CSS 캐시 키**: `?v=20260424design-v4` → `?v=20260424healing-v1`

### 커밋 `72490a3` — 홈 권한 분기 + 빅터 도크 힐링 (§5·§8-bis)

**홈 매출 KPI 권한 분기 — 3중 방어 구현**:

① **UI 조건 분기** (home.html Jinja `{% if is_executive %}`)
② **컨텍스트 분기** (main.py `home_page` — 데이터 애초에 미전달)
③ **라우트 권한** (기존 `/dashboard` `require executive`)

**경영진 전용 매출 KPI 카드**:
- `monthly_revenue` — 이번 달 수주 (억/천만/원 자동 변환)
- `yoy_delta` — 전년 동월 대비 증감률
- 우상단 "🔒 경영진" 배지

**팀장+ 전용 "팀 지연 공정" KPI** (`is_leader_plus`)

**시간대별 인사말** (힐링 §7-1):
```
아침(6-11): "좋은 아침입니다, {name}님 ☀️"
점심(11-14): "점심은 드셨나요? 잠깐 쉬어가요"
오후(14-18): "오후도 힘내세요 🌿"
저녁(18-22): "오늘도 수고하셨어요"
심야(22-6): "늦은 시간까지 애쓰시네요"
```

**빅터 도크 세이지 스킨 (§5)**:
- `dock-head`: `grad-brand-deep` → `grad-sage`
- `dock-avatar`: 반투명 → 흰배경 + 세이지 글자
- online dot: 초록 pulse → 앰버 정적 (힐링)
- 사용자 말풍선: `grad-brand-warm` → `grad-sage` + `sh-green`
- AI 답변 타이틀: `knk-red` → `sage-700`
- AI 답변 border: `ink-200` → `sage-200`
- 말풍선 라운드 10 → 16px (힐링 부드러움)

---

## 검증 (CEO `kjr` 로그인)

```
/home /dashboard /sales /logistics /progress → 전부 200 ✓
CSS 힐링 토큰 로드 확인 (sage/grad/ink 20회) ✓
경영진 배지 2개 (매출 KPI + 팀 지연 KPI) ✓
이번 달 수주 KPI 노출 ✓
시간대별 인사말 동작 ("수고하셨어요" 18시+) ✓
빅터 도크 victorDock 렌더 ✓
admin 로그인도 매출 KPI 노출 (is_executive 통과) ✓
```

**평직원 분기 검증**: 브라우저 테스트 권장. `is_executive=False`, `monthly_revenue=None` 전달이 자동 되어 매출 KPI **섹션 자체가 렌더되지 않음** (3중 방어 ②).

---

## 후속 예정 (S1 게이트 이후 또는 별도 승인 시)

| 커밋 | 내용 | 시안 | ETA |
|------|------|------|-----|
| #6 | 로그인 세이지 스킨 (tonal reskin) | `13_login_healing.html` | 1h |
| #8 | /progress 매트릭스 UI | `14_progress_healing.html` | 1.5h |
| #9 | /dashboard SVG 차트 | `15_dashboard_healing.html` | 2h |
| #4 | _page_header_healing.html partial + 10 라우트 제목 | — | 2h |

**현재 `/login` 상태**: 제안 #07 브랜드 스플릿 기반 구현 완료. 토큰이 힐링으로 바뀌면서 `--grad-brand-deep` 등이 유지되어 (좌 패널 딥 레드 그라디언트) 힐링 톤 아님. → #6 에서 시안 13 기반 재스킨 필요.

## 상위 정책 준수 확인

- [x] 외부 자산 0건 (Lucide 기존 · 신규 없음)
- [x] 언어 옵션 ko / vi / en 유지 (중국어 추가 없음)
- [x] 매출 KPI 권한 분기 3중 방어 (대표 직접 지적 대응)
- [x] KNK 브랜드 레드 = CTA 전용 (활성 메뉴 세이지)
- [x] 라우팅·데이터 구조 변경 0건

## 알려진 제한

1. **로그인 페이지** — 현재 딥 레드 그라디언트 (제안 #07 기반). #6 에서 세이지 시안 13 교체 예정.
2. **`/progress`·`/dashboard`** — 기존 UI 힐링 톤만 자동 적용 (토큰 연결). 본격 시안 14·15 매트릭스·SVG 차트는 #8·#9 에서.
3. **페이지 헤더 마이크로카피** — 주요 10 라우트 제목 교체는 #4 에서. 현재 `/home` 만 `greeting` 적용.
4. **드래그 리사이즈 제거 (#09 계승)** — 사이드바 `.sb-resize` JS 는 아직 활성. #3 에서 CSS 우선 적용, JS 정리는 후속.

## 회신 요청 (05 → 01)

- [ ] 1차 결과 브라우저 확인 후 시각 피드백
- [ ] `#4·#6·#8·#9` 우선순위 조정 필요 시 05 권고
- [ ] 평직원 계정 매출 미노출 QA 결과 공유 필요

---
**01 메인 세션** · 2026-04-24
**커밋**: `f61f06c` + `72490a3`
