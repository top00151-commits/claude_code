# -*- coding: utf-8 -*-
"""메일 목록 오른쪽 클릭 메뉴 — 모든 메일함(대표 11-26 「오른쪽 클릭하면 그 항목에서 지금 쓸 수 있는 도구가 나와 바로 쓰게」).
가짜 직원·가짜 메일·임시 DB(운영 무접촉). 실행: PYTHONIOENCODING=utf-8 py -3.13 _검증/mail_ctx_menu_test.py"""
import io
import os
import re
import shutil
import subprocess
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
    _TMP = tempfile.mkdtemp(prefix="knk_ctx_")
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
        print("  [FAIL]", name, "<-", str(extra)[:400])


ME = 9851
with _db.db_session() as c:
    c.execute("INSERT INTO users(id, login_id, name, role, is_active, password) VALUES(?,?,?,?,1,'x')", (ME, "t9851", "가짜나", "member"))
    mi, _ = ms.store_inbound(c, to_email="t9851@knknara.co.kr", from_email="a@partner-demo.example", from_name="가짜",
                             subject="가짜 받은 메일", text="가짜", html="", owner_id=ME, run_ai=False, message_id="ctx-1@demo")
    mo = ms.store_outbound(c, user_id=ME, from_email="t9851@knknara.co.kr", to_email="b@partner-demo.example", subject="가짜 보낸 메일", body="가짜")
    md = ms.save_draft(c, user_id=ME, to_email="", subject="가짜 임시", body="쓰던 글", body_html="<div>쓰던 글</div>")
    mt, _ = ms.store_inbound(c, to_email="t9851@knknara.co.kr", from_email="c@partner-demo.example", from_name="가짜",
                             subject="가짜 지운 메일", text="가짜", html="", owner_id=ME, run_ai=False, message_id="ctx-2@demo")
    ms.soft_delete(c, mt, ME)
    mb, _ = ms.store_inbound(c, to_email="t9851@knknara.co.kr", from_email="d@spam-demo.example", from_name="가짜",
                             subject="가짜 스팸", text="가짜", html="", owner_id=ME, run_ai=False, message_id="ctx-3@demo")
    c.execute("UPDATE mail_messages SET is_blocked=1 WHERE id=?", (mb,))

m.get_user = lambda req: {"id": ME, "role": "member", "name": "가짜나", "team_id": None, "team_name": ""}
k = TestClient(m.app, base_url="http://127.0.0.1:5051", raise_server_exceptions=False, follow_redirects=False)
k.headers.update({"host": "works.knknara.co.kr", "x-forwarded-proto": "https"})

pages = {}
print("① 메일함마다 줄에 메일 번호 · 메뉴 코드")
for box, url, mid in (("draft", "/mail/drafts", md), ("sent", "/mail/sent", mo), ("trash", "/mail/trash", mt), ("blocked", "/mail/blocked", mb)):
    r = k.get(url)
    h = r.text
    pages[box] = h
    check("%s 200 · 줄에 data-mail-id=%d" % (box, mid), r.status_code == 200 and ('data-mail-id="%d"' % mid) in h, r.status_code)
    check("%s 오른쪽 클릭 메뉴 코드(이 메일함 몫)" % box, "['draft','sent','trash','blocked'].indexOf(BOX)" in h and "BOX==='%s'" % box in h)
h = pages["draft"]
check("임시보관: 이어 쓰기 · 새 창 · 삭제(휴지통 · ↺ 되돌리기)", "✏️ 이어 쓰기" in h and "🗗 새 창으로 이어 쓰기" in h and "toTrash(id, '임시 메일')" in h and "↺ 되돌리기" in h)
check("보낸편지함: 열기 · 새 창 · 전달 · 다시 묻기 · 중요 · 삭제", all(x in h for x in ("📄 열기", "compose('forward='+id)", "compose('nudge='+id)", "⭐ 중요 표시", "toTrash(id, '보낸 메일')")))
check("휴지통: 복원 · 완전삭제(확인 창은 purgeMail 안)", "restoreMail(null, id)" in h and "purgeMail(null, id)" in h)
check("스팸함: 열기(주의) · 스팸 아님 · 삭제", "notSpam(null, id)" in h and "toTrash(id, '스팸 메일')" in h)
check("메뉴 ✕ 닫기 = 공용(.mbx-ctx 저절로) · Esc 로도 닫힘", "['.mbx-ctx', function(el)" in h and "e.key==='Escape') closeMenu()" in h)

print("② 받은편지함 메뉴는 그대로 + ✕ 닫기")
hi = k.get("/mail/inbox").text
check("받은편지함 = 원래 메뉴(답장·삭제·다시 안 받기) · ✕ 닫기는 공용", "item('🔕 다시 안 받기(나만 · 스팸함으로)'" in hi and "['.mbx-ctx', function(el)" in hi)
check("받은편지함에서는 새 메뉴가 안 켜짐(두 메뉴 겹침 없음)", "if(BOX==='in' ||" in hi)

print("③ 메뉴로 하는 일 — 서버 길(휴지통 · 복원 · 완전삭제 · 스팸 아님)")
check("임시 메일 휴지통으로", k.post("/mail/%d/delete" % md).json().get("ok"))
check("휴지통에서 복원", k.post("/mail/%d/restore" % md).json().get("ok"))
with _db.db_session() as c:
    d = c.execute("SELECT is_deleted, direction FROM mail_messages WHERE id=?", (md,)).fetchone()
check("복원된 임시 메일 = 임시보관함 그대로", d["is_deleted"] == 0 and d["direction"] == "draft", dict(d))
check("스팸 아님 → 받은편지함으로", k.post("/mail/%d/notspam" % mb).json().get("ok"))

print("④ 화면 스크립트 문법(node --check)")
node = shutil.which("node")
if not node:
    print("  (node 없음 — 건너뜀)")
else:
    bad = []
    for box, h in pages.items():
        for i, sc in enumerate(re.findall(r"<script(?![^>]*src=)[^>]*>([\s\S]*?)</script>", h)):
            if "BOX==='" not in sc:
                continue
            fn = os.path.join(_TMP, "s_%s_%d.js" % (box, i))
            open(fn, "w", encoding="utf-8").write(sc)
            rr = subprocess.run([node, "--check", fn], capture_output=True, text=True, encoding="utf-8")
            if rr.returncode != 0:
                bad.append((box, rr.stderr[:300]))
    check("메뉴 스크립트 문법 맞음", not bad, bad)

print("\n결과: %d 통과 / %d 실패" % (P, F))
shutil.rmtree(_TMP, ignore_errors=True)
sys.exit(1 if F else 0)
