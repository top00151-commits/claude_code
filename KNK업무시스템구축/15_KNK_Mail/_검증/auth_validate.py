# -*- coding: utf-8 -*-
"""KNK Eum MAIL 인증(2단계) 검증 — 메신저 SSO 이식 + 직원명부 미러 upsert.
네트워크 없이: build_login_url 형태, /sso/land 토큰없음 처리, dev 로그인=미러 upsert,
get_user=미러 로드, dir-sync 권한/무키 graceful.
"""
import os, sys, io, ast, tempfile

try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass

VAL_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(VAL_DIR)
APP = os.path.join(PROJECT, "app")
sys.path.insert(0, PROJECT)

ok = True
def chk(n, c):
    global ok; print(("[OK] " if c else "[FAIL] ") + n); ok = ok and bool(c)
def rd(p):
    with io.open(p, encoding="utf-8") as f: return f.read()

# 1) 문법
for f in ["sso_client.py", "main.py"]:
    try: ast.parse(rd(os.path.join(APP, f))); print("[OK] ast", f)
    except SyntaxError as e: ok=False; print("[FAIL] ast", f, e)

# 2) 임시 DB + dev 로그인. 서비스키 미설정(무키 graceful 확인). 메신저 base 고정.
tmp = tempfile.mkdtemp(prefix="knkmail_auth_")
os.environ["KNK_MAIL_DATA"] = tmp
os.environ["KNK_MAIL_DB"] = os.path.join(tmp, "mail.db")
os.environ["KNK_MAIL_DEV_LOGIN"] = "1"
os.environ["KNK_MESSENGER_SSO_BASE"] = "https://haist.knknara.co.kr/msg"
os.environ["KNK_MAIL_PUBLIC_BASE"] = "https://mail.knknara.co.kr"
os.environ.pop("KNK_SSO_SERVICE_KEY", None)

from app import db as mdb           # noqa
from app import sso_client as sso   # noqa
from app.main import app           # noqa

chk("audience=knk-mail", sso.SSO_AUDIENCE == "knk-mail")

# 3) upsert (직원명부 미러) — 직접 호출
with mdb.db_session() as c:
    uid1 = sso.upsert_user_from_payload(c, {"sub": "210101", "name_kr": "김직원",
                                            "dept": "검사사업부", "email": "k@knknara.co.kr", "entity": "KOR"})
    uid2 = sso.upsert_user_from_payload(c, {"sub": "210101", "name_kr": "김직원변경"})  # 갱신(같은 사번)
chk("upsert 신규 id 반환", bool(uid1))
chk("upsert 동일 사번 갱신(같은 id)", uid1 == uid2)
with mdb.db_session() as c:
    row = c.execute("SELECT name, email FROM users WHERE employee_no='210101'").fetchone()
chk("갱신 반영(name=김직원변경, email 보존)", row["name"] == "김직원변경" and row["email"] == "k@knknara.co.kr")

# 4) TestClient
from starlette.testclient import TestClient
c = TestClient(app)

r = c.get("/sso/login", follow_redirects=False)
loc = r.headers.get("location", "")
chk("/sso/login → 메신저 SSO", r.status_code in (302,303) and loc.startswith("https://haist.knknara.co.kr/msg/sso/login?"))
chk("redirect_uri에 /sso/land 포함", "%2Fsso%2Fland" in loc or "/sso/land" in loc)

r = c.get("/sso/land", follow_redirects=False)
chk("/sso/land 토큰없음 → 로그인+오류", r.status_code == 200 and "입장 토큰이 없습니다" in r.text)

r = c.post("/admin/dir-sync", follow_redirects=False)
chk("미로그인 dir-sync 거부(403)", r.status_code == 403)

# dev 로그인 → 미러 upsert + 세션
r = c.post("/login/dev", data={"name": "테스트대표"}, follow_redirects=False)
chk("dev 로그인 → /mail/inbox", r.status_code in (302,303) and r.headers.get("location") == "/mail/inbox")
with mdb.db_session() as cc:
    dev = cc.execute("SELECT id, role FROM users WHERE employee_no='DEV001'").fetchone()
chk("dev 사용자 미러 생성+role=ceo", dev is not None and dev["role"] == "ceo")

r = c.get("/mail/inbox")
chk("로그인 후 메일함 200(미러 로드)", r.status_code == 200 and "받은편지함" in r.text)

r = c.post("/admin/dir-sync")
chk("dir-sync 무키 graceful(200, ok=false)", r.status_code == 200 and r.json().get("ok") is False
    and "공유키" in (r.json().get("error") or ""))

r = c.get("/logout", follow_redirects=False)
chk("로그아웃 → /login", r.status_code in (302,303) and r.headers.get("location") == "/login")
r = c.get("/mail/inbox", follow_redirects=False)
chk("로그아웃 후 메일함 → /login", r.status_code in (302,303) and r.headers.get("location") == "/login")

print("\nRESULT:", "ALL PASS" if ok else "HAS FAILURES")
sys.exit(0 if ok else 1)
