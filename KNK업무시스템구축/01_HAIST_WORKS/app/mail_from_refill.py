# -*- coding: utf-8 -*-
"""보낸 사람 주소를 못 읽은 메일 다시 채우기 (대표 2026-11-22 「보낸 사람 없는 메일 5통 다시 읽어서 채워 줘」)

까닭: 예전 가져오기가 보낸 사람 머리(From)를 먼저 글자로 푼 뒤 주소를 읽어, 이름에 쉼표·@ 가 있으면 이름·주소가 빈 값으로 저장됨
      (11-22 `mail_store.split_from` 으로 고침 — 새 메일은 정상). 이미 저장된 메일은 원문을 따로 보관하지 않아 하이웍스 원본에서 머리만 다시 읽는다.

방법(내 메일만 · 읽기 전용으로 원본에 접속 · 원본은 바꾸지 않음):
  ① 대상 = 내 받은 메일 중 보낸 사람 주소가 빈 것 → 저장된 「같은 메일」 판정값(dedup_hash = Message-ID 의 해시)
  ② 메일함(POP3/IMAP)에서 최근 것부터 머리만 읽어(POP3 TOP · IMAP BODY.PEEK) Message-ID 해시가 같은 원본을 찾음
  ③ 찾은 원본의 보낸 사람 머리를 새 방식(split_from)으로 읽음
  ④ 바꾸기 전 값을 되돌림 표(mail_from_refill_bak)에 남기고 → 보낸 사람 이름·주소만 채움(다른 칸은 그대로)
  ↺ 되돌리기 = 되돌림 표의 값으로 되돌림
셈만(dry) 하면 ①~③ 까지만 하고 숫자만 돌려준다(주소·이름은 돌려주지 않음).
"""
import email
import threading
import time

_JOBS = {}            # user_id -> 상태
_LOCK = threading.Lock()
SCAN_LIMIT = 40000    # 원본 몇 통까지 머리를 볼지(11-22 하이웍스 「전체 메일」로 옛 원본까지 — 머리만이라 가벼움)


def ensure(c):
    c.execute("""CREATE TABLE IF NOT EXISTS mail_from_refill_bak (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        batch TEXT NOT NULL,
        user_id INTEGER NOT NULL,
        mail_id INTEGER NOT NULL,
        old_from_email TEXT, old_from_name TEXT,
        new_from_email TEXT, new_from_name TEXT,
        created_at TEXT DEFAULT (datetime('now','localtime')))""")


def targets(c, user_id) -> dict:
    """{dedup_hash: mail_id} — 내 받은 메일 중 보낸 사람 주소가 빈 것(지운 것 빼고). 판정값 없는 메일은 따로 셈."""
    out, nohash = {}, 0
    for r in c.execute("SELECT id, COALESCE(dedup_hash,'') AS h FROM mail_messages WHERE user_id=? AND direction='in' "
                       "AND is_deleted=0 AND (COALESCE(from_email,'')='' OR instr(from_email,'@')=0)", (int(user_id),)).fetchall():
        if r["h"]:
            out[r["h"]] = r["id"]
        else:
            nohash += 1
    return {"by_hash": out, "nohash": nohash}


def _norm_subj(sj) -> str:
    return " ".join(str(sj or "").split())


def _ts(v):
    import datetime as _dt
    try:
        return _dt.datetime.strptime(str(v or "")[:19], "%Y-%m-%d %H:%M:%S")
    except Exception:
        return None


def targets_ext(c, user_id) -> list:
    """11-24 3차 — 제목·시각으로 짝 맞추기용 대상 [(mail_id, 제목, [시각들])] (Message-ID 짝이 안 맞은 것에 씀)."""
    try:
        from .mail_body_pack import has_sent_at
        hs = has_sent_at(c)
    except Exception:
        hs = False
    out = []
    for r in c.execute("SELECT id, subject, received_at, %s AS s FROM mail_messages WHERE user_id=? AND direction='in' "
                       "AND is_deleted=0 AND (COALESCE(from_email,'')='' OR instr(from_email,'@')=0)"
                       % ("COALESCE(sent_at,'')" if hs else "''"), (int(user_id),)).fetchall():
        ts = [t for t in (_ts(r["s"]), _ts(r["received_at"])) if t]
        out.append((r["id"], _norm_subj(r["subject"]), ts))
    return out


def diag(c, user_id) -> dict:
    """11-24 대표 「무조건 해결」 — 왜 원본에서 못 찾는지 숫자로만(주소·제목·본문 안 돌려줌).
    대상의 판정값 종류(mid = Message-ID 로 만든 것 · c = 보낸이+제목+본문으로 만든 것 → 원본 Message-ID 로는 절대 안 맞음) ·
    대상 받은 달별 · 원문 머리 남은 수 · 원래 날짜 있는 수 · 내 받은 메일 전체 달별."""
    from .mail_store import _dedup_hash, _ensure_raw_hdr
    try:
        from .mail_body_pack import has_sent_at
        hs = has_sent_at(c)
    except Exception:
        hs = False
    _ensure_raw_hdr(c)
    rows = c.execute("SELECT m.id, COALESCE(m.dedup_hash,'') AS h, COALESCE(m.from_email,'') AS fe, COALESCE(m.subject,'') AS sj, "
                     "COALESCE(m.body_text,'') AS bt, COALESCE(m.received_at,'') AS ra, %s AS s, "
                     "(SELECT COUNT(*) FROM mail_raw_headers h WHERE h.mail_id=m.id) AS hk "
                     "FROM mail_messages m WHERE m.user_id=? AND m.direction='in' AND m.is_deleted=0 "
                     "AND (COALESCE(m.from_email,'')='' OR instr(m.from_email,'@')=0)"
                     % ("COALESCE(m.sent_at,'')" if hs else "''"), (int(user_id),)).fetchall()
    kind = {"mid": 0, "c": 0, "none": 0}
    by_m, hdr_kept, sent_n = {}, 0, 0
    for r in rows:
        if not r["h"]:
            kind["none"] += 1
        elif r["h"] == _dedup_hash("", r["fe"], r["sj"], r["bt"]):
            kind["c"] += 1
        else:
            kind["mid"] += 1
        mo = (r["ra"] or "")[:7] or "?"
        by_m[mo] = by_m.get(mo, 0) + 1
        hdr_kept += 1 if r["hk"] else 0
        sent_n += 1 if (r["s"] or "").strip() else 0
    allm = {}
    for r in c.execute("SELECT substr(COALESCE(received_at,''),1,7) AS mo, COUNT(*) AS n FROM mail_messages "
                       "WHERE user_id=? AND direction='in' AND is_deleted=0 GROUP BY mo", (int(user_id),)).fetchall():
        allm[r["mo"] or "?"] = r["n"]
    return {"targets": len(rows), "hash_kind": kind, "targets_by_month": dict(sorted(by_m.items())),
            "raw_header_kept": hdr_kept, "sent_at_known": sent_n,
            "all_in": sum(allm.values()), "all_in_by_month": dict(sorted(allm.items()))}


def diag_all(c) -> list:
    """11-24 대표 「다음부터 등록하는 다른 직원들 메일은 정확하게 보낸 사람이」 — 모든 사람 기준 숫자만(관리자).
    사람 번호별: 받은 메일 · 보낸 사람 주소 빈 메일 · 그중 최근 7일 안에 저장된 것(새로 생긴 것) · 그중 원문 머리 남긴 것."""
    from .mail_store import _ensure_raw_hdr
    _ensure_raw_hdr(c)
    rows = c.execute(
        "SELECT m.user_id AS u, COUNT(*) AS n_in, "
        "SUM(CASE WHEN (COALESCE(m.from_email,'')='' OR instr(m.from_email,'@')=0) THEN 1 ELSE 0 END) AS empty, "
        "SUM(CASE WHEN (COALESCE(m.from_email,'')='' OR instr(m.from_email,'@')=0) "
        "         AND COALESCE(m.created_at,'') >= datetime('now','localtime','-7 days') THEN 1 ELSE 0 END) AS empty_7d, "
        "SUM(CASE WHEN (COALESCE(m.from_email,'')='' OR instr(m.from_email,'@')=0) "
        "         AND EXISTS(SELECT 1 FROM mail_raw_headers h WHERE h.mail_id=m.id) THEN 1 ELSE 0 END) AS empty_hdr "
        "FROM mail_messages m WHERE m.direction='in' AND m.is_deleted=0 GROUP BY m.user_id ORDER BY empty DESC, m.user_id").fetchall()
    return [{"user_id": r["u"], "in": r["n_in"] or 0, "empty": r["empty"] or 0, "empty_7d": r["empty_7d"] or 0,
             "empty_hdr": r["empty_hdr"] or 0} for r in rows]


def _hash_of_header(raw_hdr: bytes) -> str:
    from .mail_store import _dedup_hash
    try:
        msg = email.message_from_bytes(raw_hdr)
        mid = str(msg.get("Message-ID") or msg.get("Message-Id") or "").strip().strip("<>").strip()
    except Exception:
        mid = ""
    return _dedup_hash(mid, "", "", "") if mid else ""


def _parse_from(raw_hdr: bytes):
    from .mail_store import parse_raw_email
    p = parse_raw_email(bytes(raw_hdr).rstrip(b"\r\n") + b"\r\n\r\n") or {}
    return (p.get("from_name") or "").strip(), (p.get("from_email") or "").strip()


def _parse_hdr(raw_hdr: bytes) -> dict:
    """머리 한 번 읽기 — 보낸 사람(이름·주소) · 제목 · 보낸 시각(Date → 서버 시각)."""
    from .mail_store import parse_raw_email
    p = parse_raw_email(bytes(raw_hdr).rstrip(b"\r\n") + b"\r\n\r\n") or {}
    return {"nm": (p.get("from_name") or "").strip(), "ad": (p.get("from_email") or "").strip(),
            "sj": _norm_subj(p.get("subject")), "t": _ts(p.get("sent_at"))}


WIN_MIN = 15   # 제목·시각 짝 맞추기 허용 차이(분)


def _subj_pairs(ext: list, heads: list) -> dict:
    """제목이 같고 시각이 ±15분인 짝 — **서로 하나씩만** 맞을 때만 채움(둘 이상이면 안 채움). 반환 {mail_id: (이름, 주소)}."""
    import datetime as _dt
    w = _dt.timedelta(minutes=WIN_MIN)
    by_sj = {}
    for i, (_mid, sj, _ts_) in enumerate(ext):
        if sj and sj != "(제목 없음)":
            by_sj.setdefault(sj, []).append(i)
    t_c, h_c = {}, {}
    for hi, h in enumerate(heads):
        if not (h["sj"] and h["t"] and h["ad"]):
            continue
        for ti in by_sj.get(h["sj"], ()):
            if any(abs(h["t"] - t) <= w for t in ext[ti][2]):
                t_c.setdefault(ti, []).append(hi)
                h_c.setdefault(hi, []).append(ti)
    out = {}
    for ti, hs_ in t_c.items():
        if len(hs_) == 1 and len(h_c.get(hs_[0], ())) == 1:
            h = heads[hs_[0]]
            out[ext[ti][0]] = (h["nm"], h["ad"])
    return out


def scan(protocol, host, port, ssl, user, pw, want: dict, state: dict, ext=None) -> dict:
    """메일함에서 최근 것부터 머리만 읽어 want(해시→mail_id) 와 같은 원본을 찾는다. 반환 {mail_id: (이름, 주소)}.
    11-24 3차: ext(제목·시각 대상)가 있으면 Message-ID 로 못 찾은 대상을 제목+시각(±15분)으로 — 서로 하나씩만 맞을 때만.
    state 에 원본 숫자(src_stat · src_uidl · src_oldest · src_newest = YYYY-MM)도 적음."""
    from . import mail_fetch as F
    found = {}
    left = dict(want)
    heads = []
    mos = []
    ext = list(ext or [])

    def _seen(raw):
        hd = _parse_hdr(raw)
        if hd["t"]:
            mos.append(hd["t"].strftime("%Y-%m"))
        if ext:
            heads.append(hd)
        return hd
    if (protocol or "pop3").lower() == "imap":
        M = F._imap_connect(host, port, ssl, user, pw, timeout=40)
        try:
            M.select("INBOX", readonly=True)
            typ, data = M.uid("search", None, "ALL")
            uids = sorted(int(x) for x in data[0].split()) if (data and data[0]) else []
            state["src_uidl"] = len(uids)
            uids = uids[::-1][:SCAN_LIMIT]
            for i in range(0, len(uids), 100):
                if not left and not ext:
                    break
                chunk = ",".join(str(u) for u in uids[i:i + 100])
                typ, md = M.uid("fetch", chunk, "(BODY.PEEK[HEADER.FIELDS (MESSAGE-ID FROM REPLY-TO SENDER RETURN-PATH X-ORIGINAL-FROM X-SENDER SUBJECT DATE)])")
                for part in md or []:
                    if isinstance(part, tuple) and len(part) > 1 and isinstance(part[1], (bytes, bytearray)):
                        raw = bytes(part[1])
                        hd = _seen(raw)
                        h = _hash_of_header(raw)
                        if h and h in left:
                            found[left.pop(h)] = (hd["nm"], hd["ad"])
                            if ext:
                                heads.pop()
                state["scanned"] = min(len(uids), i + 100)
        finally:
            try:
                M.logout()
            except Exception:
                pass
    else:
        M = F._pop3_connect(host, port, ssl, user, pw, timeout=40)
        try:
            try:
                state["src_stat"] = int(M.stat()[0])
            except Exception:
                state["src_stat"] = -1
            resp, lines, _o = M.uidl()
            nums = []
            for ln in lines or []:
                try:
                    nums.append(int(ln.split()[0]))
                except Exception:
                    pass
            state["src_uidl"] = len(nums)
            nums = sorted(nums, reverse=True)[:SCAN_LIMIT]
            for k, n in enumerate(nums):
                if not left and not ext:
                    break
                try:
                    resp, hl, _o = M.top(n, 0)
                except Exception:
                    continue
                raw = b"\r\n".join(hl)
                hd = _seen(raw)
                h = _hash_of_header(raw)
                if h and h in left:
                    found[left.pop(h)] = (hd["nm"], hd["ad"])
                    if ext:
                        heads.pop()
                if k % 50 == 0:
                    state["scanned"] = k + 1
            state["scanned"] = k + 1 if nums else 0
        finally:
            try:
                M.quit()
            except Exception:
                pass
    if mos:
        state["src_oldest"], state["src_newest"] = min(mos), max(mos)
    if ext:
        rest = [e for e in ext if e[0] not in found]
        sp = _subj_pairs(rest, heads)
        state["found_subj"] = len([1 for v in sp.values() if v[1]])
        found.update(sp)
    return found


def apply(c, user_id, found: dict, batch: str) -> int:
    """되돌림 표에 바꾸기 전 값을 남기고 보낸 사람 이름·주소만 채움. 지금도 비어 있는 메일만(그사이 바뀐 것은 안 건드림)."""
    ensure(c)
    n = 0
    for mid, (nm, ad) in found.items():
        if not ad:
            continue
        r = c.execute("SELECT from_email, from_name FROM mail_messages WHERE id=? AND user_id=? AND (COALESCE(from_email,'')='' OR instr(from_email,'@')=0)",
                      (int(mid), int(user_id))).fetchone()
        if not r:
            continue
        c.execute("INSERT INTO mail_from_refill_bak(batch, user_id, mail_id, old_from_email, old_from_name, new_from_email, new_from_name) "
                  "VALUES(?,?,?,?,?,?,?)", (batch, int(user_id), int(mid), r["from_email"], r["from_name"], ad, nm))
        # fd_key 비움 = 보낸 사람이 바뀌었으니 폴더를 다시 나눔(11-22)
        c.execute("UPDATE mail_messages SET from_email=?, from_name=?, fd_key='' WHERE id=? AND user_id=?", (ad, nm, int(mid), int(user_id)))
        n += 1
    return n


def undo(c, user_id) -> int:
    """마지막으로 채운 묶음을 되돌림(그 뒤 다시 바뀐 메일은 그대로)."""
    ensure(c)
    r = c.execute("SELECT batch FROM mail_from_refill_bak WHERE user_id=? ORDER BY id DESC LIMIT 1", (int(user_id),)).fetchone()
    if not r:
        return 0
    n = 0
    for b in c.execute("SELECT * FROM mail_from_refill_bak WHERE user_id=? AND batch=?", (int(user_id), r["batch"])).fetchall():
        n += c.execute("UPDATE mail_messages SET from_email=?, from_name=?, fd_key='' WHERE id=? AND user_id=? AND from_email=?",
                       (b["old_from_email"] or "", b["old_from_name"] or "", b["mail_id"], int(user_id), b["new_from_email"])).rowcount
    c.execute("DELETE FROM mail_from_refill_bak WHERE user_id=? AND batch=?", (int(user_id), r["batch"]))
    return n


def status(user_id) -> dict:
    with _LOCK:
        return dict(_JOBS.get(int(user_id)) or {"state": "none"})


def start(user_id, creds, dry: bool, db_session, on_done=None) -> dict:
    """뒤에서 돌림(메일함 머리 읽기가 오래 걸릴 수 있어 화면이 기다리지 않게) — 같은 사람이 돌리는 중이면 새로 안 함."""
    uid = int(user_id)
    with _LOCK:
        cur = _JOBS.get(uid)
        if cur and cur.get("state") == "running":
            return dict(cur)
        st = {"state": "running", "dry": bool(dry), "targets": 0, "nohash": 0, "scanned": 0, "found": 0,
              "found_mid": 0, "found_subj": 0, "src_stat": None, "src_uidl": None, "src_oldest": "", "src_newest": "",
              "diag": {}, "updated": 0, "error": "", "started": time.strftime("%H:%M:%S")}
        _JOBS[uid] = st

    def run():
        try:
            with db_session() as c:
                t = targets(c, uid)
                ext = targets_ext(c, uid)
                try:
                    st["diag"] = diag(c, uid)
                except Exception as _e:
                    st["diag"] = {"error": str(_e)[:120]}
            st["targets"], st["nohash"] = len(t["by_hash"]) + t["nohash"], t["nohash"]
            found = {}
            if t["by_hash"] or ext:
                protocol, host, port, ssl, user, pw = creds
                found = scan(protocol, host, port, ssl, user, pw, t["by_hash"], st, ext=ext)
            st["found"] = sum(1 for v in found.values() if v[1])
            st["found_mid"] = st["found"] - int(st.get("found_subj") or 0)
            if not dry and found:
                with db_session() as c:
                    st["updated"] = apply(c, uid, found, time.strftime("%Y%m%d-%H%M%S"))
                if on_done:
                    try:
                        on_done(uid)
                    except Exception:
                        pass
            st["state"] = "done"
        except Exception as e:
            st["state"] = "error"
            st["error"] = ("%s: %s" % (type(e).__name__, e))[:300]
    threading.Thread(target=run, name="mail-from-refill-%d" % uid, daemon=True).start()
    return dict(st)
