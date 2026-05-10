# 📋 실무팀2 → 빅터(01) 핸드오프 v7 — sales_orders.html v1 차수

> **발신**: 실무팀2 (매출영업센터)
> **수신**: 빅터 (01 통합실무팀)
> **결재**: 김정락 대표이사 — 2026-05-10 "(β) 권장안으로 진행" (sales_orders.html 우선)
> **작성일**: 2026-05-10
> **버전**: v5H226z43 → **v5H226z44**
> **이전 보고**: `output/HANDOFF_TO_01_v6_data-dn.md`
> **참조**: `REPLY_FROM_01_2026-05-10_v2.md` v1 차수 가이드

---

## 1. 페이지 진단 결과

### ✅ 이미 양호 (sales_orders.html 진입 시 발견)
| 항목 | 상태 |
|---|---|
| `data-dn` 부착 | 18 영역 광범위 부착 (페이지 자체 v2 차수급) |
| `@media (max-width:1100px)` | 적용됨 (line 42, 55) |
| sticky thead | 적용됨 (line 141) |
| 관리번호 1열 | 적용됨 (line 294) |
| 좌우 2단 분할 (B안) | 적용됨 (z23) |

### ❌ 갭 3건 발견
| # | 갭 | 위반 |
|---|---|---|
| 1 | 시안1 토큰 0회 | `--qv-*` / `--biz-*` 0회 — REPLY v2 라인 154 검수 미달 |
| 2 | mgmt 알약 분기 | `.mgmt-tag` (amber #b45309) ≠ project_detail.html `.mgmt-pill` (잉크 #0f172a) — 일관성 위반 |
| 3 | 빨강 hex 다수 | `#dc2626 / b91c1c / 991b1b / fee2e2` 약 10~12회 — REPLY v2 라인 155 빨강 ≤5% 위반 가능 |

---

## 2. v1 차수 적용 (갭 1·2)

REPLY v2 v1 차수 정의 = "토큰 마이그레이션 + 핵심 컴포넌트 1~2개" → 갭 1·2 적용. **갭 3 (빨강 다이어트) 는 v3 차수 별도**.

### 2-1. 시안1 토큰 11종 도입 (갭 1)
sales_orders.html 라인 5~17 신규 CSS:
```css
body {
  --qv-surface:   #ffffff;
  --qv-surface-2: #f7f8fa;
  --qv-line:      #eef0f4;
  --qv-ink:       #0f172a;
  --qv-ink-2:     #334155;
  --qv-ink-3:     #64748b;
  --biz-t: #c2410c;  /* New Equipment */
  --biz-m: #1e40af;  /* Maintenance/Service */
  --biz-e: #6d28d9;  /* Export */
  --biz-c: #047857;  /* Consumable */
}
```
- project_detail.html z41 과 동일값 → 페이지 간 일관성 확보
- body 스코프 한정, 다른 페이지 영향 0

### 2-2. mgmt 알약 통일 (갭 2)
1. `.mgmt-pill` 컴포넌트 sales_orders.html 에 신규 추가 (project_detail z41 과 동일)
2. SO 리스트 `.mgmt-tag` (line 156~157) 색상 → 잉크 토큰
   - `background:#b45309` → `background:var(--qv-ink)`
   - hover `#92400e` → `var(--qv-ink-2)`
3. 임박 납기 `.up-r1 .mgmt` (line 117) 색상 → 잉크 토큰
   - `background:#b45309` → `background:var(--qv-ink)`

이로써 페이지 3곳 (project_detail / sales_orders SO 리스트 / sales_orders 임박납기) 모두 동일 잉크 알약 톤.

### 2-3. 빨강 다이어트 (갭 3) — **본 v1 차수 적용 안 함**
- REPLY v2 v1 차수 정의 = "토큰 + 컴포넌트 1~2개" → 빨강 미포함
- v3 차수에 별도 결재로 묶음 (project_detail.html v3 와 함께 가능)

---

## 3. 변경 파일

```
- KNK업무시스템구축/01_HAIST_WORKS/app/templates/sales_orders.html  (+24줄, -10줄 변경)
  · 시안1 토큰 11종 신규 (line 5~17)
  · .mgmt-pill 컴포넌트 신규 (line 19~36)
  · .so-list-b .mgmt-tag 색상 amber → 잉크 (line 156)
  · .up-r1 .mgmt 색상 amber → 잉크 (line 117)
```

(메인 BAT 미수정 — REPLY v2 라인 33,170 룰 준수)

---

## 4. 검증

### 4-1. 정적 검증
- ✅ `body` 스코프 → 본 페이지 한정. 다른 페이지/partial 영향 0
- ✅ `_v5_partials/styles.html` 미접촉
- ✅ `main.py` 라우트 / DB 스키마 미접촉
- ✅ 좌우 분할(B안) / 캘린더 / 임박납기 / KPI / 사업부 탭 모두 보존
- ✅ data-dn 18 영역 보존

### 4-2. 회귀 위험 점검
| 항목 | 영향 |
|---|---|
| 좌우 2단 그리드 (z23) | ⭕ 보존 |
| 1100px 반응형 | ⭕ 보존 |
| sticky thead + sticky shadow | ⭕ 보존 |
| 캘린더 색상 (cls-overdue / d3 / d7 / future) | ⭕ 보존 — 빨강 hex 그대로 (v3에서 처리 예정) |
| KPI 6칸 사업부 색상 | ⭕ 보존 — `.k1~k6 --c` 로컬 변수 그대로 |
| 사업부 탭 그라디언트 | ⭕ 보존 — t-T/M/K/C 활성 상태 그대로 |

### 4-3. 시각 영향
- mgmt 알약 (SO 리스트 + 임박 납기) **호박색 → 검정 잉크색** 으로 변경
- 시각 영향 큼 (페이지 헤더 부분)
- project_detail.html 헤더와 동일 톤 → 매출영업 페이지 군 일관성 ↑

---

## 5. 페이지 v1 차수 진행률

REPLY v2 라인 124~130 단계 분할:
| 페이지 | v1 (토큰+컴포넌트) | v2 (data-dn) | v3 (빈 스켈레톤) | v4+ |
|---|---|---|---|---|
| project_detail.html | 🟢 통과 (z41) | 🟢 완료 (z43) | ⏭ | ⏭ |
| **sales_orders.html** | **🟢 본 차수 완료 (z44)** | 🟢 이미 부착 (기존) | ⏭ | ⏭ |
| sales_home.html | 🔘 | 🔘 | 🔘 | 🔘 |
| sales_order_detail.html | 🔘 | 🔘 | 🔘 | 🔘 |
| customer_detail.html | 🔘 | 🔘 | 🔘 | 🔘 |
| 견적/납품수금/미수금 (10) | 🔘 | 🔘 | 🔘 | 🔘 |
| 수출입/FTA (11) | 🔘 | 🔘 | 🔘 | 🔘 |

---

## 6. 다음 단계 결재 요청

### 결재 사항
- [ ] **결재 A**: 본 차수 git push 승인 (commit `v5H226z44`)
- [ ] **결재 B**: 다음 페이지 / 다음 차수
  - 옵션 (γ) `sales_home.html` 진입 (입사 첫 화면, 시안1 12-col bento 미적용)
  - 옵션 (δ) `customer_detail.html` 진입 (중요 페이지)
  - 옵션 (ε) project_detail.html v3 차수 (빈 스켈레톤 + 빨강 다이어트 묶기)
  - 옵션 (ζ) 결재 A만 + 검증 후 다음 사이클

빅터 권장: **(γ) sales_home.html** — 입사 첫 화면이 비어있는 게 가장 큰 사용자 첫인상 갭. 다음 빠른 win 가능.

---

**문의**: `_ORDERS/` 발주서 v2 / `99_DISPATCH/` 채널
