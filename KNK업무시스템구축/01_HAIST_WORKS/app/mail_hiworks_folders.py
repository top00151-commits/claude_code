# -*- coding: utf-8 -*-
"""하이웍스 개인 메일함 가져오기 — 11-27 대표 「1번으로 진행해」 · 「아웃룩 안 쓰고 하이웍스만 쓰는 직원들이 있어서 만드는 거야」

하이웍스 웹메일에서 직원이 직접 만든 메일함(주간업무·자금일보·사람 이름 폴더 등)을 이음 메일로 옮겨 온다.
  ① 연결·폴더 보기 — 본인 하이웍스 주소·비밀번호(그 자리 입력 · 저장 안 함) 또는 저장된 받기 설정으로 IMAP 연결
     → 폴더 목록(이름 해독) 중 받은·보낸·임시·휴지통·스팸 같은 기본 함은 빼고 개인 메일함만 · 각 메일 수
  ② 폴더 고르기 → ③ 가져오기(뒤에서 묶음으로 · 진행 상황 · 멈추기 · 다시 누르면 이어서)
     · 이미 이음 메일에 있는 메일(같은 메일 번호 · 번호 없으면 보낸이+제목+본문이 같은 것) = 같은 이름 폴더로 옮기기만
       (사용자가 이미 다른 폴더로 옮긴 메일·내가 정한 규칙이 다른 곳으로 보내는 메일·지운 메일 = 그대로 둠 · 수만 알림)
     · 없는 메일 = 원문을 받아 저장(AI·알림·자동 응답 없음 · 받은 때 = 하이웍스에 도착한 때 · 읽음 = 하이웍스 그대로)
  ④ 규칙 확인 — 폴더마다 보낸 사람(또는 회사 주소)이 대부분이면 「보낸 사람 → 이 폴더」 후보만 보여 줌
     → 사용자가 체크하고 「확인한 규칙 저장」을 눌러야 저장(저절로 저장 없음 · 대표 규정 knk-no-silent-change)
하이웍스 쪽은 읽기만 한다(읽기 전용으로 열기 · 원문도 읽음 표시가 안 붙는 방식으로만 읽음 · 지우기·옮기기·표시 바꾸기 없음).
비밀번호는 저장하지 않는다 — 가져오는 동안 그 작업 안에만 들고 있다가 끝나거나 멈추면 버림(기록·로그에 안 남김).
본인 메일함만 — 입력한 하이웍스 주소가 로그인한 사람 본인의 회사 메일 주소와 같을 때만 · 저장되는 메일도 본인 것으로만.
DB 를 잡은 채 하이웍스를 기다리지 않는다(받기 → 그다음 짧게 저장).
"""
from __future__ import annotations

import base64
import datetime as _dt
import email.utils as _eu
import imaplib
import json
import re
import threading
import time
from collections import Counter
from email.parser import BytesHeaderParser

DEFAULT_HOST = "imaps.hiworks.com"       # 하이웍스 IMAP(SSL) — 받기 설정 기본값과 같은 계열(pop3s/smtps.hiworks.com)
ALT_HOSTS = ("imap.hiworks.com",)        # 기본 주소에 닿지 않을 때만 한 번 더(받기 설정 화면의 옛 기본값)
DEFAULT_PORT = 993
HEAD_CHUNK = 50                          # 머리글을 한 번에 읽는 통수
MAX_MSG_BYTES = 40 * 1024 * 1024         # 한 통이 이보다 크면 받지 않고 하이웍스에 둠(수만 알림)
STALE_MIN = 10                           # 「가져오는 중」인데 이만큼 소식이 없으면 멈춘 것으로 봄(서버 재시작 등)
RULE_RATIO = 0.7
RULE_MIN = 3

# 기본 함(개인 메일함 아님) — 빈칸 뺀 소문자 이름
_SYSTEM_NAMES = {
    "inbox", "받은메일함", "받은편지함",
    "보낸메일함", "보낸편지함", "sent", "sentmessages", "sentitems", "sentmail",
    "임시보관함", "drafts", "draft",
    "휴지통", "trash", "deleteditems", "deletedmessages",
    "스팸메일함", "스팸편지함", "스팸", "junk", "junkemail", "junkmail", "spam", "bulkmail",
    "예약메일함", "내게쓴메일함", "outbox", "보낼편지함", "승인대기메일함", "archive", "allmail",
}
_INBOX_NAMES = {"inbox", "받은메일함", "받은편지함"}
_SYSTEM_FLAGS = {"\\sent", "\\drafts", "\\trash", "\\junk", "\\all", "\\archive", "\\flagged", "\\important"}

# 가져오는 중인 작업(이 프로세스) — 사용자 번호 → 멈춤 신호
_RUNNING = {}
_RUN_LOCK = threading.Lock()


# ─── 이름 ─────────────────────────────────────────────────────────
def decode_mutf7(s) -> str:
    """IMAP 폴더 이름(수정 UTF-7) → 한글 이름. 예) &yPzBXNHg- → 주간업무 쪽 글자."""
    if isinstance(s, (bytes, bytearray)):
        s = bytes(s).decode("ascii", "replace")
    out, i = [], 0
    while i < len(s):
        ch = s[i]
        if ch != "&":
            out.append(ch)
            i += 1
            continue
        j = s.find("-", i)
        if j < 0:
            out.append(s[i:])
            break
        if j == i + 1:
            out.append("&")
        else:
            b64 = s[i + 1:j].replace(",", "/")
            b64 += "=" * (-len(b64) % 4)
            try:
                out.append(base64.b64decode(b64).decode("utf-16-be"))
            except Exception:
                out.append(s[i:j + 1])
        i = j + 1
    return "".join(out)


def encode_mutf7(s: str) -> str:
    """한글 이름 → IMAP 폴더 이름(시험·되짚기용)."""
    out, buf = [], []

    def flush():
        if buf:
            b = base64.b64encode("".join(buf).encode("utf-16-be")).decode("ascii").rstrip("=").replace("/", ",")
            out.append("&" + b + "-")
            buf.clear()
    for ch in s:
        if 0x20 <= ord(ch) <= 0x7e:
            flush()
            out.append("&-" if ch == "&" else ch)
        else:
            buf.append(ch)
    flush()
    return "".join(out)


def _norm(s) -> str:
    return re.sub(r"[\s._\-]+", "", (s or "")).lower()


_LIST_RE = re.compile(r'^\((?P<flags>[^)]*)\)\s+(?P<d>"(?:[^"\\]|\\.)*"|NIL)\s+(?P<n>.*)$', re.I)


def _unq(s: str) -> str:
    s = s.strip()
    if len(s) >= 2 and s[0] == '"' and s[-1] == '"':
        return re.sub(r'\\(.)', r'\1', s[1:-1])
    return s


def parse_list_item(item):
    """LIST 응답 한 줄 → (표시 목록, 구분자, 원래 이름) 또는 None. 글자 묶음(literal)으로 온 이름도 받음."""
    if isinstance(item, tuple):
        head = item[0].decode("utf-8", "replace") if isinstance(item[0], (bytes, bytearray)) else str(item[0])
        name = item[1].decode("utf-8", "replace") if isinstance(item[1], (bytes, bytearray)) else str(item[1])
        head = re.sub(r"\{\d+\}\s*$", "", head).strip() + ' "' + name.replace("\\", "\\\\").replace('"', '\\"') + '"'
        line = head
    elif isinstance(item, (bytes, bytearray)):
        line = bytes(item).decode("utf-8", "replace")
    else:
        line = str(item or "")
    m = _LIST_RE.match(line.strip())
    if not m:
        return None
    flags = [f.lower() for f in m.group("flags").split()]
    d = m.group("d")
    delim = "" if d.upper() == "NIL" else _unq(d)
    return flags, delim, _unq(m.group("n"))


def folder_path(raw: str, delim: str) -> list:
    """원래 이름 → 받은메일함 아래 경로(한글 이름 조각들). 받은메일함 자체·기본 함 = []."""
    parts = [decode_mutf7(p) for p in (raw.split(delim) if delim else [raw])]
    parts = [p.strip() for p in parts if p.strip()]
    if parts and _norm(parts[0]) in _INBOX_NAMES:
        parts = parts[1:]
    if not parts or any(_norm(p) in _SYSTEM_NAMES for p in parts[:1]):
        return []
    return parts


def quote(raw: str) -> str:
    return '"' + raw.replace("\\", "\\\\").replace('"', '\\"') + '"'


# ─── 본인 확인 ─────────────────────────────────────────────────────
def own_addresses(c, uid) -> set:
    """로그인한 사람 본인의 회사 메일 주소들 — 직원 명부 이메일 · 내 보내기 주소 · 내 받기 설정 아이디."""
    out = set()
    for sql in ("SELECT email AS a FROM users WHERE id=?",
                "SELECT smtp_email AS a FROM user_mail_creds WHERE user_id=?",
                "SELECT username AS a FROM mail_fetch_accounts WHERE owner_user_id=?"):
        try:
            for r in c.execute(sql, (uid,)).fetchall():
                a = (r["a"] or "").strip().lower()
                if "@" in a and " " not in a:
                    out.add(a)
        except Exception:
            pass
    return out


def match_own(c, uid, typed) -> str:
    """입력한 하이웍스 아이디 → 본인 주소(맞으면) 또는 ''. 「hong」만 쳐도 본인 주소 앞부분과 같으면 그 주소."""
    t = (typed or "").strip().lower()
    if not t:
        return ""
    own = own_addresses(c, uid)
    if "@" in t:
        return t if t in own else ""
    hit = [a for a in own if a.split("@", 1)[0] == t]
    return hit[0] if len(set(hit)) == 1 else ""


def saved_password(c, uid, addr):
    """저장된 비밀번호(받기 설정 · 보내기 설정 — 아이디가 본인 주소와 같을 때만) → 글자 또는 None. 화면·기록에는 내보내지 않음."""
    from . import mail_send as MSend
    from . import mail_fetch as MFetch
    try:
        a = MFetch.get_account(c, uid)
    except Exception:
        a = None
    if a and (a.get("username") or "").strip().lower() == addr and a.get("password_enc"):
        try:
            pw = MSend.decrypt(a["password_enc"])
            if pw:
                return pw
        except Exception:
            pass
    try:
        cr = MSend.get_creds(c, uid)
    except Exception:
        cr = None
    if cr and (cr.get("email") or "").strip().lower() == addr:
        return cr.get("password")
    return None


# ─── 연결 ─────────────────────────────────────────────────────────
def _real_connect(host, port, user, pw):
    from .mail_fetch import _imap_connect
    return _imap_connect(host, port, True, user, pw, timeout=30)


CONNECT = _real_connect   # 시험에서 가짜로 바꿈


def connect(host, port, user, pw):
    """연결 → (IMAP 객체, 쓴 주소). 기본 주소에 닿지 않으면(로그인 실패 말고) 옛 주소로 한 번 더."""
    host = (host or DEFAULT_HOST).strip()
    tries = [host] + ([h for h in ALT_HOSTS if h != host] if host == DEFAULT_HOST else [])
    last = None
    for h in tries:
        try:
            return CONNECT(h, int(port or DEFAULT_PORT), user, pw), h
        except imaplib.IMAP4.error:
            raise
        except Exception as e:   # 주소를 못 찾음·연결 거부 등
            last = e
    raise last


def friendly_error(e) -> str:
    s = "%s" % (e,)
    low = s.lower()
    if isinstance(e, imaplib.IMAP4.error) or "authenticat" in low or "login" in low:
        return ("하이웍스에 로그인하지 못했습니다. 주소·비밀번호를 다시 확인해 주세요. 맞는데도 안 되면 "
                "하이웍스 메일 → 환경설정 → 「POP3/IMAP 설정」에서 IMAP 사용을 켜 주세요(관리자가 막아 둔 경우 관리팀에 요청).")
    if "timed out" in low or "timeout" in low:
        return "하이웍스가 답하지 않습니다(시간 초과). 잠시 뒤 다시 해 주세요."
    if "getaddrinfo" in low or "name or service" in low or "nodename" in low or "refused" in low:
        return "하이웍스 서버 주소에 닿지 못했습니다. 아래 「서버 주소」가 맞는지 확인해 주세요(보통 imaps.hiworks.com)."
    return "하이웍스에 연결하지 못했습니다(%s). 잠시 뒤 다시 해 주세요." % type(e).__name__


def _logout(M):
    try:
        M.logout()
    except Exception:
        pass


def list_folders(M) -> list:
    """개인 메일함 목록 [{raw, delim, path, label, count}] — 기본 함·고를 수 없는 묶음은 뺌."""
    typ, data = M.list()
    out = []
    for it in data or []:
        if it is None:
            continue
        p = parse_list_item(it)
        if not p:
            continue
        flags, delim, raw = p
        if "\\noselect" in flags or "\\nonexistent" in flags or (set(flags) & _SYSTEM_FLAGS):
            continue
        path = folder_path(raw, delim)
        if not path:
            continue
        n = None
        try:
            t2, d2 = M.status(quote(raw), "(MESSAGES)")
            mm = re.search(rb"MESSAGES\s+(\d+)", d2[0] if d2 and isinstance(d2[0], (bytes, bytearray)) else b"")
            n = int(mm.group(1)) if mm else None
        except Exception:
            n = None
        out.append({"raw": raw, "delim": delim, "path": path, "label": " › ".join(path), "count": n})
    out.sort(key=lambda f: f["label"])
    return out


# ─── 메일 읽기(하이웍스 쪽 — 읽기만) ───────────────────────────────
_HEAD_ITEMS = "(UID FLAGS INTERNALDATE RFC822.SIZE BODY.PEEK[HEADER.FIELDS (MESSAGE-ID FROM SUBJECT DATE)])"


def _select(M, raw):
    typ, d = M.select(quote(raw), readonly=True)
    if typ != "OK":
        raise RuntimeError("폴더를 열지 못했습니다")


def all_uids(M) -> list:
    typ, data = M.uid("SEARCH", None, "ALL")
    if not data or not data[0]:
        return []
    return sorted(int(x) for x in data[0].split())


def _idate(meta: bytes) -> str:
    m = re.search(rb'INTERNALDATE "([^"]+)"', meta or b"")
    if not m:
        return ""
    try:
        d = _dt.datetime.strptime(m.group(1).decode("ascii"), "%d-%b-%Y %H:%M:%S %z")
        return d.astimezone().strftime("%Y-%m-%d %H:%M:%S")   # 서버 시각(받은 때와 같은 기준)
    except Exception:
        return ""


def fetch_heads(M, uids) -> list:
    """[{uid, mid, from, subject, date, seen, size}] — 본문 없이 머리글만(읽음 표시 안 붙음)."""
    if not uids:
        return []
    typ, data = M.uid("FETCH", ",".join(str(u) for u in uids), _HEAD_ITEMS)
    out = []
    for it in data or []:
        if not isinstance(it, tuple) or len(it) < 2:
            continue
        meta = it[0] if isinstance(it[0], (bytes, bytearray)) else str(it[0]).encode()
        mu = re.search(rb"UID (\d+)", meta)
        if not mu:
            continue
        ms = re.search(rb"RFC822\.SIZE (\d+)", meta)
        mf = re.search(rb"FLAGS \(([^)]*)\)", meta)
        h = BytesHeaderParser().parsebytes(it[1] if isinstance(it[1], (bytes, bytearray)) else b"")
        mid = str(h.get("Message-ID") or h.get("Message-Id") or "").strip().strip("<>").strip()
        out.append({"uid": int(mu.group(1)), "mid": mid[:500],
                    "from": (_eu.parseaddr(str(h.get("From") or ""))[1] or "").strip().lower(),
                    "size": int(ms.group(1)) if ms else 0,
                    "seen": bool(mf and b"\\seen" in mf.group(1).lower()),
                    "idate": _idate(meta)})
    return out


def fetch_raw(M, uid) -> bytes:
    typ, data = M.uid("FETCH", str(uid), "(BODY.PEEK[])")
    for it in data or []:
        if isinstance(it, tuple) and len(it) >= 2 and isinstance(it[1], (bytes, bytearray)):
            return bytes(it[1])
    return b""


# ─── 작업 기록 표 ─────────────────────────────────────────────────
_COUNTS = ("total", "done", "saved", "moved", "already", "kept", "other", "failed", "big")


def ensure(c):
    try:   # 메일 표의 더한 칸(이 메일만 폴더 fd_pin 등)이 먼저 있어야 함
        from .mail_store import _ensure_security_cols
        _ensure_security_cols(c)
    except Exception:
        pass
    c.execute("""CREATE TABLE IF NOT EXISTS mail_hw_runs(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        state TEXT DEFAULT 'running',
        folders TEXT DEFAULT '[]',
        created_at TEXT DEFAULT (datetime('now','localtime')),
        last_at TEXT DEFAULT (datetime('now','localtime')),
        total INTEGER DEFAULT 0, done INTEGER DEFAULT 0, saved INTEGER DEFAULT 0, moved INTEGER DEFAULT 0,
        already INTEGER DEFAULT 0, kept INTEGER DEFAULT 0, other INTEGER DEFAULT 0, failed INTEGER DEFAULT 0,
        big INTEGER DEFAULT 0, cur TEXT DEFAULT '', msg TEXT DEFAULT '')""")
    c.execute("CREATE INDEX IF NOT EXISTS idx_mailhw_run_user ON mail_hw_runs(user_id, id)")
    c.execute("""CREATE TABLE IF NOT EXISTS mail_hw_items(
        mail_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        run_id INTEGER,
        fkey TEXT NOT NULL,
        action TEXT,
        old_pin TEXT DEFAULT '',
        from_email TEXT DEFAULT '',
        PRIMARY KEY(user_id, mail_id, fkey))""")


def latest(c, uid):
    ensure(c)
    r = c.execute("SELECT * FROM mail_hw_runs WHERE user_id=? ORDER BY id DESC LIMIT 1", (uid,)).fetchone()
    return dict(r) if r else None


def _stale(t) -> bool:
    try:
        last = _dt.datetime.strptime((t.get("last_at") or "")[:19], "%Y-%m-%d %H:%M:%S")
    except Exception:
        return True
    return _dt.datetime.now() - last > _dt.timedelta(minutes=STALE_MIN)


def public(t) -> dict:
    if not t:
        return {}
    st = t.get("state")
    if st == "running" and t.get("user_id") not in _RUNNING and _stale(t):
        st = "lost"   # 서버가 다시 켜졌거나 끊김 — 「이어서 하기」
    try:
        fl = [f.get("label") for f in json.loads(t.get("folders") or "[]")]
    except Exception:
        fl = []
    d = {k: int(t.get(k) or 0) for k in _COUNTS}
    d.update(state=st, folders=fl, cur=t.get("cur") or "", msg=t.get("msg") or "",
             created_at=t.get("created_at") or "", last_at=t.get("last_at") or "")
    return d


def _bump(c, rid, **kw):
    sets = ["last_at=datetime('now','localtime')"]
    args = []
    for k, v in kw.items():
        if k in _COUNTS:
            sets.append("%s=%s+?" % (k, k))
            args.append(int(v or 0))
        elif k in ("state", "cur", "msg"):
            sets.append("%s=?" % k)
            args.append((v or "")[:300])
    args.append(rid)
    c.execute("UPDATE mail_hw_runs SET " + ",".join(sets) + " WHERE id=?", args)


def is_running(uid) -> bool:
    with _RUN_LOCK:
        return uid in _RUNNING


def stop(c, uid) -> int:
    ensure(c)
    with _RUN_LOCK:
        ev = _RUNNING.get(uid)
        if ev:
            ev.set()
    return c.execute("UPDATE mail_hw_runs SET state='stopped', msg='멈추기를 눌러 멈췄습니다', "
                     "last_at=datetime('now','localtime') WHERE user_id=? AND state='running'", (uid,)).rowcount


# ─── 한 통 판단(이음 메일 쪽 — 짧게) ───────────────────────────────
def _rules_of(c, uid):
    from . import mail_folders as MF
    valid = {r[0] for r in c.execute("SELECT DISTINCT target FROM mail_move_rules WHERE user_id=?", (uid,)).fetchall()}
    return MF._rule_index(c, uid, valid) if valid else None


def _find(c, uid, h):
    from . import mail_store as MS
    MS._ensure_dedup_cols(c)
    r = c.execute("SELECT id, direction, is_deleted, COALESCE(fd_pin,'') AS pin, lower(COALESCE(from_email,'')) AS e, "
                  "COALESCE(received_at,'') AS ts FROM mail_messages WHERE user_id=? AND dedup_hash=? "
                  "ORDER BY is_deleted, (direction='in') DESC, id LIMIT 1", (uid, h)).fetchone()
    return dict(r) if r else None


def place_existing(c, uid, row, key, ri, rid):
    """이미 있는 메일 → 'moved' | 'already' | 'kept' | 'other'. 사용자가 고른 자리(다른 폴더·규칙)·지운 메일·보낸 메일은 그대로."""
    from . import mail_folders as MF
    if row["direction"] != "in" or row["is_deleted"]:
        act = "other"
    elif row["pin"] == key:
        act = "already"
    elif row["pin"]:
        act = "kept"
    else:
        hit = MF._rule_for(ri, row["e"], row["ts"]) if ri else None
        if hit and hit[0] == key:
            act = "already"
        elif hit:
            act = "kept"
        else:
            c.execute("UPDATE mail_messages SET fd_pin=? WHERE id=? AND user_id=? AND COALESCE(fd_pin,'')=''", (key, row["id"], uid))
            act = "moved"
    if act in ("moved", "already"):
        c.execute("INSERT OR IGNORE INTO mail_hw_items(mail_id, user_id, run_id, fkey, action, old_pin, from_email) "
                  "VALUES(?,?,?,?,?,?,?)", (row["id"], uid, rid, key, act, "", row["e"]))
    return act


def store_new(c, uid, parsed, raw_len, head, key, rid, to_fallback):
    """새 메일 저장 → (결과, 메일 번호). 저장 직전에 같은 메일이 생겼으면 그 메일로 판단."""
    from . import mail_store as MS
    subject = (parsed.get("subject") or "(제목 없음)").strip()
    body = (parsed.get("text") or "").strip() or MS._html_to_text(parsed.get("html") or "")
    h = MS._dedup_hash(parsed.get("message_id", ""), parsed.get("from_email", ""), subject, body)
    row = _find(c, uid, h)
    if row:
        return place_existing(c, uid, row, key, _rules_of(c, uid), rid), row["id"]
    mx = c.execute("SELECT COALESCE(MAX(id),0) FROM mail_messages").fetchone()[0] or 0
    mid, _own = MS.store_inbound(
        c, to_email=(parsed.get("to_email") or to_fallback), from_email=parsed.get("from_email", ""),
        from_name=parsed.get("from_name", ""), subject=parsed.get("subject", ""), text=parsed.get("text", ""),
        html=parsed.get("html", ""), cc=parsed.get("cc", ""), size=raw_len, owner_id=uid, run_ai=False,
        attachments=parsed.get("attachments"), message_id=parsed.get("message_id", ""), auth=parsed.get("auth"),
        reply_to=parsed.get("reply_to", ""), to_all=parsed.get("to_all", ""), raw_headers=parsed.get("raw_headers", ""),
        sent_at=parsed.get("sent_at", ""))
    if not mid:
        return "failed", None
    if mid <= mx:   # store_inbound 가 이미 있던 같은 메일 번호를 돌려줌
        row = c.execute("SELECT id, direction, is_deleted, COALESCE(fd_pin,'') AS pin, lower(COALESCE(from_email,'')) AS e, "
                        "COALESCE(received_at,'') AS ts FROM mail_messages WHERE id=? AND user_id=?", (mid, uid)).fetchone()
        return (place_existing(c, uid, dict(row), key, _rules_of(c, uid), rid) if row else "failed"), mid
    sets, args = ["is_read=?", "fd_pin=?"], [1 if head.get("seen") else 0, key]
    if head.get("idate"):
        sets.append("received_at=?")
        args.append(head["idate"])
    c.execute("UPDATE mail_messages SET " + ",".join(sets) + " WHERE id=? AND user_id=?", args + [mid, uid])
    c.execute("INSERT OR IGNORE INTO mail_hw_items(mail_id, user_id, run_id, fkey, action, old_pin, from_email) VALUES(?,?,?,?,?,?,?)",
              (mid, uid, rid, key, "saved", "", (parsed.get("from_email") or "").strip().lower()))
    return "saved", mid


# ─── 가져오기(뒤에서) ──────────────────────────────────────────────
def start(db_session, uid, addr, pw, host, folders, port=DEFAULT_PORT, wait=False):
    """가져오기 시작 → (ok, 메시지). folders = list_folders 의 항목 중 고른 것. 비밀번호는 이 작업 안에서만."""
    with _RUN_LOCK:
        if uid in _RUNNING:
            return False, "이미 가져오는 중입니다. 끝날 때까지 기다리시거나 「멈추기」를 눌러 주세요."
        ev = threading.Event()
        _RUNNING[uid] = ev
    try:
        with db_session() as c:
            ensure(c)
            c.execute("UPDATE mail_hw_runs SET state='stopped' WHERE user_id=? AND state='running'", (uid,))
            fl = [{"raw": f["raw"], "delim": f.get("delim", ""), "path": f["path"], "label": f["label"]} for f in folders]
            rid = c.execute("INSERT INTO mail_hw_runs(user_id, state, folders, cur) VALUES(?,?,?,?)",
                            (uid, "running", json.dumps(fl, ensure_ascii=False), "연결하는 중")).lastrowid
    except Exception:
        with _RUN_LOCK:
            _RUNNING.pop(uid, None)
        raise
    box = {"pw": pw}
    pw = None

    def _job():
        try:
            run(db_session, uid, rid, addr, box, host, port, fl, ev)
        finally:
            box.clear()   # 비밀번호 버림
            with _RUN_LOCK:
                _RUNNING.pop(uid, None)
    if wait:
        _job()
    else:
        threading.Thread(target=_job, name="mail-hw-%s" % uid, daemon=True).start()
    return True, rid


def run(db_session, uid, rid, addr, box, host, port, folders, ev):
    from . import mail_store as MS
    from .mail_import_outlook import _folder_for_path, disk_state
    try:
        M, _h = connect(host, port, addr, box.get("pw") or "")
    except Exception as e:
        with db_session() as c:
            _bump(c, rid, state="failed", cur="", msg=friendly_error(e))
        return
    box.clear()   # 로그인 뒤에는 비밀번호가 더 필요 없음
    state, msg = "done", ""
    try:
        for f in folders:
            if ev.is_set():
                break
            try:
                _select(M, f["raw"])
                uids = all_uids(M)
            except Exception as e:
                with db_session() as c:
                    _bump(c, rid, failed=0, msg="「%s」 폴더를 열지 못했습니다" % f["label"])
                continue
            with db_session() as c:
                key = _folder_for_path(c, uid, f["path"])
                _bump(c, rid, total=len(uids), cur=f["label"])
                ri = _rules_of(c, uid)
            if not key:
                with db_session() as c:
                    _bump(c, rid, failed=len(uids), msg="「%s」 폴더를 이음 메일에 만들지 못했습니다" % f["label"])
                continue
            for i in range(0, len(uids), HEAD_CHUNK):
                if ev.is_set():
                    break
                if not disk_state().get("ok", True):
                    state, msg = "stopped", "서버 남은 공간이 모자라 멈췄습니다(빅터에게 알려 주세요)"
                    ev.set()
                    break
                heads = fetch_heads(M, uids[i:i + HEAD_CHUNK])          # 하이웍스(네트워크) — DB 밖
                need, cnt = [], Counter()
                with db_session() as c:                                   # 짧게: 이미 있는 메일만 판단·옮김
                    for h in heads:
                        if h["mid"]:
                            row = _find(c, uid, MS._dedup_hash(h["mid"], "", "", ""))
                            if row:
                                cnt[place_existing(c, uid, row, key, ri, rid)] += 1
                                continue
                        need.append(h)
                    cnt["failed"] += max(0, len(uids[i:i + HEAD_CHUNK]) - len(heads))
                    _bump(c, rid, done=sum(cnt.values()), **cnt)
                for h in need:
                    if ev.is_set():
                        break
                    if h["size"] > MAX_MSG_BYTES:
                        with db_session() as c:
                            _bump(c, rid, done=1, big=1)
                        continue
                    try:
                        raw = fetch_raw(M, h["uid"])                      # 하이웍스(네트워크) — DB 밖
                        parsed = MS.parse_raw_email(raw) if raw else {}
                    except Exception:
                        raw, parsed = b"", {}
                    with db_session() as c:
                        if not parsed:
                            _bump(c, rid, done=1, failed=1)
                            continue
                        try:
                            act, _mid = store_new(c, uid, parsed, len(raw), h, key, rid, addr)
                        except Exception as e:
                            print("[MAIL-HW] 한 통 저장 건너뜀: %s" % type(e).__name__, flush=True)
                            act = "failed"
                        _bump(c, rid, done=1, **{act: 1})
        if ev.is_set() and state == "done":
            state = "stopped"
            msg = msg or "멈추기를 눌러 멈췄습니다"
    except Exception as e:
        state, msg = "stopped", "하이웍스 연결이 끊겼습니다(%s) — 「이어서 하기」를 눌러 주세요" % type(e).__name__
    finally:
        _logout(M)
        try:
            from . import mail_folders as MF
            MF._CACHE.pop(uid, None)
        except Exception:
            pass
        with db_session() as c:
            cur = c.execute("SELECT state FROM mail_hw_runs WHERE id=?", (rid,)).fetchone()
            if cur and cur["state"] == "stopped" and state == "done":
                state = "stopped"
            _bump(c, rid, state=state, cur="", msg=msg)
    print("[MAIL-HW] user=%s run=%s %s" % (uid, rid, state), flush=True)


# ─── 규칙 후보 ─────────────────────────────────────────────────────
def _folder_name(c, uid, key):
    if key.startswith("f") and key[1:].isdigit():
        r = c.execute("SELECT name FROM mail_folders WHERE id=? AND user_id=?", (int(key[1:]), uid)).fetchone()
        return r["name"] if r else ""
    return ""


def rule_candidates(c, uid) -> list:
    """가져온 폴더마다 보낸 사람(또는 회사 주소)이 RULE_RATIO 이상 · RULE_MIN 통 이상이면 후보 하나.
    [{id, fkey, folder, kind, pattern, n, total, status('new'|'have'|'other'), other_folder, more}]"""
    from . import mail_folders as MF
    ensure(c)
    MF.ensure(c)
    by = {}
    for r in c.execute("SELECT i.fkey, lower(COALESCE(m.from_email,'')) AS e FROM mail_hw_items i "
                       "JOIN mail_messages m ON m.id=i.mail_id AND m.user_id=i.user_id "
                       "WHERE i.user_id=? AND m.is_deleted=0 AND m.direction='in' AND COALESCE(m.fd_pin,'')=i.fkey",
                       (uid,)).fetchall():
        by.setdefault(r["fkey"], []).append(r["e"])
    free = MF._free_domains()
    raw = []
    for key, es in by.items():
        es = [e for e in es if "@" in e]
        n = len(es)
        if n < RULE_MIN:
            continue
        dc = Counter(MF._dom(e) for e in es)
        d, dn = dc.most_common(1)[0]
        if dn >= RULE_MIN and dn / float(n) >= RULE_RATIO and d not in free and d not in MF.OUR_DOMAINS:
            raw.append([key, "domain", d, dn, n, es])
            continue
        e, en = Counter(es).most_common(1)[0]
        if en >= RULE_MIN and en / float(n) >= RULE_RATIO:
            raw.append([key, "email", e, en, n, es])
    # 한 회사 주소가 여러 폴더 후보 = 회사 단위로는 못 나눔 → 사람 단위로(되면)
    dkeys = Counter(x[2] for x in raw if x[1] == "domain")
    out = []
    for key, kind, pat, cnt, n, es in raw:
        if kind == "domain" and dkeys[pat] > 1:
            e, en = Counter(es).most_common(1)[0]
            if not (en >= RULE_MIN and en / float(n) >= RULE_RATIO):
                continue
            kind, pat, cnt = "email", e, en
        have = c.execute("SELECT target FROM mail_move_rules WHERE user_id=? AND kind=? AND pattern=? ORDER BY id DESC",
                         (uid, kind, pat)).fetchall()
        tg = [h["target"] for h in have]
        status = "have" if key in tg else ("other" if tg else "new")
        other = ""
        if status == "other":
            other = _folder_name(c, uid, tg[0]) or ("일반" if tg[0] == "gen" else "다른 곳")
        # 「지난 메일도」를 고르면 더 옮겨질 메일 = 그 보낸 사람의 받은 메일 중 따로 정해 둔 자리(이 메일만)가 없는 것
        more = c.execute(
            "SELECT COUNT(*) FROM mail_messages WHERE user_id=? AND direction='in' AND is_deleted=0 "
            "AND COALESCE(is_blocked,0)=0 AND COALESCE(fd_pin,'')='' AND " +
            ("lower(from_email)=?" if kind == "email" else "lower(from_email) LIKE ?"),
            (uid, pat if kind == "email" else "%@" + pat)).fetchone()[0]
        out.append({"id": "%s|%s|%s" % (kind, pat, key), "fkey": key, "folder": _folder_name(c, uid, key),
                    "kind": kind, "pattern": pat, "n": cnt, "total": n, "status": status, "other_folder": other,
                    "more": max(0, int(more or 0))})
    out.sort(key=lambda x: x["folder"])
    return out


def save_rules(c, uid, picked, when) -> dict:
    """확인한 후보만 저장. picked = 후보 id 목록(화면 체크) · when = 'new'(지금부터 오는 메일만) | 'all'(지난 메일도).
    지금 다시 계산한 후보에 있는 것만 받음(화면에서 보낸 값을 그대로 믿지 않음)."""
    from . import mail_folders as MF
    if when not in ("new", "all"):
        return {"ok": False, "message": "언제부터 적용할지 골라 주세요(지금부터 오는 메일만 / 지난 메일도)."}
    cand = {x["id"]: x for x in rule_candidates(c, uid)}
    undo = {"add": [], "del": [], "pins": []}
    saved, have, skip = 0, 0, 0
    since = c.execute("SELECT datetime('now','localtime')").fetchone()[0] if when == "new" else ""
    for pid in picked or []:
        x = cand.get(pid)
        if not x:
            skip += 1
            continue
        if x["status"] == "have":
            have += 1
            continue
        MF._put_rule(c, uid, x["kind"], x["pattern"], x["fkey"], since, undo)
        saved += 1
    if saved:
        MF._save_undo(c, uid, undo, "hw%d" % int(time.time()))
        MF._CACHE.pop(uid, None)
    return {"ok": True, "saved": saved, "have": have, "skipped": skip}
