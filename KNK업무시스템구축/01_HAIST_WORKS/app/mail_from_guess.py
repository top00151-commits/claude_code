# -*- coding: utf-8 -*-
"""보낸 사람 주소를 모르는 메일 — 우리 자료 안에서 주소 찾기 (대표 2026-11-22 「④랑 ③ 숫자 세기부터 진행해」)

까닭: 예전에 받은 메일 중 보낸 사람 주소 칸이 비었거나(252) 이름만 든(59) 메일 — 하이웍스 원본(POP3 최근 몇백 통)에 닿지 않음.
→ 바깥으로 아무것도 보내지 않고, 서버 안 자료만으로 후보 주소를 찾는다.

근거(메일마다):
  원문   = 서버에 남긴 원문 머리글(11-22 부터 받는 메일 · 정확)
  이름   = 같은 이름이 **내 다른 메일**에서 주소와 함께 온 적(보낸 사람 · 받는 사람 · 참조 줄)
  직원   = 사내 직원 명단의 같은 이름
  주소록 = 내가 볼 수 있는 주소록(공유 연락처)의 같은 이름
  답장   = 내가 그 메일(같은 제목)에 답장한 보낸 메일의 받는 사람(한 명일 때)
  서명   = 그 메일 본문(인용 앞)의 서명에 적힌 주소(우리 회사·받는 사람 주소 빼고 하나일 때)
판정: 하나뿐인 근거들이 모두 같은 주소 = 「하나로 모임」 · 서로 다름/여럿 = 「여러 후보」 · 없음 = 「못 찾음」.
⚠ 지금은 **숫자만** 센다(자료 안 바꿈 · 주소·이름을 돌려주지 않음). 채우기는 대표 확인 뒤 따로.
"""
import re
from datetime import datetime, timedelta

_RE_EMAIL = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
# 본문에서 인용(앞 메일)이 시작되는 표시 — 그 앞까지만 「이 사람의 서명」으로 본다
_RE_QUOTE = re.compile(r"(?im)^\s*(?:-{2,}\s*(?:original message|원본 메시지|원본 메일|forwarded message)[^\n]*"
                       r"|>|from\s*:|보낸\s*사람\s*:|보낸사람\s*:|sent\s*:|on .{4,80} wrote:|.{0,60}님이 작성:)")
SRC = ("원문", "이름", "직원", "주소록", "답장", "서명")
REPLY_DAYS = 60


def _nk(name: str) -> str:
    """이름 맞추기 열쇠 — 따옴표·띄어쓰기·대소문자 무시."""
    s = re.sub(r"[\"'`<>]", " ", name or "")
    s = re.sub(r"\s+", " ", s).strip().lower()
    return s


def _core(name: str) -> str:
    """「이상우 (드림텍 구매팀)」·「이상우/드림텍」 → 「이상우」."""
    s = re.split(r"[(\[/|,]", name or "", 1)[0]
    return _nk(s)


def _ok_key(k: str) -> bool:
    return len(k.replace(" ", "")) >= 2


def _own_addrs(c, uid) -> set:
    out = set()
    try:
        r = c.execute("SELECT COALESCE(email,'') AS e, COALESCE(login_id,'') AS l FROM users WHERE id=?", (int(uid),)).fetchone()
        if r:
            out |= {a.lower() for a in _RE_EMAIL.findall(r["e"] or "")}
    except Exception:
        pass
    try:
        for r in c.execute("SELECT DISTINCT lower(to_email) AS t FROM mail_messages WHERE user_id=? AND direction='in' "
                           "AND COALESCE(to_email,'') LIKE '%@%' LIMIT 50", (int(uid),)).fetchall():
            if r["t"]:
                out.add(r["t"])
    except Exception:
        pass
    return out


def _add(mp: dict, key: str, addr: str):
    if key and _ok_key(key) and addr:
        mp.setdefault(key, set()).add(addr.lower())


def build_index(c, uid, user=None) -> dict:
    """이름 → 주소 모음(근거별)."""
    from .mail_people import split_addrs, staff, OUR_DOMAINS
    mine = _own_addrs(c, uid)
    nm, nm_core = {}, {}
    for r in c.execute("SELECT COALESCE(from_name,'') AS n, lower(COALESCE(from_email,'')) AS e, "
                       "COALESCE(to_all,'') AS ta, COALESCE(cc,'') AS cc FROM mail_messages "
                       "WHERE user_id=? AND direction='in' AND is_deleted=0", (int(uid),)).fetchall():
        e = r["e"]
        if e and _RE_EMAIL.fullmatch(e) and r["n"]:
            _add(nm, _nk(r["n"]), e)
            _add(nm_core, _core(r["n"]), e)
        for n2, a2 in split_addrs((r["ta"] or "") + ", " + (r["cc"] or "")):
            if n2 and a2 and a2 not in mine:
                _add(nm, _nk(n2), a2)
                _add(nm_core, _core(n2), a2)
    st_nm = {}
    try:
        for a, p in staff(c).items():
            _add(st_nm, _nk(p.get("name") or ""), a)
            if p.get("name_vi"):
                _add(st_nm, _nk(p.get("name_vi")), a)
    except Exception:
        pass
    ct_nm = {}
    try:
        from .contacts import _vis_clause
        vsql, vp = _vis_clause(user) if user else ("", [])
        q = "SELECT COALESCE(sc.name,'') AS n, COALESCE(sc.email,'') AS e FROM shared_contacts sc"
        if vsql:
            q += " WHERE " + vsql
        for r in c.execute(q, vp).fetchall():
            for a in _RE_EMAIL.findall(r["e"] or ""):
                _add(ct_nm, _nk(r["n"]), a)
                _add(ct_nm, _core(r["n"]), a)
    except Exception:
        pass
    sent = []
    try:
        from .mail_store import _normalize_subject
        for r in c.execute("SELECT subject, COALESCE(to_email,'') AS t, COALESCE(received_at, created_at) AS at "
                           "FROM mail_messages WHERE user_id=? AND direction='out' AND is_deleted=0", (int(uid),)).fetchall():
            sent.append((_normalize_subject(r["subject"] or ""), r["t"] or "", r["at"] or ""))
    except Exception:
        pass
    by_subj = {}
    for sj, t, at in sent:
        by_subj.setdefault(sj, []).append((t, at))
    return {"nm": nm, "nm_core": nm_core, "staff": st_nm, "contacts": ct_nm, "sent": by_subj,
            "mine": mine, "ours": tuple(OUR_DOMAINS)}


def _dt(s):
    try:
        return datetime.strptime((s or "")[:19], "%Y-%m-%d %H:%M:%S")
    except Exception:
        return None


def _sig_addrs(body: str, exclude: set, ours: tuple) -> set:
    b = body or ""
    m = _RE_QUOTE.search(b)
    if m:
        b = b[:m.start()]
    out = set()
    for a in _RE_EMAIL.findall(b):
        a = a.lower().strip(".")
        if a in exclude or a.rsplit("@", 1)[-1] in ours:
            continue
        if a.startswith(("noreply", "no-reply", "mailer-daemon", "postmaster")):
            continue
        out.add(a)
    return out


def guess_one(c, m: dict, ix: dict) -> dict:
    """메일 한 통 → {근거: 주소 모음}."""
    from .mail_store import _normalize_subject, reparse_from
    from .mail_people import split_addrs
    name = (m.get("from_name") or "").strip()
    fe = (m.get("from_email") or "").strip()
    if not name and fe and "@" not in fe:
        name = fe                              # 예전엔 이름이 주소 칸에 들어감
    src = {}
    try:
        rp = reparse_from(c, m["id"])
        if rp and rp[1] and "@" in rp[1]:
            src["원문"] = {rp[1].lower()}
    except Exception:
        pass
    k, kc = _nk(name), _core(name)
    if _ok_key(k):
        s = ix["nm"].get(k) or (ix["nm_core"].get(kc) if _ok_key(kc) else None)
        if s:
            src["이름"] = set(s)
        s = ix["staff"].get(k) or (ix["staff"].get(kc) if _ok_key(kc) else None)
        if s:
            src["직원"] = set(s)
        s = ix["contacts"].get(k) or (ix["contacts"].get(kc) if _ok_key(kc) else None)
        if s:
            src["주소록"] = set(s)
    rcv = _dt(m.get("received_at"))
    rep = set()
    for t, at in ix["sent"].get(_normalize_subject(m.get("subject") or ""), []):
        sd = _dt(at)
        if rcv and sd and not (rcv <= sd <= rcv + timedelta(days=REPLY_DAYS)):
            continue
        tos = [a.strip().lower() for a in (t or "").split(",") if "@" in a]
        tos = [a for a in tos if a not in ix["mine"]]
        if len(tos) == 1:
            rep.add(tos[0])
    if rep:
        src["답장"] = rep
    excl = set(ix["mine"])
    for _n, a in split_addrs((m.get("to_all") or "") + ", " + (m.get("cc") or "")):
        excl.add(a)
    sg = _sig_addrs(m.get("body_text") or "", excl, ix["ours"])
    if sg:
        src["서명"] = sg
    return src


def verdict(src: dict) -> tuple:
    """(판정, 하나로 모인 주소 또는 '') — 판정 = one|many|none."""
    if "원문" in src and len(src["원문"]) == 1:
        return "one", next(iter(src["원문"]))
    single = {next(iter(v)) for v in src.values() if len(v) == 1}
    if len(single) == 1:
        return "one", next(iter(single))
    if single or any(len(v) > 1 for v in src.values()):
        return "many", ""
    return "none", ""


def targets(c, uid) -> list:
    return [dict(r) for r in c.execute(
        "SELECT id, COALESCE(from_name,'') AS from_name, COALESCE(from_email,'') AS from_email, subject, "
        "COALESCE(to_all,'') AS to_all, COALESCE(cc,'') AS cc, body_text, received_at FROM mail_messages "
        "WHERE user_id=? AND direction='in' AND is_deleted=0 "
        "AND (COALESCE(from_email,'')='' OR instr(from_email,'@')=0) ORDER BY id", (int(uid),)).fetchall()]


def count(c, uid, user=None) -> dict:
    """숫자만 — 주소·이름은 돌려주지 않는다."""
    rows = targets(c, uid)
    ix = build_index(c, uid, user)
    out = {"total": len(rows), "empty": 0, "name_only": 0, "no_name": 0,
           "one": 0, "one_2plus": 0, "many": 0, "none": 0,
           "by_src": {s: 0 for s in SRC}, "one_by_src": {s: 0 for s in SRC},
           "by_year": {}, "recent7_missing": 0}
    for m in rows:
        fe = (m.get("from_email") or "").strip()
        if not fe:
            out["empty"] += 1
        else:
            out["name_only"] += 1
        if not (m.get("from_name") or "").strip() and not fe:
            out["no_name"] += 1
        y = (m.get("received_at") or "")[:4] or "?"
        out["by_year"][y] = out["by_year"].get(y, 0) + 1
        src = guess_one(c, m, ix)
        for s in src:
            out["by_src"][s] = out["by_src"].get(s, 0) + 1
        v, addr = verdict(src)
        out[v] += 1
        if v == "one":
            agree = [s for s, a in src.items() if a == {addr}]
            if len(agree) >= 2:
                out["one_2plus"] += 1
            for s in agree:
                out["one_by_src"][s] = out["one_by_src"].get(s, 0) + 1
    try:
        since = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
        out["recent7_missing"] = c.execute(
            "SELECT COUNT(*) FROM mail_messages WHERE user_id=? AND direction='in' AND is_deleted=0 "
            "AND (COALESCE(from_email,'')='' OR instr(from_email,'@')=0) AND COALESCE(created_at,'')>=?",
            (int(uid), since)).fetchone()[0]
    except Exception:
        pass
    try:
        from .mail_store import _ensure_raw_hdr
        _ensure_raw_hdr(c)
        r = c.execute("SELECT COUNT(*) AS n, COALESCE(SUM(full),0) AS f FROM mail_raw_headers h "
                      "JOIN mail_messages m ON m.id=h.mail_id WHERE m.user_id=?", (int(uid),)).fetchone()
        out["hdr_saved"], out["hdr_full"] = int(r["n"] or 0), int(r["f"] or 0)
    except Exception:
        out["hdr_saved"], out["hdr_full"] = 0, 0
    return out
