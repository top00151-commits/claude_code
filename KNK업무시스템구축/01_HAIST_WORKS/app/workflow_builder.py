"""
v5H226z104 (2026-05-16) — 워크플로우 레고 빌더 라우트 모듈

대표 결재: 2026-05-16 (c) 1+2차 통합 GO

기능:
  - /workflow                     워크플로우 허브 (시나리오 선택 + 마법사 진입)
  - /workflow/wizard              8문항 마법사 (POST 시 워크플로우 생성)
  - /workflow/project/<id>        프로젝트 워크플로우 체크리스트 + 매트릭스
  - /workflow/project/<id>/node/<node_id>/toggle  (POST) 상태 변경
  - /workflow/project/<id>/ic_pair  (POST) IC 페어 자동 매칭 실행
  - /workflow/ic_pairs            전체 IC 페어 모니터 (회계팀)

워크플로우 조립 알고리즘 (마법사 응답 → 노드 리스트):
  1) 영업/계약 노드는 항상 포함
  2) Q3~Q5 설계 분담 → KR/VN/KR+VN 에 따라 mech/elec/sw 노드 선택
  3) Q6 가공 위치 → prod.kr_assy / prod.vn_assy / prod.outsource
  4) Q1·Q2·Q7 조합 → IC 노드 자동 삽입
     - PO수주=KR, 출하=VN → ic.kr_sale_to_vn + ic.vn_buy_from_kr (자재판매)
                          + ic.vn_sale_to_kr + ic.kr_buy_from_vn (가공품매출)
     - PO수주=VN, 가공=KR (역방향) → ic.kr_sale_to_vn (가공품) + ic.vn_buy_from_kr
  5) 수출 여부 (고객국 ≠ 출하법인) → 수출서류/통관 노드 추가
  6) Q8 setup_loc != 'NONE' → 설치/시운전/SAT 노드 추가
"""

from fastapi import Request, Form
from fastapi.responses import RedirectResponse, JSONResponse
from datetime import date, datetime
import json


# ──────────────────────────────────────────────────────────────────────────
# 라우트 등록 헬퍼 — main.py 에서 register_workflow_routes(app, tpl, ctx, get_user, db_session) 호출
# ──────────────────────────────────────────────────────────────────────────


def register_workflow_routes(app, tpl, ctx, get_user, db_session):
    """main.py에서 호출 — 모든 워크플로우 라우트를 app에 등록."""

    # ────────────────────────────────────────────────────────────
    # /workflow — 허브 (프로젝트 목록 + 시나리오 카드)
    # ────────────────────────────────────────────────────────────
    @app.get("/workflow")
    def workflow_home(request: Request):
        user = get_user(request)
        if not user:
            return RedirectResponse("/login", 303)
        with db_session() as c:
            templates = c.execute("""
                SELECT id, code, title_ko, description,
                       customer_country_hint, po_entity_hint, ship_entity_hint
                FROM workflow_templates WHERE is_active=1
                ORDER BY display_order
            """).fetchall()
            projects = c.execute("""
                SELECT p.id, COALESCE(p.mgmt_code,'') AS mgmt_code, p.name,
                       p.customer_country, p.po_entity, p.ship_entity,
                       (SELECT COUNT(*) FROM project_workflow pw WHERE pw.project_id=p.id) AS has_wf,
                       (SELECT pw.id FROM project_workflow pw WHERE pw.project_id=p.id ORDER BY pw.id DESC LIMIT 1) AS wf_id
                FROM projects p
                ORDER BY p.id DESC LIMIT 100
            """).fetchall()
            node_count = c.execute("SELECT COUNT(*) FROM workflow_nodes_master").fetchone()[0]
            ic_pending = c.execute(
                "SELECT COUNT(*) FROM ic_invoice_pairs WHERE status='pending'"
            ).fetchone()[0]
        return ctx(request, "workflow/home.html", user=user,
                   templates=templates, projects=projects,
                   node_count=node_count, ic_pending=ic_pending)

    # ────────────────────────────────────────────────────────────
    # /workflow/wizard — 8문항 마법사 (GET=폼, POST=조립)
    # ────────────────────────────────────────────────────────────
    @app.get("/workflow/wizard")
    def workflow_wizard_form(request: Request, project_id: int = 0, template: str = ""):
        user = get_user(request)
        if not user:
            return RedirectResponse("/login", 303)
        with db_session() as c:
            countries = c.execute("""
                SELECT code, name_ko, name_en, region
                FROM countries_master WHERE is_active=1 ORDER BY display_order
            """).fetchall()
            projects = c.execute("""
                SELECT id, COALESCE(mgmt_code,'')||' '||COALESCE(name,'') AS label
                FROM projects ORDER BY id DESC LIMIT 200
            """).fetchall()
            tpl_row = None
            if template:
                tpl_row = c.execute(
                    "SELECT * FROM workflow_templates WHERE code=?", (template,)
                ).fetchone()
        return ctx(request, "workflow/wizard.html", user=user,
                   countries=countries, projects=projects,
                   project_id=project_id, tpl_row=tpl_row)

    @app.post("/workflow/wizard")
    def workflow_wizard_submit(
        request: Request,
        project_id: int = Form(...),
        template_code: str = Form(""),
        customer_country: str = Form(...),
        po_entity: str = Form(...),
        mech_design_split: str = Form(...),
        elec_design_split: str = Form(...),
        sw_design_split: str = Form(...),
        processing_loc: str = Form(...),
        ship_entity: str = Form(...),
        setup_loc: str = Form("NONE"),
    ):
        user = get_user(request)
        if not user:
            return RedirectResponse("/login", 303)

        with db_session() as c:
            # 템플릿 id 조회
            tid = None
            if template_code:
                row = c.execute("SELECT id FROM workflow_templates WHERE code=?", (template_code,)).fetchone()
                if row:
                    tid = row[0]

            # 프로젝트 메타 업데이트
            c.execute("""UPDATE projects SET customer_country=?, po_entity=?, ship_entity=?
                         WHERE id=?""",
                      (customer_country, po_entity, ship_entity, project_id))

            # 기존 워크플로우가 있으면 삭제하고 재생성
            c.execute("DELETE FROM project_workflow WHERE project_id=?", (project_id,))

            _cur = c.execute("""INSERT INTO project_workflow
                         (project_id,template_id,customer_country,po_entity,
                          mech_design_split,elec_design_split,sw_design_split,
                          processing_loc,ship_entity,setup_loc,status,created_by)
                         VALUES (?,?,?,?,?,?,?,?,?,?,'active',?)""",
                      (project_id, tid, customer_country, po_entity,
                       mech_design_split, elec_design_split, sw_design_split,
                       processing_loc, ship_entity, setup_loc, user.get('id')))
            wf_id = _cur.lastrowid

            # 노드 조립
            node_codes = _assemble_nodes(
                customer_country, po_entity,
                mech_design_split, elec_design_split, sw_design_split,
                processing_loc, ship_entity, setup_loc
            )

            for seq, code in enumerate(node_codes, start=1):
                # assigned_entity 결정
                assigned = _decide_entity(code, mech_design_split, elec_design_split,
                                          sw_design_split, processing_loc, ship_entity, po_entity)
                c.execute("""INSERT INTO project_workflow_nodes
                             (workflow_id,node_code,seq,assigned_entity,status)
                             VALUES (?,?,?,?,'pending')""",
                          (wf_id, code, seq, assigned))

            # IC 페어 자동 생성
            _auto_create_ic_pairs(c, wf_id, project_id)

        return RedirectResponse(f"/workflow/project/{project_id}", 303)

    # ────────────────────────────────────────────────────────────
    # /workflow/project/<id> — 체크리스트 + 매트릭스
    # ────────────────────────────────────────────────────────────
    @app.get("/workflow/project/{project_id}")
    def workflow_project_view(request: Request, project_id: int):
        user = get_user(request)
        if not user:
            return RedirectResponse("/login", 303)
        with db_session() as c:
            proj = c.execute(
                "SELECT id, COALESCE(mgmt_code,'') AS mgmt_code, name, customer_country, po_entity, ship_entity FROM projects WHERE id=?",
                (project_id,)
            ).fetchone()
            if not proj:
                return RedirectResponse("/workflow", 303)
            wf = c.execute("""SELECT * FROM project_workflow WHERE project_id=?
                              ORDER BY id DESC LIMIT 1""", (project_id,)).fetchone()
            nodes = []
            if wf:
                nodes = c.execute("""
                    SELECT n.id, n.node_code, n.seq, n.assigned_entity, n.assigned_user_id,
                           n.status, n.due_date, n.done_at, n.note,
                           m.title_ko, m.category, m.default_dept, m.est_hours, m.is_ic, m.ic_direction
                    FROM project_workflow_nodes n
                    JOIN workflow_nodes_master m ON m.node_code=n.node_code
                    WHERE n.workflow_id=? ORDER BY n.seq
                """, (wf['id'],)).fetchall()
                ic_pairs = c.execute("""
                    SELECT * FROM ic_invoice_pairs WHERE workflow_id=? ORDER BY id
                """, (wf['id'],)).fetchall()
            else:
                ic_pairs = []
            countries = c.execute(
                "SELECT code, name_ko FROM countries_master WHERE is_active=1 ORDER BY display_order"
            ).fetchall()

        # 매트릭스 집계 (카테고리 × 법인)
        matrix = _build_matrix(nodes)
        progress = _calc_progress(nodes)

        return ctx(request, "workflow/project.html", user=user,
                   proj=proj, wf=wf, nodes=nodes, ic_pairs=ic_pairs,
                   countries=countries, matrix=matrix, progress=progress)

    # ────────────────────────────────────────────────────────────
    # 노드 상태 토글 (AJAX)
    # ────────────────────────────────────────────────────────────
    @app.post("/workflow/node/{node_id}/status")
    def workflow_node_status(request: Request, node_id: int,
                              status: str = Form(...), note: str = Form("")):
        user = get_user(request)
        if not user:
            return JSONResponse({"ok": False, "error": "auth"}, 401)
        if status not in ('pending', 'in_progress', 'done', 'skipped', 'blocked'):
            return JSONResponse({"ok": False, "error": "invalid_status"}, 400)
        with db_session() as c:
            done_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S") if status == 'done' else None
            c.execute("""UPDATE project_workflow_nodes
                         SET status=?, done_at=?, note=?
                         WHERE id=?""", (status, done_at, note, node_id))
        return JSONResponse({"ok": True, "status": status, "done_at": done_at})

    # ────────────────────────────────────────────────────────────
    # IC 페어 모니터 (회계팀)
    # ────────────────────────────────────────────────────────────
    @app.get("/workflow/ic_pairs")
    def workflow_ic_pairs(request: Request, status: str = ""):
        user = get_user(request)
        if not user:
            return RedirectResponse("/login", 303)
        with db_session() as c:
            q = """SELECT p.*, pr.name AS project_name, pr.mgmt_code
                   FROM ic_invoice_pairs p
                   LEFT JOIN projects pr ON pr.id=p.project_id"""
            args = []
            if status:
                q += " WHERE p.status=?"
                args.append(status)
            q += " ORDER BY p.id DESC LIMIT 200"
            pairs = c.execute(q, args).fetchall()
            cnt = c.execute("""
                SELECT status, COUNT(*) AS n FROM ic_invoice_pairs GROUP BY status
            """).fetchall()
        counts = {row['status']: row['n'] for row in cnt}
        return ctx(request, "workflow/ic_pairs.html", user=user,
                   pairs=pairs, counts=counts, status_filter=status)

    @app.post("/workflow/ic_pair/{pair_id}/close")
    def workflow_ic_pair_close(request: Request, pair_id: int,
                                 amount: float = Form(0), currency: str = Form("USD"),
                                 note: str = Form("")):
        user = get_user(request)
        if not user:
            return JSONResponse({"ok": False, "error": "auth"}, 401)
        with db_session() as c:
            c.execute("""UPDATE ic_invoice_pairs
                         SET amount=?, currency=?, status='matched',
                             matched_at=?, note=?
                         WHERE id=?""",
                      (amount, currency, datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                       note, pair_id))
        return JSONResponse({"ok": True})


# ──────────────────────────────────────────────────────────────────────────
# 노드 조립 알고리즘
# ──────────────────────────────────────────────────────────────────────────

def _assemble_nodes(customer_country, po_entity,
                     mech, elec, sw,
                     processing_loc, ship_entity, setup_loc):
    """마법사 응답 → 노드 코드 리스트(순서 보장)."""
    out = []
    # 공통 영업
    out += ['sales.lead', 'sales.meeting', 'sales.requirement',
            'sales.quote', 'sales.po_receive', 'sales.contract']
    out += ['design.spec', 'design.bom']
    # 설계 분담
    for kind, split in (('mech', mech), ('elec', elec), ('sw', sw)):
        if split == 'KR':
            out.append(f'design.{kind}_kr')
        elif split == 'VN':
            out.append(f'design.{kind}_vn')
        elif split == 'KR+VN':
            out.append(f'design.{kind}_kr')
            out.append(f'design.{kind}_vn')
    out += ['design.review',
            'purchase.new_review', 'purchase.po_issue', 'purchase.receive']

    # IC: 자재가 KR에 있고 가공이 VN인 경우 (KR→VN 자재 판매)
    is_export = (customer_country not in ('KR',) and customer_country != ship_entity)
    if processing_loc == 'VN' and po_entity == 'KR':
        out.append('ic.kr_sale_to_vn')
        out.append('ic.vn_buy_from_kr')
    if processing_loc == 'KR' and po_entity == 'VN':
        out.append('ic.vn_sale_to_kr')
        out.append('ic.kr_buy_from_vn')

    # 생산
    if processing_loc == 'KR':
        out.append('prod.kr_assy')
    elif processing_loc == 'VN':
        out.append('prod.vn_assy')
    elif processing_loc == 'OUT':
        out.append('prod.outsource')

    out += ['qa.in_inspect', 'qa.in_process', 'qa.final', 'qa.fat']

    # 가공품 IC 매출 (가공 위치와 수주 법인이 다를 때)
    if processing_loc == 'VN' and po_entity == 'KR':
        out.append('ic.vn_sale_to_kr')
        out.append('ic.kr_buy_from_vn')
    if processing_loc == 'KR' and po_entity == 'VN':
        out.append('ic.kr_sale_to_vn')
        out.append('ic.vn_buy_from_kr')

    # 물류
    out.append('logi.packing')
    if is_export or ship_entity != customer_country:
        out.append('logi.export_doc')
    out.append('logi.ship_vn' if ship_entity == 'VN' else 'logi.ship_kr')
    if is_export:
        out.append('logi.customs')
    out.append('logi.delivery')

    if setup_loc and setup_loc != 'NONE':
        out.append('logi.setup')
        out.append('qa.sat')

    out += ['finance.invoice', 'finance.receipt']

    # IC 송금
    if po_entity == 'KR' and processing_loc == 'VN':
        out.append('ic.tt_kr_to_vn')
    if po_entity == 'VN' and processing_loc == 'KR':
        out.append('ic.tt_vn_to_kr')

    out += ['as.handover', 'as.warranty']

    # 중복 제거 (순서 유지)
    seen = set()
    final = []
    for n in out:
        if n not in seen:
            seen.add(n)
            final.append(n)
    return final


def _decide_entity(node_code, mech, elec, sw, processing_loc, ship_entity, po_entity):
    """노드에 법인 할당."""
    if node_code.endswith('_kr') or '.kr_' in node_code or node_code.startswith('ic.kr_'):
        return 'KR'
    if node_code.endswith('_vn') or '.vn_' in node_code or node_code.startswith('ic.vn_'):
        return 'VN'
    if node_code.startswith('prod.'):
        return {'KR': 'KR', 'VN': 'VN', 'OUT': 'OUT'}.get(processing_loc, 'KR')
    if node_code.startswith('logi.ship_'):
        return 'VN' if 'vn' in node_code else 'KR'
    # 영업·계약·재무 → 수주 법인
    if node_code.startswith('sales.') or node_code.startswith('finance.') or node_code.startswith('as.'):
        return po_entity
    # 기본
    return po_entity


# ──────────────────────────────────────────────────────────────────────────
# IC 페어 자동 매칭
# ──────────────────────────────────────────────────────────────────────────

def _auto_create_ic_pairs(c, wf_id, project_id):
    """워크플로우 노드 중 IC 노드를 양방향 페어로 자동 매칭."""
    rows = c.execute("""
        SELECT n.id, n.node_code, m.ic_direction
        FROM project_workflow_nodes n
        JOIN workflow_nodes_master m ON m.node_code=n.node_code
        WHERE n.workflow_id=? AND m.is_ic=1 ORDER BY n.seq
    """, (wf_id,)).fetchall()

    # 페어 매핑: 매출 노드 ↔ 매입 노드
    pair_map = {
        'ic.kr_sale_to_vn': ('KR', 'VN', 'ic.vn_buy_from_kr'),
        'ic.vn_sale_to_kr': ('VN', 'KR', 'ic.kr_buy_from_vn'),
    }

    # 노드 코드 → id 매핑
    by_code = {}
    for r in rows:
        by_code.setdefault(r['node_code'], []).append(r['id'])

    today = date.today().strftime('%y%m%d')
    seq = 1
    for sell_code, (sell_ent, buy_ent, buy_code) in pair_map.items():
        sells = by_code.get(sell_code, [])
        buys = by_code.get(buy_code, [])
        # 같은 인덱스끼리 페어링
        for i in range(min(len(sells), len(buys))):
            pair_code = f"IC-{today}-{seq:03d}"
            seq += 1
            c.execute("""INSERT INTO ic_invoice_pairs
                         (pair_code,workflow_id,project_id,
                          sell_entity,buy_entity,sell_node_id,buy_node_id,
                          status,currency) VALUES (?,?,?,?,?,?,?,'pending','USD')""",
                      (pair_code, wf_id, project_id, sell_ent, buy_ent,
                       sells[i], buys[i]))


# ──────────────────────────────────────────────────────────────────────────
# 매트릭스 + 진행률 집계
# ──────────────────────────────────────────────────────────────────────────

CATEGORIES_ORDER = ['sales', 'design', 'purchase', 'ic', 'production',
                     'qa', 'logi', 'finance', 'as']
ENTITIES = ['KR', 'VN', 'OUT']


def _build_matrix(nodes):
    """카테고리 × 법인 매트릭스: {cat: {ent: {total, done, in_progress, pending}}}."""
    mat = {cat: {ent: {'total': 0, 'done': 0, 'in_progress': 0, 'pending': 0, 'blocked': 0}
                  for ent in ENTITIES}
            for cat in CATEGORIES_ORDER}
    for n in nodes:
        cat = n['category'] if 'category' in n.keys() else None
        ent = n['assigned_entity'] or 'KR'
        if cat not in mat:
            continue
        if ent not in mat[cat]:
            ent = 'KR'
        mat[cat][ent]['total'] += 1
        st = n['status']
        if st in mat[cat][ent]:
            mat[cat][ent][st] += 1
    return mat


def _calc_progress(nodes):
    total = len(nodes)
    if total == 0:
        return {'total': 0, 'done': 0, 'pct': 0}
    done = sum(1 for n in nodes if n['status'] == 'done')
    return {'total': total, 'done': done, 'pct': round(done * 100 / total)}
