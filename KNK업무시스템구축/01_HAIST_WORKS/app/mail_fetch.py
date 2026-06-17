# -*- coding: utf-8 -*-
"""메일 '가져오기' — 하이웍스 등 외부 메일함의 새 메일을 KNK 메일로 당겨온다 (방법 B, 대표 지시 2026-06-14).

· 하이웍스는 POP3(pop3s.hiworks.com:995 SSL) 제공 → POP3 기본 지원. IMAP 도 지원(타 제공사 대비).
· 원본 삭제(DELE) 절대 안 함 → 하이웍스 원본 그대로(양수신·되돌리기 가능).
· 중복 방지: POP3 = UIDL(메시지 고유번호) seen 집합 / IMAP = last_uid 커서.
· '시작점 설정' = 지금까지 메일을 seen 으로 표시(안 가져옴) → 이후 새 메일만.
· 가져온 원문은 mail_store.parse_raw_email → store_inbound 로 적재(기존 받기 파이프 재사용).
· 비밀번호는 mail_send.encrypt(Fernet, KNK_MAIL_KEY)로 암호화 저장.
"""
from __future__ import annotations

import imaplib
import poplib

RUN_LIMIT = 100  # 한 번에 가져오는 최대 통수(폭주 방지). 더 있으면 다시 누르면 이어서.
poplib._MAXLINE = 1 << 20  # 긴 헤더 라인 대응


def _ensure_table(c):
    c.execute(
        """CREATE TABLE IF NOT EXISTS mail_fetch_accounts (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_user_id   INTEGER UNIQUE,
            label           TEXT,
            protocol        TEXT DEFAULT 'pop3',     -- pop3 / imap
            host            TEXT,
            port            INTEGER DEFAULT 995,
            use_ssl         INTEGER DEFAULT 1,
            username        TEXT,
            password_enc    TEXT,
            last_uid        INTEGER DEFAULT 0,       -- IMAP 진행 커서
            enabled         INTEGER DEFAULT 1,
            last_run        TEXT,
            last_status     TEXT,
            last_count      INTEGER DEFAULT 0,
            created_at      TEXT DEFAULT (datetime('now','localtime'))
        )"""
    )
    # 기존 테이블에 protocol 컬럼이 없으면 추가(이전 배포 호환)
    try:
        c.execute("ALTER TABLE mail_fetch_accounts ADD COLUMN protocol TEXT DEFAULT 'pop3'")
    except Exception:
        pass
    c.execute(
        """CREATE TABLE IF NOT EXISTS mail_fetch_seen (
            account_id  INTEGER,
            uidl        TEXT,
            fetched_at  TEXT DEFAULT (datetime('now','localtime')),
            PRIMARY KEY (account_id, uidl)
        )"""
    )


def get_account(c, owner_id):
    _ensure_table(c)
    r = c.execute("SELECT * FROM mail_fetch_accounts WHERE owner_user_id=?", (owner_id,)).fetchone()
    return dict(r) if r else None


def save_account(c, owner_id, *, protocol="pop3", host, port, use_ssl, username, password_enc=None, label=""):
    """비번(password_enc)이 None 이면 기존 비번 유지."""
    _ensure_table(c)
    host = (host or "").strip()
    username = (username or "").strip()
    protocol = (protocol or "pop3").strip().lower()
    if protocol not in ("pop3", "imap"):
        protocol = "pop3"
    try:
        port = int(port or (995 if protocol == "pop3" else 993))
    except Exception:
        port = 995 if protocol == "pop3" else 993
    ssl = 1 if use_ssl else 0
    exist = get_account(c, owner_id)
    if exist:
        if password_enc is None:
            c.execute("UPDATE mail_fetch_accounts SET protocol=?,host=?,port=?,use_ssl=?,username=?,label=? WHERE owner_user_id=?",
                      (protocol, host, port, ssl, username, label, owner_id))
        else:
            c.execute("UPDATE mail_fetch_accounts SET protocol=?,host=?,port=?,use_ssl=?,username=?,password_enc=?,label=? WHERE owner_user_id=?",
                      (protocol, host, port, ssl, username, password_enc, label, owner_id))
    else:
        c.execute("INSERT INTO mail_fetch_accounts(owner_user_id,protocol,host,port,use_ssl,username,password_enc,label) "
                  "VALUES(?,?,?,?,?,?,?,?)",
                  (owner_id, protocol, host, port, ssl, username, password_enc or "", label))


def set_status(c, owner_id, *, last_uid=None, status=None, count=None):
    sets = ["last_run=datetime('now','localtime')"]
    args = []
    if last_uid is not None:
        sets.append("last_uid=?"); args.append(int(last_uid))
    if status is not None:
        sets.append("last_status=?"); args.append((status or "")[:300])
    if count is not None:
        sets.append("last_count=?"); args.append(int(count))
    args.append(owner_id)
    c.execute("UPDATE mail_fetch_accounts SET " + ",".join(sets) + " WHERE owner_user_id=?", args)


def set_enabled(c, owner_id, enabled):
    """자동 가져오기 켜기/끄기 (enabled 1/0). 스케줄러는 enabled=1 계정만 수집."""
    _ensure_table(c)
    c.execute("UPDATE mail_fetch_accounts SET enabled=? WHERE owner_user_id=?",
              (1 if enabled else 0, owner_id))


def get_seen(c, account_id) -> set:
    _ensure_table(c)
    return {r[0] for r in c.execute("SELECT uidl FROM mail_fetch_seen WHERE account_id=?", (account_id,)).fetchall()}


def add_seen(c, account_id, uidls):
    _ensure_table(c)
    for u in uidls:
        try:
            c.execute("INSERT OR IGNORE INTO mail_fetch_seen(account_id, uidl) VALUES(?,?)", (account_id, u))
        except Exception:
            pass


# ── POP3 (하이웍스 기본) — 순수·DB 무관(run_in_threadpool 로 호출) ─────────────
def _pop3_connect(host, port, use_ssl, username, password, timeout=30):
    if use_ssl:
        M = poplib.POP3_SSL(host, int(port), timeout=timeout)
    else:
        M = poplib.POP3(host, int(port), timeout=timeout)
    M.user(username)
    M.pass_(password)
    return M


def pop3_test(host, port, use_ssl, username, password):
    try:
        M = _pop3_connect(host, port, use_ssl, username, password)
        try:
            n, _sz = M.stat()
        finally:
            try: M.quit()
            except Exception: pass
        return {"ok": True, "message": "연결 성공 — 받은편지함 %d통 확인" % n, "count": n}
    except Exception as e:
        return {"ok": False, "message": "연결 실패: %s: %s" % (type(e).__name__, e)}


def pop3_uidls(host, port, use_ssl, username, password):
    """현재 POP3 메일함의 모든 (msgnum, uidl). '시작점 설정'용."""
    try:
        M = _pop3_connect(host, port, use_ssl, username, password, timeout=25)
        try:
            resp, lines, _o = M.uidl()
            out = []
            for ln in lines:
                s = ln.decode("ascii", "replace").split()
                if len(s) >= 2:
                    out.append((int(s[0]), s[1]))
        finally:
            try: M.quit()
            except Exception: pass
        return {"ok": True, "items": out}
    except Exception as e:
        return {"ok": False, "message": "%s: %s" % (type(e).__name__, e)}


def pop3_collect(host, port, use_ssl, username, password, seen, limit=RUN_LIMIT):
    """seen(이미 본 uidl 집합)에 없는 새 메일만 수집(원본 삭제 안 함). 반환 messages:[(uidl, raw_bytes)]."""
    out = {"ok": False, "messages": [], "error": ""}
    seen = seen or set()
    try:
        M = _pop3_connect(host, port, use_ssl, username, password, timeout=40)
        try:
            resp, lines, _o = M.uidl()
            pairs = []
            for ln in lines:
                s = ln.decode("ascii", "replace").split()
                if len(s) >= 2:
                    pairs.append((int(s[0]), s[1]))
            new = [(num, uidl) for (num, uidl) in pairs if uidl not in seen]
            new.sort(key=lambda x: x[0])
            if limit and len(new) > limit:
                new = new[-limit:]   # 가장 최근(높은 msgnum) 위주
            for num, uidl in new:
                try:
                    resp2, mlines, _oc = M.retr(num)
                    raw = b"\r\n".join(mlines)
                    out["messages"].append((uidl, raw))
                except Exception:
                    pass
            out["ok"] = True
        finally:
            try: M.quit()    # QUIT — DELE 안 했으므로 원본 보존
            except Exception: pass
    except Exception as e:
        out["error"] = "%s: %s" % (type(e).__name__, e)
    return out


# ── IMAP (타 제공사용) — 순수 ─────────────────────────────────────────────────
def _imap_connect(host, port, use_ssl, username, password, timeout=25):
    M = imaplib.IMAP4_SSL(host, int(port), timeout=timeout) if use_ssl else imaplib.IMAP4(host, int(port), timeout=timeout)
    M.login(username, password)
    return M


def imap_test(host, port, use_ssl, username, password):
    try:
        M = _imap_connect(host, port, use_ssl, username, password)
        try:
            M.select("INBOX", readonly=True)
            typ, data = M.uid("search", None, "ALL")
            n = len(data[0].split()) if data and data[0] else 0
        finally:
            try: M.logout()
            except Exception: pass
        return {"ok": True, "message": "연결 성공 — 받은편지함 %d통 확인" % n, "count": n}
    except Exception as e:
        return {"ok": False, "message": "연결 실패: %s: %s" % (type(e).__name__, e)}


def imap_current_max_uid(host, port, use_ssl, username, password):
    try:
        M = _imap_connect(host, port, use_ssl, username, password, timeout=20)
        try:
            M.select("INBOX", readonly=True)
            typ, data = M.uid("search", None, "ALL")
            uids = [int(x) for x in data[0].split()] if data and data[0] else []
        finally:
            try: M.logout()
            except Exception: pass
        return {"ok": True, "uid": max(uids) if uids else 0}
    except Exception as e:
        return {"ok": False, "message": "%s: %s" % (type(e).__name__, e)}


def imap_collect(host, port, use_ssl, username, password, since_uid=0, limit=RUN_LIMIT):
    since_uid = int(since_uid or 0)
    out = {"ok": False, "messages": [], "max_uid": since_uid, "error": ""}
    try:
        M = _imap_connect(host, port, use_ssl, username, password, timeout=35)
        try:
            M.select("INBOX", readonly=True)
            typ, data = M.uid("search", None, "ALL")
            uids = sorted(int(x) for x in data[0].split()) if (data and data[0]) else []
            new = [u for u in uids if u > since_uid]
            if limit and len(new) > limit:
                new = new[-limit:]
            for u in new:
                typ, md = M.uid("fetch", str(u), "(RFC822)")
                if not md or not md[0] or not isinstance(md[0], tuple):
                    continue
                raw = md[0][1]
                if isinstance(raw, (bytes, bytearray)):
                    out["messages"].append((u, bytes(raw)))
                    if u > out["max_uid"]:
                        out["max_uid"] = u
            out["ok"] = True
        finally:
            try: M.logout()
            except Exception: pass
    except Exception as e:
        out["error"] = "%s: %s" % (type(e).__name__, e)
    return out


# ── 통합 디스패치 ─────────────────────────────────────────────────────────────
def test_connection(protocol, host, port, use_ssl, username, password):
    if (protocol or "pop3").lower() == "imap":
        return imap_test(host, port, use_ssl, username, password)
    return pop3_test(host, port, use_ssl, username, password)
