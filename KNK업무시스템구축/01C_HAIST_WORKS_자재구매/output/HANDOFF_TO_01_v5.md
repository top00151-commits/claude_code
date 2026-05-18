# 📤 실무팀3 → 빅터(01) 핸드오프 — v5 (3차 발주 풀체인)

> **세션:** 실무팀3 (자재구매센터)
> **워크트리:** `cranky-shtern-789fa2` — 메인 폴더 직접 작업 모드
> **기준일:** 2026-05-11
> **시스템 버전:** v5H226z57
> **차수:** 5차 (발주 풀체인 완성)

---

## 1. 배경

대표님 2026-05-11 직접 지시:
> "다음차수 진행해.. 넌 항상 완료 후 한번더 검증을 꼭하고 산출물 완료 했다고 해야해."

→ HANDOFF v4 §8 우선순위 1번 (발주 풀체인 완성: po_form / po_receive) 즉시 착수.
→ **완료 선언 전 자체 검증 룰 메모리화** (`feedback_verify_before_done.md`).

## 2. 산출물 (2 페이지 + 검증 룰 메모리)

### A. 페이지 (전면 재작성, 시안1 + 룰 v4)

| # | 그룹 | 파일 | 핵심 |
|---|---|---|---|
| 1 | B 발주 | `po_form.html` | 4-step stepper + 폼 카드 + 라인 표(datalist 자동매핑 + active-price fetch) + 합계 자동 + 사이드 요약 |
| 2 | B 발주 | `po_receive.html` | KPI 4 (발주량/기입고/금일입고/잔량) + 발주 정보 카드 + 9-cols 라인 (LOT/유효기한/비고) + 입고율 progress bar |

### B. **라우터 호환성 핵심 수정 — po_receive.html**

**기존(z54 이하) 폼 형식:**
```html
<input name="receive_qty_{id}" />   ← indexed name
```

**라우터(main.py:12035) 기대 형식:**
```python
item_ids = form.getlist("po_item_id")
qtys = form.getlist("receive_qty")
notes = form.getlist("item_note")
lots = form.getlist("lot_no")
expiries = form.getlist("expiry_date")
```

**z57 정정 후:**
```html
<input type="hidden" name="po_item_id" value="{{ it.id }}" />
<input class="line-input rcv" type="number" name="receive_qty" ... />
<input type="text" name="lot_no" ... />
<input type="date" name="expiry_date" ... />
<input type="text" name="item_note" ... />
```
→ getlist 순서가 라인 순서와 일치 (DOM 순서 직렬화).

⚠️ **잠재 영향:** 이 수정 전에는 사용자가 입고 처리 폼에 입력한 값이 `getlist("po_item_id")`가 빈 리스트라서 `lines=[]`로 처리되어 `?error=empty`로 리디렉션. **z54 이하에서 발주 입고 자체가 작동하지 않았던 잠재 버그를 z57에서 복구**.

### C. 검증 룰 메모리

`memory/feedback_verify_before_done.md`:
> 작업 완료 후 곧바로 "완료" 보고하지 말 것. 반드시 한 번 더 검증한 뒤에 산출물 완료를 선언한다.

## 3. 자체 검증 패스 결과 (3패스)

### 1패스 — Syntax + 파일 구조
- ✅ chrome.html / styles.html / debug_overlay.html include
- ✅ Jinja syntax 정상 (`{% if is_edit %}`, `{% for %}`, `|default()` 안전)
- ✅ z57 라벨 + tokens.css `?v=20260511v5H226z57`
- ❌ **결함 1 발견** — po_receive 헤더 `<textarea name="note">`는 라우터에서 받지 않음 → 사용자 입력 손실 위험

### 2패스 — 결함 1 수정
- 헤더 textarea 제거 → 안내문으로 대체 ("라인별 LOT·유효기한·비고는 아래 표에서 입력")
- 라인에 `<input name="item_note">` 추가 → 라우터 `getlist("item_note")` 호환
- ❌ **결함 2 발견** — 라인 grid 8 → 9 cols 변경했으나 `line-foot`은 9번째 div에 클래스 없어 모바일 미디어 쿼리 일치 X

### 3패스 — 결함 2 수정 + 최종 확인
- `line-foot` 마지막 3 div에 `lot-cell` / `exp-cell` / `note-cell` 클래스 추가
- 1023px 미디어 쿼리에 `col-note` / `note-cell` 숨김 추가
- ✅ Grep `amber-grad|--grad-amber` → 0건 (양 페이지)
- ✅ Grep form name (`po_item_id`/`receive_qty`/`item_note`/`lot_no`/`expiry_date`/`occurred_at`) → 모두 정확 위치에 존재
- ✅ line-head/row/foot 모두 9 div 일관 (1280px ↓ 8 cols / 1023px ↓ 6 cols)

## 4. 룰 v4 ADDENDUM 100% 준수

| 룰 | 본 차수 적용 |
|---|---|
| 1. 메인 BAT 갱신 | 0건 ✅ |
| 2. v5H226z 라벨 | HTML 주석만 ✅ |
| 3. 워크트리 동기화 | 메인 직접 작업 (옵션 A 불필요) ✅ |
| 4. 시안1 (e) 단계 | v1 토큰 + v2 data-dn 적용 ✅ |
| 5. 99_DISPATCH 게시 | 0건 ✅ |

## 5. 발주서 7항 금지사항 100% 준수

| 금지 | 본 차수 |
|---|---|
| 다른 팀 페이지 | 0건 ✅ |
| `_v5_partials/` 공통 partial | 0건 ✅ |
| DB 스키마 변경 | 0건 ✅ |
| **라우트/Jinja 변수/권한 변경** | **0건** ✅ (라우터는 그대로 두고, 폼 form name을 라우터에 맞춤) |
| 위하고 ERP 직접 연동 | 0건 ✅ |

## 6. data-dn 부착 (debug_overlay 호환)

### po_form.html (6개)
- `pf:head` (회색)
- `pf:stepper` (blue)
- `pf:basic` (green)
- `pf:lines` (purple)
- `pf:terms` (blue)
- `pf:totals` (green)
- `pf:side` (blue)
- `pf:action` (amber)

### po_receive.html (7개)
- `gr:head` (회색)
- `gr:kpi` (green)
- `gr:po-info` (blue)
- `gr:date` (green)
- `gr:lines` (purple)
- `gr:rate` (green)
- `gr:action` (amber)

## 7. 검수 절차 (빅터 검수용)

```
http://localhost:8081/po/new?debug=1                  ← 새 발주 작성
http://localhost:8081/po/{기존 PO id}/edit?debug=1    ← 발주 수정
http://localhost:8081/po/{기존 PO id}/receive?debug=1 ← 입고 처리
```
- Ctrl+Shift+D 토글 → 우측 하단 디버그 패널
- 영역 outline + 라벨 표시

검수 항목:
- amber-grad 잔존 0건 ✅
- 빨강 ≤1개/페이지 (req 표시 + over 클래스만) ✅
- 폼 동작:
  - po_form: 라인 추가/삭제, datalist 매칭 시 단가 자동, 합계 즉시 갱신, 사이드 요약 동기화
  - po_receive: 「전 행 잔량」/「전 행 0」 버튼, 수량 초과 시 빨강 (over 클래스), 입고율 progress bar, KPI 금일/잔량 즉시 갱신
- **라우터 호환성 (가장 중요):** 입고 처리 후 `/po/{id}?received=N`으로 리디렉션 정상

## 8. 빅터(01) 처리 요청

- [ ] 2 페이지 검수 (위 3개 URL)
- [ ] 입고 처리 form 정상 동작 검증 (z54에서 `?error=empty` 발생했던 케이스가 z57에서 정상 작동하는지)
- [ ] STATUS.md `🟢 통합 완료` 섹션 z57 추가 (5차)
- [ ] git push (빅터 책임)
- [ ] 메인 BAT z58 → 다음 z 갱신 (빅터 책임)
- [ ] 다음 차수 승인 — part_detail / wo_form / 출고 영역

## 9. 다음 차수 권장 (대표 결재 시)

| 우선 | 페이지 | 이유 |
|---|---|---|
| 1 | `part_detail.html` | 부품 상세 (FIFO 레이어 + 단가 이력 + 첨부 + 프로젝트 사용량) — 분량 큰 페이지 |
| 2 | `wo_form.html` / `wo_print.html` | 작업지시 풀체인 (WO 목록 z57 이미 완료) |
| 3 | `stock_issue.html` / `stock_issues.html` / `stock_qc.html` | 재고 출고·검사 분리 |
| 4 | `qc_report_form.html` / `qc_report_print.html` | 품질 입력·인쇄 |
| 5 | `qms_dashboard.html` / `qms_pareto.html` / `qms_capa.html` | 품질 모듈 (QC 목록 z57 이미 완료) |
| 6 | `rates_*` 5종 | 환율·원가 (별도 결재 필요 — 매출영업과 연계) |

## 10. 운영 메모

- **본 워크트리(`cranky-shtern-789fa2`)**: 메인 폴더 직접 작업 모드
- **2~5차 누적:** 16 페이지 (po_list / logistics_home / parts / suppliers / stock_balances·movements·abc·safety·turnover·reorder·receipts / po_detail / wo_list / qc_report_list / **po_form / po_receive**)
- **잠재 버그 복구:** po_receive z57은 라우터 호환성 회복으로 z54 이하의 입고 처리 실패를 해소

---

**보고:** 실무팀3 (자재구매센터) → 빅터(01)
**결재:** 김정락 대표이사 직접 라인
**자체 검증:** 3패스 통과 (결함 2건 발견 → 즉시 수정 → 재검증 통과)
**완료 선언:** 2026-05-11 / **검증 통과 후** 정식 산출물 완료
