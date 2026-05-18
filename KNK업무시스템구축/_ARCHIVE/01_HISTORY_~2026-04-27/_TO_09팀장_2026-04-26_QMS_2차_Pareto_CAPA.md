# 01 → 09 회신 — QMS 2차 (Pareto 차트 + CAPA 라이프사이클 심화)

**작성**: 빅터 (01 메인) · **일시**: 2026-04-26 · **사이클**: 09 발주 → 01 작업(현재) → 04 회귀 대기 → 00 감사 → 99

---

## 1. Pareto 차트 (CSS gradient bar + 인라인 SVG cumulative line)

`GET /qms/pareto` 신규. issues.root_cause 를 SUBSTR(1,40) 그룹화 → 빈도 정렬 + 누적 % 계산. 80/20 컷오프 자동 산출 (`p80_cutoff_idx` / `p80_pct_of_causes`). 표는 80% 누적까지 핑크 배경 강조 (#FEF7F7), 그라디언트 막대 (#A5282C → #EF6C00). 별도 SVG 패널에 누적선 polyline + 80% 가이드 라인 (점선) + 점(circle r=3). **외부 차트 라이브러리 0건** — 모든 좌표 Jinja `loop.index0 * step` + `round(2)` 로 계산.

## 2. CAPA 라이프사이클 (DRAFT → APPROVED → IN_PROGRESS → COMPLETED → VERIFIED)

`corrective_actions` / `preventive_actions` 각 +6 컬럼 ALTER ADD (idempotent · CHECK 제약 없는 TEXT DEFAULT 'DRAFT'):
`lifecycle_status` / `approved_by` / `approved_at` / `verified_by` / `verified_at` / `effectiveness_note`. 인덱스 2개 (`idx_ca_lifecycle` / `idx_pa_lifecycle`). 기존 `status` (OPEN/IN_PROGRESS/DONE/CANCELLED) 무수정 — 1차 호환 보존.

## 3. 라우트 신규 9개

`@app\.(get|post)\("/qms` grep:
```
6272 GET  /qms                              (1차)
6313 GET  /qms/issues/{iid}/sla             (1차)
6326 POST /qms/issues/{iid}/corrective       (1차)
6352 POST /qms/issues/{iid}/preventive       (1차)
6379 GET  /qms/recurrence                   (1차)
6476 GET  /qms/pareto                       ★2차 신규
6509 GET  /qms/capa                         ★2차 신규
6604 POST /qms/corrective/{cid}/approve     ★2차 신규 (admin/leader)
6611 POST /qms/corrective/{cid}/start       ★2차 신규
6618 POST /qms/corrective/{cid}/complete    ★2차 신규
6625 POST /qms/corrective/{cid}/verify      ★2차 신규 (admin/leader · effectiveness_note)
6634 POST /qms/preventive/{pid}/approve     ★2차 신규 (admin/leader)
6641 POST /qms/preventive/{pid}/complete    ★2차 신규
6648 POST /qms/preventive/{pid}/verify      ★2차 신규 (admin/leader)
```
QMS 트랙 누적: 5(1차) + 9(2차) = **14 라우트**. `_qms_capa_guard()` 신규 (admin/ceo/executive/leader 만 승인·검증). `_capa_transition()` 헬퍼로 가드/UPDATE/감사로그 단일 경로.

## 4. CAPA KPI 정직성 (`_capa_kpi(c)`)

- **평균 closure (일)**: created_at(DRAFT) → completed_at 차이의 평균. 파싱 실패 시 skip. 계산식: `sum(days)/len(days)` round 1자리. `kpi.sample_size` 로 표본 크기 명시 — 0건이면 0 반환 (가짜값 X).
- **검증 비율 (%)**: `VERIFIED / (COMPLETED+VERIFIED) * 100`. 분모 0이면 0 반환.
- **부서별 분포**: issues.owner_team_id → teams.name LEFT JOIN. NULL 부서는 `(미지정)` 으로 명시. Top 10.
- **외부 numpy/pandas/scipy 0건** — pure Python `datetime.strptime` + 산술만.

## 5. 변경 라인 분리 (정직성 정책 5항)

**Python**: `database.py` 5982 → 6028 (**+46**) · `main.py` 6612 → 6849 (**+237**). **HTML**: `qms_pareto.html` **+101 신규** · `qms_capa.html` **+131 신규** · `qms_dashboard.html` 80→82 (**+2** nav 링크). **CSS**: `static/style.css` **본 사이클 미접촉** (net 0).
**본 사이클 합계**: **+517줄** (Python 283 + HTML 234).

## 6. 누적 라인 (3 카테고리)

| 카테고리 | 라인 |
|---|---|
| 본 사이클 (QMS 2차) | **+517** |
| QMS 트랙 1+2차 합 | +452(1차) + 517(2차) = **+969** |
| 세션 전체 누적 | 약 +861(이전) + 517(본) = **약 +1,378** |

## 7. 핫패치 G1~G5 보존 grep — 직접 인용

```
static/style.css:2253  핫패치 G1·G5 영향 없음 (margin-right 시프트만)
static/style.css:4613  v2 본체(4287~4574) 무수정 · 핫패치 G1~G5 보존
static/style.css:4731  v2 본체(4287~4574) 무수정 · 핫패치 G1~G5 보존
static/style.css:4903  v2 본체(4287~4574) 무수정 · 핫패치 G1~G5 보존
static/style.css:5130  v2 본체(4287~4574) 무수정 · 핫패치 G1~G5 보존
static/style.css:5371  v2 본체(4287~4574) 무수정 · 핫패치 G1~G5 보존
static/style.css:5548  v2 본체(L4287~L4574) 미접촉 / 핫패치 G1~G5 영향 없음
```
style.css 본 사이클 미접촉 → **G1~G5 7/7 마커 보존**.

## 8. BAT 갱신 (절대준수)

- `START.bat` L3 LAST UPDATE / L7 title / L13 echo → `2026-04-26 QMS-2차-Pareto-CAPA`
- `KNK_시작.bat` L3 / L7 / L14 동일 갱신

## 9. 자기검증 (정직성 v2 7항)

- [x] G1~G5 7/7 grep 보존 (style.css 미접촉)
- [x] v2 본체(L4287~L4574) 미접촉
- [x] 외부 차트 라이브러리 0건 / numpy 0건 (datetime + 산술만)
- [x] DB idempotent (ALTER ADD PRAGMA 검사 + CREATE INDEX IF NOT EXISTS)
- [x] `_qms_capa_guard()` / `_capa_transition()` 단일 정의 (7 라이프사이클 라우트 일관)
- [x] 1차 status 컬럼 무수정 — 호환 보존
- [x] BAT 2개 갱신 (3행 × 2파일)

## 10. 다음 사이클 예고 — QMS 3차 (안)

- ISO 9001 8.7 부적합품 보고서 PDF 출력 (XLSX 스킬과 동일 정책 — 외부 의존 0)
- Pareto 카테고리 필터 (severity / owner_team)
- CAPA SLA — verify 까지 14일 임박 알림 (하이웍스 푸시)
