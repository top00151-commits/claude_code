"""받은 시각 바로잡기 — 11-24 대표 「메일 받은 일자가 실제 받은 날짜·시간이 아니고 메일을 연결해서 처음 끌고 온 날짜·시간으로
기록되어 있어 · 아주 중요한 문제 · 꼭 실제 메일이 도착한 날짜와 시간으로」.

까닭: 메일을 저장할 때 받은 시각(received_at) 칸이 「저장한 때」(DB 기본값 = 지금)로 채워졌다.
  평소 받기(1~2분마다)는 거의 같지만, 계정을 처음 연결해 「지난 메일 가져오기」로 들어온 메일은 모두 가져온 날짜가 됐다.
  → 새로 받는 메일은 mail_store.arrival_at(맨 위 Received → 없으면 Date)로 저장(같은 날 고침).

이미 저장된 메일: 서버에 남은 원문 머리(mail_raw_headers · Date 포함) 또는 원래 날짜(sent_at = Date 머리)로 고친다.
  · 받은 메일(direction='in')만 · 지금 받은 시각이 원래 시각보다 30분 넘게 늦은 것만(평소 받은 메일은 그대로)
  · 고치기 전 값을 되돌림 표(mail_recv_fix_bak)에 묶음 번호와 함께 남김 → undo 로 그대로 되돌림
  · 돌려주는 값 = 숫자만(제목·내용 안 돌려줌)
"""
from __future__ import annotations

import datetime as _dt

GAP_MIN = 30


def ensure(c) -> None:
    c.execute("""CREATE TABLE IF NOT EXISTS mail_recv_fix_bak(
        mail_id INTEGER NOT NULL,
        batch TEXT NOT NULL,
        user_id INTEGER,
        old_received TEXT,
        new_received TEXT,
        PRIMARY KEY(mail_id, batch))""")


def _cands(c, uid=None):
    """(mail_id, user_id, 지금 받은 시각, 고칠 시각) — 30분 넘게 늦게 적힌 받은 메일."""
    from .mail_store import arrival_at, _ensure_raw_hdr
    try:
        from .mail_body_pack import ensure as _pe, has_sent_at
        _pe(c)
        has_sent = has_sent_at(c)
    except Exception:
        has_sent = False
    _ensure_raw_hdr(c)
    sql = ("SELECT m.id, m.user_id, m.received_at, %s AS sent_at, COALESCE(h.hdr,'') AS hdr "
           "FROM mail_messages m LEFT JOIN mail_raw_headers h ON h.mail_id=m.id "
           "WHERE m.direction='in'" % ("COALESCE(m.sent_at,'')" if has_sent else "''"))
    args = ()
    if uid:
        sql += " AND m.user_id=?"
        args = (uid,)
    out = []
    for r in c.execute(sql, args).fetchall():
        hdr = r["hdr"] or ""
        new = arrival_at(hdr, r["sent_at"] or "") if (hdr or r["sent_at"]) else ""
        if not new:
            continue
        try:
            cur = _dt.datetime.strptime((r["received_at"] or "")[:19], "%Y-%m-%d %H:%M:%S")
            nt = _dt.datetime.strptime(new, "%Y-%m-%d %H:%M:%S")
        except Exception:
            continue
        if cur - nt > _dt.timedelta(minutes=GAP_MIN):
            out.append((r["id"], r["user_id"], r["received_at"], new))
    return out


def count(c, uid=None) -> dict:
    """고칠 메일 수 — 사람별 통수(사람 번호만) · 자료 안 바꿈."""
    ensure(c)
    per = {}
    for _mid, u, _o, _n in _cands(c, uid):
        per[u] = per.get(u, 0) + 1
    return {"total": sum(per.values()), "users": len(per),
            "per_user": [{"user_id": k, "n": v} for k, v in sorted(per.items(), key=lambda x: -x[1])]}


def apply(c, uid=None) -> dict:
    ensure(c)
    batch = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    rows = _cands(c, uid)
    for mid, u, old, new in rows:
        c.execute("INSERT OR REPLACE INTO mail_recv_fix_bak(mail_id, batch, user_id, old_received, new_received) "
                  "VALUES(?,?,?,?,?)", (mid, batch, u, old, new))
        c.execute("UPDATE mail_messages SET received_at=? WHERE id=?", (new, mid))
    return {"fixed": len(rows), "users": len({r[1] for r in rows}), "batch": batch}


def undo(c, batch="") -> int:
    """마지막(또는 고른) 묶음을 그대로 되돌림."""
    ensure(c)
    if not batch:
        r = c.execute("SELECT MAX(batch) AS b FROM mail_recv_fix_bak").fetchone()
        batch = (r["b"] if r else "") or ""
    if not batch:
        return 0
    n = 0
    for r in c.execute("SELECT mail_id, old_received FROM mail_recv_fix_bak WHERE batch=?", (batch,)).fetchall():
        n += c.execute("UPDATE mail_messages SET received_at=? WHERE id=?", (r["old_received"], r["mail_id"])).rowcount
    c.execute("DELETE FROM mail_recv_fix_bak WHERE batch=?", (batch,))
    return n
