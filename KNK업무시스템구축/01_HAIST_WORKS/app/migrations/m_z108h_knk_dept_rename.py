"""
v5H226z108h (2026-05-17) — KNK 실제 부서명 적용

대표 지시: "매트릭스·체크리스트 용어들이 안 맞아. 우리가 사용하는 용어 및 부서들이 아니야."

기존: 영업/설계/자재구매/생산/품질/물류/회계/법인 (일반어)
변경: KNK 실제 부서명 (기술영업팀·제조기술2팀·구매팀·VN조립팀 등)
"""

import sqlite3
import os


# 노드 코드 → KNK 실제 부서 매핑
NODE_DEPT_MAP = {
    # ── 영업 (sales) ──
    'sales.lead': '기술영업팀',
    'sales.meeting': '기술영업팀',
    'sales.concept_meeting': '기술영업팀',
    'sales.proposal': '설계팀',
    'sales.requirement': '기술영업팀',
    'sales.quote': '기술영업팀',
    'sales.po_receive': '기술영업팀',
    'sales.contract': '기술영업팀',
    'sales.kickoff': '기술영업팀',
    'sales.so_to_vn': '기술영업팀',
    'sales.closeout': '기술영업팀',
    # ── 설계 (design) ──
    'design.spec': '설계팀',
    'design.bom': '설계팀',
    'design.mech_kr': '설계팀',
    'design.mech_vn': 'VN설계팀',
    'design.elec_kr': '전장설계팀',
    'design.elec_vn': 'VN전장팀',
    'design.sw_kr': '소프트웨어팀',
    'design.sw_vn': 'VN소프트웨어팀',
    'design.review': '설계팀',
    # ── 자재·구매 (purchase) ──
    'purchase.long_lead': '구매팀',
    'purchase.new_review': '구매팀',
    'purchase.part_list': '구매팀',
    'purchase.po_issue': '구매팀',
    'purchase.machined_po': '구매팀',  # OR 설계팀 (마법사 선택)
    'purchase.receive': '구매팀',
    'purchase.machined_recv': '구매팀',
    # ── 제조 (production) ──
    'prod.kr_assy': '제조기술2팀',
    'prod.vn_assy': 'VN조립팀',
    'prod.outsource': '구매팀',
    'mfg.machining_kr': '제조기술2팀',
    'mfg.machining_vn': 'VN조립팀',
    'mfg.assembly_kr': '제조기술2팀',
    'mfg.assembly_vn': 'VN조립팀',
    'mfg.electrical_kr': '제조기술2팀',
    'mfg.electrical_vn': 'VN조립팀',
    'mfg.verification_kr': '제조기술2팀',
    'mfg.verification_vn': 'VN조립팀',
    'mfg.io_check_kr': '제조기술2팀',
    'mfg.io_check_vn': 'VN조립팀',
    'mfg.sw_apply_kr': '소프트웨어팀',
    'mfg.sw_apply_vn': 'VN소프트웨어팀',
    # ── 품질 (qa) — 제조기술2팀 주관 (별도 품질팀 없음) ──
    'qa.in_inspect': '제조기술2팀',
    'qa.in_process': '제조기술2팀',
    'qa.final': '제조기술2팀',
    'qa.fat': '제조기술2팀',
    'qa.fat_vn': 'VN조립팀',
    'qa.sat': '제조기술2팀',
    'qa.kr_recv_inspect': '제조기술2팀',
    # ── 물류 (logi) ──
    'logi.packing': '제조기술2팀',     # 또는 VN조립팀 (시나리오별)
    'logi.export_doc': '기술영업팀',
    'logi.ship_kr': '기술영업팀',
    'logi.ship_vn': 'VN관리팀',
    'logi.customs': '기술영업팀',
    'logi.delivery': '기술영업팀',
    'logi.setup': '제조기술2팀',
    'logi.ship_prep': '제조기술2팀',
    'logi.kr_to_vn': '기술영업팀',
    'logi.vn_to_kr': 'VN관리팀',
    'logi.vn_export': 'VN관리팀',
    # ── 회계 (finance) ──
    'finance.invoice': '회계팀',
    'finance.receipt': '회계팀',
    'finance.payment': '회계팀',
    # ── IC (intercompany) ──
    'ic.kr_sale_to_vn': '기술영업팀',
    'ic.vn_buy_from_kr': 'VN관리팀',
    'ic.vn_sale_to_kr': 'VN관리팀',
    'ic.kr_buy_from_vn': '구매팀',
    'ic.tt_kr_to_vn': '회계팀',
    'ic.tt_vn_to_kr': '회계팀',
    'ic.vn_po_to_kr': 'VN관리팀',
    'ic.kr_import_from_vn': '기술영업팀',
    # ── AS / 사후 ──
    'as.handover': '기술영업팀',
    'as.warranty': '기술영업팀',
    'as.followup': '기술영업팀',
    'docs.manual': '소프트웨어팀',
}


def migrate(db_path: str) -> dict:
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    updated = 0
    not_found = []
    for code, dept in NODE_DEPT_MAP.items():
        r = c.execute(
            "UPDATE workflow_nodes_master SET default_dept=? WHERE node_code=?",
            (dept, code)
        )
        if r.rowcount:
            updated += 1
        else:
            not_found.append(code)

    conn.commit()
    conn.close()
    return {'updated': updated, 'not_found': not_found,
            'total_mapped': len(NODE_DEPT_MAP)}


if __name__ == '__main__':
    here = os.path.dirname(os.path.abspath(__file__))
    db = os.path.normpath(os.path.join(here, '..', '..', 'data', 'knk.db'))
    print(migrate(db))
