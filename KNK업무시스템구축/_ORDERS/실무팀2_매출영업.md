# 📋 발주서 — 실무팀2 (매출영업센터)

> **발신:** ㈜케이엔케이 김정락 대표이사 / 빅터 (01 통합실무팀)
> **수신:** 실무팀2 (매출영업센터) 세션
> **발행일:** 2026-05-10
> **시스템 현재 버전:** v5H226z53

---

## 1. 🎭 세션 정체성

당신은 **HAIST WORKS 실무팀2 (매출영업센터 담당)** 입니다.

- **이름:** 실무팀2
- **사업자:** ㈜케이엔케이 (KNK · HAIST Innovation)
- **대표:** 김정락 대표이사 (직접 결재권자)
- **상위 통합팀:** 빅터(01) — 작업 산출물을 빅터에게 보고
- **작업 위치:** `C:\Users\top00\JR\Claude 코드\KNK업무시스템구축\01B_HAIST_WORKS_매출영업\`

## 2. 🔑 권한 폴더

### ✅ 작업 가능
- `01B_HAIST_WORKS_매출영업/` — 자체 폴더
- `01_HAIST_WORKS/app/templates/` — **다음 페이지만** 수정 가능 (작업 범위 참조)

### ❌ 작업 금지
- 다른 팀(01A, 01C) 페이지
- `_v5_partials/` 공통
- DB 스키마 / main.py 라우트
- 다른 세션 폴더

## 3. 📋 작업 범위 (총 30+ 페이지)

### 그룹 A — 매출 홈 / 대시보드 (2 페이지)
| 페이지 | 파일 | URL | 핵심 기능 |
|---|---|---|---|
| 매출 홈 | `sales_home.html` | `/sales` | 6 KPI + 진행 프로젝트 + TOP 고객사 |
| 매출 대시보드 | `sales_dashboard.html` | `/sales/dashboard` | 차트 중심 분석 |
| 매출 예측 | `sales_forecast.html` | `/sales/forecast` | 시계열 예측 |
| 생산 현황 | `sales_production.html` | `/sales/production` | 생산 진행 |

### 그룹 B — 프로젝트 (4 페이지) ⭐ 핵심
| 페이지 | 파일 | URL | 핵심 기능 |
|---|---|---|---|
| 프로젝트 목록 | `projects.html` | `/projects` | 카드 그리드 + 검색·필터 |
| **프로젝트 상세** ⭐ | `project_detail.html` | `/project/{id}` | **가장 복잡 — 호기별 SO + PARTS 28컬럼** |
| 프로젝트 등록 | `project_form.html` | `/projects/new` | 4단 섹션 (기본/일정/금액/메모) |
| 종류 선택 | `project_new_chooser.html` | `/projects/new` (chooser) | T/M/E/C 4 카드 |

### 그룹 C — 고객사 (3 페이지)
| 페이지 | 파일 | URL | 핵심 기능 |
|---|---|---|---|
| 고객사 목록 | `customers_list.html` | `/customers` | 카드 그리드 + 검색 |
| 고객사 상세 | `customer_detail.html` | `/customer/{id}` | KPI 4 + 프로젝트 + 컨택 |
| 고객사 등록 | `customer_form.html` | `/customers/new` | 사업자 정보 + 컨택 |

### 그룹 D — 견적서 (4 페이지)
| 페이지 | 파일 | URL | 핵심 기능 |
|---|---|---|---|
| 견적 목록 | `sales_quotations.html` | `/sales/quotations` | 견적 진행률 표 |
| 견적 상세 | `sales_quote_detail.html` | `/sales/quote/{id}` | 라인 입력 + 합계 |
| 견적 작성 | `sales_quote_form.html` | `/sales/quote/new` | 정식 양식 |
| 견적 인쇄 | `quotation_print.html` | `/sales/quote/{id}/print` | A4 PDF 양식 |

### 그룹 E — 수주 (2 페이지) ⭐ 핵심
| 페이지 | 파일 | URL | 핵심 기능 |
|---|---|---|---|
| **수주 관리** ⭐ | `sales_orders.html` | `/sales/orders` | 캘린더 + 임박납기 + 관리번호 리스트 |
| 수주 상세 | `sales_order_detail.html` | `/sales/orders/{id}` | 호기별 인라인 편집 + 인보이스 |

### 그룹 F — 납품 / 수금 / 미수금 (3 페이지)
| 페이지 | 파일 | URL | 핵심 기능 |
|---|---|---|---|
| 납품·수금 | `sales_shipments_receipts.html` | `/sales/shipments-receipts` | 좌(납품 대기) | 우(수금 대기) |
| 미수금 | `sales_outstanding.html` | `/sales/outstanding` | Aging 차트 + 고객사별 |
| 미수금 분석 | `sales_aging.html` | `/sales/aging` | 30/60/90/120일 분석 |

### 그룹 G — 소모품 (3 페이지)
| 페이지 | 파일 | URL | 핵심 기능 |
|---|---|---|---|
| 소모품 목록 | `consumables.html` | `/consumables` | 발주 목록 |
| 소모품 상세 | `consumable_detail.html` | `/consumable/{id}` | 라인별 진행 |
| 소모품 등록 | `consumable_form_upload.html` | `/consumable/new` | 엑셀 업로드 + 이미지 |

### 그룹 H — 수출입 / 통관 (11 페이지)
| 페이지 | 파일 | URL |
|---|---|---|
| 수출입 홈 | `export_home.html` | `/export` |
| 수출 주문 | `export_order_form.html` / `export_order_detail.html` | `/export/orders/...` |
| Commercial Invoice | `export_ci.html` / `export_ci_print.html` | `/export/ci/...` |
| Packing List | `export_pl.html` / `export_pl_print.html` | `/export/pl/...` |
| B/L 통관 | `export_bl_customs.html` / `export_bl_print.html` | `/export/bl/...` |
| FTA 원산지 | `fta_list.html` / `fta_form.html` / `fta_print.html` | `/fta/...` |

## 4. 📐 표준 (절대 준수)

`KNK업무시스템구축/_STANDARDS/` 폴더 모든 문서 숙지 후 작업.

### 필수 참조
- `_STANDARDS/_TEAM_ORIENTATION.md`
- `_STANDARDS/디자인_의뢰서_HAIST_WORKS_v1.md`
- `_STANDARDS/_INDEX_코드구조.md`

### 디자인 토큰 (이미 적용됨)
```css
--qv-surface: #ffffff; --qv-surface-2: #f7f8fa; --qv-line: #eef0f4;
--qv-ink: #0f172a; --qv-ink-2: #334155; --qv-ink-3: #64748b;
--knk-red: #a5282c;  /* ≤5% */
--biz-t: #c2410c; --biz-m: #1e40af; --biz-e: #6d28d9; --biz-c: #047857;
```

### 핵심 UX 원칙 (대표 직접 지시)
1. **관리번호 우선** — 모든 표/카드/리스트에서 관리번호가 1열
2. **한 화면에 다 보이게** — 스크롤 최소화
3. **표 헤더 sticky** — 스크롤 시 컬럼명 안 움직임
4. **상태별 컬러** — 진행중/완료/취소/보류 한눈에

## 5. 📦 참고 자료

- **디자인 핸드오프:** `01_HAIST_WORKS/HAIST WORKS디자인변경/design_handoff_haist_works/`
  - `screenshots/02-orders.png` (수주 관리)
  - `screenshots/03-project.png` (프로젝트 상세 ⭐)
  - `screenshots/01-sales-home.png` (매출 홈)
  - `specs/02-orders.md`, `specs/03-project.md`, `specs/01-sales-home.md`
  - `components-base.jsx` (`OrdersPage`, `ProjectDetail`, `SalesHome` 참조)
- **현재 코드:** `01_HAIST_WORKS/app/templates/sales_*.html`, `project_*.html`, `customer_*.html`, `export_*.html`
- **PARTS 28컬럼 백엔드:** `01_HAIST_WORKS/app/main.py` 의 `_parse_packing_list_xlsx()` (수정 금지, 호출만)

## 6. ⚙️ 현재 상태 (v5H226z53)

- ✅ Quiet Tone v3 색상 적용
- ✅ 수주 관리(`sales_orders.html`) — B안 좌우분할, 관리번호 우선
- ✅ 프로젝트 상세 PARTS 28컬럼 + 컬럼 그룹 토글 + 가로 스크롤
- ⏭ 매출 홈(`sales_home.html`) — 시안1 12-col bento 미적용
- ⏭ 견적서/납품수금/미수금/수출입/FTA — 디자인 시스템 적용 미흡

## 7. 🚫 금지 사항

1. ❌ **다른 팀 페이지 수정** (home/daily/weekly/notifications/calendar/tickets/changes/issues/board/po_*/parts/stock/qc/rates/wo_*)
2. ❌ **공통 partial 수정**
3. ❌ **DB 스키마 변경**
4. ❌ **PARTS 28컬럼 백엔드 로직 변경** (display 만 개선)
5. ❌ **라우트/Jinja 변수/권한 분기 변경**

## 8. ✅ 완료 기준

각 페이지마다:
1. 시안1 디자인 토큰 적용
2. 관리번호 1열 + 잉크 알약 강조
3. 표 sticky thead + zebra
4. `?debug=1` 영역 라벨링
5. 1100px 이하 반응형
6. 빨강 사용 ≤1개/페이지

### 우선순위
1. **`project_detail.html`** (가장 복잡, 가장 사고 많음 — 우선 진행)
2. `sales_orders.html` (자주 보는 화면 — 이미 80% 진행됨)
3. `sales_home.html` (입사 첫 화면)
4. `sales_order_detail.html`, `customer_detail.html`
5. 견적/납품수금/미수금
6. 수출입/FTA

## 9. 📤 빅터 보고 양식

`01B_HAIST_WORKS_매출영업/output/HANDOFF_TO_01.md`

(실무팀1 발주서와 동일 양식 — 변경 파일/요약/위험/검증)

## 10. 🚀 시작 방법

```bash
cd "C:\Users\top00\JR\Claude 코드\KNK업무시스템구축\01B_HAIST_WORKS_매출영업"
# Claude Code 새 세션 시작 후:
# "INSTRUCTIONS.md 읽고 매출영업 페이지 작업 시작.
#  우선 project_detail.html 부터 진행."
```

---

**문의:** 빅터 (01) — `99_DISPATCH/` 채널 또는 `_ORDERS/` 발주서 v2 요청
**대표 결재:** 김정락 대표이사 직접 라인

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
