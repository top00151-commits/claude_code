# -*- coding: utf-8 -*-
"""메일 받기 설정 = 대표만 · 다른 사이트에서 온 저장 요청 막기 · 큰 파일 하루 한도·밤 지우기 — 시험(11-27). 가짜 자료·임시 DB(운영 무접촉).
실행: PYTHONIOENCODING=utf-8 py -3.13 _검증/mail_owner_origin_large_test.py"""
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
    _TMP = tempfile.mkdtemp(prefix="knk_ool_")
    _db.DB_PATH = os.path.join(_TMP, "t.db")
    _db.init_db()
    import app.main as m
    from app import mail_store as ms
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


OWNER, ADMIN, STAFF = 9901, 9902, 9903
with _db.db_session() as c:
    c.execute("UPDATE users SET is_active=0 WHERE login_id='kjr'")
    c.execute("INSERT INTO users(id, login_id, name, role, is_active, password) VALUES(?,?,?,?,1,'x')", (OWNER, "kjr", "가짜대표", "ceo"))
    c.execute("INSERT INTO users(id, login_id, name, role, is_active, password) VALUES(?,?,?,?,1,'x')", (ADMIN, "t9902", "가짜관리자", "admin"))
    c.execute("INSERT INTO users(id, login_id, name, role, is_active, password) VALUES(?,?,?,?,1,'x')", (STAFF, "t9903", "가짜직원", "member"))
    c.execute("INSERT INTO app_settings(key, value) VALUES('mail_inbound_token','fake-old-token-test') ON CONFLICT(key) DO UPDATE SET value=excluded.value")
    c.execute("INSERT INTO app_settings(key, value) VALUES('mail_default_user_id', ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (str(OWNER),))
USERS = {OWNER: ("ceo", "가짜대표"), ADMIN: ("admin", "가짜관리자"), STAFF: ("member", "가짜직원")}
CUR = [OWNER]
m.get_user = lambda req: {"id": CUR[0], "role": USERS[CUR[0]][0], "name": USERS[CUR[0]][1], "team_id": None, "team_name": "", "login_id": ""}
k = TestClient(m.app, base_url="http://127.0.0.1:5051", raise_server_exceptions=False, follow_redirects=False)
k.headers.update({"host": "works.knknara.co.kr", "x-forwarded-proto": "https"})
ORG = {"Origin": "https://works.knknara.co.kr"}


def setting(key):
    with _db.db_session() as c:
        r = c.execute("SELECT value FROM app_settings WHERE key=?", (key,)).fetchone()
        return r[0] if r else None


print("① 메일 받기 설정 = 대표 한 사람만")
CUR[0] = ADMIN
r = k.get("/admin/mail-inbound")
check("관리자 = 설정 화면 못 엶(도구 화면으로 · 안내)", r.status_code == 303 and "owner_only=1" in r.headers.get("location", ""), (r.status_code, r.headers.get("location")))
r = k.post("/admin/mail-inbound", headers=ORG)
check("관리자 = 토큰 다시 만들기 403 · 토큰 그대로", r.status_code == 403 and setting("mail_inbound_token") == "fake-old-token-test", r.status_code)
r = k.post("/admin/mail-inbound/bind-me", headers=ORG)
check("관리자 = 받는 사람 바꾸기 403 · 그대로 대표", r.status_code == 403 and setting("mail_default_user_id") == str(OWNER), r.status_code)
t = k.get("/mail/tools").text
check("관리자 도구 화면 = 「받기 설정」 줄 안 보임", 'href="/admin/mail-inbound"' not in t)
t = k.get("/mail/tools?owner_only=1").text
check("안내 글 「대표님만 바꿀 수 있습니다」", "대표님만 바꿀 수 있습니다" in t)
CUR[0] = OWNER
r = k.get("/admin/mail-inbound")
check("대표 = 설정 화면 열림", r.status_code == 200, r.status_code)
t = k.get("/mail/tools").text
check("대표 도구 화면 = 「받기 설정」 줄 보임", 'href="/admin/mail-inbound"' in t)
r = k.post("/admin/mail-inbound", headers=ORG)
check("대표 = 토큰 다시 만들기 됨", r.status_code == 303 and setting("mail_inbound_token") not in (None, "", "fake-old-token-test"), r.status_code)
with _db.db_session() as c:
    lg = [x[0] for x in c.execute("SELECT result FROM mail_inbound_log ORDER BY id").fetchall()]
check("바꾼 기록 남음(누가)", any(x.startswith("토큰 다시 만듦(%d)" % OWNER) for x in lg), lg)

print("② 다른 사이트에서 온 메일 저장 요청 막기")
CUR[0] = STAFF
r = k.post("/mail/autoreply", data={"on": "1"}, headers={"Origin": "https://evil-demo.example"})
check("다른 회사 사이트 Origin = 403", r.status_code == 403 and "다른 사이트" in r.text, r.status_code)
r = k.post("/mail/autoreply", data={"on": "1"}, headers={"Origin": "https://other.knknara.co.kr"})
check("같은 회사 다른 주소 Origin = 403", r.status_code == 403, r.status_code)
r = k.post("/mail/autoreply", data={"on": "1"}, headers={"Origin": "null"})
check("Origin null = 403", r.status_code == 403, r.status_code)
r = k.post("/mail/autoreply", data={"on": "1"}, headers={"Sec-Fetch-Site": "cross-site"})
check("Origin 없이 다른 사이트 표시 = 403", r.status_code == 403, r.status_code)
for o in ("https://works.knknara.co.kr", "https://kmail.knknara.co.kr"):
    r = k.post("/mail/autoreply", data={"on": "1"}, headers={"Origin": o})
    check("우리 주소 Origin(%s) = 안 막음" % o.split("//")[1], r.status_code != 403 or "다른 사이트" not in r.text, (r.status_code, r.text[:80]))
r = k.post("/mail/autoreply", data={"on": "1"})
check("Origin 없음(브라우저 아닌 프로그램) = 안 막음", "다른 사이트" not in r.text, r.text[:80])
r = k.get("/mail/tools", headers={"Origin": "https://evil-demo.example"})
check("보기(GET)는 막지 않음", r.status_code == 200, r.status_code)
r = k.post("/api/mail/inbound", json={}, headers={"Origin": "https://evil-demo.example"})
check("바깥 받는 입구는 이 검사 밖(토큰으로 판정 → 401)", r.status_code == 401, r.status_code)
r = k.post("/projects/x-demo", headers={"Origin": "https://evil-demo.example"})
check("메일 밖(웍스) 요청은 건드리지 않음", "다른 사이트에서 온 요청" not in r.text, r.status_code)

print("③ 큰 파일 — 하루 한도 · 남은 공간 · 기한 지난 것 지우기")
CUR[0] = STAFF
_LR = os.path.join(_TMP, "mail_large")
ms._large_root = lambda: _LR
with _db.db_session() as c:
    for i in range(ms.LARGE_DAY_MAX_N):
        c.execute("INSERT INTO mail_large_files(token, filename, size, path, uploaded_by, expires_at) VALUES(?,?,?,?,?,datetime('now','localtime','+30 days'))",
                  ("tk-day-%d" % i, "a.bin", 10, "", STAFF))
r = k.post("/mail/large/upload", files={"file": ("x.bin", b"x" * 10)}, headers=ORG)
check("하루 개수 한도 넘음 = 429 · 안내 글", r.status_code == 429 and "한도" in r.json().get("message", ""), (r.status_code, r.text[:120]))
with _db.db_session() as c:
    c.execute("DELETE FROM mail_large_files WHERE token LIKE 'tk-day-%'")
import app.mail_import_outlook as _mio  # noqa: E402
_ods = _mio.disk_state
_mio.disk_state = lambda path=None: {"free": 0, "total": 1, "ok": False}
r = k.post("/mail/large/upload", files={"file": ("x.bin", b"x" * 10)}, headers=ORG)
check("서버 공간 모자람 = 507 · 안내 글", r.status_code == 507 and "공간" in r.json().get("message", ""), (r.status_code, r.text[:120]))
_mio.disk_state = lambda path=None: {"free": 10 ** 12, "total": 2 * 10 ** 12, "ok": True}   # 시험 PC 디스크와 상관없이 「공간 충분」
r = k.post("/mail/large/upload", files={"file": ("x.bin", b"x" * 10)}, headers=ORG)
check("보통 = 올라감", r.status_code == 200 and r.json().get("ok"), r.text[:120])
tok_new = r.json().get("token")
# 기한 지난 것 두 개(여유 넘은 것 · 여유 안의 것)
for tok, days in (("tk-old", -10), ("tk-grace", -3)):
    d = ms.large_file_dir(tok)
    os.makedirs(d, exist_ok=True)
    p = os.path.join(d, "f.bin")
    open(p, "wb").write(b"x")
    with _db.db_session() as c:
        c.execute("INSERT INTO mail_large_files(token, filename, size, path, uploaded_by, expires_at) VALUES(?,?,?,?,?,datetime('now','localtime',?))",
                  (tok, "f.bin", 1, p, STAFF, "%d days" % days))
n = ms.purge_expired_large(_db.db_session)
with _db.db_session() as c:
    rows = {r["token"]: r["path"] for r in c.execute("SELECT token, path FROM mail_large_files").fetchall()}
check("여유(7일)까지 넘은 것만 지움 · 1개", n == 1 and not os.path.exists(ms.large_file_dir("tk-old")) and os.path.exists(ms.large_file_dir("tk-grace")), (n, rows))
check("표의 줄은 남고 경로만 비움 · 새 파일은 그대로", rows.get("tk-old") == "" and rows.get("tk-grace") and rows.get(tok_new), rows)
r = k.get("/dl/tk-old")
check("지운 파일 링크 = 기한 지남 안내(410)", r.status_code == 410, r.status_code)

print("\n결과: %d 통과 / %d 실패" % (P, F))
sys.exit(1 if F else 0)
