# -*- coding: utf-8 -*-
"""🏖 부재중 자동 응답 — 시작일·끝나는 날이 하루 어긋나지 않는지 (2026-11-21 세션 15 점검) — 운영 무접촉 · 임시 DB(knk_mar_*) · 가짜 사람·가짜 메일만.

「11/24 ~ 11/26 휴가」 = 11/24 00:00 부터 11/26 23:59 까지(보는 사람 소속 시각) 나감 · 11/27 부터 안 나감.
본사 = UTC+9 · 베트남 = UTC+7. 시각은 시험 안에서 m._mail_now_local 을 바꿔치기해 고정한다(운영 코드에 시험용 갈래 없음).

증명할 것
  ① 실제 보냄(_mail_autoreply_run): 시작 전날 X · 시작일 O · 끝나는 날 O · 다음 날 X — 본사·베트남 각각, 날 바뀌는 시각 앞뒤 30분
  ② 받은편지함 위 띠 · 설정 화면 · 설정·정리 줄: 같은 순간에 「예약됨 / 켜짐 / 기간 지남」이 ①과 똑같이 바뀜
  ③ 저장: 끝나는 날 = 오늘이면 저장 됨, 어제면 거절(소속 날짜 기준)
  ④ 이음 휴가 제안 띠(/api/mail/vacation/me): 이음 끝 시각(UTC ISO) → 소속 날짜 · 그 날까지 보이고 다음 날 안 보임
"""
import ast
import io
import os
import sys
import tempfile
from datetime import datetime, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
os.chdir(ROOT)
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
os.environ["KNK_RUN_MAIL_FETCH"] = "0"

_so = sys.stdout
sys.stdout = io.StringIO()
try:
    from cryptography.fernet import Fernet
    os.environ.setdefault("KNK_MAIL_KEY", Fernet.generate_key().decode())
    import app.database as _db
    _TMP = tempfile.mkdtemp(prefix="knk_mar_")
    _db.DB_PATH = os.path.join(_TMP, "t.db")
    _db.init_db()
    import app.main as m
    from app import mail_store as MS
    from app import mail_glance as MG
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
        print("  [FAIL]", name, "<-", str(extra)[:500])


D = "@knknara.co.kr"
KR, VN = 9790, 9791
with _db.db_session() as c:
    c.execute("UPDATE users SET login_id=login_id||'_x', email=NULL")
    if "employee_no" not in [r[1] for r in c.execute("PRAGMA table_info(users)").fetchall()]:
        c.execute("ALTER TABLE users ADD COLUMN employee_no TEXT")   # 임시 DB 에만(운영은 이미 있음)
    if "entity" not in [r[1] for r in c.execute("PRAGMA table_info(teams)").fetchall()]:
        c.execute("ALTER TABLE teams ADD COLUMN entity TEXT")
    MS._ensure_security_cols(c)   # 스팸 표시 칸(운영엔 있음) — 없으면 광고 보낸 곳 찾기가 오류 한 줄을 찍음
    c.execute("INSERT INTO teams(id, code, name, display_order, entity) VALUES(9781,'T9781','시험본사팀',3,'KOR')")
    c.execute("INSERT INTO teams(id, code, name, display_order, entity) VALUES(9782,'T9782','시험법인팀',4,'VN')")
    c.execute("INSERT INTO users(id, login_id, name, rank, role, team_id, is_active, password, email, employee_no) "
              "VALUES(?, 't_kr','시험본사','사원','member',9781,1,'x','krme" + D + "','99790')", (KR,))
    c.execute("INSERT INTO users(id, login_id, name, rank, role, team_id, is_active, password, email, employee_no) "
              "VALUES(?, 'VN99791','시험법인','사원','member',9782,1,'x','vnme" + D + "','VN99791')", (VN,))
    MID = {}
    for uid, me in ((KR, "krme" + D), (VN, "vnme" + D)):
        c.execute("INSERT INTO mail_messages(user_id, direction, from_email, from_name, to_email, subject, body_text, is_read, is_deleted, received_at) "
                  "VALUES(?,'in','buyer@client-demo.example','가짜',?,'견적 문의','가짜',0,0,datetime('now','localtime'))", (uid, me))
        MID[uid] = c.execute("SELECT last_insert_rowid()").fetchone()[0]
    USERS = {r["id"]: dict(r) for r in c.execute("SELECT * FROM users WHERE id IN (?,?)", (KR, VN)).fetchall()}

check("소속 판정: 본사 +9 · 베트남 +7", True)
with _db.db_session() as c:
    o_kr, o_vn = m._mail_off(c, USERS[KR]), m._mail_off(c, USERS[VN])
check("_mail_off 본사=9 · 베트남=7", (o_kr, o_vn) == (9, 7), (o_kr, o_vn))

# ── 시각 고정 ──
NOW_UTC = {"t": datetime(2026, 11, 25, 3, 0)}
m._mail_now_local = lambda off: NOW_UTC["t"] + timedelta(hours=off)   # 운영 코드는 그대로 · 여기서만 바꿔치기

# 보낸 것 기록(실제로 보내지 않음)
SENT = []


def _fake_send(owner_user, to, *a, **k):
    SENT.append((owner_user.get("id"), to))
    return {"ok": True}


m._mail_send_core = _fake_send

with _db.db_session() as c:
    for uid in (KR, VN):
        MS.save_autoreply(c, uid, enabled=True, start_date="2026-11-24", end_date="2026-11-26",
                          subject="", body="휴가 중입니다(가짜)", only_known=False)

CUR = {"u": USERS[KR]}
m.get_user = lambda req: CUR["u"]
k = TestClient(m.app, base_url="http://127.0.0.1:5051", raise_server_exceptions=False, follow_redirects=False)
k.headers.update({"host": "works.knknara.co.kr", "x-forwarded-proto": "https"})


def sends(uid):
    with _db.db_session() as c:
        c.execute("DELETE FROM mail_autoreply_log WHERE user_id=?", (uid,))   # 「이번 기간에 이미 보냄」 영향 없게 매번 비움
    SENT.clear()
    m._mail_autoreply_run(dict(USERS[uid]), [(MID[uid], False)])
    return len(SENT) == 1


def screens(uid):
    CUR["u"] = USERS[uid]
    hi = k.get("/mail/inbox").text
    ar = k.get("/mail/autoreply").text
    tl = k.get("/mail/tools").text
    if "부재중 자동 응답 켜짐" in hi:
        bar = "live"
    elif "기간이 지났습니다" in hi:
        bar = "over"
    elif "부재중 자동 응답 예약됨" in hi:
        bar = "wait"
    else:
        bar = "?"
    page = "live" if "지금 켜짐" in ar else ("over" if "기간 지남 · 안 보냄" in ar else ("wait" if 'ar-state wait' in ar else "?"))
    tool = "live" if "켜짐 11/24~11/26" in tl else ("over" if "기간 지남 11/24~11/26" in tl else ("wait" if "예약됨 11/24~11/26" in tl else "?"))
    return bar, page, tool


#            (UTC 시각, 사람, 그 사람 현지 시각 설명, 나가야 하나, 화면 상태)
CASES = [
    (datetime(2026, 11, 23, 14, 30), KR, "본사 11/23 23:30(시작 전날 밤)", False, "wait"),
    (datetime(2026, 11, 23, 15, 30), KR, "본사 11/24 00:30(시작일 첫 시각)", True, "live"),
    (datetime(2026, 11, 23, 15, 30), VN, "베트남 11/23 22:30(시작 전날 · 본사는 이미 24일)", False, "wait"),
    (datetime(2026, 11, 23, 16, 30), VN, "베트남 11/23 23:30(시작 전날 밤)", False, "wait"),
    (datetime(2026, 11, 23, 17, 30), VN, "베트남 11/24 00:30(시작일 첫 시각)", True, "live"),
    (datetime(2026, 11, 25, 3, 0), KR, "본사 11/25 12:00(기간 가운데)", True, "live"),
    (datetime(2026, 11, 25, 3, 0), VN, "베트남 11/25 10:00(기간 가운데)", True, "live"),
    (datetime(2026, 11, 26, 14, 30), KR, "본사 11/26 23:30(끝나는 날 밤)", True, "live"),
    (datetime(2026, 11, 26, 14, 59, 30), KR, "본사 11/26 23:59:30(끝나는 날 마지막)", True, "live"),
    (datetime(2026, 11, 26, 15, 0, 30), KR, "본사 11/27 00:00:30(다음 날 첫 시각)", False, "over"),
    (datetime(2026, 11, 26, 15, 30), KR, "본사 11/27 00:30(끝 다음 날)", False, "over"),
    (datetime(2026, 11, 26, 15, 30), VN, "베트남 11/26 22:30(끝나는 날 · 본사는 이미 27일)", True, "live"),
    (datetime(2026, 11, 26, 16, 59, 30), VN, "베트남 11/26 23:59:30(끝나는 날 마지막)", True, "live"),
    (datetime(2026, 11, 26, 17, 30), VN, "베트남 11/27 00:30(끝 다음 날)", False, "over"),
]

print("① 실제 보냄 · ② 화면(받은편지함 띠 · 설정 화면 · 설정·정리 줄)")
for t, uid, label, want_send, want_scr in CASES:
    NOW_UTC["t"] = t
    got = sends(uid)
    check("%s → %s" % (label, "나감" if want_send else "안 나감"), got == want_send, (t, got))
    scr = screens(uid)
    check("%s → 화면 「%s」(띠·설정·정리 같음)" % (label, {"live": "켜짐", "wait": "예약됨", "over": "기간 지남"}[want_scr]),
          scr == (want_scr,) * 3, scr)

print("\n③ 저장(끝나는 날 = 오늘이면 됨 · 어제면 거절 — 소속 날짜)")
NOW_UTC["t"] = datetime(2026, 11, 26, 15, 30)   # 본사 11/27 00:30 · 베트남 11/26 22:30
CUR["u"] = USERS[VN]
r = k.post("/mail/autoreply", data={"enabled": "1", "start_date": "2026-11-24", "end_date": "2026-11-26", "body": "가짜"})
check("베트남 11/26 22:30 에 끝=11/26 저장 → 됨", r.status_code == 200 and r.json().get("ok"), (r.status_code, r.text[:200]))
CUR["u"] = USERS[KR]
r = k.post("/mail/autoreply", data={"enabled": "1", "start_date": "2026-11-24", "end_date": "2026-11-26", "body": "가짜"})
check("본사 11/27 00:30 에 끝=11/26 저장 → 「이미 지났습니다」", r.status_code == 400 and "지났" in r.text, (r.status_code, r.text[:200]))
NOW_UTC["t"] = datetime(2026, 11, 26, 14, 30)   # 본사 11/26 23:30
r = k.post("/mail/autoreply", data={"enabled": "1", "start_date": "2026-11-24", "end_date": "2026-11-26", "body": "가짜"})
check("본사 11/26 23:30 에 끝=11/26 저장 → 됨", r.status_code == 200 and r.json().get("ok"), (r.status_code, r.text[:200]))
r = k.get("/mail/autoreply")
check("설정 화면 = 저장한 기간 그대로(11/24 ~ 11/26) · 「지금 켜짐」", 'value="2026-11-24"' in r.text and 'value="2026-11-26"' in r.text and "지금 켜짐" in r.text, "")

print("\n④ 이음 휴가 제안 띠(/api/mail/vacation/me) — 자동 응답 꺼 둔 상태")
with _db.db_session() as c:
    for uid in (KR, VN):
        MS.save_autoreply(c, uid, enabled=False, start_date="", end_date="", subject="", body="", only_known=True)
# 이음 명부의 휴가 끝(until_at) = UTC ISO. 「11/26 까지」를 본사 자정 끝으로 적은 값과 베트남 자정 끝으로 적은 값.
FAKE = {"emp": {MG._norm_emp("99790"): {"emp": MG._norm_emp("99790"), "name": "시험본사", "position": "", "dept": "", "until": "2026-11-26T15:00:00+00:00"},
                MG._norm_emp("VN99791"): {"emp": MG._norm_emp("VN99791"), "name": "시험법인", "position": "", "dept": "", "until": "2026-11-26T17:00:00Z"}},
        "email": {}}
MG.directory = lambda *a, **kw: FAKE
check("이음 끝 11-26T15:00Z(본사 11/27 00:00 딱) → 본사 「11/26 까지」", MG.until_local("2026-11-26T15:00:00Z", 9) == "2026-11-26")
check("이음 끝 11-26T17:00Z(베트남 11/27 00:00 딱) → 베트남 「11/26 까지」", MG.until_local("2026-11-26T17:00:00Z", 7) == "2026-11-26")
check("이음 끝 11-26T14:59:59Z(본사 11/26 23:59:59) → 「11/26 까지」", MG.until_local("2026-11-26T14:59:59Z", 9) == "2026-11-26")
check("날짜만 적힌 끝 → 그 날짜 그대로", MG.until_local("2026-11-26", 7) == "2026-11-26")
VAC = [
    (datetime(2026, 11, 26, 14, 30), KR, "본사 11/26 23:30", True),
    (datetime(2026, 11, 26, 15, 30), KR, "본사 11/27 00:30", False),
    (datetime(2026, 11, 26, 16, 30), VN, "베트남 11/26 23:30", True),
    (datetime(2026, 11, 26, 17, 30), VN, "베트남 11/27 00:30", False),
]
for t, uid, label, want in VAC:
    NOW_UTC["t"] = t
    CUR["u"] = USERS[uid]
    j = k.get("/api/mail/vacation/me").json()
    check("%s → 휴가 제안 띠 %s" % (label, "보임(~11/26)" if want else "안 보임"),
          bool(j.get("show")) == want and (not want or j.get("label") == "~11/26"), j)

print("\n⑤ 문법")
for p in ("app/main.py", "app/mail_store.py", "app/mail_glance.py"):
    try:
        ast.parse(io.open(os.path.join(ROOT, p), encoding="utf-8").read(), feature_version=(3, 8))
        ok = True
    except SyntaxError as e:
        ok = e
    check("파이썬 3.8 문법: %s" % p, ok is True, ok)

print("\n결과: %d 통과 / %d 실패" % (P, F))
sys.exit(1 if F else 0)
