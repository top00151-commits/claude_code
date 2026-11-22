# -*- coding: utf-8 -*-
"""보낸 사람 주소 — From 에 주소가 없는 메일 · 이름이 주소 칸에 든 예전 메일 (가짜 자료 · 임시 DB · 운영 무접촉).
대표 11-22 「보낸 사람 메일 주소가 확인 안 되는 게 있어 — 근본적인 원인을 찾아서 해결」
사용: py -3.13 _검증/mail_from_fallback_test.py"""
import io
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
os.chdir(ROOT)
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
_so = sys.stdout
sys.stdout = io.StringIO()
try:
    import app.database as _db
    _db.DB_PATH = os.path.join(tempfile.mkdtemp(prefix="knk_fromfb_"), "t.db")
    _db.init_db()
    from app import mail_store as ms
    from app import mail_from_refill as mfr
finally:
    sys.stdout = _so
from email.header import Header  # noqa: E402

P = F = 0


def check(name, cond, extra=""):
    global P, F
    if cond:
        P += 1
        print("  [PASS]", name)
    else:
        F += 1
        print("  [FAIL]", name, "<-", str(extra)[:400])


NM = Header("홍길동", "euc-kr").encode()


def parse(hdrs):
    raw = ("\r\n".join(hdrs) + "\r\nSubject: t\r\nMessage-ID: <x@demo>\r\n\r\nbody").encode("utf-8")
    p = ms.parse_raw_email(raw)
    return (p.get("from_name") or ""), (p.get("from_email") or "")


print("== 1. From 에 주소가 없을 때 다른 머리에서 ==")
check("From 이름만 + Sender → 이름 홍길동 · 주소 = Sender", parse(["From: " + NM, "Sender: hong@demo-sender.example"]) == ("홍길동", "hong@demo-sender.example"))
check("From 이름만 + Reply-To → 주소 = Reply-To", parse(["From: " + NM, "Reply-To: reply@demo-r.example"]) == ("홍길동", "reply@demo-r.example"))
check("From 이름만 + Return-Path → 주소 = Return-Path", parse(["From: " + NM, "Return-Path: <rp@demo-rp.example>"]) == ("홍길동", "rp@demo-rp.example"))
check("순서 = Sender → Reply-To → Return-Path", parse(["From: " + NM, "Return-Path: <rp@demo.example>", "Reply-To: r@demo.example", "Sender: s@demo.example"])[1] == "s@demo.example")
check("반송 주소(mailer-daemon) 는 안 씀", parse(["From: " + NM, "Return-Path: <MAILER-DAEMON@demo.example>"])[1] == "")
check("From <이름> 꼴 + Return-Path", parse(["From: <" + NM + ">", "Return-Path: <rp@demo-rp.example>"]) == ("홍길동", "rp@demo-rp.example"))
check("주소를 어디서도 못 찾으면 이름은 살리고 주소는 빈칸(이름을 주소 칸에 넣지 않음)", parse(["From: " + NM]) == ("홍길동", ""))
check("From 에 주소가 있으면 그대로(다른 머리 안 봄)", parse(["From: " + NM + " <hong@demo.example>", "Sender: other@demo.example"]) == ("홍길동", "hong@demo.example"))
check("꺾쇠 없이 「이름 주소」 → 주소만 주소 칸 · 이름만 이름 칸(덩어리 주소 막음)", parse(["From: " + NM + " hong@demo.example"]) == ("홍길동", "hong@demo.example"))
check("이름에 쉼표(1차 고침 그대로)", parse(["From: " + Header("홍길동, KNK VINA", "utf-8").encode() + " <h@demo.example>"]) == ("홍길동, KNK VINA", "h@demo.example"),
      parse(["From: " + Header("홍길동, KNK VINA", "utf-8").encode() + " <h@demo.example>"]))

print("== 2. 예전 메일 — 이름이 주소 칸에 든 것 ==")
with _db.db_session() as c:
    c.execute("INSERT INTO users(id, login_id, name, role, is_active, password) VALUES(9301,'t9301','시험','member',1,'x')")
    ms._ensure_security_cols(c)
    ms._ensure_dedup_cols(c)
    c.execute("INSERT INTO mail_messages(id, user_id, direction, from_email, from_name, subject, dedup_hash) VALUES(80001,9301,'in','홍길동','', '예전 메일', 'h1')")
    c.execute("INSERT INTO mail_messages(id, user_id, direction, from_email, from_name, subject, dedup_hash) VALUES(80002,9301,'in','','', '빈 주소', 'h2')")
    c.execute("INSERT INTO mail_messages(id, user_id, direction, from_email, from_name, subject, dedup_hash) VALUES(80003,9301,'in','ok@demo.example','정상', '정상', 'h3')")
    m1 = ms.get_mail(c, 80001, 9301)
    m3 = ms.get_mail(c, 80003, 9301)
    tg = mfr.targets(c, 9301)
check("화면·답장용 읽기: 주소 칸의 이름 → 이름으로 · 주소는 빈칸(답장 받는 사람에 「홍길동」이 들어가지 않게)",
      m1["from_name"] == "홍길동" and m1["from_email"] == "" and m1.get("from_bad") == "홍길동", m1 and {k: m1[k] for k in ("from_name", "from_email")})
check("정상 메일은 그대로", m3["from_email"] == "ok@demo.example" and m3["from_name"] == "정상")
check("다시 채우기 대상 = 빈 주소 + 주소 칸에 @ 없는 메일", set(tg["by_hash"].values()) == {80001, 80002}, tg)
with _db.db_session() as c:
    n = mfr.apply(c, 9301, {80001: ("홍길동", "hong@demo.example")}, "b1")
    r = c.execute("SELECT from_email, from_name FROM mail_messages WHERE id=80001").fetchone()
check("다시 채우기 = 주소 칸에 이름이 든 메일도 채움(되돌림 표에 예전 값)", n == 1 and r["from_email"] == "hong@demo.example" and r["from_name"] == "홍길동", dict(r))
with _db.db_session() as c:
    u = mfr.undo(c, 9301)
    r = c.execute("SELECT from_email FROM mail_messages WHERE id=80001").fetchone()
check("↺ 되돌리기 = 예전 값(이름) 그대로", u == 1 and r["from_email"] == "홍길동", dict(r))

print("\n결과: %d 통과 / %d 실패" % (P, F))
sys.exit(1 if F else 0)
