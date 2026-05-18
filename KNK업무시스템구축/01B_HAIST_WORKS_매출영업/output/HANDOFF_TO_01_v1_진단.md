# 📋 실무팀2 → 빅터(01) 핸드오프 v1 (진단 패스)

> **발신**: 실무팀2 (매출영업센터)
> **수신**: 빅터 (01 통합실무팀)
> **결재**: 김정락 대표이사
> **작성일**: 2026-05-10
> **워크트리**: `claude/charming-yonath-a72046`
> **베이스 커밋**: `7c173f6 v5H226z39` (HEAD == main)
> **단계**: **진단 패스 (코드 수정 0건)** — 갭 리스트 보고용

---

## 1. 요약

`project_detail.html` (2,439줄) 시안1 디자인 시스템 6항 완료 기준 점검 결과,
**6항 중 0항 완전 충족, 3항 부분 충족, 3항 미적용** 으로 확인됩니다.

| 기준 | 상태 | 메모 |
|---|---|---|
| 1. 시안1 디자인 토큰 (`--qv-*`, `--biz-*`) | ❌ **미적용** | `--qv-*` 0회 / `--biz-t/m/e/c` 0회 사용 |
| 2. 관리번호 1열 + 잉크 알약 | 🟡 **부분** | mgmt_code 22회 표시되나 amber-deep(스카치 호박색) 사용 — 시안1의 잉크(`#0f172a`) 알약 아님 |
| 3. 표 sticky thead + zebra | 🟡 **부분** | thead sticky 4곳 적용. **단, spec 명시 "sticky 첫 3컬럼(No/부품번호/부품명)" 미적용** |
| 4. `?debug=1` 영역 라벨링 | ❌ **미적용** | `debug` 키워드 0회 |
| 5. 1100px 이하 반응형 | ❌ **미적용** | 1280px 한 군데(`@media (max-width:1280px)` line 108)만, 1100px 분기 없음 |
| 6. 빨강 ≤1개/페이지 | ❌ **위반** | `--knk-red` 27회 + 임의 빨강 30회 (`#fee2e2`, `#dc2626`, `#ef4444` 등) 누적 사용 |

---

## 2. 환경

```
워크트리: C:\Users\top00\JR\Claude 코드\.claude\worktrees\charming-yonath-a72046
브랜치 : claude/charming-yonath-a72046 (HEAD == main, diff 없음)
최신   : 7c173f6 v5H226z39 (2026-05-08 23:45 롤백 포인트)
대상   : KNK업무시스템구축/01_HAIST_WORKS/app/templates/project_detail.html
줄수   : 2,439줄 / inline style= 366회
```

> ⚠️ 발주서 표기 v5H226z53 vs 실제 z39 — 핫패치 진입 시 z40 부터 부여 예정.

> ℹ️ 디자인 핸드오프(`design_handoff_haist_works/`)는 worktree 외부에 위치 (실제 폴더에서 참조). 코드 수정은 worktree 내부에서 진행.

---

## 3. 상세 갭 (정직성 v3 — grep -n 직접 인용)

### 갭 1 — 시안1 신규 토큰 0회 사용 ❌
- `--qv-surface / --qv-ink / --qv-line` : `grep '--qv-' = 0`
- `--biz-t / --biz-m / --biz-e / --biz-c` : `grep '--biz-(t|m|e|c)' = 0`
- 현재 강조색: `amber` 계열 36회 (`var(--amber-deep)` 등) — 시안1과 색계열 충돌 가능

### 갭 2 — 관리번호 잉크 알약 미적용 🟡
- mgmt_code 22회 표시 (line 116, 118, 156, 159 등)
- **현행**: `<span style="font-family:monospace;color:var(--amber-deep);">{{ p.mgmt_code }}</span>` (line 118)
- **시안1**: 잉크색(`#0f172a` = `--qv-ink`) 알약 (pill) — 강한 가독성

### 갭 3 — sticky 첫 3컬럼 미적용 (spec 핵심) 🟡
- spec(`03-project.md` line 21): "**sticky 첫 3컬럼**: No / 부품번호 / 부품명"
- 현재 PARTS 표(line 794~): `position:sticky;top:0` (thead만)
- **좌측 sticky 없음** → 가로 스크롤 시 No/품명이 떠나감 → 28컬럼 데이터 식별 어려움

### 갭 4 — `?debug=1` 영역 라벨링 미적용 ❌
- `grep 'debug' = 0`
- 완료 기준 4항: "`?debug=1` 영역 라벨링" — 디버그 모드에서 영역명 오버레이 표시. 현재 없음.

### 갭 5 — 1100px 이하 반응형 미적용 ❌
- 현재(line 108): `@media (max-width: 1280px) { .detail-grid { grid-template-columns: 1fr; } }`
- 완료 기준 5항: "1100px 이하 반응형"
- 1100px 미만 분기 없음 → 작은 모니터/노트북에서 깨질 위험

### 갭 6 — 빨강 사용 과다 ❌
- `--knk-red` 27회 사용 (`grep '--knk-red' = 27`)
- 임의 빨강 hex: `#fee2e2` (line 814, 815), `dc2626 / ef4444 / f87171 / fca5a5` 등 **누적 30회**
- 완료 기준 6항: "빨강 ≤1개/페이지"
- **위반 폭이 가장 큼** — 색상 위계 재정립 필요

### 갭 7 — 임의 hex 컬러 산재 (보너스 발견)
- PARTS 헤더 chip: `#f5efde / #d4b75a / #b07a18 / #5a4a00 / #fff7e0 / #7c4a03 / #4a4030` (line 64~75, 96~102)
- HS/DUTY/VAT 컬럼: `#fef9e6 / #e0f2fe / #dcfce7 / #fee2e2 / #fef3c7` (line 808~816)
- inline `style=` 366회 — 토큰화 큰 리팩터 필요

---

## 4. 위험 / 회귀 우려

| # | 위험 | 영향도 | 비고 |
|---|---|---|---|
| R1 | PARTS 표 z11~z19 누적 핫패치 (가로 스크롤·sticky proxy·풀스크린·인라인 편집) | 🔴 **높음** | 손대면 회귀 위험 큼. `소중한 핫패치` 보호 |
| R2 | 호기 일괄 상태 적용 / 추가 발주 모달 / 엑셀 업로드 등 비즈니스 로직 | 🔴 **높음** | 디자인만 손대고 동작 안 깨야 함 |
| R3 | inline `style=` 366회 → 일괄 변환 시 누락 위험 | 🟡 중 | 점진 적용 권장 |
| R4 | `_v5_partials/` 미접촉 의무 | 🟢 낮음 | `chrome.html / styles.html / project_type_pill.html` 호출만 |

---

## 5. 핫패치 후보 (대표 결재 시 진입)

### z40 — 갭 4·5 즉시 적용 (저위험·고가치)
1. `?debug=1` 영역 라벨링: 본문 영역 4구역(헤더 / 메타 그리드 / SO 카드 / PARTS 표)에 `?debug=1` 시 라벨 띄우기
2. `@media (max-width: 1100px)` 분기 추가: 좌측 그리드 스택, PARTS chip 바 wrap

### z41 — 갭 1·2 (시안1 토큰 도입)
1. `_v5_partials/styles.html` 에 시안1 토큰 변수 추가는 **타 팀 영역** → 스타일은 본 페이지 `<style>` 안에서 매핑만
2. mgmt_code 표시 부분: 잉크색 알약 컴포넌트로 교체 (line 118 등)
3. amber-deep → `--biz-t` 또는 `--qv-ink-2` 로 점진 치환

### z42 — 갭 3 (sticky 첫 3컬럼)
1. PARTS 표 첫 3컬럼 `position:sticky; left:0/Npx; z-index:6` 추가
2. 가로 스크롤 시 No / 사진 / 품명 항상 보임

### z43 — 갭 6 (빨강 다이어트)
1. `#fee2e2` (관세 컬럼) → 호박색(amber pale) 또는 `--qv-surface-2`
2. `--knk-red` 27회 → 4~5회 (CTA·경고만) 로 축소
3. 빨강은 `?debug=1` 헬프에서 사용처 가시화

### z44~ — 갭 7 (인라인 → 토큰)
- 점진 적용. 보고 후 결정.

---

## 6. 권장 우선순위 (대표 결재 사항)

빅터 권장:
1. **z40 (debug + 1100px)** — 회귀 위험 거의 0, 즉시 진행 가능
2. **z42 (sticky 첫 3컬럼)** — spec 핵심, 사용자 체감 큼
3. **z41 (시안1 토큰)** — 점진 적용
4. **z43 (빨강 다이어트)** — 시각 영향 크니 z41 와 함께 결재

대표님 결재 후 z40 부터 단계 진행 / 단계마다 git push + BAT 갱신 + 보고.

---

## 7. 다음 단계 차단 / 결재 필요 사항

- [ ] **결재 1**: z40~z43 진행 순서 승인 (빅터 권장: 40 → 42 → 41+43)
- [ ] **결재 2**: 각 핫패치 결과 검증 후 다음 단계 진입할지 / 한꺼번에 4개 진입할지
- [ ] **결재 3**: 페이지 우선순위 1번(이 파일) 완료 후 2번(`sales_orders.html`) 진입 시점

---

**문의**: `_ORDERS/` 발주서 v2 / `99_DISPATCH/` 채널
**보고 위치**: `01B_HAIST_WORKS_매출영업/output/HANDOFF_TO_01_v1_진단.md` (본 문서)
