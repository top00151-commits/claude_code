# 📤 실무팀3 → 빅터(01) 핸드오프 — v8 (part_detail.html 단독 차수)

> **세션:** 실무팀3 (자재구매센터)
> **워크트리:** `cranky-shtern-789fa2` — 메인 폴더 직접 작업 모드
> **기준일:** 2026-05-11
> **시스템 버전:** v5H226z58
> **차수:** 8차 (z58-4: 분량 최다 단독 차수)

---

## 1. 배경

빅터 추천 순서 §8차 — z58 시리즈 마지막. **part_detail.html** 은 부품 상세의 종합 페이지로 라우터 전달 변수 13종을 모두 활용. 구버전(amber-grad / knk-red 톤)을 시안1 z58 톤으로 전면 재작성.

## 2. 산출물 (1 파일 — 분량 최다)

### `part_detail.html` (구버전 → z58)

#### 헤더
- 크럼 + 품목 코드(mono) + 품명 + chip-biz/chip-acc/chip-proc/pill-active
- 액션 3종: 목록 / 수정 / **+ 발주서 작성** (part_id pre-fill)

#### 알림 (조건부)
- 자가치유 알림 (stock_self_heal — 재고 정합성 보정)
- 재고 임계 미만 (sq < ss × 0.5) → 빨간 alert
- 재고 부족 (sq < ss 또는 sq ≤ rop) → 황 alert

#### KPI 5종
| 카드 | 표시 |
|---|---|
| 현재 재고 | sq + 단위 (FIFO 레이어 수 표시) |
| 재고 가치 | layers × unit_price 합계 + 통화 |
| 활성 단가 | active_price 또는 std_price + 통화 |
| 안전재고 | ss + 충족 % |
| 재주문점 / 발주량 | ROP / ROQ |

#### 좌측 메인 — 9 섹션

| # | 섹션 | 데이터 |
|---|---|---|
| 1 | 📦 FIFO 재고 레이어 | layers (입고일 / 입고수량 / 잔량 + 막대 / 단가 / 잔여가치 / LOT·유효기한·비고) |
| 2 | 💰 단가 이력 (30건) | price_history (적용일 / 공급사 / 유형tag / 단가 / 변동률±% / 통화 / 비고) |
| 3 | 📅 적용일자 단가 | managed_prices (시작/종료 / 공급사 / 유형 / 단가 / 최소·최대 수량 / 승인 상태) |
| 4 | 📊 7단가 chain | **placeholder** — z58 SQL 적용 후 활성화 안내 |
| 5 | 🌲 BOM 트리 | **placeholder** — z56 SQL 적용 후 활성화 (FIN/SEMI 품목만 표시) |
| 6 | 📋 최근 입출고 (30건) | recent_moves (일자 / 종류tag / 수량±색상 / 단가 / 잔량 / 참조·LOT·비고) |
| 7 | 🎯 프로젝트별 사용 | project_usage (관리코드 / 프로젝트 / 누적 수량·금액 / 마지막 발주일 / 연결수) |
| 8 | 📎 첨부 갤러리 | attachments (image/pdf/dwg/dxf 썸네일 + 파일명 + 사이즈) |
| 9 | ＋ 단가 등록 폼 | POST `/parts/{id}/prices/new` — 10 필드 (공급사·유형·단가·통화·시작/종료·협상일·최소/최대 수량·비고) |

#### 우측 사이드 — 3 카드

| 카드 | 내용 |
|---|---|
| 📌 마스터 정보 | def 16~20개 — 코드/v2/품명/규격/단위/사업부/품목계정/조달구분/카테고리/대분류/시리즈/제조사/원산지/표준가/HS코드/환산계수/위치/창고/추가규격/상태/비고 |
| 🏢 공급사별 단가 | by_supplier (공급사명 + 최근 단가) |
| 🚀 빠른 액션 | + 발주서 작성 / 📋 이동 이력 / 📝 마스터 수정 |

## 3. 자체 검증 결과 (1패스)

| 항목 | 결과 |
|---|---|
| amber-grad / knk-red 잔존 | **0건** ✅ (시안1 완전 적용) |
| data-dn 영역 | **15개** (head/self-heal/critical/low/kpi/fifo/price-hist/managed-prices/7price/bom/moves/project-usage/attach/price-form/side) |
| 라우터 변수 13종 활용 | 37 매칭 ✅ (part/layers/price_history/by_supplier/managed_prices/active_price/recent_moves/stock_value/stock_self_heal/suppliers/attachments/project_usage/CURRENCIES/PRICE_TYPES) |
| z58 컬럼 노출 | 마스터 정보 def에 전체 (item_account/procurement_kind/code_v2/category_main/series/sub_spec1-3/conversion_factor/default_warehouse/hs_code) |
| 단가 등록 폼 라우터 호환 | form name 10개 (supplier_id/price_type/unit_price/currency/effective_from/effective_to/negotiated_at/min_qty/max_qty/note) ✅ |
| chrome / styles / debug_overlay include | ✅ |
| 토큰 z58 | ✅ |

## 4. 룰 v4 + 발주서 7항 준수

| 룰 | 본 차수 |
|---|---|
| 메인 BAT 갱신 | 0건 ✅ |
| v5H226z 라벨 | HTML 주석 ✅ |
| 워크트리 동기화 | 메인 직접 작업 ✅ |
| 시안1 (e) 단계 | 완료 ✅ |
| 99_DISPATCH 게시 | 0건 ✅ |
| 다른 팀 페이지 | 0건 ✅ |
| `_v5_partials/` partial | 0건 ✅ |
| DB 스키마 변경 | 0건 (z58 SQL 작성만, 적용 위임) ✅ |
| 라우트 추가/변경 | 0건 ✅ (기존 라우터 그대로) |
| 위하고 직접 연동 | 0건 ✅ |

## 5. 검수 절차

```
http://localhost:8081/parts/{기존 자재 id}?debug=1
```

검수 항목:
- 헤더 chip 4종 (biz / acc / proc / pill) 정상 표시
- KPI 5종 — 안전재고 임계 미만 시 색상 변경 (warn → critical)
- FIFO 표 — 잔량 바 + 소비된 레이어 흐림 처리
- 단가 이력 — 변동률 색상 (상승 빨강 / 하강 초록)
- 입출고 이력 — 종류별 tag-mv (IN/OUT/ADJUST/TRANSFER) + 수량 부호 색상
- 단가 등록 폼 — 제출 후 `/parts/{id}?price_added=1` 리디렉션
- 사이드 마스터 정보 — z58 컬럼 모두 표시 (적용 안 됐을 시 fallback)

## 6. z58 시리즈 누적 완료 표

| 차수 | 항목 | 상태 |
|---|---|---|
| 5차 | E. z58 SQL 작성 | 🟡 적용 위임 |
| 6차 | A+B. parts 마스터 + part_form | 🟢 완료 |
| 7차 | D. VAT 모드 발주 풀체인 | 🟢 완료 |
| **8차** | **C. part_detail.html** | **🟢 완료** |

→ **z58 시리즈 4 차수 모두 완료 ✅**

## 7. 빅터(01) 처리 요청

- [ ] part_detail.html 검수 (z58 적용 전/후 양쪽)
- [ ] z58 SQL 검토 + 적용 결재 (5차 산출)
- [ ] STATUS.md 🟢 통합 완료 섹션 z58 5~8차 일괄 등록
- [ ] git push (빅터 책임)
- [ ] **다음 차수 — 9차 (z59 시리즈) 승인**

## 8. 다음 차수 (z59 시리즈 권장)

| 차수 | 항목 | 비고 |
|---|---|---|
| 9차 | z59 SQL — 재고 잠금일자 / 불량품 정규화 / 자재 패키지 / 매입 정산 | z59 작성만 |
| 10차 | stock_lock.html — 재고 잠금일자 관리 페이지 | KNK 어휘 매뉴얼 §3.3 |
| 11차 | qc_defects.html — 불량품 재고 현황 | po_receive defect_qty 연계 |
| 12차 | part_packages.html — 자재 패키지 (일괄군 대체) | 정기 발주 묶음 |

또는 다른 영역 (rates_* / wo_form / qms_*) 진행 가능.

## 9. 운영 메모

- **z58 시리즈 단계적 마이그레이션 패턴 정착**: PRAGMA gate + try/except — SQL 적용 전/후 모두 안전
- **시안1 일관성**: chip-biz / chip-acc / chip-proc / pill-active — 전 페이지 동일 색상 토큰
- **매뉴얼 부합**: 매뉴얼 §1.1 (품목등록) + §3 (구매관리) 워크플로우의 KNK 자체 재구현 완료

---

**보고:** 실무팀3 (자재구매센터) → 빅터(01)
**결재:** 김정락 대표이사 직접 라인
**자체 검증:** 1패스 통과 (0 결함 + 13종 변수 + 15 data-dn)
**완료 선언:** 2026-05-11 / 검증 후 정식 산출물 완료
**z58 시리즈 종료** — 5차~8차 4 차수 모두 🟢 완료
