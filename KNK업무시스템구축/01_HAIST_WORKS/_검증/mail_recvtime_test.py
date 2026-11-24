# -*- coding: utf-8 -*-
"""받은 시각 = 메일 서버에 도착한 시각 시험 — 가짜 메일·임시 DB(운영 무접촉 · 실제 메일 없음).
대표 11-24 「메일 받은 일자가 실제 받은 날짜·시간이 아니고 메일을 연결해서 처음 끌고 온 날짜·시간으로 기록 · 꼭 실제 도착한 날짜와 시간으로」.
① 새로 받는 메일 = 맨 위 Received 시각 · 없으면 Date · 둘 다 없거나 이상하면 저장 시각
② 이미 저장된 메일 바로잡기(/mail/recv-fix) = 숫자만 · 30분 넘게 늦은 것만 · 되돌림 표 · undo · 관리자만
사용: py -3.13 _검증/mail_recvtime_test.py"""
import datetime as dt
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
    _TMP = tempfile.mkdtemp(prefix="knk_mrecv_")
    _db.DB_PATH = os.path.join(_TMP, "t.db")
    _db.init_db()
    import app.main as m
    from app import mail_store as ms
    from app import mail_recv_fix as mrf
finally:
    sys.stdout = _so
from starlette.testclient import TestClient  # noqa: E402

P = F = 0


def check(name, cond, extra=""):
    global P, F
    if cond:
        P += 1
        print("  [PASS]", name)
    else:
        F += 1
        print("  [FAIL]", name, "<-", str(extra)[:400])


U = 9301
with _db.db_session() as c:
    c.execute("INSERT INTO users(id, login_id, name, role, is_active, password) VALUES(9301,'t9301','가짜직원','member',1,'x')")


def raw(subject, date_hdr, recv_hdr=None):
    h = ["Return-Path: <a@fake.example>"]
    if recv_hdr:
        h += ["Received: from mx.fake.example (mx [10.0.0.1])", "\tby pop.fake.example with ESMTP id x1;", "\t" + recv_hdr,
              "Received: from out.fake.example by mx.fake.example; Mon, 1 Jan 2024 00:00:00 +0900"]
    h += ["From: =?utf-8?b?6rCA7KecIOuztOuCuOydtA==?= <a@fake.example>", "To: t9301@knknara.co.kr",
          "Subject: " + subject, "Message-ID: <%s@fake>" % subject]
    if date_hdr:
        h += ["Date: " + date_hdr]
    h += ["MIME-Version: 1.0", "Content-Type: text/plain; charset=utf-8", "", "가짜 본문 " + subject, ""]
    return "\r\n".join(h).encode("utf-8")


def store(b):
    p = ms.parse_raw_email(b)
    with _db.db_session() as c:
        mid, _o = ms.store_inbound(c, to_email="t9301@knknara.co.kr", from_email=p["from_email"], from_name=p["from_name"],
                                   subject=p["subject"], text=p["text"], owner_id=U, run_ai=False,
                                   message_id=p.get("message_id", ""), raw_headers=p.get("raw_headers", ""),
                                   sent_at=p.get("sent_at", ""))
        return c.execute("SELECT received_at FROM mail_messages WHERE id=?", (mid,)).fetchone()["received_at"], mid


def kst(s):
    """+0900 시각 글 → 이 PC 시간대의 'YYYY-MM-DD HH:MM:SS'(서버와 같은 기준)."""
    from email.utils import parsedate_to_datetime
    return parsedate_to_datetime(s).astimezone().replace(tzinfo=None).strftime("%Y-%m-%d %H:%M:%S")


print("== 1. 새로 받는 메일 ==")
R1 = "Thu, 12 Nov 2026 09:31:07 +0900"
D1 = "Thu, 12 Nov 2026 09:30:55 +0900"
ra, m1 = store(raw("r1", D1, R1))
check("Received 있음 → 맨 위 Received 시각(도착 시각)", ra == kst(R1), ra)
ra, m2 = store(raw("r2", D1))
check("Received 없음 → Date 시각", ra == kst(D1), ra)
now = dt.datetime.now()
ra, m3 = store(raw("r3", ""))
t3 = dt.datetime.strptime(ra[:19], "%Y-%m-%d %H:%M:%S")
check("둘 다 없음 → 저장 시각(지금)", abs((t3 - now).total_seconds()) < 120, ra)
ra, m4 = store(raw("r4", "Mon, 1 Jan 2099 00:00:00 +0900", "Mon, 1 Jan 2099 00:00:00 +0900"))
t4 = dt.datetime.strptime(ra[:19], "%Y-%m-%d %H:%M:%S")
check("이상한 미래 시각 → 쓰지 않고 저장 시각", abs((t4 - now).total_seconds()) < 120, ra)
ra, m5 = store(raw("r5", "Mon, 2 Nov 2026 14:05:00 +0700"))
check("베트남(+0700) Date → 서버 시각으로 바꿔 적음", ra == kst("Mon, 2 Nov 2026 14:05:00 +0700"), ra)
with _db.db_session() as c:
    _order = [r["id"] for r in c.execute("SELECT id FROM mail_messages WHERE user_id=? ORDER BY received_at DESC, id DESC", (U,))]
check("목록 정렬 = 도착 시각 순(11-12 메일이 11-02 보다 위 · 늦게 저장한 11-02 메일이 위로 안 옴)",
      _order.index(m1) < _order.index(m5), _order)

print("== 2. 이미 저장된 메일 바로잡기 ==")
with _db.db_session() as c:
    # 예전 방식처럼 「가져온 때」로 잘못 적힌 메일 둘 + 평소 받기(5분 늦음) 하나
    c.execute("UPDATE mail_messages SET received_at='2026-11-24 10:00:00' WHERE id IN (?,?)", (m1, m2))
    c.execute("UPDATE mail_messages SET received_at=datetime(?, '+5 minutes') WHERE id=?", (kst("Mon, 2 Nov 2026 14:05:00 +0700"), m5))
    m5_before = c.execute("SELECT received_at FROM mail_messages WHERE id=?", (m5,)).fetchone()["received_at"]
    cnt = mrf.count(c)
check("세기 = 30분 넘게 늦은 2통만(평소 받기 5분 늦음은 그대로) · 사람 번호·통수만", cnt["total"] == 2 and cnt["per_user"] == [{"user_id": U, "n": 2}], cnt)
_UID = {"role": "member"}
m.get_user = lambda req: {"id": U, "role": _UID["role"], "name": "가짜", "team_id": None, "team_name": ""}
k = TestClient(m.app, base_url="http://127.0.0.1:5051", raise_server_exceptions=False, follow_redirects=False)
k.headers.update({"host": "works.knknara.co.kr", "x-forwarded-proto": "https"})
check("직원은 세기·고치기 못 함(관리자만)", k.get("/mail/recv-fix").status_code == 403 and k.post("/mail/recv-fix").status_code == 403)
_UID["role"] = "ceo"
j = k.get("/mail/recv-fix").json()
check("관리자 세기 = 숫자만(제목 없음)", j.get("ok") and j.get("total") == 2 and "r1" not in str(j), j)
j = k.post("/mail/recv-fix").json()
with _db.db_session() as c:
    g = {r["id"]: r["received_at"] for r in c.execute("SELECT id, received_at FROM mail_messages WHERE id IN (?,?,?)", (m1, m2, m5))}
    bak = c.execute("SELECT COUNT(*) FROM mail_recv_fix_bak").fetchone()[0]
check("고치기 → 2통이 원래 시각(Date)으로 · 되돌림 표 2줄", j.get("fixed") == 2 and g[m1] == kst(D1) and g[m2] == kst(D1) and bak == 2, (j, g, bak))
check("평소 받은 메일은 그대로", g[m5] == m5_before, g)
check("다시 세면 0", k.get("/mail/recv-fix").json().get("total") == 0)
j = k.post("/mail/recv-fix", data={"undo": "1"}).json()
with _db.db_session() as c:
    g = {r["id"]: r["received_at"] for r in c.execute("SELECT id, received_at FROM mail_messages WHERE id IN (?,?)", (m1, m2))}
check("되돌리기 → 고치기 전 값 그대로", j.get("undone") == 2 and g[m1] == "2026-11-24 10:00:00" and g[m2] == "2026-11-24 10:00:00", (j, g))

print("결과: %d 통과 · %d 실패" % (P, F))
sys.exit(1 if F else 0)
