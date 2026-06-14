# -*- coding: utf-8 -*-
"""KNK Eum MAIL 독립 앱 골격(Phase 1) 검증.
문법 + Jinja + 별도 DB 스키마 + TestClient 라우트(500 없음·독립 동작).
"""
import os, sys, io, ast, tempfile

try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass

VAL_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(VAL_DIR)               # 15_KNK_Mail
APP = os.path.join(PROJECT, "app")
sys.path.insert(0, PROJECT)

ok = True
def chk(n, c):
    global ok; print(("[OK] " if c else "[FAIL] ") + n); ok = ok and bool(c)
def rd(p):
    with io.open(p, encoding="utf-8") as f: return f.read()

# 1) 문법
for f in ["config.py", "db.py", "main.py"]:
    try: ast.parse(rd(os.path.join(APP, f))); print("[OK] ast", f)
    except SyntaxError as e: ok=False; print("[FAIL] ast", f, e)

# 2) Jinja 문법
from jinja2 import Environment
for t in ["base_mail.html", "login.html", "inbox_min.html"]:
    try: Environment().parse(rd(os.path.join(APP, "templates", t))); print("[OK] jinja", t)
    except Exception as e: ok=False; print("[FAIL] jinja", t, e)

# 3) 임시 DB + dev 로그인 환경에서 앱 import
tmp = tempfile.mkdtemp(prefix="knkmail_")
os.environ["KNK_MAIL_DATA"] = tmp
os.environ["KNK_MAIL_DB"] = os.path.join(tmp, "mail.db")
os.environ["KNK_MAIL_DEV_LOGIN"] = "1"

from app import db as mdb           # noqa
from app.main import app           # noqa

# 4) 별도 DB 스키마 (10 테이블)
tables = set(mdb.table_names())
need = {"app_settings", "users", "mail_messages", "mail_attachments", "mail_aliases",
        "mail_large_files", "mail_signatures", "mail_fetch_accounts", "mail_fetch_seen", "mail_rules"}
chk("별도 DB 파일 생성", os.path.exists(os.environ["KNK_MAIL_DB"]))
chk("스키마 10종 모두 생성", need.issubset(tables))
if not need.issubset(tables):
    print("   missing:", sorted(need - tables))

# 5) TestClient 라우트 (500 없음)
from starlette.testclient import TestClient
c = TestClient(app)

r = c.get("/healthz")
chk("/healthz 200", r.status_code == 200)
chk("/healthz ok=true(누락 없음)", r.json().get("ok") is True)

r = c.get("/api/version")
chk("/api/version 200 knk-mail", r.status_code == 200 and r.json().get("app") == "knk-mail")

r = c.get("/", follow_redirects=False)
chk("/ → /login 리다이렉트(미로그인)", r.status_code in (302, 303) and r.headers.get("location") == "/login")

r = c.get("/mail/inbox", follow_redirects=False)
chk("미로그인 /mail/inbox → /login", r.status_code in (302, 303) and r.headers.get("location") == "/login")

r = c.get("/login")
chk("/login 200 + 앱이름", r.status_code == 200 and "KNK Eum MAIL" in r.text)
chk("/login dev 폼 노출", "개발 로그인" in r.text)

# dev 로그인 → 세션 → 메일함
r = c.post("/login/dev", data={"name": "테스트대표"}, follow_redirects=False)
chk("dev 로그인 → /mail/inbox", r.status_code in (302, 303) and r.headers.get("location") == "/mail/inbox")

r = c.get("/mail/inbox")
chk("로그인 후 /mail/inbox 200", r.status_code == 200)
chk("받은편지함 렌더(독립 DB 문구)", "독립 DB(mail.db)" in r.text and "받은편지함" in r.text)

# 메일 1통 넣고 표시 확인
with mdb.db_session() as cc:
    cc.execute("INSERT INTO users(id, login_id, name, role, is_active) VALUES(1,'dev','테스트대표','ceo',1)")
    cc.execute("INSERT INTO mail_messages(user_id, direction, from_name, subject, category, received_at) "
               "VALUES(1,'in','홍길동','[검증] 독립 메일 1통','견적','2026-06-14 10:00')")
r = c.get("/mail/inbox")
chk("삽입한 메일 제목 표시", "[검증] 독립 메일 1통" in r.text and "전체 1통" in r.text)

r = c.get("/logout", follow_redirects=False)
chk("/logout → /login", r.status_code in (302, 303) and r.headers.get("location") == "/login")

print("\nRESULT:", "ALL PASS" if ok else "HAS FAILURES")
sys.exit(0 if ok else 1)
