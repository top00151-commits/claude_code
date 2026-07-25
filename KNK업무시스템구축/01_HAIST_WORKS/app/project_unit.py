# -*- coding: utf-8 -*-
# ============================================================
# v5H226z1053 (2026-07-25, ERP V1 전환 WP-03) — 프로젝트 호기·일련번호 (Project Unit·Serial)
# 게이트 검토판정(2026-07-25) P0/P1 반영본.
# ------------------------------------------------------------
# ADR-001: 프로젝트 → [수주] → 호기(Project Unit·필수) → 일련번호(Serial·후발급)
#   · project_unit.id = 앞으로 BOM·출고·투입·변경·출하가 붙는 영구 축
#   · equipment_serial = 표시 식별값(PK 아님)·법인 내 영구 유일·출하 전 필수
#
# ⭐ 순수 추가(additive): 기존 order_items·작업일정표 무변경(교량 조건).
#    씨앗 대상 = 정식 호기 라벨 '^\d+호기$'(z779 규약)만. 부속/부품(비표준 라벨) 제외.
#
# 게이트 반영:
#   [P0-01] 일련번호 법인 내 영구 유일(과거 포함·대소문자 무시)·호기당 활성 1건·교체 메타/연결
#   [P0-02] 씨앗 전 정식 호기 라인 수량=1 검사 → 아니면 전체 중단(부분 씨앗 금지)
#   [P0-03] 일련번호 교체 = 사유 필수 + 종료 메타 + 이력 조회 API
#   [P0-04] 법인 KOR/VN — 충돌 시 중단(entity CHECK 는 DB)
#   [P1-7.1] 삭제 가드 = FK 메타데이터 동적 전참조 스캔(고정 목록 아님)
#   [P1-7.2] 씨앗 원본(수주번호·라벨) 스냅샷 보존
#   [P1-8.1/8.2] 미씨앗 카운트·결과 분리(created/already/conflicts)
#   [P1-9.1/9.2/9.3] unit_no 정규화·일련번호 대소문자·동일 재입력 무동작
# ============================================================
import re
import sqlite3

from .database import db_session, _logi_now

# 정식 호기 라벨(기존 시스템 규약·z779). 부속/부품(비표준 라벨)은 매칭 안 됨 → 씨앗 제외.
HOGI_RE = re.compile(r"^\d+호기$")
_HOGI_NUM_RE = re.compile(r"^0*(\d+)호기$")
_VN_SIG = ("VN", "VNM", "VINA", "VIETNAM", "베트남")
_KOR_SIG = ("KR", "KOR", "KOREA", "한국", "본사", "HQ")


def _norm_unit_no(s) -> str:
    """제작번호 정규화(P1-9.1): 공백 제거 + 'N호기'는 앞자리 0 제거('01호기'·'1 호기'→'1호기')."""
    s = re.sub(r"\s+", "", (s or "")).strip()
    m = _HOGI_NUM_RE.match(s)
    return f"{int(m.group(1))}호기" if m else s


def _project_entity(c, pid) -> str:
    """프로젝트 법인(일련번호 유일성 스코프) — KOR/VN. 충돌(둘 다 명시·불일치)이면 중단(P0-04).
    빈값은 KOR(본사) — ⚠국내 시범 한정. 전체 확산 전 단일 기준을 대표가 확정해야 함."""
    try:
        r = c.execute("SELECT po_entity, ship_entity FROM projects WHERE id=?", (pid,)).fetchone()
    except sqlite3.OperationalError:
        return "KOR"   # 법인 컬럼이 없는 스키마(구버전) — 국내 기본
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


def _unit_ref_counts(c, unit_id) -> dict:
    """이 호기를 참조하는 **모든 표**를 FK 메타데이터로 동적 스캔(전참조 스캔·WP-01 방식·P1-7.1).
    WP-04+ 에서 project_units 를 FK 로 참조하는 표가 생기면 자동 포함(목록 등록 누락 위험 없음)."""
    out = {}
    tables = [r[0] for r in c.execute(
        "SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    for tbl in tables:
        if tbl == "project_units":
            continue
        try:
            fks = c.execute(f"PRAGMA foreign_key_list([{tbl}])").fetchall()
        except sqlite3.Error:
            continue
        for fk in fks:
            # fk 컬럼: (id, seq, table, from, to, on_update, on_delete, match)
            if fk[2] == "project_units":
                col = fk[3]
                n = c.execute(
                    f"SELECT COUNT(*) FROM [{tbl}] WHERE [{col}]=?", (unit_id,)).fetchone()[0]
                if n:
                    out[f"{tbl}.{col}"] = out.get(f"{tbl}.{col}", 0) + n
    return out


def _hogi_target_rows(c, pid):
    """이 프로젝트의 정식 호기 라인(order_items) — 씨앗 대상. (id, label, order_id, qty, order_no)."""
    rows = c.execute(
        "SELECT oi.id AS oid, oi.unit_label AS lbl, oi.order_id AS ord, "
        "oi.qty AS qty, o.order_no AS ono "
        "FROM order_items oi JOIN orders o ON o.id=oi.order_id "
        "WHERE o.project_id=? "
        "ORDER BY o.order_date ASC, o.id ASC, oi.id ASC", (pid,)).fetchall()
    return [r for r in rows if HOGI_RE.match((r["lbl"] or ""))]


def count_hogi_lines(pid) -> int:
    """씨앗 대상(정식 호기 라인) 총수 — 호기 수 대조용."""
    with db_session() as c:
        return len(_hogi_target_rows(c, pid))


def count_unseeded_hogi_lines(pid) -> int:
    """아직 호기로 안 만든 정식 호기 라인 수(P1-8.1 · 씨앗 버튼 정확 계산)."""
    with db_session() as c:
        target = _hogi_target_rows(c, pid)
        seeded = {r[0] for r in c.execute(
            "SELECT seed_order_item_id FROM project_units "
            "WHERE project_id=? AND seed_order_item_id IS NOT NULL", (pid,)).fetchall()}
    return sum(1 for r in target if r["oid"] not in seeded)


def seed_units_from_orders(pid, actor_id=0) -> dict:
    """order_items(정식 호기 라인) → project_units 씨앗. **멱등**.
    [P0-02] 정식 호기 라인 수량이 1이 아니면(0/NULL/소수/≥2) **전체 중단**(부분 씨앗 금지).
    반환(P1-8.2 분리): target_lines/created/already_seeded/unit_no_conflicts/unit_ids."""
    with db_session() as c:
        pr = c.execute("SELECT id FROM projects WHERE id=?", (pid,)).fetchone()
        if not pr:
            raise ValueError("프로젝트가 없습니다.")           # RS-01: Project 없는 호기 금지
        entity = _project_entity(c, pid)                       # 충돌이면 여기서 중단
        target = _hogi_target_rows(c, pid)
        # [P0-02] 수량=1 강제 — 위반 라인이 하나라도 있으면 아무것도 만들지 않음
        bad = [(r["oid"], r["ono"], r["lbl"], r["qty"]) for r in target
               if r["qty"] is None or float(r["qty"]) != 1.0]
        if bad:
            head = "; ".join(f"{(o or '')} {l}(수량 {q})" for _, o, l, q in bad[:5])
            more = " 외" if len(bad) > 5 else ""
            raise ValueError(
                f"정식 호기 라인은 수량이 1이어야 합니다. 위반 {len(bad)}건: {head}{more}. "
                "데이터를 고친 뒤 다시 실행하세요(부분 생성 안 함).")
        created, already, conflicts, unit_ids = 0, 0, [], []
        for r in target:
            oi_id, lbl, oid, ono = r["oid"], (r["lbl"] or ""), r["ord"], r["ono"]
            if c.execute("SELECT id FROM project_units WHERE seed_order_item_id=?",
                         (oi_id,)).fetchone():
                already += 1
                continue
            unit_no = _norm_unit_no(lbl)
            if c.execute("SELECT id FROM project_units WHERE project_id=? AND unit_no=?",
                         (pid, unit_no)).fetchone():
                conflicts.append(unit_no)
                continue
            cur = c.execute(
                "INSERT INTO project_units(project_id, order_id, seed_order_item_id, seed_order_no, "
                "seed_unit_label, unit_no, entity, status, created_by, created_at, updated_at) "
                "VALUES(?,?,?,?,?,?,?, 'draft', ?, ?, ?)",
                (pid, oid, oi_id, ono, lbl, unit_no, entity, actor_id, _logi_now(), _logi_now()))
            unit_ids.append(cur.lastrowid)
            created += 1
    return {"target_lines": len(target), "created": created, "already_seeded": already,
            "unit_no_conflicts": conflicts, "unit_ids": unit_ids}


def _unit_sort_key(u):
    m = re.match(r"^(\d+)", u.get("unit_no") or "")
    return (int(m.group(1)) if m else 999999, u.get("id") or 0)


def get_units(pid) -> list:
    """프로젝트 호기 목록 + 각 호기의 활성 일련번호·일련번호 이력 수 (RS-01 조회·화면)."""
    with db_session() as c:
        if not _table_ready(c):
            return []
        units = [dict(r) for r in c.execute(
            "SELECT * FROM project_units WHERE project_id=?", (pid,)).fetchall()]
        for u in units:
            sn = c.execute(
                "SELECT serial_no FROM equipment_serials "
                "WHERE project_unit_id=? AND active=1 ORDER BY id DESC LIMIT 1",
                (u["id"],)).fetchone()
            u["serial_no"] = sn["serial_no"] if sn else None
            u["serial_count"] = c.execute(
                "SELECT COUNT(*) FROM equipment_serials WHERE project_unit_id=?",
                (u["id"],)).fetchone()[0]
    units.sort(key=_unit_sort_key)
    return units


def get_unit(unit_id):
    with db_session() as c:
        u = c.execute("SELECT * FROM project_units WHERE id=?", (unit_id,)).fetchone()
        if not u:
            return None
        u = dict(u)
        u["serials"] = get_serial_history(unit_id, _conn=c)
    return u


def get_serial_history(unit_id, _conn=None) -> list:
    """호기의 일련번호 이력 전체(P0-03 조회 계약) — 활성/비활성·교체 메타 포함."""
    def _q(c):
        return [dict(r) for r in c.execute(
            "SELECT es.*, iu.name AS issued_by_name, du.name AS deactivated_by_name "
            "FROM equipment_serials es "
            "LEFT JOIN users iu ON iu.id=es.issued_by "
            "LEFT JOIN users du ON du.id=es.deactivated_by "
            "WHERE es.project_unit_id=? ORDER BY es.id DESC", (unit_id,)).fetchall()]
    if _conn is not None:
        return _q(_conn)
    with db_session() as c:
        return _q(c)


def project_unit_summary(pid) -> dict:
    """상세 페이지 카드용: 호기 수·일련번호 부여 수·씨앗 대상·미씨앗 수."""
    with db_session() as c:
        ready = _table_ready(c)
        n_units = c.execute("SELECT COUNT(*) FROM project_units WHERE project_id=?",
                            (pid,)).fetchone()[0] if ready else 0
        n_serial = c.execute(
            "SELECT COUNT(*) FROM project_units pu JOIN equipment_serials es "
            "ON es.project_unit_id=pu.id AND es.active=1 WHERE pu.project_id=?",
            (pid,)).fetchone()[0] if ready else 0
        target = _hogi_target_rows(c, pid)
        seeded = {r[0] for r in c.execute(
            "SELECT seed_order_item_id FROM project_units "
            "WHERE project_id=? AND seed_order_item_id IS NOT NULL", (pid,)).fetchall()} if ready else set()
    n_unseeded = sum(1 for r in target if r["oid"] not in seeded)
    return {"ready": ready, "units": n_units, "serials": n_serial,
            "hogi_lines": len(target), "unseeded": n_unseeded}


def _table_ready(c) -> bool:
    """마이그레이션이 아직 안 돌아 표가 없으면 False(P1-9.4 · 런타임 오류 대신 안내)."""
    return bool(c.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='project_units'").fetchone())


def create_unit(pid, unit_no, equipment_type=None, actor_id=0, note=None) -> int:
    """호기 수동 생성. RS-01 차단: 프로젝트 없음·제작번호 중복(정규화 후)."""
    unit_no = _norm_unit_no(unit_no)
    if not unit_no:
        raise ValueError("제작번호(호기)를 입력하세요.")
    with db_session() as c:
        if not c.execute("SELECT id FROM projects WHERE id=?", (pid,)).fetchone():
            raise ValueError("프로젝트가 없습니다.")
        if c.execute("SELECT id FROM project_units WHERE project_id=? AND unit_no=?",
                     (pid, unit_no)).fetchone():
            raise ValueError(f"이미 있는 제작번호입니다: {unit_no}")
        entity = _project_entity(c, pid)
        cur = c.execute(
            "INSERT INTO project_units(project_id, unit_no, equipment_type, entity, "
            "status, note, created_by, created_at, updated_at) "
            "VALUES(?,?,?,?, 'draft', ?, ?, ?, ?)",
            (pid, unit_no, (equipment_type or None), entity, (note or None),
             actor_id, _logi_now(), _logi_now()))
        return cur.lastrowid


def link_serial(unit_id, serial_no, actor_id=0, reason=None, note=None) -> int:
    """호기에 일련번호 연결/교체.
    [P0-01] 법인 내 영구 유일(과거 포함·대소문자 무시)·호기당 활성 1건.
    [P0-03] 교체 시 사유 필수 + 이전행 종료 메타 + supersedes 연결.
    [P1-9.3] 동일 호기에 동일 일련번호 재입력 = 무동작(중복 이력 방지)."""
    serial_no = (serial_no or "").strip()
    if not serial_no:
        raise ValueError("일련번호를 입력하세요.")
    with db_session() as c:
        u = c.execute("SELECT id, entity FROM project_units WHERE id=?", (unit_id,)).fetchone()
        if not u:
            raise ValueError("호기가 없습니다.")
        entity = u["entity"] or "KOR"
        cur_active = c.execute(
            "SELECT id, serial_no FROM equipment_serials WHERE project_unit_id=? AND active=1",
            (unit_id,)).fetchone()
        # [9.3] 같은 일련번호를 같은 호기에 재입력 → 무동작
        if cur_active and (cur_active["serial_no"] or "").upper() == serial_no.upper():
            return cur_active["id"]
        # [P0-01] 법인 내 영구 유일(과거 포함·대소문자 무시)
        if c.execute("SELECT id FROM equipment_serials WHERE entity=? AND serial_no=? COLLATE NOCASE",
                     (entity, serial_no)).fetchone():
            raise ValueError(f"이미 쓰인 일련번호입니다({entity}·과거 포함): {serial_no}")
        # [P0-03] 교체(기존 활성 존재)면 사유 필수
        if cur_active and not (reason or "").strip():
            raise ValueError("일련번호를 교체하려면 사유를 입력하세요.")
        if cur_active:
            c.execute(
                "UPDATE equipment_serials SET active=0, deactivated_at=?, deactivated_by=?, "
                "deactivation_reason=? WHERE id=?",
                (_logi_now(), actor_id, (reason or "").strip(), cur_active["id"]))
        cur = c.execute(
            "INSERT INTO equipment_serials(project_unit_id, serial_no, entity, active, note, "
            "issued_by, issued_at, supersedes_serial_id) VALUES(?,?,?,1,?,?,?,?)",
            (unit_id, serial_no, entity, (note or None), actor_id, _logi_now(),
             cur_active["id"] if cur_active else None))
        c.execute(
            "UPDATE project_units SET status=CASE WHEN status='draft' THEN 'active' ELSE status END, "
            "updated_at=? WHERE id=?", (_logi_now(), unit_id))
        return cur.lastrowid


def delete_unit(unit_id, actor_id=0) -> bool:
    """호기 삭제 — ADR: 초안 상태 + 이력(일련번호·하위 참조) 없을 때만. 전참조 스캔(P1-7.1)."""
    with db_session() as c:
        u = c.execute("SELECT id, status FROM project_units WHERE id=?", (unit_id,)).fetchone()
        if not u:
            raise ValueError("호기가 없습니다.")
        if (u["status"] or "draft") != "draft":
            raise ValueError("초안 상태의 호기만 삭제할 수 있습니다.")
        blocking = {k: v for k, v in _unit_ref_counts(c, unit_id).items() if v > 0}
        if blocking:
            desc = ", ".join(f"{k} {v}건" for k, v in blocking.items())
            raise ValueError(f"이력이 있어 삭제할 수 없습니다: {desc}")
        c.execute("DELETE FROM project_units WHERE id=?", (unit_id,))
    return True
