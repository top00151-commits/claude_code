# Handoff: HAIST WORKS — 통합 ERP 운영 화면 (시안1 기반)

## Overview
KNK(한국정밀공업) 사내 ERP "HAIST WORKS"의 운영 화면 디자인입니다. **Quiet Ops** 미감 — 차가운 흰색 표면 / 진한 잉크 텍스트 / 단일 KNK Red 액센트(≤5%) / 벤토 그리드(페이지 스크롤 0) — 위에 ERP 다운 정보 밀도(다중 필터바, sticky 컬럼, 합계행, 인라인 데이터 시각)를 얹은 형태입니다.

본 패키지는 **시안1을 기준 디자인**으로 채택하여, 사용자가 요청한 3개 모듈을 모두 같은 시스템으로 발행한 결과물을 담고 있습니다:

1. **공통/기본 (업무 진행 · 일일 업무 · 캘린더 · 결재함)**
2. **영업·매출 (매출 홈 · 수주 · 프로젝트 상세 · 견적 · 고객사 · 미수금 · 출하)**
3. **구매·자재 (구매 홈 · 발주 · BOM·소요량 · 현재고/안전재고 · 입출고 · 공급사)**

> 시안 2/3/4는 디자인 방향성 비교용 대안이며, 본 핸드오프는 **시안1만** 포함합니다.

## About the Design Files
이 폴더의 파일들은 **HTML로 만든 디자인 레퍼런스(프로토타입)** 입니다. 그대로 복붙해 배포하는 코드가 아니라, **타겟 코드베이스의 기존 환경(React/Vue/Django 템플릿/Jinja 등)** 에 맞게 **재구현**하기 위한 시각·구조 명세입니다.

- 코드베이스가 이미 정해져 있다면(예: Django + Jinja + Vue island, Next.js, Spring + Thymeleaf 등) 그 안의 기존 컴포넌트·레이아웃 컨벤션을 우선합니다.
- 환경이 없다면, 본 디자인의 정보 밀도(테이블/필터/벤토)와 친화적인 React + CSS Variables(또는 Tailwind + CSS vars) 조합을 권장합니다.

## Fidelity
**High-fidelity (hifi)** — 픽셀, 색상, 타이포, 간격, 인터랙션 톤이 모두 확정된 수준입니다. 토큰(`assets/시안1-tokens.css`)에 정의된 값을 그대로 코드베이스의 디자인 토큰으로 옮겨 사용하세요.

## File Map (이 폴더 안)
- `HAIST WORKS · 시안1.html` — 진입점. React + Babel(브라우저 컴파일)로 마운트.
- `design-canvas.jsx` — 디자인 캔버스(아트보드 그리드). **구현에는 불필요**, 디자인 미리보기 전용.
- `assets/시안1-tokens.css` — **핵심**. 모든 색/간격/타이포/그림자/컴포넌트 클래스 정의. 그대로 토큰으로 채택.
- `components/시안1-mockups.jsx` — 공통(TopBar/Sidebar/PageHead/Sparkline/Bar/Trend/Mgmt/Chip 등) + 영업·매출 5페이지 + 토큰/컴포넌트 갤러리.
- `components/시안1-po-mockups.jsx` — 구매·자재 6페이지.

> 가장 먼저 읽어야 할 파일: `assets/시안1-tokens.css`(시스템) → `시안1-mockups.jsx`(공통 + 영업) → `시안1-po-mockups.jsx`(구매).

## Design Tokens

### Color — Surface
| 토큰 | Hex | 용도 |
|---|---|---|
| `--surface` | `#ffffff` | 카드 기본 |
| `--surface-2` | `#f7f8fa` | 앱 배경 |
| `--surface-3` | `#eef0f4` | 구분/탭 배경 |
| `--surface-inset` | `#fafbfc` | 조용한 강조(zebra) |

### Color — Ink (텍스트)
| 토큰 | Hex | 용도 |
|---|---|---|
| `--ink` | `#0f172a` | 본문 (16.7:1 AAA) |
| `--ink-2` | `#334155` | 보조 |
| `--ink-3` | `#64748b` | 메타 |
| `--ink-4` | `#94a3b8` | 비활성 |

### Color — Lines
`--line:#eef0f4` / `--line-2:#e2e8f0` / `--line-3:#cbd5e1`

### Color — KNK Brand Accent
`--knk-red:#a5282c` / `--knk-red-hover:#8b1f23` / `--knk-red-soft:#fef2f2` / `--knk-red-line:#fecaca`
> **규칙: 빨강은 화면 픽셀의 ≤5%만**. 주 CTA, 마감 임박, 오늘 표시 한정.

### Color — Status (semantic)
| 토큰 | Hex | Soft |
|---|---|---|
| `--ok` | `#0d7c4f` | `#ecfdf5` |
| `--info` | `#1e5fbf` | `#eff6ff` |
| `--warn` | `#b45309` | `#fef3c7` |
| `--danger` | `#b91c1c` | `#fef2f2` |

### Color — Business Unit (사업부)
| 코드 | 사업부 | Hex | Soft |
|---|---|---|---|
| T | 정밀 | `#c2410c` | `#fff7ed` |
| M | 가공 | `#1e40af` | `#eff6ff` |
| E | 전기 | `#6d28d9` | `#f5f3ff` |
| C | 화학 | `#047857` | `#ecfdf5` |

### Spacing (8pt + finer)
`4 / 8 / 12 / 16 / 20 / 24 / 32 / 40 / 48` (— `--space-1`..`--space-9`)

### Radius
`6 / 10 / 14 / 20 / 999` (— `sm/md/lg/xl/pill`)

### Shadow
- `--shadow-1` 카드 기본 (1px 2px + 1px 3px @ rgba(15,23,42,.04~.06))
- `--shadow-2` 호버
- `--shadow-3` 모달
- `--shadow-knk` 빨강 CTA 전용

### Typography
- Sans: `Pretendard Variable` → fallback `Pretendard, Segoe UI, Malgun Gothic, system-ui`
- Mono: `ui-monospace, JetBrains Mono, SF Mono, Consolas`
- Scale: `xs:12 / sm:13 / base:14 / md:15 / lg:17 / xl:20 / 2xl:24 / 3xl:30 / display:40`
- 본문 `14px / line-height 1.55` / `font-feature-settings: 'ss01','cv11'`
- 숫자(`.num`)는 mono + `font-variant-numeric: tabular-nums` + `letter-spacing: -0.01em` 필수
- 큰 KPI 숫자는 **letter-spacing: -0.03em**, 페이지 제목은 **-0.02em**

### Layout 상수
- `--topbar-h: 56px` / `--sidebar-w: 220px` / `--page-head-h: 60px` / `--page-pad: 24px`
- 아트보드 표준 캔버스: **1440 × 900** (페이지 스크롤 X. 영역별 내부 스크롤만)

## Common Components (스펙 핵심)

### `.chrome` (페이지 셸)
```
grid-template-columns: var(--sidebar-w) 1fr;
grid-template-rows: var(--topbar-h) 1fr;
height: 100vh; overflow: hidden;
```
3 영역: TopBar(상단 풀폭) / Sidebar(좌) / Main(우).

### TopBar
- 56px, `border-bottom:1px solid var(--line)`
- 좌: 24×24 잉크 사각형 로고("K") + "HAIST WORKS" + 버전 라벨
- 중: 5개 메인 nav 텍스트 링크 (active = 잉크 배경 + 흰 글씨)
- 우: 검색(240w 34h, 좌측 ⌕ 아이콘) · 알림 아이콘 버튼 · 사용자 칩(아바타 24원 + 이름)

### Sidebar
- 220px, `var(--surface)`, `border-right`
- 그룹 라벨(11px upper-case `--ink-4`) + 아이템(이모지 18 + 라벨 + 우측 카운트 배지)
- 활성 아이템: 잉크 배경 / 흰 글씨 / 배지는 반투명 흰색
- **메뉴 트리** (실제 채택할 IA):
  - 영업 — 매출 홈 · 수주 관리 · 견적 관리 · 고객사 · 미수금
  - 생산 — 프로젝트 · 생산 현황 · 납품·수금
  - **구매·자재** — 구매 홈 · 발주 관리 · BOM·소요량 · 현재고 · 안전재고 · 입출고 · 공급사
  - 공통 — 일일 업무 · 캘린더 · 결재함 · 티켓

### PageHead (60px)
크럼 11px → 제목 24px(700, -0.01em) — 옆에 관리번호 알약 → meta(왼쪽 보더로 분리) → 우측 actions(seg + 보조 btn + primary btn).

### Buttons
- `.btn` 기본: 36h, 14 padding, `--line-2` 보더, radius 10, 13px 500
- `.btn-primary` = KNK Red + 흰글씨 + `--shadow-knk`
- `.btn-dark` = 잉크 배경 + 흰글씨
- `.btn-ghost` = 무배경, hover 시 `--surface-2`
- `.btn-sm`(30h/12fs) / `.btn-lg`(44h/15fs) / `.btn-icon`(36×36 정사각)

### Mgmt-no (관리번호 알약)
잉크 배경 + 흰 mono. `YY-{T|M|E|C}-####` (견적은 `Q` 접두). 3 size: sm 20h / 기본 24h / lg 30h.

### Chips
- `.chip` 기본 회색
- `.chip-biz` — 좌측 8×8 컬러닷 + 사업부 라벨(`biz-t/m/e/c`)
- `.chip-status` — neutral 회색이 기본, **임팩트 있는 상태만 채색**
  - draft / cancelled / invoiced = 회색 톤
  - confirmed / shipped = info 파랑 톤
  - in-production = warn 호박 톤
  - paid = ok 초록 톤

### KPI 카드
- `box-shadow:--shadow-1`, radius 14, padding 20, min-h 120
- 라벨(11~12px `--ink-3`) → **숫자(mono, 40px, 700, -0.03em)** + 단위(15px `--ink-3`) → 트렌드(`up/down/flat` 화살표 + 색)
- 우측 하단에 32×80 스파크라인(opacity 0.6)
- 강조 KPI는 잉크 배경 + 흰 숫자(`--ink` BG)

### Sparkline (인라인 SVG)
- viewBox `0 0 80 32`, area fill 0.08, stroke 1.5, 끝점 dot r=2.5
- 색은 의미 매핑: 매출=잉크 / 수주=info / 미수금=ok

### Bar (진척바)
- 6px 높이, radius 999, BG `--surface-3`
- 채움 색: 기본 잉크 / `is-ok` 초록 / `is-warn` 호박 / `is-danger` 빨강 / `is-info` 파랑

### Tables
- 행 48px / 컴팩트 36px / dense 32px
- thead: sticky top, BG surface, 11px upper-case `--ink-3` 0.04em letter-spacing
- 첫 컬럼(체크박스 32w)·관리번호·품명까지 **sticky-left** 가능 (PARTS 28-col 케이스)
- `tbl-zebra`: 짝수 행 `--surface-inset`
- 숫자 셀은 `.num` (우측 정렬, mono, tabular-nums)
- **합계행** (`tfoot`): 잉크 텍스트 / 굵게 / `border-top: 2px solid var(--line-2)`

### Filter Bar (ERP 다중 필터)
- 카드 위 24h 12px sub-bar
- 6~8개 select/검색/날짜레인지 필터 가로 나열
- 우측: "필터 저장 / 초기화" 텍스트 버튼
- 활성 필터는 칩으로 한 줄 더 (제거 X 가능)

### Segmented control (`.seg`)
- BG `--surface-3`, 3px inset padding
- 활성: 흰 BG + `--shadow-1` + ink 색

### Forms
- input/select/textarea 40h, 12 padding, radius 10
- focus: `border-color: var(--ink)` + `box-shadow: 0 0 0 3px rgba(15,23,42,0.08)`

## Screens

### 그룹 A — 공통/기본 (4개 화면)

#### A1. 일일 업무 (DailyWork)
- **목적**: 오늘 해야 할 일 + 시간표 + 빠른 KPI
- **레이아웃**: 3열 12-grid + 2행
  - row1 (full): KPI 5장 (오늘/완료/지연/회의/결재대기) — 각 셀 패딩 18×20, 32px mono 숫자
  - row2 col1-2: 업무 리스트 카드 (필터 seg + 체크박스 행)
  - row2 col3: 오늘의 시간표 카드 (09:00~17:30 시간 슬롯, 좌 보더 색상으로 상태 표시)
- 지연 항목은 `--knk-red-soft` 배경 + 좌 보더, "⚠ 지연" 라벨
- 완료 항목은 opacity 0.55 + line-through

#### A2. 캘린더 (CalendarPage)
- **레이아웃**: 좌 260 사이드 + 우 1fr 큰 캘린더
- 좌: 미니 캘린더(35칸 grid 4px) → 분류 체크박스(개인/T/M/E/C/결재/휴일) → 이번 달 요약(전체/완료/진행/지연)
- 우: 7×5 풀 월간 그리드, 셀당 최대 3 이벤트, 4번째부터 `+N` 카운트
  - 이벤트 칩: 좌 2px 보더 + soft BG / 강조는 fill BG + 흰 글씨

#### A3. 결재함 (Approvals — 추가 IA)
> 디자인 캔버스에는 미수록. 구현 시 다음 톤으로:
> 좌측 트리(상신/수신/대기/완료) + 우측 표 + 상세 패널(우 380w drawer). 상태 chip 4종. 결재 라인(승인자 아바타 chip 가로 → 화살표).

#### A4. 티켓·주요사항 (Issues — 추가 IA)
> 칸반 4열(접수/진행/대기/완료) 또는 표 모드 토글. 우선순위 chip(긴급/높음/보통/낮음). 담당자 아바타 stack.

### 그룹 B — 영업·매출 (5개 화면 + 확장)

#### B1. 매출 홈 (SalesHome)
- 12-grid 4행 벤토
- KPI 4: 이번 달 매출(62.4억, 잉크 스파크) / 신규 수주(35건, info 스파크) / 미수금(6.9/84.2억, ok 스파크) / **목표 달성률 78% — 잉크 배경 강조 카드** + 흰 progress bar
- 사업부별 매출(좌) + 도넛(우, 220×220, 4 segment, 중앙 "총 매출 62.4 억")
- 일별 매출 14일 막대 (오늘만 KNK Red, 나머지 잉크 opacity 0.2~0.86 그라디언트)
- 진행 중인 프로젝트 표 5행 (관리번호/사업부/프로젝트/거래처/상태/진척바/금액)
- 곧 도래 일정 패널 (D-day 색상 강조)

#### B2. 수주 관리 (OrdersPage)
- 좌 1fr 캘린더 + 우 360w 선택일 패널
- 캘린더: 사업부별 색 범례 헤더 → 7×5 그리드, 셀당 2 이벤트
- 우 패널: 선택일 4건 카드 (사업부 chip + 시간 + 제목 + 관리번호 + 금액 + 상태)

#### B3. 프로젝트 상세 (ProjectDetail) — **PARTS 28-column**
- 페이지 헤드 + 6 KPI strip (24px mono 숫자) + 세그 탭 + 컬럼 그룹 토글 + 표 + 페이지네이션
- 컬럼 그룹: 기본(6) / 재질(4) / 공정(4) / 납기(4) / 원가(4) — 토글 시 보이는 컬럼만 교체
- 첫 3컬럼(체크/품번/품명) sticky-left
- 행 hover, zebra, sticky thead

#### B4. 견적 관리 (Quotes — 확장)
> 표 모드 + 칸반 모드 토글. 견적 단계 칩 5종(작성중/송부/회신대기/승인/거절). 만료 D-day 색상 경고.

#### B5. 고객사 (Customers — 확장)
> 좌측 거래처 표 + 우측 360w 상세(연락처/누적매출 KPI 3장/최근 프로젝트 5/최근 미수 표).

#### B6. 미수금 (Receivables — 확장)
> KPI 3(총 미수/연체/평균 회수일) + 연체 일수 버킷 막대(0-30/31-60/61-90/90+) + 표(거래처/관리번호/금액/연체일/마지막 연락).

#### B7. 출하·납품 (Shipments — 확장)
> 표 + 우측 일정 stack. 송장 번호 mono. 상태(출하예정/출하/도착/완료).

### 그룹 C — 구매·자재 (6개 화면)

`components/시안1-po-mockups.jsx` 안에 모두 구현됨.

#### C1. 구매 홈 (PurchaseHome)
- KPI 4 (이번 달 발주액 / 미입고 PO / 자재 부족 / 입고 임박)
- 발주 흐름 칸반(요청→승인→발주→입고대기→입고완료) 카운트 칩
- 입고 임박 7일 리스트
- 카테고리별 발주액 도넛 + 사업부별 발주 막대

#### C2. 발주 관리 (PurchaseOrders)
- 6필터 바 (기간/상태/공급사/사업부/검색)
- 큰 표: PO번호(Mgmt) / 발주일 / 공급사 / 품목수 / 금액 / 입고예정 / 진척바 / 상태
- 합계행 tfoot
- 우측 380 detail drawer (선택 PO 상세 — 공급사/품목 라인/입고이력)

#### C3. BOM·소요량 (BomExplosion)
- 좌측 250 프로젝트 picker (검색 + 트리)
- 우측: 상단 KPI(BOM 깊이 / 자재 종 / 총 소요량 / 외주 공정)
- 메인: 들여쓰기 + 가이드선 BOM 트리 (3 level), 행마다 [품번 / 품명 / 단위소요 × 발주수량 = 총소요 / 재고 / 부족 / 액션]
- 부족 행은 KNK Red soft + ⚠
- 우 360 자재 카탈로그 검색 patch

#### C4. 현재고 / 안전재고 (Stock)
- KPI 5 (총 SKU / 안전재고 미달 / 과잉재고 / 입고 대기 / 출고 대기)
- 창고 탭 (본사/A창고/B창고/외주)
- 표: 자재코드 / 명 / 카테고리 / 단위 / **현재고 ↔ 안전재고 시각화 막대** (현재가 안전 미만이면 빨강) / 입고예정 / 출고예정 / 액션
- 안전재고 미달 행 sticky 상단 옵션

#### C5. 입출고 (InOut)
- 좌측 폼(입고 등록 / 출고 등록 토글) + 우측 최근 이력 표
- 입고 폼: PO 선택 → 라인 자동 채움 → 검수 결과(양품/불량) → 저장
- 이력 표 행 56h: 일시 / 종류칩 / 자재 / 수량 / 담당 / 비고

#### C6. 공급사 (Vendors)
- 표 + 우측 360 상세
- 표: 공급사명 / 카테고리 / 누적 발주액 / 평균 리드타임 / 불량률 / 평가(★) / 마지막 거래일
- 상세: 연락처 / 거래조건 / 최근 PO 5 / 평가 그래프

## Interactions & Behavior
- **페이지 스크롤 0**: `body, .chrome { overflow: hidden }` — 데이터는 카드/표 내부 스크롤로
- **숫자 카운트업**(선택): KPI 진입 시 0→값 (300ms ease-out, 한 번만)
- **표 행 hover**: `background: var(--surface-2)` (transition .1s)
- **버튼 hover**: 보더 색만 한 단계 진하게 + BG `--surface-2`. transition .12s ease.
- **focus-visible**: `outline: 2px solid var(--knk-red); outline-offset: 2px`
- **세그 컨트롤**: 활성 변경 시 `--shadow-1` 부드럽게 등장
- **drawer**: 우측 360w slide-in (`transform: translateX(0)`, 200ms ease-out)
- **filter 적용**: 즉시 표 갱신 (debounce 150ms로 검색 input)
- **키보드**: 표 ↑↓ 행 이동, Enter 상세 drawer, Esc 닫기

## State (재구성 시 필요한 도메인 모델 힌트)
- `Project { mgmtNo, biz, name, customer, status, progressPct, amount, … }`
- `Order` (수주) / `Quote` (견적) / `Invoice` / `Receivable`
- `PO { poNo, vendor, lines[ItemLine], status:[req|approved|placed|partial|received], expectedDate }`
- `BomNode { itemCode, name, qty, depth, children[] }`
- `Stock { itemCode, warehouse, qty, safetyQty, incoming, outgoing }`
- `Vendor { id, name, category, leadTimeAvg, defectRate, rating }`
- 상태 chip 매핑은 위 토큰 표 참조

## Assets
- `assets/KNK로고.png` / `assets/knk-logo.png` — KNK 로고 (이미 디자인 안에는 SVG 1×1 잉크 사각형 + "K" 텍스트로 대체됨; 실제 코드에서는 PNG 사용 가능)
- 아이콘은 디자인에서 **이모지**로 임시 대체. 실 구현 시 코드베이스의 아이콘 셋(예: lucide, phosphor, material-symbols)으로 1:1 치환:
  - 📊 → bar-chart / 📑 → file-text / 📝 → edit-3 / 🏢 → building-2 / 💰 → dollar-sign / 📦 → package / 🛠 → wrench / 🚚 → truck / ✅ → check-square / 📅 → calendar / 📨 → inbox / 🔔 → bell / ⌕ → search / ⤓ → download / ＋ → plus

## Implementation Notes (코드베이스에 반영할 때)
1. **`assets/시안1-tokens.css` 를 그대로 가져가** 글로벌 스타일에 import. 클래스 명명이 충돌하면 prefix(`hw-`) 1회로 일괄 변경.
2. 컴포넌트는 **TopBar / Sidebar / PageHead / Card / KPI / Mgmt / Chip(Biz/Status) / Bar / Sparkline / Seg / Tbl** 11종을 **공통**으로 분리.
3. 화면(Screens)은 위 12종 컴포넌트 조합. JSX는 디자인 파일이 그대로 합리적인 출발점.
4. 데이터는 더미 인라인 → API 연결로 점진 교체. 표는 row virtualization 권장(>200 rows 케이스).
5. **반응형은 데스크톱 우선** — 본 운영툴은 1280+ 기준. 1024 이하는 사이드바 collapse(아이콘만 56w)로 축소.
6. 다크모드는 v2에서. 토큰 구조는 이미 호환 (surface/ink 토큰만 swap).
7. KNK Red 사용 룰을 컴포넌트 레벨에서 강제: `<Button variant="primary">` 1개 / `Today badge` / `urgent` flag 한정.

## Files in this bundle
```
design_handoff_haist_works/
├─ README.md                                    ← 이 문서
├─ HAIST WORKS · 시안1.html                      ← 진입 HTML (브라우저로 열어 확인)
├─ design-canvas.jsx                            ← 디자인 미리보기 셸 (구현 불필요)
├─ assets/
│   └─ 시안1-tokens.css                          ← ★ 토큰/컴포넌트 CSS (그대로 채택)
└─ components/
    ├─ 시안1-mockups.jsx                         ← 공통 + 영업·매출 5p + 토큰 갤러리
    └─ 시안1-po-mockups.jsx                      ← 구매·자재 6p
```

## How to use with Claude Code
1. 위 ZIP을 받아 작업 레포 루트 옆에 펼친다.
2. Claude Code 세션에 다음을 붙여 시작:
   ```
   `design_handoff_haist_works/README.md` 를 먼저 읽고,
   `assets/시안1-tokens.css` 의 토큰을 우리 코드베이스의 글로벌 스타일에 통합해줘.
   그 다음 `components/시안1-mockups.jsx` 의 TopBar / Sidebar / PageHead / KPI / Mgmt / Chip / Bar / Sparkline / Seg / Tbl 을
   우리 코드베이스의 컴포넌트 컨벤션으로 추출해 공통 디렉토리에 만들어줘.
   화면은 README의 "Screens" 순서대로 1개씩 PR 단위로 진행한다.
   ```
3. 한 번에 한 화면씩(작은 PR) 옮기는 것을 권장. SalesHome → ProjectDetail → PurchaseOrders 순이 효과적.
