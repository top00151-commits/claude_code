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
import time
from datetime import datetime, timedelta

_RE_EMAIL = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
# 본문에서 인용(앞 메일)이 시작되는 표시 — 그 앞까지만 「이 사람의 서명」으로 본다
_RE_QUOTE = re.compile(r"(?im)^\s*(?:-{2,}\s*(?:original message|원본 메시지|원본 메일|forwarded message)[^\n]*"
                       r"|>|from\s*:|보낸\s*사람\s*:|보낸사람\s*:|sent\s*:|on .{4,80} wrote:|.{0,60}님이 작성:)")
SRC = ("원문", "이름", "직원", "주소록", "답장", "서명", "인용", "본문머리", "대화", "본문주소")
# 11-25 대표 「본문 단서로 찾을 수 있으면 찾아봐」 — 약한 근거(혼자서는 채우지 않고, 다른 근거와 같을 때만 힘 보탬)
WEAK = ("본문주소",)
REPLY_DAYS = 120          # 11-25 60 → 120일(같은 제목에 늦게 답한 것까지)
CONV_DAYS = 180           # 같은 대화(제목) 앞뒤 메일을 보는 기간
CONV_MIN_SUBJ = 6         # 대화 근거 = 정리한 제목이 이 글자 수 이상일 때만(「견적」 같은 흔한 제목은 안 씀)
# 서명 줄 표시 — 「E-mail: …」「Email : …」「메일: …」「E. …」「이메일 …」
_RE_SIG_LABEL = re.compile(r"(?im)^[ \t]*(?:[|·•\-]\s*)?(?:e-?mail|email|mail|이메일|메일|e)\s*[.:：]?\s*[:：]?\s*"
                           r"(?:<|\[|\()?\s*(?:mailto:)?\s*([A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,})")
_RE_MAILTO = re.compile(r"mailto:\s*([A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,})", re.I)
# 본문 첫머리 「보낸 사람: …」 한 줄(시스템 알림 등) — 이 메일 자신의 보낸 사람일 때만
_RE_TOPHEAD = re.compile(r"^(?:보낸\s*사람|보낸이|from|발신자?|sender)\s*[:：]\s*(.+)$", re.I)
_RE_FWRE = re.compile(r"^\s*(?:\[?\s*(?:re|fw|fwd|답장|회신|전달)\s*\]?\s*[:：\]])", re.I)
# HTML 에서 인용(앞 메일)이 시작되는 곳 — 그 앞의 mailto 만 서명으로 본다
_HTML_QUOTE_MARKS = ("<blockquote", "knk-quote", "gmail_quote", "divrplyfwdmsg", "original message", "원본 메시지",
                     "forwarded message", "-----원본", "보낸 사람:", "from:")
SIG_TAIL_LINES = 14       # 내가 쓴 부분 맨 아래 몇 줄을 「서명 자리」로 볼지
_NOREPLY = ("noreply", "no-reply", "donotreply", "do-not-reply", "mailer-daemon", "postmaster")

# ── 인용 머리(11-22 2차 · 하이웍스 「전체 메일함」이 348통뿐 = 옛 원본은 하이웍스에도 없음) ──────────────
#   같은 제목의 뒤 메일(내 답장 · 다른 사람 회신 · 전달)에는 앞 메일이 인용되고, 인용 머리에
#   「From: 이름 <주소>」 + 「Sent/보낸 날짜」(또는 「…님이 작성:」·「On … wrote:」 한 줄)가 남는다.
#   → **제목이 같고 인용 날짜가 그 메일 받은 날(±1일)과 맞는 인용 머리**의 주소 = 근거 「인용」.
_RE_QFROM = re.compile(r"(?im)^[ \t>]*(?:from|보낸\s*사람|보낸이|발신자?)\s*[:：]\s*(.+)$")
_RE_QWROTE = re.compile(r"(?im)^[ \t>]*(.{6,200}?)\s*(?:wrote|님이\s*작성|작성)\s*:?\s*$")
_RE_QDATE = re.compile(r"(?im)^[ \t>]*(?:sent|date|보낸\s*날짜|날짜|발송일|보낸\s*시간|받은\s*날짜)\s*[:：]\s*(.+)$")
_RE_QSUBJ = re.compile(r"(?im)^[ \t>]*(?:subject|제목)\s*[:：]\s*(.+)$")
_RE_D_NUM = re.compile(r"(20\d{2})\s*[-./년]\s*(\d{1,2})\s*[-./월]\s*(\d{1,2})")
_MON = {m: i + 1 for i, m in enumerate(("jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"))}
_RE_D_EN1 = re.compile(r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+(\d{1,2}),?\s+(20\d{2})", re.I)
_RE_D_EN2 = re.compile(r"\b(\d{1,2})\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?,?\s+(20\d{2})", re.I)
_RE_ANGLE = re.compile(r"[<\[(]\s*(?:mailto:)?\s*([A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,})\s*[>\])]", re.I)
QUOTE_DAYS = 120


def _any_date(s: str):
    """글 속 날짜 하나 → date(못 읽으면 None)."""
    from datetime import date
    s = s or ""
    for rx, order in ((_RE_D_NUM, "ymd"), (_RE_D_EN1, "mdy"), (_RE_D_EN2, "dmy")):
        m = rx.search(s)
        if not m:
            continue
        try:
            g = m.groups()
            if order == "ymd":
                return date(int(g[0]), int(g[1]), int(g[2]))
            if order == "mdy":
                return date(int(g[2]), _MON[g[0][:3].lower()], int(g[1]))
            return date(int(g[2]), _MON[g[1][:3].lower()], int(g[0]))
        except Exception:
            return None
    return None


def _addr_in(s: str) -> str:
    m = _RE_ANGLE.search(s or "")
    if m:
        return m.group(1).lower().strip(".")
    m = _RE_EMAIL.search(s or "")
    return m.group(0).lower().strip(".") if m else ""


def quote_heads(body: str) -> list:
    """본문의 인용 머리 → [(주소, 날짜 또는 None, 제목 또는 '')]."""
    out = []
    b = body or ""
    for m in _RE_QFROM.finditer(b):
        a = _addr_in(m.group(1))
        if not a:
            continue
        seg = b[m.end():m.end() + 700]
        dm = _RE_QDATE.search(seg)
        sm = _RE_QSUBJ.search(seg)
        out.append((a, _any_date(dm.group(1)) if dm else None, (sm.group(1).strip() if sm else "")))
    for m in _RE_QWROTE.finditer(b):
        line = m.group(1)
        a = _addr_in(line)
        if a:
            out.append((a, _any_date(line), ""))
    return out


def quote_index(c, uid, rows) -> dict:
    """대상 메일 제목들과 같은 제목인 내 메일(받은·보낸)의 본문 → {제목 열쇠: [(번호, 받은 때, 본문)]}."""
    from .mail_store import _normalize_subject
    want = {_normalize_subject(r.get("subject") or "") for r in rows}
    want.discard("(제목 없음)")
    if not want:
        return {}
    ids = {}
    for r in c.execute("SELECT id, subject, COALESCE(received_at, created_at) AS at FROM mail_messages "
                       "WHERE user_id=? AND is_deleted=0 AND direction IN ('in','out')", (int(uid),)).fetchall():
        k = _normalize_subject(r["subject"] or "")
        if k in want:
            ids[r["id"]] = (k, r["at"] or "")
    out = {}
    idl = list(ids)
    for i in range(0, len(idl), 400):
        part = idl[i:i + 400]
        for r in c.execute("SELECT id, COALESCE(body_text,'') AS b FROM mail_messages WHERE id IN (%s)" % ",".join("?" * len(part)),
                           part).fetchall():
            k, at = ids[r["id"]]
            if r["b"]:
                out.setdefault(k, []).append((r["id"], at, r["b"]))
    return out


def _quote_addrs(m: dict, ix: dict) -> set:
    from .mail_store import _normalize_subject
    q = ix.get("quote") or {}
    k = _normalize_subject(m.get("subject") or "")
    rcv = _dt(m.get("received_at"))
    if not rcv or k not in q:
        return set()
    rd = rcv.date()
    found = set()
    for mid, at, body in q[k]:
        if mid == m.get("id"):
            continue
        sd = _dt(at)
        if sd and not (rcv - timedelta(days=1) <= sd <= rcv + timedelta(days=QUOTE_DAYS)):
            continue
        for a, d, sj in quote_heads(body):
            if d is None or abs((d - rd).days) > 1:
                continue
            if sj and _normalize_subject(sj) != k:
                continue
            if a in ix["mine"]:
                continue
            found.add(a)
    return found


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
    # 11-25 대화 근거 — 같은 대화(정리한 제목)에서 다른 받은 메일의 보낸 사람(주소 있는 것)
    recv = {}
    try:
        from .mail_store import _normalize_subject as _ns
        for r in c.execute("SELECT subject, lower(COALESCE(from_email,'')) AS e, COALESCE(received_at, created_at) AS at "
                           "FROM mail_messages WHERE user_id=? AND direction='in' AND is_deleted=0 "
                           "AND instr(COALESCE(from_email,''),'@')>0", (int(uid),)).fetchall():
            if r["e"] and r["e"] not in mine:
                recv.setdefault(_ns(r["subject"] or ""), []).append((r["e"], r["at"] or ""))
    except Exception:
        pass
    return {"nm": nm, "nm_core": nm_core, "staff": st_nm, "contacts": ct_nm, "sent": by_subj, "recv": recv,
            "mine": mine, "ours": tuple(OUR_DOMAINS)}


def _conv_addrs(m: dict, ix: dict) -> set:
    """대화 근거 — 같은 대화에서 ① 내가 보낸 메일의 받는 사람이 한 명이고 ② 그 사람이 대화의 다른 받은 메일 보낸이 → 그 주소.
    둘 이상이면 모두 돌려줌(= 여러 후보 · 채우지 않음). 흔한 짧은 제목은 안 씀."""
    from .mail_store import _normalize_subject
    k = _normalize_subject(m.get("subject") or "")
    if k == "(제목 없음)" or len(k.replace(" ", "")) < CONV_MIN_SUBJ:
        return set()
    rcv = _dt(m.get("received_at"))
    win = timedelta(days=CONV_DAYS)

    def _in(at):
        d = _dt(at)
        return not (rcv and d) or (rcv - win <= d <= rcv + win)
    sent1 = set()
    for t, at in (ix.get("sent") or {}).get(k, []):
        if not _in(at):
            continue
        tos = [a.strip().lower() for a in (t or "").split(",") if "@" in a]
        tos = [a for a in tos if a not in ix["mine"]]
        if len(tos) == 1:
            sent1.add(tos[0])
    if not sent1:
        return set()
    others = {e for e, at in (ix.get("recv") or {}).get(k, []) if _in(at)}
    return sent1 & others


def _dt(s):
    try:
        return datetime.strptime((s or "")[:19], "%Y-%m-%d %H:%M:%S")
    except Exception:
        return None


def _norm_at(b: str) -> str:
    """전각 ＠ · 「 @ 」 띄어 쓴 꼴 → @ (11-25 서명 보강)."""
    b = (b or "").replace("\uff20", "@").replace("\u2024", ".")
    b = re.sub(r"\s+@\s+", "@", b)
    b = re.sub(r"\s*[\[(]\s*at\s*[\])]\s*", "@", b, flags=re.I)
    return b


def own_part(body: str) -> str:
    """본문 중 이 사람이 쓴 부분(인용 앞)."""
    b = _norm_at(body)
    m = _RE_QUOTE.search(b)
    return b[:m.start()] if m else b


def _bad(a: str, exclude: set) -> bool:
    return (not a) or a in exclude or a.startswith(_NOREPLY)


def _sig_addrs(body: str, exclude: set, ours: tuple) -> set:
    """서명 근거 — 내가 쓴 부분(인용 앞)에서
    ① 「E-mail: / Email : / 메일: / E. …」 표시가 붙은 주소(우리 회사 주소도 — 사내 직원 서명 · 11-25 보강)
    ② 표시가 없으면 맨 아래 서명 자리(마지막 몇 줄)의 주소(우리 회사 주소는 뺌)."""
    b = own_part(body)
    out = set()
    for m in _RE_SIG_LABEL.finditer(b):
        a = m.group(1).lower().strip(".")
        if not _bad(a, exclude):
            out.add(a)
    if out:
        return out
    lines = [ln for ln in b.splitlines() if ln.strip()]
    tail = "\n".join(lines[-SIG_TAIL_LINES:])
    for a in _RE_EMAIL.findall(tail):
        a = a.lower().strip(".")
        if _bad(a, exclude) or a.rsplit("@", 1)[-1] in ours:
            continue
        out.add(a)
    return out


def _body_addrs(body: str, exclude: set, ours: tuple) -> set:
    """본문 주소(약한 근거) — 내가 쓴 부분의 주소 모두(우리 회사·받는 사람·나·무응답 주소 빼고)."""
    out = set()
    for a in _RE_EMAIL.findall(own_part(body)):
        a = a.lower().strip(".")
        if _bad(a, exclude) or a.rsplit("@", 1)[-1] in ours:
            continue
        out.add(a)
    return out


def _html_of(c, mid) -> str:
    try:
        r = c.execute("SELECT COALESCE(body_html,'') AS h, COALESCE(html_sha,'') AS s FROM mail_messages WHERE id=?",
                      (int(mid),)).fetchone()
    except Exception:
        try:
            r = c.execute("SELECT COALESCE(body_html,'') AS h, '' AS s FROM mail_messages WHERE id=?", (int(mid),)).fetchone()
        except Exception:
            return ""
    if not r:
        return ""
    if r["h"]:
        return r["h"]
    if r["s"]:
        try:
            from .mail_body_pack import unpack_html
            return unpack_html(c, r["s"]) or ""
        except Exception:
            return ""
    return ""


def _mailto_addrs(html: str, exclude: set, ours: tuple) -> set:
    """HTML 서명의 mailto 링크(인용 앞) — 글자 없이 링크만 있는 서명(그림 서명 옆 등)."""
    h = _norm_at(html or "")
    low = h.lower()
    cut = len(h)
    for mk in _HTML_QUOTE_MARKS:
        i = low.find(mk)
        if i >= 0:
            cut = min(cut, i)
    out = set()
    for a in _RE_MAILTO.findall(h[:cut]):
        a = a.lower().strip(".")
        if _bad(a, exclude) or a.rsplit("@", 1)[-1] in ours:
            continue
        out.add(a)
    return out


def top_head(body: str, subject: str, exclude: set) -> str:
    """본문 첫 줄이 「보낸 사람: 이름 <주소>」 꼴(시스템 알림 등)이면 그 주소 — 이 메일 자신의 보낸 사람일 때만.
    안 쓰는 경우(틀리게 채우지 않게): 제목이 RE·FW·답장·회신·전달 · 본문에 From 머리가 둘 이상(앞 메일 인용) ·
    첫 줄이 아님(내가 쓴 글 아래 붙은 전달 머리) · 나·받는 사람 주소."""
    if _RE_FWRE.match(subject or ""):
        return ""
    b = _norm_at(body)
    if len(_RE_QFROM.findall(b)) != 1:
        return ""
    first = next((ln.strip() for ln in b.splitlines() if ln.strip()), "")
    m = _RE_TOPHEAD.match(first)
    if not m:
        return ""
    a = _addr_in(m.group(1))
    return "" if _bad(a, exclude) else a


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
    body = m.get("body_text") or ""
    sg = _sig_addrs(body, excl, ix["ours"])
    if not sg:
        try:
            sg = _mailto_addrs(_html_of(c, m["id"]), excl, ix["ours"])
        except Exception:
            sg = set()
    if sg:
        src["서명"] = sg
    qa = _quote_addrs(m, ix)
    if qa:
        src["인용"] = qa
    th = top_head(body, m.get("subject") or "", excl)
    if th:
        src["본문머리"] = {th}
    cv = _conv_addrs(m, ix)
    if cv:
        src["대화"] = cv
    ba = _body_addrs(body, excl, ix["ours"])
    if len(ba) == 1 and not (ba & sg):   # 서명과 같은 글에서 나온 같은 주소는 두 번 세지 않음
        src["본문주소"] = ba
    return src


def verdict(src: dict) -> tuple:
    """(판정, 하나로 모인 주소 또는 '') — 판정 = one|many|none."""
    if "원문" in src and len(src["원문"]) == 1:
        return "one", next(iter(src["원문"]))
    strong = {k: v for k, v in src.items() if k not in WEAK}
    single = {next(iter(v)) for v in strong.values() if len(v) == 1}
    if len(single) == 1:
        return "one", next(iter(single))
    if single or any(len(v) > 1 for v in strong.values()):
        return "many", ""
    return "none", ""     # 약한 근거(본문 주소)만 있으면 = 못 찾음(채우지 않음)


LABEL = {"원문": "원문 머리글", "이름": "같은 이름의 다른 메일", "직원": "직원 명단", "주소록": "주소록",
         "답장": "내가 보낸 답장", "서명": "본문 서명", "인용": "뒤 메일의 인용 머리",
         "본문머리": "본문 첫머리 「보낸 사람」 줄", "대화": "같은 대화의 상대", "본문주소": "본문 속 주소"}


def _ensure_mark(c):
    c.execute("""CREATE TABLE IF NOT EXISTS mail_from_guessed (
        mail_id INTEGER PRIMARY KEY,
        addr TEXT, src TEXT, batch TEXT,
        created_at TEXT DEFAULT (datetime('now','localtime')))""")


def apply(c, uid, user=None, min_agree=1) -> dict:
    """11-22 대표 「둘 다 진행해」 — 「하나로 모임」 메일만 채움(여러 후보·못 찾음은 그대로).
    바꾸기 전 값 = 되돌림 표(mail_from_refill_bak · 묶음 이름 guess-…) · 「추정」 표시 = mail_from_guessed(근거 글)
    · fd_key 비움 = 폴더 다시 나눔. 반환 = 통수만."""
    from .mail_from_refill import ensure as _ensure_bak
    _ensure_bak(c)
    _ensure_mark(c)
    batch = "guess-" + time.strftime("%Y%m%d-%H%M%S")
    rows = targets(c, uid)
    ix = build_index(c, uid, user)
    ix["quote"] = quote_index(c, uid, rows)
    n = 0
    for m in rows:
        src = guess_one(c, m, ix)
        v, addr = verdict(src)
        if v != "one" or not addr:
            continue
        agree = [s for s in SRC if src.get(s) == {addr}]
        if len(agree) < min_agree:
            continue
        fe = (m.get("from_email") or "").strip()
        nm = (m.get("from_name") or "").strip() or (re.sub(r"[<>\"']", " ", fe).strip() if fe and "@" not in fe else "")
        nm = re.sub(r"\s+", " ", nm).strip()
        cur = c.execute("UPDATE mail_messages SET from_email=?, from_name=?, fd_key='' WHERE id=? AND user_id=? "
                        "AND (COALESCE(from_email,'')='' OR instr(from_email,'@')=0)", (addr, nm, int(m["id"]), int(uid)))
        if not cur.rowcount:
            continue
        c.execute("INSERT INTO mail_from_refill_bak(batch, user_id, mail_id, old_from_email, old_from_name, new_from_email, new_from_name) "
                  "VALUES(?,?,?,?,?,?,?)", (batch, int(uid), int(m["id"]), m.get("from_email") or "", m.get("from_name") or "", addr, nm))
        c.execute("INSERT OR REPLACE INTO mail_from_guessed(mail_id, addr, src, batch) VALUES(?,?,?,?)",
                  (int(m["id"]), addr, " · ".join(LABEL[s] for s in agree), batch))
        n += 1
    return {"updated": n, "batch": batch if n else ""}


def undo(c, uid) -> int:
    """마지막 「우리 자료로 채우기」 묶음 되돌림(그 뒤 다시 바뀐 메일은 그대로)."""
    from .mail_from_refill import ensure as _ensure_bak
    _ensure_bak(c)
    _ensure_mark(c)
    r = c.execute("SELECT batch FROM mail_from_refill_bak WHERE user_id=? AND batch LIKE 'guess-%' ORDER BY id DESC LIMIT 1",
                  (int(uid),)).fetchone()
    if not r:
        return 0
    n = 0
    for b in c.execute("SELECT * FROM mail_from_refill_bak WHERE user_id=? AND batch=?", (int(uid), r["batch"])).fetchall():
        n += c.execute("UPDATE mail_messages SET from_email=?, from_name=?, fd_key='' WHERE id=? AND user_id=? AND from_email=?",
                       (b["old_from_email"] or "", b["old_from_name"] or "", b["mail_id"], int(uid), b["new_from_email"])).rowcount
    c.execute("DELETE FROM mail_from_guessed WHERE batch=?", (r["batch"],))
    c.execute("DELETE FROM mail_from_refill_bak WHERE user_id=? AND batch=?", (int(uid), r["batch"]))
    return n


def guess_label(c, mail_id, addr) -> str:
    """이 메일 주소가 「우리 자료로 찾은 추정 주소」면 근거 글 · 아니면 ''."""
    try:
        _ensure_mark(c)
        r = c.execute("SELECT addr, src FROM mail_from_guessed WHERE mail_id=?", (int(mail_id),)).fetchone()
        if r and (r["addr"] or "").lower() == (addr or "").strip().lower():
            return r["src"] or "우리 자료"
    except Exception:
        pass
    return ""


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
    ix["quote"] = quote_index(c, uid, rows)
    out = {"total": len(rows), "empty": 0, "name_only": 0, "no_name": 0,
           "one": 0, "one_2plus": 0, "many": 0, "none": 0,
           "by_src": {s: 0 for s in SRC}, "one_by_src": {s: 0 for s in SRC},
           "by_year": {}, "recent7_missing": 0, "weak_only": 0}
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
        if v == "none" and src and all(k in WEAK for k in src):
            out["weak_only"] += 1
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
