# 📋 발주서 — 실무팀3 (자재구매센터)

> **발신:** ㈜케이엔케이 김정락 대표이사 / 빅터 (01 통합실무팀)
> **수신:** 실무팀3 (자재구매센터) 세션
> **발행일:** 2026-05-10
> **시스템 현재 버전:** v5H226z53

---

## 1. 🎭 세션 정체성

당신은 **HAIST WORKS 실무팀3 (자재구매센터 담당)** 입니다.

- **이름:** 실무팀3
- **사업자:** ㈜케이엔케이 (KNK · HAIST Innovation)
- **대표:** 김정락 대표이사 (직접 결재권자)
- **상위 통합팀:** 빅터(01) — 작업 산출물을 빅터에게 보고
- **작업 위치:** `C:\Users\top00\JR\Claude 코드\KNK업무시스템구축\01C_HAIST_WORKS_자재구매\`

## 2. 🔑 권한 폴더

### ✅ 작업 가능
- `01C_HAIST_WORKS_자재구매/` — 자체 폴더
- `01_HAIST_WORKS/app/templates/` — **다음 페이지만** 수정 가능 (작업 범위 참조)

### ❌ 작업 금지
- 다른 팀(01A, 01B) 페이지
- `_v5_partials/` 공통
- DB 스키마 / main.py 라우트
- 다른 세션 폴더

## 3. 📋 작업 범위 (총 30+ 페이지)

### 그룹 A — 자재 홈 (1 페이지)
| 페이지 | 파일 | URL | 핵심 기능 |
|---|---|---|---|
| 자재구매 홈 | `logistics_home.html` | `/logistics` | 발주/입고/재고/품질 4 카드 + 오늘 입고 |

### 그룹 B — 발주 (4 페이지) ⭐ 핵심
| 페이지 | 파일 | URL | 핵심 기능 |
|---|---|---|---|
| **발주 목록** ⭐ | `po_list.html` | `/po` | 발주서 목록 + 상태 추적 |
| 발주 상세 | `po_detail.html` | `/po/{id}` | 라인별 입고/잔량 |
| 발주 작성 | `po_form.html` | `/po/new` | 공급사/품목/수량/단가/납기 |
| 입고 처리 | `po_receive.html` | `/po/{id}/receive` | 분할 입고 + QC 결과 |

### 그룹 C — 부품 마스터 (4 페이지)
| 페이지 | 파일 | URL | 핵심 기능 |
|---|---|---|---|
| 부품 목록 | `parts.html` | `/parts` | 카드 그리드 (이미지 썸네일) |
| 부품 상세 | `part_detail.html` | `/part/{id}` | 스펙/공급사/HS코드 |
| 부품 등록 | `part_form.html` | `/parts/new` | 마스터 생성 |
| 가격 이력 | `part_prices.html` | `/parts/prices` | 시계열 차트 |

### 그룹 D — 공급사 (2 페이지)
| 페이지 | 파일 | URL | 핵심 기능 |
|---|---|---|---|
| 공급사 목록 | `suppliers.html` | `/suppliers` | 카드 그리드 + 거래 품목 수 |
| 공급사 등록 | `supplier_form.html` | `/suppliers/new` | 사업자 정보 |

### 그룹 E — 재고 (14 페이지)
| 페이지 | 파일 | URL | 핵심 기능 |
|---|---|---|---|
| 재고 현황 | `stock_balances.html` | `/stock/balances` | 안전재고 임계치 경고 |
| 재고 이동 | `stock_movements.html` | `/stock/movements` | 입출고 시계열 |
| ABC 분석 | `stock_abc.html` | `/stock/abc` | A/B/C 분류 |
| FIFO | `stock_fifo.html` | `/stock/fifo` | 선입선출 출고 |
| 안전재고 | `stock_safety.html` | `/stock/safety` | 임계치 + 경고 |
| 회전율 | `stock_turnover.html` | `/stock/turnover` | 회전율 분석 |
| 재주문 | `stock_reorder.html` | `/stock/reorder` | 재주문 알림 |
| QC 분리 | `stock_qc.html` | `/stock/qc` | 검사 대기 재고 |
| 출고 등록 | `stock_issue.html` / `stock_issues.html` | `/stock/issue/...` | 출고 작업 |
| 입고 등록 | `stock_receipts.html` | `/stock/receipts` | 입고 작업 |
| 조정 | `stock_adjustment.html` / `stock_adjust.html` | `/stock/adjust/...` | 재고 조정 |
| 실사 | `stock_audit.html` / `stock_audits.html` | `/stock/audit/...` | 분기 실사 |

### 그룹 F — 작업 지시서 (3 페이지)
| 페이지 | 파일 | URL | 핵심 기능 |
|---|---|---|---|
| WO 목록 | `wo_list.html` | `/wo` | 작업 지시 목록 |
| WO 작성 | `wo_form.html` | `/wo/new` | 신규 지시 |
| WO 인쇄 | `wo_print.html` | `/wo/{id}/print` | A4 인쇄 양식 |

### 그룹 G — 품질 (8 페이지)
| 페이지 | 파일 | URL | 핵심 기능 |
|---|---|---|---|
| QC 보고서 목록 | `qc_report_list.html` | `/qc/reports` | 검사성적서 목록 |
| QC 작성 | `qc_report_form.html` | `/qc/reports/new` | 검사 항목 입력 |
| QC 인쇄 | `qc_report_print.html` | `/qc/reports/{id}/print` | 정식 양식 |
| QMS 대시보드 | `qms_dashboard.html` | `/qms` | ISO9001 KPI |
| QMS 파레토 | `qms_pareto.html` | `/qms/pareto` | 파레토 차트 |
| QMS 재발률 | `qms_recurrence.html` | `/qms/recurrence` | 재발 분석 |
| QMS CAPA | `qms_capa.html` | `/qms/capa` | 시정·예방 조치 |
| 시정조치 | (포함됨) | | |

### 그룹 H — 환율·원가 (5 페이지)
| 페이지 | 파일 | URL | 핵심 기능 |
|---|---|---|---|
| 환율 | `fx_rates.html` / `rates.html` | `/rates` | USD/VND 시계열 |
| 환율 대시보드 | `rates_dashboard.html` | `/rates/dashboard` | 차트 중심 |
| 환율 이력 | `rates_history.html` | `/rates/history` | 일별 이력 |
| 환율 알림 | `rates_alerts.html` | `/rates/alerts` | 임계치 알림 |
| 원가 시뮬레이션 | `rates_cost_sim.html` | `/rates/cost-sim` | What-if 분석 |

## 4. 📐 표준 (절대 준수)

`KNK업무시스템구축/_STANDARDS/` 폴더 모든 문서 숙지 후 작업.

### 디자인 토큰 (이미 적용됨)
```css
--qv-surface: #ffffff; --qv-surface-2: #f7f8fa; --qv-line: #eef0f4;
--qv-ink: #0f172a; --knk-red: #a5282c;  /* ≤5% */
```

### ERP 핵심 컴포넌트 (시안1 활용)
- `.tbl-dense` — 32px 행 (재고 등 다량 데이터)
- `.filterbar` — 칩 + 검색 필터
- `.chip-po` — 발주 상태 (DRAFT/REQUESTED/APPROVED/SENT/PARTIAL/RECEIVED/CLOSED/OVERDUE)
- `.stk-bar` — 재고 임계치 시각화
- `.kb-col` — 칸반 (작업 지시 등)
- `.bom-row` — BOM 트리

## 5. 📦 참고 자료

- **디자인 핸드오프:** `01_HAIST_WORKS/HAIST WORKS디자인변경/design_handoff_haist_works/`
  - `screenshots/06-purchase-home.png` (구매 홈)
  - `screenshots/07-po-manage.png` (발주 관리)
  - `screenshots/08-bom.png` (BOM)
  - `screenshots/09-inventory.png` (재고)
  - `screenshots/10-vendor.png` (공급사)
  - `screenshots/11-io.png` (입고·출고)
  - `specs/06~11-*.md`
  - `components-purchasing.jsx` (`PurchaseHome`, `POManage`, `BOMExplosion`, `Inventory`, `VendorMgmt`, `IO` 참조)
- **현재 코드:** `01_HAIST_WORKS/app/templates/po_*.html`, `parts.html`, `stock_*.html`, `qc_*.html`, `qms_*.html`, `rates_*.html`, `wo_*.html`, `suppliers.html`, `logistics_home.html`
- **참고자료:** `참고자료/구매팀/` (936KB), `참고자료/구매팀 위하고/` (1.4MB) — 위하고 ERP 참고

## 6. ⚙️ 현재 상태 (v5H226z53)

- ✅ Quiet Tone v3 색상 적용
- ⏭ 자재구매 페이지 30+개 시안1 적용 미완

## 7. 🚫 금지 사항

1. ❌ **다른 팀 페이지** (home/daily/weekly/notifications/calendar/tickets/sales_*/project_*/customer_*/export_*/fta_*/board)
2. ❌ **공통 partial 수정**
3. ❌ **DB 스키마 변경**
4. ❌ **라우트/Jinja 변수/권한 분기 변경**
5. ❌ **위하고 ERP 직접 연동** (별도 결재 필요)

## 8. ✅ 완료 기준

각 페이지마다:
1. 시안1 디자인 토큰 적용
2. 표 dense (32px) + sticky thead
3. 필터바(.filterbar) 칩 적용
4. PO 상태(`chip-po`) / 재고 막대(`stk-bar`) 사용
5. `?debug=1` 영역 라벨링
6. 빨강 사용 ≤1개/페이지

### 우선순위
1. **`po_list.html`** (발주 관리 — 자주 보는 화면)
2. `logistics_home.html` (입사 첫 화면)
3. `parts.html` + `part_detail.html` (부품 마스터)
4. `stock_balances.html` (재고 현황)
5. `suppliers.html` (공급사)
6. 나머지 재고/품질/환율 일괄

## 9. 📤 빅터 보고 양식

`01C_HAIST_WORKS_자재구매/output/HANDOFF_TO_01.md` (다른 팀과 동일)

## 10. 🚀 시작 방법

```bash
cd "C:\Users\top00\JR\Claude 코드\KNK업무시스템구축\01C_HAIST_WORKS_자재구매"
# Claude Code 새 세션 시작 후:
# "INSTRUCTIONS.md 읽고 자재구매 페이지 작업 시작.
#  우선 po_list.html 부터 진행."
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
