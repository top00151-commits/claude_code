# -*- coding: utf-8 -*-
"""IMAP '가져오기' — 하이웍스 등 외부 IMAP 메일함의 새 메일을 KNK 메일로 당겨온다 (방법 B, 대표 지시 2026-06-14).

· 읽기전용(readonly) 접속 → 하이웍스 원본은 절대 바뀌지 않음(양수신 안전).
· 계정별 last_uid 커서로 중복 방지. '시작점 설정'으로 '지금부터' 새 메일만(과거 폭주 방지).
· 가져온 원문은 mail_store.parse_raw_email → store_inbound 로 KNK 메일함에 적재(기존 받기 파이프 재사용).
· 비밀번호는 mail_send.encrypt(Fernet, KNK_MAIL_KEY)로 암호화 저장. (앱 비밀번호 권장)
"""
from __future__ import annotations

import imaplib

# 한 번에 가져오는 최대 통수(폭주 방지). 더 있으면 '지금 가져오기'를 다시 누르면 이어서 가져옴.
RUN_LIMIT = 100


def _ensure_table(c):
    c.execute(
        """CREATE TABLE IF NOT EXISTS mail_fetch_accounts (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_user_id   INTEGER UNIQUE,          -- 가져온 메일을 넣을 KNK 사용자
            label           TEXT,
            host            TEXT,
            port            INTEGER DEFAULT 993,
            use_ssl         INTEGER DEFAULT 1,
            username        TEXT,
            password_enc    TEXT,                    -- Fernet 암호화
            last_uid        INTEGER DEFAULT 0,       -- 진행 커서(이 UID 초과만 가져옴)
            enabled         INTEGER DEFAULT 1,
            last_run        TEXT,
            last_status     TEXT,
            last_count      INTEGER DEFAULT 0,
            created_at      TEXT DEFAULT (datetime('now','localtime'))
        )"""
    )


def get_account(c, owner_id):
    _ensure_table(c)
    r = c.execute("SELECT * FROM mail_fetch_accounts WHERE owner_user_id=?", (owner_id,)).fetchone()
    return dict(r) if r else None


def save_account(c, owner_id, *, host, port, use_ssl, username, password_enc=None, label=""):
    """비번(password_enc)이 None 이면 기존 비번 유지(미입력 저장 시 비번 안 지워지게)."""
    _ensure_table(c)
    host = (host or "").strip()
    username = (username or "").strip()
    try:
        port = int(port or 993)
    except Exception:
        port = 993
    ssl = 1 if use_ssl else 0
    exist = get_account(c, owner_id)
    if exist:
        if password_enc is None:
            c.execute("UPDATE mail_fetch_accounts SET host=?,port=?,use_ssl=?,username=?,label=? WHERE owner_user_id=?",
                      (host, port, ssl, username, label, owner_id))
        else:
            c.execute("UPDATE mail_fetch_accounts SET host=?,port=?,use_ssl=?,username=?,password_enc=?,label=? WHERE owner_user_id=?",
                      (host, port, ssl, username, password_enc, label, owner_id))
    else:
        c.execute("INSERT INTO mail_fetch_accounts(owner_user_id,host,port,use_ssl,username,password_enc,label) "
                  "VALUES(?,?,?,?,?,?,?)",
                  (owner_id, host, port, ssl, username, password_enc or "", label))


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


# ── IMAP 접속(순수·DB 무관 — main.py 에서 run_in_threadpool 로 호출) ────────────
def _connect(host, port, use_ssl, username, password, timeout=25):
    if use_ssl:
        M = imaplib.IMAP4_SSL(host, int(port), timeout=timeout)
    else:
        M = imaplib.IMAP4(host, int(port), timeout=timeout)
    M.login(username, password)
    return M


def test_connection(host, port, use_ssl, username, password):
    """연결·로그인·받은편지함 통수 확인."""
    try:
        M = _connect(host, port, use_ssl, username, password)
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


def current_max_uid(host, port, use_ssl, username, password):
    """현재 받은편지함의 최대 UID(=지금까지의 모든 메일). '시작점 설정'(여기까지는 안 가져옴)용."""
    try:
        M = _connect(host, port, use_ssl, username, password, timeout=20)
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
    """since_uid 초과 UID 의 새 메일 raw 를 수집(읽기전용). limit>0 이면 가장 최근 limit 개만.
    반환: {ok, messages:[(uid, raw_bytes)...], max_uid, error}."""
    since_uid = int(since_uid or 0)
    out = {"ok": False, "messages": [], "max_uid": since_uid, "error": ""}
    try:
        M = _connect(host, port, use_ssl, username, password, timeout=35)
        try:
            M.select("INBOX", readonly=True)
            typ, data = M.uid("search", None, "ALL")
            uids = sorted(int(x) for x in data[0].split()) if (data and data[0]) else []
            new = [u for u in uids if u > since_uid]
            if limit and len(new) > limit:
                new = new[-limit:]   # 가장 최근 것 위주
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
