# -*- coding: utf-8 -*-
"""본문이 빈 채 저장된 메일 다시 채우기 시험 (11-23) — 빈 임시 DB · 가짜 자료만.
실행: 프로젝트 루트(01_HAIST_WORKS)에서  python _검증/mail_body_refill_test.py"""
import io
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
_so = sys.stdout
sys.stdout = io.StringIO()
import app.database as _db  # noqa: E402
_db.DB_PATH = os.path.join(tempfile.mkdtemp(prefix="knk_bodyrefill_"), "t.db")
_db.init_db()
from app import mail_store as ms  # noqa: E402
from app import mail_body_refill as mbr  # noqa: E402
sys.stdout = _so

P, F = [], []


def ck(n, ok):
    (P if ok else F).append(n)
    print(("  [OK] " if ok else "  [XX] ") + n)


MARK = "본문표시확인"
HTML = ("<html><head><meta charset='utf-8'></head><body><p>" + MARK + " 가짜</p></body></html>").encode("utf-8")
with _db.db_session() as c:
    c.execute("INSERT INTO users(id, login_id, name, role, is_active, password) VALUES(9101,'t_br','시험','ceo',1,'x')")
    c.execute("INSERT INTO users(id, login_id, name, role, is_active, password) VALUES(9102,'t_br2','남','member',1,'x')")


def put(uid, subj, text, html, atts):
    with _db.db_session() as c:
        mid, _o = ms.store_inbound(c, to_email="t@knknara.co.kr", from_email="no_reply@demo.example", from_name="가짜",
                                   subject=subj, text=text, html=html, owner_id=uid, run_ai=False, attachments=atts,
                                   message_id="br-%s@demo" % subj)
    return mid


def att(mime, data, inline=1, fn="image"):
    return {"filename": fn, "mime": mime, "size": len(data), "content_id": "", "inline": inline, "data": data}


a = put(9101, "a", "", "", [att("text/plain", (MARK + " 글").encode("utf-8")), att("text/html", HTML)])
b = put(9101, "b", "\n\n[첨부 1개: x.pdf]", "", [att("text/html", HTML), att("application/pdf", b"%PDF", 0, "x.pdf")])
cc = put(9101, "c", "보통 본문", "<p>보통</p>", [])                                     # 정상 — 안 건드림
d = put(9101, "d", "본문", "<p>본문</p>", [att("application/pdf", b"%PDF", 1, "mac.pdf")])  # 숨은 파일만
e = put(9101, "e", "", "", [att("image/png", b"\x89PNG", 1, "logo.png")])                # 그림만 — 대상 아님
o = put(9102, "o", "", "", [att("text/html", HTML)])                                     # 남의 메일 — 대상 아님

with _db.db_session() as c:
    mbr.ensure(c)
    n = mbr.count(c, 9101)
    b_old = c.execute("SELECT body_text FROM mail_messages WHERE id=?", (b,)).fetchone()[0]
ck("셈: 대상 메일 3통(a·b·d)", n["mails"] == 3)
ck("셈: 본문 되살림 2통(a·b) · 서식 2", n["body"] == 2 and n["html"] == 2)
ck("셈: 숨은 파일 1개(d)", n["files"] == 1 and n["file_mails"] == 1)
with _db.db_session() as c:
    ck("셈만으로는 자료 안 바뀜", (c.execute("SELECT body_html FROM mail_messages WHERE id=?", (a,)).fetchone()[0] or "") == "")

out = mbr.apply(_db.db_session, 9101)
ck("채움: 3통 · 본문 2 · 파일 1", out["mails"] == 3 and out["body"] == 2 and out["files"] == 1)
with _db.db_session() as c:
    g = lambda i: c.execute("SELECT body_text, body_html FROM mail_messages WHERE id=?", (i,)).fetchone()
    ck("a: HTML 본문 채움", MARK in (g(a)[1] or ""))
    ck("a: 글 본문 = 인라인 text/plain", MARK in (g(a)[0] or ""))
    ck("b: HTML 채움 · 글엔 첨부 표시 남김", MARK in (g(b)[1] or "") and "[첨부 1개: x.pdf]" in (g(b)[0] or "") and MARK in (g(b)[0] or ""))
    ck("c: 정상 메일 그대로", g(cc)[1] == "<p>보통</p>")
    ck("d: 숨은 PDF → 첨부로 보임", c.execute("SELECT is_inline FROM mail_attachments WHERE mail_id=? AND mime='application/pdf'", (d,)).fetchone()[0] == 0)
    ck("d: 본문 그대로", g(d)[1] == "<p>본문</p>")
    ck("e: 그림만 있는 메일 그대로", (g(e)[1] or "") == "")
    ck("남의 메일 안 건드림", (g(o)[1] or "") == "")
    n2 = mbr.count(c, 9101)
ck("다시 세면 0통", n2["mails"] == 0)
ck("다시 채워도 0통", mbr.apply(_db.db_session, 9101)["mails"] == 0)

with _db.db_session() as c:
    u = mbr.undo(c, 9101)
    ck("되돌리기 3통", u == 3)
    ck("되돌린 뒤 a 본문 다시 빈 값", (c.execute("SELECT body_html FROM mail_messages WHERE id=?", (a,)).fetchone()[0] or "") == "")
    ck("되돌린 뒤 b 글 원래 값", c.execute("SELECT body_text FROM mail_messages WHERE id=?", (b,)).fetchone()[0] == b_old)
    ck("되돌린 뒤 d 파일 다시 숨김", c.execute("SELECT is_inline FROM mail_attachments WHERE mail_id=? AND mime='application/pdf'", (d,)).fetchone()[0] == 1)
    ck("되돌린 뒤 다시 3통 셈", mbr.count(c, 9101)["mails"] == 3)
    ck("되돌림 표 비움", c.execute("SELECT COUNT(*) FROM mail_body_refill_bak").fetchone()[0] == 0)
print("결과: %d 통과 / %d 실패" % (len(P), len(F)))
