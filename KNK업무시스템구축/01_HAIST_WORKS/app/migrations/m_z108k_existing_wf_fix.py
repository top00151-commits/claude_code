"""
v5H226z108k (2026-05-17) — 기존 워크플로우 내용 수정

대표 지시: "기존에 만들어진 워크플로우도 내용 수정해줘"

자동 반영 사항 (별도 작업 불필요):
  - 노드 제목·부서: workflow_nodes_master JOIN 으로 자동 반영
    · z108h 부서 변경, z108i 제목 변경 → 기존 워크플로우 화면에 즉시 반영됨

수동 수정 필요 (이 마이그):
  - T4 시나리오 워크플로우: logi.customs/delivery 를 _vn 버전으로 교체
  - 변경된 노드의 체크포인트 재시드 (새 master deliverables 반영)

T4 식별 기준: po_entity='VN' AND customer_country != 'KR'
"""

import sqlite3
import json
import os


NODE_REPLACEMENTS_T4 = [
    ('logi.customs',  'logi.customs_vn'),
    ('logi.delivery', 'logi.delivery_vn'),
]


def migrate(db_path: str) -> dict:
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    # 1. T4 워크플로우 식별
    t4_wfs = [r[0] for r in c.execute("""
        SELECT id FROM project_workflow
        WHERE po_entity='VN' AND COALESCE(customer_country,'') != 'KR'
    """).fetchall()]

    nodes_updated = 0
    checkpoints_reseeded = 0
    affected_wfs = []

    for wf_id in t4_wfs:
        wf_affected = False
        for old_code, new_code in NODE_REPLACEMENTS_T4:
            # 해당 노드 인스턴스 찾기
            rows = c.execute(
                "SELECT id FROM project_workflow_nodes WHERE workflow_id=? AND node_code=?",
                (wf_id, old_code)
            ).fetchall()
            for (pwfn_id,) in rows:
                # node_code 교체
                c.execute(
                    "UPDATE project_workflow_nodes SET node_code=? WHERE id=?",
                    (new_code, pwfn_id)
                )
                nodes_updated += 1
                wf_affected = True

                # 기존 체크포인트 삭제
                c.execute(
                    "DELETE FROM project_workflow_node_checkpoints WHERE pwfn_id=?",
                    (pwfn_id,)
                )
                # 새 master의 deliverables_json 으로 재시드
                row = c.execute(
                    "SELECT deliverables_json FROM workflow_nodes_master WHERE node_code=?",
                    (new_code,)
                ).fetchone()
                if row and row[0]:
                    try:
                        items = json.loads(row[0])
                        if isinstance(items, list):
                            for i, label in enumerate(items, start=1):
                                c.execute("""INSERT INTO project_workflow_node_checkpoints
                                             (pwfn_id, label, seq, is_done)
                                             VALUES (?,?,?,0)""",
                                          (pwfn_id, str(label), i))
                            checkpoints_reseeded += len(items)
                    except Exception:
                        pass
        if wf_affected:
            affected_wfs.append(wf_id)

    conn.commit()
    conn.close()
    return {
        't4_workflows_found': len(t4_wfs),
        'nodes_updated': nodes_updated,
        'checkpoints_reseeded': checkpoints_reseeded,
        'affected_workflow_ids': affected_wfs,
    }


if __name__ == '__main__':
    here = os.path.dirname(os.path.abspath(__file__))
    db = os.path.normpath(os.path.join(here, '..', '..', 'data', 'knk.db'))
    print(migrate(db))
