# -*- coding: utf-8 -*-
"""✓ 피싱 아님(이 보낸 사람 믿기 · 나에게만) 시험 — 가짜 직원·가짜 메일·임시 DB(운영 무접촉 · 실제 메일 없음).
대표 11-26 「피싱이 아닌 것으로 확정하는 방법은 없어? 의심을 해지해야 다음부터 정상적으로 들어오지」 · 「오른쪽 두 아이콘 줄이 틀어졌어」
사용: py -3.13 _검증/mail_not_phish_test.py"""
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
    _TMP = tempfile.mkdtemp(prefix="knk_notphish_")
    _db.DB_PATH = os.path.join(_TMP, "t.db")
    _db.init_db()
    import app.main as m
    from app import mail_store as ms
finally:
    sys.stdout = _so
from starlette.testclient import TestClient  # noqa: E402

P = F = 0
_SEQ = [0]


def check(name, cond, extra=""):
    global P, F
    if cond:
        P += 1
        print("  [PASS]", name)
    else:
        F += 1
        print("  [FAIL]", name, "<-", str(extra)[:500])


ME, OTHER = 9701, 9702
with _db.db_session() as c:
    c.execute("INSERT INTO users(id, login_id, name, role, is_active, password) VALUES(?,?,?,?,1,'x')", (ME, "t9701", "가짜나", "member"))
    c.execute("INSERT INTO users(id, login_id, name, role, is_active, password) VALUES(?,?,?,?,1,'x')", (OTHER, "t9702", "가짜남", "member"))

IP_LINK = '<p>자료 확인 부탁드립니다 <a href="http://10.20.30.40/data">자료</a></p>'   # 숫자(IP) 링크 = 링크만으로 의심(2) · 이유 코드 없음


def put(owner, frm, html=IP_LINK, att=None, text="가짜 본문 http://10.20.30.40/data"):
    _SEQ[0] += 1
    with _db.db_session() as c:
        mid, _o = ms.store_inbound(c, to_email="t%d@knknara.co.kr" % owner, from_email=frm, from_name="가짜 보낸이",
                                   subject="가짜 제목 #%d" % _SEQ[0], text=text, html=html,
                                   owner_id=owner, run_ai=False, message_id="np-%d@test" % _SEQ[0], attachments=att)
        r = c.execute("SELECT risk_level, risk_note, is_blocked FROM mail_messages WHERE id=?", (mid,)).fetchone()
    return mid, dict(r)


_U = {"id": ME, "role": "member"}
m.get_user = lambda req: dict(_U, name="가짜", team_id=None, team_name="")
k = TestClient(m.app, base_url="http://127.0.0.1:5051", raise_server_exceptions=False, follow_redirects=False)
k.headers.update({"host": "works.knknara.co.kr", "x-forwarded-proto": "https"})

FRM = "ymcho@partner-demo.example"
print("① 처음 = 링크만으로 의심(2) · 경고 띠 · 단추 한 줄")
m1, r1 = put(ME, FRM)
check("링크만으로 의심 = risk 2", r1["risk_level"] == 2, r1)
h = k.get("/mail/%d/pane" % m1).text
check("경고 띠 + 「✓ 피싱 아님(이 보낸 사람 믿기)」 단추", "피싱·사칭 의심 메일" in h and "mvNotPhish(%d" % m1 in h, "")
_w = h[h.find('class="mv-warn high"'):]
_w = _w[:_w.find('<div class="mv-head">')]
check("단추들이 한 칸(mv-warn-acts) 안에 같이 · 예전 margin-top 칸 없음",
      _w.count('class="mv-warn-acts"') == 1 and 'style="margin-top:6px"' not in _w and _w.find("다시 안 받기") > _w.find("mv-warn-acts"), _w[:600])
check("링크는 막혀 있음(경고 중)", 'href="http://10.20.30.40/data"' not in h, "")

print("② ✓ 피싱 아님 누름")
j = k.post("/mail/%d/not-phish" % m1).json()
with _db.db_session() as c:
    r = dict(c.execute("SELECT risk_level, risk_note FROM mail_messages WHERE id=?", (m1,)).fetchone())
    tr = c.execute("SELECT COUNT(*) FROM mail_user_trust WHERE user_id=? AND email=?", (ME, FRM)).fetchone()[0]
check("이 메일 = 외부(1) · 표시 「내가 확인: 피싱 아님」", j.get("ok") and r["risk_level"] == 1 and r["risk_note"].startswith(ms.NOT_PHISH_MARK), (j, r))
check("이 보낸 사람 믿기 저장(나에게만)", tr == 1, tr)
h = k.get("/mail/%d/pane" % m1).text
check("경고 띠 없음 · 「피싱 아님으로 확인한 메일」 줄 + ↩ 되돌리기", "피싱·사칭 의심 메일" not in h and "피싱 아님으로 확인한 메일입니다" in h and "mvNotPhish(%d, '', 1, this)" % m1 in h, "")

print("③ 다음부터 = 같은 사람 링크만 의심 → 경고 없이(1) · 다른 사람·다른 직원은 그대로")
m2, r2 = put(ME, FRM)
check("같은 사람 다음 메일 = 1(경고 없음) · 까닭 글에 「믿는 보낸 사람」", r2["risk_level"] == 1 and "믿는 보낸 사람" in (r2["risk_note"] or ""), r2)
m3, r3 = put(ME, "other@stranger-demo.example")
check("다른 보낸 사람 = 그대로 의심(2)", r3["risk_level"] == 2, r3)
m4, r4 = put(OTHER, FRM)
check("다른 직원이 같은 사람에게 받으면 = 그대로 의심(2)(나에게만)", r4["risk_level"] == 2, r4)
m5, r5 = put(ME, FRM, text="입금 계좌 변경 안내 — 새 계좌로 송금 부탁드립니다 http://10.20.30.40/data")
check("믿는 사람이라도 송금·계좌 변경 같은 이유가 있으면 = 경고 그대로(2 이상)", r5["risk_level"] >= 2, r5)

print("④ 되돌리기")
j = k.post("/mail/%d/not-phish?undo=1" % m1).json()
with _db.db_session() as c:
    r = dict(c.execute("SELECT risk_level, risk_note FROM mail_messages WHERE id=?", (m1,)).fetchone())
    tr = c.execute("SELECT COUNT(*) FROM mail_user_trust WHERE user_id=? AND email=?", (ME, FRM)).fetchone()[0]
check("이 메일 경고 원래대로(2 · 표시 지움) · 믿기 취소", j.get("ok") and r["risk_level"] == 2 and not r["risk_note"].startswith(ms.NOT_PHISH_MARK) and tr == 0, (j, r, tr))
m6, r6 = put(ME, FRM)
check("되돌린 뒤 같은 사람 새 메일 = 다시 의심(2)", r6["risk_level"] == 2, r6)
check("되돌릴 것 없는 메일에 되돌리기 = 거절", not k.post("/mail/%d/not-phish?undo=1" % m3).json().get("ok"))

print("⑤ 막아야 할 것")
with _db.db_session() as c:
    c.execute("UPDATE mail_messages SET risk_level=3 WHERE id=?", (m3,))
check("위험(3) 메일은 풀 수 없음", not k.post("/mail/%d/not-phish" % m3).json().get("ok"))
check("남의 메일 = 404", k.post("/mail/%d/not-phish" % m4).status_code == 404)
with _db.db_session() as c:
    ms.add_block(c, "bad@blocked-demo.example", kind="email", note="시험", by=1)
mb, rb = put(ME, "bad@blocked-demo.example")
with _db.db_session() as c:
    c.execute("UPDATE mail_messages SET risk_level=2 WHERE id=?", (mb,))
check("회사 전체 차단 주소 = 풀 수 없음(관리자 일)", not k.post("/mail/%d/not-phish" % mb).json().get("ok"))
_U["id"] = OTHER
check("다른 직원은 내 메일을 못 품", k.post("/mail/%d/not-phish" % m2).status_code == 404)

print("\n결과: %d 통과 / %d 실패" % (P, F))
sys.exit(1 if F else 0)
