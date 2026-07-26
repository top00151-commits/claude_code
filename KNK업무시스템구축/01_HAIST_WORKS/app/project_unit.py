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
from datetime import datetime

from .database import db_session, _logi_now

# 정식 호기 라벨(기존 시스템 규약·z779). 부속/부품(비표준 라벨)은 후보에서 제외.
HOGI_RE = re.compile(r"^\d+호기$")
_HOGI_NUM_RE = re.compile(r"^0*(\d+)호기$")
# ── 시작 법인(KOR/VN) = **관리번호가 단일 근거** ────────────────────────────────
# [대표 규정 V1 2026-07-26 `KNK_WORKS_ERP_베트남법인_배포및관리번호적용규정_V1`]
#   §3  본사 `[순번3][업무구분][YYMM]`(8자리) · 베트남 `[순번3][V][업무구분][YYMM]`(9자리)
#   §4  법인 구분 = **최초로 시작한 법인**. 담당자·생산 장소·최종 출하처가 아니다.
#       ⛔ 그래서 po_entity/ship_entity(주문 법인·출하 법인)를 근거로 쓰지 않는다.
#         '한국에서 수주 → 베트남으로 출하'는 **정상 업무**이지 충돌이 아니다(실데이터 존재).
#   §1·§6 현재 WORKS 데이터는 전부 본사 진행분 → V 없는 번호 = KOR.
#   §7  읽을 수 없으면 **임의로 KOR 를 넣지 않고 중단**한다.
#   §8  V 발번 도입 자체는 WP-03 범위 밖(별도 전사 작업).
#   ※ A 접두(A01T2606)는 검증(테스트) 모드 관리번호 — 본사 발급분이라 KOR.
MGMT_RE = re.compile(r"^(?:A\d{2}|\d{3})(V?)([TMLECR])(\d{4})$")

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


# ── 적용시점(Effectivity) 입력 검증 ─────────────────────────────
# [게이트 v6 P1-02] 화면은 날짜칸을 쓰지만 HTTP 요청은 화면을 통하지 않고 직접 보낼 수 있다.
#   문자열 비교만 하면 '0001-01-01' 같은 값이 '과거'로 통과해 이력에 들어가고,
#   '20260501'·'2026/05/01' 은 엉뚱하게 "미래 예약" 이라며 거부돼 사용자가 이유를 오해한다.
#   → 서버에서 **명시적으로 해석·정규화**하고, 형식 위반은 이력 변경 전에 거부한다.
_EFF_DATE_FMT = "%Y-%m-%d"
_EFF_DT_FMTS = ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M")
_EFF_MIN_YEAR = 2000            # 업무상 있을 수 없는 과거(오타·기본값 유입) 차단


def norm_effective_from(s) -> str:
    """적용시점 문자열을 해석·정규화한다. 빈값이면 '' (호출부가 '지금'으로 처리).
    허용: `YYYY-MM-DD` / `YYYY-MM-DD HH:MM[:SS]`(T 구분자 포함). 그 외·없는 날짜는 거부."""
    s = re.sub(r"\s+", " ", (s or "")).strip()
    if not s:
        return ""
    out = None
    try:
        out = datetime.strptime(s, _EFF_DATE_FMT).strftime(_EFF_DATE_FMT)
    except ValueError:
        for f in _EFF_DT_FMTS:
            try:
                out = datetime.strptime(s, f).strftime("%Y-%m-%d %H:%M:%S")
                break
            except ValueError:
                continue
    if not out:
        raise ValueError("적용시점 형식이 올바르지 않습니다. 날짜로 입력하세요(예: 2026-05-01).")
    if int(out[:4]) < _EFF_MIN_YEAR:
        raise ValueError(f"적용시점이 너무 이릅니다({out[:10]}). {_EFF_MIN_YEAR}년 이후로 입력하세요.")
    return out


# ── 감사 기록(업무 변경과 **같은 트랜잭션**) ─────────────────────
# [게이트 v6 P0-03] 업무 변경이 먼저 커밋되고 감사 기록이 다른 연결에서 실패하면
#   "업무는 바뀌었는데 누가·왜 바꿨는지는 없는" 상태가 남는다.
#   관리자 비상복구 감사를 필수로 정한 이상 **둘 다 성공하거나 둘 다 실패**해야 한다.
def _audit_tx(c, audit):
    """열린 트랜잭션 안에서 감사 1건 기록. audit=None(일반 업무)이면 아무것도 하지 않는다."""
    if not audit:
        return
    c.execute(
        "INSERT INTO project_unit_audit(actor_id, actor_name, action, target, note, created_at) "
        "VALUES(?,?,?,?,?,?)",
        (audit.get("actor_id") or 0, audit.get("actor_name") or "", audit.get("action") or "",
         audit.get("target") or "", audit.get("note") or "", _logi_now()))


def _table_ready(c) -> bool:
    return bool(c.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='project_units'").fetchone())


def mgmt_code_entity(code) -> str:
    """관리번호 → 시작 법인('KOR'/'VN'). 읽을 수 없으면 ValueError(임의 부여 금지)."""
    s = (code or "").strip().upper()
    if not s:
        raise ValueError("프로젝트에 관리번호가 없습니다. 관리번호를 먼저 발급하세요"
                         "(시작 법인은 관리번호로 정해집니다).")
    m = MGMT_RE.match(s)
    if not m:
        raise ValueError(f"관리번호 형식을 읽을 수 없어 시작 법인을 정할 수 없습니다({s}). "
                         "정상 발급된 관리번호가 필요합니다"
                         "(임의로 본사로 처리하지 않습니다 · 규정 V1 §7).")
    return "VN" if m.group(1) else "KOR"


def _project_entity(c, pid) -> str:
    """[F-08 · 규정 V1] 프로젝트 **시작 법인** — 관리번호에서 읽는다.
    ⛔ 임의 KOR 부여 금지: 관리번호가 없거나 형식을 못 읽으면 중단한다."""
    r = c.execute("SELECT mgmt_code FROM projects WHERE id=?", (pid,)).fetchone()
    if not r:
        raise ValueError("프로젝트가 없습니다.")
    return mgmt_code_entity(r["mgmt_code"])


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
                # [대표 지시 07-25] '수주내역 표기를 호기번호로 그대로 쓰기' 를 고를 수 있는지.
                #   [F-06] 한 관리번호에서 한 번 쓴 번호는 취소분·과거이력 포함 재사용 금지 →
                #   이미 쓴 번호면 화면에서 그 선택지를 아예 못 고르게 한다(눌러보고 거부당하지 않게).
                "no_taken": bool(no) and _unit_no_ever_used(c, pid, no),
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


def apply_candidate_decisions(pid, decisions, reason, actor_id=0, audit=None) -> dict:
    """사용자가 **후보마다 내린 판정**을 반영한다(F-01/F-02/F-03).

    decisions = [{order_item_id, action, unit_id?, relation_type?}, ...]
      · action='new'    → 신규 **개발호기**(PROVISIONAL) 생성.
                          ⭐ current_unit_no 는 **NULL**(후보 라벨은 working_name·seed 에만 보존).
      · action='new_no' → 신규 개발호기 + **수주내역 표기를 호기번호로 그대로 사용**.
                          [대표 지시 2026-07-25] F-01 이 금지한 것은 **자동 승격**이고,
                          사용자가 화면에서 보고 이 선택지를 고르는 것은 **명시 지정**이다.
                          (표기와 최종 호기번호가 딱 맞는 프로젝트에서 23번을 다시 입력하게 만들지 않는다.)
      · action='link'   → 기존 Unit 에 이 수주를 관계로 연결(ORIGIN/ADDITIONAL/CHANGE).
      · action='hold'/'exclude' → 아무것도 하지 않음(보류·제외).
    반영 사유(reason)는 **필수**.
    """
    if not (reason or "").strip():
        raise ValueError("반영 사유를 입력하세요.")
    decisions = [d for d in (decisions or []) if (d or {}).get("action") in ("new", "new_no", "link")]
    if not decisions:
        raise ValueError("반영할 후보를 선택하세요.")
    scan = scan_candidates(pid)
    if not scan["ready"]:
        raise ValueError("호기 기능이 아직 준비되지 않았습니다.")
    by_id = {c0["order_item_id"]: c0 for c0 in scan["candidates"]}
    created, linked, rejected, numbered = [], [], [], []
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
            if d["action"] in ("new", "new_no"):
                # 'new_no' 만 표기를 호기번호로 승격한다(사용자가 명시 선택한 경우).
                unit_no = _norm_unit_no(cd["label"]) if d["action"] == "new_no" else None
                if unit_no and _unit_no_ever_used(c, pid, unit_no):
                    # [F-06] 취소분·과거 이력 포함 재사용 금지 — 조용히 넘기지 않고 사유를 알린다.
                    rejected.append((oid, f"이 관리번호에서 이미 쓴 호기번호입니다(취소분 포함): {unit_no}"))
                    continue
                cur = c.execute(
                    "INSERT INTO project_units(project_id, working_name, current_unit_no, "
                    "unit_state, entity, seed_order_item_id, seed_order_no, seed_unit_label, "
                    "note, created_by, created_at, updated_by, updated_at) "
                    "VALUES(?,?,?, 'PROVISIONAL', ?,?,?,?,?,?,?,?,?)",
                    (pid, cd["label"], unit_no, entity, oid, cd["order_no"], cd["label"],
                     reason.strip(), actor_id, _logi_now(), actor_id, _logi_now()))
                uid = cur.lastrowid
                if unit_no:
                    # 번호를 정했으면 **변경이력 첫 줄**을 남긴다(나중에 바꿔도 처음 값을 안다).
                    _n0 = _logi_now()
                    c.execute(
                        "INSERT INTO project_unit_identifier_history(project_unit_id, old_unit_no, "
                        "new_unit_no, change_reason, changed_by, changed_at, effective_from) "
                        "VALUES(?,NULL,?,?,?,?,?)",
                        (uid, unit_no, f"수주내역 표기로 최초 지정 — {reason.strip()}",
                         actor_id, _n0, _n0))
                    numbered.append(uid)
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
        # [게이트 v6 P0-03] 감사도 **같은 트랜잭션** — 감사가 실패하면 이 반영 전체가 취소된다.
        if audit:
            _a = dict(audit)
            _a["note"] = (f"{_a.get('note') or ''} — 신규 {len(created)}(번호지정 {len(numbered)}) · "
                          f"연결 {len(linked)} · 거부 {len(rejected)}").strip()
            _audit_tx(c, _a)
    return {"created": len(created), "created_ids": created, "numbered": len(numbered),
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
               actor_id=0, change_id=None, audit=None) -> int:
    with db_session() as c:
        rid = _link_order_tx(c, unit_id, order_id, relation_type, reason, actor_id, change_id)
        _audit_tx(c, audit)          # [v6 P0-03] 연결과 감사는 함께 남거나 함께 취소
        return rid


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


def _unit_no_at_tx(c, unit_id, when: str):
    """열린 연결에서 '그 시점에 유효한 호기번호' 계산 — 적용구간(effective_from/to) 기준."""
    r = c.execute(
        "SELECT new_unit_no FROM project_unit_identifier_history "
        "WHERE project_unit_id=? AND COALESCE(effective_from,'') <= ? "
        "AND (effective_to IS NULL OR effective_to > ?) "
        "ORDER BY COALESCE(effective_from,''), id DESC LIMIT 1", (unit_id, when, when)).fetchone()
    return r["new_unit_no"] if r else None


def unit_no_at(unit_id, when: str):
    """[F-07] **업무 적용시점(effective_from/to)** 기준으로 그 시점의 호기번호를 재현한다.
    changed_at(기록시각)은 누가 언제 입력했는지를 나타내는 audit 값이며 조회 기준이 아니다."""
    with db_session() as c:
        return _unit_no_at_tx(c, unit_id, when)


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
        # ⚠[대표 지적 07-26] 후보 수는 **아직 반영 안 한 것만** 센다.
        #   전체 호기 라인 수를 그대로 보이면, 23대를 다 등록한 뒤에도 '후보 23'이 남아
        #   "아직 23개 할 일이 있나?" 로 읽힌다(이미 반영된 것은 후보가 아니다).
        _rows = _hogi_candidate_rows(c, pid)
        _seeded = {r[0] for r in c.execute(
            "SELECT seed_order_item_id FROM project_units "
            "WHERE project_id=? AND seed_order_item_id IS NOT NULL", (pid,)).fetchall()}
        cands = sum(1 for r in _rows if r["oid"] not in _seeded)
        wired = impact_status(c, 0)["wired"]
    return {"ready": True, "units": sum(st.values()),
            "provisional": st.get("PROVISIONAL", 0), "confirmed": st.get("CONFIRMED", 0),
            "cancelled": st.get("CANCELLED", 0), "candidates": cands,
            "candidates_total": len(_rows), "candidates_done": len(_rows) - cands,
            "impact_wired": wired, "no_unit_no": no_num}


# ══════════════════ 생성·번호지정/변경·확정·취소 ══════════════════

def create_unit(pid, working_name=None, unit_no=None, equipment_type=None,
                actor_id=0, note=None, audit=None) -> int:
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
        if audit:                    # [v6 P0-03] 생성과 감사는 함께 남거나 함께 취소
            _a = dict(audit)
            _a["target"] = (_a.get("target") or "").replace("{unit_id}", str(uid))
            _audit_tx(c, _a)
        return uid


def change_unit_no(unit_id, new_unit_no, reason, actor_id=0, change_id=None,
                   effective_from=None, audit=None) -> bool:
    """호기번호 지정·변경 — **Unit id 는 유지**되고 이력이 남는다(적용시점 포함).
    확정(CONFIRMED) 호기는 영향 확인이 필요(V1 미연동이라 차단)."""
    new_no = _norm_unit_no(new_unit_no)
    if not new_no:
        raise ValueError("새 호기번호를 입력하세요.")
    if not (reason or "").strip():
        raise ValueError("호기번호를 정하거나 바꾸려면 사유를 입력하세요.")
    # [게이트 v6 P1-02] 적용시점 형식은 **DB 를 건드리기 전에** 해석·정규화하고 위반이면 거부한다.
    eff_in = norm_effective_from(effective_from)
    with db_session() as c:
        u = c.execute("SELECT * FROM project_units WHERE id=?", (unit_id,)).fetchone()
        if not u:
            raise ValueError("호기가 없습니다.")
        if u["unit_state"] == "CANCELLED":
            raise ValueError("취소된 호기는 변경할 수 없습니다.")
        now = _logi_now()
        eff = eff_in or now
        # ── [게이트 v5 P0-02] V1 은 **미래 적용 예약을 지원하지 않는다** ──────────
        #   예약일이 도래해도 current_unit_no 를 자동으로 바꿔주는 배치·스케줄러가 없어
        #   화면과 다른 모듈이 옛 번호를 계속 보게 된다(불완전 기능을 운영에 노출하지 않는다).
        #   → **즉시 변경 + 승인된 소급 정정만** 허용. 미래 Effectivity 는 WP-04 Change 승인·
        #     자동 활성화 구조와 함께 구현한다.
        if eff > now:
            raise ValueError(
                "미래 날짜로 호기번호를 예약할 수 없습니다. "
                "지금 적용하거나 지난 날짜로 정정하세요(미래 적용 예약은 다음 단계에서 제공).")
        # ── [게이트 v5 P0-01] 변경 '전' 값 = **적용시점 직전에 유효하던 번호** ────
        #   현재값(current_unit_no)을 쓰면 소급 정정이 '3호기→4호기'로 잘못 기록돼
        #   ECR/ECO 변경 근거가 왜곡된다. 5월 직전 실제 값은 2호기 → '2호기→4호기'가 맞다.
        old_no = _unit_no_at_tx(c, unit_id, eff)
        if old_no == new_no:
            return False
        if u["unit_state"] == "CONFIRMED":
            _require_impact_cleared(c, unit_id, "호기번호를 변경")
        if _unit_no_ever_used(c, u["project_id"], new_no, exclude_unit_id=unit_id):
            raise ValueError(f"이 관리번호에서 이미 사용된 호기번호입니다(취소분 포함): {new_no}")
        # ── [게이트 v4 P0-03] 적용기간(Effectivity) 규칙 ──────────────────────
        #   ① 적용시점 T 를 포함하는 기존 구간을 찾아 ② T 에서 종료하고
        #   ③ 새 구간은 T 에서 시작해 **다음 예정 변경시점**에서 끝난다(소급 입력이 미래 계획을 덮지 않음).
        #   ④ 같은 적용시점 중복 금지 ⑤ effective_to > effective_from 항상 보장.
        if c.execute("SELECT 1 FROM project_unit_identifier_history "
                     "WHERE project_unit_id=? AND effective_from=?", (unit_id, eff)).fetchone():
            raise ValueError(f"같은 적용시점({eff})의 변경이 이미 있습니다.")
        # ① T 를 포함하는 구간(시작<=T 이고 종료가 없거나 T 보다 뒤) → ② T 에서 종료
        c.execute("UPDATE project_unit_identifier_history SET effective_to=? "
                  "WHERE project_unit_id=? AND COALESCE(effective_from,'') <= ? "
                  "AND (effective_to IS NULL OR effective_to > ?)", (eff, unit_id, eff, eff))
        # ③ 새 구간의 종료 = T 이후 가장 이른 기존 적용시점(있으면). 없으면 열린 구간.
        nxt = c.execute("SELECT MIN(effective_from) FROM project_unit_identifier_history "
                        "WHERE project_unit_id=? AND effective_from > ?", (unit_id, eff)).fetchone()[0]
        c.execute(
            "INSERT INTO project_unit_identifier_history(project_unit_id, old_unit_no, new_unit_no, "
            "change_reason, changed_by, changed_at, change_id, effective_from, effective_to) "
            "VALUES(?,?,?,?,?,?,?,?,?)",
            (unit_id, old_no, new_no, reason.strip(), actor_id, now, change_id, eff, nxt))
        # ⑥ current_unit_no = **지금 이 시각에 유효한 값**(입력 순서의 마지막 값이 아님)
        c.execute("UPDATE project_units SET current_unit_no=?, updated_by=?, updated_at=? "
                  "WHERE id=?", (_unit_no_at_tx(c, unit_id, now), actor_id, now, unit_id))
        _audit_tx(c, audit)          # [v6 P0-03] 번호변경과 감사는 함께 남거나 함께 취소
    return True


def confirm_unit(unit_id, actor_id=0, audit=None) -> bool:
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
        _audit_tx(c, audit)          # [v6 P0-03] 확정과 감사는 함께 남거나 함께 취소
    return True


def cancel_unit(unit_id, reason, actor_id=0, audit=None) -> bool:
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
        _audit_tx(c, audit)          # [v6 P0-03] 취소와 감사는 함께 남거나 함께 취소
    return True


def audit_override(actor_id, actor_name, action, target, note):
    """권한 우회(시스템 관리자 복구) 감사 기록 — 사용자·시각·사유 (대표 확정 §3).
    ⛔ 조용히 삼키지 않는다: 표가 없으면 만들지 않고 예외를 올려 호출부가 알게 한다.
    ⚠ 업무 변경과 **같은 트랜잭션**이 필요한 경로는 이 함수를 쓰지 말고
       각 함수의 `audit=` 인자로 넘긴다(감사 실패 시 업무 변경도 취소돼야 하므로)."""
    with db_session() as c:
        _audit_tx(c, {"actor_id": actor_id, "actor_name": actor_name,
                      "action": action, "target": target, "note": note})


def get_audit(limit=50) -> list:
    with db_session() as c:
        if not c.execute("SELECT 1 FROM sqlite_master WHERE type='table' "
                         "AND name='project_unit_audit'").fetchone():
            return []
        return [dict(r) for r in c.execute(
            "SELECT * FROM project_unit_audit ORDER BY id DESC LIMIT ?", (limit,)).fetchall()]


def get_unit_relations(unit_id) -> list:
    """분할·통합 관계 이력 조회(읽기 전용). ⛔ V1: 생성·실행·승인 기능 없음(WP-04 이후)."""
    with db_session() as c:
        return [dict(r) for r in c.execute(
            "SELECT * FROM project_unit_relations WHERE source_unit_id=? OR result_unit_id=? "
            "ORDER BY id", (unit_id, unit_id)).fetchall()]
