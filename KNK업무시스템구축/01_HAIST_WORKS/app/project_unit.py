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

# ══ 작업일정표 상태 → 호기 상태 (게이트 판정 2026-07-26 §3 · **과거 데이터 보정 규칙**) ══
#   ⭐§4 두 상태는 의미가 다르므로 **따로** 보존한다. 하나로 합쳐 저장하지 않는다.
#      · 신원(unit_state)  = 이 장비가 몇 호기인지 확정됐는가
#      · 진행(work_status) = 장비가 지금 어느 단계인가
#   ⚠§5.2 이건 **이미 벌어진 일을 ERP 로 복원**하는 규칙이다. 정상 운영에서는 출하가
#         호기 신원을 자동 확정하지 않는다(생성→기술영업 지정·검토→승인권자 확정→생산·검사→출하).
#   ⛔§2.1 납품일이 지났다는 이유만으로 완료·확정 처리하지 않는다(지연·검사대기·보류·부분출하).
SCHEDULE_MAP = {
    "출하":   ("CONFIRMED",   "SHIPPED"),
    "진행중": ("PROVISIONAL", "IN_PROGRESS"),
    "보류":   ("PROVISIONAL", "ON_HOLD"),
    "취소":   ("CANCELLED",   "CANCELLED"),
}
SCHEDULE_UNSET = "(미지정)"      # 작업일정표에 상태가 비어 있음 — 확정하지 않고 진행중으로 둔다
WORK_LABEL = {"IN_PROGRESS": "진행중", "ON_HOLD": "보류", "SHIPPED": "출하", "CANCELLED": "취소"}
STATE_LABEL = {"PROVISIONAL": "개발·미확정", "CONFIRMED": "확정", "CANCELLED": "취소"}


def schedule_target(label):
    """작업일정표 표기 → (호기 신원, 업무 진행상태). 빈값·모르는 값은 **확정하지 않는다**."""
    return SCHEDULE_MAP.get((label or "").strip(), ("PROVISIONAL", "IN_PROGRESS"))


def schedule_label(label) -> str:
    """화면에 보여줄 작업일정표 표기 — 빈값도 색이 아니라 **글자로** 알린다(§8)."""
    return (label or "").strip() or SCHEDULE_UNSET


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
def _audit_tx(c, audit, change=None, change_label="상태"):
    """열린 트랜잭션 안에서 감사 1건 기록. audit=None 이면 아무것도 하지 않는다.

    [최종 실행 승인서 2026-07-26 §4.2] 감사기록의 **최소 요건**은
      "누가, 언제, 어떤 상태에서 어떤 상태로 변경했는지" 다.
      → `change=(전, 후)` 를 주면 그 변화를 note 에 함께 남긴다.
    ⛔ 호출부에서 change 를 빼먹으면 '무엇이 바뀌었는지 모르는 기록'이 된다."""
    if not audit:
        return
    note = audit.get("note") or ""
    if change:
        note = (note + " · %s %s → %s" % (change_label, change[0] or "(없음)",
                                          change[1] or "(없음)")).strip(" ·").strip()
    c.execute(
        "INSERT INTO project_unit_audit(actor_id, actor_name, action, target, note, created_at) "
        "VALUES(?,?,?,?,?,?)",
        (audit.get("actor_id") or 0, audit.get("actor_name") or "", audit.get("action") or "",
         audit.get("target") or "", note, _logi_now()))


def _state_ko(code):
    """감사기록도 사람이 읽는다 — '확정(CONFIRMED)' 처럼 쉬운 말과 코드를 함께 남긴다."""
    if not code:
        return ""
    return "%s(%s)" % (STATE_LABEL.get(code, code), code)


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
        "o.order_no AS ono, oi.unit_status AS ust, "
        # 발주일·납기·납품처 빈 칸은 수주번호 부모값을 상속한다(수주 화면 규칙과 동일)
        "COALESCE(NULLIF(oi.due_date,''), o.due_date) AS due "
        "FROM order_items oi JOIN orders o ON o.id=oi.order_id "
        "WHERE o.project_id=? "
        "ORDER BY o.order_date ASC, o.id ASC, oi.id ASC", (pid,)).fetchall()
    return [r for r in rows if HOGI_RE.match((r["lbl"] or ""))]


def _cancelled_nonhogi_rows(c, pid):
    """[§3.4 둘째 갈래] **취소**인데 호기로 식별되지 않는 줄(단순 계획행).
    → 새 호기를 만들지 않되, **아무 기록 없이 사라지게 두지 않는다**(제외 사유를 남긴다)."""
    rows = c.execute(
        "SELECT oi.id AS oid, oi.unit_label AS lbl, oi.order_id AS ord, "
        "o.order_no AS ono, oi.unit_status AS ust "
        "FROM order_items oi JOIN orders o ON o.id=oi.order_id "
        "WHERE o.project_id=? AND TRIM(COALESCE(oi.unit_status,''))='취소' "
        "ORDER BY o.id, oi.id", (pid,)).fetchall()
    return [r for r in rows if not HOGI_RE.match((r["lbl"] or ""))]


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
            # [§8] 담당자가 판단할 수 있게 **작업일정표 상태·납품예정일·반영 예정 결과**를 함께 준다.
            _sched = schedule_label(r["ust"])
            _st, _wk = schedule_target(r["ust"])
            cands.append({
                "order_item_id": r["oid"], "order_id": r["ord"], "order_no": r["ono"],
                "label": lbl, "unit_no_hint": no, "qty": r["qty"],
                "schedule_label": _sched, "due_date": r["due"],
                "planned_state": _st, "planned_work": _wk,
                "planned_state_label": STATE_LABEL.get(_st, _st),
                "planned_work_label": WORK_LABEL.get(_wk, _wk),
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
        # [§3.4] 취소인데 호기로 식별되지 않는 줄 — 만들지 않되 **사유와 함께 보여준다**
        excluded = [{"order_item_id": r["oid"], "order_no": r["ono"], "label": r["lbl"],
                     "schedule_label": schedule_label(r["ust"]),
                     "skip_reason": "작업일정표 취소 · 호기로 식별되지 않는 줄"}
                    for r in _cancelled_nonhogi_rows(c, pid)]
    s = {"total": len(cands), "excluded": len(excluded),
         "new": sum(1 for x in cands if x["suggestion"] == CAND_NEW),
         "link": sum(1 for x in cands if x["suggestion"] == CAND_LINK),
         "already_linked": sum(1 for x in cands if x["suggestion"] == CAND_ALREADY),
         "blocked": sum(1 for x in cands if x["suggestion"] == CAND_BLOCKED)}
    return {"ready": True, "candidates": cands, "summary": s, "units": units,
            "excluded": excluded}


def apply_candidate_decisions(pid, decisions, reason, actor_id=0, audit=None,
                              allow_confirm=False) -> dict:
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
            # 작업일정표가 '출하'·'취소'인 줄은 결과가 **확정·취소**다 → 승인권자만 반영할 수 있다.
            #   (권한 없는 사람이 후보 반영으로 확정을 우회하지 못하게)
            if (not allow_confirm) and cd.get("planned_state") in ("CONFIRMED", "CANCELLED"):
                rejected.append((oid, f"작업일정표 '{cd.get('schedule_label')}' 은 "
                                      f"{STATE_LABEL.get(cd.get('planned_state'))} 처리라 "
                                      "승인권자(기술영업팀장·대표·임원)만 반영할 수 있습니다."))
                continue
            if d["action"] in ("new", "new_no"):
                # 'new_no' 만 표기를 호기번호로 승격한다(사용자가 명시 선택한 경우).
                unit_no = _norm_unit_no(cd["label"]) if d["action"] == "new_no" else None
                if unit_no and _unit_no_ever_used(c, pid, unit_no):
                    # [F-06] 취소분·과거 이력 포함 재사용 금지 — 조용히 넘기지 않고 사유를 알린다.
                    rejected.append((oid, f"이 관리번호에서 이미 쓴 호기번호입니다(취소분 포함): {unit_no}"))
                    continue
                # [게이트 §3] 작업일정표 상태를 **신원·진행 두 칸에 나눠** 반영한다.
                #   출하 → 확정 + SHIPPED / 진행중 → 개발·미확정 + IN_PROGRESS
                #   보류 → 개발·미확정 + ON_HOLD / 취소 → 취소 + CANCELLED
                _st, _wk = schedule_target(cd.get("schedule_label"))
                _now0 = _logi_now()
                cur = c.execute(
                    "INSERT INTO project_units(project_id, working_name, current_unit_no, "
                    "unit_state, entity, seed_order_item_id, seed_order_no, seed_unit_label, "
                    "note, created_by, created_at, updated_by, updated_at, "
                    "work_status, work_status_src, work_status_label, work_status_at) "
                    "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (pid, cd["label"], unit_no, _st, entity, oid, cd["order_no"], cd["label"],
                     reason.strip(), actor_id, _now0, actor_id, _now0,
                     _wk, "작업일정표", cd.get("schedule_label"), _now0))
                uid = cur.lastrowid
                if _st == "CONFIRMED":
                    c.execute("UPDATE project_units SET confirmed_by=?, confirmed_at=? WHERE id=?",
                              (actor_id, _now0, uid))
                elif _st == "CANCELLED":
                    c.execute("UPDATE project_units SET cancelled_by=?, cancelled_at=?, "
                              "cancellation_reason=? WHERE id=?",
                              (actor_id, _now0, f"작업일정표 취소 — {reason.strip()}", uid))
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


def _decorate_status(u: dict):
    """[§8] 화면에 색만이 아니라 **상태 문구**를 함께 보여주기 위한 라벨."""
    _wk = u.get("work_status") or "IN_PROGRESS"
    u["work_status"] = _wk
    u["work_status_text"] = WORK_LABEL.get(_wk, _wk)
    u["unit_state_text"] = STATE_LABEL.get(u.get("unit_state"), u.get("unit_state"))
    return u


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
            _decorate_status(u)          # [§8] 신원·진행상태를 **글자로** 함께 내려준다
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
        _decorate_status(u)
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
        # [§3.1] 출하된 호기는 진행중 호기와 **구분해서** 보여준다(신원 상태와 별개)
        try:
            wk = {r[0]: r[1] for r in c.execute(
                "SELECT COALESCE(work_status,'IN_PROGRESS'), COUNT(*) FROM project_units "
                "WHERE project_id=? GROUP BY 1", (pid,)).fetchall()}
        except sqlite3.OperationalError:
            wk = {}                       # z1054 마이그레이션 전이면 표시만 생략(기능 영향 없음)
    return {"ready": True, "units": sum(st.values()),
            "provisional": st.get("PROVISIONAL", 0), "confirmed": st.get("CONFIRMED", 0),
            "cancelled": st.get("CANCELLED", 0), "candidates": cands,
            "candidates_total": len(_rows), "candidates_done": len(_rows) - cands,
            "shipped": wk.get("SHIPPED", 0), "on_hold": wk.get("ON_HOLD", 0),
            "in_progress": wk.get("IN_PROGRESS", 0), "work_cancelled": wk.get("CANCELLED", 0),
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
            _audit_tx(c, _a, change=("", _state_ko("PROVISIONAL")))
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
        # [승인서 §4.2] 무엇이 무엇으로 바뀌었는지 — 적용시점까지 함께 남긴다
        _audit_tx(c, audit, change=(old_no, "%s (적용 %s)" % (new_no, eff)),
                  change_label="호기번호")   # [v6 P0-03] 번호변경과 감사는 함께 남거나 함께 취소
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
        # [승인서 §4.2] **정상 확정도** 어떤 상태에서 어떤 상태로 바뀌었는지 남긴다
        _audit_tx(c, audit, change=(_state_ko(u["unit_state"]), _state_ko("CONFIRMED")))
    return True                      # [v6 P0-03] 확정과 감사는 함께 남거나 함께 취소


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
        _audit_tx(c, audit, change=(_state_ko(u["unit_state"]), _state_ko("CANCELLED")))
    return True                      # [v6 P0-03] 취소와 감사는 함께 남거나 함께 취소


# ══════════ 과거 데이터 보정 — 작업일정표 상태 대조 (게이트 판정 §9) ══════════

def _backfill_rows(c, pid):
    """이미 만든 호기를 **원본 작업일정표 상태와 호기별로 다시 대조**한다(읽기 전용).
    [§10-9] 원본과 기존 ERP 상태가 **충돌**하면 덮어쓰지 않고 예외로 표시한다."""
    pr = c.execute("SELECT mgmt_code FROM projects WHERE id=?", (pid,)).fetchone()
    mgmt = (pr["mgmt_code"] if pr else "") or ""
    src = {r["oid"]: r for r in _hogi_candidate_rows(c, pid)}
    out = []
    for u in c.execute("SELECT * FROM project_units WHERE project_id=? ORDER BY id",
                       (pid,)).fetchall():
        u = dict(u)
        r = src.get(u.get("seed_order_item_id"))
        sched = schedule_label(r["ust"]) if r else None
        cur_state = u.get("unit_state")
        cur_work = u.get("work_status") or "IN_PROGRESS"
        # [게이트 §3 제출표] 연결된 수주번호는 **여럿이면 전부** 보인다
        links = [dict(x) for x in c.execute(
            "SELECT order_no, relation_type, active FROM project_unit_order_links "
            "WHERE project_unit_id=? ORDER BY id", (u["id"],)).fetchall()]
        row = {
            "unit_id": u["id"], "mgmt_code": mgmt, "entity": u.get("entity"),
            "order_no": u.get("seed_order_no"), "unit_no": u.get("current_unit_no"),
            "order_nos": ", ".join(x["order_no"] or "?" for x in links if x["active"]) or "—",
            "working_name": u.get("working_name"),
            "due_date": (r["due"] if r else None),
            # [§1.2] 실제 출하일 — 모르면 **미확인**. 납품 예정일·보정일로 지어내지 않는다.
            "shipped_on": u.get("shipped_on"),
            "confirmed_by": u.get("confirmed_by"), "confirmed_at": u.get("confirmed_at"),
            # [§4] 이미 확정된 호기의 **확정 근거**. 감사기록이 없으면 추정하지 않고 그렇다고 적는다.
            "confirm_audit": [dict(x) for x in c.execute(
                "SELECT actor_id, actor_name, action, note, created_at FROM project_unit_audit "
                "WHERE target LIKE ? ORDER BY id", (f"%unit#{u['id']}",)).fetchall()]
            if u.get("unit_state") == "CONFIRMED" else [],
            "source": ("작업일정표" if r else "직접 생성(수주내역 연결 없음)"),
            "schedule_label": sched,
            "before_state": cur_state, "before_work": cur_work,
            "before_state_label": STATE_LABEL.get(cur_state, cur_state),
            "before_work_label": WORK_LABEL.get(cur_work, cur_work),
            "after_state": cur_state, "after_work": cur_work,
            "change": False, "conflict": None, "fields": [],
        }
        if not r:
            # 수주내역에 근거가 없는 호기(직접 만든 개발호기) — 보정 대상이 아니다.
            row["conflict"] = "수주내역 근거 없음 — 보정하지 않음"
        else:
            t_state, t_work = schedule_target(r["ust"])
            # ⛔ 되돌리는 보정은 하지 않는다: 확정→미확정, 취소→부활은 사람이 판단할 일.
            if cur_state == "CANCELLED" and t_state != "CANCELLED":
                row["conflict"] = f"이미 취소된 호기인데 작업일정표는 '{sched}' — 덮어쓰지 않음"
            elif cur_state == "CONFIRMED" and t_state == "PROVISIONAL":
                row["conflict"] = f"이미 확정된 호기인데 작업일정표는 '{sched}' — 되돌리지 않음"
            elif t_state == "CONFIRMED" and not (u.get("current_unit_no") or "").strip():
                row["conflict"] = "호기번호가 없어 확정할 수 없음 — 번호를 먼저 정하세요"
            else:
                row["after_state"], row["after_work"] = t_state, t_work
                row["change"] = (t_state != cur_state) or (t_work != cur_work)
                # [§3 제출표] 이번 작업에서 **실제로 바뀌는 필드**만 열거한다.
                f = []
                if t_state != cur_state:
                    f.append("unit_state")
                    # ⭐[§1.1] 이미 확정인 호기는 **다시 확정하지 않는다** —
                    #   확정자·확정시각·확정사유를 덮어쓰지 않고 그대로 둔다.
                    if t_state == "CONFIRMED":
                        f += ["confirmed_by", "confirmed_at"]
                    elif t_state == "CANCELLED":
                        f += ["cancelled_by", "cancelled_at", "cancellation_reason"]
                if t_work != cur_work:
                    f += ["work_status", "work_status_src", "work_status_label", "work_status_at"]
                f += ["updated_by", "updated_at"]
                row["fields"] = f
        row["after_state_label"] = STATE_LABEL.get(row["after_state"], row["after_state"])
        row["after_work_label"] = WORK_LABEL.get(row["after_work"], row["after_work"])
        row["action"] = ("변경" if row["change"] else ("예외" if row["conflict"] else "유지"))
        out.append(row)
    return out


def status_backfill_preview(pid) -> dict:
    """[§9-2] 반영 **전 상태와 반영 예정 상태**를 표로 제출한다(실행하지 않음)."""
    with db_session() as c:
        if not _table_ready(c):
            return {"ready": False, "rows": [], "summary": {}}
        rows = _backfill_rows(c, pid)
    s = {"total": len(rows),
         "change": sum(1 for x in rows if x["change"]),
         "conflict": sum(1 for x in rows if x["conflict"]),
         "to_confirmed": sum(1 for x in rows if x["change"] and x["after_state"] == "CONFIRMED"),
         "to_cancelled": sum(1 for x in rows if x["change"] and x["after_state"] == "CANCELLED"),
         "keep": sum(1 for x in rows if not x["change"] and not x["conflict"])}
    return {"ready": True, "rows": rows, "summary": s}


def status_backfill_apply(pid, reason, actor_id=0, audit=None) -> dict:
    """[§9] 대조 결과대로 보정한다. **바뀌는 것만** 손대고 원본 상태·근거를 이력에 남긴다.
    [§9-8] 같은 보정을 다시 실행해도 중복 생성·이력 중복이 생기지 않는다(바뀐 게 없으면 무동작).
    [§10-8] 감사기록이 실패하면 보정 전체가 함께 취소된다(단일 트랜잭션)."""
    if not (reason or "").strip():
        raise ValueError("보정 사유를 입력하세요.")
    changed, skipped = [], []
    with db_session() as c:
        if not _table_ready(c):
            raise ValueError("호기 기능이 아직 준비되지 않았습니다.")
        now = _logi_now()
        for row in _backfill_rows(c, pid):
            if row["conflict"]:
                skipped.append((row["unit_id"], row["conflict"]))
                continue
            if not row["change"]:
                continue
            uid = row["unit_id"]
            c.execute("UPDATE project_units SET unit_state=?, work_status=?, "
                      "work_status_src='작업일정표', work_status_label=?, work_status_at=?, "
                      "updated_by=?, updated_at=? WHERE id=?",
                      (row["after_state"], row["after_work"], row["schedule_label"], now,
                       actor_id, now, uid))
            # ⭐[§1.1] **이미 확정인 호기는 다시 확정하지 않는다** — 기존 확정자·확정시각·확정사유를
            #   덮어쓰면 "누가 언제 확정했나"가 이번 보정으로 바뀌어 버린다(중복 확정·이력 훼손 금지).
            #   신원이 실제로 바뀔 때만 확정/취소 정보를 채운다.
            if row["after_state"] == "CONFIRMED" and row["before_state"] != "CONFIRMED":
                c.execute("UPDATE project_units SET confirmed_by=?, confirmed_at=? WHERE id=?",
                          (actor_id, now, uid))
            elif row["after_state"] == "CANCELLED" and row["before_state"] != "CANCELLED":
                c.execute("UPDATE project_units SET cancelled_by=?, cancelled_at=?, "
                          "cancellation_reason=? WHERE id=?",
                          (actor_id, now, f"작업일정표 취소 — {reason.strip()}", uid))
                c.execute("UPDATE project_unit_order_links SET active=0, unlinked_by=?, "
                          "unlinked_at=? WHERE project_unit_id=? AND active=1", (actor_id, now, uid))
            c.execute(
                "INSERT INTO project_unit_status_backfill(project_unit_id, project_id, "
                "order_item_id, source_label, old_unit_state, new_unit_state, old_work_status, "
                "new_work_status, reason, actor_id, created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                (uid, pid, None, row["schedule_label"], row["before_state"], row["after_state"],
                 row["before_work"], row["after_work"], reason.strip(), actor_id, now))
            changed.append(uid)
        # [§3.4] 취소인데 호기로 식별 안 되는 줄 — 제외 사유를 남긴다(중복 기록 안 함)
        for r in _cancelled_nonhogi_rows(c, pid):
            c.execute(
                "INSERT OR IGNORE INTO project_unit_candidate_skips(project_id, order_item_id, "
                "order_no, unit_label, source_label, skip_reason, actor_id, created_at) "
                "VALUES(?,?,?,?,?,?,?,?)",
                (pid, r["oid"], r["ono"], r["lbl"], schedule_label(r["ust"]),
                 "작업일정표 취소 · 호기로 식별되지 않는 줄", actor_id, now))
        if audit:
            # [승인서 §4.1] 과거 데이터 보정의 감사 근거 — 근거·대상·실제 출하일까지 사실대로.
            #   ⛔ 실제 출하일은 이 함수가 **아무것도 쓰지 않는다**(모르면 미확인으로 둔다).
            _a = dict(audit)
            _a["note"] = (f"{_a.get('note') or ''} — 근거: 작업일정표 원본 상태 · "
                          f"보정 {len(changed)}대 · 예외 {len(skipped)}건 · "
                          f"실제 출하일 미확인(저장하지 않음)").strip()
            _audit_tx(c, _a)
    return {"changed": len(changed), "changed_ids": changed,
            "skipped": len(skipped), "skipped_detail": skipped}


def get_status_backfill_log(pid, limit=200) -> list:
    with db_session() as c:
        if not c.execute("SELECT 1 FROM sqlite_master WHERE type='table' "
                         "AND name='project_unit_status_backfill'").fetchone():
            return []
        return [dict(r) for r in c.execute(
            "SELECT * FROM project_unit_status_backfill WHERE project_id=? "
            "ORDER BY id DESC LIMIT ?", (pid, limit)).fetchall()]


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
