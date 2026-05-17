"""
v5H226z108j (2026-05-17) — 시나리오별 부서 정합성 수정

대표 지시: 4 시나리오 전체 검토 결과 발견된 부서 미스매치 수정.

이슈:
  1. T2/T3 #31 포장 — 제조기술2팀 → VN조립팀 (VN에서 진행)
  2. T4 #35 통관 / #36 현지 인도 — 기술영업팀 → VN관리팀 (VN 직출하)

해결:
  - logi.packing 부서 → VN조립팀 (VN 포장이 일반적이므로) + 제목 명확화
  - logi.customs_vn / logi.delivery_vn 신규 노드 (VN관리팀 주관)
  - T4 시퀀스: logi.customs → logi.customs_vn, logi.delivery → logi.delivery_vn
"""

import sqlite3
import json
import os


# 기존 노드 부서·제목 갱신
EXISTING_UPDATES = {
    # T2/T3 포장은 VN조립팀 (베트남법인 포장)
    'logi.packing': ('VN조립팀', '포장 (베트남법인 — 기본사항 확인 후)'),
}


# T4 (VN 직출하) 전용 신규 노드
NEW_NODES = [
    # (node_code, category, title_ko, default_dept, est_h, order)
    ('logi.customs_vn',  'logi', '통관 (베트남법인 출하)',  'VN관리팀', 4, 65),
    ('logi.delivery_vn', 'logi', '현지 인도 (베트남법인 출하)', 'VN관리팀', 4, 66),
]


NEW_META = {
    'logi.customs_vn': (
        "베트남법인 → 해외 직수출 시 통관 처리.\nVN관리팀 주관.",
        ["수출 신고 (VN)", "통관 완료"],
        None
    ),
    'logi.delivery_vn': (
        "베트남법인 직출하 시 현지 인도.",
        ["현지 수령 확인 (VN→해외)"],
        None
    ),
}


def _has_col(c, table, col):
    rows = c.execute(f"PRAGMA table_info({table})").fetchall()
    return any(r[1] == col for r in rows)


def migrate(db_path: str) -> dict:
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    # 1) 기존 노드 부서·제목 갱신
    n_updated = 0
    for code, (dept, title) in EXISTING_UPDATES.items():
        r = c.execute(
            "UPDATE workflow_nodes_master SET default_dept=?, title_ko=? WHERE node_code=?",
            (dept, title, code)
        )
        if r.rowcount:
            n_updated += 1

    # 2) 신규 노드 추가
    n_new = 0
    for code, cat, title, dept, est, order in NEW_NODES:
        r = c.execute("""INSERT OR IGNORE INTO workflow_nodes_master
                         (node_code, category, title_ko, default_dept, est_hours,
                          is_ic, ic_direction, display_order, is_active)
                         VALUES (?,?,?,?,?,0,NULL,?,1)""",
                       (code, cat, title, dept, est, order))
        if r.rowcount:
            n_new += 1

    # 3) 메타 시드
    n_meta = 0
    for code, (sop, dels, link) in NEW_META.items():
        r = c.execute(
            "UPDATE workflow_nodes_master SET sop_guide=?, deliverables_json=?, system_link_template=? WHERE node_code=?",
            (sop, json.dumps(dels, ensure_ascii=False), link, code)
        )
        if r.rowcount:
            n_meta += 1

    conn.commit()
    conn.close()
    return {'existing_updated': n_updated, 'new_nodes': n_new, 'meta_seeded': n_meta}


if __name__ == '__main__':
    here = os.path.dirname(os.path.abspath(__file__))
    db = os.path.normpath(os.path.join(here, '..', '..', 'data', 'knk.db'))
    print(migrate(db))
