"""
v5H226z104 (2026-05-16) — 워크플로우 레고 빌더 DB 마이그레이션

추가 테이블:
  1) countries_master              국가 마스터 (확장 가능)
  2) workflow_nodes_master         업무 노드 마스터 (45개)
  3) workflow_templates            5개 빠른시작 시나리오
  4) workflow_template_nodes       템플릿별 포함 노드
  5) project_workflow              프로젝트 워크플로우 인스턴스 (8문항 마법사 응답 포함)
  6) project_workflow_nodes        조립된 노드 (체크리스트 단위)
  7) project_workflow_edges        노드 의존관계
  8) ic_invoice_pairs              IC 양방향 페어 매칭

projects 테이블에 마법사 메타 컬럼 3개 추가:
  - customer_country (TEXT)
  - po_entity        (TEXT, 'KR'|'VN')
  - ship_entity      (TEXT, 'KR'|'VN')

대표 결재: 2026-05-16 (c) 1+2차 통합 모드 GO
"""

import sqlite3
import os


SCHEMA_SQL = r"""
-- 1. 국가 마스터
CREATE TABLE IF NOT EXISTS countries_master (
  code         TEXT PRIMARY KEY,         -- ISO2 (KR, VN, IN, ID, MY, CN, US, ...)
  name_ko      TEXT NOT NULL,
  name_en      TEXT NOT NULL,
  region       TEXT,                     -- 'asia','sea','europe', etc.
  is_active    INTEGER NOT NULL DEFAULT 1,
  display_order INTEGER NOT NULL DEFAULT 99,
  created_at   TEXT DEFAULT (datetime('now','localtime'))
);

-- 2. 업무 노드 마스터 (45개)
CREATE TABLE IF NOT EXISTS workflow_nodes_master (
  node_code      TEXT PRIMARY KEY,       -- 예: 'sales.quote', 'design.bom', 'ic.kr_sale_to_vn'
  category       TEXT NOT NULL,          -- 'sales','design','purchase','production','qa','logi','finance','ic','as'
  title_ko       TEXT NOT NULL,
  title_en       TEXT,
  description    TEXT,
  default_dept   TEXT,                   -- '영업','설계','자재구매','생산','품질','물류','회계','법인'
  est_hours      INTEGER DEFAULT 0,
  is_ic          INTEGER NOT NULL DEFAULT 0,  -- 1=IC 거래 노드 (양방향 페어 후보)
  ic_direction   TEXT,                        -- 'kr_to_vn','vn_to_kr','sell','buy'
  display_order  INTEGER NOT NULL DEFAULT 99,
  is_active      INTEGER NOT NULL DEFAULT 1,
  created_at     TEXT DEFAULT (datetime('now','localtime'))
);

-- 3. 빠른시작 템플릿 (5개 시나리오)
CREATE TABLE IF NOT EXISTS workflow_templates (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  code         TEXT UNIQUE NOT NULL,    -- 's1_domestic','s2_kr_export','s3_vn_export', ...
  title_ko     TEXT NOT NULL,
  description  TEXT,
  customer_country_hint TEXT,
  po_entity_hint        TEXT,
  ship_entity_hint      TEXT,
  display_order INTEGER NOT NULL DEFAULT 99,
  is_active    INTEGER NOT NULL DEFAULT 1,
  created_at   TEXT DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS workflow_template_nodes (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  template_id INTEGER NOT NULL,
  node_code   TEXT NOT NULL,
  seq         INTEGER NOT NULL,
  is_optional INTEGER NOT NULL DEFAULT 0,
  FOREIGN KEY (template_id) REFERENCES workflow_templates(id) ON DELETE CASCADE,
  FOREIGN KEY (node_code)   REFERENCES workflow_nodes_master(node_code)
);

-- 4. 프로젝트 워크플로우 인스턴스
CREATE TABLE IF NOT EXISTS project_workflow (
  id                INTEGER PRIMARY KEY AUTOINCREMENT,
  project_id        INTEGER NOT NULL,
  template_id       INTEGER,                  -- 시작점 템플릿 (선택)
  -- 마법사 8문항 응답
  customer_country  TEXT,                     -- Q1
  po_entity         TEXT,                     -- Q2 'KR'|'VN'
  mech_design_split TEXT,                     -- Q3 'KR'|'VN'|'KR+VN'
  elec_design_split TEXT,                     -- Q4 'KR'|'VN'|'KR+VN'
  sw_design_split   TEXT,                     -- Q5 'KR'|'VN'|'KR+VN'
  processing_loc    TEXT,                     -- Q6 'KR'|'VN'|'OUT' (외주)
  ship_entity       TEXT,                     -- Q7 'KR'|'VN'
  setup_loc         TEXT,                     -- Q8 국가코드 또는 'NONE'
  -- 메타
  status            TEXT NOT NULL DEFAULT 'draft',  -- 'draft','active','done','cancelled'
  created_by        INTEGER,
  created_at        TEXT DEFAULT (datetime('now','localtime')),
  updated_at        TEXT DEFAULT (datetime('now','localtime')),
  FOREIGN KEY (project_id)  REFERENCES projects(id) ON DELETE CASCADE,
  FOREIGN KEY (template_id) REFERENCES workflow_templates(id)
);

CREATE INDEX IF NOT EXISTS ix_pwf_project ON project_workflow(project_id);

-- 5. 조립된 노드 (체크리스트 단위)
CREATE TABLE IF NOT EXISTS project_workflow_nodes (
  id             INTEGER PRIMARY KEY AUTOINCREMENT,
  workflow_id    INTEGER NOT NULL,
  node_code      TEXT NOT NULL,
  seq            INTEGER NOT NULL,
  assigned_entity TEXT,                  -- 'KR'|'VN' (분담 시)
  assigned_user_id INTEGER,
  status         TEXT NOT NULL DEFAULT 'pending',  -- 'pending','in_progress','done','skipped','blocked'
  due_date       TEXT,
  done_at        TEXT,
  note           TEXT,
  created_at     TEXT DEFAULT (datetime('now','localtime')),
  FOREIGN KEY (workflow_id) REFERENCES project_workflow(id) ON DELETE CASCADE,
  FOREIGN KEY (node_code)   REFERENCES workflow_nodes_master(node_code)
);

CREATE INDEX IF NOT EXISTS ix_pwfn_workflow ON project_workflow_nodes(workflow_id);
CREATE INDEX IF NOT EXISTS ix_pwfn_status   ON project_workflow_nodes(status);

-- 6. 노드 의존관계 (DAG)
CREATE TABLE IF NOT EXISTS project_workflow_edges (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  workflow_id  INTEGER NOT NULL,
  from_node_id INTEGER NOT NULL,
  to_node_id   INTEGER NOT NULL,
  edge_type    TEXT NOT NULL DEFAULT 'precede',  -- 'precede','handoff','ic_pair'
  FOREIGN KEY (workflow_id)  REFERENCES project_workflow(id) ON DELETE CASCADE,
  FOREIGN KEY (from_node_id) REFERENCES project_workflow_nodes(id) ON DELETE CASCADE,
  FOREIGN KEY (to_node_id)   REFERENCES project_workflow_nodes(id) ON DELETE CASCADE
);

-- 7. IC 양방향 페어 매칭 (KR매출 ↔ VN매입 등)
CREATE TABLE IF NOT EXISTS ic_invoice_pairs (
  id             INTEGER PRIMARY KEY AUTOINCREMENT,
  pair_code      TEXT UNIQUE,            -- 'IC-260516-001'
  workflow_id    INTEGER,
  project_id     INTEGER,
  sell_entity    TEXT NOT NULL,          -- 'KR'|'VN'
  buy_entity     TEXT NOT NULL,
  sell_node_id   INTEGER,                -- 매출 측 노드
  buy_node_id    INTEGER,                -- 매입 측 노드
  sell_invoice_id INTEGER,               -- commercial_invoices.id (있으면)
  buy_invoice_id  INTEGER,
  amount         REAL DEFAULT 0,
  currency       TEXT DEFAULT 'USD',
  status         TEXT NOT NULL DEFAULT 'pending',  -- 'pending','matched','closed'
  matched_at     TEXT,
  note           TEXT,
  created_at     TEXT DEFAULT (datetime('now','localtime'))
);

CREATE INDEX IF NOT EXISTS ix_icp_workflow ON ic_invoice_pairs(workflow_id);
CREATE INDEX IF NOT EXISTS ix_icp_status   ON ic_invoice_pairs(status);
"""


def _column_exists(c, table, col):
    rows = c.execute(f"PRAGMA table_info({table})").fetchall()
    return any((r[1] if not isinstance(r, dict) else r['name']) == col for r in rows)


def migrate(db_path: str) -> dict:
    """idempotent 마이그레이션."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.executescript(SCHEMA_SQL)

    # projects 메타 컬럼 3개 (없으면 추가)
    added_cols = []
    for col, typ in [
        ('customer_country', 'TEXT'),
        ('po_entity', 'TEXT'),
        ('ship_entity', 'TEXT'),
    ]:
        if not _column_exists(c, 'projects', col):
            c.execute(f"ALTER TABLE projects ADD COLUMN {col} {typ}")
            added_cols.append(col)

    conn.commit()
    # 시드는 별도 함수
    seeded = _seed_all(c, conn)
    conn.close()
    return {'added_cols': added_cols, **seeded}


# ──────────────────────────────────────────────────────────────────────────
# SEED DATA
# ──────────────────────────────────────────────────────────────────────────

COUNTRIES = [
    # code, name_ko, name_en, region, order
    ('KR', '대한민국',    'South Korea', 'asia', 1),
    ('VN', '베트남',      'Vietnam',     'sea',  2),
    ('IN', '인도',        'India',       'asia', 10),
    ('CN', '중국',        'China',       'asia', 11),
    ('JP', '일본',        'Japan',       'asia', 12),
    ('ID', '인도네시아',  'Indonesia',   'sea',  20),
    ('MY', '말레이시아',  'Malaysia',    'sea',  21),
    ('TH', '태국',        'Thailand',    'sea',  22),
    ('PH', '필리핀',      'Philippines', 'sea',  23),
    ('SG', '싱가포르',    'Singapore',   'sea',  24),
    ('US', '미국',        'USA',         'americas', 30),
    ('DE', '독일',        'Germany',     'europe',   40),
    ('OTHER', '기타',     'Other',       'other',    99),
]


# 45개 노드 마스터
NODES = [
    # (node_code, category, title_ko, default_dept, est_h, is_ic, ic_dir, order)
    # ── 영업 (sales) ──
    ('sales.lead',         'sales', '리드 발굴',           '영업', 2,  0, None,        10),
    ('sales.meeting',      'sales', '고객 미팅',           '영업', 4,  0, None,        11),
    ('sales.requirement',  'sales', '요구사항 정리',       '영업', 4,  0, None,        12),
    ('sales.quote',        'sales', '견적 제출',           '영업', 8,  0, None,        13),
    ('sales.po_receive',   'sales', 'PO 수주',             '영업', 2,  0, None,        14),
    ('sales.contract',     'sales', '계약 체결',           '영업', 6,  0, None,        15),
    # ── 설계 (design) ──
    ('design.spec',        'design', '사양서 작성',         '설계', 16, 0, None,        20),
    ('design.bom',         'design', 'BOM 작성',            '설계', 16, 0, None,        21),
    ('design.mech_kr',     'design', '기계설계 (한국)',     '설계', 80, 0, None,        22),
    ('design.mech_vn',     'design', '기계설계 (베트남)',   '설계', 80, 0, None,        23),
    ('design.elec_kr',     'design', '전기설계 (한국)',     '설계', 60, 0, None,        24),
    ('design.elec_vn',     'design', '전기설계 (베트남)',   '설계', 60, 0, None,        25),
    ('design.sw_kr',       'design', 'SW설계 (한국)',       '설계', 80, 0, None,        26),
    ('design.sw_vn',       'design', 'SW설계 (베트남)',     '설계', 80, 0, None,        27),
    ('design.review',      'design', '설계 검토',           '설계', 8,  0, None,        28),
    # ── 자재·구매 (purchase) ──
    ('purchase.new_review','purchase', '신규자재 검토',     '자재구매', 4,  0, None,    30),
    ('purchase.po_issue',  'purchase', '구매발주',          '자재구매', 8,  0, None,    31),
    ('purchase.receive',   'purchase', '자재 입고',         '자재구매', 4,  0, None,    32),
    # ── 생산 (production) ──
    ('prod.kr_assy',       'production', '한국 가공/조립',  '생산', 80, 0, None,        40),
    ('prod.vn_assy',       'production', '베트남 가공/조립','생산', 80, 0, None,        41),
    ('prod.outsource',     'production', '외주 가공',       '생산', 40, 0, None,        42),
    # ── 품질 (qa) ──
    ('qa.in_inspect',      'qa', '입고 검사',              '품질', 4,  0, None,        50),
    ('qa.in_process',      'qa', '공정 검사',              '품질', 8,  0, None,        51),
    ('qa.final',           'qa', '최종 검사',              '품질', 8,  0, None,        52),
    ('qa.fat',             'qa', 'FAT (출하 시험)',        '품질', 16, 0, None,        53),
    # ── 물류 (logi) ──
    ('logi.packing',       'logi', '포장',                 '물류', 4,  0, None,        60),
    ('logi.export_doc',    'logi', '수출 서류',            '물류', 4,  0, None,        61),
    ('logi.ship_kr',       'logi', '한국 출하',            '물류', 4,  0, None,        62),
    ('logi.ship_vn',       'logi', '베트남 출하',          '물류', 4,  0, None,        63),
    ('logi.customs',       'logi', '통관',                 '물류', 4,  0, None,        64),
    ('logi.delivery',      'logi', '현지 인도',            '물류', 4,  0, None,        65),
    ('logi.setup',         'logi', '현장 설치/시운전',     '물류', 40, 0, None,        66),
    ('qa.sat',             'qa',   'SAT (현장 시험)',      '품질', 16, 0, None,        67),
    # ── 회계 (finance) ──
    ('finance.invoice',    'finance', '세금계산서/INVOICE','회계', 2,  0, None,        70),
    ('finance.receipt',    'finance', '수금',              '회계', 2,  0, None,        71),
    ('finance.payment',    'finance', '대금 지급',         '회계', 2,  0, None,        72),
    # ── IC (intercompany) — 양방향 페어 후보 ──
    ('ic.kr_sale_to_vn',   'ic', 'KR→VN 매출 (본사→법인)', '법인', 2,  1, 'kr_to_vn',   80),
    ('ic.vn_buy_from_kr',  'ic', 'VN←KR 매입 (법인→본사)', '법인', 2,  1, 'vn_to_kr',   81),
    ('ic.vn_sale_to_kr',   'ic', 'VN→KR 매출 (법인→본사)', '법인', 2,  1, 'vn_to_kr',   82),
    ('ic.kr_buy_from_vn',  'ic', 'KR←VN 매입 (본사→법인)', '법인', 2,  1, 'kr_to_vn',   83),
    ('ic.tt_kr_to_vn',     'ic', 'KR→VN 송금',             '회계', 2,  1, 'kr_to_vn',   84),
    ('ic.tt_vn_to_kr',     'ic', 'VN→KR 송금',             '회계', 2,  1, 'vn_to_kr',   85),
    # ── AS (사후관리) ──
    ('as.handover',        'as', '인수인계',               '영업', 4,  0, None,        90),
    ('as.warranty',        'as', '보증 기간 관리',         '영업', 0,  0, None,        91),
    ('as.followup',        'as', 'AS 대응',                '영업', 0,  0, None,        92),
]


# 5개 시나리오 템플릿 (빠른 시작용)
TEMPLATES = [
    # code, title, desc, customer_country_hint, po_entity, ship_entity, order, nodes (list of node_code)
    {
        'code': 's1_kr_domestic',
        'title_ko': '① 국내 (한국 고객·KR 수주·KR 출하)',
        'description': '본사 수주 → 한국 설계·생산 → 국내 출하',
        'customer_country_hint': 'KR', 'po_entity_hint': 'KR', 'ship_entity_hint': 'KR',
        'order': 1,
        'nodes': [
            'sales.lead','sales.meeting','sales.requirement','sales.quote','sales.po_receive','sales.contract',
            'design.spec','design.bom','design.mech_kr','design.elec_kr','design.sw_kr','design.review',
            'purchase.new_review','purchase.po_issue','purchase.receive',
            'prod.kr_assy',
            'qa.in_inspect','qa.in_process','qa.final','qa.fat',
            'logi.packing','logi.ship_kr','logi.delivery','logi.setup','qa.sat',
            'finance.invoice','finance.receipt',
            'as.handover','as.warranty',
        ],
    },
    {
        'code': 's2_kr_export_in',
        'title_ko': '② KR 수출 (인도 등 KR 직수출)',
        'description': '본사 수주 → 한국 설계·생산 → 인도/해외 수출',
        'customer_country_hint': 'IN', 'po_entity_hint': 'KR', 'ship_entity_hint': 'KR',
        'order': 2,
        'nodes': [
            'sales.lead','sales.meeting','sales.requirement','sales.quote','sales.po_receive','sales.contract',
            'design.spec','design.bom','design.mech_kr','design.elec_kr','design.sw_kr','design.review',
            'purchase.new_review','purchase.po_issue','purchase.receive',
            'prod.kr_assy',
            'qa.in_inspect','qa.in_process','qa.final','qa.fat',
            'logi.packing','logi.export_doc','logi.ship_kr','logi.customs','logi.delivery','logi.setup','qa.sat',
            'finance.invoice','finance.receipt',
            'as.handover','as.warranty',
        ],
    },
    {
        'code': 's3_vn_export',
        'title_ko': '③ VN 수출 (본사 수주 → VN 출하·KR↔VN IC)',
        'description': '본사가 수주받고 VN 법인이 생산·출하 (KR→VN 자재판매 + VN→KR 가공품 매출 IC 페어)',
        'customer_country_hint': 'VN', 'po_entity_hint': 'KR', 'ship_entity_hint': 'VN',
        'order': 3,
        'nodes': [
            'sales.lead','sales.meeting','sales.requirement','sales.quote','sales.po_receive','sales.contract',
            'design.spec','design.bom','design.mech_kr','design.elec_vn','design.sw_kr','design.review',
            'purchase.new_review','purchase.po_issue','purchase.receive',
            'ic.kr_sale_to_vn','ic.vn_buy_from_kr',
            'prod.vn_assy',
            'qa.in_inspect','qa.in_process','qa.final','qa.fat',
            'ic.vn_sale_to_kr','ic.kr_buy_from_vn',
            'logi.packing','logi.export_doc','logi.ship_vn','logi.customs','logi.delivery','logi.setup','qa.sat',
            'finance.invoice','finance.receipt','ic.tt_kr_to_vn',
            'as.handover','as.warranty',
        ],
    },
    {
        'code': 's4_vn_local_po',
        'title_ko': '④ VN 현지 수주 (VN 법인 직수주·VN 출하)',
        'description': 'VN 법인이 직접 수주·생산·VN 현지 출하 (SW만 한국 지원 가능)',
        'customer_country_hint': 'VN', 'po_entity_hint': 'VN', 'ship_entity_hint': 'VN',
        'order': 4,
        'nodes': [
            'sales.lead','sales.meeting','sales.requirement','sales.quote','sales.po_receive','sales.contract',
            'design.spec','design.bom','design.mech_vn','design.elec_vn','design.sw_kr','design.review',
            'purchase.new_review','purchase.po_issue','purchase.receive',
            'prod.vn_assy',
            'qa.in_inspect','qa.in_process','qa.final','qa.fat',
            'logi.packing','logi.ship_vn','logi.delivery','logi.setup','qa.sat',
            'finance.invoice','finance.receipt',
            'as.handover','as.warranty',
        ],
    },
    {
        'code': 's5_split',
        'title_ko': '⑤ 분담 시나리오 (설계 KR+VN, 생산 KR)',
        'description': '복합 케이스 — 마법사 8문항으로 미세조정',
        'customer_country_hint': None, 'po_entity_hint': None, 'ship_entity_hint': None,
        'order': 5,
        'nodes': [
            'sales.lead','sales.meeting','sales.requirement','sales.quote','sales.po_receive','sales.contract',
            'design.spec','design.bom',
            'design.mech_kr','design.mech_vn',
            'design.elec_kr','design.elec_vn',
            'design.sw_kr','design.sw_vn',
            'design.review',
            'purchase.new_review','purchase.po_issue','purchase.receive',
            'prod.kr_assy','prod.outsource',
            'qa.in_inspect','qa.in_process','qa.final','qa.fat',
            'logi.packing','logi.export_doc','logi.ship_kr','logi.customs','logi.delivery','logi.setup','qa.sat',
            'finance.invoice','finance.receipt',
            'as.handover','as.warranty',
        ],
    },
]


def _seed_all(c, conn):
    n_countries = 0
    for code, ko, en, region, order in COUNTRIES:
        c.execute("""INSERT OR IGNORE INTO countries_master
                     (code,name_ko,name_en,region,display_order) VALUES (?,?,?,?,?)""",
                  (code, ko, en, region, order))
        if c.rowcount:
            n_countries += 1

    n_nodes = 0
    for code, cat, title, dept, est, is_ic, ic_dir, order in NODES:
        c.execute("""INSERT OR IGNORE INTO workflow_nodes_master
                     (node_code,category,title_ko,default_dept,est_hours,is_ic,ic_direction,display_order)
                     VALUES (?,?,?,?,?,?,?,?)""",
                  (code, cat, title, dept, est, is_ic, ic_dir, order))
        if c.rowcount:
            n_nodes += 1

    n_templates = 0
    n_tnodes = 0
    for tpl in TEMPLATES:
        c.execute("""INSERT OR IGNORE INTO workflow_templates
                     (code,title_ko,description,customer_country_hint,po_entity_hint,ship_entity_hint,display_order)
                     VALUES (?,?,?,?,?,?,?)""",
                  (tpl['code'], tpl['title_ko'], tpl['description'],
                   tpl['customer_country_hint'], tpl['po_entity_hint'], tpl['ship_entity_hint'],
                   tpl['order']))
        if c.rowcount:
            n_templates += 1
        row = c.execute("SELECT id FROM workflow_templates WHERE code=?", (tpl['code'],)).fetchone()
        if not row:
            continue
        tid = row[0]
        # 기존 노드 매핑 삭제 후 재삽입 (멱등)
        c.execute("DELETE FROM workflow_template_nodes WHERE template_id=?", (tid,))
        for i, ncode in enumerate(tpl['nodes'], start=1):
            c.execute("""INSERT INTO workflow_template_nodes (template_id,node_code,seq)
                         VALUES (?,?,?)""", (tid, ncode, i))
            n_tnodes += 1

    conn.commit()
    return {
        'countries': n_countries,
        'nodes': n_nodes,
        'templates': n_templates,
        'template_nodes': n_tnodes,
    }


if __name__ == '__main__':
    here = os.path.dirname(os.path.abspath(__file__))
    db = os.path.normpath(os.path.join(here, '..', '..', 'data', 'knk.db'))
    if not os.path.exists(db):
        db = os.path.normpath(os.path.join(here, '..', 'knk.db'))
    print(f'[migrate] DB = {db}')
    r = migrate(db)
    print(f'[migrate] result = {r}')
