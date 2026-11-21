# -*- coding: utf-8 -*-
"""👔 사내 보낸 사람 — 2026-11-21 대표 「신입사원 관점」 다 묶음(6-1 · 3-2 · 6-2).

- 6-1 사내 주소로 온 메일은 보낸 사람을 직원 명부 「이름 직책 부서」로(이름 표시 규칙 · vname_full 과 같은 꼴)
- 3-2 그 사람이 나보다 윗분이면 「👔」 꼬리표 — 임원 · 우리 팀장 · 우리 팀 윗 직책
- 6-2 이 메일에서 나는 받는 사람인가 · 참조인가 · 숨은참조인가
읽기만 · AI 안 씀 · 직원 명부(users·teams)만 봄 · 이음 대화방은 보지 않음.
"""
import re

OUR_DOMAINS = ("knknara.co.kr",)
_RE_EMAIL = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")

# 직책 높낮이(클수록 윗분) — 표에 없는 직책(프로·매니저·연구원 등)은 「모름」(None) → 직책으로는 가르지 않음
RANK_LEVEL = {
    "대표이사": 100, "대표": 100, "사장": 95, "부사장": 92, "법인장": 88,
    "전무이사": 85, "전무": 85, "상무이사": 80, "상무": 80, "이사": 75,
    "부장": 60, "차장": 50, "과장": 40, "대리": 30, "주임": 20, "사원": 10,
}
EXEC_LEVEL = 75            # 이사 이상 = 임원
_ROLE_LEVEL = {"ceo": 100, "executive": EXEC_LEVEL}


def is_internal(addr: str) -> bool:
    a = (addr or "").strip().lower()
    return "@" in a and a.rsplit("@", 1)[-1] in OUR_DOMAINS


def rank_level(rank: str, role: str = ""):
    """직책 → 높낮이. 「과장(팀장)」처럼 겹친 꼴은 앞 직책. 역할이 대표·임원이면 그 높이 이상."""
    r = re.sub(r"\(.*?\)", "", (rank or "")).strip()
    lv = RANK_LEVEL.get(r)
    rl = _ROLE_LEVEL.get((role or "").strip().lower())
    if rl is not None:
        lv = max(lv or 0, rl)
    return lv


def staff(c) -> dict:
    """사내 주소 → 직원. {주소: {"id","name","name_vi","rank","role","team_id","team_name","leader"}}.
    재직 중인 직원만 · 한 주소를 두 사람이 쓰면 그 주소는 뺀다(잘못 붙이지 않게)."""
    rows = []
    try:
        cols = {r[1] for r in c.execute("PRAGMA table_info(users)").fetchall()}
        sel = ["u.id", "u.name", "COALESCE(u.rank,'') AS rank", "COALESCE(u.role,'') AS role", "u.team_id",
               "COALESCE(t.name,'') AS team_name", "t.leader_id AS leader", "COALESCE(u.email,'') AS email",
               "COALESCE(u.login_id,'') AS login_id"]
        sel.append("COALESCE(u.name_vi,'') AS name_vi" if "name_vi" in cols else "'' AS name_vi")
        where = "WHERE COALESCE(u.is_active,1)=1" if "is_active" in cols else ""
        rows = c.execute("SELECT " + ", ".join(sel) + " FROM users u LEFT JOIN teams t ON t.id=u.team_id " + where).fetchall()
    except Exception as e:
        print("[MAIL-PEOPLE] 직원 명부 읽기 실패: %s" % str(e)[:160], flush=True)
        return {}
    out, dup = {}, set()
    for r in rows:
        d = dict(r)
        addrs = set(a.lower() for a in _RE_EMAIL.findall(d.get("email") or "") if is_internal(a))
        lid = (d.get("login_id") or "").strip().lower()
        if lid and re.match(r"^[a-z][a-z0-9._\-]*$", lid):
            addrs.add(lid + "@" + OUR_DOMAINS[0])
        for a in addrs:
            if a in out and out[a]["id"] != d["id"]:
                dup.add(a)
            out[a] = d
    for a in dup:
        out.pop(a, None)
    return out


def disp(p: dict) -> str:
    """「이름 직책 부서」 — 베트남 직원은 베트남어 이름(한국 발음)."""
    nm = (p.get("name") or "").strip()
    nv = (p.get("name_vi") or "").strip()
    if nv and nv != nm:
        nm = "%s (%s)" % (nv, nm) if nm else nv
    return " ".join(x for x in (nm, (p.get("rank") or "").strip(), (p.get("team_name") or "").strip()) if x)


def boss_why(me: dict, s: dict) -> str:
    """보낸 사람 s 가 나(me)보다 윗분이면 까닭(「대표」·「임원」·「우리 팀장」·「우리 팀 윗 직책」), 아니면 ""."""
    if not me or not s or s.get("id") == me.get("id"):
        return ""
    sl = rank_level(s.get("rank"), s.get("role"))
    ml = rank_level(me.get("rank"), me.get("role"))
    if sl is not None and sl >= EXEC_LEVEL and sl > (ml or 0):
        return "대표" if sl >= 100 else "임원"
    if me.get("team_id") and s.get("id") == me.get("leader") and me.get("leader") != me.get("id"):
        return "우리 팀장"
    if me.get("team_id") and s.get("team_id") == me.get("team_id") and sl is not None and ml is not None and sl > ml:
        return "우리 팀 윗 직책"
    return ""


def me_of(c, uid, st: dict = None) -> dict:
    """나(보는 사람) — 직원 명부에서."""
    st = st if st is not None else staff(c)
    for p in st.values():
        if p.get("id") == uid:
            return p
    try:
        r = c.execute("SELECT u.id, COALESCE(u.rank,'') AS rank, COALESCE(u.role,'') AS role, u.team_id, "
                      "t.leader_id AS leader FROM users u LEFT JOIN teams t ON t.id=u.team_id WHERE u.id=?", (uid,)).fetchone()
        return dict(r) if r else {"id": uid}
    except Exception:
        return {"id": uid}


def sender(st: dict, me: dict, from_email: str) -> dict:
    """보낸 사람 → {"disp": 「이름 직책 부서」, "boss": 까닭} · 사내 직원이 아니면 {}."""
    a = (from_email or "").strip().lower()
    p = st.get(a) if is_internal(a) else None
    if not p:
        return {}
    return {"disp": disp(p), "boss": boss_why(me, p), "uid": p.get("id")}


def my_role(m: dict, mine: set) -> str:
    """이 메일에서 나는 — "to"(받는 사람) · "cc"(참조) · "bcc"(받는 사람·참조에 내 주소가 없음 = 숨은참조·그룹 주소 등) · ""(보낸 메일·모름)."""
    if not mine or (m.get("direction") or "in") != "in":
        return ""
    to = set(x.lower() for x in _RE_EMAIL.findall((m.get("to_all") or "") + " " + (m.get("to_email") or "")))
    if to & mine:
        return "to"
    cc = set(x.lower() for x in _RE_EMAIL.findall(m.get("cc") or ""))
    if cc & mine:
        return "cc"
    return "bcc" if (to or cc) else ""
