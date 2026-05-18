# 📤 실무팀3 → 빅터(01) 핸드오프 — v7 (VAT 모드 발주 풀체인)

> **세션:** 실무팀3 (자재구매센터)
> **워크트리:** `cranky-shtern-789fa2` — 메인 폴더 직접 작업 모드
> **기준일:** 2026-05-11
> **시스템 버전:** v5H226z58
> **차수:** 7차 (z58-3: VAT 모드 발주 풀체인 적용)

---

## 1. 배경

빅터 추천 순서 §7차 — VAT 모드를 발주 풀체인(po_form / po_detail / po_receive) 3페이지 + 백엔드(database.py / main.py)에 일괄 적용.

매뉴얼 §3.2 표준 공식 차용 (회계학·세법 표준 — IP 무관):
```
vat_excluded:  공급가액 = qty×price,        부가세 = 공급가액 × 10%
vat_included:  공급가액 = (qty×price)/1.1,  부가세 = base - 공급가액
vat_none:      공급가액 = qty×price,        부가세 = 0
```

## 2. 산출물 (5 파일)

### A. po_form.html (z58 보강)
- VAT 모드 select 3종 + 과세구분 select 4종 (기본정보 섹션)
- 합계 라벨 동적 변경 (vat_mode 따라):
  - "공급가액 (VAT 미포함)" / "공급가액 (VAT 포함분 환산)" / "공급가액 (VAT 없음)"
- JS `recalcTotals()` — 3종 분기 + 자동 재계산 (라인 입력 + VAT 모드 변경 시 즉시 갱신)

### B. po_detail.html (z58 보강)
- 발주 정보 def 영역에 4줄 추가:
  - VAT 모드 (라벨화: 미포함/포함/없음)
  - 과세구분 (라벨화: 과세/영세/면세/기타)
  - 공급가액 (조건부: z58 supply_total 존재 시)
  - 부가세 (조건부)
- z58 미적용 환경에서도 fallback 정상 (default + is defined check)

### C. po_receive.html (z58 보강)
- 발주 정보 카드에 4 항목 추가 (po-info grid)
- 입고 시 발주 헤더 VAT 따라가므로 표시만 (입력 X)

### D. database.py 확장
```python
def _po_vat_calc(qty, price, vat_mode):
    # VAT 3종 공식 일관 계산
def _po_backfill_vat(c, po_id, vat_mode, tax_class):
    # PRAGMA gate — z58 컬럼 존재 시에만 헤더·라인 백필
```
- `po_create` 끝부분에 `_po_backfill_vat()` 호출 추가
- `po_update` 끝부분에 `_po_backfill_vat()` 호출 추가

### E. main.py 라우터 확장
- `po_new_submit` header dict — vat_mode + tax_classification 키 추가
- `po_edit_submit` header dict — 동일

## 3. 자체 검증 결과 (1패스)

| 영역 | Grep 매칭 |
|---|---|
| database.py | 21 (헬퍼 2개 + po_create/update 호출 + 도큐먼트) |
| main.py | 4 (2 라우터 × 2 키) |
| po_form.html | 4 (vat_mode + hdrVatMode + tax_classification + 주석) |
| po_detail.html | 5 (vat_mode + tc + 라벨화 + supply_total + vat_total) |
| po_receive.html | 5 (vat_mode + tc + 라벨화 + supply_total + vat_total) |
| **합계** | **39** (legacy 4 제외) |

z58 토큰 일관 적용 6 페이지 (po_form/po_detail/po_receive/parts/part_form/sales_outstanding) — 자재 영역 5개 + 매출 영역 1개(타팀).

## 4. 룰 v4 + 발주서 7항 준수

| 항목 | 본 차수 |
|---|---|
| 메인 BAT 갱신 | 0건 ✅ |
| v5H226z 라벨 (HTML 주석) | OK ✅ |
| 워크트리 동기화 | 메인 직접 작업 ✅ |
| 시안1 (e) 단계 | 유지 ✅ |
| 99_DISPATCH 게시 | 0건 ✅ |
| 다른 팀 페이지 | 0건 ✅ |
| `_v5_partials/` partial | 0건 ✅ |
| DB 스키마 직접 적용 | 0건 ✅ (z58 SQL 적용 위임, PRAGMA gate 안전) |
| 라우트 추가 | 0건 ✅ (기존 2 라우터의 header dict 확장만) |
| 위하고 직접 연동 | 0건 ✅ |

## 5. PRAGMA gate 핵심 안전망 재확인

- z58 SQL **적용 전**: 라우터에서 vat_mode/tax_classification 받아 _po_backfill_vat() 호출 → PRAGMA로 컬럼 부재 감지 → silently skip → 정상 동작
- z58 SQL **적용 후**: 자동으로 supply_amount/vat_amount/supply_total/vat_total 백필 활성화

## 6. 검수 절차

```
http://localhost:8081/po/new?debug=1                ← VAT 모드 select + 동적 합계 라벨
http://localhost:8081/po/{id}/edit?debug=1          ← 동일 (편집)
http://localhost:8081/po/{id}?debug=1               ← 발주 정보 def에 VAT 4줄
http://localhost:8081/po/{id}/receive?debug=1       ← 발주 정보 카드에 VAT 4항목
```

검수 항목:
- VAT 모드 변경 시 라벨이 즉시 변경
- 라인 입력 시 공급가액/부가세 자동 재계산
- z58 SQL 적용 후 supply_total / vat_total 실제 저장 검증

## 7. 빅터(01) 처리 요청

- [ ] 3 페이지 + 백엔드 검수
- [ ] STATUS.md `🟢 통합 완료` 섹션 z58 7차 등록
- [ ] git push (빅터 책임)
- [ ] **다음 차수 (8차) 승인 — C. part_detail.html (FIFO 레이어 + 7단가 chain + BOM 트리 + 첨부 + 프로젝트 사용량)**

## 8. 다음 차수 (z58 시리즈 잔여)

| 차수 | 항목 | 비고 |
|---|---|---|
| **8차** | C. part_detail.html — FIFO 레이어 + 7단가 chain + BOM 트리 + 첨부 + 프로젝트 사용량 | 분량 최다 단독 차수 |
| **9차** | z59 시작 — 재고 잠금일자 / 불량품 정규화 / 자재 패키지 | z59 SQL 신규 |

## 9. 운영 메모

- **VAT 계산 일관성**: 헬퍼 함수 `_po_vat_calc()` 로 백엔드 + JS 양쪽 동일 공식 적용
- **PRAGMA gate 패턴**: 6차(parts) + 7차(po) 모두 동일 패턴 — 점진적 마이그레이션 표준 정착

---

**보고:** 실무팀3 (자재구매센터) → 빅터(01)
**결재:** 김정락 대표이사 직접 라인
**자체 검증:** 1패스 통과 (39 매칭 정합)
**완료 선언:** 2026-05-11 / 검증 후 정식 산출물 완료
