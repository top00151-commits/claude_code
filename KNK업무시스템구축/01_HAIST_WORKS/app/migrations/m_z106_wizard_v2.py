"""
v5H226z106 (2026-05-16) — 마법사 v2: 라벨 변경 + 제조구분 4섹션 + 출하/셋업 3옵션

대표 결재 2026-05-16:
  - Q3 기계설계 → 기구설계
  - Q4 전기설계 → 전장설계
  - Q5 SW설계  → 소프트웨어설계
  - 옵션 라벨: KR/VN/KR+VN → 본사/베트남법인/협업(본사+베트남법인)

신규:
  - 제조구분 4개: 가공·조립·전장·검증 (각각 본사/VN/협업)
  - 출하구분 3옵션: 본사/VN/협업 (기존 단일 KR/VN → 협업 추가)
  - 셋업구분 3옵션: 본사/VN/협업 (기존 국가코드 → 단순 3옵션)

DB 변경:
  - project_workflow 에 컬럼 6개 추가
  - workflow_nodes_master 에 신규 노드 8개 (mfg.*)
"""

import sqlite3
import json
import os


def _has_col(c, table, col):
    rows = c.execute(f"PRAGMA table_info({table})").fetchall()
    return any(r[1] == col for r in rows)


NEW_COLS_PROJECT_WORKFLOW = [
    ('mfg_machining',     'TEXT'),   # 가공: 'KR'|'VN'|'BOTH'
    ('mfg_assembly',      'TEXT'),   # 조립
    ('mfg_electrical',    'TEXT'),   # 전장
    ('mfg_verification',  'TEXT'),   # 검증
    ('ship_split',        'TEXT'),   # 출하구분: 'KR'|'VN'|'BOTH'
    ('setup_split',       'TEXT'),   # 셋업구분
]


# 신규 8 노드 (제조구분 4종 × KR/VN, 협업은 양쪽 노드 함께 추가)
NEW_NODES = [
    # node_code, category, title_ko, default_dept, est_h, order
    ('mfg.machining_kr',    'production', '가공 (본사)',       '생산', 40, 1, 36),
    ('mfg.machining_vn',    'production', '가공 (베트남법인)', '생산', 40, 1, 37),
    ('mfg.assembly_kr',     'production', '조립 (본사)',       '생산', 60, 1, 38),
    ('mfg.assembly_vn',     'production', '조립 (베트남법인)', '생산', 60, 1, 39),
    ('mfg.electrical_kr',   'production', '전장 작업 (본사)',   '생산', 40, 1, 43),
    ('mfg.electrical_vn',   'production', '전장 작업 (베트남법인)', '생산', 40, 1, 44),
    ('mfg.verification_kr', 'qa',         '검증 (본사)',       '품질', 16, 1, 54),
    ('mfg.verification_vn', 'qa',         '검증 (베트남법인)', '품질', 16, 1, 55),
]


# 신규 노드 메타 (SOP/산출물/링크)
NEW_NODE_META = {
    'mfg.machining_kr': (
        "한국 본사에서 자재를 가공합니다.\n1) 작업지시 발행\n2) NC/머시닝 공정\n3) 치수 셀프체크",
        ["작업지시 발행", "가공 완료", "치수 확인"],
        "/work-orders"
    ),
    'mfg.machining_vn': (
        "베트남 법인에서 가공합니다.",
        ["작업지시 발행 (VN)", "가공 완료", "치수 확인"],
        "/work-orders"
    ),
    'mfg.assembly_kr': (
        "한국 본사에서 조립합니다.",
        ["조립 작업지시", "기계 조립 완료", "체결 확인"],
        "/work-orders"
    ),
    'mfg.assembly_vn': (
        "베트남 법인에서 조립합니다.",
        ["조립 작업지시 (VN)", "기계 조립 완료", "체결 확인"],
        "/work-orders"
    ),
    'mfg.electrical_kr': (
        "한국 본사에서 전장 작업 (배선·결선·제어반).",
        ["배선 작업", "결선 점검", "절연 확인"],
        None
    ),
    'mfg.electrical_vn': (
        "베트남 법인에서 전장 작업.",
        ["배선 작업 (VN)", "결선 점검", "절연 확인"],
        None
    ),
    'mfg.verification_kr': (
        "한국에서 검증 (동작·성능·안전).",
        ["동작 시험", "성능 측정", "안전 시험"],
        None
    ),
    'mfg.verification_vn': (
        "베트남에서 검증.",
        ["동작 시험 (VN)", "성능 측정", "안전 시험"],
        None
    ),
}


def migrate(db_path: str) -> dict:
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    added = []
    for col, typ in NEW_COLS_PROJECT_WORKFLOW:
        if not _has_col(c, 'project_workflow', col):
            c.execute(f"ALTER TABLE project_workflow ADD COLUMN {col} {typ}")
            added.append(col)

    # 신규 노드 시드
    n_nodes = 0
    for code, cat, title, dept, est, is_active, order in NEW_NODES:
        r = c.execute("""INSERT OR IGNORE INTO workflow_nodes_master
                         (node_code, category, title_ko, default_dept, est_hours,
                          is_ic, ic_direction, display_order, is_active)
                         VALUES (?,?,?,?,?,0,NULL,?,?)""",
                       (code, cat, title, dept, est, order, is_active))
        if r.rowcount:
            n_nodes += 1

    # 메타 시드
    n_meta = 0
    for code, (sop, dels, link) in NEW_NODE_META.items():
        r = c.execute(
            "UPDATE workflow_nodes_master SET sop_guide=?, deliverables_json=?, system_link_template=? WHERE node_code=?",
            (sop, json.dumps(dels, ensure_ascii=False), link, code)
        )
        if r.rowcount:
            n_meta += 1

    conn.commit()
    conn.close()
    return {'added_cols': added, 'new_nodes': n_nodes, 'meta_updated': n_meta}


if __name__ == '__main__':
    here = os.path.dirname(os.path.abspath(__file__))
    db = os.path.normpath(os.path.join(here, '..', '..', 'data', 'knk.db'))
    print(migrate(db))
