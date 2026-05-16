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
from fastapi.responses import RedirectResponse, JSONResponse, HTMLResponse
from datetime import date, datetime
import json


# ──────────────────────────────────────────────────────────────────────────
# z105b: 마법사 권한 정책 (대표 결재 2026-05-16 (a)+(d))
#   허용: admin / ceo + 영업·PM·경영·기획·관리 부서
# ──────────────────────────────────────────────────────────────────────────
_WIZARD_DEPTS = {'영업', '영업팀', 'PM', '경영', '경영기획', '기획', '관리', '관리팀'}


def _can_run_wizard(user) -> bool:
    if not user:
        return False
    role = (user.get('role') or '').lower()
    if role in ('admin', 'ceo'):
        return True
    dept = user.get('dept') or user.get('team_name') or ''
    if dept in _WIZARD_DEPTS:
        return True
    # 추가: position에 '팀장','부장','이사','대표' 들어가면 허용
    pos = (user.get('position') or '').strip()
    if any(k in pos for k in ('팀장', '부장', '이사', '대표', '관리자')):
        return True
    return False


def _deny_wizard_html(reason: str = "") -> HTMLResponse:
    body = f"""<!doctype html><html lang="ko"><head><meta charset="utf-8"><title>권한 없음</title>
<style>body{{font-family:system-ui;background:#f8fafc;display:flex;align-items:center;justify-content:center;height:100vh;margin:0}}
.card{{background:#fff;border:1px solid #e2e8f0;border-radius:12px;padding:40px;max-width:480px;text-align:center;box-shadow:0 4px 20px rgba(0,0,0,.05)}}
h1{{font-size:20px;color:#dc2626;margin:0 0 12px}}
p{{color:#475569;font-size:13.5px;line-height:1.6}}
a{{display:inline-block;margin-top:16px;padding:8px 16px;background:#6366f1;color:#fff;border-radius:6px;text-decoration:none;font-size:13px}}</style>
</head><body><div class="card">
<h1>⛔ 워크플로우 마법사 권한 없음</h1>
<p>마법사 등록·재실행은 <strong>관리자·CEO·영업·PM·경영기획·팀장급</strong>만 가능합니다.
{('<br><br>' + reason) if reason else ''}<br><br>
일반 직원은 <strong>📥 내 할 일</strong>에서 본인 담당 노드를 처리하시면 됩니다.</p>
<a href="/workflow/my">📥 내 할 일 →</a>
<a href="/workflow" style="background:#94a3b8">← 워크플로우 허브</a>
</div></body></html>"""
    return HTMLResponse(body, status_code=403)


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
                   node_count=node_count, ic_pending=ic_pending,
                   can_run_wizard=_can_run_wizard(user))

    # ────────────────────────────────────────────────────────────
    # /workflow/wizard — 8문항 마법사 (GET=폼, POST=조립)
    # ────────────────────────────────────────────────────────────
    @app.get("/workflow/wizard")
    def workflow_wizard_form(request: Request, project_id: int = 0, template: str = ""):
        user = get_user(request)
        if not user:
            return RedirectResponse("/login", 303)
        # z105b: 권한 게이트
        if not _can_run_wizard(user):
            return _deny_wizard_html()
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
            # z105b: 대상 프로젝트에 이미 워크플로우가 있는지 확인 (재실행 경고용)
            existing_wf = None
            if project_id:
                existing_wf = c.execute("""
                    SELECT pw.id, pw.created_at,
                           (SELECT COUNT(*) FROM project_workflow_nodes WHERE workflow_id=pw.id) AS n_nodes,
                           (SELECT COUNT(*) FROM project_workflow_nodes WHERE workflow_id=pw.id AND status='done') AS n_done
                    FROM project_workflow pw WHERE pw.project_id=? ORDER BY pw.id DESC LIMIT 1
                """, (project_id,)).fetchone()
        return ctx(request, "workflow/wizard.html", user=user,
                   countries=countries, projects=projects,
                   project_id=project_id, tpl_row=tpl_row,
                   existing_wf=existing_wf)

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
        # z106: 제조구분 4섹션
        mfg_machining: str = Form("KR"),
        mfg_assembly: str = Form("KR"),
        mfg_electrical: str = Form("KR"),
        mfg_verification: str = Form("KR"),
        # z106: 출하/셋업 (KR|VN|BOTH|NONE)
        ship_split: str = Form("KR"),
        setup_split: str = Form("NONE"),
        # 구버전 호환 (기존 폼이 보낼 경우)
        processing_loc: str = Form(""),
        ship_entity: str = Form(""),
        setup_loc: str = Form(""),
        mode: str = Form("preserve"),
        rebuild_reason: str = Form(""),
    ):
        # z106: 구버전 폼 호환 — 새 필드 미입력 시 구필드 값 사용
        if not ship_split or ship_split == 'KR':
            if ship_entity in ('KR', 'VN'):
                ship_split = ship_entity
        if setup_split == 'NONE' and setup_loc and setup_loc not in ('NONE',''):
            setup_split = 'KR' if setup_loc == 'KR' else 'VN' if setup_loc == 'VN' else 'NONE'
        # processing_loc → mfg_assembly (구버전 호환 최소 매핑)
        if processing_loc and processing_loc in ('KR','VN','OUT'):
            _legacy = 'KR' if processing_loc == 'KR' else ('VN' if processing_loc == 'VN' else 'KR')
            mfg_assembly = mfg_assembly or _legacy
        user = get_user(request)
        if not user:
            return RedirectResponse("/login", 303)
        # z105b: 권한 게이트
        if not _can_run_wizard(user):
            return _deny_wizard_html()

        with db_session() as c:
            # 템플릿 id 조회
            tid = None
            if template_code:
                row = c.execute("SELECT id FROM workflow_templates WHERE code=?", (template_code,)).fetchone()
                if row:
                    tid = row[0]

            # 프로젝트 메타 업데이트 (ship_entity는 ship_split 의 KR/VN 만, BOTH 는 'KR' 로 기록)
            _proj_ship = ship_split if ship_split in ('KR','VN') else 'KR'
            c.execute("""UPDATE projects SET customer_country=?, po_entity=?, ship_entity=?
                         WHERE id=?""",
                      (customer_country, po_entity, _proj_ship, project_id))

            existing = c.execute(
                "SELECT id FROM project_workflow WHERE project_id=? ORDER BY id DESC LIMIT 1",
                (project_id,)
            ).fetchone()

            if existing and mode == 'preserve':
                # z105b: 보존 모드 — 메타데이터만 갱신
                c.execute("""UPDATE project_workflow
                             SET template_id=?, customer_country=?, po_entity=?,
                                 mech_design_split=?, elec_design_split=?, sw_design_split=?,
                                 processing_loc=?, ship_entity=?, setup_loc=?,
                                 mfg_machining=?, mfg_assembly=?, mfg_electrical=?, mfg_verification=?,
                                 ship_split=?, setup_split=?,
                                 updated_at=datetime('now','localtime')
                             WHERE id=?""",
                          (tid, customer_country, po_entity,
                           mech_design_split, elec_design_split, sw_design_split,
                           processing_loc or mfg_assembly, _proj_ship, setup_split,
                           mfg_machining, mfg_assembly, mfg_electrical, mfg_verification,
                           ship_split, setup_split, existing[0]))
                # 감사 로그
                try:
                    c.execute("""INSERT INTO workflow_handoffs
                                 (workflow_id, from_node_id, to_node_id, triggered_by, message)
                                 VALUES (?, NULL, 0, ?, ?)""",
                              (existing[0], user.get('id'),
                               f"[메타 업데이트] {user.get('name','?')} 마법사 재실행 (보존 모드)"))
                except Exception:
                    pass
                return RedirectResponse(f"/workflow/project/{project_id}", 303)

            # 재조립 모드 (또는 신규 등록)
            if existing:
                # 감사 로그 (삭제 직전)
                try:
                    c.execute("""INSERT INTO workflow_handoffs
                                 (workflow_id, from_node_id, to_node_id, triggered_by, message)
                                 VALUES (?, NULL, 0, ?, ?)""",
                              (existing[0], user.get('id'),
                               f"[재조립] {user.get('name','?')} — 사유: {rebuild_reason or '(미입력)'} — 기존 워크플로우 삭제"))
                except Exception:
                    pass
                c.execute("DELETE FROM project_workflow WHERE project_id=?", (project_id,))

            _cur = c.execute("""INSERT INTO project_workflow
                         (project_id,template_id,customer_country,po_entity,
                          mech_design_split,elec_design_split,sw_design_split,
                          processing_loc,ship_entity,setup_loc,
                          mfg_machining,mfg_assembly,mfg_electrical,mfg_verification,
                          ship_split,setup_split,
                          status,created_by)
                         VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,'active',?)""",
                      (project_id, tid, customer_country, po_entity,
                       mech_design_split, elec_design_split, sw_design_split,
                       processing_loc or mfg_assembly, _proj_ship, setup_split,
                       mfg_machining, mfg_assembly, mfg_electrical, mfg_verification,
                       ship_split, setup_split, user.get('id')))
            wf_id = _cur.lastrowid

            # z106: 새 시그니처로 노드 조립
            node_codes = _assemble_nodes_v2(
                customer_country, po_entity,
                mech_design_split, elec_design_split, sw_design_split,
                mfg_machining, mfg_assembly, mfg_electrical, mfg_verification,
                ship_split, setup_split
            )

            for seq, code in enumerate(node_codes, start=1):
                assigned = _decide_entity_v2(code, po_entity, ship_split)
                _cur2 = c.execute("""INSERT INTO project_workflow_nodes
                             (workflow_id,node_code,seq,assigned_entity,status)
                             VALUES (?,?,?,?,'pending')""",
                          (wf_id, code, seq, assigned))
                pwfn_id = _cur2.lastrowid
                _seed_checkpoints(c, pwfn_id, code)

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
        handoff_to = None
        with db_session() as c:
            done_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S") if status == 'done' else None
            c.execute("""UPDATE project_workflow_nodes
                         SET status=?, done_at=?, note=?
                         WHERE id=?""", (status, done_at, note, node_id))
            # z105: 자동 핸드오프 — done 시 다음 노드 in_progress 후보로 표시 + 알림
            if status == 'done':
                handoff_to = _auto_handoff(c, node_id, user.get('id'))
        return JSONResponse({"ok": True, "status": status, "done_at": done_at,
                              "handoff_to": handoff_to})

    # ────────────────────────────────────────────────────────────
    # z105: 노드 상세 페이지 (5W 가이드)
    # ────────────────────────────────────────────────────────────
    @app.get("/workflow/node/{pwfn_id}")
    def workflow_node_detail(request: Request, pwfn_id: int):
        user = get_user(request)
        if not user:
            return RedirectResponse("/login", 303)
        with db_session() as c:
            n = c.execute("""
                SELECT n.*, m.title_ko, m.category, m.default_dept, m.est_hours,
                       m.is_ic, m.ic_direction, m.sop_guide, m.deliverables_json,
                       m.system_link_template,
                       pw.project_id AS project_id, pw.id AS workflow_id,
                       p.name AS project_name, p.mgmt_code
                FROM project_workflow_nodes n
                JOIN workflow_nodes_master m ON m.node_code=n.node_code
                JOIN project_workflow pw ON pw.id=n.workflow_id
                JOIN projects p ON p.id=pw.project_id
                WHERE n.id=?
            """, (pwfn_id,)).fetchone()
            if not n:
                return RedirectResponse("/workflow", 303)

            # 체크포인트 조회 (없으면 시드)
            cps = c.execute("""SELECT * FROM project_workflow_node_checkpoints
                                WHERE pwfn_id=? ORDER BY seq""", (pwfn_id,)).fetchall()
            if not cps and n['deliverables_json']:
                _seed_checkpoints(c, pwfn_id, n['node_code'])
                cps = c.execute("""SELECT * FROM project_workflow_node_checkpoints
                                    WHERE pwfn_id=? ORDER BY seq""", (pwfn_id,)).fetchall()

            # 이전/다음 노드
            prev_n = c.execute("""SELECT id, node_code, seq FROM project_workflow_nodes
                                   WHERE workflow_id=? AND seq<? ORDER BY seq DESC LIMIT 1""",
                                (n['workflow_id'], n['seq'])).fetchone()
            next_n = c.execute("""SELECT id, node_code, seq FROM project_workflow_nodes
                                   WHERE workflow_id=? AND seq>? ORDER BY seq ASC LIMIT 1""",
                                (n['workflow_id'], n['seq'])).fetchone()
            # 사용자 목록 (담당자 지정용)
            users = c.execute("""SELECT id, name, email FROM users
                                  WHERE is_active=1 ORDER BY name LIMIT 300""").fetchall()
            # 담당자 정보
            assignee = None
            if n['assigned_user_id']:
                assignee = c.execute("SELECT id, name FROM users WHERE id=?",
                                      (n['assigned_user_id'],)).fetchone()

        # 시스템 링크 템플릿 치환
        sys_link = None
        if n['system_link_template']:
            sys_link = n['system_link_template'].replace('{project_id}', str(n['project_id']))

        return ctx(request, "workflow/node_detail.html", user=user,
                   n=n, checkpoints=cps, prev_n=prev_n, next_n=next_n,
                   users=users, assignee=assignee, sys_link=sys_link)

    # 담당자 지정
    @app.post("/workflow/node/{pwfn_id}/assign")
    def workflow_node_assign(request: Request, pwfn_id: int,
                              user_id: str = Form("")):
        user = get_user(request)
        if not user:
            return JSONResponse({"ok": False, "error": "auth"}, 401)
        uid = int(user_id) if user_id and user_id.isdigit() else None
        with db_session() as c:
            c.execute("UPDATE project_workflow_nodes SET assigned_user_id=? WHERE id=?",
                      (uid, pwfn_id))
            # 알림
            if uid:
                _notify_user(c, uid, pwfn_id, "워크플로우 노드 담당으로 지정됨", user.get('id'))
        return JSONResponse({"ok": True, "assigned_user_id": uid})

    # 체크포인트 토글
    @app.post("/workflow/checkpoint/{cp_id}/toggle")
    def workflow_cp_toggle(request: Request, cp_id: int):
        user = get_user(request)
        if not user:
            return JSONResponse({"ok": False, "error": "auth"}, 401)
        with db_session() as c:
            row = c.execute("SELECT is_done FROM project_workflow_node_checkpoints WHERE id=?",
                             (cp_id,)).fetchone()
            if not row:
                return JSONResponse({"ok": False, "error": "not_found"}, 404)
            new_v = 0 if row[0] else 1
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S") if new_v else None
            c.execute("""UPDATE project_workflow_node_checkpoints
                         SET is_done=?, done_by=?, done_at=? WHERE id=?""",
                      (new_v, user.get('id') if new_v else None, now, cp_id))
        return JSONResponse({"ok": True, "is_done": new_v, "done_at": now})

    # ────────────────────────────────────────────────────────────
    # z108: 원샷 완료 — [✓ 끝] 한 번에 처리 (대표 지시 "쉬워야 해")
    #   동작: 모든 체크포인트 done + tasks 자동 생성 + 노드 done + 다음 담당자 알림
    # ────────────────────────────────────────────────────────────
    @app.post("/workflow/node/{pwfn_id}/complete")
    def workflow_node_complete(request: Request, pwfn_id: int,
                                 hours: float = Form(1.0),
                                 note: str = Form("")):
        user = get_user(request)
        if not user:
            return JSONResponse({"ok": False, "error": "auth"}, 401)
        with db_session() as c:
            row = c.execute("""SELECT n.workflow_id, n.node_code, n.status, n.assigned_user_id,
                                      m.title_ko, m.default_dept,
                                      pw.project_id
                               FROM project_workflow_nodes n
                               JOIN workflow_nodes_master m ON m.node_code=n.node_code
                               JOIN project_workflow pw ON pw.id=n.workflow_id
                               WHERE n.id=?""", (pwfn_id,)).fetchone()
            if not row:
                return JSONResponse({"ok": False, "error": "not_found"}, 404)
            now_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            # 1) 체크포인트 일괄 done
            c.execute("""UPDATE project_workflow_node_checkpoints
                         SET is_done=1, done_by=?, done_at=?
                         WHERE pwfn_id=? AND is_done=0""",
                      (user.get('id'), now_ts, pwfn_id))
            # 2) tasks 자동 생성 (오늘자, 시간 입력값)
            today = date.today().isoformat()
            existing_task = c.execute(
                "SELECT id FROM tasks WHERE user_id=? AND work_date=? AND workflow_node_id=?",
                (user.get('id'), today, pwfn_id)
            ).fetchone()
            if not existing_task:
                c.execute("""INSERT INTO tasks
                             (user_id, work_date, title, category, project_id,
                              status, hours, notes, workflow_node_id)
                             VALUES (?,?,?,?,?,'완료',?,?,?)""",
                          (user.get('id'), today, row['title_ko'],
                           row['default_dept'] or '기타', row['project_id'],
                           hours, note, pwfn_id))
            else:
                c.execute("""UPDATE tasks
                             SET status='완료', hours=COALESCE(hours,0)+?, notes=COALESCE(notes,'')||?
                             WHERE id=?""",
                          (hours, ('\n' + note) if note else '', existing_task[0]))
            # 3) 노드 done 처리
            c.execute("""UPDATE project_workflow_nodes
                         SET status='done', done_at=?, note=COALESCE(note,'')||?
                         WHERE id=?""",
                      (now_ts, ('\n' + note) if note else '', pwfn_id))
            # 4) 자동 핸드오프
            handoff = _auto_handoff(c, pwfn_id, user.get('id'))
        return JSONResponse({
            "ok": True,
            "handoff_to": handoff,
            "msg": "완료 처리 + 일일업무 자동 등록 + 다음 담당자 알림"
        })

    # 노드 메모(note) 저장
    @app.post("/workflow/node/{pwfn_id}/note")
    def workflow_node_note(request: Request, pwfn_id: int, note: str = Form("")):
        user = get_user(request)
        if not user:
            return JSONResponse({"ok": False, "error": "auth"}, 401)
        with db_session() as c:
            c.execute("UPDATE project_workflow_nodes SET note=? WHERE id=?", (note, pwfn_id))
        return JSONResponse({"ok": True})

    # ────────────────────────────────────────────────────────────
    # z108c: 4가지 형태 시각 순서도 (참고자료 엑셀 1:1 매칭)
    # ────────────────────────────────────────────────────────────
    @app.get("/workflow/scenarios")
    def workflow_scenarios_view(request: Request, tab: str = "T1"):
        user = get_user(request)
        if not user:
            return RedirectResponse("/login", 303)
        from . import workflow_scenarios as _ws
        return ctx(request, "workflow/scenarios.html", user=user,
                   scenarios=_ws.SCENARIOS, depts=_ws.DEPTS, sel_tab=tab)

    # ────────────────────────────────────────────────────────────
    # z107: 팀 업무카드 칸반 (팀장 전용)
    # ────────────────────────────────────────────────────────────
    @app.get("/workflow/team")
    def workflow_team_kanban(request: Request, dept: str = ""):
        user = get_user(request)
        if not user:
            return RedirectResponse("/login", 303)
        # 권한 게이트: 팀장/임원/CEO/admin
        role = (user.get('role') or '').lower()
        pos = (user.get('position') or '')
        is_leader = (role in ('admin','ceo','leader','manager') or
                     any(k in pos for k in ('팀장','부장','이사','대표','관리자')))
        if not is_leader:
            return _deny_wizard_html("팀 업무카드는 팀장급만 열람 가능합니다.")

        with db_session() as c:
            # 부서 목록 (실제 사용 중인 default_dept)
            depts = [r[0] for r in c.execute(
                "SELECT DISTINCT default_dept FROM workflow_nodes_master WHERE default_dept IS NOT NULL ORDER BY default_dept"
            ).fetchall()]
            # 기본 부서 = URL 파라미터 or 사용자 본인 부서
            sel_dept = dept or user.get('dept') or user.get('team_name') or (depts[0] if depts else '')
            # 4 컬럼 노드 조회
            cols = {'pending': [], 'in_progress': [], 'blocked': [], 'done': []}
            if sel_dept:
                rows = c.execute("""
                    SELECT n.id, n.node_code, n.seq, n.status, n.assigned_entity, n.assigned_user_id,
                           m.title_ko, m.category, m.default_dept,
                           p.id AS project_id, p.name AS project_name, p.mgmt_code,
                           u.name AS assignee_name
                    FROM project_workflow_nodes n
                    JOIN workflow_nodes_master m ON m.node_code=n.node_code
                    JOIN project_workflow pw ON pw.id=n.workflow_id
                    JOIN projects p ON p.id=pw.project_id
                    LEFT JOIN users u ON u.id=n.assigned_user_id
                    WHERE m.default_dept=?
                    ORDER BY p.id DESC, n.seq
                """, (sel_dept,)).fetchall()
                for r in rows:
                    s = r['status']
                    if s in cols:
                        cols[s].append(dict(r))
                    elif s == 'skipped':
                        # 생략은 별도 컬럼 만들지 않고 done과 함께
                        cols['done'].append(dict(r))

        return ctx(request, "workflow/team.html", user=user,
                   depts=depts, sel_dept=sel_dept, cols=cols)

    # ────────────────────────────────────────────────────────────
    # z105: 내 할 일 (My todos)
    # ────────────────────────────────────────────────────────────
    @app.get("/workflow/my")
    def workflow_my_todos(request: Request):
        user = get_user(request)
        if not user:
            return RedirectResponse("/login", 303)
        with db_session() as c:
            # 1) 내가 직접 배정된 노드
            mine = c.execute("""
                SELECT n.id, n.node_code, n.seq, n.status, n.assigned_entity,
                       m.title_ko, m.category, m.default_dept,
                       p.id AS project_id, p.name AS project_name, p.mgmt_code
                FROM project_workflow_nodes n
                JOIN workflow_nodes_master m ON m.node_code=n.node_code
                JOIN project_workflow pw ON pw.id=n.workflow_id
                JOIN projects p ON p.id=pw.project_id
                WHERE n.assigned_user_id=? AND n.status IN ('pending','in_progress','blocked')
                ORDER BY n.status DESC, p.id DESC, n.seq
            """, (user.get('id'),)).fetchall()
            # 2) 내 부서 default_dept 인데 미배정 (팀원 누구든 잡을 수 있음)
            dept = (user.get('dept') or user.get('team_name') or '') or ''
            dept_unassigned = []
            if dept:
                dept_unassigned = c.execute("""
                    SELECT n.id, n.node_code, n.seq, n.status, n.assigned_entity,
                           m.title_ko, m.category, m.default_dept,
                           p.id AS project_id, p.name AS project_name, p.mgmt_code
                    FROM project_workflow_nodes n
                    JOIN workflow_nodes_master m ON m.node_code=n.node_code
                    JOIN project_workflow pw ON pw.id=n.workflow_id
                    JOIN projects p ON p.id=pw.project_id
                    WHERE m.default_dept=? AND n.assigned_user_id IS NULL
                      AND n.status IN ('pending','in_progress')
                    ORDER BY p.id DESC, n.seq LIMIT 50
                """, (dept,)).fetchall()
        return ctx(request, "workflow/my.html", user=user,
                   mine=mine, dept_unassigned=dept_unassigned, dept=dept)

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


# ──────────────────────────────────────────────────────────────────────────
# z105: 가이드형 워크플로우 헬퍼
# ──────────────────────────────────────────────────────────────────────────

def _seed_checkpoints(c, pwfn_id, node_code):
    """노드 마스터의 deliverables_json → 체크포인트 인스턴스 생성."""
    row = c.execute("SELECT deliverables_json FROM workflow_nodes_master WHERE node_code=?",
                     (node_code,)).fetchone()
    if not row or not row[0]:
        return 0
    try:
        items = json.loads(row[0])
    except Exception:
        return 0
    if not isinstance(items, list):
        return 0
    for i, label in enumerate(items, start=1):
        c.execute("""INSERT INTO project_workflow_node_checkpoints
                     (pwfn_id, label, seq, is_done) VALUES (?,?,?,0)""",
                  (pwfn_id, str(label), i))
    return len(items)


def _auto_handoff(c, from_node_id, by_user_id):
    """노드 done → 다음 노드 자동 'in_progress' 전환 + 알림 로그.

    반환: {to_node_id, to_user_id, message} 또는 None
    """
    row = c.execute("""SELECT n.workflow_id, n.seq, m.title_ko
                       FROM project_workflow_nodes n
                       JOIN workflow_nodes_master m ON m.node_code=n.node_code
                       WHERE n.id=?""", (from_node_id,)).fetchone()
    if not row:
        return None
    wf_id, seq, prev_title = row[0], row[1], row[2]
    nxt = c.execute("""SELECT n.id, n.assigned_user_id, n.status, m.title_ko, m.default_dept
                       FROM project_workflow_nodes n
                       JOIN workflow_nodes_master m ON m.node_code=n.node_code
                       WHERE n.workflow_id=? AND n.seq>? AND n.status NOT IN ('done','skipped')
                       ORDER BY n.seq ASC LIMIT 1""", (wf_id, seq)).fetchone()
    if not nxt:
        return None
    to_id = nxt[0]
    to_uid = nxt[1]
    next_title = nxt[3]
    next_dept = nxt[4]
    if nxt[2] == 'pending':
        c.execute("UPDATE project_workflow_nodes SET status='in_progress' WHERE id=?", (to_id,))

    msg = f"이전 단계 '{prev_title}' 완료 → 다음 '{next_title}' ({next_dept}) 시작"
    notified = []
    if to_uid:
        _notify_user(c, to_uid, to_id, msg, by_user_id)
        notified.append(to_uid)
    c.execute("""INSERT INTO workflow_handoffs
                 (workflow_id, from_node_id, to_node_id, triggered_by, notified_users, message)
                 VALUES (?,?,?,?,?,?)""",
              (wf_id, from_node_id, to_id, by_user_id,
               ','.join(str(x) for x in notified), msg))
    return {'to_node_id': to_id, 'to_user_id': to_uid, 'message': msg}


def _notify_user(c, target_uid, pwfn_id, message, by_uid):
    """알림 테이블에 insert. notifications 스키마는 기존 시스템 따름.
    실패해도 트랜잭션 영향 없도록 try."""
    try:
        # notifications(user_id, type, title, body, link, created_at)
        link = f"/workflow/node/{pwfn_id}"
        c.execute("""INSERT INTO notifications (user_id, type, title, body, link)
                     VALUES (?, 'workflow', ?, ?, ?)""",
                  (target_uid, '[워크플로우]', message, link))
    except Exception:
        # 스키마 다를 경우 패스
        try:
            c.execute("""INSERT INTO notifications (user_id, message, link)
                         VALUES (?,?,?)""", (target_uid, message, f"/workflow/node/{pwfn_id}"))
        except Exception:
            pass


# ──────────────────────────────────────────────────────────────────────────
# z106: 마법사 v2 — 새 조립 알고리즘 (제조구분 4섹션 + 출하/셋업 3옵션)
# ──────────────────────────────────────────────────────────────────────────

def _split_to_nodes(base, split):
    """split: 'KR' | 'VN' | 'BOTH' → 노드 코드 리스트."""
    if split == 'KR':
        return [f'{base}_kr']
    if split == 'VN':
        return [f'{base}_vn']
    if split == 'BOTH':
        return [f'{base}_kr', f'{base}_vn']
    return [f'{base}_kr']


def _assemble_nodes_v2(customer_country, po_entity,
                       mech, elec, sw,
                       mfg_machining, mfg_assembly, mfg_electrical, mfg_verification,
                       ship_split, setup_split):
    """z106: 새 마법사 응답으로 노드 리스트 조립."""
    out = []
    # 공통 영업
    out += ['sales.lead', 'sales.meeting', 'sales.requirement',
            'sales.quote', 'sales.po_receive', 'sales.contract']
    out += ['design.spec', 'design.bom']

    # 설계 분담 (기구·전장·SW)
    for kind, split in (('mech', mech), ('elec', elec), ('sw', sw)):
        out += _split_to_nodes(f'design.{kind}', split)
    out.append('design.review')

    # 자재
    out += ['purchase.new_review', 'purchase.po_issue', 'purchase.receive']

    # IC 자재 판매 (PO=KR, 가공/조립 일부라도 VN 이면 자재가 VN으로 이동)
    mfg_uses_vn = any(s in ('VN', 'BOTH') for s in
                       (mfg_machining, mfg_assembly, mfg_electrical, mfg_verification))
    mfg_uses_kr = any(s in ('KR', 'BOTH') for s in
                       (mfg_machining, mfg_assembly, mfg_electrical, mfg_verification))
    if po_entity == 'KR' and mfg_uses_vn:
        out += ['ic.kr_sale_to_vn', 'ic.vn_buy_from_kr']
    if po_entity == 'VN' and mfg_uses_kr:
        out += ['ic.vn_sale_to_kr', 'ic.kr_buy_from_vn']

    # 제조 4섹션 — 가공·조립·전장·검증
    out += _split_to_nodes('mfg.machining',    mfg_machining)
    out += _split_to_nodes('mfg.assembly',     mfg_assembly)
    out += _split_to_nodes('mfg.electrical',   mfg_electrical)
    out += _split_to_nodes('mfg.verification', mfg_verification)

    # 일반 품질
    out += ['qa.in_inspect', 'qa.in_process', 'qa.final', 'qa.fat']

    # IC 가공품 매출 (가공이 VN 인데 PO=KR — 가공품을 KR이 사들임)
    if po_entity == 'KR' and mfg_uses_vn:
        out += ['ic.vn_sale_to_kr', 'ic.kr_buy_from_vn']
    if po_entity == 'VN' and mfg_uses_kr:
        out += ['ic.kr_sale_to_vn', 'ic.vn_buy_from_kr']

    # 물류 — 출하
    out.append('logi.packing')
    is_export = (customer_country not in ('KR',))
    if is_export:
        out.append('logi.export_doc')
    if ship_split in ('KR', 'BOTH'):
        out.append('logi.ship_kr')
    if ship_split in ('VN', 'BOTH'):
        out.append('logi.ship_vn')
    if is_export:
        out.append('logi.customs')
    out.append('logi.delivery')

    # 셋업
    if setup_split and setup_split != 'NONE':
        out.append('logi.setup')
        out.append('qa.sat')

    # 회계
    out += ['finance.invoice', 'finance.receipt']

    # IC 송금
    if po_entity == 'KR' and mfg_uses_vn:
        out.append('ic.tt_kr_to_vn')
    if po_entity == 'VN' and mfg_uses_kr:
        out.append('ic.tt_vn_to_kr')

    # AS
    out += ['as.handover', 'as.warranty']

    # 중복 제거 (순서 유지)
    seen = set()
    final = []
    for n in out:
        if n not in seen:
            seen.add(n)
            final.append(n)
    return final


def _decide_entity_v2(node_code, po_entity, ship_split):
    """z106: 노드에 법인 할당. _kr 접미는 KR, _vn 접미는 VN, ic 노드는 코드 기반."""
    if node_code.endswith('_kr') or '.kr_' in node_code or node_code.startswith('ic.kr_'):
        return 'KR'
    if node_code.endswith('_vn') or '.vn_' in node_code or node_code.startswith('ic.vn_'):
        return 'VN'
    if node_code.startswith('logi.ship_'):
        return 'VN' if 'vn' in node_code else 'KR'
    if node_code.startswith('sales.') or node_code.startswith('finance.') or node_code.startswith('as.'):
        return po_entity
    return po_entity
