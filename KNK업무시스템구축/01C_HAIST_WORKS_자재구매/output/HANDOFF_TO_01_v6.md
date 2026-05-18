# 📤 실무팀3 → 빅터(01) 핸드오프 — v6 (자재모듈 표준 v2 도입)

> **세션:** 실무팀3 (자재구매센터)
> **워크트리:** `cranky-shtern-789fa2` — 메인 폴더 직접 작업 모드
> **기준일:** 2026-05-11
> **시스템 버전:** v5H226z58
> **차수:** 5차+6차 (자재모듈 표준 v2 — SQL + parts 마스터 + part_form 신규)

---

## 1. 배경

대표님 2026-05-11 직접 지시:
> "여기에 맞춰서 만들어보자.. 지금 구매실무자들이 쓰고 있는 방식이라 최대한 헛갈리지 않을려면 최대한 반영을 하는게 좋을것 같아."
> "저작권·특허·상표권 등 문제가 발생하는 것들은 항상 우리가 다시 고민해서 새롭게 적용해야 해."
> "너무 큰 범위라 빅터가 추천하는 순서대로 진행해보자."

→ 매뉴얼 분석 보고서(`_분석보고서_자재물류.md`) §5.1 1순위 4종을 IP 안전 어휘로 재해석 + 단계 분할 실행.

## 2. IP 안전 어휘 매핑 (z58 적용분)

| 참조 ERP A 용어 | KNK 어휘 (z58) |
|---|---|
| 수불통제일자 | **재고 잠금일자** (inventory_lock_dates) |
| 환산재고수량 | **재고 환산계수** (conversion_factor) |
| 다규격 | **추가 규격** (sub_spec1/2/3) |
| 적정재고량 | **안전재고** (safety_stock — z56 적용) |
| 매매군 | **자재 패키지** (z59 예정) |
| 매입마감 | **매입 정산** (z59 예정) |

회계학·세법 표준 용어는 그대로 차용: VAT 3종 / 품목계정 5종 / 조달구분 / FIFO / 재주문점 (ROP) / 재주문량 (ROQ).

## 3. 산출물 (5차 + 6차)

### 5차 — z58 마이그레이션 SQL
- **파일:** `migrations/v5H226z58_VAT_품목강화_v2.sql`
- **적용 위임:** 빅터(01) 또는 대표 직접 라인
- **선행:** v5H226z56

| 영역 | 변경 |
|---|---|
| purchase_orders | + vat_mode / tax_classification / supply_total / vat_total (4 컬럼) |
| po_items | + supply_amount / vat_amount / defect_qty / warehouse_code (4 컬럼) |
| parts | + conversion_factor / sub_spec1/2/3 (4 컬럼) — reorder_point·reorder_qty 는 자동 마이그레이션 사전 존재 |
| **신규 테이블** | inventory_lock_dates (재고 잠금일자) |
| 백필 UPDATE | po_items.supply_amount=amount, vat_amount=amount×0.1 / purchase_orders.supply_total·vat_total 헤더 동기화 |

### 6차 — parts 마스터 + part_form 신규 + 백엔드 확장

#### A. `part_form.html` (신규 작성, z58)
- **7섹션**: 기본정보 / 분류 / 단가 / 재고관리 / 추가규격 / 문서출력명 / 기타
- **사이드 카드 3종**: 요약 / 입력 가이드 / 첨부 / (편집 시) 위험 작업
- **칩 선택 UI**: 사업부 4종(T/M/E/C) + 품목계정 5종(RAW/SUB/SEMI/FIN/CONS) + 조달구분 3종(PURCHASE/MAKE/OUTSOURCE) + 활성여부 2종

#### B. `parts.html` (z57 → z58 보강)
- 표 컬럼 추가: **"품목계정" (5번째 자리)** — chip-acc 5색 (a-raw/a-sub/a-semi/a-fin/a-cons)
- CSS `chip-acc` 추가 (모노 폰트 + 색상 매핑)
- 총 컬럼 11개 (코드/자재명/규격제조사/사업부/**품목계정**/분류/표준가/단위/재고/안전재고/상태)

#### C. `database.py` parts_create / parts_update — PRAGMA gate 확장
- **핵심 안전망**: `PRAGMA table_info(parts)` 로 실제 존재 컬럼만 INSERT/UPDATE
- z58 SQL 미적용 환경에서도 base 14 컬럼은 정상 동작 (z58 13 확장 컬럼은 skip)
- z58 SQL 적용 후 자동으로 ext 컬럼까지 처리

#### D. `main.py` POST /parts/new + POST /parts/{pid}/edit
- Form 파라미터 14 → **27 (13 신규)**
- 신규: item_account / procurement_kind / category_main / category_series / reorder_point / reorder_qty / conversion_factor / sub_spec1/2/3 / tax_invoice_name / trade_invoice_name / default_warehouse / hs_code

## 4. 자체 검증 결과 (1패스)

### 5차 SQL
- ❌ **결함 1 발견** — reorder_point/reorder_qty 가 database.py:1971-1974 자동 마이그레이션과 중복
- ✅ **즉시 수정** — z58 SQL 에서 두 컬럼 제거, 인덱스만 유지

### 6차 백엔드 + 프론트
- ✅ part_form.html name 속성 20개 매칭
- ✅ main.py Form 시그니처 13 신규 매칭 (라우터 2개 × 3 키워드 = 6 카운트)
- ✅ database.py 27개 매칭 (parts_create + parts_update + ext_pairs)
- ✅ parts.html chip-acc CSS + tbody 분기 9개 매칭
- ✅ PRAGMA gate 동적 컬럼 — z58 미적용 환경 호환 안전

## 5. 룰 v4 + 발주서 7항 준수 확인

| 룰 | 본 차수 |
|---|---|
| 1. 메인 BAT 갱신 | 0건 ✅ |
| 2. v5H226z 라벨 | HTML 주석만 ✅ |
| 3. 워크트리 동기화 | 메인 직접 작업 (옵션 A 불필요) ✅ |
| 4. 시안1 (e) 단계 | v1 토큰 + v2 data-dn 적용 ✅ |
| 5. 99_DISPATCH 게시 | 0건 ✅ |

| 발주서 7항 | 본 차수 |
|---|---|
| 다른 팀 페이지 | 0건 ✅ |
| `_v5_partials/` 공통 partial | 0건 ✅ |
| **DB 스키마 변경 (직접 적용)** | **0건** ✅ (z58 SQL 작성만, 적용 위임) |
| 라우트 추가/삭제 | 0건 ✅ (기존 라우트의 Form 파라미터 확장만 — 자재구매 영역) |
| 위하고 ERP 직접 연동 | 0건 (참조만, 익명화 100%) ✅ |

## 6. 검수 절차

### 라우터 동작 확인 (z58 SQL 미적용 상태)
```
http://localhost:8081/parts                          ← 목록 (chip-acc는 빈 칸 표시)
http://localhost:8081/parts/new?debug=1              ← 새 품목 등록 (신규 13 필드 입력 가능)
http://localhost:8081/parts/{id}/edit?debug=1        ← 품목 수정
```
- PRAGMA gate로 미적용 환경에서도 신규 필드는 silently skip → 400 에러 X
- 적용 후에는 chip-acc / 5종 라디오 / 7단가 가이드 모두 활성화

### z58 SQL 적용 후
```
1) DB 백업: copy "01_HAIST_WORKS/data/haist_works.db" "data/backup/haist_works_pre_z58.db"
2) sqlite3 .read 01C_HAIST_WORKS_자재구매/migrations/v5H226z58_VAT_품목강화_v2.sql
3) §VERIFY 7개 쿼리로 검증
4) 신규 필드 입력 테스트
```

## 7. 빅터(01) 처리 요청

- [ ] z58 SQL 검토 + 적용 결재
- [ ] part_form / parts 동작 검수 (z58 적용 전/후 양쪽)
- [ ] STATUS.md `🟢 통합 완료` 섹션 z58 6차 등록
- [ ] git push (빅터 책임)
- [ ] 메인 BAT z59 갱신
- [ ] **다음 차수 (7차) 승인 — D 항목 VAT 모드 발주 풀체인 (po_form / po_detail / po_receive 일괄)**

## 8. 다음 차수 (z58 시리즈)

| 차수 | 항목 | 비고 |
|---|---|---|
| **7차** | D. VAT 모드 발주 풀체인 — po_form / po_detail / po_receive | 영향 큼 |
| **8차** | C. part_detail.html — FIFO 레이어 + 7단가 chain + BOM 트리 + 첨부 + 프로젝트 사용량 | 분량 최다 |
| **9차** | z59 — 재고 잠금일자 / 불량 정규화 / 자재 패키지 | z59 SQL |

## 9. 운영 메모

- **자체 검증 룰 적용 성과**: 5차 SQL에서 중복 컬럼 결함 1건 사전 발견 → 즉시 수정
- **PRAGMA gate 도입**: SQL 적용 전/후 환경 모두 안전 동작 (점진적 마이그레이션 지원)
- **칩 디자인 일관성**: chip-biz(T/M/E/C) ← chip-acc(RAW/SUB/SEMI/FIN/CONS) 동일 패턴

---

**보고:** 실무팀3 (자재구매센터) → 빅터(01)
**결재:** 김정락 대표이사 직접 라인
**자체 검증:** 1패스 통과 (결함 1건 즉시 수정)
**완료 선언:** 2026-05-11 / 검증 후 정식 산출물 완료
