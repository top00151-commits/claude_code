"""
v5H226z108d (2026-05-17) — 엑셀 100% 활용 통합

대표 지시: 엑셀 124 단계 → 시스템 100% 반영. 직원이 흐름 따라가면 자동 진행.

추가:
  - workflow_nodes_master: 22 신규 노드 (영업 6 + 구매 4 + 제조 4 + 물류 4 + 기타 4)
  - project_workflow: 2 신규 컬럼
    · is_mass_revision (양산 변경사항 Y/N)
    · machined_po_dept ('design' | 'purchase')

엑셀 시트별 매핑:
  본사PO 시트 → 유형 ①②③
  베트남PO 시트 → 유형 ④
"""

import sqlite3
import json
import os


def _has_col(c, table, col):
    rows = c.execute(f"PRAGMA table_info({table})").fetchall()
    return any(r[1] == col for r in rows)


# (node_code, category, title_ko, default_dept, est_h, display_order)
NEW_NODES = [
    # ── 영업 (sales) — 6개 신규 ──
    ('sales.concept_meeting', 'sales', '컨셉회의 진행', '영업', 4, 11),
    ('sales.proposal',        'sales', '제안서 작성',   '영업', 16, 12),
    ('sales.kickoff',         'sales', '프로젝트 시작 미팅', '영업', 4, 16),
    ('sales.so_to_vn',        'sales', 'VN으로 견적·매출 발행', '영업', 2, 17),
    ('sales.closeout',        'sales', '최종 마감 정리', '영업', 4, 93),
    ('ic.vn_po_to_kr',        'ic',    'VN → 본사 IC PO 발행', '법인', 2, 86),
    # ── 구매 (purchase) — 4개 신규 ──
    ('purchase.long_lead',     'purchase', '장납기 자재 선행 발주', '자재구매', 4, 29),
    ('purchase.part_list',     'purchase', '전체 PART LIST 작성',  '자재구매', 4, 30),
    ('purchase.machined_po',   'purchase', '가공품 발주',          '자재구매', 6, 33),
    ('purchase.machined_recv', 'purchase', '가공품 입고 확인',     '자재구매', 2, 34),
    # ── 제조 (mfg) — 4개 신규 (I/O 체크 + SW 적용) ──
    ('mfg.io_check_kr',  'production', 'I/O 체크 (본사)',       '생산', 4, 45),
    ('mfg.io_check_vn',  'production', 'I/O 체크 (베트남법인)', '생산', 4, 46),
    ('mfg.sw_apply_kr',  'production', 'SW 적용·드라이런·디버깅 (본사)',     '소프트웨어', 16, 47),
    ('mfg.sw_apply_vn',  'production', 'SW 적용·드라이런·디버깅 (베트남법인)', '소프트웨어', 16, 48),
    # ── 물류 (logi) — 4개 신규 ──
    ('logi.ship_prep',  'logi', '장비 출하 준비',         '물류', 8, 61),
    ('logi.kr_to_vn',   'logi', '본사 → VN 자재 발송',    '물류', 8, 64),
    ('logi.vn_to_kr',   'logi', 'VN → 본사 장비 출하',    '물류', 8, 68),
    ('logi.vn_export',  'logi', 'VN → 해외 출하',         '물류', 8, 69),
    # ── 본사 수입·검증 (ic, qa) — 2개 신규 ──
    ('ic.kr_import_from_vn', 'ic', '본사 장비 수입 처리', '법인', 4, 87),
    ('qa.kr_recv_inspect',   'qa', '본사 입고 장비 동작 검증', '품질', 8, 56),
    # ── 문서 (docs) — 1개 신규 ──
    ('docs.manual', 'as', '설비 매뉴얼 작성', '소프트웨어', 16, 92),
    # ── 유형 ④ VN 직수주 출하검증 (VN 주관) ──
    ('qa.fat_vn',    'qa', '출하검증 (VN 주관)', '품질', 16, 53),
]


# 노드별 SOP/산출물/시스템링크
NODE_META = {
    'sales.concept_meeting': (
        "고객사 요구사항·기술 검토 + 초기 프로젝트 PM 선정.\n참석: 기술영업·설계·소프트웨어·전장설계.",
        ["컨셉 정리", "초기 PM 선정", "회의록 작성"],
        None
    ),
    'sales.proposal': (
        "제안서 작성 — 설계팀 주도, 기술영업 협업.\n양산 변경사항 적용 시에만 진행 (추가양산은 생략 가능).",
        ["제안 문서 작성", "내부 검토", "고객사 송부"],
        None
    ),
    'sales.kickoff': (
        "PO 입수 후 전체 부서가 모여 최종 프로젝트 PM 확정.",
        ["일정 확정", "최종 PM 지정", "역할 분담"],
        None
    ),
    'sales.so_to_vn': (
        "본사가 VN 법인에 견적서 발행 (본사 매출).\n· 상품(부품): 매입단가 +8~12%\n· 제품: 본사 제작품 +100% 이상.",
        ["견적서 발행", "본사 매출 등록"],
        None
    ),
    'sales.closeout': (
        "프로젝트 정산·문서 마감.",
        ["최종 정산", "프로젝트 종결 처리", "후속 AS 인계"],
        None
    ),
    'ic.vn_po_to_kr': (
        "VN 법인이 본사로 IC PO 발행.\n해외 고객사가 VN에 직발주한 경우 (유형 ④).",
        ["VN→본사 IC PO 작성", "본사 프로젝트 등록 의뢰"],
        None
    ),
    'purchase.long_lead': (
        "장납기 자재 사전 식별 + 선행 발주.\n공급업체·자재 검토 동시 진행.",
        ["장납기 자재 식별", "공급선 사전 협의", "선행 PO 발행"],
        None
    ),
    'purchase.part_list': (
        "설계·전장·SW BOM 통합 → 전체 PART LIST 작성.",
        ["BOM 3종 취합", "통합 PART LIST", "신규/등록 자재 구분"],
        None
    ),
    'purchase.machined_po': (
        "가공품 발주 — 비교 견적·납기 확인 후 발주.\n발주부서: 설계 OR 구매 (프로젝트별 선택).",
        ["비교 견적 수집", "납기 확인", "발주 처리"],
        None
    ),
    'purchase.machined_recv': (
        "가공품 입고 확인 + 제조기술2팀(또는 VN조립팀) 전달.",
        ["수량/도면 확인", "전달"],
        None
    ),
    'mfg.io_check_kr': (
        "본사 제조기술2팀에서 I/O 체크.",
        ["입출력 신호 검증", "결선 확인"],
        None
    ),
    'mfg.io_check_vn': (
        "VN 조립팀에서 I/O 체크.",
        ["입출력 신호 검증 (VN)", "결선 확인"],
        None
    ),
    'mfg.sw_apply_kr': (
        "본사 SW: 프로그램 적용 → 드라이런 → 디버깅 → 최종 검증.",
        ["프로그램 적용", "드라이런", "디버깅", "최종 검증"],
        None
    ),
    'mfg.sw_apply_vn': (
        "VN SW: 프로그램 적용 → 드라이런 → 디버깅 → 검증.\n기구 최종 완성 전이면 생략 가능.",
        ["프로그램 적용 (VN)", "드라이런", "디버깅", "검증"],
        None
    ),
    'logi.ship_prep': (
        "장비 출하 준비 — 포장·라벨링·도면 동봉.",
        ["포장 사양 확정", "라벨 부착", "출하 도면 동봉"],
        None
    ),
    'logi.kr_to_vn': (
        "본사 → VN 자재 발송.\n· 판매: 원산지증명서 발급으로 관세 최소화 (기술영업 수출/매출)\n· 임가공: 무관세 (재입고 원칙).",
        ["발송 방식 결정 (해상/항공)", "수출 서류", "선적"],
        None
    ),
    'logi.vn_to_kr': (
        "VN → 본사 장비 출하.\n· 본사 판매: 본사 수입금액 + VN 자재·가공·공수 포함\n· 임가공: VN 자재·가공·공수만.",
        ["견적 발행 (VN)", "출하 매출 처리", "수출 진행"],
        None
    ),
    'logi.vn_export': (
        "VN → 해외 직접 출하.\n유형 ④ 전용.",
        ["출하 서류 (VN)", "통관", "현지 인도"],
        None
    ),
    'ic.kr_import_from_vn': (
        "본사 장비 수입 처리.\n기술영업: 수입 진행 / 구매팀: 매입 처리.",
        ["수입 신고", "매입 등록", "입고 처리"],
        None
    ),
    'qa.kr_recv_inspect': (
        "VN에서 입고된 장비의 본사 동작 검증.",
        ["기본 동작 확인", "이상 사항 식별"],
        None
    ),
    'docs.manual': (
        "설비 사용·유지보수 매뉴얼 작성.\n소프트웨어팀·설계팀 공동.",
        ["사용 매뉴얼", "유지보수 가이드", "도면 첨부"],
        None
    ),
    'qa.fat_vn': (
        "VN 자체 출하검증 (VN조립팀 주관).\n유형 ④ 전용 — 본사 개입 없음.",
        ["시험 시나리오 (VN)", "측정 데이터", "고객 사인"],
        None
    ),
}


def migrate(db_path: str) -> dict:
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    # project_workflow 컬럼 추가
    added = []
    for col, typ in [
        ('is_mass_revision', 'INTEGER DEFAULT 0'),
        ('machined_po_dept', "TEXT DEFAULT 'purchase'"),
    ]:
        if not _has_col(c, 'project_workflow', col):
            c.execute(f"ALTER TABLE project_workflow ADD COLUMN {col} {typ}")
            added.append(col)

    # 신규 노드 시드
    n_nodes = 0
    for code, cat, title, dept, est, order in NEW_NODES:
        r = c.execute("""INSERT OR IGNORE INTO workflow_nodes_master
                         (node_code, category, title_ko, default_dept, est_hours,
                          is_ic, ic_direction, display_order, is_active)
                         VALUES (?,?,?,?,?,?,?,?,1)""",
                       (code, cat, title, dept, est,
                        1 if code.startswith('ic.') else 0,
                        None, order))
        if r.rowcount:
            n_nodes += 1

    # 노드 메타 시드
    n_meta = 0
    for code, (sop, dels, link) in NODE_META.items():
        r = c.execute(
            "UPDATE workflow_nodes_master SET sop_guide=?, deliverables_json=?, system_link_template=? WHERE node_code=?",
            (sop, json.dumps(dels, ensure_ascii=False), link, code)
        )
        if r.rowcount:
            n_meta += 1

    conn.commit()
    conn.close()
    return {'added_cols': added, 'new_nodes': n_nodes, 'meta_updated': n_meta,
            'total_new_node_specs': len(NEW_NODES)}


if __name__ == '__main__':
    here = os.path.dirname(os.path.abspath(__file__))
    db = os.path.normpath(os.path.join(here, '..', '..', 'data', 'knk.db'))
    print(migrate(db))
