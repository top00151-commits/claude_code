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


def scan(protocol, host, port, ssl, user, pw, want: dict, state: dict) -> dict:
    """메일함에서 최근 것부터 머리만 읽어 want(해시→mail_id) 와 같은 원본을 찾는다. 반환 {mail_id: (이름, 주소)}."""
    from . import mail_fetch as F
    found = {}
    left = dict(want)
    if (protocol or "pop3").lower() == "imap":
        M = F._imap_connect(host, port, ssl, user, pw, timeout=40)
        try:
            M.select("INBOX", readonly=True)
            typ, data = M.uid("search", None, "ALL")
            uids = sorted(int(x) for x in data[0].split()) if (data and data[0]) else []
            uids = uids[::-1][:SCAN_LIMIT]
            for i in range(0, len(uids), 100):
                if not left:
                    break
                chunk = ",".join(str(u) for u in uids[i:i + 100])
                typ, md = M.uid("fetch", chunk, "(BODY.PEEK[HEADER.FIELDS (MESSAGE-ID FROM REPLY-TO SENDER RETURN-PATH X-ORIGINAL-FROM X-SENDER)])")
                for part in md or []:
                    if isinstance(part, tuple) and len(part) > 1 and isinstance(part[1], (bytes, bytearray)):
                        h = _hash_of_header(bytes(part[1]))
                        if h and h in left:
                            found[left.pop(h)] = _parse_from(bytes(part[1]))
                state["scanned"] = min(len(uids), i + 100)
        finally:
            try:
                M.logout()
            except Exception:
                pass
    else:
        M = F._pop3_connect(host, port, ssl, user, pw, timeout=40)
        try:
            resp, lines, _o = M.uidl()
            nums = []
            for ln in lines or []:
                try:
                    nums.append(int(ln.split()[0]))
                except Exception:
                    pass
            nums = sorted(nums, reverse=True)[:SCAN_LIMIT]
            for k, n in enumerate(nums):
                if not left:
                    break
                try:
                    resp, hl, _o = M.top(n, 0)
                except Exception:
                    continue
                raw = b"\r\n".join(hl)
                h = _hash_of_header(raw)
                if h and h in left:
                    found[left.pop(h)] = _parse_from(raw)
                if k % 50 == 0:
                    state["scanned"] = k + 1
            state["scanned"] = len(nums) if not left else state.get("scanned", 0)
        finally:
            try:
                M.quit()
            except Exception:
                pass
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
              "updated": 0, "error": "", "started": time.strftime("%H:%M:%S")}
        _JOBS[uid] = st

    def run():
        try:
            with db_session() as c:
                t = targets(c, uid)
            st["targets"], st["nohash"] = len(t["by_hash"]) + t["nohash"], t["nohash"]
            found = {}
            if t["by_hash"]:
                protocol, host, port, ssl, user, pw = creds
                found = scan(protocol, host, port, ssl, user, pw, t["by_hash"], st)
            st["found"] = sum(1 for v in found.values() if v[1])
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
