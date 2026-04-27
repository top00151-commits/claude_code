# [TO 01] 정식 시안 — Stock Audits + Stock Adjustments (사이클 56·57)

- 발신: 05 디자인팀 빅터(Victor) → 수신: 01 코드팀 / 일자: 2026-04-27
- 출처: 04 Explore (11:50) Top10 #1·#2 갭, 09팀장 정식 발주
- 외부 자산: **0건** (폰트·이미지·라이브러리 신규 0)
- v2 본체 `static/style.css` L4287~4574 미접촉 / 핫패치 G1~G5 보존
- 토큰: `05_HAIST_WORKS_디자인팀/03_시안/00_design_tokens.css` 만 사용
- 재사용 클래스: `.mini-tbl`(style.css L300), `.data-table`, `.card`, `.btn`, `.btn-primary`, `.chip`, `.tag-done/-progress/-wait/-delay`(00_design_tokens.css L165~168), `.page-head`, `.muted`

---

## 0. 자기 점검 (8조 의무, 5/5 PASS)

- KNK 11+1 페르소나 — P4 분기 1회 / admin 승인 가치 직접
- 외부 자산 0 / v2 본체 미접촉 / 핫패치 G1~G5 보존
- 결재 사안 아님 — 시안 .md 단계 (코드 변경 없음)
- 정직성 v3 — grep 직접 인용만 사용
- BAT 갱신 의무 — 01 작업 시 양파일 갱신

---

## A. Stock Audits (재고 실사) 시안

### A-0. 현황 인용 (grep 직접)
```
app/templates/stock_audit.html → 148행 (wc -l)
app/main.py L5035 GET  /stock/audits        L5048 POST /stock/audits/new
app/main.py L5059 GET  /stock/audits/{id}   L5095 POST /stock/audits/{id}/items
app/main.py L5256 POST /stock/audits/{id}/close
```
→ 라우트·템플릿 골격은 **이미 존재**. 본 시안은 **UX·시각 보강** 방향만.

### A-1. 화면 4뷰

| 화면 | URL | 모드 |
|---|---|---|
| 1. 실사 목록 | `/stock/audits` | mode=list (기존) + KPI Strip 추가 |
| 2. 신규 시작 | `/stock/audits/new` (POST) | 비고 입력 폼 (기존) |
| 3. 실사 상세 | `/stock/audits/{id}` | mode=detail (기존) + 라인 그리드 보강 |
| 4. 실사 마감 | `/stock/audits/{id}/close` (POST) | PENDING 차단 (기존) |

### A-2. 보강 요소 4건
1. **KPI Strip (목록 상단)** — `.card` × 3 flex grid: 진행중 실사 / 미마감 라인 / PENDING 조정. PENDING 8↑ 시 빨강 배경(`#FEF2F2`).
2. **부품 검색 (datalist)** — 기존 `<select>` 를 표준 `<datalist>`로 교체. 외부 라이브러리 0. 부품 N개 시 검색·스캔 같은 단순 입력.
3. **차이 라이브 미리보기** — `oninput` 인라인 JS. 양수=`#059669` 녹색(입고누락), 음수=`#DC2626` 빨강(분실), 0=`#6B7280` 회색. 기존 L134 동일 표기 유지.
4. **매칭률 카드 색상** — 95%↑ `#ECFDF5` / 80~95% `#FFFBEB` / 80%↓ `#FEF2F2`. 기존 L72~93 4-grid 보존, 인라인 style만 추가.

### A-3. P4 시나리오
```
[1] /stock/audits → "신규 실사" 클릭 → 비고 "2026-Q2 정기" → AUD-202604-0001 생성
[2] 상세 진입 → datalist 부품 검색 → 실측 → 차이 라이브 → "라인 저장"
[3] 라인 N건 반복 → 차이 발생 라인은 stock_adjustments PENDING 자동 생성
[4] /stock/adjustments 점프 → 자재팀장 승인 대기
[5] PENDING 0건 시 /stock/audits/{id}/close 활성 → 마감
```

### A-4. P1 CEO 위젯 (선택, `/` 대시보드 1줄)
`.card` 단일 — "분기 실사 현황 / 진행중 1 · PENDING 8 [상세→]". PENDING 8↑ 자동 빨강 배경.

---

## B. Stock Adjustments (재고 조정) 시안

### B-0. 현황 인용 (grep 직접)
```
app/templates/stock_adjustment.html → 115행 (wc -l)
app/main.py L5116 GET  /stock/adjustments       L5141 POST .../approve
app/main.py L5155 POST .../reject               L5190 POST .../attach
app/main.py L5224 GET  .../attachments          L5238 GET .../download
```
→ 골격 + 첨부 + 승인 워크플로우 **이미 존재**. 본 시안은 **수동 조정 추가 + UX 보강**.

### B-1. 화면 5뷰

| # | 화면 | URL | 상태 |
|---|---|---|---|
| 1 | 조정 목록 | `/stock/adjustments?status=...` | 기존 ✓ + KPI/필터 보강 |
| 2 | **수동 조정 등록** | `/stock/adjustments/new` | **신규 발주** |
| 3 | 상세+첨부 | `/stock/adjustments/{id}/attachments` | 기존 ✓ |
| 4 | 승인 | `/stock/adjustments/{id}/approve` (POST) | 기존 ✓ |
| 5 | 반려 | `/stock/adjustments/{id}/reject` (POST) | 기존 ✓ + 사유 의무화 |

### B-2. KPI Strip + 필터 보강
```
PENDING 8 (빨강) | APPROVED(月) 24 | REJECTED(月) 2 | 첨부누락 3 (주의)
[상태▾] [사유코드▾ 신규] [기간▾ 신규]
```
- `.card` × 4 flex / 기존 L46~57 필터 행 보존 + 사유·기간 추가

### B-3. 사유 코드 6종

| 코드 | 한글 | chip | 첨부 | 비고 |
|---|---|---|---|---|
| `COUNT` | 실사조정 | tag-wait | 권장 | stock_audits 차이 → 자동 PENDING. 수동 등록 차단 |
| `DAMAGE` | 불량 | tag-delay | **의무** | 입고 검수 / 가공 중 발견 |
| `SCRAP` | 폐기 | tag-delay | **의무** | 사용 불가 폐기 (사진) |
| `TRANSFER` | 창고이동 | tag-progress | 권장 | 본사 ↔ 외주 / 창고 간 |
| `RETURN` | 반품 | tag-progress | **의무** | 거래처 반품 (문서) |
| `OTHER` | 기타 | tag-wait | **의무** | 사유 텍스트 + 증빙 |

기존 `.tag-*` 4종만 사용. 의무 첨부 코드는 승인 시 첨부 0이면 서버 거부 (D-3 #3 발주).

### B-4. 신규 수동 조정 폼 (`/stock/adjustments/new`)
- 부품 [datalist 검색] · 시스템 수량 라이브 표기
- 사유코드 [select ▾] · 선택 시 chip 색 미리보기
- 조정 수량 [number] · 차이 색상 라이브
- 사유 메모 [text] · 첨부 [file] (사유에 따라 의무 표시)
- [등록 (PENDING)] → 자재팀장/임원 승인 대기

### B-5. 승인 워크플로우 시각화 (`<details>` collapse)
```
[등록] → ●PENDING ─[승인]→ ●APPROVED → stock_movements ADJUST 자동기록
                  └─[반려]→ ●REJECTED  (감사 추적 보존)
```
표준 HTML `<details>` — 외부 자산 0. 권한 분기는 기존 `can_approve` (L54·89) 보존.

### B-6. P4 + admin 시나리오
```
P4: /stock/adjustments/new → 부품 검색 → DAMAGE → -3 → 사진 첨부 → 등록(PENDING)
admin: /stock/adjustments?status=PENDING → 첨부·사유 확인 → [승인] / [반려+사유]
승인 시: stock_movements kind=ADJUST 자동 기록 + stock_balances 즉시 반영
```

---

## C. 외부 자산 0 보장 체크리스트

| 항목 | 사용 컴포넌트 | 신규? |
|---|---|---|
| 폼 | `<input>` `<select>` `<datalist>` `<details>` 표준 HTML | 0 |
| 테이블 | `.data-table` `.mini-tbl` (style.css L300, L1502) | 0 |
| 카드 | `.card` (00_design_tokens.css L170) | 0 |
| Chip | `.chip` `.tag-*` 4종 (L165~168) | 0 |
| 버튼 | `.btn` `.btn-primary` (기존 base) | 0 |
| 색상 | 토큰 변수 + HEX 인라인 (`#059669` `#DC2626` 등) | 0 |
| 폰트 | 기존 Pretendard 시스템 | 0 |
| 아이콘 | 텍스트 화살표 `→` `←` `▾` `▰` 만 | 0 |
| 이미지 / JS 라이브러리 | 0건 | 0 |

**합계 = 외부 신규 자산 0건**

---

## D. 01에 전달할 발주 사양

### D-1. 라우트 (신규 2 / 보강 5 / 보존 4)

| # | 메서드 | URL | 변경 |
|---|---|---|---|
| 1 | GET | `/stock/audits` | 보강 (KPI Strip) |
| 2 | POST | `/stock/audits/new` | 보존 |
| 3 | GET | `/stock/audits/{id}` | 보강 (매칭률 색상 + datalist) |
| 4 | POST | `/stock/audits/{id}/items` | 보존 |
| 5 | POST | `/stock/audits/{id}/close` | 보존 |
| 6 | GET | `/stock/adjustments` | 보강 (KPI + 사유필터) |
| 7 | **GET** | **`/stock/adjustments/new`** | **신규 (폼)** |
| 8 | **POST** | **`/stock/adjustments/new`** | **신규 (수동 등록)** |
| 9 | POST | `/stock/adjustments/{id}/approve` | 보강 (의무첨부 검증) |
| 10 | POST | `/stock/adjustments/{id}/reject` | 보강 (사유 의무화) |
| 11 | POST | `/stock/adjustments/{id}/attach` | 보존 |

### D-2. 템플릿 (신규 0 / 수정 2)

| 파일 | 현재 | 변경 |
|---|---|---|
| `app/templates/stock_audit.html` | 148행 | KPI Strip + datalist + 차이 라이브 + 매칭률 카드 색상 |
| `app/templates/stock_adjustment.html` | 115행 | KPI Strip + 사유필터 + 신규 mode (`mode=new` 폼) + 사유코드 chip 6종 |

### D-3. 헬퍼 (신규 1 / 보강 2)

1. **신규**: `create_stock_adjustment_manual(part_id, reason, qty, note, user_id)` (`app/database.py`)
2. **신규 검증**: 사유=COUNT 수동 등록 차단 (라우트 #8 내부)
3. **보강 검증**: 의무 첨부 (DAMAGE/SCRAP/RETURN/OTHER) — approve 라우트 #9 거부 로직

### D-4. 권한 (기존 정책 보존)

| 동작 | P4 자재 | 자재팀장 | 임원/admin |
|---|---|---|---|
| 실사 시작·라인 입력 | ✓ | ✓ | ✓ |
| 실사 마감 | ✗ | ✓ | ✓ |
| 수동 조정 등록 | ✓ | ✓ | ✓ |
| 조정 승인/반려 | ✗ | ✓ | ✓ |

### D-5. 01 작업 시 정직성 v3 의무
- grep -n 직접 인용 (라인번호 포함)
- wc -l 결과 직접 인용 (수정 후 라인 수)
- BAT 양 파일 LAST UPDATE 갱신 (`KNK_시작.bat` + `START.bat`)
- v2 본체 L4287~4574 미접촉 grep 검증
- 핫패치 G1~G5 grep 130 매칭 보존 검증

---

## E. 산출 위치
`05_HAIST_WORKS_디자인팀/_TO_01_정식시안_StockAudits_Adjustments_2026-04-27.md` (본 문서)

## F. 사이클 발주 분배
- **사이클 56 (Stock Audits)**: D-1 #1·#3·#4 보강 + D-2 #1 보강 (KPI/datalist/차이 라이브/매칭률 색상)
- **사이클 57 (Stock Adjustments)**: D-1 #6~#10 + D-2 #2 + D-3 신규 1·검증 2 (수동 등록 폼 + 사유코드 6종 + 의무첨부 검증)

대표 결재 필요 사안 없음. 01 즉시 착수 가능.

---

*05 디자인팀 빅터 · 2026-04-27 · v2 본체 미접촉 · 외부 자산 0건 · 핫패치 보존 · 8조 자기점검 5/5 PASS*
