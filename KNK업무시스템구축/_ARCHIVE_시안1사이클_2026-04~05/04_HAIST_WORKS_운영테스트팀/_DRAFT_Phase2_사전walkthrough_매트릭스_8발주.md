# Phase 2 사전 walkthrough 매트릭스 — 8 발주서 / 101 페이지

> 04 운영테스트팀 / 빅터
> 일자: 2026-05-01
> 트리거: 05→01 Phase 2 발주 8건 도착 (2026-04-30) + 01 응답 모니터링 단계
> 목적: 01 Phase 2-N 응답 도착 시 04가 즉시 walkthrough 발주 가능하도록 사전 매트릭스 정리
> 비간섭 원칙: 본 문서는 **사전 시나리오만**, 동적 회귀는 09/대표 신호 후

---

## 0. Phase 2 발주 8건 요약

| # | 카테고리 | 페이지 | P0 | 04 walkthrough 매핑 |
|---|---|---:|---|---|
| 2-1 | A 대시보드 | 5 | home (P0) | W1·W9 |
| 2-2 | B 매트릭스 | 12 | sales_dashboard | W2·W12 환율 |
| 2-3 | C 폼 + M1·M2 | 22 | po_form/quotation_form/quotation·issue·qc | W3·W5·W7·W8 |
| 2-4 | D 리스트 + M3 | 24 | po (마스터) | W6·W11 |
| 2-5 | E 상세 + M4 | 15 | board_detail/ticket/customer/po_detail | (po·ticket·customer) |
| 2-6 | H 관리자 | 15 | admin/permissions/company-info/team_perms | W10 |
| 2-7 | I 보고서 | 5 | weekly (마스터) | W9 |
| 2-8 | J 빅터 AI | 3 | dock (P0) / search | (전체 통합) |
| **합계** | — | **101** | 17개 P0 | W1~W12 전 매핑 |

---

## 1. 04 walkthrough 발주 즉시 사용 — Phase 2 grep 자체 검증 매트릭스

### 1.1 Phase 2-1 A 대시보드 (5 페이지)

```bash
# A-1. 신규 패턴 (PASS = ≥1)
grep -c 'class="bento"\|class="scope-tabs"\|class="action-card"' app/templates/home.html

# A-2. 옛 sage 잔존 (PASS = 0)
grep -cE 'var\(--sage-[0-9]+\)' app/templates/home.html app/templates/dashboard.html \
  app/templates/sales_home.html app/templates/logistics_home.html app/templates/cockpit.html

# A-3. 인라인 #hex 잔존 (PASS = 0, 현 home.html 19건 → 0)
grep -cE 'style="[^"]*#[0-9a-fA-F]{3,6}' app/templates/home.html

# A-4. v5 토큰 사용 (PASS = ≥3)
grep -c '\-\-amber\|\-\-paper\|\-\-knk-red' app/templates/home.html

# A-5. dashboard·cockpit 권한 가드 보존 (PASS = ≥1)
grep -n "require(req,\s*\['ceo','admin','executive'\]" app/main.py
```

**04 walkthrough W1·W9**:
- W1 김 부장 /home → 히어로 견적 23건 / 빠른 액션 4 / 알림 4 / 3 탭 #my·#team·#all
- W9 대표 /dashboard → 9 KPI 그리드 + 빅터 인사이트 카드

### 1.2 Phase 2-2 B 매트릭스 (12 페이지)

```bash
# B-1. 5 탭 (sales_dashboard 마스터)
grep -c 'class="metric-tabs"\|sales-period-tab' app/templates/sales_dashboard.html

# B-2. KPI 카드 통일 (PASS = 5종 페이지 동일 컴포넌트 사용)
grep -c 'class="kpi-card v5"\|metric-card' app/templates/sales_*.html

# B-3. /qms 카테고리 색상 통일
grep -c '\-\-amber\|\-\-knk-red' app/templates/qms_*.html

# B-4. /rates_dashboard 환율 통화 코드 다국어
grep -nE 'USD|VND|JPY|CNY|EUR' app/templates/rates_dashboard.html

# B-5. /bottlenecks 시각 일관성
grep -c '\-\-amber\|\-\-paper' app/templates/bottlenecks.html
```

**04 walkthrough W2·W12 환율**:
- W2 김 부장 5 탭 (현재·예측·노화·미수금·매출) 순회 → 대성기업 인지
- W12 환율 페이지 외화 표시 + 추세 그래프 (OPS-C-002 [P1] 적용 검증)

### 1.3 Phase 2-3 C 폼 + M1·M2 (22 페이지)

```bash
# C-1. 4-step 인디케이터 시각 (PASS = ≥1, 백엔드 P3 보류)
grep -c 'class="form-stepper"\|step-indicator-4' app/templates/po_form.html app/templates/quotation_form.html

# C-2. M-1 임시저장·템플릿 버튼 (시각만)
grep -c 'btn-temp-save\|btn-template' app/templates/po_form.html

# C-3. 섹션 표준 (h3 + 4px 앰버)
grep -c 'class="form-section"' app/templates/po_form.html app/templates/quotation_form.html

# C-4. 안전재고 모달 (OPS-P0-3 보존)
grep -n "checkSafetyStock\|onsubmit=.*checkSafetyStock" app/templates/stock_issue.html

# C-5. QC disposition 모달 (사이클 88 W7 보존)
grep -n "mode == 'disposition'" app/templates/stock_qc.html

# C-6. VAT 라디오 (OPS-D2 [C-007] 보존)
grep -n 'name="vat_mode"' app/templates/po_form.html
```

**04 walkthrough W3·W5·W7·W8**:
- W3 김 부장 견적 작성 4 step → 발행 모달 (M-2 시각 PASS, 백엔드 단일 폼)
- W5 이 차장 발주서 작성 → 라인 3 + 모달 → 발행 (VAT 라디오 PASS)
- W7 박 대리 입고 → QC FAIL → disposition 모달 자동 redirect
- W8 최 과장 출고 → 안전재고 미달 confirm 차단

### 1.4 Phase 2-4 D 리스트 + M3 (24 페이지)

```bash
# D-1. 상태 요약 5 카드 (마스터 po)
grep -c 'class="status-summary-card"\|class="state-cards"' app/templates/po_list.html

# D-2. M-3 일괄 액션 바 (검정+앰버 글로우)
grep -c 'class="bulk-action-bar"\|data-bulk-action' app/templates/po_list.html app/templates/parts.html

# D-3. 도구바 (필터 칩 + 검색 + 컬럼 설정)
grep -c 'class="toolbar"\|class="filter-chips"' app/templates/po_list.html

# D-4. 모바일 카드 레이아웃 (W11)
grep -c 'class="mobile-card"\|@media (max-width: 768px)' app/templates/notifications.html app/templates/tickets_list.html
```

**04 walkthrough W6·W11**:
- W6 이 차장 /po 일괄 액션 바 (체크박스 다중 선택 시 등장 / 일괄 삭제·내보내기 PASS, 일괄 발행 P3)
- W11 모바일 영업 외근 9페이지 카드 레이아웃

### 1.5 Phase 2-5 E 상세 + M4 (15 페이지)

```bash
# E-1. M-4 5단계 워크플로우 (po 마스터 적용)
grep -c 'class="workflow-stepper"\|class="stage-step"' app/templates/po_detail.html

# E-2. 적용 대상 분기 (적용 4종)
grep -l 'workflow-stepper' app/templates/po_detail.html app/templates/change_detail.html \
  app/templates/issue_detail.html app/templates/ticket_detail.html

# E-3. 비활성 대상 (워크플로우 영역 제거)
grep -L 'workflow-stepper' app/templates/customer_detail.html app/templates/board_detail.html \
  app/templates/part_detail.html
# (위 3개 파일은 매치 0 = PASS)

# E-4. 댓글·반응 표준 컴포넌트
grep -c 'class="comment-list"\|class="reaction-bar"' app/templates/po_detail.html
```

**04 walkthrough**:
- po_detail (P0 마스터) 5단계 + 라인 + 댓글
- ticket_detail (P0) 처리 흐름
- customer_detail (P0) 매출 그래프 + 모바일 fab

### 1.6 Phase 2-6 H 관리자 (15 페이지)

```bash
# H-1. admin_team_perms sage 0 강제 (현 46건 → 0)
grep -cE 'var\(--sage-[0-9]+\)' app/templates/admin_team_perms.html

# H-2. /admin 그리드 진입
grep -c 'class="admin-grid"\|class="atab"' app/templates/admin.html

# H-3. /admin/permissions/matrix 토글 + 감사 (W10)
grep -n 'class="perm-toggle"' app/templates/admin_permissions_matrix.html

# H-4. /admin/company-info ?saved=1 (OPS-P0-4 보존)
grep -n 'admin/company-info?saved' app/main.py

# H-5. team / team_perms 통일
grep -c '\-\-amber\|\-\-knk-red' app/templates/team.html app/templates/admin_team_perms.html
```

**04 walkthrough W10**: 대표 권한 매트릭스 → 토글 → 감사 로그

### 1.7 Phase 2-7 I 보고서 (5 페이지)

```bash
# I-1. weekly 빅터 인사이트 카드
grep -c 'class="weekly-insight"\|victor-insight' app/templates/weekly.html

# I-2. weekly @media print (OPS-W-3 보존)
grep -c '@media print' app/templates/weekly.html

# I-3. summary 시안 일관
grep -c '\-\-amber\|metric-card' app/templates/summary.html
```

**04 walkthrough W9**: 대표 /weekly → 빅터 인사이트 → PDF 인쇄 (사이드바·도크 숨김)

### 1.8 Phase 2-8 J 빅터 AI (3 페이지)

```bash
# J-1. dock (base.html 임베드 — 사이클 88 W4·W5 PASS 보존)
grep -c 'data-mode="victor"\|data-mode="search"' app/templates/base.html

# J-2. /search 마스터
grep -c 'class="search-results"\|class="search-filter"' app/templates/search.html

# J-3. dock 모드 전환 (사이클 88 보존)
grep -n 'function setDockMode' app/templates/base.html

# J-4. /me redirect
grep -n '/me.*RedirectResponse\|@app.get("/me"' app/main.py
```

**04 walkthrough**: 사이클 88 W4·W5 dock 흡수 + /search 신규

---

## 2. Phase 2 통합 W1~W12 매트릭스 (재정리)

| W# | 시나리오 | Phase 2 매핑 |
|---|---|---|
| W1 | 김 부장 /login → /home + .menu-code | 2-1 (home P0) + Phase 1 |
| W2 | 매출 매트릭스 5 탭 | 2-2 (sales_dashboard 마스터) |
| W3 | 견적 작성 4 step | 2-3 (quotation_form A) |
| W4 | 자재 hub | 2-1 (logistics_home D) |
| W5 | 발주서 작성 + VAT | 2-3 (po_form 마스터) |
| W6 | 발주 목록 + 일괄 액션 | 2-4 (po 마스터 + M-3) |
| W7 | 입고 → QC disposition | 2-3 (qc + disposition 모달) |
| W8 | 출고 + 안전재고 confirm | 2-3 (stock_issue + 모달) |
| W9 | 주간 보고 + 빅터 인사이트 | 2-7 (weekly 마스터) + Phase 1 print |
| W10 | 권한 매트릭스 + 감사 | 2-6 (admin_permissions_matrix) |
| W11 | 모바일 9페이지 | 2-4 (D 모바일 카드) + 모바일 spec |
| W12 | 인쇄 6종 + 빨간 배너 | 2-3 (수출 5종) + Phase 1 인쇄 |

---

## 3. 04 walkthrough 발주 트리거 매핑

| 01 응답 도착 | 04 즉시 발주 |
|---|---|
| `_FROM_01_2026-04-30_v5H5_Phase2-1_A_완료.md` | 위 §1.1 grep 5종 + W1·W9 |
| `_FROM_01_2026-04-30_v5H5_Phase2-2_B_완료.md` | §1.2 grep 5종 + W2·W12 환율 |
| `_FROM_01_2026-04-30_v5H5_Phase2-3_C_완료.md` | §1.3 grep 6종 + W3·W5·W7·W8 |
| `_FROM_01_2026-04-30_v5H5_Phase2-4_D_완료.md` | §1.4 grep 4종 + W6·W11 |
| `_FROM_01_2026-04-30_v5H5_Phase2-5_E_완료.md` | §1.5 grep 4종 + po·ticket·customer 상세 |
| `_FROM_01_2026-04-30_v5H5_Phase2-6_H_완료.md` | §1.6 grep 5종 + W10 |
| `_FROM_01_2026-04-30_v5H5_Phase2-7_I_완료.md` | §1.7 grep 3종 + W9 |
| `_FROM_01_2026-04-30_v5H5_Phase2-8_J_완료.md` | §1.8 grep 4종 + dock·search 통합 |

→ 01 응답 도착 시간 매트릭스 (가장 빠른 응답): Phase 2-1(4h) → 2-7(작은 5p) → 2-6/2-8 → 2-2(8h) → 2-5 → 2-4 → 2-3(16h) 예상.

---

## 4. 04 발주 표준 헤더 (Phase 2 walkthrough)

```markdown
# [04 → 01] v5 H5 Phase 2-N — walkthrough 결과 (정적 회귀)

> 트리거: `_FROM_01_2026-04-30_v5H5_Phase2-N_X_완료.md` 도착
> 비간섭 원칙 §평시 파일 검토 적용 — 서버 미기동 정적 grep
> 정직성 v3: grep -n 직접 인용, 추정 0건

## 1. Phase 2-N 적용분 §1 검증 (위 §1.N grep N종)
## 2. 04 walkthrough W#~W# 매트릭스 (PASS/SKIP/FAIL)
## 3. 발견 OPS-W-N (FAIL 시 재 발주)
## 4. P2 보류 비활성 확인 (M-1·M-2·M-3·M-4 일관)
## 5. 다음 사이클 (다른 Phase 2-N 회신 도착 시)
```

---

## 5. 정직성 v3 자가 검증

- ✅ 8개 발주서 §1 적용 대상 + §04 walkthrough grep 직접 인용
- ✅ 추정 0건 (Phase 2 응답 미도착 영역 = "도착 시 즉시" 명시)
- ✅ 합산 산식: 5 + 12 + 22 + 24 + 15 + 15 + 5 + 3 = 101 페이지 (정확 일치)
- ✅ "% 완료" 표현 미사용

---

## 6. 우선순위 (01 응답 도착 시 가동 순서)

1. **Phase 2-1 (5p, 4h)**: 가장 먼저 도착 예상 — W1·W9 walkthrough
2. **Phase 2-7 (5p, weekly)**: 빅터 인사이트 + print — OPS-W-3 흡수 검증
3. **Phase 2-6 (admin)**: H-1 sage 46건 → 0 검증 핵심
4. **Phase 2-8 (3p, dock)**: 사이클 88 회귀 + /search 신규
5. **Phase 2-2 (12p, 8h)**: 매트릭스 5 탭 + 환율
6. **Phase 2-5 (15p)**: M-4 워크플로우 5단계
7. **Phase 2-4 (24p)**: M-3 일괄 액션
8. **Phase 2-3 (22p, 16h)**: 가장 큰 규모 — P0 5종 우선

→ 04는 **01 응답 도착 즉시 본 매트릭스 §1.N grep 자동 발사** + walkthrough 매트릭스 발행.

---

*04 운영테스트팀 빅터 — 2026-05-01*
*Phase 2 사전 매트릭스 — 01 응답 8건 도착 시 즉시 walkthrough 발주 가능 상태.*
