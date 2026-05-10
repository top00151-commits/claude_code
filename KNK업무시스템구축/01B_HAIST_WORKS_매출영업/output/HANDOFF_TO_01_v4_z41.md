# 📋 실무팀2 → 빅터(01) 핸드오프 v4 — z41 핫패치 결과

> **발신**: 실무팀2 (매출영업센터)
> **수신**: 빅터 (01 통합실무팀)
> **결재**: 김정락 대표이사
> **작성일**: 2026-05-10
> **버전**: v5H226z42 → **v5H226z41** (※ 발주서 갭 번호 기준, D-1 진행 순서: z40→z42→z41→z43)
> **이전 보고**: `output/HANDOFF_TO_01_v3_z42.md`

---

## 1. 적용 범위

**z41 = 갭 1 + 갭 2 동시 적용** (D-1 결재 3순위, 시각 영향 큼)

| 갭 | 내용 | 상태 |
|---|---|---|
| 1 | 시안1 디자인 토큰 (`--qv-*`, `--biz-*`) 도입 | ✅ 변수 등록 + 부분 사용 |
| 2 | 관리번호 잉크 알약 (mgmt_code 메인 위치) | ✅ 적용 |

> ⚠️ 발주서 INSTRUCTIONS.md 라인 105 "디자인 토큰 (이미 적용됨)" 표기와 달리 실제 코드 검색 결과 **`--qv-*` / `--biz-*` 변수가 어떤 partial 에도 정의되지 않음**. 본 z41 에서 본 페이지 한정 처음 도입.

---

## 2. 변경 파일 (3건)

```
- KNK업무시스템구축/01_HAIST_WORKS/app/templates/project_detail.html  (+33줄)
  · 토큰 정의 11종 (qv 6 + biz 4 + mgmt-pill 컴포넌트)
  · mgmt_code 표시부 1곳 잉크 알약 변환 (line 118)
- KNK업무시스템구축/KNK_시작.bat                                       (LAST UPDATE → z41)
- KNK업무시스템구축/START.bat                                          (LAST UPDATE → z41)
```

---

## 3. 변경 상세

### 3-1. 시안1 토큰 도입 (갭 1)

`project_detail.html` 라인 6~21 신규 CSS:

```css
/* v5H226z41: 시안1 디자인 토큰 — 본 페이지 한정 도입 (다른 partial 미접촉, body 스코프) */
body {
  --qv-surface:   #ffffff;
  --qv-surface-2: #f7f8fa;
  --qv-line:      #eef0f4;
  --qv-ink:       #0f172a;
  --qv-ink-2:     #334155;
  --qv-ink-3:     #64748b;
  --biz-t: #c2410c;  /* New Equipment (Tech, 호박)  */
  --biz-m: #1e40af;  /* Maintenance/Service (네이비) */
  --biz-e: #6d28d9;  /* Export (자주)              */
  --biz-c: #047857;  /* Consumable (그린)           */
}
```

- 발주서 INSTRUCTIONS.md 라인 105~110 정의값 그대로
- `_STANDARDS/디자인_의뢰서_HAIST_WORKS_v1.md` 와 정합
- `body` 스코프 → 본 페이지 트리 전체에서 사용 가능, 다른 페이지 영향 0
- `_v5_partials/` 미접촉

### 3-2. mgmt_code 잉크 알약 (갭 2)

`project_detail.html` 라인 23~38 신규 컴포넌트 + 라인 144 변경:

```css
.mgmt-pill {
  display: inline-flex; align-items: center; justify-content: center;
  padding: 4px 12px; border-radius: 6px;
  background: var(--qv-ink); color: #ffffff;
  font-family: monospace; font-size: 16px; font-weight: 700;
  letter-spacing: 0.5px; line-height: 1.4;
  box-shadow: 0 1px 2px rgba(0,0,0,0.08);
}
.mgmt-pill.empty {
  background: var(--qv-surface-2); color: var(--qv-ink-3);
  box-shadow: none; border: 1px dashed var(--qv-line);
  font-weight: 500;
}
.mgmt-pill.sm { padding: 2px 8px;  font-size: 13px; }
.mgmt-pill.lg { padding: 6px 16px; font-size: 18px; }
```

```html
<!-- 변경 전 (라인 118) -->
<span style="font-family:monospace;color:var(--amber-deep);">{{ p.mgmt_code|default('—') }}</span>

<!-- 변경 후 (라인 144) -->
<span class="mgmt-pill lg{% if not p.mgmt_code %} empty{% endif %}" title="관리번호">{{ p.mgmt_code|default('—') }}</span>
```

**효과**:
- 메인 페이지 헤더 관리번호 → 흰 배경에 강한 잉크색 알약 (가독성 ↑)
- 미발급 상태 → 회색 점선 알약 (시각적 차이 명확)
- 발주서 UX 원칙 1번 "관리번호 우선" 강화

---

## 4. 변경 미적용 부분 (의도적 보류)

| 위치 | 이유 |
|---|---|
| crumbs (line 116) `<b>{{ p.mgmt_code }}</b>` | 빵부스러기 텍스트 — 알약화 시 시각 무게 과중 |
| 추가 발주 모달 (line 156, 159) | 모달 안 텍스트 — 알약화 시 모달 흐름 방해 |
| `--biz-t/m/e/c` 사업부 색상 사용 | **변수 등록만, 적용은 z44+ 점진** (project_type pill 등 기존 amber 강조와 충돌 위험) |
| amber-deep → biz 토큰 일괄 치환 | z44+ 점진 — 크게 손대면 회귀 위험 |

---

## 5. 검증

### 5-1. 정적 검증
- ✅ `body` 스코프 → 본 페이지 한정. 다른 페이지/partial 영향 0
- ✅ `_v5_partials/styles.html` 미접촉 (다른 팀 영역)
- ✅ `_v5_partials/project_type_pill.html` 미접촉 (사업부 pill 기존 amber 유지)
- ✅ `main.py` 라우트 / DB 스키마 / PARTS 백엔드 미접촉
- ✅ inline `style=` 367회 (1 추가, 1 제거 = 순증 0) — line 118의 inline style 제거되고 class 로 이전

### 5-2. 회귀 위험 점검
| 항목 | 영향 |
|---|---|
| z11~z19 누적 핫패치 | ⭕ 영향 없음 — 토큰 변수 추가만 |
| z40 `?debug=1` / 1100px | ⭕ 영향 없음 |
| z42 PARTS sticky 첫 3컬럼 | ⭕ 영향 없음 |
| `--amber / --amber-deep` 기존 사용 36회 | ⭕ 영향 없음 — 시안1 토큰은 신규 추가, 기존 amber 변수 보존 |
| 페이지 헤더 레이아웃 | ⚠️ mgmt_code lg 알약 (높이 ≈ 28px) → 기존 텍스트(≈ 22px)보다 6px 키 — page-title `gap:14px flex-wrap` 안에서 흡수, 줄바꿈 영향 없음 (1100px 분기 z40 호환) |

### 5-3. BAT 갱신 검증
```
KNK_시작.bat: REM LAST UPDATE / title / echo z42 → z41 (3곳)
START.bat:    REM LAST UPDATE / title / echo z42 → z41 (3곳)
```
※ **버전 번호 역행 (z42 → z41)**: D-1 진행 순서가 z40→z42→z41→z43 (발주서 갭 번호 기준)이라 발생. z43 진입 시 정상 정합 회복.

---

## 6. 사용자 체감 (대표 직접 확인 권장)

`/project/{id}` 접속 → 페이지 상단 관리번호:
- **이전**: amber-deep (호박색) monospace 텍스트
- **현재**: 검은 잉크색 알약 (배경 #0f172a, 흰 글자)
- **빈 상태**: 회색 점선 알약 ("—" 표시)

검증 권장 시나리오:
1. 관리번호 발급된 프로젝트 → 잉크색 알약 확인
2. 신규 프로젝트(미발급) → 회색 점선 알약 확인
3. 페이지 폭 1100px ~ 1440px 변동 → 알약 wrap 정상 동작
4. PARTS sticky / debug 라벨 / 호기 일괄 / 추가 발주 모달 — 정상 동작

---

## 7. 다음 단계 — z43 진입 결재 요청

**(D-1) 결재 순서대로** 다음은 **z43 (빨강 다이어트)** — D-1 마지막 단계.

- [ ] **결재 A**: z41 git push 승인
- [ ] **결재 B**: z43 진입 시점

z43 = 갭 6 (빨강 ≤ 1개) 적용:
- `--knk-red` 27회 → 4~5회 (CTA·경고만) 로 축소
- 임의 빨강 hex (`#fee2e2 / dc2626 / ef4444 / fee2e2 / fca5a5`) → `--qv-surface-2` 또는 호박색으로 치환
- PARTS 관세 컬럼 배경 (`#fee2e2`) → 호박 pale (`#fef3c7`)

---

## 8. 위험 / 한계

- ⚠️ 시안1 토큰을 본 페이지 한정으로만 도입 (다른 매출영업 페이지는 별도 z 단계). 향후 매출영업 30+ 페이지 적용 시 표준화 발주 필요.
- ⚠️ `--biz-*` 사업부 색상은 변수 등록만, 적용은 z44+ 점진 (현재 amber 시스템과 시각 충돌 방지).
- ⚠️ 발주서 INSTRUCTIONS.md "디자인 토큰 이미 적용됨" 표기는 **사실과 다름** — 본 z41 에서 처음 도입. 발주서 갱신 권장.

---

**문의**: `_ORDERS/` 발주서 v2 / `99_DISPATCH/` 채널
