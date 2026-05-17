"""
v5H226z108i (2026-05-17) — KNK 노드 제목 친화 정비

대표 지시: 체크리스트 내용 확인 → 엑셀 용어와 안 맞는 노드 제목 일괄 교정
- 영문 약어 앞으로: SW → 소프트웨어, FAT/SAT 괄호로 (한국어 앞으로)
- 한국 → 본사
- 기계설계 → 기구설계 (KNK 실제 용어)
- 전기설계 → 전장설계 (KNK 실제 용어)
- 엑셀 표현 그대로 가져옴: "기구조립 진행", "전장작업 진행" 등
"""

import sqlite3
import os


NODE_TITLE_MAP = {
    # ── 영업 ──
    'sales.lead': '프로젝트 회의 요청',
    'sales.meeting': '회의 참석 진행',
    'sales.requirement': '요구사항 정리',
    'sales.concept_meeting': '컨셉회의 진행',
    'sales.proposal': '제안서 작성',
    'sales.quote': '견적서·고객사 협의',
    'sales.po_receive': 'PO 입수 + 프로젝트 등록',
    'sales.contract': '계약 체결',
    'sales.kickoff': '프로젝트 시작 미팅',
    'sales.so_to_vn': '베트남법인으로 견적·매출 발행',
    'sales.closeout': '최종 마감 정리',
    # ── 설계 ──
    'design.spec': '사양서 작성',
    'design.bom': '부품목록(BOM) 작성',
    'design.mech_kr': '기구설계 (본사)',
    'design.mech_vn': '기구설계 (베트남법인)',
    'design.elec_kr': '전장설계 (본사)',
    'design.elec_vn': '전장설계 (베트남법인)',
    'design.sw_kr': '소프트웨어설계 (본사)',
    'design.sw_vn': '소프트웨어설계 (베트남법인)',
    'design.review': '설계 검토',
    # ── 구매 ──
    'purchase.long_lead': '장납기 자재 선행 발주',
    'purchase.new_review': '신규자재 검토',
    'purchase.part_list': '전체 부품목록(PART LIST) 작성',
    'purchase.po_issue': '자재 발주',
    'purchase.machined_po': '가공품 발주',
    'purchase.receive': '자재 입고 확인',
    'purchase.machined_recv': '가공품 입고 확인',
    # ── 제조 ──
    'prod.kr_assy': '기구조립 (본사)',
    'prod.vn_assy': '기구조립 (베트남법인)',
    'prod.outsource': '외주 가공',
    'mfg.machining_kr': '가공 (본사)',
    'mfg.machining_vn': '가공 (베트남법인)',
    'mfg.assembly_kr': '기구조립 진행 (본사)',
    'mfg.assembly_vn': '기구조립 진행 (베트남법인)',
    'mfg.electrical_kr': '전장작업 진행 (본사)',
    'mfg.electrical_vn': '전장작업 진행 (베트남법인)',
    'mfg.io_check_kr': 'I/O 체크 (본사)',
    'mfg.io_check_vn': 'I/O 체크 (베트남법인)',
    'mfg.sw_apply_kr': '프로그램 적용·드라이런·디버깅 (본사)',
    'mfg.sw_apply_vn': '프로그램 적용·드라이런·디버깅 (베트남법인)',
    'mfg.verification_kr': '검증 (본사)',
    'mfg.verification_vn': '검증 (베트남법인)',
    # ── 품질 ──
    'qa.in_inspect': '입고 검사',
    'qa.in_process': '공정 검사',
    'qa.final': '최종 검사',
    'qa.fat': '출하검증 (FAT)',
    'qa.fat_vn': '출하검증 — 베트남법인 주관 (FAT)',
    'qa.sat': '현장 인수 시험 (SAT)',
    'qa.kr_recv_inspect': '본사 입고 장비 동작 검증',
    # ── 물류 ──
    'logi.packing': '포장',
    'logi.export_doc': '수출 서류 (INVOICE·PACKING LIST·B/L)',
    'logi.ship_kr': '본사 출하 (물류 예약·거래명세서)',
    'logi.ship_vn': '베트남법인 출하',
    'logi.customs': '통관',
    'logi.delivery': '현지 인도',
    'logi.setup': '셋업지 설치·시운전',
    'logi.ship_prep': '장비 출하 준비',
    'logi.kr_to_vn': '본사 → 베트남법인 자재 발송 (해상/항공)',
    'logi.vn_to_kr': '베트남법인 → 본사 장비 출하',
    'logi.vn_export': '베트남법인 → 해외 출하',
    # ── 회계 ──
    'finance.invoice': '세금계산서·INVOICE 발행',
    'finance.receipt': '수금',
    'finance.payment': '대금 지급',
    # ── 본사↔법인 거래 (IC) ──
    'ic.kr_sale_to_vn': '본사 → 베트남법인 매출 (자재·제품 판매)',
    'ic.vn_buy_from_kr': '베트남법인 ← 본사 매입',
    'ic.vn_sale_to_kr': '베트남법인 → 본사 매출 (가공품 판매)',
    'ic.kr_buy_from_vn': '본사 ← 베트남법인 매입',
    'ic.tt_kr_to_vn': '본사 → 베트남법인 송금',
    'ic.tt_vn_to_kr': '베트남법인 → 본사 송금',
    'ic.vn_po_to_kr': '베트남법인 → 본사 주문서 발행',
    'ic.kr_import_from_vn': '본사 장비 수입 처리',
    # ── 사후 ──
    'as.handover': '인수인계 (사용자 교육)',
    'as.warranty': '보증 기간 관리',
    'as.followup': 'AS 대응',
    'docs.manual': '설비 매뉴얼 작성',
}


def migrate(db_path: str) -> dict:
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    updated = 0
    not_found = []
    for code, title in NODE_TITLE_MAP.items():
        r = c.execute(
            "UPDATE workflow_nodes_master SET title_ko=? WHERE node_code=?",
            (title, code)
        )
        if r.rowcount:
            updated += 1
        else:
            not_found.append(code)

    conn.commit()
    conn.close()
    return {'updated': updated, 'not_found': not_found,
            'total_mapped': len(NODE_TITLE_MAP)}


if __name__ == '__main__':
    here = os.path.dirname(os.path.abspath(__file__))
    db = os.path.normpath(os.path.join(here, '..', '..', 'data', 'knk.db'))
    print(migrate(db))
