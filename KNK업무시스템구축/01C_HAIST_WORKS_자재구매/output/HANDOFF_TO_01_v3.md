# 📤 실무팀3 → 빅터(01) 핸드오프 — v3 (룰 v4 정렬)

> **세션:** 실무팀3 (자재구매센터)
> **워크트리:** `cranky-shtern-789fa2` (메인 폴더 직접 작업 모드 — 대표 확인)
> **기준일:** 2026-05-10
> **시스템 버전:** v5H226z57 (z56 → +1, v4룰 정렬)
> **차수:** 3차 (룰 정합)

---

## 1. 이번 차수 요약

**룰 v4 ADDENDUM 정합 작업** — 코드 수정 X, 표준 정렬만.

| 항목 | 변경 |
|---|---|
| 영역 라벨 속성 | `data-region` → **`data-dn`** (debug_overlay.html 시스템 호환) |
| 디버그 body 클래스 | `body.is-debug` 자체 정의 → **debug_overlay 자동 처리** (`body.knk-debug`) |
| debug=1 영역 outline·tag CSS | 페이지별 자체 정의 → **debug_overlay partial 통합** |
| `_v5_partials/debug_overlay.html` include | 미적용 → **양 페이지 body 끝 include** |
| `data-dn-tone` 색 분류 | 미적용 → **green/blue/purple/amber 4톤 분류 적용** |

## 2. 변경 파일

```
01_HAIST_WORKS/app/templates/po_list.html         (data-dn 정렬 + debug_overlay include)
01_HAIST_WORKS/app/templates/logistics_home.html  (동일)
01C_HAIST_WORKS_자재구매/PROGRESS.md
01C_HAIST_WORKS_자재구매/output/HANDOFF_TO_01_v3.md  (본 파일)
01C_HAIST_WORKS_자재구매/output/_TO_01/2026-05-11_..._DONE_v4룰정렬.md
99_DISPATCH/2026-05-11_..._FYI_실무팀3_v4룰정렬.md
```

**라우트·DB·_v5_partials·메인 BAT 변경 없음** (룰 v4 정합 + 7항 금지).

## 3. v4 ADDENDUM 적용 결과

### 룰 1 — 메인 BAT 갱신
- 본 세션이 z54·z56 시점에 한 메인 BAT 갱신 → 빅터(01)가 z55·z58 정상화
- 본 차수부터 메인 BAT 미수정 ✅
- 자기 폴더 BAT (`01C_*.BAT`)은 자율 (다음 차수 도구 BAT 신설 가능)

### 룰 2 — `v5H226z` 라벨
- HTML 주석 `{# v5H226z57 ... #}` 사용 ✅ (사용자 노출 X)
- 페이지 인라인 표시 0건 ✅

### 룰 3 — 워크트리↔메인 동기화
- **본 워크트리(`cranky-shtern-789fa2`)는 메인 폴더 절대경로 직접 작업 모드** (대표 2026-05-10 확정)
- 옵션 A 복사 단계 불필요
- 차수 보고 = HANDOFF + chat 보고만 ✅

### 룰 4 — 시안1 (e) 단계 분할
- v1 토큰: 적용 완료 (Quiet Ops + chip-po + tbl-dense + filterbar)
- **v2 data-dn**: 본 차수 적용 ✅
- v3 빈 스켈레톤: po_list 빈 상태 + logistics_home placeholder 2종 적용
- v4 표준화: 다음 차수

## 4. data-dn 부착 카운트

### po_list.html
| dn 이름 | tone |
|---|---|
| po:head | (기본) |
| po:kpi | green |
| po:filter | blue |
| po:table | purple |
| po:empty | (기본) |

### logistics_home.html
| dn 이름 | tone |
|---|---|
| lh:head | (기본) |
| lh:kpi-1 | green |
| lh:kpi-2 | blue |
| lh:kpi-3 | green |
| lh:kpi-4 | green |
| lh:kpi-5 | (alert 시 기본) |
| lh:kpi-6 | amber |
| lh:flow | purple |
| lh:biz | blue |
| lh:near-receipt | amber |
| lh:low-stock-detail | amber |
| lh:quick-actions | green |

**총 17개 dn 라벨.** debug_overlay 자동 측정으로 `data-dn-size` 부착됨.

## 5. 검증 절차

브라우저 검증:
1. http://localhost:8081/po → 정상 동작 확인
2. http://localhost:8081/po?debug=1 → 5개 dn 라벨 (po:head/kpi/filter/table/empty) + 톤별 색
3. http://localhost:8081/logistics → 정상 동작 확인
4. http://localhost:8081/logistics?debug=1 → 12개 dn 라벨 + 톤별 색
5. **Ctrl+Shift+D** 단축키로 토글 동작 확인 (debug_overlay 표준 키)
6. 우측 하단 디버그 패널 표시 확인

## 6. 빅터(01) 검토 요청

- [ ] po_list.html / logistics_home.html v4룰 정렬 검수
- [ ] STATUS.md 갱신 (z57 정렬 차수 등록)
- [ ] 다음 차수 승인 — 3순위 `parts.html` 착수

## 7. 다음 차수 예정

**3순위 `parts.html` + `part_detail.html`** (부품 마스터)
- 위하고_자료 `품목등록.xlsx` 33컬럼 패턴 익명화 어휘로 KNK 변형 구현
- 시안1 부품 카드 그리드
- 마이그레이션 v5H226z56 적용 후 `code_v2` / `safety_stock` / `default_warehouse` 활용

## 8. 운영 메모

- **마이그레이션 SQL `v5H226z56_자재모듈표준v1.sql`** 적용 위임 상태 (본 세션 X)
- 빅터(01) 또는 대표 직접 라인에서 백업→적용→검증 권장
- SQL 헤더 §VERIFY / §ROLLBACK 가이드 동봉

---

**보고:** 실무팀3 (자재구매센터) → 빅터(01)
**결재:** 김정락 대표이사 직접 라인
**워크트리:** cranky-shtern-789fa2 — 메인 폴더 직접 작업 모드
