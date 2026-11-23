# -*- coding: utf-8 -*-
"""본문이 빈 채 저장된 메일 다시 채우기 (대표 2026-11-23 「이미 받아 둔 메일 중 본문이 빈 것을 운영 DB 에 다시 채워」)

까닭: 11-23 고치기 전 해석기는 본문(글·HTML) 부분에 'Content-Disposition: inline' 이 붙은 메일(애플 영수증 등)의 본문을
      「인라인 첨부」로 저장해 본문 칸이 비었다. 그 부분은 서버(mail_attachments)에 그대로 남아 있다.
      같은 까닭으로 inline 표시가 붙은 진짜 파일(맥·아이폰 메일의 PDF 등)은 첨부 목록에서 숨어 있었다.

방법(내 메일만 · 하이웍스에 다시 접속하지 않음 · 서버에 남은 부분만 씀):
  ① 대상 = 내 받은 메일 중 (HTML 본문이 비고 인라인 text/html·text/plain 이 남은 것) 또는 (그림·본문 글이 아닌 인라인 파일이 숨은 것)
  ② 본문 = mail_store.view_body_fallback (보기 화면과 같은 규칙) · 숨은 파일 = 첨부로 보이게(is_inline 0)
  ③ 바꾸기 전 값(본문 글·HTML·바꾼 첨부 번호)을 되돌림 표(mail_body_refill_bak)에 남긴 뒤 바꿈
  ↺ 되돌리기 = 마지막 묶음을 되돌림 표의 값으로
셈만(dry) 하면 숫자만 돌려준다(제목·내용은 돌려주지 않음).
"""
import time

from . import mail_store as _ms


def ensure(c):
    c.execute("""CREATE TABLE IF NOT EXISTS mail_body_refill_bak (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        batch TEXT NOT NULL,
        user_id INTEGER NOT NULL,
        mail_id INTEGER NOT NULL,
        old_text TEXT, old_html TEXT,
        body_changed INTEGER DEFAULT 0,
        flipped_att_ids TEXT DEFAULT '',
        created_at TEXT DEFAULT (datetime('now','localtime')))""")


_CAND_SQL = (
    "SELECT m.id, m.body_text, m.body_html FROM mail_messages m "
    "WHERE m.user_id=? AND m.direction='in' AND m.is_deleted=0 AND ("
    " (COALESCE(m.body_html,'')='' AND COALESCE(m.html_sha,'')='' AND EXISTS(SELECT 1 FROM mail_attachments a WHERE a.mail_id=m.id AND a.is_inline=1 "
    "   AND lower(COALESCE(a.mime,'')) IN ('text/html','text/plain')))"
    " OR EXISTS(SELECT 1 FROM mail_attachments a WHERE a.mail_id=m.id AND a.is_inline=1 "
    "   AND lower(COALESCE(a.mime,'')) NOT LIKE 'image/%' AND lower(COALESCE(a.mime,'')) NOT IN ('text/html','text/plain'))"
    ") ORDER BY m.id")


def _plan(c, user_id):
    """[(mail_id, old_text, old_html, new_text, new_html, body_changed, [파일로 보일 첨부 번호])]"""
    from .mail_body_pack import ensure as _pk_ensure
    _pk_ensure(c)   # 11-23 html_sha 칸(본문 정리)이 아직 없을 수 있음
    out = []
    for r in c.execute(_CAND_SQL, (int(user_id),)).fetchall():
        m = {"id": r["id"], "body_text": r["body_text"] or "", "body_html": r["body_html"] or ""}
        atts = _ms.list_attachments(c, r["id"])
        nh, nt, used = _ms.view_body_fallback(c, m, atts)
        files = [a["id"] for a in atts if _ms.inline_is_file(a)]
        changed = bool(used) and (nh != m["body_html"] or nt != m["body_text"])
        if changed or files:
            out.append((r["id"], m["body_text"], m["body_html"], nt, nh, 1 if changed else 0, files))
    return out


def count(c, user_id) -> dict:
    """숫자만 — 본문을 되살릴 메일 · 그중 서식(HTML) · 숨은 파일 첨부가 보이게 될 메일·파일 수."""
    p = _plan(c, user_id)
    return {"mails": len(p),
            "body": sum(1 for x in p if x[5]),
            "html": sum(1 for x in p if x[5] and (x[4] or "").strip()),
            "file_mails": sum(1 for x in p if x[6]),
            "files": sum(len(x[6]) for x in p)}


def apply(db_session, user_id) -> dict:
    """읽기(파일 읽기 포함)는 짧은 세션에서 먼저 → 쓰기는 한 번에 짧게(쓰기 잠금을 쥔 채 파일을 읽지 않음)."""
    with db_session() as c:
        ensure(c)
        plan = _plan(c, user_id)
    if not plan:
        return {"mails": 0, "body": 0, "files": 0, "batch": ""}
    batch = time.strftime("%Y%m%d-%H%M%S")
    nb = nf = 0
    with db_session() as c:
        for mid, ot, oh, nt, nh, ch, files in plan:
            c.execute("INSERT INTO mail_body_refill_bak(batch, user_id, mail_id, old_text, old_html, body_changed, flipped_att_ids) "
                      "VALUES(?,?,?,?,?,?,?)", (batch, int(user_id), mid, ot, oh, ch, ",".join(str(i) for i in files)))
            if ch:
                c.execute("UPDATE mail_messages SET body_text=?, body_html=? WHERE id=? AND user_id=?", (nt, nh, mid, int(user_id)))
                nb += 1
            for aid in files:
                c.execute("UPDATE mail_attachments SET is_inline=0 WHERE id=? AND mail_id=?", (aid, mid))
                nf += 1
    return {"mails": len(plan), "body": nb, "files": nf, "batch": batch}


def undo(c, user_id) -> int:
    """마지막 묶음 되돌림 — 되돌린 메일 수."""
    ensure(c)
    r = c.execute("SELECT batch FROM mail_body_refill_bak WHERE user_id=? ORDER BY id DESC LIMIT 1", (int(user_id),)).fetchone()
    if not r:
        return 0
    batch = r["batch"]
    rows = c.execute("SELECT mail_id, old_text, old_html, body_changed, flipped_att_ids FROM mail_body_refill_bak "
                     "WHERE user_id=? AND batch=?", (int(user_id), batch)).fetchall()
    for x in rows:
        if x["body_changed"]:
            c.execute("UPDATE mail_messages SET body_text=?, body_html=? WHERE id=? AND user_id=?",
                      (x["old_text"], x["old_html"], x["mail_id"], int(user_id)))
        for aid in [s for s in (x["flipped_att_ids"] or "").split(",") if s.strip().isdigit()]:
            c.execute("UPDATE mail_attachments SET is_inline=1 WHERE id=? AND mail_id=?", (int(aid), x["mail_id"]))
    c.execute("DELETE FROM mail_body_refill_bak WHERE user_id=? AND batch=?", (int(user_id), batch))
    return len(rows)
