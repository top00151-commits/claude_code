"""
v5H226z105 (2026-05-16) — 가이드형 워크플로우 보강

대표 의도:
  "어떤 단계 / 어느 부서 / 누가 / 무엇을 / 어떻게 / 했는지"
  를 순서도 따라가면서 누락 없이 업무 진행

추가:
  1) workflow_nodes_master 에 3 컬럼:
     - sop_guide              "어떻게" 절차 텍스트 (마크다운)
     - deliverables_json      "무엇을" 산출물 체크포인트 JSON 배열
     - system_link_template   관련 시스템 URL 템플릿 (예: '/parts/bom?project={project_id}')

  2) project_workflow_node_checkpoints (산출물 체크포인트 인스턴스)
     - 노드별 deliverables 항목 각각을 체크 가능하게

  3) workflow_handoffs (자동 핸드오프 알림 로그)
"""

import sqlite3
import json
import os


SCHEMA = r"""
CREATE TABLE IF NOT EXISTS project_workflow_node_checkpoints (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  pwfn_id      INTEGER NOT NULL,         -- project_workflow_nodes.id
  label        TEXT NOT NULL,
  is_done      INTEGER NOT NULL DEFAULT 0,
  done_by      INTEGER,
  done_at      TEXT,
  seq          INTEGER NOT NULL DEFAULT 1,
  FOREIGN KEY (pwfn_id) REFERENCES project_workflow_nodes(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS ix_pwfn_cp ON project_workflow_node_checkpoints(pwfn_id);

CREATE TABLE IF NOT EXISTS workflow_handoffs (
  id             INTEGER PRIMARY KEY AUTOINCREMENT,
  workflow_id    INTEGER NOT NULL,
  from_node_id   INTEGER,
  to_node_id     INTEGER NOT NULL,
  triggered_by   INTEGER,                 -- user_id
  notified_users TEXT,                    -- comma-separated user ids
  message        TEXT,
  created_at     TEXT DEFAULT (datetime('now','localtime'))
);
CREATE INDEX IF NOT EXISTS ix_handoffs_wf ON workflow_handoffs(workflow_id);
"""


def _has_col(c, table, col):
    rows = c.execute(f"PRAGMA table_info({table})").fetchall()
    return any(r[1] == col for r in rows)


# 노드별 SOP/산출물/시스템링크 시드 (확장 가능)
# format: { node_code: (sop_guide, [deliverables], system_link_template) }
NODE_META = {
    # ── 영업 ──
    'sales.lead': (
        "잠재 고객을 발굴하고 KNK CRM 에 등록합니다.\n1) 산업·지역·예상 규모 파악\n2) 1차 컨택 (전화/메일)\n3) 미팅 일정 확보",
        ["고객사 정보 등록", "1차 컨택 기록", "예상 규모 메모"],
        "/customers"
    ),
    'sales.meeting': (
        "현장 미팅으로 요구사항을 수집합니다.\n1) 라인 정보·기존 설비 파악\n2) 핵심 요구사항 메모\n3) 제약사항·납기 협의",
        ["미팅 일정 등록", "회의록 작성", "사진/도면 수집"],
        "/calendar"
    ),
    'sales.requirement': (
        "요구사항을 정리하여 사양서 초안의 입력으로 만듭니다.",
        ["기능 요구 목록", "제약사항 목록", "예산 범위 확정"],
        None
    ),
    'sales.quote': (
        "견적을 작성·제출합니다.\n1) BOM 기반 견적 산출\n2) 환율·통화 확인\n3) 결재 후 송부",
        ["견적서 PDF 작성", "결재 완료", "고객 송부 기록"],
        "/quotations"
    ),
    'sales.po_receive': (
        "고객 PO를 수신하고 시스템에 등록합니다.",
        ["PO 원본 수령", "관리번호 발급", "수주번호(SO) 발행"],
        "/orders"
    ),
    'sales.contract': (
        "정식 계약 체결 (필요 시).",
        ["계약서 검토", "법무 검토", "서명 완료"],
        None
    ),
    # ── 설계 ──
    'design.spec': (
        "고객 요구사항을 기반으로 사양서를 작성합니다.",
        ["기능 사양 정의", "성능 사양 정의", "인터페이스 사양"],
        None
    ),
    'design.bom': (
        "자재 카탈로그를 활용해 BOM을 작성합니다.\n1) 카탈로그에서 부품 검색\n2) 신규 자재는 별도 표기\n3) 수량·사양 확정",
        ["BOM 시트 작성", "신규자재 검토 요청", "도면 첨부"],
        "/catalog"
    ),
    'design.mech_kr': (
        "한국 기계설계팀이 주도하여 설계를 진행합니다.",
        ["3D 모델링", "조립도", "부품도 출력"],
        None
    ),
    'design.mech_vn': (
        "베트남 기계설계팀이 주도합니다 (한국팀 검토 지원 가능).",
        ["3D 모델링 (VN)", "조립도", "한국팀 검토 의견 반영"],
        None
    ),
    'design.elec_kr': (
        "한국 전기설계팀 — 회로도·결선도 작성.",
        ["회로도", "결선도", "PLC 입출력표"],
        None
    ),
    'design.elec_vn': (
        "베트남 전기설계팀 — 현지 인증 규격 반영.",
        ["회로도 (VN)", "결선도", "현지 규격 체크"],
        None
    ),
    'design.sw_kr': (
        "한국 SW팀 — PLC·HMI·비전 소프트웨어 개발.",
        ["PLC 프로그램", "HMI 화면", "비전 알고리즘"],
        None
    ),
    'design.sw_vn': (
        "베트남 SW팀.",
        ["PLC 프로그램 (VN)", "HMI 화면", "테스트"],
        None
    ),
    'design.review': (
        "설계 전체 검토 — 부서간 누락 확인.",
        ["기계/전기/SW 정합성", "BOM 최종 확정", "검토 회의록"],
        None
    ),
    # ── 자재·구매 ──
    'purchase.new_review': (
        "설계팀이 올린 신규 자재를 검토합니다.",
        ["사양 검토", "공급선 조사", "등록 / 견적 / 거절 결정"],
        "/materials/new-review"
    ),
    'purchase.po_issue': (
        "자재 발주 — 공급사 견적 비교 후 발주.",
        ["견적 비교", "발주서 작성", "결재 + 송부"],
        "/orders/po"
    ),
    'purchase.receive': (
        "자재 입고 — 수량·사양 확인.",
        ["입고 검수", "재고 등록", "공급사 통보"],
        "/stocks"
    ),
    # ── 생산 ──
    'prod.kr_assy': (
        "한국 공장에서 가공·조립.",
        ["작업지시 발행", "조립 진행", "셀프 체크"],
        "/work-orders"
    ),
    'prod.vn_assy': (
        "베트남 공장에서 가공·조립.",
        ["작업지시 발행 (VN)", "조립 진행", "셀프 체크"],
        "/work-orders"
    ),
    'prod.outsource': (
        "외주 가공.",
        ["외주처 선정", "도면 전달", "납기 관리"],
        None
    ),
    # ── 품질 ──
    'qa.in_inspect': ("입고 검사.", ["수량 확인", "외관 검사", "치수 검사"], None),
    'qa.in_process': ("공정 검사.", ["공정별 체크리스트", "이상 대응"], None),
    'qa.final':      ("최종 검사.", ["기능 시험", "안전 시험", "외관 검수"], None),
    'qa.fat': (
        "FAT — 출하 전 고객 입회 시험.",
        ["시험 시나리오", "측정 데이터", "고객 사인"],
        None
    ),
    'qa.sat': (
        "SAT — 현장 인수 시험.",
        ["현장 시험", "성능 확인", "고객 사인"],
        None
    ),
    # ── 물류 ──
    'logi.packing':     ("포장.",        ["포장 사양 확정", "포장 사진"],   None),
    'logi.export_doc':  ("수출 서류 작성.", ["INVOICE", "PACKING LIST", "B/L"], None),
    'logi.ship_kr':     ("한국 출하.",     ["픽업", "선적", "B/L 수령"], None),
    'logi.ship_vn':     ("베트남 출하.",   ["픽업", "선적", "B/L 수령"], None),
    'logi.customs':     ("통관.",          ["수출 신고", "통관 완료"], None),
    'logi.delivery':    ("현지 인도.",     ["현지 수령 확인"], None),
    'logi.setup': (
        "현장 설치·시운전.",
        ["설치 완료", "시운전 성공", "사진/영상 보관"],
        None
    ),
    # ── 회계 ──
    'finance.invoice': ("세금계산서/INVOICE 발행.", ["발행 완료", "고객 송부"], None),
    'finance.receipt': ("수금.",                  ["수금 확인", "회계 처리"], None),
    'finance.payment': ("대금 지급.",             ["공급사 정산", "회계 처리"], None),
    # ── IC ──
    'ic.kr_sale_to_vn': (
        "본사(KR) → 베트남(VN) 자재 또는 가공품 매출 거래.",
        ["IC INVOICE 발행", "관세·증빙", "VN 측 매입과 페어 매칭"],
        "/workflow/ic_pairs"
    ),
    'ic.vn_buy_from_kr': (
        "베트남 법인의 본사 매입 처리.",
        ["IC PO 발행", "수입 신고", "본사 매출과 페어"],
        "/workflow/ic_pairs"
    ),
    'ic.vn_sale_to_kr': (
        "베트남(VN) → 본사(KR) 가공품 매출.",
        ["IC INVOICE 발행 (VN)", "본사 매입과 페어"],
        "/workflow/ic_pairs"
    ),
    'ic.kr_buy_from_vn': (
        "본사의 베트남 매입 처리.",
        ["IC PO 발행 (KR)", "VN 매출과 페어"],
        "/workflow/ic_pairs"
    ),
    'ic.tt_kr_to_vn':   ("KR → VN 송금.", ["송금 의뢰", "착금 확인"], None),
    'ic.tt_vn_to_kr':   ("VN → KR 송금.", ["송금 의뢰", "착금 확인"], None),
    # ── AS ──
    'as.handover': ("고객 인수인계.", ["사용자 교육", "도면·메뉴얼 전달"], None),
    'as.warranty': ("보증 기간 관리.", ["보증 시작일 등록", "정기 점검"], None),
    'as.followup': ("AS 대응.",        ["이슈 접수", "조치", "재발 방지"], "/issues"),
}


def migrate(db_path: str) -> dict:
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    # 신규 테이블
    c.executescript(SCHEMA)

    # workflow_nodes_master 컬럼 추가
    added = []
    for col, typ in [('sop_guide', 'TEXT'),
                      ('deliverables_json', 'TEXT'),
                      ('system_link_template', 'TEXT')]:
        if not _has_col(c, 'workflow_nodes_master', col):
            c.execute(f"ALTER TABLE workflow_nodes_master ADD COLUMN {col} {typ}")
            added.append(col)

    # 시드 (UPDATE)
    n_updated = 0
    for code, (sop, dels, link) in NODE_META.items():
        r = c.execute(
            "UPDATE workflow_nodes_master SET sop_guide=?, deliverables_json=?, system_link_template=? WHERE node_code=?",
            (sop, json.dumps(dels, ensure_ascii=False), link, code)
        )
        if r.rowcount:
            n_updated += 1

    conn.commit()
    conn.close()
    return {'added_cols': added, 'meta_updated': n_updated}


if __name__ == '__main__':
    here = os.path.dirname(os.path.abspath(__file__))
    db = os.path.normpath(os.path.join(here, '..', '..', 'data', 'knk.db'))
    print(migrate(db))
