# -*- coding: utf-8 -*-
# ============================================================
# v5H226z1053 (2026-07-25, ERP V1 전환 WP-03) — 프로젝트 호기 (Project Unit)
# 대표 업무교정(07-25) + 게이트 v3 판정(F-01~F-09) 반영본
# ------------------------------------------------------------
# ⭐ 영구 식별자 계약 (F-05 · 문서·주석·화면 통일 문구):
#    장비 Unit 의 시스템 영구 식별자는 `project_units.id` 이다.
#    관리번호, 현재 호기번호 및 연결된 수주번호는 사용자가 장비를 찾고 업무 관계를 확인하기 위한
#    표시·검색 정보이며 영구 식별자가 아니다.
#
# KNK 업무 사실:
#   · 일련번호(S/N) 미사용.
#   · 개발호기로 시작하고 개발·수주 변경에 따라 호기번호·구성이 바뀐다.
#   · ⭐ **관리번호 1개에 수주번호가 여러 개** 붙고, **같은 호기가 최초·추가·변경 수주에 모두**
#     나타나는 것은 오류가 아니라 정상 업무다(F-02).
#
# V1 핵심 규칙:
#   [F-01] 후보 반영 시 후보 라벨은 working_name·seed_* 에만 보존.
#          **사용자가 명시 지정하기 전까지 current_unit_no 는 NULL**(미확정을 사실로 승격 금지).
#   [F-02] 같은 호기번호가 여러 수주에 있는 것은 정상 → 차단하지 않고
#          '기존 Unit 에 연결(ORIGIN/ADDITIONAL/CHANGE)' vs '신규 개발호기' 를 사용자가 선택.
#   [F-06] 한 관리번호 안에서 **한 번 쓴 호기번호는 재사용 금지**(취소분 포함).
#   [F-07] 과거 조회는 **effective_from/to** 기준(changed_at 은 audit 시각).
#   [F-08] 법인은 프로젝트 확정값만 사용. **빈값·충돌이면 중단**(KOR 자동부여 폐지).
#   [F-09] 권한은 업무 역할 기준(조회/개발호기 생성/수주연결/번호지정·변경/확정/취소).
#   ⛔ 분할·통합은 구조만(실행·승인 없음) · 영향분석 미연동 사실대로 표시.
# ============================================================
import re
import sqlite3

from .database import db_session, _logi_now

# 정식 호기 라벨(기존 시스템 규약·z779). 부속/부품(비표준 라벨)은 후보에서 제외.
HOGI_RE = re.compile(r"^\d+호기$")
_HOGI_NUM_RE = re.compile(r"^0*(\d+)호기$")
_VN_SIG = ("VN", "VNM", "VINA", "VIETNAM", "베트남")
_KOR_SIG = ("KR", "KOR", "KOREA", "한국", "본사", "HQ")

IDENTITY_CONTRACT = (
    "장비 Unit 의 시스템 영구 식별자는 project_units.id 이다. "
    "관리번호·현재 호기번호·연결된 수주번호는 사용자가 장비를 찾고 업무 관계를 확인하기 위한 "
    "표시·검색 정보이며 영구 식별자가 아니다.")

# ── 영향 분석 대상(WP-04 이후 연동) ─────────────────────────────
IMPACT_SOURCES = (
    ("bom_unit_baselines", "project_unit_id", "BOM 기준"),
    ("po_items", "project_unit_id", "발주"),
    ("receipts", "project_unit_id", "입고"),
    ("issues_out", "project_unit_id", "생산 투입"),
    ("shipments", "project_unit_id", "출하"),
)
IMPACT_NOT_WIRED_MSG = (
    "BOM·발주·생산 영향 분석은 아직 연동되지 않았습니다. "
    "영향 확인이 필요한 호기 변경은 승인 처리할 수 없습니다.")

# 후보 판정(사용자가 고르는 선택지)
CAND_NEW = "new"                 # 신규 개발호기 후보
CAND_LINK = "link"               # 기존 Unit 에 수주 연결(관계 유형 선택)
CAND_ALREADY = "already_linked"  # 이미 이 라인으로 만든 Unit 이 있음
CAND_BLOCKED = "blocked"         # 확인 필요(수량 등) — 자동 적용 금지
REL_TYPES = ("ORIGIN", "ADDITIONAL", "CHANGE", "CANCEL")


def _norm_unit_no(s) -> str:
    """호기번호 표기 정규화: 공백 제거 + 'N호기' 앞자리 0 제거('01호기'·'1 호기'→'1호기')."""
    s = re.sub(r"\s+", "", (s or "")).strip()
    m = _HOGI_NUM_RE.match(s)
    return f"{int(m.group(1))}호기" if m else s


def _table_ready(c) -> bool:
    return bool(c.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='project_units'").fetchone())


def _project_entity(c, pid) -> str:
    """[F-08] 프로젝트 법인(KOR/VN) — **확정값만 사용**. 비었거나 충돌하면 중단.
    ⛔ KOR 자동부여 폐지: 국내 프로젝트도 데이터에 법인을 명시해야 한다."""
    try:
        r = c.execute("SELECT po_entity, ship_entity FROM projects WHERE id=?", (pid,)).fetchone()
    except sqlite3.OperationalError:
        raise ValueError("프로젝트에 법인(KOR/VN) 칸이 없습니다. 법인 정보를 먼저 갖춘 뒤 진행하세요.")
    sigs = set()
    if r:
        for v in (r["po_entity"], r["ship_entity"]):
            s = (v or "").strip().upper()
            if not s:
                continue
            if any(k in s for k in _VN_SIG):
                sigs.add("VN")
            elif any(k in s for k in _KOR_SIG):
                sigs.add("KOR")
    if not sigs:
        raise ValueError("프로젝트 법인(KOR/VN)이 정해져 있지 않습니다. "
                         "프로젝트에 법인을 먼저 지정하세요(임의로 본사로 처리하지 않습니다).")
    if len(sigs) > 1:
        raise ValueError("프로젝트 법인(KOR/VN)이 충돌합니다. 법인을 확정한 뒤 호기를 생성하세요.")
    return sigs.pop()


# ══════════════════ 영향 분석 (V1: 미연동 — 사실대로 알림) ══════════════════

def impact_status(c, unit_id) -> dict:
    """호기에 걸린 업무 이력 현황. 표가 없으면 '영향 없음'이 아니라 **미연동**으로 알린다."""
    have = {r[0] for r in c.execute(
        "SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    wired, counts, missing = [], {}, []
    for tbl, col, label in IMPACT_SOURCES:
        if tbl not in have:
            missing.append(label)
            continue
        cols = {r[1] for r in c.execute(f"PRAGMA table_info([{tbl}])").fetchall()}
        if col not in cols:
            missing.append(label)
            continue
        wired.append(label)
        counts[label] = c.execute(
            f"SELECT COUNT(*) FROM [{tbl}] WHERE [{col}]=?", (unit_id,)).fetchone()[0]
    return {"wired": (not missing), "wired_sources": wired, "not_wired_sources": missing,
            "counts": counts, "has_impact": any(v > 0 for v in counts.values()),
            "message": None if not missing else IMPACT_NOT_WIRED_MSG}


def _require_impact_cleared(c, unit_id, action: str):
    """확정(CONFIRMED) 호기의 번호 변경·취소 가드. 미연동이면 차단(거짓 통과 금지)."""
    st = impact_status(c, unit_id)
    if not st["wired"]:
        raise ValueError(f"{IMPACT_NOT_WIRED_MSG} (요청: {action})")
    if st["has_impact"]:
        detail = ", ".join(f"{k} {v}건" for k, v in st["counts"].items() if v)
        raise ValueError(f"이 호기에 업무 이력이 있어 영향 분석·승인 없이 {action}할 수 없습니다: {detail}")


# ══════════════════ 호기번호 사용 이력 (F-06 재사용 금지) ══════════════════

def _unit_no_ever_used(c, pid, unit_no, exclude_unit_id=None) -> bool:
    """[F-06] 이 관리번호에서 **한 번이라도 쓴** 호기번호인가(취소·과거 이력 포함).
    같은 관리번호 안에 과거 '1호기'와 새 '1호기'가 생기면 현장 대화·서류가 어긋난다."""
    q1 = ("SELECT 1 FROM project_units WHERE project_id=? AND current_unit_no=?"
          + (" AND id<>?" if exclude_unit_id else ""))
    a1 = (pid, unit_no) + ((exclude_unit_id,) if exclude_unit_id else ())
    if c.execute(q1, a1).fetchone():
        return True
    q2 = ("SELECT 1 FROM project_unit_identifier_history h "
          "JOIN project_units u ON u.id=h.project_unit_id "
          "WHERE u.project_id=? AND (h.new_unit_no=? OR h.old_unit_no=?)"
          + (" AND u.id<>?" if exclude_unit_id else ""))
    a2 = (pid, unit_no, unit_no) + ((exclude_unit_id,) if exclude_unit_id else ())
    return bool(c.execute(q2, a2).fetchone())


# ══════════════════ 후보 탐색 (씨앗 = 자동확정 아님) ══════════════════

def _hogi_candidate_rows(c, pid):
    rows = c.execute(
        "SELECT oi.id AS oid, oi.unit_label AS lbl, oi.order_id AS ord, oi.qty AS qty, "
        "o.order_no AS ono "
        "FROM order_items oi JOIN orders o ON o.id=oi.order_id "
        "WHERE o.project_id=? "
        "ORDER BY o.order_date ASC, o.id ASC, oi.id ASC", (pid,)).fetchall()
    return [r for r in rows if HOGI_RE.match((r["lbl"] or ""))]


def scan_candidates(pid) -> dict:
    """수주내역 호기 라인을 **Unit 후보**로 제시(생성하지 않음).

    [F-02] 같은 호기번호가 여러 수주에 나오는 것은 **정상 업무**(추가·변경수주).
           → 차단하지 않고, 그 번호를 쓰는 **기존 Unit 후보 목록**을 함께 제시해
             '기존 Unit 에 연결(관계 유형)' 또는 '신규 개발호기'를 사용자가 고르게 한다.
    [F-01] 후보 라벨은 어디까지나 원본 표기다. 현재 호기번호로 승격하지 않는다.
    자동 적용 금지: 수량≠1(확인 필요).
    """
    with db_session() as c:
        if not _table_ready(c):
            return {"ready": False, "candidates": [], "summary": {}, "units": []}
        rows = _hogi_candidate_rows(c, pid)
        seeded = {r["seed_order_item_id"]: dict(r) for r in c.execute(
            "SELECT * FROM project_units WHERE project_id=? AND seed_order_item_id IS NOT NULL",
            (pid,)).fetchall()}
        units = [dict(r) for r in c.execute(
            "SELECT id, working_name, current_unit_no, unit_state FROM project_units "
            "WHERE project_id=? AND unit_state<>'CANCELLED' ORDER BY id", (pid,)).fetchall()]
        # 라벨(정규화) → 그 번호를 현재값 또는 개발호기명으로 쓰는 기존 Unit
        by_no = {}
        for u in units:
            for key in (u["current_unit_no"], _norm_unit_no(u["working_name"])):
                if key:
                    by_no.setdefault(key, []).append(u)
        linked_pairs = {(r[0], r[1]) for r in c.execute(
            "SELECT l.project_unit_id, l.order_id FROM project_unit_order_links l "
            "JOIN project_units u ON u.id=l.project_unit_id WHERE u.project_id=?",
            (pid,)).fetchall()}

        cands = []
        for r in rows:
            lbl = r["lbl"] or ""
            no = _norm_unit_no(lbl)
            blockers = []
            if r["qty"] is None or float(r["qty"]) != 1.0:
                blockers.append(f"수량이 1이 아닙니다(수량 {r['qty']})")
            exist = seeded.get(r["oid"])
            # 이 후보 번호를 쓰는 기존 Unit — 연결 대상 후보(F-02)
            match_units = [u for u in by_no.get(no, [])
                           if not exist or u["id"] != exist["id"]]
            if exist:
                sug = CAND_ALREADY
            elif blockers:
                sug = CAND_BLOCKED
            elif match_units:
                sug = CAND_LINK      # 같은 번호의 기존 Unit 있음 → 연결/신규를 사용자가 선택
            else:
                sug = CAND_NEW
            cands.append({
                "order_item_id": r["oid"], "order_id": r["ord"], "order_no": r["ono"],
                "label": lbl, "unit_no_hint": no, "qty": r["qty"],
                "existing_unit_id": (exist or {}).get("id"),
                "existing_state": (exist or {}).get("unit_state"),
                "match_units": [{
                    "id": u["id"], "working_name": u["working_name"],
                    "current_unit_no": u["current_unit_no"], "state": u["unit_state"],
                    "already_linked_order": ((u["id"], r["ord"]) in linked_pairs),
                } for u in match_units],
                "suggestion": sug, "blockers": blockers,
            })
    s = {"total": len(cands),
         "new": sum(1 for x in cands if x["suggestion"] == CAND_NEW),
         "link": sum(1 for x in cands if x["suggestion"] == CAND_LINK),
         "already_linked": sum(1 for x in cands if x["suggestion"] == CAND_ALREADY),
         "blocked": sum(1 for x in cands if x["suggestion"] == CAND_BLOCKED)}
    return {"ready": True, "candidates": cands, "summary": s, "units": units}


def apply_candidate_decisions(pid, decisions, reason, actor_id=0) -> dict:
    """사용자가 **후보마다 내린 판정**을 반영한다(F-01/F-02/F-03).

    decisions = [{order_item_id, action, unit_id?, relation_type?}, ...]
      · action='new'   → 신규 **개발호기**(PROVISIONAL) 생성.
                         ⭐ current_unit_no 는 **NULL**(후보 라벨은 working_name·seed 에만 보존).
      · action='link'  → 기존 Unit 에 이 수주를 관계로 연결(ORIGIN/ADDITIONAL/CHANGE).
      · action='hold'/'exclude' → 아무것도 하지 않음(보류·제외).
    반영 사유(reason)는 **필수**.
    """
    if not (reason or "").strip():
        raise ValueError("반영 사유를 입력하세요.")
    decisions = [d for d in (decisions or []) if (d or {}).get("action") in ("new", "link")]
    if not decisions:
        raise ValueError("반영할 후보를 선택하세요.")
    scan = scan_candidates(pid)
    if not scan["ready"]:
        raise ValueError("호기 기능이 아직 준비되지 않았습니다.")
    by_id = {c0["order_item_id"]: c0 for c0 in scan["candidates"]}
    created, linked, rejected = [], [], []
    with db_session() as c:
        entity = _project_entity(c, pid)          # [F-08] 빈값·충돌이면 여기서 중단
        for d in decisions:
            oid = int(d.get("order_item_id") or 0)
            cd = by_id.get(oid)
            if not cd:
                rejected.append((oid, "후보 목록에 없음"))
                continue
            if cd["suggestion"] == CAND_ALREADY:
                rejected.append((oid, "이미 반영된 후보"))
                continue
            if cd["blockers"]:
                rejected.append((oid, " / ".join(cd["blockers"])))
                continue
            if d["action"] == "new":
                cur = c.execute(
                    "INSERT INTO project_units(project_id, working_name, current_unit_no, "
                    "unit_state, entity, seed_order_item_id, seed_order_no, seed_unit_label, "
                    "note, created_by, created_at, updated_by, updated_at) "
                    "VALUES(?,?, NULL, 'PROVISIONAL', ?,?,?,?,?,?,?,?,?)",
                    (pid, cd["label"], entity, oid, cd["order_no"], cd["label"],
                     reason.strip(), actor_id, _logi_now(), actor_id, _logi_now()))
                uid = cur.lastrowid
                if cd["order_id"]:
                    _insert_order_link(c, uid, cd["order_id"], cd["order_no"], "ORIGIN",
                                       reason.strip(), actor_id)
                created.append(uid)
            else:  # link
                uid = int(d.get("unit_id") or 0)
                rel = (d.get("relation_type") or "ADDITIONAL").upper()
                try:
                    _link_order_tx(c, uid, cd["order_id"], rel, reason.strip(), actor_id,
                                   expect_project=pid)
                    linked.append((uid, cd["order_no"], rel))
                except ValueError as e:
                    rejected.append((oid, str(e)))
    return {"created": len(created), "created_ids": created,
            "linked": len(linked), "linked_detail": linked, "rejected": rejected}


# ══════════════════ 수주 연결(관계) ══════════════════

def _insert_order_link(c, unit_id, order_id, order_no, rel, reason, actor_id, change_id=None):
    return c.execute(
        "INSERT INTO project_unit_order_links(project_unit_id, order_id, order_no, "
        "relation_type, active, reason, change_id, linked_by, linked_at) "
        "VALUES(?,?,?,?,1,?,?,?,?)",
        (unit_id, order_id, order_no, rel, (reason or None), change_id, actor_id,
         _logi_now())).lastrowid


def _link_order_tx(c, unit_id, order_id, relation_type, reason, actor_id,
                   change_id=None, expect_project=None):
    """수주 연결 공통 규칙(§5 무결성).
    · 취소된 Unit 에는 새 수주를 연결할 수 없다.
    · 같은 Unit·수주·관계유형 중복 금지.
    · ORIGIN 은 Unit 당 1개.
    · 다른 프로젝트의 수주는 연결 불가.
    """
    if relation_type not in REL_TYPES:
        raise ValueError("연결 유형이 올바르지 않습니다.")
    u = c.execute("SELECT id, project_id, unit_state FROM project_units WHERE id=?",
                  (unit_id,)).fetchone()
    if not u:
        raise ValueError("호기가 없습니다.")
    if expect_project is not None and u["project_id"] != expect_project:
        raise ValueError("다른 프로젝트의 호기입니다.")
    if u["unit_state"] == "CANCELLED":
        raise ValueError("취소된 호기에는 수주를 연결할 수 없습니다.")
    o = c.execute("SELECT id, order_no, project_id FROM orders WHERE id=?", (order_id,)).fetchone()
    if not o:
        raise ValueError("수주가 없습니다.")
    if o["project_id"] and o["project_id"] != u["project_id"]:
        raise ValueError("다른 프로젝트의 수주는 연결할 수 없습니다.")
    if c.execute("SELECT id FROM project_unit_order_links WHERE project_unit_id=? AND order_id=? "
                 "AND relation_type=? AND active=1",
                 (unit_id, order_id, relation_type)).fetchone():
        raise ValueError(f"이미 같은 유형으로 연결돼 있습니다({o['order_no']}).")
    if relation_type == "ORIGIN" and c.execute(
            "SELECT id FROM project_unit_order_links WHERE project_unit_id=? "
            "AND relation_type='ORIGIN' AND active=1", (unit_id,)).fetchone():
        raise ValueError("최초 수주(ORIGIN)는 이미 연결돼 있습니다. 추가·변경으로 연결하세요.")
    return _insert_order_link(c, unit_id, order_id, o["order_no"], relation_type,
                              reason, actor_id, change_id)


def link_order(unit_id, order_id, relation_type="ADDITIONAL", reason=None,
               actor_id=0, change_id=None) -> int:
    with db_session() as c:
        return _link_order_tx(c, unit_id, order_id, relation_type, reason, actor_id, change_id)


# ══════════════════ 조회 ══════════════════

def _unit_sort_key(u):
    m = re.match(r"^(\d+)", u.get("current_unit_no") or u.get("working_name") or "")
    return (0 if u.get("unit_state") != "CANCELLED" else 1,
            int(m.group(1)) if m else 999999, u.get("id") or 0)


def get_units(pid, include_cancelled=True) -> list:
    with db_session() as c:
        if not _table_ready(c):
            return []
        q = "SELECT * FROM project_units WHERE project_id=?"
        if not include_cancelled:
            q += " AND unit_state<>'CANCELLED'"
        units = [dict(r) for r in c.execute(q, (pid,)).fetchall()]
        for u in units:
            prev = c.execute(
                "SELECT old_unit_no FROM project_unit_identifier_history "
                "WHERE project_unit_id=? AND old_unit_no IS NOT NULL "
                "ORDER BY id DESC LIMIT 1", (u["id"],)).fetchone()
            u["previous_unit_no"] = prev["old_unit_no"] if prev else None
            u["orders"] = [dict(r) for r in c.execute(
                "SELECT order_id, order_no, relation_type, active FROM project_unit_order_links "
                "WHERE project_unit_id=? ORDER BY id", (u["id"],)).fetchall()]
            u["active_orders"] = [o for o in u["orders"] if o["active"]]
            u["impact"] = impact_status(c, u["id"])
    units.sort(key=_unit_sort_key)
    return units


def get_unit(unit_id):
    with db_session() as c:
        r = c.execute("SELECT * FROM project_units WHERE id=?", (unit_id,)).fetchone()
        if not r:
            return None
        u = dict(r)
        u["identifier_history"] = [dict(x) for x in c.execute(
            "SELECT h.*, us.name AS changed_by_name FROM project_unit_identifier_history h "
            "LEFT JOIN users us ON us.id=h.changed_by "
            "WHERE h.project_unit_id=? ORDER BY h.id DESC", (unit_id,)).fetchall()]
        u["orders"] = [dict(x) for x in c.execute(
            "SELECT * FROM project_unit_order_links WHERE project_unit_id=? ORDER BY id",
            (unit_id,)).fetchall()]
        u["relations"] = [dict(x) for x in c.execute(
            "SELECT * FROM project_unit_relations "
            "WHERE source_unit_id=? OR result_unit_id=? ORDER BY id",
            (unit_id, unit_id)).fetchall()]
        u["impact"] = impact_status(c, unit_id)
    return u


def unit_no_at(unit_id, when: str):
    """[F-07] **업무 적용시점(effective_from/to)** 기준으로 그 시점의 호기번호를 재현한다.
    changed_at(기록시각)은 누가 언제 입력했는지를 나타내는 audit 값이며 조회 기준이 아니다."""
    with db_session() as c:
        rows = [dict(r) for r in c.execute(
            "SELECT new_unit_no, effective_from, effective_to "
            "FROM project_unit_identifier_history WHERE project_unit_id=? "
            "ORDER BY COALESCE(effective_from,''), id", (unit_id,)).fetchall()]
    val = None
    for r in rows:
        ef, et = (r["effective_from"] or ""), r["effective_to"]
        if ef and ef > when:
            continue                      # 아직 적용 전(미래 예약 포함)
        if et and et <= when:
            continue                      # 이미 종료된 구간
        val = r["new_unit_no"]
    return val


def project_unit_summary(pid) -> dict:
    with db_session() as c:
        ready = _table_ready(c)
        if not ready:
            return {"ready": False, "units": 0, "provisional": 0, "confirmed": 0,
                    "cancelled": 0, "candidates": 0, "impact_wired": False, "no_unit_no": 0}
        rows = c.execute("SELECT unit_state, COUNT(*) FROM project_units WHERE project_id=? "
                         "GROUP BY unit_state", (pid,)).fetchall()
        st = {r[0]: r[1] for r in rows}
        no_num = c.execute("SELECT COUNT(*) FROM project_units WHERE project_id=? "
                           "AND current_unit_no IS NULL AND unit_state<>'CANCELLED'",
                           (pid,)).fetchone()[0]
        cands = len(_hogi_candidate_rows(c, pid))
        wired = impact_status(c, 0)["wired"]
    return {"ready": True, "units": sum(st.values()),
            "provisional": st.get("PROVISIONAL", 0), "confirmed": st.get("CONFIRMED", 0),
            "cancelled": st.get("CANCELLED", 0), "candidates": cands,
            "impact_wired": wired, "no_unit_no": no_num}


# ══════════════════ 생성·번호지정/변경·확정·취소 ══════════════════

def create_unit(pid, working_name=None, unit_no=None, equipment_type=None,
                actor_id=0, note=None) -> int:
    """개발호기 생성 — 호기번호 없이 개발호기명만으로 생성 가능."""
    working_name = (working_name or "").strip() or None
    unit_no = _norm_unit_no(unit_no) or None
    if not working_name and not unit_no:
        raise ValueError("개발호기명 또는 호기번호 중 하나는 입력하세요.")
    with db_session() as c:
        if not c.execute("SELECT id FROM projects WHERE id=?", (pid,)).fetchone():
            raise ValueError("프로젝트가 없습니다.")
        entity = _project_entity(c, pid)
        if unit_no and _unit_no_ever_used(c, pid, unit_no):
            raise ValueError(f"이 관리번호에서 이미 사용된 호기번호입니다(취소분 포함): {unit_no}")
        cur = c.execute(
            "INSERT INTO project_units(project_id, working_name, current_unit_no, unit_state, "
            "entity, equipment_type, note, created_by, created_at, updated_by, updated_at) "
            "VALUES(?,?,?, 'PROVISIONAL', ?,?,?,?,?,?,?)",
            (pid, working_name, unit_no, entity, (equipment_type or None), (note or None),
             actor_id, _logi_now(), actor_id, _logi_now()))
        uid = cur.lastrowid
        if unit_no:
            c.execute(
                "INSERT INTO project_unit_identifier_history(project_unit_id, old_unit_no, "
                "new_unit_no, change_reason, changed_by, changed_at, effective_from) "
                "VALUES(?,NULL,?,?,?,?,?)",
                (uid, unit_no, "최초 지정", actor_id, _logi_now(), _logi_now()))
        return uid


def change_unit_no(unit_id, new_unit_no, reason, actor_id=0, change_id=None,
                   effective_from=None) -> bool:
    """호기번호 지정·변경 — **Unit id 는 유지**되고 이력이 남는다(적용시점 포함).
    확정(CONFIRMED) 호기는 영향 확인이 필요(V1 미연동이라 차단)."""
    new_no = _norm_unit_no(new_unit_no)
    if not new_no:
        raise ValueError("새 호기번호를 입력하세요.")
    if not (reason or "").strip():
        raise ValueError("호기번호를 정하거나 바꾸려면 사유를 입력하세요.")
    with db_session() as c:
        u = c.execute("SELECT * FROM project_units WHERE id=?", (unit_id,)).fetchone()
        if not u:
            raise ValueError("호기가 없습니다.")
        if u["unit_state"] == "CANCELLED":
            raise ValueError("취소된 호기는 변경할 수 없습니다.")
        old_no = u["current_unit_no"]
        if old_no == new_no:
            return False
        if u["unit_state"] == "CONFIRMED":
            _require_impact_cleared(c, unit_id, "호기번호를 변경")
        if _unit_no_ever_used(c, u["project_id"], new_no, exclude_unit_id=unit_id):
            raise ValueError(f"이 관리번호에서 이미 사용된 호기번호입니다(취소분 포함): {new_no}")
        now = _logi_now()
        eff = (effective_from or "").strip() or now
        # 적용기간 겹침 방지 — 직전 유효구간을 새 적용시점에서 종료
        c.execute("UPDATE project_unit_identifier_history SET effective_to=? "
                  "WHERE project_unit_id=? AND effective_to IS NULL", (eff, unit_id))
        c.execute("UPDATE project_units SET current_unit_no=?, updated_by=?, updated_at=? "
                  "WHERE id=?", (new_no, actor_id, now, unit_id))
        c.execute(
            "INSERT INTO project_unit_identifier_history(project_unit_id, old_unit_no, new_unit_no, "
            "change_reason, changed_by, changed_at, change_id, effective_from) "
            "VALUES(?,?,?,?,?,?,?,?)",
            (unit_id, old_no, new_no, reason.strip(), actor_id, now, change_id, eff))
    return True


def confirm_unit(unit_id, actor_id=0) -> bool:
    """개발·미확정 → 확정. 현재 호기번호 필수."""
    with db_session() as c:
        u = c.execute("SELECT * FROM project_units WHERE id=?", (unit_id,)).fetchone()
        if not u:
            raise ValueError("호기가 없습니다.")
        if u["unit_state"] == "CANCELLED":
            raise ValueError("취소된 호기는 확정할 수 없습니다.")
        if not (u["current_unit_no"] or "").strip():
            raise ValueError("확정하려면 현재 호기번호가 있어야 합니다.")
        c.execute("UPDATE project_units SET unit_state='CONFIRMED', confirmed_by=?, "
                  "confirmed_at=?, updated_by=?, updated_at=? WHERE id=?",
                  (actor_id, _logi_now(), actor_id, _logi_now(), unit_id))
    return True


def cancel_unit(unit_id, reason, actor_id=0) -> bool:
    """호기 취소 — 물리삭제 금지. CANCELLED 전환 + 사유. 수주 연결은 이력으로 보존."""
    if not (reason or "").strip():
        raise ValueError("취소 사유를 입력하세요.")
    with db_session() as c:
        u = c.execute("SELECT * FROM project_units WHERE id=?", (unit_id,)).fetchone()
        if not u:
            raise ValueError("호기가 없습니다.")
        if u["unit_state"] == "CANCELLED":
            return False
        if u["unit_state"] == "CONFIRMED":
            _require_impact_cleared(c, unit_id, "호기를 취소")
        now = _logi_now()
        c.execute("UPDATE project_units SET unit_state='CANCELLED', cancelled_by=?, "
                  "cancelled_at=?, cancellation_reason=?, updated_by=?, updated_at=? WHERE id=?",
                  (actor_id, now, reason.strip(), actor_id, now, unit_id))
        c.execute("UPDATE project_unit_order_links SET active=0, unlinked_by=?, unlinked_at=? "
                  "WHERE project_unit_id=? AND active=1", (actor_id, now, unit_id))
    return True


def get_unit_relations(unit_id) -> list:
    """분할·통합 관계 이력 조회(읽기 전용). ⛔ V1: 생성·실행·승인 기능 없음(WP-04 이후)."""
    with db_session() as c:
        return [dict(r) for r in c.execute(
            "SELECT * FROM project_unit_relations WHERE source_unit_id=? OR result_unit_id=? "
            "ORDER BY id", (unit_id, unit_id)).fetchall()]
