# 📋 실무팀2 → 빅터(01) 핸드오프 v6 — v2 차수 (data-dn 부착)

> **발신**: 실무팀2 (매출영업센터)
> **수신**: 빅터 (01 통합실무팀)
> **결재**: 김정락 대표이사 — 2026-05-10 "메인 폴더 동기화 + 다음 차수 진행"
> **작성일**: 2026-05-10
> **버전**: v5H226z41 → **v5H226z43**
> **이전 보고**: `output/HANDOFF_TO_01_v5_도구.md`
> **참조**: `REPLY_FROM_01_2026-05-10_v2.md` 라인 137~140 (v2 차수 가이드)

---

## 1. 적용 범위

**v2 차수 = REPLY v2 라인 137~140 명시 작업**

| 항목 | 상태 |
|---|---|
| z40 자체 ::before 시스템 제거 (partial 충돌 해소) | ✅ |
| `data-dn` 영역 라벨 6건 명시 부착 | ✅ |
| `_v5_partials/debug_overlay.html` 자동 라벨 시스템 통합 | ✅ |

---

## 2. 핵심 발견 — z40 ::before 시스템 partial 과 충돌

### 발견 경위
`_v5_partials/debug_overlay.html` 정독 결과:
- **chrome.html line 389** 에서 자동 include 중
- `?debug=1` → `body.knk-debug` 클래스 자동 추가
- `[data-dn]` 속성 가진 모든 영역 ::before 자동 라벨링
- AUTO_ZONES 12종 자동 감지 — `.page-head / .so-card / .so-units-wrapper / .parts-h-proxy` 등 우리 페이지 영역 다수 포함

### 충돌 양상
- 우리 z40: `body.debug-on` + 4구역 ::before 직접 정의
- partial: `body.knk-debug` + `[data-dn]::before` (attr content)
- `?debug=1` 시 동일 요소에 ::before 두 시스템 경쟁 → CSS spec 상 ::before 1개만 가능 → 후정의 우선

### 해결 (v2 차수 본 작업)
- 우리 z40 자체 ::before CSS 4구역 + body.debug-on JS 토글 **제거**
- partial 시스템 활용 (`?debug=1` → 자동)
- AUTO_ZONES 미감지 영역만 `data-dn` 명시 부착

---

## 3. 변경 파일 (1건 — worktree)

```
- KNK업무시스템구축/01_HAIST_WORKS/app/templates/project_detail.html
  (CSS 18줄 제거 + JS 9줄 제거 + data-dn 속성 6건 추가)
```

### 메인 폴더 동기화 (REPLY v2 라인 105~109 옵션 A)
```
- 워크트리 → 메인:
  · 01_HAIST_WORKS/app/templates/project_detail.html
  · 01B_HAIST_WORKS_매출영업/PROGRESS.md
  · 01B_HAIST_WORKS_매출영업/output/HANDOFF_TO_01_v1~v6.md
  · 01B_HAIST_WORKS_매출영업/01B_매출영업_상태확인.bat
- 메인 BAT (KNK_시작.bat / START.bat) 미복사 — REPLY v2 라인 33,170 빅터 통합 시점
```

---

## 4. data-dn 부착 6건 (AUTO_ZONES 미감지 영역만)

| # | 영역 | 위치 | data-dn | tone |
|---|---|---|---|---|
| 1 | 추가 발주 모달 | line 221 | `followup-order-modal` | purple |
| 2 | 메인 그리드 컨테이너 | line 439 | `detail-grid` | amber |
| 3 | 메인 콘텐츠 좌측 컬럼 (1fr) | line 440 | `main-content` | blue |
| 4 | 호기 일괄 상태 도구 | line 822 | `bulk-status-tools` | amber |
| 5 | PARTS 컬럼 토글 chip 바 | line 846 | `parts-col-toggle` | green |
| 6 | 우측 사이드바 (320px aside) | line 1699 | `right-rail` | purple |

### partial 자동 감지 영역 (부착 불요)
- `.page-head` ✅
- `.crumbs` ✅
- `h1.page-title` ✅
- `.so-card` ✅ (모든 SO 카드)
- `.so-units-wrapper` ✅ (PARTS 표 wrapper)
- `.parts-h-proxy` ✅ (가로 스크롤 proxy)
- `main.main` ✅

---

## 5. 검증

### 5-1. 정적 검증
- ✅ `body.debug-on` 검색 결과 0회 (제거 완료)
- ✅ `data-dn` 검색 결과 6회 (부착 완료)
- ✅ `_v5_partials/` 미접촉 (디버그 오버레이 partial 자체는 빅터 영역)
- ✅ `main.py` 라우트 / DB 스키마 / PARTS 백엔드 미접촉
- ✅ z41 토큰·잉크 알약 보존 / z42 PARTS sticky 보존 / z40 1100px 반응형 보존

### 5-2. 회귀 위험 점검
| 항목 | 영향 |
|---|---|
| z40 1100px 반응형 (CSS) | ⭕ 보존 |
| z40 ::before 시스템 | 🔄 **제거됨 — partial 시스템으로 통합** |
| z41 시안1 토큰 + mgmt-pill | ⭕ 보존 |
| z42 PARTS sticky 첫 3컬럼 | ⭕ 보존 |
| 다른 영역 사용자 노출 시각 | ⭕ 영향 없음 — `data-dn`/`data-dn-tone` 은 디버그 모드에서만 보임 |

### 5-3. 사용자 체감
- **`?debug=1` ON**: partial 시스템이 우리 6 영역 + AUTO_ZONES 7 영역 모두 outline + 라벨링 + 크기 측정
- **`?debug=1` OFF**: 일반 사용자에 영향 0 (data-dn 속성은 시각 출력 없음)

### 5-4. 메인 BAT 미수정 (REPLY v2 룰 준수)
- ✅ 본 v2 차수 작업 동안 `KNK_시작.bat` / `START.bat` 미수정
- ⚠️ z40~z41 단계 BAT 갱신 (z38→z40→z42→z41) 은 워크트리 한정 — REPLY v2 라인 43~45에 따라 빅터 통합 시점에 정정

---

## 6. 시안1 (e) 적용 진행률

REPLY v2 라인 124~130 분할표 기준:

| 차수 | 항목 | 상태 |
|---|---|---|
| **v1** | 토큰 마이그레이션 + 핵심 컴포넌트 1~2개 | 🟢 통과 (z41 시안1 토큰 + mgmt-pill) |
| **v2** | + `data-dn` 영역 라벨 부착 | 🟢 본 차수 완료 |
| v3 | + 빈 스켈레톤 6개 골격 | ⏭ 다음 사이클 |
| v4+ | + 페이지 고유 컴포넌트 표준화 | ⏭ |

---

## 7. 다음 단계

### REPLY v2 동기화 절차 (라인 175~179) 시범 운영
1. ✅ 변경 HTML → 메인 폴더 같은 경로 복사
2. ✅ HANDOFF + PROGRESS → 메인 `01B.../output/`, `01B.../PROGRESS.md` 복사
3. ✅ chat 출력: "01B v2 차수 메인 폴더 동기화 완료"

### 결재 요청
- [ ] **결재 A**: 본 차수 git push 승인 (commits: `v5H226z43` v2 차수)
- [ ] **결재 B**: v3 차수 진입 (빈 스켈레톤 6개 골격) 또는 다음 페이지(`sales_orders.html`) 우선
- [ ] **결재 C**: 보류 중인 z43 (빨강 다이어트) — REPLY v2 검수 기준 "빨강 ≤5%" 와 충돌 미해소 → v3 또는 별도 차수에 묶기

빅터 권장:
- A 즉시 push
- B: 1번 페이지 다음 차수보다 **2번 페이지(`sales_orders.html`) 우선** — 80% 진행됨, 빠른 win 가능
- C: v3 차수에 빨강 다이어트 + 빈 스켈레톤 묶기 (한 번에 2갭 해소)

---

**문의**: `_ORDERS/` 발주서 v2 / `99_DISPATCH/` 채널
