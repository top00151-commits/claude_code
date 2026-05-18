# 📋 실무팀2 → 빅터(01) 핸드오프 v3 — z42 핫패치 결과

> **발신**: 실무팀2 (매출영업센터)
> **수신**: 빅터 (01 통합실무팀)
> **결재**: 김정락 대표이사
> **작성일**: 2026-05-10
> **버전**: v5H226z40 → **v5H226z42**
> **이전 보고**: `output/HANDOFF_TO_01_v2_z40.md`

---

## 1. 적용 범위

**z42 = 갭 3 적용** (D-1 결재 2순위, spec 핵심·사용자 체감 가장 큼)

| 갭 | 내용 | 상태 |
|---|---|---|
| 3 | 표 sticky 첫 3컬럼 (`#` / 사진 / 품명) — `03-project.md` line 21 명시 | ✅ 적용 |

---

## 2. 변경 파일 (3건)

```
- KNK업무시스템구축/01_HAIST_WORKS/app/templates/project_detail.html  (+18줄)
- KNK업무시스템구축/KNK_시작.bat                                       (LAST UPDATE → z42)
- KNK업무시스템구축/START.bat                                          (LAST UPDATE → z42)
- KNK업무시스템구축/01B_HAIST_WORKS_매출영업/output/HANDOFF_TO_01_v3_z42.md  ← 본 문서
- KNK업무시스템구축/01B_HAIST_WORKS_매출영업/PROGRESS.md                     (z42 누적)
```

---

## 3. 변경 상세

### 3-1. PARTS 표 첫 3컬럼 좌측 sticky (갭 3)

`project_detail.html` 라인 142~159 신규 CSS:

```css
/* v5H226z42: PARTS 28컬럼 표 — 좌측 첫 3컬럼 sticky (#·사진·품명) */
table.so-units.parts-excel thead th:nth-child(1),
table.so-units.parts-excel tbody td:nth-child(1) { position: sticky; left: 0;     z-index: 4; }
table.so-units.parts-excel thead th:nth-child(2),
table.so-units.parts-excel tbody td:nth-child(2) { position: sticky; left: 30px;  z-index: 4; }
table.so-units.parts-excel thead th:nth-child(3),
table.so-units.parts-excel tbody td:nth-child(3) { position: sticky; left: 90px;  z-index: 4; }

/* sticky 셀 배경 — zebra/hover/row-collapsed 동작 보존 */
table.so-units.parts-excel tbody td:nth-child(-n+3) { background: #ffffff; }
table.so-units.parts-excel tbody tr:nth-child(even) td:nth-child(-n+3) { background: #fafafa; }
table.so-units.parts-excel tbody tr:hover td:nth-child(-n+3) { background: #fef9c3; }

/* 행/열 sticky 교차 시 thead 우선 */
table.so-units.parts-excel thead th:nth-child(-n+3) { z-index: 6; }

/* 우측 경계 음영 — 좌측 고정·우측 스크롤 영역 구분 */
table.so-units.parts-excel thead th:nth-child(3),
table.so-units.parts-excel tbody td:nth-child(3) { box-shadow: 2px 0 4px -2px rgba(0,0,0,0.18); }
```

### 3-2. 컬럼 폭 / 좌측 누적 위치
| nth | 컬럼 | 폭 | left |
|---|---|---|---|
| 1 | `#` (행번호) | 30px | 0 |
| 2 | 사진 | 60px | 30px |
| 3 | 품명 | 200px | 90px |
| 4~ | (스크롤 시작) | — | 290px+ |

---

## 4. 검증

### 4-1. 정적 검증
- ✅ `parts-excel` 클래스 셀렉터 한정 → 일반 SO 표(2컬럼/4컬럼)는 영향 없음
- ✅ 컬럼 그룹 hide 클래스(`.hide-basic`)와 호환 — basic 그룹 hide 시 첫 3컬럼 모두 사라지고 sticky 자연 비활성
- ✅ 행 접기 `tr.row-collapsed` 호환 — 첫 2 셀만 보이는 모드에서 sticky 유지
- ✅ z-index 충돌 없음: thead 6 > sticky body 4 > 일반 td 0 / sticky 가로 proxy 8 > sticky thead 5 (기존 z40 미만)

### 4-2. 회귀 위험 점검
| 항목 | 영향 |
|---|---|
| z11~z19 누적 핫패치 (가로 스크롤 wrapper / 풀스크린) | ⭕ 영향 없음 — sticky 셀이 wrapper 안 정상 동작 |
| 컬럼 폭 조정 핸들 (`.col-resize-handle`) | ⚠️ **사용자가 좌측 3컬럼 폭 조정 시 left 값 깨질 수 있음** — 추후 z45+ 보정 필요 (현재는 readme 안내) |
| zebra/hover/row-collapsed | ⭕ 명시 보존 처리 |
| `?debug=1` 라벨 (z40) | ⭕ 영향 없음 |
| 1100px 반응형 (z40) | ⭕ 영향 없음 |

### 4-3. BAT 갱신 검증
```
KNK_시작.bat: REM LAST UPDATE / title / echo z40 → z42 (3곳)
START.bat:    REM LAST UPDATE / title / echo z40 → z42 (3곳)
```

---

## 5. 사용자 체감 (대표 직접 확인 권장)

`/project/{PARTS 프로젝트 ID}` 접속 → PARTS 표 가로 스크롤 → 좌측 `#·사진·품명` 3컬럼 항상 보임. 28컬럼 데이터 식별 즉시 가능.

**검증 권장 시나리오**:
1. PARTS 프로젝트 진입 (`shipment_form == PARTS` 또는 `so_type == PARTS_EXPORT`)
2. PARTS 표 우측 스크롤 → 좌측 3컬럼 고정 확인
3. zebra 행 색상 유지 확인
4. 행 hover 시 노란 강조 확인 (`#fef9c3`)
5. 행 접기 (`row-toggle`) 시 좌측 2셀 유지 확인
6. 컬럼 그룹 토글 (`기본` 클릭 OFF/ON) 시 정상 동작 확인

---

## 6. 다음 단계 — z41 진입 결재 요청

**(D-1) 결재 순서대로** 다음은 z41 (시안1 토큰 + 잉크 알약).

- [ ] **결재 A**: z42 git push 승인
- [ ] **결재 B**: z41 진입 시점 (지금 / 검증 후 / 대기)

빅터 권장:
1. push 즉시 (변경 격리됨, 회귀 위험 낮음)
2. z41 바로 진입 — 단, **z41은 시각 영향 큼** (강조색 amber → 잉크색 변경) → 보고 후 검증 권장

---

## 7. 위험 / 한계

- ⚠️ **컬럼 폭 조정 핸들**: 사용자가 첫 3컬럼 폭 변경 시 sticky `left` 하드코딩 값(30/90/290) 어긋남. 향후 z45 보정 발주 검토.
- ⚠️ 디자인 핸드오프 spec(`03-project.md` line 21) "No / 부품번호 / 부품명" 과 실제 첫 3컬럼 "# / 사진 / 품명" 차이 — **실제 DB 컬럼 정렬에 따라 sticky 적용**. spec과 컬럼명 일부 다름 (실제 코드 기준 적용).

---

**문의**: `_ORDERS/` 발주서 v2 / `99_DISPATCH/` 채널
