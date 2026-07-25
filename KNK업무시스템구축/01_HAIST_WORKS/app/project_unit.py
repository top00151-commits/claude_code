# -*- coding: utf-8 -*-
# ============================================================
# v5H226z1053 (2026-07-25, ERP V1 전환 WP-03) — 프로젝트 호기 (Project Unit)
# ⭐ 대표 업무교정(2026-07-25) 반영본 — 일련번호 폐기 · 호기번호는 변경 가능
# ------------------------------------------------------------
# KNK 현실:
#   · 일련번호(S/N) 안 씀. 식별 = 관리번호(프로젝트) + 수주번호(발주차수) + 호기번호.
#   · **개발호기로 시작**하고 개발·수주 변경에 따라 호기번호·구성이 바뀐다
#     (대수 변경·번호 변경·추가·취소·분할·통합·수주 후행 발행).
#   → 호기번호는 영구 식별자가 아니다. **영구 식별자는 project_units.id 하나**.
#     BOM·설계변경·자재·생산·검사·출하는 전부 이 id 에 연결한다.
#
# V1 범위(대표 확정 2026-07-25):
#   · 영구 id · 개발호기명 · 호기번호 변경이력 · 수주 다중연결 · 분할/통합 **수용 구조까지**
#   · 분할·통합 **실행·승인은 미구현**(WP-04 영향분석 연결 후) — 앱에 쓰기 경로 없음
#   · ⛔ **영향분석 미연동**: BOM·발주·입고·생산투입·출하 이력이 하나라도 있으면
#        영향 분석·승인 없이는 호기번호 변경·취소를 **차단**한다(거짓 '영향 없음' 표시 금지).
#
# 상태: PROVISIONAL(개발·미확정) / CONFIRMED(확정) / CANCELLED(취소·물리삭제 금지)
# 씨앗: 수주내역 호기 라인 = 확정 사실이 아니라 **Unit 후보** → 사용자 확인·승인 후 반영.
# ============================================================
import re
import sqlite3

from .database import db_session, _logi_now

# 정식 호기 라벨(기존 시스템 규약·z779). 부속/부품(비표준 라벨)은 후보에서 제외.
HOGI_RE = re.compile(r"^\d+호기$")
_HOGI_NUM_RE = re.compile(r"^0*(\d+)호기$")
_VN_SIG = ("VN", "VNM", "VINA", "VIETNAM", "베트남")
_KOR_SIG = ("KR", "KOR", "KOREA", "한국", "본사", "HQ")

# ── 영향 분석 대상(WP-04 이후 연동) ─────────────────────────────
#   호기에 붙게 될 업무 이력. **아직 연동되지 않았다**는 사실을 숨기지 않고 그대로 알린다.
#   각 항목: (표 이름, 호기 참조 컬럼, 사람이 읽는 이름)
#   ⚠ WP-04~08 에서 표가 생기면 여기에 등록 + 실제 조회로 전환한다(완료 조건은 문서 참조).
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


def _norm_unit_no(s) -> str:
    """호기번호 표기 정규화: 공백 제거 + 'N호기' 앞자리 0 제거('01호기'·'1 호기'→'1호기')."""
    s = re.sub(r"\s+", "", (s or "")).strip()
    m = _HOGI_NUM_RE.match(s)
    return f"{int(m.group(1))}호기" if m else s


def _table_ready(c) -> bool:
    """마이그레이션 전이면 False — 런타임 오류 대신 '준비 중' 안내."""
    return bool(c.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='project_units'").fetchone())


def _project_entity(c, pid) -> str:
    """프로젝트 법인(KOR/VN). 둘 다 명시됐는데 다르면 중단. 빈값=KOR(⚠국내 시범 한정)."""
    try:
        r = c.execute("SELECT po_entity, ship_entity FROM projects WHERE id=?", (pid,)).fetchone()
    except sqlite3.OperationalError:
        return "KOR"
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
    if len(sigs) > 1:
        raise ValueError("프로젝트 법인(KOR/VN)이 충돌합니다. 법인을 확정한 뒤 호기를 생성하세요.")
    return sigs.pop() if sigs else "KOR"


# ══════════════════ 영향 분석 (V1: 미연동 — 사실대로 알림) ══════════════════

def impact_status(c, unit_id) -> dict:
    """이 호기에 걸린 업무 이력(BOM·발주·입고·생산투입·출하) 현황.

    ⛔ V1 계약: 표가 아직 없으면 **'영향 없음'이라고 말하지 않는다.** 'wired=False'(미연동)로 알린다.
    표가 생기면(WP-04+) 실제 건수를 세고 wired=True 가 된다.
    """
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
    return {
        "wired": (not missing),                 # 전부 연동됐을 때만 True
        "wired_sources": wired,
        "not_wired_sources": missing,
        "counts": counts,
        "has_impact": any(v > 0 for v in counts.values()),
        "message": None if not missing else IMPACT_NOT_WIRED_MSG,
    }


def _require_impact_cleared(c, unit_id, action: str):
    """영향 확인이 필요한 변경(확정된 호기의 번호 변경·취소)의 공통 가드.

    적용 대상 = **CONFIRMED 호기**(BOM·발주·생산이 붙을 수 있는 단계).
      · 개발·미확정(PROVISIONAL)은 업무 이력이 아직 붙지 않으므로 자유롭게 정리 가능
        (문서 §4: "BOM Release·발주·생산투입 이후 변경은 Change 승인 필요").
      · 연동 전(V1): 확정 호기는 **차단**. 거짓 통과 금지 —
        대표 확정: "영향 확인이 필요한 호기 변경은 승인 처리할 수 없습니다."
      · 연동 후(WP-04+): 이력이 하나라도 있으면 영향분석·승인 없이는 차단.
    """
    st = impact_status(c, unit_id)
    if not st["wired"]:
        raise ValueError(f"{IMPACT_NOT_WIRED_MSG} (요청: {action})")
    if st["has_impact"]:
        detail = ", ".join(f"{k} {v}건" for k, v in st["counts"].items() if v)
        raise ValueError(f"이 호기에 업무 이력이 있어 영향 분석·승인 없이 {action}할 수 없습니다: {detail}")


def _unit_ref_counts(c, unit_id) -> dict:
    """이 호기를 참조하는 **모든 표**를 FK 메타데이터로 동적 스캔(전참조 스캔).
    WP-04+ 새 표가 FK 를 걸면 자동 포함(목록 등록 누락 위험 없음)."""
    out = {}
    for (tbl,) in c.execute(
            "SELECT name FROM sqlite_master WHERE type='table'").fetchall():
        if tbl == "project_units":
            continue
        try:
            fks = c.execute(f"PRAGMA foreign_key_list([{tbl}])").fetchall()
        except sqlite3.Error:
            continue
        for fk in fks:
            if fk[2] == "project_units":
                col = fk[3]
                n = c.execute(f"SELECT COUNT(*) FROM [{tbl}] WHERE [{col}]=?",
                              (unit_id,)).fetchone()[0]
                if n:
                    out[f"{tbl}.{col}"] = out.get(f"{tbl}.{col}", 0) + n
    return out


# ══════════════════ 후보 탐색 (씨앗 = 자동확정 아님) ══════════════════

def _hogi_candidate_rows(c, pid):
    """수주내역에서 호기 후보 라인(정식 호기 라벨)만 추림."""
    rows = c.execute(
        "SELECT oi.id AS oid, oi.unit_label AS lbl, oi.order_id AS ord, oi.qty AS qty, "
        "o.order_no AS ono "
        "FROM order_items oi JOIN orders o ON o.id=oi.order_id "
        "WHERE o.project_id=? "
        "ORDER BY o.order_date ASC, o.id ASC, oi.id ASC", (pid,)).fetchall()
    return [r for r in rows if HOGI_RE.match((r["lbl"] or ""))]


def scan_candidates(pid) -> dict:
    """수주내역 호기 라인을 **Unit 후보**로 제시(생성하지 않음).

    각 후보의 판정 제안(suggestion)과 **자동적용 금지 사유(blockers)** 를 함께 낸다.
      · already_linked  : 이미 이 라인으로 만든 호기가 있음
      · new             : 새 PROVISIONAL 호기 후보
      · blocked         : 사용자 확인 없이는 적용 불가(아래 사유)
    자동적용 금지(대표 확정 §6): 수량≠1 · 현재 호기번호 충돌 · 같은 번호가 여러 수주에 존재
    """
    with db_session() as c:
        if not _table_ready(c):
            return {"ready": False, "candidates": [], "summary": {}}
        rows = _hogi_candidate_rows(c, pid)
        seeded = {r["seed_order_item_id"]: dict(r) for r in c.execute(
            "SELECT * FROM project_units WHERE project_id=? AND seed_order_item_id IS NOT NULL",
            (pid,)).fetchall()}
        cur_nos = {r[0]: r[1] for r in c.execute(
            "SELECT current_unit_no, id FROM project_units "
            "WHERE project_id=? AND current_unit_no IS NOT NULL AND unit_state<>'CANCELLED'",
            (pid,)).fetchall()}
        label_seen = {}
        for r in rows:
            label_seen.setdefault(_norm_unit_no(r["lbl"]), []).append(r["ono"] or "")

        cands = []
        for r in rows:
            lbl = r["lbl"] or ""
            no = _norm_unit_no(lbl)
            blockers = []
            if r["qty"] is None or float(r["qty"]) != 1.0:
                blockers.append(f"수량이 1이 아님(수량 {r['qty']})")
            if len(label_seen.get(no, [])) > 1:
                blockers.append(f"같은 호기번호가 여러 수주에 있음({', '.join(label_seen[no][:3])})")
            exist = seeded.get(r["oid"])
            if not exist and no in cur_nos:
                blockers.append(f"현재 호기번호 충돌({no})")
            cands.append({
                "order_item_id": r["oid"], "order_id": r["ord"], "order_no": r["ono"],
                "label": lbl, "unit_no": no, "qty": r["qty"],
                "existing_unit_id": (exist or {}).get("id"),
                "existing_state": (exist or {}).get("unit_state"),
                "suggestion": ("already_linked" if exist else ("blocked" if blockers else "new")),
                "blockers": blockers,
            })
    s = {
        "total": len(cands),
        "already_linked": sum(1 for x in cands if x["suggestion"] == "already_linked"),
        "new": sum(1 for x in cands if x["suggestion"] == "new"),
        "blocked": sum(1 for x in cands if x["suggestion"] == "blocked"),
    }
    return {"ready": True, "candidates": cands, "summary": s}


def apply_candidates(pid, order_item_ids, actor_id=0, reason=None) -> dict:
    """사용자가 **확인·선택한 후보만** PROVISIONAL 호기로 생성 + 수주 링크(ORIGIN).

    · 자동확정 아님: 화면에서 고른 라인 목록만 처리.
    · 자동적용 금지 조건에 걸린 후보는 **거부**(사유 반환) — 조용히 건너뛰지 않는다.
    · 생성 상태는 PROVISIONAL(확정은 사람이 별도 승인).
    """
    ids = {int(x) for x in (order_item_ids or [])}
    if not ids:
        raise ValueError("선택한 후보가 없습니다.")
    scan = scan_candidates(pid)
    if not scan["ready"]:
        raise ValueError("호기 기능이 아직 준비되지 않았습니다.")
    by_id = {c0["order_item_id"]: c0 for c0 in scan["candidates"]}
    created, skipped, rejected = 0, 0, []
    with db_session() as c:
        entity = _project_entity(c, pid)
        for oid in sorted(ids):
            cd = by_id.get(oid)
            if not cd:
                rejected.append((oid, "후보 목록에 없음"))
                continue
            if cd["suggestion"] == "already_linked":
                skipped += 1
                continue
            if cd["blockers"]:
                rejected.append((oid, " / ".join(cd["blockers"])))
                continue
            cur = c.execute(
                "INSERT INTO project_units(project_id, working_name, current_unit_no, unit_state, "
                "entity, seed_order_item_id, seed_order_no, seed_unit_label, "
                "created_by, created_at, updated_by, updated_at) "
                "VALUES(?,?,?, 'PROVISIONAL', ?,?,?,?,?,?,?,?)",
                (pid, cd["label"], cd["unit_no"], entity, oid, cd["order_no"], cd["label"],
                 actor_id, _logi_now(), actor_id, _logi_now()))
            uid = cur.lastrowid
            c.execute(
                "INSERT INTO project_unit_identifier_history(project_unit_id, old_unit_no, "
                "new_unit_no, change_reason, changed_by, changed_at, effective_from) "
                "VALUES(?,?,?,?,?,?,?)",
                (uid, None, cd["unit_no"], (reason or "수주내역 호기 후보 반영"),
                 actor_id, _logi_now(), _logi_now()))
            if cd["order_id"]:
                c.execute(
                    "INSERT INTO project_unit_order_links(project_unit_id, order_id, order_no, "
                    "relation_type, active, reason, linked_by, linked_at) "
                    "VALUES(?,?,?, 'ORIGIN', 1, ?, ?, ?)",
                    (uid, cd["order_id"], cd["order_no"], (reason or "후보 반영"),
                     actor_id, _logi_now()))
            created += 1
    return {"created": created, "already_linked": skipped, "rejected": rejected}


# ══════════════════ 호기 조회 ══════════════════

def _unit_sort_key(u):
    m = re.match(r"^(\d+)", u.get("current_unit_no") or "")
    return (0 if u.get("unit_state") != "CANCELLED" else 1,
            int(m.group(1)) if m else 999999, u.get("id") or 0)


def get_units(pid, include_cancelled=True) -> list:
    """프로젝트 호기 목록 — 현재 호기번호·이전 호기번호·수주 연결·상태."""
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
            "WHERE source_unit_id=? OR result_unit_id=? ORDER BY id", (unit_id, unit_id)).fetchall()]
        u["impact"] = impact_status(c, unit_id)
    return u


def unit_no_at(unit_id, when: str):
    """특정 시점의 호기번호 재현(과거 조회 · 문서 §3)."""
    with db_session() as c:
        rows = [dict(r) for r in c.execute(
            "SELECT new_unit_no, old_unit_no, changed_at FROM project_unit_identifier_history "
            "WHERE project_unit_id=? ORDER BY id", (unit_id,)).fetchall()]
        cur = c.execute("SELECT current_unit_no FROM project_units WHERE id=?",
                        (unit_id,)).fetchone()
    val = None
    for r in rows:
        if (r["changed_at"] or "") <= when:
            val = r["new_unit_no"]
        else:
            return val if val is not None else r["old_unit_no"]
    return val if val is not None else (cur["current_unit_no"] if cur else None)


def project_unit_summary(pid) -> dict:
    with db_session() as c:
        ready = _table_ready(c)
        if not ready:
            return {"ready": False, "units": 0, "provisional": 0, "confirmed": 0,
                    "cancelled": 0, "candidates": 0, "impact_wired": False}
        rows = c.execute(
            "SELECT unit_state, COUNT(*) FROM project_units WHERE project_id=? "
            "GROUP BY unit_state", (pid,)).fetchall()
        st = {r[0]: r[1] for r in rows}
        cands = len(_hogi_candidate_rows(c, pid))
        wired = impact_status(c, 0)["wired"]
    return {"ready": True, "units": sum(st.values()),
            "provisional": st.get("PROVISIONAL", 0), "confirmed": st.get("CONFIRMED", 0),
            "cancelled": st.get("CANCELLED", 0), "candidates": cands, "impact_wired": wired}


# ══════════════════ 호기 생성·변경·확정·취소 ══════════════════

def create_unit(pid, working_name=None, unit_no=None, equipment_type=None,
                actor_id=0, note=None) -> int:
    """호기 직접 생성 — 개발 단계에서는 **호기번호 없이도** 생성(PROVISIONAL)."""
    working_name = (working_name or "").strip() or None
    unit_no = _norm_unit_no(unit_no) or None
    if not working_name and not unit_no:
        raise ValueError("개발호기명 또는 호기번호 중 하나는 입력하세요.")
    with db_session() as c:
        if not c.execute("SELECT id FROM projects WHERE id=?", (pid,)).fetchone():
            raise ValueError("프로젝트가 없습니다.")
        if unit_no and c.execute(
                "SELECT id FROM project_units WHERE project_id=? AND current_unit_no=? "
                "AND unit_state<>'CANCELLED'", (pid, unit_no)).fetchone():
            raise ValueError(f"현재 쓰이는 호기번호입니다: {unit_no}")
        entity = _project_entity(c, pid)
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


def change_unit_no(unit_id, new_unit_no, reason, actor_id=0, change_id=None) -> bool:
    """호기번호 변경 — **Unit id 는 유지**하고 이력을 남긴다.
    ⛔ 업무 이력(BOM·발주·입고·생산투입·출하)이 있으면 영향분석·승인 없이 불가(V1=미연동이라 차단)."""
    new_no = _norm_unit_no(new_unit_no)
    if not new_no:
        raise ValueError("새 호기번호를 입력하세요.")
    if not (reason or "").strip():
        raise ValueError("호기번호를 변경하려면 사유를 입력하세요.")
    with db_session() as c:
        u = c.execute("SELECT * FROM project_units WHERE id=?", (unit_id,)).fetchone()
        if not u:
            raise ValueError("호기가 없습니다.")
        if u["unit_state"] == "CANCELLED":
            raise ValueError("취소된 호기는 변경할 수 없습니다.")
        old_no = u["current_unit_no"]
        if old_no == new_no:
            return False
        # 확정(CONFIRMED) 호기 = BOM·발주·생산이 붙는 단계 → 영향 확인 필요(V1 은 미연동이라 차단).
        # 개발·미확정 호기는 아직 업무가 붙지 않으므로 번호를 자유롭게 정리할 수 있다.
        if u["unit_state"] == "CONFIRMED":
            _require_impact_cleared(c, unit_id, "호기번호를 변경")
        if c.execute("SELECT id FROM project_units WHERE project_id=? AND current_unit_no=? "
                     "AND unit_state<>'CANCELLED' AND id<>?",
                     (u["project_id"], new_no, unit_id)).fetchone():
            raise ValueError(f"현재 쓰이는 호기번호입니다: {new_no}")
        now = _logi_now()
        c.execute("UPDATE project_units SET current_unit_no=?, updated_by=?, updated_at=? "
                  "WHERE id=?", (new_no, actor_id, now, unit_id))
        c.execute("UPDATE project_unit_identifier_history SET effective_to=? "
                  "WHERE project_unit_id=? AND effective_to IS NULL", (now, unit_id))
        c.execute(
            "INSERT INTO project_unit_identifier_history(project_unit_id, old_unit_no, new_unit_no, "
            "change_reason, changed_by, changed_at, change_id, effective_from) "
            "VALUES(?,?,?,?,?,?,?,?)",
            (unit_id, old_no, new_no, reason.strip(), actor_id, now, change_id, now))
    return True


def confirm_unit(unit_id, actor_id=0) -> bool:
    """PROVISIONAL → CONFIRMED. **현재 호기번호 필수**(문서 §4)."""
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
    """호기 취소 — **물리삭제 금지**. CANCELLED 전환 + 사유 기록.
    ⛔ 업무 이력이 있으면 영향분석·승인 없이 불가(V1=미연동이라 차단)."""
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
        # 수주 연결은 지우지 않고 비활성 이력으로 남긴다(덮어쓰기·삭제 금지)
        c.execute("UPDATE project_unit_order_links SET active=0, unlinked_by=?, unlinked_at=? "
                  "WHERE project_unit_id=? AND active=1", (actor_id, now, unit_id))
    return True


# ══════════════════ 수주 연결(관계) ══════════════════

def link_order(unit_id, order_id, relation_type="ADDITIONAL", reason=None,
               actor_id=0, change_id=None) -> int:
    """호기에 수주번호 연결 — 기존 링크를 **덮어쓰거나 지우지 않고** 새 행으로 추가."""
    if relation_type not in ("ORIGIN", "ADDITIONAL", "CHANGE", "CANCEL"):
        raise ValueError("연결 유형이 올바르지 않습니다.")
    with db_session() as c:
        u = c.execute("SELECT id, project_id FROM project_units WHERE id=?", (unit_id,)).fetchone()
        if not u:
            raise ValueError("호기가 없습니다.")
        o = c.execute("SELECT id, order_no, project_id FROM orders WHERE id=?", (order_id,)).fetchone()
        if not o:
            raise ValueError("수주가 없습니다.")
        if o["project_id"] and o["project_id"] != u["project_id"]:
            raise ValueError("다른 프로젝트의 수주는 연결할 수 없습니다.")
        if relation_type == "ORIGIN" and c.execute(
                "SELECT id FROM project_unit_order_links WHERE project_unit_id=? "
                "AND relation_type='ORIGIN'", (unit_id,)).fetchone():
            raise ValueError("최초 수주(ORIGIN)는 이미 연결돼 있습니다. 추가·변경으로 연결하세요.")
        cur = c.execute(
            "INSERT INTO project_unit_order_links(project_unit_id, order_id, order_no, "
            "relation_type, active, reason, change_id, linked_by, linked_at) "
            "VALUES(?,?,?,?,1,?,?,?,?)",
            (unit_id, order_id, o["order_no"], relation_type, (reason or None), change_id,
             actor_id, _logi_now()))
        return cur.lastrowid


def get_unit_relations(unit_id) -> list:
    """분할·통합 관계 이력 조회(읽기 전용).
    ⛔ V1: 생성·실행·승인 기능 없음 — WP-04 영향분석 연결 후 구현."""
    with db_session() as c:
        return [dict(r) for r in c.execute(
            "SELECT * FROM project_unit_relations WHERE source_unit_id=? OR result_unit_id=? "
            "ORDER BY id", (unit_id, unit_id)).fetchall()]
