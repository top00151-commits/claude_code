-- ============================================================
-- v5H226z56 — 자재모듈 표준 v1 마이그레이션 SQL
-- 작성: 2026-05-10 / 실무팀3 (자재구매센터)
-- 결재: 2026-05-10 김정락 대표이사 5건 일괄 승인
-- 적용 권한: 빅터(01) 또는 대표 직접 라인 (실무팀3 직접 적용 금지)
-- 대상 DB: SQLite (`01_HAIST_WORKS/data/haist_works.db` 가정)
-- ============================================================
--
-- 본 마이그레이션은 _STANDARD_자재모듈기준_v1.md §6.2 갭 분석 결과 중
-- 결재 승인된 항목만 반영. 다음 5건:
--
--   ① PO_STATUSES enum 확장 — Python 상수만 (DB CHECK 없음, ALTER 불요)
--   ② 단가 마스터 2종 신설 (item_prices, vendor_item_prices)
--   ③ stock_movements.kind 세분화 (입고 3종 + 출고 3종 → kind_detail 컬럼)
--   ④ 작업지시(WO) — work_orders 이미 존재. BOM만 신설 (bom_items)
--   ⑤ 품목코드 체계 v2 (parts.code_v2 컬럼 추가, 병행 운영)
--
-- 추가 보강:
--   ⑥ stock_movements.loss_rate (출고 로스율, 자재출고 표준 컬럼)
--
-- ============================================================
-- 안전 적용 가이드
-- ============================================================
-- 1) 현재 DB 백업:
--      copy "01_HAIST_WORKS/data/haist_works.db" "data/backup/haist_works_pre_z56.db"
--
-- 2) SQL 단위 실행 (sqlite3 CLI 또는 DB Browser for SQLite):
--      .open 01_HAIST_WORKS/data/haist_works.db
--      .read 01C_HAIST_WORKS_자재구매/migrations/v5H226z56_자재모듈표준v1.sql
--
-- 3) 트랜잭션 실패 시 롤백 SQL: 본 파일 끝 §ROLLBACK
--
-- 4) 적용 후 검증 쿼리: 본 파일 끝 §VERIFY
-- ============================================================

BEGIN TRANSACTION;

-- ────────────────────────────────────────────────────────────
-- ② 단가 마스터 2종
-- ────────────────────────────────────────────────────────────

-- ② -1. 품목별 단가 마스터 (매입 7단가 + 매출 7단가)
--    1품목 = 1행. 거래처 무관 기본 단가.
--    적용 우선순위: 거래처별 단가 > 품목별 단가 chain (정상가 → 설정가1 → 2 → 3 → 4)
CREATE TABLE IF NOT EXISTS item_prices (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    part_id         INTEGER NOT NULL UNIQUE REFERENCES parts(id) ON DELETE CASCADE,

    -- 매입 (Purchase) 7단가
    buy_upper       REAL,                 -- 상한가
    buy_normal      REAL,                 -- 정상가
    buy_lower       REAL,                 -- 하한가
    buy_set1        REAL,                 -- 설정가1
    buy_set2        REAL,                 -- 설정가2
    buy_set3        REAL,                 -- 설정가3
    buy_set4        REAL,                 -- 설정가4

    -- 매출 (Sales) 7단가
    sell_upper      REAL,
    sell_normal     REAL,
    sell_lower      REAL,
    sell_set1       REAL,
    sell_set2       REAL,
    sell_set3       REAL,
    sell_set4       REAL,

    currency        TEXT DEFAULT 'KRW',
    note            TEXT,
    is_active       INTEGER DEFAULT 1,
    created_at      TEXT DEFAULT (datetime('now','localtime')),
    updated_at      TEXT DEFAULT (datetime('now','localtime'))
);
CREATE INDEX IF NOT EXISTS idx_item_prices_part ON item_prices(part_id);


-- ② -2. 거래처 × 품목 단가 마스터 (Override)
--    동일 품목이라도 거래처별 단가 차등 가능 (예: 광원전기 16,500 / 우리산전 18,000)
--    참조 ERP A 화면 모델 차용 (KNK 자체 어휘로 변형)
CREATE TABLE IF NOT EXISTS vendor_item_prices (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    supplier_id     INTEGER NOT NULL REFERENCES suppliers(id) ON DELETE CASCADE,
    part_id         INTEGER NOT NULL REFERENCES parts(id)     ON DELETE CASCADE,

    -- 매입 측 단가 코드 (11~17 매입 / 21~27 매출)
    buy_price_code  INTEGER,              -- 11=상한가, 12=정상가, 13=하한가, 14~17=설정가1~4
    buy_price       REAL,
    sell_price_code INTEGER,              -- 21~27 매출 측
    sell_price      REAL,

    -- 7단가 옵션 (필요 시 모두 보관, 우선순위 chain은 백엔드)
    buy_upper       REAL,
    buy_normal      REAL,
    buy_lower       REAL,
    buy_set1        REAL,
    buy_set2        REAL,
    buy_set3        REAL,
    buy_set4        REAL,
    sell_upper      REAL,
    sell_normal     REAL,
    sell_lower      REAL,
    sell_set1       REAL,
    sell_set2       REAL,
    sell_set3       REAL,
    sell_set4       REAL,

    currency        TEXT DEFAULT 'KRW',
    valid_from      TEXT,                 -- YYYY-MM-DD (가격 유효 시작)
    valid_to        TEXT,                 -- YYYY-MM-DD (가격 유효 종료)
    note            TEXT,
    is_active       INTEGER DEFAULT 1,
    created_at      TEXT DEFAULT (datetime('now','localtime')),
    updated_at      TEXT DEFAULT (datetime('now','localtime')),

    UNIQUE(supplier_id, part_id, valid_from)
);
CREATE INDEX IF NOT EXISTS idx_vip_supplier ON vendor_item_prices(supplier_id);
CREATE INDEX IF NOT EXISTS idx_vip_part ON vendor_item_prices(part_id);
CREATE INDEX IF NOT EXISTS idx_vip_active ON vendor_item_prices(is_active);


-- ────────────────────────────────────────────────────────────
-- ③ stock_movements 입출고 종류 세분화 + ⑥ 로스율
-- ────────────────────────────────────────────────────────────
-- 기존 kind: IN / OUT / ADJUST / TRANSFER (4종)
-- 신규 kind_detail: 회계 자동 분개 키
--   IN_PURCHASE      구매입고  (외부 발주서 입고)
--   IN_PRODUCTION    생산입고  (자체 완제품·반제품)
--   IN_OUTSOURCE     외주제품입고
--   OUT_SALES        판매출고  (완제품·상품 매출)
--   OUT_PRODUCTION   생산출고  (자재 투입)
--   OUT_OUTSOURCE    외주자재출고 (외주가공처 자재 지급)
--   ADJUST_OVER      실사 증가 조정
--   ADJUST_SHORT     실사 감소 조정
--   TRANSFER_IN      창고 이동 (수신측)
--   TRANSFER_OUT     창고 이동 (발신측)
--
-- 기존 행은 NULL 유지 (마이그레이션 후 일괄 백필 권장)

ALTER TABLE stock_movements ADD COLUMN kind_detail TEXT;
CREATE INDEX IF NOT EXISTS idx_sm_kind_detail ON stock_movements(kind_detail);

-- 출고 로스율 (출고 라인의 자재 손실 비율, 0~1)
ALTER TABLE stock_movements ADD COLUMN loss_rate REAL DEFAULT 0;


-- ────────────────────────────────────────────────────────────
-- ④ BOM 트리 신설 (work_orders 는 이미 존재)
-- ────────────────────────────────────────────────────────────
-- BOM = 완제품/반제품을 만들기 위한 자재 구성표.
-- 트리 구조: parent_part_id 가 자기 자신을 참조하는 self-FK
-- effective_date 로 BOM 버전 관리

CREATE TABLE IF NOT EXISTS bom_items (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    parent_part_id      INTEGER NOT NULL REFERENCES parts(id) ON DELETE CASCADE,
    child_part_id       INTEGER NOT NULL REFERENCES parts(id),

    qty_per_parent      REAL NOT NULL DEFAULT 1,          -- 부모 1개당 자식 수량 (EA당)
    unit                TEXT DEFAULT 'EA',
    loss_rate           REAL DEFAULT 0,                    -- BOM 라인별 표준 로스율
    process_seq         INTEGER DEFAULT 0,                 -- 공정 순서 (1·2·3)
    process_name        TEXT,                              -- 공정명 (외주 등)

    -- BOM 종류 (참조 ERP A의 3종 BOM)
    bom_type            TEXT DEFAULT 'ENG'
                        CHECK(bom_type IN ('ENG','ROUTE','PROJECT')),
                        -- ENG=Engineering BOM / ROUTE=공정경로 BOM / PROJECT=프로젝트 BOM

    -- 버전 / 효력
    version             INTEGER DEFAULT 1,
    effective_from      TEXT,                              -- YYYY-MM-DD
    effective_to        TEXT,                              -- YYYY-MM-DD (NULL=현행)
    is_active           INTEGER DEFAULT 1,

    -- 프로젝트 BOM 인 경우 프로젝트 매핑
    project_id          INTEGER REFERENCES projects(id),

    -- 공급사 권장 (외주 공정의 경우)
    suggested_supplier_id INTEGER REFERENCES suppliers(id),

    note                TEXT,
    created_by          INTEGER REFERENCES users(id),
    created_at          TEXT DEFAULT (datetime('now','localtime')),
    updated_at          TEXT DEFAULT (datetime('now','localtime'))
);
CREATE INDEX IF NOT EXISTS idx_bom_parent ON bom_items(parent_part_id);
CREATE INDEX IF NOT EXISTS idx_bom_child ON bom_items(child_part_id);
CREATE INDEX IF NOT EXISTS idx_bom_active ON bom_items(is_active);
CREATE INDEX IF NOT EXISTS idx_bom_project ON bom_items(project_id);
CREATE INDEX IF NOT EXISTS idx_bom_type ON bom_items(bom_type);


-- ────────────────────────────────────────────────────────────
-- ⑤ 품목코드 체계 v2 (parts.code_v2)
-- ────────────────────────────────────────────────────────────
-- 기존 part_no 유지 (UNIQUE 그대로) + 신규 code_v2 병행 운영
-- 형식: KNK-{대분류2자}-{시리즈1자}-{6자리연번}
--   예: KNK-PT-K-000713  (Parts·K시리즈·713번)
--      KNK-RM-D-000018  (Raw Material·D시리즈·18번)
-- 백엔드 함수가 자동 생성 (database.py:gen_part_code_v2)

ALTER TABLE parts ADD COLUMN code_v2 TEXT;
ALTER TABLE parts ADD COLUMN category_main TEXT;            -- 대분류 (PT/RM/FG 등)
ALTER TABLE parts ADD COLUMN category_series TEXT;          -- 시리즈 (D/K/J/P 등)
ALTER TABLE parts ADD COLUMN procurement_kind TEXT;         -- 조달구분: PURCHASE/MAKE/OUTSOURCE
ALTER TABLE parts ADD COLUMN item_account TEXT;             -- 품목계정: RAW/SEMI/FIN/MERCH/CONS
ALTER TABLE parts ADD COLUMN tax_invoice_name TEXT;         -- 세금계산서 출력명
ALTER TABLE parts ADD COLUMN trade_invoice_name TEXT;       -- 거래명세서 출력명
ALTER TABLE parts ADD COLUMN default_warehouse TEXT;        -- 기본 입출고 창고
ALTER TABLE parts ADD COLUMN safety_stock REAL DEFAULT 0;   -- 적정재고량
ALTER TABLE parts ADD COLUMN hs_code TEXT;                  -- HS코드 (수출입)

CREATE UNIQUE INDEX IF NOT EXISTS idx_parts_code_v2 ON parts(code_v2) WHERE code_v2 IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_parts_category_main ON parts(category_main);
CREATE INDEX IF NOT EXISTS idx_parts_procurement ON parts(procurement_kind);
CREATE INDEX IF NOT EXISTS idx_parts_item_account ON parts(item_account);


-- ────────────────────────────────────────────────────────────
-- ⑦ purchase_order_items.loss_rate (PO 라인 로스율 옵션, ⑥의 PO 측 보강)
-- ────────────────────────────────────────────────────────────
ALTER TABLE po_items ADD COLUMN loss_rate REAL DEFAULT 0;


-- ────────────────────────────────────────────────────────────
-- ⑧ 마이그레이션 메타 (선택)
-- ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS schema_migrations (
    version         TEXT PRIMARY KEY,
    applied_at      TEXT DEFAULT (datetime('now','localtime')),
    note            TEXT
);
INSERT OR IGNORE INTO schema_migrations(version, note) VALUES
  ('v5H226z56', '실무팀3 자재모듈 표준 v1 — 단가 마스터 2종 + BOM + kind_detail + code_v2 + loss_rate');


COMMIT;


-- ============================================================
-- §VERIFY 검증 쿼리 (적용 후 수동 실행)
-- ============================================================
-- SELECT version, applied_at, note FROM schema_migrations WHERE version='v5H226z56';
--
-- 신규 테이블 존재 확인:
-- SELECT name FROM sqlite_master WHERE type='table'
--   AND name IN ('item_prices','vendor_item_prices','bom_items','schema_migrations');
--
-- 신규 컬럼 존재 확인:
-- PRAGMA table_info(stock_movements);   -- kind_detail, loss_rate 있어야 함
-- PRAGMA table_info(parts);             -- code_v2, category_main 등 있어야 함
-- PRAGMA table_info(po_items);          -- loss_rate 있어야 함
--
-- 인덱스 확인:
-- SELECT name FROM sqlite_master WHERE type='index'
--   AND name LIKE 'idx_item_prices%' OR name LIKE 'idx_vip%' OR name LIKE 'idx_bom_%';

-- ============================================================
-- §ROLLBACK 롤백 SQL (응급 시)
-- ============================================================
-- ※ SQLite 는 ALTER TABLE DROP COLUMN 미지원 (3.35+ 부터 지원되나 KNK Python 환경 확인 필요).
--   안전한 롤백은 v5H226z56 적용 직전 백업 (haist_works_pre_z56.db)에서 복구.
--
-- 백업 복구:
--   1) 서비스 정지
--   2) copy "data/backup/haist_works_pre_z56.db" "01_HAIST_WORKS/data/haist_works.db"
--   3) 서비스 재기동
--
-- 신규 테이블만 제거하는 부분 롤백 (컬럼은 그대로):
--   DROP TABLE IF EXISTS item_prices;
--   DROP TABLE IF EXISTS vendor_item_prices;
--   DROP TABLE IF EXISTS bom_items;
--   DELETE FROM schema_migrations WHERE version='v5H226z56';
-- ============================================================
