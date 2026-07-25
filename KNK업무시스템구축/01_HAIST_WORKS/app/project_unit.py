# -*- coding: utf-8 -*-
# ============================================================
# v5H226z1053 (2026-07-25, ERP V1 전환 WP-03) — 프로젝트 호기·일련번호 (Project Unit·Serial)
# ------------------------------------------------------------
# ADR-001: 프로젝트 → [수주] → 호기(Project Unit·필수) → 일련번호(Serial·후발급)
#   · project_unit.id = 앞으로 BOM·출고·투입·변경·출하가 붙는 영구 축
#   · equipment_serial = 표시 식별값(PK 아님)·법인 내 유일·출하 전 필수
#
# ⭐ 순수 추가(additive): 기존 order_items·작업일정표는 건드리지 않는다(교량 조건).
#    호기는 order_items(호기 라인)에서 '씨앗'으로 생성. 씨앗 대상 = 정식 호기 라벨 '^\d+호기$'
#    (기존 z779 재번호 대상과 동일 정의) — 부속/부품(비표준 라벨) 라인은 호기가 아니므로 제외.
#
# RS-01 통과 기준: "관리번호에서 호기 N대와 각 일련번호를 조회할 수 있다."
# RS-01 차단조건: ①같은 프로젝트 제작번호 중복 ②일련번호 중복(법인 내) ③프로젝트 없는 호기
#                ④호기 삭제는 초안 + 이력(일련번호 등) 없을 때만
# ============================================================
import re
import sqlite3

from .database import db_session, _logi_now

# 정식 호기 라벨(기존 시스템 규약·z779). 부속/부품(비표준 라벨)은 매칭 안 됨 → 씨앗 제외.
HOGI_RE = re.compile(r"^\d+호기$")

# 호기에 붙는 하위 이력 테이블 — 삭제 가드용 '전참조 스캔'(WP-01 교훈).
#   WP-04+ 에서 호기에 붙는 표(BOM 기준·출고·실투입 등)가 생기면 여기에 등록한다.
_UNIT_REF_TABLES = (
    ("equipment_serials", "project_unit_id", "일련번호"),
)


def _project_entity(c, pid) -> str:
    """프로젝트 법인(일련번호 유일성 스코프). V1: po/ship_entity 에 VN 신호가 없으면 KOR(본사).
    (검사기 국내 시범=KOR. 베트남 호기 씨앗 시 teams.entity 기준으로 정교화 — WP-03 후속.)"""
    try:
        r = c.execute("SELECT po_entity, ship_entity FROM projects WHERE id=?", (pid,)).fetchone()
        if r:
            for v in (r["po_entity"], r["ship_entity"]):
                s = (v or "").strip().upper()
                if s in ("VN", "VINA", "VIETNAM", "베트남"):
                    return "VN"
    except Exception:
        pass
    return "KOR"


def _unit_ref_counts(c, unit_id) -> dict:
    """이 호기에 붙은 하위 이력 건수(라벨→건수). 삭제 가드가 이걸로 '이력 없음'을 확인."""
    have = {r[0] for r in c.execute(
        "SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    out = {}
    for tbl, col, label in _UNIT_REF_TABLES:
        if tbl in have:
            out[label] = c.execute(
                f"SELECT COUNT(*) FROM {tbl} WHERE {col}=?", (unit_id,)).fetchone()[0]
    return out


def count_hogi_lines(pid) -> int:
    """씨앗 대상(정식 호기 라인 '^\\d+호기$') 수 — 호기 수 대조용."""
    with db_session() as c:
        rows = c.execute(
            "SELECT oi.unit_label FROM order_items oi JOIN orders o ON o.id=oi.order_id "
            "WHERE o.project_id=?", (pid,)).fetchall()
    return sum(1 for r in rows if HOGI_RE.match((r["unit_label"] or "")))


def seed_units_from_orders(pid, actor_id=0) -> dict:
    """order_items(호기 라인) → project_units 씨앗. **멱등**(이미 씨앗된 라인 건너뜀).
    씨앗 대상 = unit_label 이 '^\\d+호기$' 인 라인만. 반환: 호기 수 대조용 집계."""
    created, skipped, unit_ids = 0, 0, []
    with db_session() as c:
        pr = c.execute("SELECT id FROM projects WHERE id=?", (pid,)).fetchone()
        if not pr:
            raise ValueError("프로젝트가 없습니다.")   # RS-01: Project 없는 호기 금지
        entity = _project_entity(c, pid)
        rows = c.execute(
            "SELECT oi.id AS oid, oi.unit_label AS lbl, oi.order_id AS ord "
            "FROM order_items oi JOIN orders o ON o.id=oi.order_id "
            "WHERE o.project_id=? "
            "ORDER BY o.order_date ASC, o.id ASC, oi.id ASC", (pid,)).fetchall()
        target = [(r["oid"], (r["lbl"] or ""), r["ord"])
                  for r in rows if HOGI_RE.match((r["lbl"] or ""))]
        for oi_id, lbl, oid in target:
            ex = c.execute("SELECT id FROM project_units WHERE seed_order_item_id=?",
                           (oi_id,)).fetchone()
            if ex:
                skipped += 1
                continue
            try:
                cur = c.execute(
                    "INSERT INTO project_units(project_id, order_id, seed_order_item_id, "
                    "unit_no, entity, status, created_by, created_at, updated_at) "
                    "VALUES(?,?,?,?,?,'draft',?,?,?)",
                    (pid, oid, oi_id, lbl, entity, actor_id, _logi_now(), _logi_now()))
                unit_ids.append(cur.lastrowid)
                created += 1
            except sqlite3.IntegrityError:
                # 같은 프로젝트에 이미 같은 제작번호(라벨 미정리 데이터) → 건너뜀(멱등·숨기지 않고 집계)
                skipped += 1
    return {"target_lines": len(target), "created": created,
            "skipped": skipped, "unit_ids": unit_ids}


def _unit_sort_key(u):
    m = re.match(r"^(\d+)", u.get("unit_no") or "")
    return (int(m.group(1)) if m else 999999, u.get("id") or 0)


def get_units(pid) -> list:
    """프로젝트 호기 목록 + 각 호기의 활성 일련번호·일련번호 개수 (RS-01 조회·화면)."""
    with db_session() as c:
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
        u["serials"] = [dict(r) for r in c.execute(
            "SELECT * FROM equipment_serials WHERE project_unit_id=? ORDER BY id DESC",
            (unit_id,)).fetchall()]
    return u


def project_unit_summary(pid) -> dict:
    """상세 페이지 카드용: 호기 수·일련번호 부여 수·씨앗 대상(호기 라인) 수."""
    with db_session() as c:
        n_units = c.execute(
            "SELECT COUNT(*) FROM project_units WHERE project_id=?", (pid,)).fetchone()[0]
        n_serial = c.execute(
            "SELECT COUNT(*) FROM project_units pu JOIN equipment_serials es "
            "ON es.project_unit_id=pu.id AND es.active=1 WHERE pu.project_id=?",
            (pid,)).fetchone()[0]
        rows = c.execute(
            "SELECT oi.unit_label AS lbl FROM order_items oi JOIN orders o ON o.id=oi.order_id "
            "WHERE o.project_id=?", (pid,)).fetchall()
    n_lines = sum(1 for r in rows if HOGI_RE.match((r["lbl"] or "")))
    return {"units": n_units, "serials": n_serial, "hogi_lines": n_lines}


def create_unit(pid, unit_no, equipment_type=None, actor_id=0, note=None) -> int:
    """호기 수동 생성. RS-01 차단: 프로젝트 없음·제작번호 중복."""
    unit_no = (unit_no or "").strip()
    if not unit_no:
        raise ValueError("제작번호(호기)를 입력하세요.")
    with db_session() as c:
        pr = c.execute("SELECT id FROM projects WHERE id=?", (pid,)).fetchone()
        if not pr:
            raise ValueError("프로젝트가 없습니다.")   # RS-01: Project 없는 호기 금지
        dup = c.execute("SELECT id FROM project_units WHERE project_id=? AND unit_no=?",
                        (pid, unit_no)).fetchone()
        if dup:
            raise ValueError(f"이미 있는 제작번호입니다: {unit_no}")   # RS-01: Unit No 중복
        entity = _project_entity(c, pid)
        cur = c.execute(
            "INSERT INTO project_units(project_id, unit_no, equipment_type, entity, "
            "status, note, created_by, created_at, updated_at) "
            "VALUES(?,?,?,?, 'draft', ?, ?, ?, ?)",
            (pid, unit_no, (equipment_type or None), entity, (note or None),
             actor_id, _logi_now(), _logi_now()))
        return cur.lastrowid


def link_serial(unit_id, serial_no, actor_id=0, note=None) -> int:
    """호기에 일련번호 연결. RS-01 차단: 법인 내 중복. 기존 활성 일련번호는 이력으로 비활성화(끊김 방지)."""
    serial_no = (serial_no or "").strip()
    if not serial_no:
        raise ValueError("일련번호를 입력하세요.")
    with db_session() as c:
        u = c.execute("SELECT id, entity FROM project_units WHERE id=?", (unit_id,)).fetchone()
        if not u:
            raise ValueError("호기가 없습니다.")
        entity = u["entity"] or "KOR"
        dup = c.execute(
            "SELECT es.id FROM equipment_serials es "
            "WHERE es.entity=? AND es.serial_no=? AND es.active=1 AND es.project_unit_id<>?",
            (entity, serial_no, unit_id)).fetchone()
        if dup:
            raise ValueError(f"이미 쓰인 일련번호입니다({entity}): {serial_no}")   # RS-01: Serial 중복
        c.execute("UPDATE equipment_serials SET active=0 WHERE project_unit_id=? AND active=1",
                  (unit_id,))
        cur = c.execute(
            "INSERT INTO equipment_serials(project_unit_id, serial_no, entity, active, "
            "note, issued_by, issued_at) VALUES(?,?,?,1,?,?,?)",
            (unit_id, serial_no, entity, (note or None), actor_id, _logi_now()))
        c.execute(
            "UPDATE project_units SET status=CASE WHEN status='draft' THEN 'active' ELSE status END, "
            "updated_at=? WHERE id=?", (_logi_now(), unit_id))
        return cur.lastrowid


def delete_unit(unit_id, actor_id=0) -> bool:
    """호기 삭제 — ADR: 초안 상태 + 이력(일련번호 등) 없을 때만."""
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
