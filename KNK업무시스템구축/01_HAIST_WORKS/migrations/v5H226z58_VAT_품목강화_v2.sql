-- ============================================================
-- v5H226z58 — 자재모듈 표준 v2 (VAT + 품목 강화 + 재고 잠금)
-- 작성: 2026-05-11 / 실무팀3 (자재구매센터)
-- 결재: 대표 일임 (2026-05-11 "빅터 추천 순서대로 진행")
-- 적용 권한: 빅터(01) 또는 대표 직접 라인 (실무팀3 직접 적용 금지)
-- 대상 DB: SQLite (`01_HAIST_WORKS/data/haist_works.db` 가정)
-- 선행 마이그레이션: v5H226z56 (자재모듈 표준 v1)
-- ============================================================
--
-- 본 마이그레이션 목적:
--   참조 SaaS ERP A 매뉴얼(자재물류) 분석 결과 도출된 실무 필수 7항목 중 4종을 도입.
--   IP 안전 원칙: 회계학·세법 표준 용어는 차용 / ERP A 특유 명칭은 KNK 어휘로 변환.
--
-- 본 차수 반영 항목:
--   ① VAT 모드 (헤더 + 라인) — 매뉴얼 §3.2, 매입세무 표준
--   ② 공급가액 / 부가세 분리 — 매뉴얼 §3.2 자동계산 공식
--   ③ 불량 갯수 (입고처리 라인) — 매뉴얼 §3.3
--   ④ 라인별 창고 코드 — 매뉴얼 §3.3 (다중창고 대비)
--   ⑤ 품목 마스터 보강 — 환산계수·재주문점·재주문수량·추가규격 3종
--   ⑥ 재고 잠금일자 신설 — 매뉴얼 §3.3 "수불통제일자" 의 KNK 자체 구현
--
-- 다음 차수 (z59) 예정:
--   ⑦ 불량품 이력 정규화 (stock_defects 신규)
--   ⑧ 자재 패키지 (part_packages — 매뉴얼 "일괄매매군" 대체어)
--   ⑨ 매입 정산 단계 (po_settlements — 매뉴얼 "매입마감" 대체어)
--
-- ============================================================
-- IP 안전 어휘 매핑 (참조 ERP A → KNK)
-- ============================================================
-- 수불통제일자  →  재고 잠금일자 (inventory_lock_dates)
-- 매매군        →  자재 패키지   (part_packages, z59 예정)
-- 매입마감      →  매입 정산     (po_settlements, z59 예정)
-- 다규격        →  추가 규격     (sub_spec1~3)
-- 환산재고수량  →  재고 환산계수 (conversion_factor)
-- 적정재고량    →  안전재고      (safety_stock — z56 적용 완료)
-- ============================================================
-- 안전 적용 가이드
-- ============================================================
-- 1) 현재 DB 백업:
--      copy "01_HAIST_WORKS/data/haist_works.db" "data/backup/haist_works_pre_z58.db"
--
-- 2) z56 선행 마이그레이션 확인:
--      SELECT version FROM schema_migrations WHERE version='v5H226z56';
--    → 행 없으면 z56 먼저 적용 (`v5H226z56_자재모듈표준v1.sql`)
--
-- 3) SQL 단위 실행 (sqlite3 CLI 또는 DB Browser for SQLite):
--      .open 01_HAIST_WORKS/data/haist_works.db
--      .read 01C_HAIST_WORKS_자재구매/migrations/v5H226z58_VAT_품목강화_v2.sql
--
-- 4) 트랜잭션 실패 시 롤백: 본 파일 끝 §ROLLBACK
--
-- 5) 적용 후 검증: 본 파일 끝 §VERIFY
-- ============================================================

BEGIN TRANSACTION;


-- ────────────────────────────────────────────────────────────
-- ① + ② VAT 모드 + 공급가액/부가세 분리 — purchase_orders 헤더
-- ────────────────────────────────────────────────────────────
-- vat_mode 3종 (매뉴얼 §3.2 표준):
--   'vat_excluded'  VAT 미포함 — 수량×단가=공급가액, 부가세=공급가액×10%
--   'vat_included'  VAT 포함   — 입력금액÷1.1=공급가액
--   'vat_none'      VAT 없음   — 영세/면세 (부가세=0)
--
-- tax_classification 4종 (매입 과세구분):
--   'taxable'    과세
--   'zero_rated' 영세 (Local L/C·구매확인서)
--   'exempt'     면세
--   'other'      기타
--
-- 기존 발주는 vat_mode='vat_excluded' / tax='taxable' 백필 (KNK 현행 가정)

ALTER TABLE purchase_orders ADD COLUMN vat_mode TEXT DEFAULT 'vat_excluded';
ALTER TABLE purchase_orders ADD COLUMN tax_classification TEXT DEFAULT 'taxable';
ALTER TABLE purchase_orders ADD COLUMN supply_total REAL DEFAULT 0;  -- 헤더 합계 (공급가액)
ALTER TABLE purchase_orders ADD COLUMN vat_total    REAL DEFAULT 0;  -- 헤더 합계 (부가세)

CREATE INDEX IF NOT EXISTS idx_po_vat_mode ON purchase_orders(vat_mode);
CREATE INDEX IF NOT EXISTS idx_po_tax ON purchase_orders(tax_classification);


-- ────────────────────────────────────────────────────────────
-- ② + ③ + ④ po_items 라인 보강
-- ────────────────────────────────────────────────────────────
-- supply_amount  라인 공급가액 (vat_mode 에 따라 계산)
-- vat_amount     라인 부가세
-- defect_qty     불량 갯수 (입고처리 시 별도 입력, 재고 미반영)
-- warehouse_code 라인별 창고 코드 (다중창고 대비, 매뉴얼 §3.3)

ALTER TABLE po_items ADD COLUMN supply_amount  REAL DEFAULT 0;
ALTER TABLE po_items ADD COLUMN vat_amount     REAL DEFAULT 0;
ALTER TABLE po_items ADD COLUMN defect_qty     REAL DEFAULT 0;
ALTER TABLE po_items ADD COLUMN warehouse_code TEXT;

CREATE INDEX IF NOT EXISTS idx_poitem_defect ON po_items(defect_qty);
CREATE INDEX IF NOT EXISTS idx_poitem_wh ON po_items(warehouse_code);

-- 기존 라인 백필: amount = quantity × unit_price 였으므로
--   vat_excluded 가정 → supply_amount = amount, vat_amount = amount × 0.1
UPDATE po_items
   SET supply_amount = COALESCE(amount, 0),
       vat_amount    = ROUND(COALESCE(amount, 0) * 0.1, 0)
 WHERE supply_amount = 0 AND vat_amount = 0;

-- 헤더 supply_total / vat_total 도 동기화
UPDATE purchase_orders
   SET supply_total = (
       SELECT COALESCE(SUM(supply_amount), 0) FROM po_items
        WHERE po_items.po_id = purchase_orders.id
   ),
       vat_total    = (
       SELECT COALESCE(SUM(vat_amount), 0) FROM po_items
        WHERE po_items.po_id = purchase_orders.id
   )
 WHERE supply_total = 0 AND vat_total = 0;


-- ────────────────────────────────────────────────────────────
-- ⑤ parts 마스터 보강 (4 컬럼 + 인덱스)
-- ────────────────────────────────────────────────────────────
-- conversion_factor  재고 환산계수 (매뉴얼 §1.1 "환산재고수량")
--                    예: 1박스=100개 — 입고 1박스 입력 → 재고 100EA로 환산
-- sub_spec1/2/3      추가 규격 (매뉴얼 §1.1 "다규격")
--                    예: 색상·재질·길이 등 main spec 외 보조 분류
--
-- ※ reorder_point / reorder_qty 는 database.py:1971-1974 (사이클 51, 2026-04-27)
--   자동 마이그레이션으로 이미 존재. 본 z58 에서는 인덱스만 추가.
-- ※ safety_stock 도 database.py:1966-1967 자동 마이그레이션으로 이미 존재
--   (z56 의 ALTER TABLE safety_stock 은 사실상 no-op 또는 에러 가능 — z58 에서는 미반복)

ALTER TABLE parts ADD COLUMN conversion_factor REAL DEFAULT 1;
ALTER TABLE parts ADD COLUMN sub_spec1         TEXT;
ALTER TABLE parts ADD COLUMN sub_spec2         TEXT;
ALTER TABLE parts ADD COLUMN sub_spec3         TEXT;

CREATE INDEX IF NOT EXISTS idx_parts_reorder ON parts(reorder_point);


-- ────────────────────────────────────────────────────────────
-- ⑥ 재고 잠금일자 (KNK 자체 구현 — 매뉴얼 "수불통제일자" 의 IP-safe 대체어)
-- ────────────────────────────────────────────────────────────
-- 목적: 마감 또는 재고평가 후 특정 일자 이전의 입출고 입력·삭제·수정 차단
-- 매뉴얼은 단일 전역 일자만 보유 / KNK 는 창고별 잠금 지원 (확장성)
-- 잠금 범위: locked_until 이전 (포함) 의 모든 stock_movements + po_receive 차단
-- 해제: is_active=0 또는 unlock_reason 기재 후 새 행 추가

CREATE TABLE IF NOT EXISTS inventory_lock_dates (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    warehouse_code  TEXT,                                      -- NULL = 전 창고 일괄
    locked_until    TEXT NOT NULL,                             -- YYYY-MM-DD (포함)
    lock_reason     TEXT DEFAULT 'PERIOD_CLOSE',
                    -- PERIOD_CLOSE=월마감/INVENTORY_VAL=재고평가/AUDIT=실사/MANUAL=수동
    is_active       INTEGER DEFAULT 1,
    note            TEXT,
    created_by      INTEGER REFERENCES users(id),
    created_at      TEXT DEFAULT (datetime('now','localtime')),

    -- 해제 (선택)
    unlocked_at     TEXT,
    unlock_reason   TEXT,
    unlocked_by     INTEGER REFERENCES users(id)
);

CREATE INDEX IF NOT EXISTS idx_inv_lock_until  ON inventory_lock_dates(locked_until);
CREATE INDEX IF NOT EXISTS idx_inv_lock_wh     ON inventory_lock_dates(warehouse_code);
CREATE INDEX IF NOT EXISTS idx_inv_lock_active ON inventory_lock_dates(is_active);


-- ────────────────────────────────────────────────────────────
-- ⑦ 마이그레이션 메타
-- ────────────────────────────────────────────────────────────
INSERT OR IGNORE INTO schema_migrations(version, note) VALUES
  ('v5H226z58', '실무팀3 자재모듈 표준 v2 — VAT 모드 + 공급가액/부가세 분리 + 불량갯수 + parts 보강 5종 + 재고 잠금일자');


COMMIT;


-- ============================================================
-- §VERIFY 검증 쿼리 (적용 후 수동 실행)
-- ============================================================
-- 1. 마이그레이션 등록 확인:
-- SELECT version, applied_at, note FROM schema_migrations WHERE version IN ('v5H226z56','v5H226z58') ORDER BY version;
--
-- 2. 헤더 신규 컬럼 확인:
-- PRAGMA table_info(purchase_orders);
--   → vat_mode, tax_classification, supply_total, vat_total 4개 존재
--
-- 3. 라인 신규 컬럼 확인:
-- PRAGMA table_info(po_items);
--   → supply_amount, vat_amount, defect_qty, warehouse_code 4개 존재
--
-- 4. parts 신규 컬럼 확인:
-- PRAGMA table_info(parts);
--   → conversion_factor, sub_spec1, sub_spec2, sub_spec3 4개 신규 존재
--   → reorder_point, reorder_qty, safety_stock 은 자동 마이그레이션 사전 존재
--
-- 5. 백필 정합성 (랜덤 발주 1건):
-- SELECT id, po_number,
--        total_amount, supply_total, vat_total,
--        ROUND(supply_total + vat_total, 0) AS calc_total
--   FROM purchase_orders
--  ORDER BY id DESC LIMIT 3;
--   → calc_total 이 total_amount 와 ±10% 이내여야 정상 (vat_excluded 백필 가정)
--
-- 6. 라인 백필:
-- SELECT id, po_id, quantity, unit_price, amount, supply_amount, vat_amount
--   FROM po_items
--  WHERE supply_amount > 0
--  ORDER BY id DESC LIMIT 5;
--
-- 7. 재고 잠금 테이블:
-- SELECT name FROM sqlite_master WHERE type='table' AND name='inventory_lock_dates';
-- SELECT count(*) FROM inventory_lock_dates;  -- 초기 0행 정상


-- ============================================================
-- §ROLLBACK 롤백 SQL (응급 시)
-- ============================================================
-- SQLite 는 ALTER TABLE DROP COLUMN 미지원 (3.35+ 부터 지원).
-- 안전 롤백: 백업 복구 권장.
--
-- 백업 복구 (권장):
--   1) 서비스 정지
--   2) copy "data/backup/haist_works_pre_z58.db" "01_HAIST_WORKS/data/haist_works.db"
--   3) 서비스 재기동
--
-- 부분 롤백 (테이블만 제거, 컬럼은 그대로):
--   DROP TABLE IF EXISTS inventory_lock_dates;
--   DELETE FROM schema_migrations WHERE version='v5H226z58';
--
-- 백필 데이터만 초기화 (컬럼 유지):
--   UPDATE po_items SET supply_amount=0, vat_amount=0;
--   UPDATE purchase_orders SET supply_total=0, vat_total=0;
-- ============================================================
