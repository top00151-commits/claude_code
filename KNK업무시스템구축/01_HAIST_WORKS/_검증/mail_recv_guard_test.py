# -*- coding: utf-8 -*-
"""메일 받기 — AI 는 저장 뒤 · 바깥 받는 입구 한도·기록 · 사내 주소 송금 문구 — 시험(11-27). 가짜 자료·임시 DB(운영 무접촉).
실행: PYTHONIOENCODING=utf-8 py -3.13 _검증/mail_recv_guard_test.py"""
import io
import os
import sqlite3
import sys
import tempfile
import threading
import time
from email.message import EmailMessage

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
    _TMP = tempfile.mkdtemp(prefix="knk_recv_")
    _db.DB_PATH = os.path.join(_TMP, "t.db")
    _db.init_db()
    import app.main as m
    from app import mail_store as ms, mail_guard as g, mail_fetch as mf
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
        print("  [FAIL]", name, "<-", str(extra)[:300])


def raw_mail(i, frm="vendor@partner-demo.example", subj=None, body="가짜 본문"):
    e = EmailMessage()
    e["From"] = frm
    e["To"] = "t9881@knknara.co.kr"
    e["Subject"] = subj or ("가짜 견적 %d" % i)
    e["Message-ID"] = "<recv-%d-%s@demo>" % (i, int(time.time() * 1000))
    e.set_content(body)
    return e.as_bytes()


ME = 9881
with _db.db_session() as c:
    c.execute("INSERT INTO users(id, login_id, name, role, is_active, password) VALUES(?,?,?,?,1,'x')", (ME, "t9881", "가짜받는이", "member"))
    mf._ensure_table(c)

# ── ① 받기 저장 중에는 AI 를 부르지 않고, 저장 뒤 AI 를 기다리는 동안에도 다른 저장이 된다 ──
print("① 자동 받기 — AI 는 저장 뒤")
calls = []
_orig_c, _orig_s = ms._ai_classify, ms._ai_summary


def slow_classify(s, b):
    calls.append(("c", time.time()))
    time.sleep(1.2)
    return ("견적", "ko")


def slow_summary(b):
    calls.append(("s", time.time()))
    time.sleep(0.3)
    return "- 가짜 요약"


ms._ai_classify, ms._ai_summary = slow_classify, slow_summary
acct = {"id": 77, "owner_user_id": ME, "last_uid": 0}
res = {"ok": True, "messages": [("u%d" % i, raw_mail(i)) for i in range(3)]}
t0 = time.time()
stored, got, ai_ids = m._mailfetch_store_all(res, acct, "t9881@knknara.co.kr", "pop3", True, ME, "자동 가져오기")
dt = time.time() - t0
check("3통 저장 · AI 번호 3개 모음", stored == 3 and len(ai_ids) == 3, (stored, ai_ids))
check("저장하는 동안 AI 를 부르지 않음(%.2f초)" % dt, not calls and dt < 1.0, (calls, dt))
with _db.db_session() as c:
    seen = {r[0] for r in c.execute("SELECT uidl FROM mail_fetch_seen WHERE account_id=77").fetchall()}
check("받은 표시(UIDL) 3개 남김", seen == {"u0", "u1", "u2"}, seen)

# 사람이 종류를 바꾼 메일은 AI 가 덮지 않음
with _db.db_session() as c:
    c.execute("UPDATE mail_messages SET category='발주' WHERE id=?", (ai_ids[0],))

# AI 를 기다리는 동안 다른 연결이 1초 안에 쓸 수 있어야 함
errs, oks = [], []


def other_writer():
    time.sleep(0.4)
    try:
        k = sqlite3.connect(_db.DB_PATH, timeout=1.0)
        k.execute("INSERT INTO app_settings(key, value) VALUES('recv_test_probe','1') "
                  "ON CONFLICT(key) DO UPDATE SET value='2'")
        k.commit()
        k.close()
        oks.append(1)
    except Exception as e:
        errs.append(str(e))


th = threading.Thread(target=other_writer)
th.start()
n = ms.ai_fill_later(_db.db_session, ai_ids)
th.join()
check("AI 기다리는 중에도 다른 저장 성공(잠금 없음)", oks and not errs, errs)
check("AI 채운 통수 3", n == 3, n)
with _db.db_session() as c:
    rows = {r["id"]: dict(r) for r in c.execute("SELECT id, category, summary, lang FROM mail_messages WHERE id IN (%s)" % ",".join(map(str, ai_ids)))}
check("AI 결과 적힘(종류·요약)", rows[ai_ids[1]]["category"] == "견적" and rows[ai_ids[1]]["summary"] == "- 가짜 요약", rows[ai_ids[1]])
check("사람이 바꾼 종류는 그대로(발주)", rows[ai_ids[0]]["category"] == "발주" and rows[ai_ids[0]]["summary"] == "- 가짜 요약", rows[ai_ids[0]])
calls.clear()
n = ms.ai_fill_later(_db.db_session, [1, 2, 3, 4, 5], limit=2)
check("AI 한도 넘는 것은 건너뜀(부른 횟수 ≤ 2통)", len([x for x in calls if x[0] == "c"]) <= 2, calls)
ms._ai_classify, ms._ai_summary = _orig_c, _orig_s

# 같은 메일을 다시 받으면 겹쳐 쌓지 않음
stored2, _g, _a = m._mailfetch_store_all({"ok": True, "messages": [("u0", res["messages"][0][1])]}, acct, "t9881@knknara.co.kr", "pop3", False, ME, "자동 가져오기")
with _db.db_session() as c:
    nmsg = c.execute("SELECT COUNT(*) FROM mail_messages WHERE user_id=? AND direction='in'", (ME,)).fetchone()[0]
check("같은 메일 다시 받아도 3통 그대로", nmsg == 3, nmsg)

# AI 를 안 켠 사람 = 예전처럼(번호 안 모음)
_s3, _g3, _a3 = m._mailfetch_store_all({"ok": True, "messages": [("u9", raw_mail(9))]}, acct, "t9881@knknara.co.kr", "pop3", False, ME, "자동 가져오기")
check("AI 꺼진 사람 = AI 번호 없음", _s3 == 1 and _a3 == [], (_s3, _a3))

# ── ② 바깥 받는 입구 ──
print("② 바깥 받는 입구 — 머리글 토큰만 · 받는 주소 · 크기·횟수 한도 · 기록 · 응답 줄임")
TOK = "fake-inbound-token-for-test-only"
with _db.db_session() as c:
    c.execute("INSERT INTO app_settings(key, value) VALUES('mail_inbound_token', ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (TOK,))
    c.execute("INSERT INTO app_settings(key, value) VALUES('mail_default_user_id', ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (str(ME),))
k = TestClient(m.app, base_url="http://127.0.0.1:5051", raise_server_exceptions=False, follow_redirects=False)
k.headers.update({"host": "works.knknara.co.kr", "x-forwarded-proto": "https"})


def post(payload, tok=TOK, q=""):
    h = {"X-KNK-Mail-Token": tok} if tok else {}
    return k.post("/api/mail/inbound" + q, json=payload, headers=h)


def pl(i, to="test@knk-mailtest.com", frm="vendor@partner-demo.example", body="가짜"):
    return {"to": to, "from": frm, "raw": raw_mail(100 + i, frm=frm, body=body).decode("utf-8")}


r = post(pl(1), tok="", q="?token=" + TOK)
check("주소 뒤 토큰(?token=) 은 거부(401)", r.status_code == 401, r.status_code)
r = post(pl(2), tok="wrong")
check("틀린 토큰 401", r.status_code == 401, r.status_code)
r = post(pl(3))
check("머리글 토큰 = 받음(200)", r.status_code == 200 and r.json().get("ok"), r.text)
check("응답에 받는 사람·메일 번호 없음", "owner" not in r.json() and "id" not in r.json(), r.json())
r = post(pl(4, to="someone@other-demo.example"))
check("우리가 받지 않는 도메인 = 거부(422)", r.status_code == 422, r.status_code)
_old_max = m.MAIL_INBOUND_MAX_BYTES
m.MAIL_INBOUND_MAX_BYTES = 2000
r = post(pl(5, body="가" * 3000))
check("너무 큰 메일 = 거부(413)", r.status_code == 413, r.status_code)
m.MAIL_INBOUND_MAX_BYTES = _old_max
m._MAIL_INBOUND_HITS.clear()
_old_pa = m.MAIL_INBOUND_PER_MIN_ADDR
m.MAIL_INBOUND_PER_MIN_ADDR = 3
codes = [post(pl(10 + i)).status_code for i in range(5)]
check("같은 주소 1분 한도 넘으면 429", codes[:3] == [200, 200, 200] and codes[3] == 429, codes)
m.MAIL_INBOUND_PER_MIN_ADDR = _old_pa
m._MAIL_INBOUND_HITS.clear()
with _db.db_session() as c:
    res_set = [r[0] for r in c.execute("SELECT result FROM mail_inbound_log ORDER BY id").fetchall()]
    cols = [r[1] for r in c.execute("PRAGMA table_info(mail_inbound_log)").fetchall()]
check("입구 기록 = 결과마다 한 줄(인증 실패·받음·받지 않는 주소·너무 큼·너무 많이)",
      {"인증 실패", "받음", "받지 않는 주소", "너무 큼", "너무 많이 들어옴"} <= set(res_set), res_set)
check("기록에 메일 내용 칸 없음", not ({"subject", "body", "body_text", "raw"} & set(cols)), cols)

# 우리 회사 주소로 바깥 입구에 들어온 메일 = 경고
r = post(pl(30, frm="ceo-demo@knknara.co.kr", body="오늘 회의 자료입니다"))
with _db.db_session() as c:
    row = c.execute("SELECT risk_level, risk_note FROM mail_messages WHERE from_email='ceo-demo@knknara.co.kr' ORDER BY id DESC LIMIT 1").fetchone()
check("바깥 입구 + 회사 주소 + 서버 확인 없음 = 의심(2)", r.status_code == 200 and row and row["risk_level"] >= 2 and "사칭" in (row["risk_note"] or ""), (r.status_code, row and dict(row)))

# ── ③ 판정 — 사내 주소 송금 문구 · 하이웍스 길은 예전과 같음 ──
print("③ 사내 주소 판정")
cd = []
lv, nt = g.assess(from_email="ceo-demo@knknara.co.kr", subject="급함", body="거래처 계좌번호가 변경되었으니 새 계좌로 송금 바랍니다", codes=cd)
check("사내 주소 + 송금·계좌 변경 = 의심(2) + 전화 확인 안내", lv >= 2 and "bec" in cd and "전화" in nt, (lv, cd, nt))
cd = []
lv, nt = g.assess(from_email="staff-demo@knknara.co.kr", subject="회의", body="내일 회의 자료 보내 드립니다", codes=cd)
check("보통 사내 메일 = 그대로 0", lv == 0 and not cd, (lv, cd, nt))
cd = []
lv, nt = g.assess(from_email="staff-demo@knknara.co.kr", subject="회의", body="자료", auth={"via": "inbound", "dmarc": "pass"}, codes=cd)
check("바깥 입구라도 서버 확인 통과면 0", lv == 0, (lv, cd, nt))
cd = []
lv, nt = g.assess(from_email="staff-demo@knknara.co.kr", subject="회의", body="자료", auth={}, codes=cd)
check("하이웍스 길(입구 표시 없음)은 예전과 같음(0)", lv == 0, (lv, cd, nt))
cd = []
lv, nt = g.assess(from_email="staff-demo@knknara.co.kr", subject="회의", body="자료", auth={"dmarc": "fail"}, codes=cd)
check("사내 주소 인증 실패 = 그대로 3", lv == 3 and "auth_ours" in cd, (lv, cd))

# 사내 주소 + 송금 문구 메일 = 스팸함으로 옮기지 않음(경고만) · 👔 윗분 지시에서 빠짐
with _db.db_session() as c:
    mid, _o = ms.store_inbound(c, to_email="t9881@knknara.co.kr", from_email="boss-demo@knknara.co.kr", from_name="가짜윗분",
                               subject="송금", text="입금 계좌 변경 안내드립니다", owner_id=ME, run_ai=False, message_id="bec-ours-1@demo")
    row = c.execute("SELECT risk_level, COALESCE(is_blocked,0) AS b FROM mail_messages WHERE id=?", (mid,)).fetchone()
    check("사내 주소 송금 문구 메일 = 받은편지함에 경고만(옮기지 않음)", row["risk_level"] >= 2 and row["b"] == 0, dict(row))
    ids = m._mail_boss_ids(c, ME, {mid: 1}, {"boss-demo@knknara.co.kr": {}}, {})
    check("의심 메일은 👔 윗분 지시 목록에서 빠짐", mid not in ids, ids)

with _db.db_session() as c:
    h = "From: a-demo@knknara.co.kr\nAuthentication-Results: mx-demo.example;\n spf=pass; dkim=pass; dmarc=pass\nSubject: 가짜\nX-Other: 버림\n"
    mid, _o = ms.store_inbound(c, to_email="t9881@knknara.co.kr", from_email="a-demo@knknara.co.kr", subject="가짜", text="가짜",
                               owner_id=ME, run_ai=False, message_id="hdr-keep-1@demo", raw_headers=h)
    kept = c.execute("SELECT hdr FROM mail_raw_headers WHERE mail_id=?", (mid,)).fetchone()["hdr"]
check("서버 확인 결과 줄(이어진 줄까지) 보관 · 다른 머리는 안 남김", "dmarc=pass" in kept and "X-Other" not in kept and "Subject" not in kept, kept)

print("\n결과: %d 통과 / %d 실패" % (P, F))
sys.exit(1 if F else 0)
