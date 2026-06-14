# -*- coding: utf-8 -*-
"""KNK Eum MAIL 기능 포팅(3단계) 검증 — 47 라우트 독립 앱 등록·렌더·액션 무500."""
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
for f in ["deps.py", "main.py", "mail_routes.py", "mail_store.py", "mail_send.py", "mail_fetch.py", "ai_client.py"]:
    try: ast.parse(rd(os.path.join(APP, f))); print("[OK] ast", f)
    except SyntaxError as e: ok=False; print("[FAIL] ast", f, e)

# 2) 환경 + import
tmp = tempfile.mkdtemp(prefix="knkmail_feat_")
os.environ["KNK_MAIL_DATA"] = tmp
os.environ["KNK_MAIL_DB"] = os.path.join(tmp, "mail.db")
os.environ["KNK_MAIL_DEV_LOGIN"] = "1"
os.environ["KNK_MAIL_PUBLIC_BASE"] = "https://mail.knknara.co.kr"

from app import db as mdb           # noqa
from app.main import app           # noqa
from starlette.testclient import TestClient
c = TestClient(app)

# 라우트 수 확인
paths = set()
for r in app.routes:
    p = getattr(r, "path", "")
    if "/mail" in p or "mail" in p:
        paths.add(p)
chk("메일 라우트 다수 등록(>=30)", len(paths) >= 30)

# 3) 미로그인 게이트
chk("미로그인 /mail/inbox → /login", c.get("/mail/inbox", follow_redirects=False).status_code in (302,303))

# 4) dev 로그인
r = c.post("/login/dev", data={"name":"테스트대표"}, follow_redirects=False)
chk("dev 로그인", r.status_code in (302,303))
with mdb.db_session() as cc:
    uid = cc.execute("SELECT id FROM users WHERE employee_no='DEV001'").fetchone()["id"]
    # 메일 2통(받은 1·삭제 1) 직접 적재(AI 호출 회피)
    cur = cc.execute("INSERT INTO mail_messages(user_id,direction,from_email,from_name,to_email,subject,"
               "body_text,body_html,category,received_at,is_deleted) VALUES(?,?,?,?,?,?,?,?,?,?,0)",
               (uid,'in','a@x.com','홍길동','test@knk-mailtest.com','[검증] 본문 보기 테스트',
                '안녕하세요 본문입니다','<p>HTML 본문 <b>굵게</b></p>','견적','2026-06-14 10:00'))
    mid = cur.lastrowid
    cc.execute("INSERT INTO mail_messages(user_id,direction,from_name,subject,category,received_at,"
               "is_deleted,deleted_at) VALUES(?,?,?,?,?,?,1,?)",
               (uid,'in','삭제인','[검증] 휴지통 메일','일반','2026-06-10 09:00','2026-06-12 10:00'))

# 5) 페이지 렌더 (200·무500)
GET_PAGES = ["/mail/inbox","/mail/sent","/mail/drafts","/mail/trash","/mail/rules",
             "/mail/signature","/mail/compose",
             "/admin/mail-inbound","/admin/mail-send","/admin/mail-fetch","/admin/mail-purge",
             f"/mail/{mid}", f"/mail/{mid}/pane"]
for p in GET_PAGES:
    r = c.get(p)
    chk(f"GET {p} 200", r.status_code == 200)

chk("받은편지함에 테스트 메일", "[검증] 본문 보기" in c.get("/mail/inbox").text)
chk("휴지통에 삭제 메일", "[검증] 휴지통 메일" in c.get("/mail/trash").text)
chk("보기 화면 본문/제목", "[검증] 본문 보기 테스트" in c.get(f"/mail/{mid}").text)

# 6) PWA
chk("/mail/manifest 200 KNK Eum MAIL", c.get("/mail/manifest.webmanifest").json().get("name")=="KNK Eum MAIL")
chk("/mail/sw.js 200", c.get("/mail/sw.js").status_code==200)
chk("/mail/icon.svg 200", c.get("/mail/icon.svg").status_code==200)
chk("/mail/app → 리다이렉트", c.get("/mail/app", follow_redirects=False).status_code in (302,303))
try:
    from PIL import Image  # noqa
    chk("/mail/icon-192.png 200(PIL)", c.get("/mail/icon-192.png").status_code==200)
except ImportError:
    print("[SKIP] PIL 미설치 — icon-png 생략(운영 requirements 에 pillow 포함)")

# 7) 액션(JSON·무500)
chk("별표 토글", c.post(f"/mail/{mid}/star").json().get("ok") is True)
chk("읽음표시", c.post(f"/mail/{mid}/read", data={"read":"1"}).json().get("ok") is True)
chk("규칙 추가", c.post("/mail/rules", data={"match_type":"sender","pattern":"x.com","category":"견적"}, follow_redirects=False).status_code in (302,303))
chk("규칙 소급적용", c.post("/mail/rules/apply").json().get("ok") is True)
chk("임시저장", c.post("/mail/draft/save", data={"to":"b@x.com","subject":"초안","body":"내용"}).json().get("ok") is True)
chk("서명 저장", c.post("/mail/signature", data={"body":"홍길동 드림"}).json().get("ok") is True)
chk("to-task 보류 안내", c.post(f"/mail/{mid}/to-task").json().get("ok") is False)
chk("to-contact 보류 안내", c.post(f"/mail/{mid}/to-contact").json().get("ok") is False)
chk("연락처자동완성 빈목록", c.post and c.get("/api/mail/contacts?q=a").json().get("items")==[])
chk("받기 토큰없음 inbound 403", c.post("/api/mail/inbound", json={"to":"x@y.com"}).status_code==403)
chk("정리 미리보기(관리자)", c.post("/admin/mail-purge/preview", data={"months":"3"}).json().get("ok") is True)
chk("디스크정리 VACUUM", c.post("/admin/mail-purge/vacuum").json().get("ok") is True)
chk("직원명부 동기화 graceful", c.post("/admin/dir-sync").json().get("ok") is False)

# 삭제→복원→완전삭제 흐름
chk("삭제(휴지통行)", c.post(f"/mail/{mid}/delete").json().get("ok") is True)
chk("복원", c.post(f"/mail/{mid}/restore").json().get("ok") is True)
chk("완전삭제", c.post(f"/mail/{mid}/purge").json().get("ok") is True)
chk("휴지통 비우기", c.post("/mail/trash/empty").json().get("ok") is True)

print("\nRESULT:", "ALL PASS" if ok else "HAS FAILURES")
sys.exit(0 if ok else 1)
